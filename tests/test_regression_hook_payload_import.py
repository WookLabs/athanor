"""Regression tests for importing live-redacted hook payload fixtures."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
IMPORT_SCRIPT = REPO_ROOT / "scripts" / "gates" / "import_hook_fixture.py"
REPLAY_SCRIPT = REPO_ROOT / "scripts" / "gates" / "replay_hook_fixtures.py"
CORPUS_DOC = REPO_ROOT / "docs" / "hook-payload-corpus.md"

FORBIDDEN_AFTER_IMPORT = [
    re.compile(r"C:\\Users\\alice", re.IGNORECASE),
    re.compile(r"C--Users-alice", re.IGNORECASE),
    re.compile(r"/home/alice/"),
    re.compile(r"sk-live_[A-Za-z0-9_]+"),
    re.compile(r"private-user-images\.githubusercontent\.com"),
]


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_import_script_redacts_live_payload_and_replay_passes(tmp_path: Path) -> None:
    fixture_root = tmp_path / "fixtures" / "hooks"
    _write_json(
        fixture_root / "index.json",
        {
            "schema_version": 1,
            "description": "temporary hook corpus",
            "fixtures": [],
        },
    )

    raw_command = (
        "python -m pytest "
        "C:\\Users\\alice\\work\\secret_repo\\tests\\test_api.py::test_token -q"
    )
    raw_target = "C:\\Users\\alice\\work\\secret_repo\\tests\\test_api.py::test_token"
    raw_payload = {
        "hook_event_name": "PostToolUse",
        "transcript_path": "C:\\Users\\alice\\.claude\\projects\\C--Users-alice-work-secret_repo\\session.jsonl",
        "tool_name": "Bash",
        "tool_input": {"command": raw_command},
        "tool_response": {
            "exit_code": 0,
            "stdout": "1 passed with token sk-live_123456789012 from /home/alice/work/secret_repo",
            "stderr": "see https://private-user-images.githubusercontent.com/example",
        },
    }
    raw_expected = {
        "exit_code": 0,
        "evidence": {
            "test-evidence.jsonl": [
                {
                    "tool_name": "Bash",
                    "command": raw_command,
                    "primary_target": raw_target,
                    "scope": "targeted",
                    "exit_code": 0,
                }
            ]
        },
    }
    payload_path = tmp_path / "raw-posttool.json"
    expected_path = tmp_path / "expected.json"
    _write_json(payload_path, raw_payload)
    _write_json(expected_path, raw_expected)

    proc = subprocess.run(
        [
            sys.executable,
            str(IMPORT_SCRIPT),
            "--fixture-root",
            str(fixture_root),
            "--id",
            "live-posttool-pytest-redacted",
            "--event",
            "PostToolUse",
            "--payload",
            str(payload_path),
            "--expected-json",
            str(expected_path),
        ],
        text=True,
        capture_output=True,
        cwd=str(REPO_ROOT),
    )

    assert proc.returncode == 0, proc.stderr
    index_text = (fixture_root / "index.json").read_text(encoding="utf-8")
    for pattern in FORBIDDEN_AFTER_IMPORT:
        assert pattern.search(index_text) is None, pattern.pattern

    index = json.loads(index_text)
    fixture = index["fixtures"][0]
    assert fixture["source_level"] == "live-redacted"
    assert fixture["id"] == "live-posttool-pytest-redacted"
    assert fixture["payload"]["tool_input"]["command"].startswith(
        "python -m pytest <REDACTED_HOME>/work/secret_repo/"
    )
    assert fixture["redaction"]["applied"] is True
    assert "home_path" in fixture["redaction"]["rules"]
    assert "claude_project_slug" in fixture["redaction"]["rules"]

    replay = subprocess.run(
        [
            sys.executable,
            str(REPLAY_SCRIPT),
            "--fixture-root",
            str(fixture_root),
            "--json",
        ],
        text=True,
        capture_output=True,
        cwd=str(REPO_ROOT),
    )
    assert replay.returncode == 0, replay.stderr
    assert json.loads(replay.stdout)["status"] == "pass"


def test_import_script_rejects_duplicate_fixture_id(tmp_path: Path) -> None:
    fixture_root = tmp_path / "fixtures" / "hooks"
    _write_json(
        fixture_root / "index.json",
        {
            "schema_version": 1,
            "description": "temporary hook corpus",
            "fixtures": [
                {
                    "id": "duplicate",
                    "event": "Stop",
                    "source_level": "synthetic",
                    "payload": {"hook_event_name": "Stop"},
                    "expected": {"exit_code": 0, "evidence": {}},
                }
            ],
        },
    )
    payload_path = tmp_path / "payload.json"
    expected_path = tmp_path / "expected.json"
    _write_json(payload_path, {"hook_event_name": "Stop"})
    _write_json(expected_path, {"exit_code": 0, "evidence": {}})

    proc = subprocess.run(
        [
            sys.executable,
            str(IMPORT_SCRIPT),
            "--fixture-root",
            str(fixture_root),
            "--id",
            "duplicate",
            "--event",
            "Stop",
            "--payload",
            str(payload_path),
            "--expected-json",
            str(expected_path),
        ],
        text=True,
        capture_output=True,
        cwd=str(REPO_ROOT),
    )

    assert proc.returncode == 1
    assert "duplicate fixture id" in proc.stderr


def test_import_script_accepts_capture_only_event_as_non_replayable(
    tmp_path: Path,
) -> None:
    fixture_root = tmp_path / "fixtures" / "hooks"
    _write_json(
        fixture_root / "index.json",
        {
            "schema_version": 1,
            "description": "temporary hook corpus",
            "fixtures": [],
        },
    )
    payload_path = tmp_path / "sessionstart-payload.json"
    expected_path = tmp_path / "expected.json"
    _write_json(
        payload_path,
        {
            "hook_event_name": "SessionStart",
            "source": "startup",
            "cwd": "C:\\Users\\alice\\work\\secret_repo",
            "session_id": "capture-only-session",
        },
    )
    _write_json(expected_path, {"exit_code": 0, "evidence": {}})

    proc = subprocess.run(
        [
            sys.executable,
            str(IMPORT_SCRIPT),
            "--fixture-root",
            str(fixture_root),
            "--id",
            "live-sessionstart-shape",
            "--event",
            "SessionStart",
            "--payload",
            str(payload_path),
            "--expected-json",
            str(expected_path),
        ],
        text=True,
        capture_output=True,
        cwd=str(REPO_ROOT),
    )

    assert proc.returncode == 0, proc.stderr
    index = json.loads((fixture_root / "index.json").read_text(encoding="utf-8"))
    fixture = index["fixtures"][0]
    assert fixture["event"] == "SessionStart"
    assert fixture["source_level"] == "live-redacted"
    assert fixture["replayable"] is False
    assert fixture["redaction"]["review_required"] is True
    assert fixture["payload"]["cwd"] == "<REDACTED_HOME>/work/secret_repo"


def test_corpus_doc_documents_live_redaction_import_workflow() -> None:
    body = CORPUS_DOC.read_text(encoding="utf-8")
    assert "scripts/gates/import_hook_fixture.py" in body
    assert "--payload" in body
    assert "--expected-json" in body
    assert "manual review" in body.lower()
