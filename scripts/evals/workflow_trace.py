#!/usr/bin/env python3
"""Helpers for Athanor workflow trace JSONL records."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ALLOWED_ACTORS = {"external", "gate", "hook", "leader", "worker"}
ALLOWED_STATUSES = {
    "concern",
    "escalated",
    "failure",
    "pass",
    "skipped",
    "started",
}
REQUIRED_FIELDS = {
    "actor",
    "event_type",
    "message",
    "phase",
    "schema_version",
    "seq",
    "status",
    "trace_id",
}
OPTIONAL_STRING_FIELDS = {"command", "session_id", "timestamp", "worker_id"}


def _non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _non_negative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def _optional_non_empty_string(
    record: dict[str, Any],
    normalized: dict[str, Any],
    field: str,
) -> None:
    if field not in record:
        return
    normalized[field] = _non_empty_string(record.get(field), field)


def _optional_positive_int(
    record: dict[str, Any],
    normalized: dict[str, Any],
    field: str,
) -> None:
    if field not in record:
        return
    normalized[field] = _positive_int(record.get(field), field)


def _optional_non_negative_int(
    record: dict[str, Any],
    normalized: dict[str, Any],
    field: str,
) -> None:
    if field not in record:
        return
    normalized[field] = _non_negative_int(record.get(field), field)


def validate_record(record: dict[str, Any]) -> dict[str, Any]:
    """Return a normalized copy of one trace record or raise ValueError."""
    if not isinstance(record, dict):
        raise ValueError("trace record must be an object")
    missing = sorted(REQUIRED_FIELDS - set(record))
    if missing:
        raise ValueError(f"trace record missing required fields: {missing}")

    if record.get("schema_version") != 1:
        raise ValueError("schema_version must be 1")

    actor = _non_empty_string(record.get("actor"), "actor")
    if actor not in ALLOWED_ACTORS:
        raise ValueError(f"unsupported actor: {actor}")

    status = _non_empty_string(record.get("status"), "status")
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"unsupported status: {status}")

    references = record.get("references", [])
    if not isinstance(references, list) or not all(
        isinstance(item, str) for item in references
    ):
        raise ValueError("references must be a list of strings")

    evidence = record.get("evidence", {})
    if not isinstance(evidence, dict):
        raise ValueError("evidence must be an object")

    normalized = {
        "schema_version": 1,
        "trace_id": _non_empty_string(record.get("trace_id"), "trace_id"),
        "seq": _positive_int(record.get("seq"), "seq"),
        "phase": _non_empty_string(record.get("phase"), "phase"),
        "event_type": _non_empty_string(record.get("event_type"), "event_type"),
        "actor": actor,
        "status": status,
        "message": _non_empty_string(record.get("message"), "message"),
    }
    for field in sorted(OPTIONAL_STRING_FIELDS):
        _optional_non_empty_string(record, normalized, field)
    _optional_positive_int(record, normalized, "parent_seq")
    _optional_non_negative_int(record, normalized, "duration_ms")
    if references:
        normalized["references"] = references
    if evidence:
        normalized["evidence"] = evidence
    return normalized


def load_trace(path: Path | str) -> list[dict[str, Any]]:
    """Load and validate a trace JSONL file."""
    trace_path = Path(path)
    if not trace_path.is_file():
        return []

    records: list[dict[str, Any]] = []
    for lineno, line in enumerate(trace_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"malformed JSONL line {lineno}: {exc.msg}") from exc
        try:
            records.append(validate_record(parsed))
        except ValueError as exc:
            raise ValueError(f"invalid trace record line {lineno}: {exc}") from exc
    return records


class TraceWriter:
    """Append normalized workflow trace records to JSONL."""

    def __init__(self, path: Path | str, *, trace_id: str) -> None:
        self.path = Path(path)
        self.trace_id = _non_empty_string(trace_id, "trace_id")
        existing = load_trace(self.path)
        self._next_seq = max((item["seq"] for item in existing), default=0) + 1

    def append(
        self,
        *,
        phase: str,
        event_type: str,
        actor: str,
        status: str,
        message: str,
        references: list[str] | None = None,
        evidence: dict[str, Any] | None = None,
        timestamp: str | None = None,
        command: str | None = None,
        session_id: str | None = None,
        worker_id: str | None = None,
        parent_seq: int | None = None,
        duration_ms: int | None = None,
    ) -> dict[str, Any]:
        optional_metadata: dict[str, Any] = {}
        for key, value in {
            "timestamp": timestamp,
            "command": command,
            "session_id": session_id,
            "worker_id": worker_id,
            "parent_seq": parent_seq,
            "duration_ms": duration_ms,
        }.items():
            if value is not None:
                optional_metadata[key] = value

        record = validate_record(
            {
                "schema_version": 1,
                "trace_id": self.trace_id,
                "seq": self._next_seq,
                "phase": phase,
                "event_type": event_type,
                "actor": actor,
                "status": status,
                "message": message,
                "references": [] if references is None else references,
                "evidence": {} if evidence is None else evidence,
                **optional_metadata,
            }
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        self._next_seq += 1
        return record
