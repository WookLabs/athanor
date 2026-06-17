#!/usr/bin/env python3
"""Promote a validated workflow trace JSONL file into a scenario fixture."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evals.workflow_trace import load_trace


def _matches(record: dict[str, Any], event_type: str) -> dict[str, str]:
    return {"event_type": event_type, "phase": str(record["phase"])}


def build_scenario(
    *,
    trace: list[dict[str, Any]],
    scenario_id: str,
    description: str,
) -> dict[str, Any]:
    if not trace:
        raise ValueError("trace has no records")
    started = next(
        (item for item in trace if item["event_type"] == "workflow.started"),
        None,
    )
    finished = next(
        (item for item in reversed(trace) if item["event_type"] == "workflow.finished"),
        None,
    )
    if started is None:
        raise ValueError("trace must contain workflow.started")
    if finished is None:
        raise ValueError("trace must contain workflow.finished")

    graders: list[dict[str, Any]] = [
        {
            "id": "workflow-started",
            "kind": "require_event",
            "match": _matches(started, "workflow.started"),
        },
        {
            "id": "workflow-finished",
            "kind": "require_event",
            "match": _matches(finished, "workflow.finished"),
        },
        {
            "id": "started-before-finished",
            "kind": "require_order",
            "before": _matches(started, "workflow.started"),
            "after": _matches(finished, "workflow.finished"),
        },
    ]

    escalation = next(
        (item for item in trace if item["event_type"] == "escalation.required"),
        None,
    )
    if escalation is not None:
        graders.append(
            {
                "id": "escalation-recorded",
                "kind": "require_event",
                "match": _matches(escalation, "escalation.required"),
            }
        )

    verifier = next(
        (
            item
            for item in trace
            if item["event_type"] == "verifier.result" and item.get("references")
        ),
        None,
    )
    if verifier is not None:
        reference = Path(str(verifier["references"][0])).name
        graders.append(
            {
                "id": "verifier-reference-present",
                "kind": "require_reference",
                "match": _matches(verifier, "verifier.result"),
                "reference": reference,
            }
        )

    return {
        "schema_version": 1,
        "scenarios": [
            {
                "id": scenario_id,
                "description": description,
                "min_score": 1.0,
                "trace": trace,
                "graders": graders,
            }
        ],
    }


def write_fixture(path: Path, scenario_file: dict[str, Any], *, force: bool) -> None:
    if path.exists() and not force:
        raise ValueError(f"output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(scenario_file, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Promote workflow trace JSONL to scenario fixture."
    )
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--scenario-id", required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    try:
        scenario_file = build_scenario(
            trace=load_trace(args.trace),
            scenario_id=args.scenario_id,
            description=args.description,
        )
        write_fixture(args.output, scenario_file, force=args.force)
    except ValueError as exc:
        print(f"promote trace scenario: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "pass",
                    "output": str(args.output),
                    "scenario_id": args.scenario_id,
                    "graders": len(scenario_file["scenarios"][0]["graders"]),
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(f"promoted {args.scenario_id} -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
