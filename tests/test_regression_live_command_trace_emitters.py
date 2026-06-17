"""Regression tests for P13 live command trace emission."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.evals.workflow_trace import TraceWriter, load_trace

REPO_ROOT = Path(__file__).resolve().parents[1]
EMITTER = REPO_ROOT / "scripts" / "evals" / "emit_workflow_trace.py"
CORE_SKILLS = [
    REPO_ROOT / "skills" / "plan" / "SKILL.md",
    REPO_ROOT / "skills" / "work" / "SKILL.md",
    REPO_ROOT / "skills" / "review" / "SKILL.md",
    REPO_ROOT / "skills" / "lfg" / "SKILL.md",
    REPO_ROOT / "skills" / "lfg-goal" / "SKILL.md",
]


def _run_emitter(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(EMITTER), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_trace_writer_preserves_live_command_metadata(tmp_path: Path) -> None:
    path = tmp_path / "trace.jsonl"
    writer = TraceWriter(path, trace_id="athanor-session")

    writer.append(
        phase="work",
        event_type="workflow.started",
        actor="leader",
        status="started",
        message="work execution started",
        command="work",
        session_id="2026-06-17-001",
        timestamp="2026-06-17T13:00:00Z",
        worker_id="leader",
        parent_seq=1,
        duration_ms=0,
    )

    record = load_trace(path)[0]
    assert record["command"] == "work"
    assert record["session_id"] == "2026-06-17-001"
    assert record["timestamp"] == "2026-06-17T13:00:00Z"
    assert record["worker_id"] == "leader"
    assert record["parent_seq"] == 1
    assert record["duration_ms"] == 0


def test_emit_cli_writes_explicit_trace_path(tmp_path: Path) -> None:
    trace_path = tmp_path / "explicit.jsonl"

    proc = _run_emitter(
        "--trace-path",
        str(trace_path),
        "--trace-id",
        "athanor-explicit",
        "--session-id",
        "2026-06-17-001",
        "--command",
        "work",
        "--phase",
        "work",
        "--event-type",
        "workflow.started",
        "--actor",
        "leader",
        "--status",
        "started",
        "--message",
        "work execution started",
        "--reference",
        ".athanor/sessions/2026-06-17-001/plan.md",
        "--evidence-json",
        '{"mode":"team"}',
        "--json",
    )

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["status"] == "pass"
    assert report["trace_path"] == str(trace_path)
    trace = load_trace(trace_path)
    assert trace[0]["trace_id"] == "athanor-explicit"
    assert trace[0]["command"] == "work"
    assert trace[0]["session_id"] == "2026-06-17-001"
    assert trace[0]["evidence"]["mode"] == "team"
    assert trace[0]["references"] == [".athanor/sessions/2026-06-17-001/plan.md"]
    assert "timestamp" in trace[0]


def test_emit_cli_appends_incrementing_sequence(tmp_path: Path) -> None:
    trace_path = tmp_path / "append.jsonl"
    common = [
        "--trace-path",
        str(trace_path),
        "--trace-id",
        "athanor-append",
        "--session-id",
        "2026-06-17-002",
        "--command",
        "review",
        "--phase",
        "review",
        "--actor",
        "leader",
        "--json",
    ]

    first = _run_emitter(
        *common,
        "--event-type",
        "workflow.started",
        "--status",
        "started",
        "--message",
        "review started",
    )
    second = _run_emitter(
        *common,
        "--event-type",
        "workflow.finished",
        "--status",
        "pass",
        "--message",
        "review finished",
    )

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert [item["seq"] for item in load_trace(trace_path)] == [1, 2]


def test_emit_cli_derives_default_trace_path_from_session(tmp_path: Path) -> None:
    proc = _run_emitter(
        "--root",
        str(tmp_path),
        "--session-id",
        "2026-06-17-003",
        "--command",
        "plan",
        "--phase",
        "plan",
        "--event-type",
        "workflow.started",
        "--actor",
        "leader",
        "--status",
        "started",
        "--message",
        "plan started",
        "--json",
    )

    assert proc.returncode == 0, proc.stderr
    trace_path = tmp_path / ".athanor" / "traces" / "2026-06-17-003.jsonl"
    assert trace_path.is_file()
    trace = load_trace(trace_path)
    assert trace[0]["trace_id"] == "athanor-2026-06-17-003"
    assert trace[0]["command"] == "plan"


def test_emit_cli_rejects_invalid_evidence_json(tmp_path: Path) -> None:
    proc = _run_emitter(
        "--trace-path",
        str(tmp_path / "bad.jsonl"),
        "--phase",
        "work",
        "--event-type",
        "workflow.started",
        "--actor",
        "leader",
        "--status",
        "started",
        "--message",
        "bad evidence",
        "--evidence-json",
        "{not-json}",
        "--json",
    )

    assert proc.returncode == 2
    assert "evidence JSON is invalid" in proc.stderr
    assert "Traceback" not in proc.stderr


def test_core_command_skills_expose_live_trace_emission_anchors() -> None:
    for skill in CORE_SKILLS:
        body = skill.read_text(encoding="utf-8")
        assert "P13 Live Trace Emission" in body, skill
        assert "scripts/evals/emit_workflow_trace.py" in body, skill
        assert "workflow.started" in body, skill
        assert "workflow.finished" in body, skill
