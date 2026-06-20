#!/usr/bin/env python3
"""Append-only run log helper for Athanor lfg-goal loops."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

VALID_STATUSES = {"blocked", "conflict", "fail", "info", "pass", "warn"}
RISKY_TASK_VALUES = {"high", "risky", "unsafe"}


class LoopRunLogError(ValueError):
    """Raised when a loop run-log input is malformed."""


def _iso_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LoopRunLogError(f"malformed JSON: {path}: {exc.msg}") from exc
    except OSError as exc:
        raise LoopRunLogError(f"could not read JSON: {path}") from exc
    if not isinstance(parsed, dict):
        raise LoopRunLogError(f"JSON root must be an object: {path}")
    return parsed


def load_goal_state(goal_dir: Path | str) -> dict[str, Any]:
    goal_path = Path(goal_dir)
    state = _read_json(goal_path / "state.json")
    goal_id = state.get("goal_id")
    if not isinstance(goal_id, str) or len(goal_id) != 8:
        raise LoopRunLogError("state.json must contain an 8-character goal_id")
    return state


def _run_log_path(goal_dir: Path | str, state: dict[str, Any] | None = None) -> Path:
    goal_path = Path(goal_dir)
    state_data = state if state is not None else load_goal_state(goal_path)
    configured = state_data.get("loop_run_log", "run-log.jsonl")
    if not isinstance(configured, str) or not configured:
        raise LoopRunLogError("loop_run_log must be a non-empty string")
    path = Path(configured)
    if path.is_absolute():
        return path
    return goal_path / path


def load_run_log(goal_dir: Path | str) -> list[dict[str, Any]]:
    state = load_goal_state(goal_dir)
    path = _run_log_path(goal_dir, state)
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as exc:
            raise LoopRunLogError(
                f"malformed JSONL record at {path}:{line_number}: {exc.msg}"
            ) from exc
        if not isinstance(parsed, dict):
            raise LoopRunLogError(f"JSONL record must be an object at {path}:{line_number}")
        records.append(parsed)
    return records


def _next_sequence(records: list[dict[str, Any]]) -> int:
    sequences = [item.get("sequence") for item in records]
    ints = [item for item in sequences if isinstance(item, int)]
    return (max(ints) if ints else 0) + 1


def _budget_snapshot(
    state: dict[str, Any],
    *,
    current_cycle: int | None = None,
    wall_minutes_used: int | None = None,
    token_estimate_used: int | None = None,
) -> dict[str, int | None]:
    budget = state.get("budget", {})
    if not isinstance(budget, dict):
        budget = {}
    return {
        "max_cycles": budget.get("max_cycles"),
        "current_cycle": current_cycle
        if current_cycle is not None
        else state.get("current_cycle"),
        "max_wall_minutes": budget.get("max_wall_minutes"),
        "wall_minutes_used": wall_minutes_used,
        "max_token_estimate": budget.get("max_token_estimate"),
        "token_estimate_used": token_estimate_used,
    }


def append_run_record(
    goal_dir: Path | str,
    *,
    event: str,
    status: str = "info",
    message: str | None = None,
    references: list[str] | None = None,
    wall_minutes_used: int | None = None,
    token_estimate_used: int | None = None,
) -> dict[str, Any]:
    if status not in VALID_STATUSES:
        raise LoopRunLogError(f"unsupported status: {status}")
    if not event:
        raise LoopRunLogError("event is required")

    state = load_goal_state(goal_dir)
    records = load_run_log(goal_dir)
    record = {
        "schema_version": 1,
        "goal_id": state["goal_id"],
        "sequence": _next_sequence(records),
        "timestamp": _iso_now(),
        "event": event,
        "status": status,
        "acting_on": state.get("acting_on"),
        "cycle": state.get("current_cycle"),
        "evaluator_role": state.get("last_evaluator_role"),
        "message": message or event.replace("_", " "),
        "references": references or [],
        "budget": _budget_snapshot(
            state,
            wall_minutes_used=wall_minutes_used,
            token_estimate_used=token_estimate_used,
        ),
        "irreversible_actions": 0,
    }
    path = _run_log_path(goal_dir, state)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def _budget_warnings(
    state: dict[str, Any],
    *,
    current_cycle: int | None,
    wall_minutes_used: int | None,
    token_estimate_used: int | None,
) -> list[str]:
    snapshot = _budget_snapshot(
        state,
        current_cycle=current_cycle,
        wall_minutes_used=wall_minutes_used,
        token_estimate_used=token_estimate_used,
    )
    warnings: list[str] = []
    if (
        isinstance(snapshot["max_cycles"], int)
        and isinstance(snapshot["current_cycle"], int)
        and snapshot["current_cycle"] >= snapshot["max_cycles"]
    ):
        warnings.append("max_cycles_reached")
    if (
        isinstance(snapshot["max_wall_minutes"], int)
        and isinstance(snapshot["wall_minutes_used"], int)
        and snapshot["wall_minutes_used"] >= snapshot["max_wall_minutes"]
    ):
        warnings.append("max_wall_minutes_reached")
    if (
        isinstance(snapshot["max_token_estimate"], int)
        and isinstance(snapshot["token_estimate_used"], int)
        and snapshot["token_estimate_used"] >= snapshot["max_token_estimate"]
    ):
        warnings.append("max_token_estimate_reached")
    return warnings


def _min_attempt_gate(
    state: dict[str, Any],
    records: list[dict[str, Any]],
    *,
    task_risk: str | None,
    score_target: bool,
    attempts_done: int | None,
) -> dict[str, Any]:
    min_attempts = state.get("min_attempts", 0)
    if not isinstance(min_attempts, int) or min_attempts < 0:
        min_attempts = 0
    actual_attempts = attempts_done
    if actual_attempts is None:
        actual_attempts = sum(1 for item in records if item.get("event") == "cycle_started")
    applies = score_target or (task_risk in RISKY_TASK_VALUES)
    status = "blocked" if applies and actual_attempts < min_attempts else "pass"
    if not applies:
        status = "not_applicable"
    return {
        "status": status,
        "required": min_attempts,
        "actual": actual_attempts,
        "task_risk": task_risk,
        "score_target": score_target,
    }


def inspect_goal_dir(
    goal_dir: Path | str,
    *,
    requested_goal_id: str | None = None,
    current_cycle: int | None = None,
    wall_minutes_used: int | None = None,
    token_estimate_used: int | None = None,
    task_risk: str | None = None,
    score_target: bool = False,
    attempts_done: int | None = None,
) -> dict[str, Any]:
    state = load_goal_state(goal_dir)
    records = load_run_log(goal_dir)
    acting_on = state.get("acting_on")
    lock_conflict = None
    lock_status = state.get("lock_status", "active")
    if requested_goal_id is not None and acting_on != requested_goal_id:
        lock_status = "conflict"
        lock_conflict = {
            "acting_on": acting_on,
            "requested_goal_id": requested_goal_id,
        }
    warnings = _budget_warnings(
        state,
        current_cycle=current_cycle,
        wall_minutes_used=wall_minutes_used,
        token_estimate_used=token_estimate_used,
    )
    min_gate = _min_attempt_gate(
        state,
        records,
        task_risk=task_risk,
        score_target=score_target,
        attempts_done=attempts_done,
    )
    status = "pass"
    if lock_conflict or warnings or min_gate["status"] == "blocked":
        status = "warn"
    return {
        "schema_version": 1,
        "status": status,
        "profile": {
            "id": "loop-run-log",
            "mutates_files_by_default": False,
            "external_telemetry": False,
        },
        "goal_id": state["goal_id"],
        "acting_on": acting_on,
        "lock_status": lock_status,
        "lock_conflict": lock_conflict,
        "budget": _budget_snapshot(
            state,
            current_cycle=current_cycle,
            wall_minutes_used=wall_minutes_used,
            token_estimate_used=token_estimate_used,
        ),
        "budget_warnings": warnings,
        "min_attempt_gate": min_gate,
        "records": records,
        "summary": {
            "records": len(records),
            "latest_sequence": records[-1]["sequence"] if records else 0,
            "budget_warnings": len(warnings),
            "irreversible_actions": 0,
        },
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect or append lfg-goal run logs.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    append = subparsers.add_parser("append", help="Append one run-log record.")
    append.add_argument("--goal-dir", type=Path, required=True)
    append.add_argument("--event", required=True)
    append.add_argument("--status", default="info", choices=sorted(VALID_STATUSES))
    append.add_argument("--message")
    append.add_argument("--reference", action="append", dest="references")
    append.add_argument("--wall-minutes-used", type=int)
    append.add_argument("--token-estimate-used", type=int)
    append.add_argument("--json", action="store_true")

    inspect = subparsers.add_parser("inspect", help="Inspect a goal run log.")
    inspect.add_argument("--goal-dir", type=Path, required=True)
    inspect.add_argument("--requested-goal-id")
    inspect.add_argument("--current-cycle", type=int)
    inspect.add_argument("--wall-minutes-used", type=int)
    inspect.add_argument("--token-estimate-used", type=int)
    inspect.add_argument("--task-risk")
    inspect.add_argument("--score-target", action="store_true")
    inspect.add_argument("--attempts-done", type=int)
    inspect.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    try:
        if args.command == "append":
            result = append_run_record(
                args.goal_dir,
                event=args.event,
                status=args.status,
                message=args.message,
                references=args.references,
                wall_minutes_used=args.wall_minutes_used,
                token_estimate_used=args.token_estimate_used,
            )
        else:
            result = inspect_goal_dir(
                args.goal_dir,
                requested_goal_id=args.requested_goal_id,
                current_cycle=args.current_cycle,
                wall_minutes_used=args.wall_minutes_used,
                token_estimate_used=args.token_estimate_used,
                task_risk=args.task_risk,
                score_target=args.score_target,
                attempts_done=args.attempts_done,
            )
    except LoopRunLogError as exc:
        print(f"loop-run-log: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{result['status']}: {result.get('event', args.command)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
