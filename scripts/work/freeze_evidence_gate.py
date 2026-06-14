#!/usr/bin/env python3
"""Concern gate for PostToolUse Freeze file-change evidence.

Hybrid v1 behavior:

- missing evidence file => pass
- in-allowlist observations only => pass
- out-of-allowlist or unknown-allowlist observations => concern
- malformed JSONL => invalid input (exit 2)

This gate never returns a failure status. Freeze enforcement remains the
PreToolUse guard; this script only turns after-the-fact evidence into a work
concern that the leader can report.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _load_evidence(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValueError(f"could not read evidence file: {exc}") from exc

    records: list[dict] = []
    for lineno, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"malformed JSONL line {lineno}: {exc.msg}") from exc
        if not isinstance(parsed, dict):
            raise ValueError(f"malformed JSONL line {lineno}: record is not an object")
        parsed["_line"] = lineno
        records.append(parsed)
    return records


def _path_entries(record: dict) -> list[dict]:
    raw = record.get("paths")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _path_text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def evaluate_freeze_evidence(evidence_path: Path | str) -> dict:
    """Return a JSON-serializable freeze evidence report."""
    evidence = Path(evidence_path)
    records = _load_evidence(evidence)

    concerns: list[str] = []
    observed_paths = 0
    concern_statuses = {"out_of_allowlist", "unknown_allowlist"}

    for record in records:
        line = record.get("_line")
        for entry in _path_entries(record):
            observed_paths += 1
            status = _path_text(entry.get("allowlist_status"))
            if status not in concern_statuses:
                continue
            path = _path_text(entry.get("path")) or "<unknown path>"
            source = _path_text(entry.get("source")) or "<unknown source>"
            concerns.append(f"line {line}: {path} is {status} via {source}")

    return {
        "schema_version": 1,
        "status": "concern" if concerns else "pass",
        "concerns": concerns,
        "observed_paths": observed_paths,
        "evidence_path": str(evidence),
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize PostToolUse Freeze file-change evidence as pass/concern."
    )
    parser.add_argument("--evidence", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    try:
        report = evaluate_freeze_evidence(args.evidence)
    except ValueError as exc:
        sys.stderr.write(f"{exc}\n")
        return 2
    sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

