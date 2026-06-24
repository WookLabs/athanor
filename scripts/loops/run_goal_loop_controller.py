#!/usr/bin/env python3
"""CLI for Athanor durable lfg-goal loop decisions."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evals.workflow_trace import TraceWriter
from scripts.loops.goal_loop_controller import (
    EvidenceSummary,
    LoopStateError,
    apply_decision,
    decide_next_action,
    load_loop_state,
    write_loop_state_atomic,
)

STOP_ACTIONS = {"stop_max_iterations", "stop_no_progress"}
# Non-forward "do not proceed" actions: the controller refuses to advance (block /
# escalate / refuse) but did not reach a terminal abort. Exit-code-wise they are halts,
# so a re-driver branching on exit code must NOT read them as "proceed".
BLOCK_ACTIONS = {
    "block_failed_eval",
    "run_scope_drift",
    "require_assessment_evidence",
    "require_receipt_validation",
    "require_eval_evidence",
    "refuse_terminal_state",
}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LoopStateError(f"malformed evidence JSON: {exc.msg}") from exc
    except OSError as exc:
        raise LoopStateError(f"could not read evidence file: {path}") from exc
    if not isinstance(parsed, dict):
        raise LoopStateError("evidence root must be an object")
    return parsed


def _write_trace(
    *,
    trace_path: Path,
    trace_id: str,
    state_path: Path,
    decision_json: dict[str, Any],
) -> None:
    references = [str(state_path), *decision_json.get("references", [])]
    writer = TraceWriter(trace_path, trace_id=trace_id)
    writer.append(
        phase="lfg-goal",
        event_type="loop.decision",
        actor="gate",
        status=decision_json["status"],
        message=decision_json["reason"],
        references=references,
        evidence={
            "action": decision_json["action"],
            "next_cycle_state": decision_json["next_cycle_state"],
            "next_cycle_phase": decision_json["next_cycle_phase"],
            **decision_json["evidence"],
        },
    )


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Decide the next action for an Athanor durable lfg-goal loop."
    )
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--trace-path", type=Path)
    parser.add_argument("--trace-id")
    parser.add_argument("--write-state", action="store_true")
    parser.add_argument("--json", action="store_true", help="Emit JSON decision.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    try:
        state = load_loop_state(args.state)
        evidence = EvidenceSummary.from_dict(_load_json(args.evidence))
        decision = decide_next_action(state, evidence)
        if args.write_state:
            write_loop_state_atomic(args.state, apply_decision(state, decision))
        decision_json = decision.to_dict()
        if args.trace_path is not None:
            _write_trace(
                trace_path=args.trace_path,
                trace_id=args.trace_id or f"goal-{decision.goal_id}",
                state_path=args.state,
                decision_json=decision_json,
            )
    except LoopStateError as exc:
        print(f"durable loop controller: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(decision_json, indent=2, sort_keys=True))
    else:
        print(f"{decision.status}: {decision.action} - {decision.reason}")
    return 1 if decision.action in (STOP_ACTIONS | BLOCK_ACTIONS) else 0


if __name__ == "__main__":
    raise SystemExit(main())
