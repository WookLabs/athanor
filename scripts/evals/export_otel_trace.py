#!/usr/bin/env python3
"""Export Athanor workflow traces to a local OTel GenAI-style JSON envelope."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evals.workflow_trace import load_trace

EXPORTER_NAME = "athanor-otel-trace-export"
OTEL_SEMCONV = "gen_ai.development.local"
SOURCE_SCHEMA = "athanor.workflow_trace.v1"
ERROR_STATUSES = {"concern", "escalated", "failure"}
TOOL_EVENTS = {"gate.evaluated", "review.result", "verifier.result"}
AGENT_EVENTS = {"agent.dispatched", "worker.started"}


def _span_id(trace_id: str, seq: int) -> str:
    digest = hashlib.sha256(f"{trace_id}:{seq}".encode("utf-8")).digest()
    return digest[:8].hex()


def _operation_name(record: dict[str, Any]) -> str:
    event_type = record["event_type"]
    command = record.get("command", "")
    phase = record["phase"]
    if event_type in AGENT_EVENTS:
        return "invoke_agent"
    if event_type in TOOL_EVENTS:
        return "execute_tool"
    if command == "plan" or phase == "plan":
        return "plan"
    return "invoke_workflow"


def _span_status(record: dict[str, Any]) -> dict[str, str]:
    return {"code": "ERROR" if record["status"] in ERROR_STATUSES else "OK"}


def _workflow_name(record: dict[str, Any]) -> str:
    return record.get("command") or record["phase"]


def _agent_name(record: dict[str, Any]) -> str | None:
    if "worker_id" in record:
        return record["worker_id"]
    if record["actor"] in {"leader", "worker"}:
        return record["actor"]
    return None


def _base_attributes(
    record: dict[str, Any],
    *,
    include_message: bool,
    include_evidence: bool,
    include_references: bool,
) -> dict[str, Any]:
    attrs: dict[str, Any] = {
        "athanor.trace_id": record["trace_id"],
        "athanor.seq": record["seq"],
        "athanor.phase": record["phase"],
        "athanor.event_type": record["event_type"],
        "athanor.actor": record["actor"],
        "athanor.status": record["status"],
        "athanor.message.redacted": not include_message,
        "athanor.evidence.redacted": not include_evidence,
        "athanor.references.redacted": not include_references,
        "gen_ai.operation.name": _operation_name(record),
        "gen_ai.workflow.name": _workflow_name(record),
    }
    if "command" in record:
        attrs["athanor.command"] = record["command"]
    if "session_id" in record:
        attrs["athanor.session_id"] = record["session_id"]
        attrs["gen_ai.conversation.id"] = record["session_id"]
    if "worker_id" in record:
        attrs["athanor.worker_id"] = record["worker_id"]
    if "parent_seq" in record:
        attrs["athanor.parent_seq"] = record["parent_seq"]
    if "duration_ms" in record:
        attrs["athanor.duration_ms"] = record["duration_ms"]

    agent_name = _agent_name(record)
    if agent_name is not None:
        attrs["gen_ai.agent.name"] = agent_name

    references = record.get("references", [])
    evidence = record.get("evidence", {})
    attrs["athanor.references.count"] = len(references)
    attrs["athanor.evidence.keys"] = sorted(evidence)

    if include_message:
        attrs["athanor.message"] = record["message"]
    if include_evidence:
        attrs["athanor.evidence"] = evidence
    if include_references:
        attrs["athanor.references"] = references

    if record["event_type"] in TOOL_EVENTS:
        attrs["gen_ai.tool.name"] = record["event_type"]
        attrs["gen_ai.tool.type"] = "function"
        attrs["gen_ai.evaluation.name"] = record["event_type"]
        attrs["gen_ai.evaluation.score.label"] = record["status"]

    if record["status"] in ERROR_STATUSES:
        attrs["error.type"] = "_OTHER"

    return attrs


def _privacy(
    *,
    include_message: bool,
    include_evidence: bool,
    include_references: bool,
) -> dict[str, str]:
    return {
        "message_content": "included" if include_message else "redacted",
        "evidence_content": "included" if include_evidence else "redacted",
        "reference_content": "included" if include_references else "redacted",
    }


def export_trace(
    records: list[dict[str, Any]],
    *,
    include_message: bool = False,
    include_evidence: bool = False,
    include_references: bool = False,
) -> dict[str, Any]:
    if not records:
        raise ValueError("trace has no records")

    trace_id = records[0]["trace_id"]
    seq_to_span_id = {record["seq"]: _span_id(trace_id, record["seq"]) for record in records}
    spans: list[dict[str, Any]] = []
    for record in records:
        if record["trace_id"] != trace_id:
            raise ValueError("all records must share one trace_id")
        operation = _operation_name(record)
        workflow_name = _workflow_name(record)
        span: dict[str, Any] = {
            "span_id": seq_to_span_id[record["seq"]],
            "trace_id": trace_id,
            "name": f"{operation} {workflow_name}",
            "kind": "INTERNAL",
            "status": _span_status(record),
            "attributes": _base_attributes(
                record,
                include_message=include_message,
                include_evidence=include_evidence,
                include_references=include_references,
            ),
        }
        if "parent_seq" in record and record["parent_seq"] in seq_to_span_id:
            span["parent_span_id"] = seq_to_span_id[record["parent_seq"]]
        if "timestamp" in record:
            span["start_time"] = record["timestamp"]
        spans.append(span)

    return {
        "schema_version": 1,
        "source_schema": SOURCE_SCHEMA,
        "exporter": EXPORTER_NAME,
        "otel_semconv": OTEL_SEMCONV,
        "trace_id": trace_id,
        "privacy": _privacy(
            include_message=include_message,
            include_evidence=include_evidence,
            include_references=include_references,
        ),
        "spans": spans,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export an Athanor workflow JSONL trace to local OTel-style JSON."
    )
    parser.add_argument("--trace-path", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--include-message", action="store_true")
    parser.add_argument("--include-evidence", action="store_true")
    parser.add_argument("--include-references", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def _write_output(path: Path, export: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(export, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    try:
        export = export_trace(
            load_trace(args.trace_path),
            include_message=args.include_message,
            include_evidence=args.include_evidence,
            include_references=args.include_references,
        )
        if args.output is None:
            print(json.dumps(export, indent=2, sort_keys=True))
            return 0
        _write_output(args.output, export)
    except (OSError, ValueError) as exc:
        print(f"export otel trace: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "pass",
                    "output": str(args.output),
                    "trace_id": export["trace_id"],
                    "spans": len(export["spans"]),
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(
            "otel-trace "
            f"path={args.output} trace_id={export['trace_id']} spans={len(export['spans'])}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
