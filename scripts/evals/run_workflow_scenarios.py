#!/usr/bin/env python3
"""Run deterministic Athanor workflow trace scenarios."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evals.workflow_trace import validate_record

DEFAULT_SCENARIO_ROOT = REPO_ROOT / "tests" / "fixtures" / "workflow_evals"
GRADER_KINDS = {
    "forbid_event",
    "require_event",
    "require_order",
    "require_reference",
}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not load scenario file {path}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"scenario file root must be an object: {path}")
    return parsed


def _scenario_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    if not root.is_dir():
        raise ValueError(f"scenario root does not exist: {root}")
    return sorted(path for path in root.glob("*.json") if path.is_file())


def _record_matches(record: dict[str, Any], match: Any) -> bool:
    if not isinstance(match, dict):
        return False
    return all(record.get(key) == value for key, value in match.items())


def _matching_records(trace: list[dict[str, Any]], match: Any) -> list[dict[str, Any]]:
    return [record for record in trace if _record_matches(record, match)]


def _require_event(trace: list[dict[str, Any]], grader: dict[str, Any]) -> tuple[bool, str]:
    matches = _matching_records(trace, grader.get("match"))
    if matches:
        return True, f"matched {len(matches)} event(s)"
    return False, "required event was not found"


def _forbid_event(trace: list[dict[str, Any]], grader: dict[str, Any]) -> tuple[bool, str]:
    matches = _matching_records(trace, grader.get("match"))
    if matches:
        return False, f"forbidden event matched {len(matches)} record(s)"
    return True, "forbidden event absent"


def _require_order(trace: list[dict[str, Any]], grader: dict[str, Any]) -> tuple[bool, str]:
    before = _matching_records(trace, grader.get("before"))
    after = _matching_records(trace, grader.get("after"))
    for before_record in before:
        for after_record in after:
            if before_record["seq"] < after_record["seq"]:
                return True, (
                    f"seq {before_record['seq']} appears before seq {after_record['seq']}"
                )
    return False, "required event order was not observed"


def _require_reference(trace: list[dict[str, Any]], grader: dict[str, Any]) -> tuple[bool, str]:
    reference = grader.get("reference")
    if not isinstance(reference, str) or not reference:
        return False, "reference must be a non-empty string"
    for record in _matching_records(trace, grader.get("match")):
        references = record.get("references", [])
        if any(reference in item for item in references):
            return True, f"matched reference {reference!r}"
    return False, f"reference {reference!r} was not found"


def evaluate_grader(trace: list[dict[str, Any]], grader: dict[str, Any]) -> dict[str, Any]:
    grader_id = grader.get("id")
    kind = grader.get("kind")
    if not isinstance(grader_id, str) or not grader_id:
        grader_id = "<missing-id>"
    if kind not in GRADER_KINDS:
        return {
            "id": grader_id,
            "kind": kind,
            "status": "fail",
            "reason": f"unsupported grader kind: {kind!r}",
        }

    if kind == "require_event":
        ok, reason = _require_event(trace, grader)
    elif kind == "forbid_event":
        ok, reason = _forbid_event(trace, grader)
    elif kind == "require_order":
        ok, reason = _require_order(trace, grader)
    else:
        ok, reason = _require_reference(trace, grader)

    return {
        "id": grader_id,
        "kind": kind,
        "status": "pass" if ok else "fail",
        "reason": reason,
    }


def _validate_trace(raw_trace: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_trace, list):
        raise ValueError("scenario trace must be a list")
    return sorted(
        [validate_record(item) for item in raw_trace],
        key=lambda item: item["seq"],
    )


def evaluate_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    scenario_id = scenario.get("id")
    if not isinstance(scenario_id, str) or not scenario_id:
        raise ValueError("scenario id must be a non-empty string")
    min_score = scenario.get("min_score", 1.0)
    if not isinstance(min_score, (int, float)) or isinstance(min_score, bool):
        raise ValueError(f"scenario {scenario_id}: min_score must be numeric")
    trace = _validate_trace(scenario.get("trace"))
    raw_graders = scenario.get("graders")
    if not isinstance(raw_graders, list) or not raw_graders:
        raise ValueError(f"scenario {scenario_id}: graders must be a non-empty list")
    graders = [
        evaluate_grader(trace, grader if isinstance(grader, dict) else {})
        for grader in raw_graders
    ]
    passed = sum(1 for grader in graders if grader["status"] == "pass")
    total = len(graders)
    score = round(passed / total, 3)
    status = "pass" if score >= float(min_score) else "fail"
    return {
        "id": scenario_id,
        "status": status,
        "score": score,
        "passed": passed,
        "total": total,
        "graders": graders,
    }


def evaluate_root(scenario_root: Path) -> dict[str, Any]:
    scenarios: list[dict[str, Any]] = []
    for path in _scenario_files(scenario_root):
        parsed = _load_json(path)
        raw_scenarios = parsed.get("scenarios")
        if not isinstance(raw_scenarios, list):
            raise ValueError(f"scenario file must contain scenarios[]: {path}")
        for scenario in raw_scenarios:
            if not isinstance(scenario, dict):
                raise ValueError(f"scenario entry must be an object: {path}")
            result = evaluate_scenario(scenario)
            result["file"] = str(path)
            scenarios.append(result)
    status = "pass" if scenarios and all(item["status"] == "pass" for item in scenarios) else "fail"
    return {
        "schema_version": 1,
        "status": status,
        "scenario_root": str(scenario_root),
        "scenarios": scenarios,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Athanor workflow eval scenarios.")
    parser.add_argument("--scenario-root", type=Path, default=DEFAULT_SCENARIO_ROOT)
    parser.add_argument("--json", action="store_true", help="Emit JSON report.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    try:
        report = evaluate_root(args.scenario_root)
    except ValueError as exc:
        print(f"workflow scenario eval: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for scenario in report["scenarios"]:
            print(
                f"{scenario['status']}: {scenario['id']} "
                f"score={scenario['score']} ({scenario['passed']}/{scenario['total']})"
            )
            for grader in scenario["graders"]:
                if grader["status"] != "pass":
                    print(f"  - {grader['id']}: {grader['reason']}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
