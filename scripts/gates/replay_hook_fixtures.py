#!/usr/bin/env python3
"""Replay sanitized hook payload fixtures against athanor hook scripts.

This is a development/CI gate, not a Claude Code runtime hook. It keeps
synthetic and future live-redacted payloads replayable before any
evidence-only behavior is promoted to strict enforcement.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS_DIR = REPO_ROOT / "scripts" / "hooks"
STOP_SCRIPT = HOOKS_DIR / "stop_verify_claims.py"
PRETOOL_SCRIPT = HOOKS_DIR / "pretool_dispatcher.py"
POSTTOOL_SCRIPT = HOOKS_DIR / "posttool_evidence_sniffer.py"
DEFAULT_SESSION_ID = "2026-06-16-001"
FORBIDDEN_FIXTURE_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"BEGIN (?:RSA |OPENSSH |PRIVATE )?PRIVATE KEY"),
    re.compile(r"C:\\Users\\", re.IGNORECASE),
    re.compile(r"C--Users-[A-Za-z0-9_.-]+", re.IGNORECASE),
    re.compile(r"/home/[^/]+/"),
    re.compile(r"private-user-images\.githubusercontent\.com"),
]


def _load_index(fixture_root: Path) -> dict:
    path = fixture_root / "index.json"
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not load fixture index {path}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("fixture index root must be a JSON object")
    fixtures = parsed.get("fixtures")
    if not isinstance(fixtures, list):
        raise ValueError("fixture index must contain fixtures[]")
    return parsed


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _make_project(root: Path, fixture: dict) -> tuple[Path, Path]:
    project = root / "project"
    session_id = fixture.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        session_id = DEFAULT_SESSION_ID
    session_dir = project / ".athanor" / "sessions" / session_id
    (session_dir / ".hook-state").mkdir(parents=True)
    _write_json(
        project / "athanor.json",
        {
            "hooks": {
                "profile": "standard",
                "freeze": {"mode": "session"},
            }
        },
    )
    return project, session_dir


def _materialize_payload(payload: dict, project: Path) -> dict:
    payload = copy.deepcopy(payload)
    transcript_entries = payload.pop("_athanor_transcript_entries", None)
    if transcript_entries is not None:
        if not isinstance(transcript_entries, list):
            raise ValueError("_athanor_transcript_entries must be a list")
        transcript = project / ".athanor" / "replay" / "transcript.jsonl"
        transcript.parent.mkdir(parents=True, exist_ok=True)
        transcript.write_text(
            "\n".join(json.dumps(item, sort_keys=True) for item in transcript_entries) + "\n",
            encoding="utf-8",
        )
        payload["transcript_path"] = str(transcript)
    return payload


def _run_script(script: Path, payload: dict, project: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=str(project),
    )
    return {
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def _jsonl_records(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    records: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parsed = json.loads(line)
        if isinstance(parsed, dict):
            records.append(parsed)
    return records


def _fixture_safety_errors(fixture: dict) -> list[str]:
    errors: list[str] = []
    raw = json.dumps(fixture, sort_keys=True)
    for pattern in FORBIDDEN_FIXTURE_PATTERNS:
        if pattern.search(raw):
            errors.append(f"forbidden fixture token: {pattern.pattern}")

    if fixture.get("source_level") == "live-redacted":
        redaction = fixture.get("redaction")
        if not isinstance(redaction, dict):
            errors.append("live-redacted fixture missing redaction metadata")
        else:
            if redaction.get("review_required") is not True:
                errors.append("live-redacted fixture redaction metadata must require review")
            rules = redaction.get("rules")
            if not isinstance(rules, list):
                errors.append("live-redacted fixture redaction metadata must list rules")
    return errors


def _is_subset(actual: Any, expected: Any) -> bool:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False
        return all(key in actual and _is_subset(actual[key], value) for key, value in expected.items())
    if isinstance(expected, list):
        if not isinstance(actual, list):
            return False
        for expected_item in expected:
            if not any(_is_subset(actual_item, expected_item) for actual_item in actual):
                return False
        return True
    return actual == expected


def _check_expected(
    *,
    fixture: dict,
    actual: dict,
    session_dir: Path,
) -> list[str]:
    expected = fixture.get("expected")
    if not isinstance(expected, dict):
        return ["fixture expected must be a JSON object"]

    errors: list[str] = []
    if "exit_code" in expected and actual.get("exit_code") != expected["exit_code"]:
        errors.append(
            f"exit_code expected {expected['exit_code']} got {actual.get('exit_code')}"
        )

    for stream in ("stdout", "stderr"):
        for needle in expected.get(f"{stream}_contains", []):
            if not isinstance(needle, str):
                errors.append(f"{stream}_contains item must be a string")
                continue
            if needle not in actual.get(stream, ""):
                errors.append(f"{stream} missing substring: {needle!r}")

    evidence = expected.get("evidence", {})
    if evidence is not None and not isinstance(evidence, dict):
        errors.append("expected.evidence must be an object")
        return errors

    for rel_path, expected_records in evidence.items():
        if not isinstance(rel_path, str) or not isinstance(expected_records, list):
            errors.append("expected.evidence entries must map path -> list")
            continue
        path = session_dir / ".hook-state" / rel_path
        records = _jsonl_records(path)
        for expected_record in expected_records:
            if not any(_is_subset(record, expected_record) for record in records):
                errors.append(
                    f"{rel_path} missing record subset: "
                    f"{json.dumps(expected_record, sort_keys=True)}"
                )

    return errors


def replay_fixture(fixture: dict) -> dict:
    fixture_id = fixture.get("id", "<missing-id>")
    event = fixture.get("event")
    payload = fixture.get("payload")
    safety_errors = _fixture_safety_errors(fixture)
    if safety_errors:
        return {
            "id": fixture_id,
            "event": event,
            "source_level": fixture.get("source_level"),
            "status": "fail",
            "errors": safety_errors,
            "exit_code": None,
        }
    if not isinstance(event, str) or not isinstance(payload, dict):
        return {
            "id": fixture_id,
            "event": event,
            "status": "fail",
            "errors": ["fixture must contain string event and object payload"],
        }

    with tempfile.TemporaryDirectory(prefix="athanor-hook-replay-") as tmp:
        project, session_dir = _make_project(Path(tmp), fixture)
        materialized = _materialize_payload(payload, project)

        if event == "Stop":
            actual = _run_script(STOP_SCRIPT, materialized, project)
        elif event == "PreToolUse":
            actual = _run_script(PRETOOL_SCRIPT, materialized, project)
        elif event == "PostToolUse":
            actual = _run_script(POSTTOOL_SCRIPT, materialized, project)
        else:
            actual = {"exit_code": 1, "stdout": "", "stderr": f"unsupported event {event}"}

        errors = _check_expected(fixture=fixture, actual=actual, session_dir=session_dir)
        return {
            "id": fixture_id,
            "event": event,
            "source_level": fixture.get("source_level"),
            "status": "pass" if not errors else "fail",
            "errors": errors,
            "exit_code": actual.get("exit_code"),
        }


def replay_index(fixture_root: Path, event: str | None = None) -> dict:
    index = _load_index(fixture_root)
    fixtures = index["fixtures"]
    if event is not None:
        fixtures = [item for item in fixtures if item.get("event") == event]

    results = [replay_fixture(item) for item in fixtures]
    status = "pass" if all(item["status"] == "pass" for item in results) else "fail"
    return {
        "schema_version": 1,
        "status": status,
        "total": len(results),
        "results": results,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay athanor hook payload fixtures.")
    parser.add_argument(
        "--fixture-root",
        type=Path,
        default=REPO_ROOT / "tests" / "fixtures" / "hooks",
    )
    parser.add_argument("--event", choices=["Stop", "PreToolUse", "PostToolUse"])
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    try:
        report = replay_index(args.fixture_root, args.event)
    except ValueError as exc:
        print(f"hook fixture replay: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for item in report["results"]:
            print(f"{item['status']}: {item['id']} ({item['event']})")
            for error in item["errors"]:
                print(f"  - {error}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
