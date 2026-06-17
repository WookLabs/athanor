"""Regression tests for the hook payload corpus replay foundation.

The corpus starts with synthetic fixtures only. It gives athanor a stable
replay harness before any PostToolUse missing-evidence concern can become a
strict failure.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "hooks"
INDEX = FIXTURE_ROOT / "index.json"
REPLAY_SCRIPT = REPO_ROOT / "scripts" / "gates" / "replay_hook_fixtures.py"
HOOKS_JSON = REPO_ROOT / "hooks" / "hooks.json"
CORPUS_DOC = REPO_ROOT / "docs" / "hook-payload-corpus.md"
ROADMAP = REPO_ROOT / "docs" / "ROADMAP.md"

ALLOWED_EVENTS = {
    "FileChanged",
    "PermissionRequest",
    "PostToolUse",
    "PostToolUseFailure",
    "PreCompact",
    "PreToolUse",
    "SessionStart",
    "Stop",
    "SubagentStop",
    "UserPromptSubmit",
}
ALLOWED_SOURCE_LEVELS = {"synthetic", "live-redacted", "summary-only"}
FORBIDDEN_FIXTURE_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"BEGIN (?:RSA |OPENSSH |PRIVATE )?PRIVATE KEY"),
    re.compile(r"C:\\Users\\", re.IGNORECASE),
    re.compile(r"C--Users-[A-Za-z0-9_.-]+", re.IGNORECASE),
    re.compile(r"/home/[^/]+/"),
    re.compile(r"private-user-images\.githubusercontent\.com"),
]


def _load_index() -> dict:
    return json.loads(INDEX.read_text(encoding="utf-8"))


def test_hook_fixture_index_schema_and_event_coverage():
    data = _load_index()
    assert data["schema_version"] == 1
    fixtures = data["fixtures"]
    assert isinstance(fixtures, list) and fixtures

    seen: set[str] = set()
    counts: dict[str, int] = {}
    for fixture in fixtures:
        fixture_id = fixture["id"]
        assert fixture_id not in seen
        seen.add(fixture_id)
        assert fixture["event"] in ALLOWED_EVENTS
        assert fixture["source_level"] in ALLOWED_SOURCE_LEVELS
        assert isinstance(fixture["payload"], dict)
        assert isinstance(fixture["expected"], dict)
        counts[fixture["event"]] = counts.get(fixture["event"], 0) + 1

    assert counts.get("Stop", 0) >= 2
    assert counts.get("PreToolUse", 0) >= 2
    assert counts.get("PostToolUse", 0) >= 3


def test_live_redacted_fixtures_cover_core_claude_code_hook_events():
    data = _load_index()
    live_fixtures = [
        fixture
        for fixture in data["fixtures"]
        if fixture["source_level"] == "live-redacted"
    ]

    for event_name in ("Stop", "PreToolUse", "PostToolUse"):
        matches = [fixture for fixture in live_fixtures if fixture["event"] == event_name]
        assert matches, f"missing live-redacted {event_name} fixture"
        fixture = matches[-1]
        redaction = fixture["redaction"]
        assert redaction["review_required"] is True
        assert isinstance(redaction["rules"], list)
        capture = fixture.get("capture")
        assert capture is not None
        assert capture["source"] == "claude-code"
        assert capture["tool_version"] in {"2.1.177", "2.1.178"}
        assert capture["captured_with"] == "scripts/hooks/hook_payload_capture.py"


def test_live_redacted_posttool_pytest_fixture_covers_test_evidence_path():
    data = _load_index()
    fixture = next(
        (
            item
            for item in data["fixtures"]
            if item["id"] == "live-claude-2-1-178-posttool-pytest-targeted"
        ),
        None,
    )

    assert fixture is not None
    assert fixture["source_level"] == "live-redacted"
    assert fixture["event"] == "PostToolUse"
    assert fixture["capture"]["tool_version"] == "2.1.178"
    assert fixture["payload"]["tool_name"] == "Bash"
    assert fixture["payload"]["tool_input"]["command"].startswith("python -m pytest ")
    expected_records = fixture["expected"]["evidence"]["test-evidence.jsonl"]
    assert expected_records[0]["scope"] == "targeted"
    assert expected_records[0]["exit_code"] == 0
    assert expected_records[0]["exit_code_source"] == "pytest_output"


def test_replay_script_replays_all_fixtures_as_json():
    proc = subprocess.run(
        [
            sys.executable,
            str(REPLAY_SCRIPT),
            "--fixture-root",
            str(FIXTURE_ROOT),
            "--json",
        ],
        text=True,
        capture_output=True,
        cwd=str(REPO_ROOT),
    )

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["status"] == "pass"
    assert report["total"] >= 10
    assert all(item["status"] == "pass" for item in report["results"])


def test_replay_script_filters_single_event():
    proc = subprocess.run(
        [
            sys.executable,
            str(REPLAY_SCRIPT),
            "--fixture-root",
            str(FIXTURE_ROOT),
            "--event",
            "PostToolUse",
            "--json",
        ],
        text=True,
        capture_output=True,
        cwd=str(REPO_ROOT),
    )

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["status"] == "pass"
    assert report["total"] >= 3
    assert {item["event"] for item in report["results"]} == {"PostToolUse"}


def _write_temp_index(fixture_root: Path, fixtures: list[dict]) -> None:
    fixture_root.mkdir(parents=True, exist_ok=True)
    (fixture_root / "index.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "description": "temporary hook corpus",
                "fixtures": fixtures,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def test_replay_rejects_live_redacted_fixture_without_redaction_metadata(tmp_path):
    fixture_root = tmp_path / "fixtures" / "hooks"
    _write_temp_index(
        fixture_root,
        [
            {
                "id": "live-without-redaction-metadata",
                "event": "Stop",
                "source_level": "live-redacted",
                "payload": {"hook_event_name": "Stop"},
                "expected": {"exit_code": 0, "evidence": {}},
            }
        ],
    )

    proc = subprocess.run(
        [sys.executable, str(REPLAY_SCRIPT), "--fixture-root", str(fixture_root), "--json"],
        text=True,
        capture_output=True,
        cwd=str(REPO_ROOT),
    )

    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert report["status"] == "fail"
    assert "redaction metadata" in report["results"][0]["errors"][0]


def test_replay_rejects_fixture_with_forbidden_secret_tokens(tmp_path):
    fixture_root = tmp_path / "fixtures" / "hooks"
    _write_temp_index(
        fixture_root,
        [
            {
                "id": "fixture-with-secret-token",
                "event": "PostToolUse",
                "source_level": "synthetic",
                "payload": {
                    "hook_event_name": "PostToolUse",
                    "tool_name": "Bash",
                    "tool_input": {"command": "echo sk-live_123456789012"},
                },
                "expected": {"exit_code": 0, "evidence": {}},
            }
        ],
    )

    proc = subprocess.run(
        [sys.executable, str(REPLAY_SCRIPT), "--fixture-root", str(fixture_root), "--json"],
        text=True,
        capture_output=True,
        cwd=str(REPO_ROOT),
    )

    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert report["status"] == "fail"
    assert "forbidden fixture token" in report["results"][0]["errors"][0]


def test_replay_skips_safe_capture_only_non_replayable_fixture(tmp_path):
    fixture_root = tmp_path / "fixtures" / "hooks"
    _write_temp_index(
        fixture_root,
        [
            {
                "id": "live-sessionstart-shape",
                "event": "SessionStart",
                "source_level": "live-redacted",
                "replayable": False,
                "redaction": {
                    "applied": True,
                    "review_required": True,
                    "rules": ["home_path"],
                },
                "payload": {
                    "hook_event_name": "SessionStart",
                    "cwd": "<REDACTED_HOME>/work/secret_repo",
                    "session_id": "capture-only-session",
                },
                "expected": {"exit_code": 0, "evidence": {}},
            }
        ],
    )

    proc = subprocess.run(
        [sys.executable, str(REPLAY_SCRIPT), "--fixture-root", str(fixture_root), "--json"],
        text=True,
        capture_output=True,
        cwd=str(REPO_ROOT),
    )

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["status"] == "pass"
    skipped = [item for item in report["results"] if item["status"] == "skipped"]
    assert len(skipped) == 1
    assert skipped[0]["event"] == "SessionStart"
    assert "capture-only" in skipped[0]["reason"]


def test_hook_fixtures_do_not_contain_obvious_secret_or_local_path_tokens():
    raw = INDEX.read_text(encoding="utf-8")
    for pattern in FORBIDDEN_FIXTURE_PATTERNS:
        assert pattern.search(raw) is None, f"forbidden fixture token: {pattern.pattern}"


def test_userpromptsubmit_remains_absent_until_live_spike_fixture_exists():
    data = _load_index()
    events = {fixture["event"] for fixture in data["fixtures"]}
    assert "UserPromptSubmit" not in events

    hooks = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))["hooks"]
    assert "UserPromptSubmit" not in hooks


def test_corpus_doc_records_fixture_provenance_and_strict_deferral():
    body = CORPUS_DOC.read_text(encoding="utf-8")
    assert "synthetic" in body
    assert "live-redacted" in body
    assert "capture-only" in body
    assert "replayable: false" in body
    assert "skipped" in body
    assert "missing evidence" in body
    assert "concern" in body
    assert "strict" in body


def test_roadmap_records_replay_foundation_without_strict_upgrade():
    body = ROADMAP.read_text(encoding="utf-8")
    marker = "### v0.19.0 — PostToolUse evidence sniffer"
    start = body.find(marker)
    assert start != -1
    section = body[start : body.find("\n### ", start + 1)]
    assert "hook payload corpus" in section.lower()
    assert "replay" in section.lower()
    assert "strict failure on missing evidence" in section
