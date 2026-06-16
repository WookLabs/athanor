#!/usr/bin/env python3
"""Evidence-bound gate for /athanor:work Spec-then-TDD results.

Consumes PostToolUse pytest evidence JSONL plus a normalized ATHANOR_RESULT
JSON object. Hybrid v1 behavior:

- matching evidence => pass
- evidence mismatch => failure in warn/strict, observation in observe
- missing evidence => concern in warn, failure in strict, observation in observe

This script does not parse the free-form ATHANOR_RESULT block. The leader
normalizes the fields it already validates into JSON and passes that here.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

EVIDENCE_MODES = {"observe", "warn", "strict"}


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _norm_command(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.strip().split())


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [v for v in value if isinstance(v, str)]


def _load_evidence(path: Path) -> tuple[list[dict], list[str]]:
    records: list[dict] = []
    concerns: list[str] = []

    if not path.is_file():
        return [], [f"evidence file missing: {path}"]

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [], [f"could not read evidence file: {exc}"]

    for lineno, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as exc:
            concerns.append(f"malformed JSONL line {lineno}: {exc.msg}")
            continue
        if not isinstance(parsed, dict):
            concerns.append(f"malformed JSONL line {lineno}: record is not an object")
            continue
        parsed["_line"] = lineno
        records.append(parsed)
    return records, concerns


def _red_entries(result: dict) -> list[dict]:
    raw = result.get("red_evidence")
    if not isinstance(raw, list):
        return []
    return [entry for entry in raw if isinstance(entry, dict)]


def _red_entry_matches_record(entry: dict, record: dict) -> bool:
    entry_command = _norm_command(entry.get("command"))
    record_command = _norm_command(record.get("command"))
    if entry_command and record_command and entry_command == record_command:
        return True

    node_id = entry.get("test_node_id")
    if not isinstance(node_id, str) or not node_id:
        return False

    targets = _string_list(record.get("test_targets"))
    primary = record.get("primary_target")
    if isinstance(primary, str):
        targets.append(primary)
    if node_id in targets:
        return True
    if record_command and node_id in record_command:
        return True
    return False


def _evaluate_red_evidence(result: dict, records: list[dict]) -> tuple[list[str], list[str], list[dict]]:
    failures: list[str] = []
    concerns: list[str] = []
    matches: list[dict] = []

    for index, entry in enumerate(_red_entries(result), start=1):
        expected_exit = _as_int(entry.get("exit_code"))
        command = entry.get("command") if isinstance(entry.get("command"), str) else ""
        node_id = entry.get("test_node_id") if isinstance(entry.get("test_node_id"), str) else ""
        matched = [record for record in records if _red_entry_matches_record(entry, record)]

        label = node_id or command or f"red_evidence[{index}]"
        if not matched:
            concerns.append(f"missing evidence for red_evidence[{index}]: {label}")
            continue

        exit_matched = [
            record for record in matched if _as_int(record.get("exit_code")) == expected_exit
        ]
        if not exit_matched:
            observed = sorted({
                str(_as_int(record.get("exit_code"))) for record in matched
            })
            failures.append(
                f"exit code mismatch for red_evidence[{index}]: {label}; "
                f"reported={expected_exit} observed={observed}"
            )
            continue

        record = exit_matched[-1]
        matches.append(
            {
                "kind": "red_evidence",
                "index": index,
                "reported_exit_code": expected_exit,
                "evidence_exit_code": _as_int(record.get("exit_code")),
                "evidence_line": record.get("_line"),
                "command": command,
                "test_node_id": node_id,
            }
        )
    return failures, concerns, matches


def _latest_full_suite(records: list[dict]) -> dict | None:
    full_suite = [record for record in records if record.get("scope") == "full_suite"]
    if not full_suite:
        return None
    return full_suite[-1]


def _evaluate_full_suite(result: dict, records: list[dict]) -> tuple[list[str], list[str], list[dict]]:
    if result.get("full_suite_passed") is not True:
        return [], [], []

    latest = _latest_full_suite(records)
    if latest is None:
        return [], ["missing evidence for full_suite_passed=true"], []

    observed = _as_int(latest.get("exit_code"))
    if observed != 0:
        return [
            "full_suite_passed=true but latest full-suite evidence "
            f"exit_code={observed}"
        ], [], []

    return [], [], [
        {
            "kind": "full_suite",
            "reported_full_suite_passed": True,
            "evidence_exit_code": observed,
            "evidence_line": latest.get("_line"),
            "command": latest.get("command") if isinstance(latest.get("command"), str) else "",
        }
    ]


def _needs_evidence(result: dict) -> bool:
    return bool(_red_entries(result)) or result.get("full_suite_passed") is True


def _normalize_mode(mode: str) -> str:
    if mode not in EVIDENCE_MODES:
        raise ValueError(f"unsupported evidence mode: {mode}")
    return mode


def _apply_mode(failures: list[str], concerns: list[str], mode: str) -> tuple[str, list[str], list[str], list[str]]:
    if mode == "observe":
        return "pass", [], [], failures + concerns
    if mode == "strict":
        strict_failures = failures + concerns
        return ("failure" if strict_failures else "pass"), strict_failures, [], []
    return ("failure" if failures else "concern" if concerns else "pass"), failures, concerns, []


def evaluate_result_against_evidence(
    result: dict,
    evidence_path: Path | str,
    *,
    mode: str = "warn",
) -> dict:
    """Return JSON-serializable gate report for normalized ATHANOR_RESULT."""
    if not isinstance(result, dict):
        raise ValueError("result must be a JSON object")
    mode = _normalize_mode(mode)

    evidence = Path(evidence_path)
    records, concerns = _load_evidence(evidence)

    failures: list[str] = []
    matches: list[dict] = []
    if _needs_evidence(result):
        red_failures, red_concerns, red_matches = _evaluate_red_evidence(result, records)
        suite_failures, suite_concerns, suite_matches = _evaluate_full_suite(result, records)
        failures.extend(red_failures)
        failures.extend(suite_failures)
        concerns.extend(red_concerns)
        concerns.extend(suite_concerns)
        matches.extend(red_matches)
        matches.extend(suite_matches)

    status, failures, concerns, observations = _apply_mode(failures, concerns, mode)
    return {
        "schema_version": 1,
        "mode": mode,
        "status": status,
        "failures": failures,
        "concerns": concerns,
        "observations": observations,
        "matches": matches,
        "evidence_path": str(evidence),
    }


def _load_result_json(arg: str) -> dict:
    try:
        raw = sys.stdin.read() if arg == "-" else Path(arg).read_text(encoding="utf-8")
        parsed = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid result json: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("invalid result json: root must be an object")
    return parsed


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cross-check normalized ATHANOR_RESULT JSON against PostToolUse pytest evidence."
    )
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--result-json", required=True)
    parser.add_argument("--mode", choices=sorted(EVIDENCE_MODES), default="warn")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    try:
        result = _load_result_json(args.result_json)
    except ValueError as exc:
        sys.stderr.write(f"{exc}\n")
        return 2

    report = evaluate_result_against_evidence(result, args.evidence, mode=args.mode)
    sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 1 if report["status"] == "failure" else 0


if __name__ == "__main__":
    raise SystemExit(main())
