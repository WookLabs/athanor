#!/usr/bin/env python3
"""Log-only UserPromptSubmit payload spike harness.

This script is deliberately not registered in repo `hooks/hooks.json`.
Operators can copy the printed settings snippet into user-global Claude
settings for a one-off live payload capture. The script never blocks and
never emits prompt-injection stdout in hook mode.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ).encode("utf-8")


def _hash_text(value: str, length: int = 12) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def _shape(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        keys = sorted(str(k) for k in value.keys())
        return {
            "type": "dict",
            "keys": keys,
            "values": {str(k): _shape(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))},
        }
    if isinstance(value, list):
        return {
            "type": "list",
            "length": len(value),
            "items": [_shape(item) for item in value[:5]],
            "truncated": len(value) > 5,
        }
    if isinstance(value, str):
        return {
            "type": "str",
            "length": len(value),
            "sha256_12": _hash_text(value),
        }
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "bool"}
    if isinstance(value, int):
        return {"type": "int"}
    if isinstance(value, float):
        return {"type": "float"}
    return {"type": type(value).__name__}


def _redacted_summary(payload: dict[str, Any], raw_sha256: str) -> dict[str, Any]:
    top_level_keys = sorted(str(k) for k in payload.keys())
    event_name = (
        payload.get("hook_event_name")
        or payload.get("event_name")
        or payload.get("event")
        or "unknown"
    )
    top_level_shape = {
        str(k): _shape(v)
        for k, v in sorted(payload.items(), key=lambda item: str(item[0]))
    }
    return {
        "schema_version": 1,
        "captured_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "event_name": str(event_name),
        "raw_sha256": raw_sha256,
        "top_level_keys": top_level_keys,
        "shape": top_level_shape,
    }


def capture_payload(payload: dict[str, Any], output_dir: Path) -> int:
    """Write raw payload and redacted shape summary for a live UPS spike."""
    if not isinstance(payload, dict):
        return 0
    raw_bytes = _json_bytes(payload)
    raw_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    basename = f"ups-payload-{stamp}-{raw_sha256[:8]}"

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        raw_path = output_dir / f"{basename}.json"
        summary_path = output_dir / f"{basename}.summary.json"
        raw_path.write_bytes(raw_bytes + b"\n")
        summary = _redacted_summary(payload, raw_sha256)
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError:
        return 0
    return 0


def _resolve_project_root(explicit: Path | None = None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    for start in (Path.cwd(), Path(__file__).resolve().parent):
        cur = start.resolve()
        for _ in range(8):
            if (cur / ".git").exists() or (cur / "athanor.json").is_file():
                return cur
            if cur.parent == cur:
                break
            cur = cur.parent
    return Path.cwd().resolve()


def _read_stdin_payload() -> dict[str, Any] | None:
    try:
        raw = sys.stdin.read()
    except (OSError, ValueError):
        return None
    if not raw.strip():
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _settings_snippet(project_root: Path, output_dir: Path) -> str:
    script_path = Path(__file__).resolve()
    command = (
        f'"{sys.executable}" "{script_path}" '
        f'--project-root "{project_root}" --output-dir "{output_dir}"'
    )
    snippet = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": command,
                        }
                    ]
                }
            ]
        }
    }
    return json.dumps(snippet, ensure_ascii=False, indent=2)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture UserPromptSubmit payloads for an opt-in live spike."
    )
    parser.add_argument("--project-root", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--print-settings-snippet", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    project_root = _resolve_project_root(args.project_root)
    output_dir = (
        args.output_dir.resolve()
        if args.output_dir is not None
        else project_root / ".athanor" / "spikes"
    )
    if args.print_settings_snippet:
        sys.stdout.write(_settings_snippet(project_root, output_dir) + "\n")
        return 0

    payload = _read_stdin_payload()
    if payload is None:
        return 0
    return capture_payload(payload, output_dir)


if __name__ == "__main__":
    raise SystemExit(main())
