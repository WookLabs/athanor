"""Regression tests for normalized workflow trace records."""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.evals.workflow_trace import TraceWriter, load_trace


def test_trace_writer_appends_schema_v1_records(tmp_path: Path) -> None:
    path = tmp_path / "trace.jsonl"
    writer = TraceWriter(path, trace_id="trace-demo")

    first = writer.append(
        phase="work",
        event_type="workflow.started",
        actor="leader",
        status="started",
        message="work started",
    )
    second = writer.append(
        phase="work",
        event_type="verifier.result",
        actor="gate",
        status="pass",
        message="pytest evidence matched",
        references=[
            ".athanor/sessions/2026-06-17-001/.hook-state/test-evidence.jsonl"
        ],
        evidence={"command": "python -m pytest tests/test_demo.py -q"},
    )

    records = load_trace(path)
    assert first["seq"] == 1
    assert second["seq"] == 2
    assert records[0]["schema_version"] == 1
    assert records[1]["event_type"] == "verifier.result"
    assert records[1]["references"][0].endswith("test-evidence.jsonl")


def test_trace_writer_rejects_unknown_status(tmp_path: Path) -> None:
    writer = TraceWriter(tmp_path / "trace.jsonl", trace_id="trace-demo")
    with pytest.raises(ValueError, match="unsupported status"):
        writer.append(
            phase="work",
            event_type="workflow.finished",
            actor="leader",
            status="done",
            message="bad status",
        )


def test_load_trace_rejects_malformed_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "trace.jsonl"
    path.write_text(
        (
            '{"actor":"leader","event_type":"workflow.started","message":"start",'
            '"phase":"work","schema_version":1,"seq":1,"status":"started",'
            '"trace_id":"trace-demo"}\n'
            "not-json\n"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="malformed JSONL line 2"):
        load_trace(path)
