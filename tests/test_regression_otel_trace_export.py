"""Regression tests for P14 OTel-style local trace export."""
from __future__ import annotations

import importlib
import json
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from scripts.evals.workflow_trace import TraceWriter, load_trace

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPORTER = REPO_ROOT / "scripts" / "evals" / "export_otel_trace.py"
SCHEMA = REPO_ROOT / "schemas" / "otel-trace-export.schema.json"


def _exporter() -> ModuleType:
    try:
        return importlib.import_module("scripts.evals.export_otel_trace")
    except ModuleNotFoundError as exc:
        pytest.fail(f"exporter module missing: {exc}")


def _run_exporter(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(EXPORTER), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _write_demo_trace(path: Path) -> list[dict[str, Any]]:
    writer = TraceWriter(path, trace_id="athanor-demo")
    writer.append(
        phase="work",
        event_type="workflow.started",
        actor="leader",
        status="started",
        message="work execution started with sensitive context",
        command="work",
        session_id="2026-06-17-001",
        timestamp="2026-06-17T13:00:00Z",
        evidence={"mode": "team", "command": "python -m pytest secret_test.py"},
        references=[".athanor/sessions/2026-06-17-001/private-plan.md"],
    )
    writer.append(
        phase="work",
        event_type="agent.dispatched",
        actor="leader",
        status="started",
        message="dispatch executor worker",
        command="work",
        session_id="2026-06-17-001",
        worker_id="executor-1",
        parent_seq=1,
    )
    writer.append(
        phase="work",
        event_type="verifier.result",
        actor="gate",
        status="failure",
        message="pytest failed with private path",
        command="work",
        session_id="2026-06-17-001",
        parent_seq=2,
        duration_ms=123,
        evidence={"exit_code": 1, "summary": "failed"},
    )
    return load_trace(path)


def test_export_trace_redacts_sensitive_fields_by_default(tmp_path: Path) -> None:
    exporter = _exporter()
    records = _write_demo_trace(tmp_path / "trace.jsonl")

    export = exporter.export_trace(records)

    assert export["schema_version"] == 1
    assert export["source_schema"] == "athanor.workflow_trace.v1"
    assert export["exporter"] == "athanor-otel-trace-export"
    assert export["trace_id"] == "athanor-demo"
    assert export["privacy"] == {
        "message_content": "redacted",
        "evidence_content": "redacted",
        "reference_content": "redacted",
    }
    first_attrs = export["spans"][0]["attributes"]
    assert "athanor.message" not in first_attrs
    assert "athanor.evidence" not in first_attrs
    assert "athanor.references" not in first_attrs
    assert first_attrs["athanor.message.redacted"] is True
    assert first_attrs["athanor.evidence.redacted"] is True
    assert first_attrs["athanor.evidence.keys"] == ["command", "mode"]
    assert first_attrs["athanor.references.redacted"] is True
    assert first_attrs["athanor.references.count"] == 1
    assert first_attrs["gen_ai.workflow.name"] == "work"
    assert first_attrs["gen_ai.conversation.id"] == "2026-06-17-001"


def test_export_trace_maps_operations_parent_ids_and_status(tmp_path: Path) -> None:
    exporter = _exporter()
    records = _write_demo_trace(tmp_path / "trace.jsonl")
    plan_writer = TraceWriter(tmp_path / "plan.jsonl", trace_id="athanor-plan")
    plan_writer.append(
        phase="plan",
        event_type="workflow.started",
        actor="leader",
        status="started",
        message="plan started",
        command="plan",
    )

    export = exporter.export_trace(records)
    spans = export["spans"]

    assert [span["attributes"]["gen_ai.operation.name"] for span in spans] == [
        "invoke_workflow",
        "invoke_agent",
        "execute_tool",
    ]
    assert re.fullmatch(r"[0-9a-f]{16}", spans[0]["span_id"])
    assert spans[1]["parent_span_id"] == spans[0]["span_id"]
    assert spans[2]["parent_span_id"] == spans[1]["span_id"]
    assert spans[2]["status"] == {"code": "ERROR"}
    assert spans[2]["attributes"]["error.type"] == "_OTHER"
    assert spans[2]["attributes"]["gen_ai.tool.name"] == "verifier.result"
    assert spans[2]["attributes"]["gen_ai.tool.type"] == "function"
    assert spans[2]["attributes"]["gen_ai.evaluation.name"] == "verifier.result"
    assert spans[2]["attributes"]["gen_ai.evaluation.score.label"] == "failure"
    assert spans[2]["attributes"]["athanor.duration_ms"] == 123

    plan_export = exporter.export_trace(load_trace(tmp_path / "plan.jsonl"))
    assert (
        plan_export["spans"][0]["attributes"]["gen_ai.operation.name"]
        == "plan"
    )
    assert plan_export["spans"][0]["name"] == "plan plan"


def test_export_trace_includes_sensitive_fields_only_when_opted_in(tmp_path: Path) -> None:
    exporter = _exporter()
    records = _write_demo_trace(tmp_path / "trace.jsonl")

    export = exporter.export_trace(
        records,
        include_message=True,
        include_evidence=True,
        include_references=True,
    )

    assert export["privacy"] == {
        "message_content": "included",
        "evidence_content": "included",
        "reference_content": "included",
    }
    attrs = export["spans"][0]["attributes"]
    assert attrs["athanor.message"] == "work execution started with sensitive context"
    assert attrs["athanor.evidence"]["mode"] == "team"
    assert attrs["athanor.references"] == [
        ".athanor/sessions/2026-06-17-001/private-plan.md"
    ]
    assert attrs["athanor.message.redacted"] is False
    assert attrs["athanor.evidence.redacted"] is False
    assert attrs["athanor.references.redacted"] is False


def test_export_cli_writes_output_and_json_status(tmp_path: Path) -> None:
    trace_path = tmp_path / "trace.jsonl"
    output_path = tmp_path / "trace.otel.json"
    _write_demo_trace(trace_path)

    proc = _run_exporter(
        "--trace-path",
        str(trace_path),
        "--output",
        str(output_path),
        "--json",
    )

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report == {
        "schema_version": 1,
        "status": "pass",
        "output": str(output_path),
        "trace_id": "athanor-demo",
        "spans": 3,
    }
    export = json.loads(output_path.read_text(encoding="utf-8"))
    assert export["trace_id"] == "athanor-demo"
    assert len(export["spans"]) == 3


def test_export_cli_prints_export_to_stdout_without_output(tmp_path: Path) -> None:
    trace_path = tmp_path / "trace.jsonl"
    _write_demo_trace(trace_path)

    proc = _run_exporter("--trace-path", str(trace_path), "--include-message")

    assert proc.returncode == 0, proc.stderr
    export = json.loads(proc.stdout)
    assert export["spans"][0]["attributes"]["athanor.message"].startswith("work")
    assert export["privacy"]["message_content"] == "included"
    assert export["privacy"]["evidence_content"] == "redacted"


def test_export_cli_rejects_invalid_trace_without_traceback(tmp_path: Path) -> None:
    trace_path = tmp_path / "bad.jsonl"
    trace_path.write_text("not-json\n", encoding="utf-8")

    proc = _run_exporter("--trace-path", str(trace_path), "--json")

    assert proc.returncode == 2
    assert "export otel trace:" in proc.stderr
    assert "Traceback" not in proc.stderr


def test_export_schema_documents_local_envelope() -> None:
    assert SCHEMA.is_file()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["title"] == "Athanor OTel-style trace export"
    assert schema["additionalProperties"] is False
    assert schema["required"] == [
        "schema_version",
        "source_schema",
        "exporter",
        "otel_semconv",
        "trace_id",
        "privacy",
        "spans",
    ]
    span = schema["properties"]["spans"]["items"]
    assert span["additionalProperties"] is False
    assert "span_id" in span["required"]
    assert "attributes" in span["required"]
