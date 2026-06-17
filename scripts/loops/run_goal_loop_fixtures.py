#!/usr/bin/env python3
"""Run deterministic Athanor durable loop controller fixtures."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.loops.goal_loop_controller import (
    EvidenceSummary,
    LoopState,
    LoopStateError,
    apply_decision,
    decide_next_action,
)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not load fixture file {path}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"fixture root must be an object: {path}")
    return parsed


def _fixture_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    if not root.is_dir():
        raise ValueError(f"fixture root does not exist: {root}")
    return sorted(path for path in root.glob("*.json") if path.is_file())


def _compare_partial(actual: dict[str, Any], expected: dict[str, Any], prefix: str) -> list[str]:
    mismatches: list[str] = []
    for key, expected_value in expected.items():
        actual_value = actual.get(key)
        if actual_value != expected_value:
            mismatches.append(
                f"{prefix}.{key}: expected {expected_value!r}, got {actual_value!r}"
            )
    return mismatches


def evaluate_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    scenario_id = scenario.get("id")
    if not isinstance(scenario_id, str) or not scenario_id:
        raise ValueError("scenario id must be a non-empty string")
    try:
        state = LoopState.from_dict(scenario.get("state"))
        evidence = EvidenceSummary.from_dict(scenario.get("evidence"))
        decision = decide_next_action(state, evidence)
        next_state = apply_decision(state, decision)
    except LoopStateError as exc:
        return {
            "id": scenario_id,
            "status": "fail",
            "reason": str(exc),
        }

    expected = scenario.get("expected")
    if not isinstance(expected, dict):
        raise ValueError(f"scenario {scenario_id}: expected must be an object")
    mismatches = _compare_partial(decision.to_dict(), expected.get("decision", {}), "decision")
    expected_state = expected.get("state", {})
    if expected_state:
        if not isinstance(expected_state, dict):
            raise ValueError(f"scenario {scenario_id}: expected.state must be an object")
        mismatches.extend(_compare_partial(next_state.to_dict(), expected_state, "state"))

    return {
        "id": scenario_id,
        "status": "fail" if mismatches else "pass",
        "action": decision.action,
        "decision_status": decision.status,
        "mismatches": mismatches,
    }


def evaluate_root(fixture_root: Path) -> dict[str, Any]:
    scenarios: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for path in _fixture_files(fixture_root):
        parsed = _load_json(path)
        if parsed.get("schema_version") != 1:
            raise ValueError(f"fixture schema_version must be 1: {path}")
        raw_scenarios = parsed.get("scenarios")
        if not isinstance(raw_scenarios, list):
            raise ValueError(f"fixture file must contain scenarios[]: {path}")
        for scenario in raw_scenarios:
            if not isinstance(scenario, dict):
                raise ValueError(f"scenario entry must be an object: {path}")
            scenario_id = scenario.get("id")
            if isinstance(scenario_id, str):
                if scenario_id in seen_ids:
                    raise ValueError(f"duplicate durable loop scenario id: {scenario_id}")
                seen_ids.add(scenario_id)
            result = evaluate_scenario(scenario)
            result["file"] = str(path)
            scenarios.append(result)
    status = "pass" if scenarios and all(item["status"] == "pass" for item in scenarios) else "fail"
    return {
        "schema_version": 1,
        "status": status,
        "fixture_root": str(fixture_root),
        "scenarios": scenarios,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run durable loop controller fixtures.")
    parser.add_argument("--fixture-root", type=Path, required=True)
    parser.add_argument("--json", action="store_true", help="Emit JSON report.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    try:
        report = evaluate_root(args.fixture_root)
    except ValueError as exc:
        print(f"durable loop fixture eval: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for scenario in report["scenarios"]:
            print(f"{scenario['status']}: {scenario['id']} action={scenario.get('action')}")
            for mismatch in scenario.get("mismatches", []):
                print(f"  - {mismatch}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
