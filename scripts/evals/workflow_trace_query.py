#!/usr/bin/env python3
"""Read-only query helpers for Athanor workflow trace JSONL files."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evals.workflow_trace import load_trace


def _public_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "seq": record["seq"],
        "phase": record["phase"],
        "event_type": record["event_type"],
        "actor": record["actor"],
        "status": record["status"],
        "message": record["message"],
        "references": record.get("references", []),
    }


def _profile() -> dict[str, Any]:
    return {
        "id": "workflow-trace-query",
        "description": "Read-only local replay/search/stats/diff over workflow trace JSONL.",
        "mutates_files_by_default": False,
        "external_telemetry": False,
        "irreversible_actions": 0,
    }


def _base_report(trace_path: Path, mode: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": "pass",
        "mode": mode,
        "trace_path": str(trace_path),
        "profile": _profile(),
        "summary": {
            "records": len(records),
            "irreversible_actions": 0,
        },
    }


def timeline_report(trace_path: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    report = _base_report(trace_path, "timeline", records)
    report["timeline"] = [_public_record(record) for record in records]
    return report


def stats_report(trace_path: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    report = _base_report(trace_path, "stats", records)
    report["stats"] = {
        "by_status": dict(sorted(Counter(record["status"] for record in records).items())),
        "by_phase": dict(sorted(Counter(record["phase"] for record in records).items())),
        "by_actor": dict(sorted(Counter(record["actor"] for record in records).items())),
        "by_event_type": dict(sorted(Counter(record["event_type"] for record in records).items())),
    }
    return report


def _search_blob(record: dict[str, Any]) -> str:
    return json.dumps(record, ensure_ascii=False, sort_keys=True).lower()


def search_report(
    trace_path: Path,
    records: list[dict[str, Any]],
    query: str,
    limit: int,
) -> dict[str, Any]:
    terms = [term for term in query.lower().split() if term]
    matches = [
        _public_record(record)
        for record in records
        if all(term in _search_blob(record) for term in terms)
    ]
    report = _base_report(trace_path, "search", records)
    report["query"] = query
    report["limit"] = limit
    report["matches"] = matches[:limit]
    report["summary"]["matches"] = len(matches[:limit])
    return report


def _by_seq(records: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {record["seq"]: record for record in records}


def diff_report(
    trace_path: Path,
    compare_path: Path,
    base_records: list[dict[str, Any]],
    candidate_records: list[dict[str, Any]],
) -> dict[str, Any]:
    base = _by_seq(base_records)
    candidate = _by_seq(candidate_records)
    added = [
        _public_record(candidate[seq])
        for seq in sorted(set(candidate) - set(base))
    ]
    removed = [
        _public_record(base[seq])
        for seq in sorted(set(base) - set(candidate))
    ]
    changed: list[dict[str, Any]] = []
    for seq in sorted(set(base) & set(candidate)):
        before = _public_record(base[seq])
        after = _public_record(candidate[seq])
        if before != after:
            changed.append({"seq": seq, "before": before, "after": after})

    report = _base_report(trace_path, "diff", base_records)
    report["compare_path"] = str(compare_path)
    report["diff"] = {
        "added": added,
        "removed": removed,
        "changed": changed,
    }
    report["summary"].update(
        {
            "candidate_records": len(candidate_records),
            "added": len(added),
            "removed": len(removed),
            "changed": len(changed),
        }
    )
    return report


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    records = load_trace(args.trace_path)
    if args.mode == "timeline":
        return timeline_report(args.trace_path, records)
    if args.mode == "stats":
        return stats_report(args.trace_path, records)
    if args.mode == "search":
        return search_report(args.trace_path, records, args.query, args.limit)
    if args.compare_path is None:
        raise ValueError("diff mode requires --compare-path")
    return diff_report(args.trace_path, args.compare_path, records, load_trace(args.compare_path))


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query Athanor workflow trace JSONL.")
    parser.add_argument("--trace-path", type=Path, required=True)
    parser.add_argument("--compare-path", type=Path, default=None)
    parser.add_argument(
        "--mode",
        choices=("timeline", "stats", "search", "diff"),
        required=True,
    )
    parser.add_argument("--query", default="")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        report = build_report(args)
    except (OSError, ValueError) as exc:
        print(f"workflow trace query: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"{report['status']}: mode={report['mode']} records={report['summary']['records']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
