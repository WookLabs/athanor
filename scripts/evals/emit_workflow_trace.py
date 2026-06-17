#!/usr/bin/env python3
"""Emit one Athanor workflow trace record from live command skills."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evals.workflow_trace import TraceWriter


def _iso_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _default_trace_id(session_id: str | None) -> str:
    return f"athanor-{session_id}" if session_id else "athanor-live"


def _default_trace_path(root: Path, session_id: str | None, trace_id: str) -> Path:
    name = session_id or trace_id
    return root / ".athanor" / "traces" / f"{name}.jsonl"


def _load_evidence(raw: str | None) -> dict[str, Any]:
    if raw is None:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"evidence JSON is invalid: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("evidence JSON must be an object")
    return parsed


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Emit one Athanor workflow trace record.")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--trace-path", type=Path)
    parser.add_argument("--trace-id")
    parser.add_argument("--session-id")
    parser.add_argument("--command")
    parser.add_argument("--worker-id")
    parser.add_argument("--parent-seq", type=int)
    parser.add_argument("--duration-ms", type=int)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--event-type", required=True)
    parser.add_argument("--actor", required=True)
    parser.add_argument("--status", required=True)
    parser.add_argument("--message", required=True)
    parser.add_argument("--reference", action="append", default=[])
    parser.add_argument("--evidence-json")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def build_record_args(args: argparse.Namespace) -> tuple[Path, str, dict[str, Any]]:
    trace_id = args.trace_id or _default_trace_id(args.session_id)
    trace_path = args.trace_path or _default_trace_path(args.root, args.session_id, trace_id)
    evidence = _load_evidence(args.evidence_json)
    event: dict[str, Any] = {
        "phase": args.phase,
        "event_type": args.event_type,
        "actor": args.actor,
        "status": args.status,
        "message": args.message,
        "references": args.reference,
        "evidence": evidence,
    }
    metadata = {
        "timestamp": _iso_now(),
        "command": args.command,
        "session_id": args.session_id,
        "worker_id": args.worker_id,
        "parent_seq": args.parent_seq,
        "duration_ms": args.duration_ms,
    }
    event["metadata"] = {
        key: value for key, value in metadata.items() if value is not None
    }
    return trace_path, trace_id, event


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    try:
        trace_path, trace_id, event = build_record_args(args)
        metadata = event.pop("metadata")
        writer = TraceWriter(trace_path, trace_id=trace_id)
        record = writer.append(**event, **metadata)
    except ValueError as exc:
        print(f"emit workflow trace: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "pass",
                    "trace_path": str(trace_path),
                    "record": record,
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(
            "workflow-trace "
            f"path={trace_path} seq={record['seq']} event={record['event_type']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
