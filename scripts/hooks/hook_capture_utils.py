"""Shared helpers for log-only hook payload capture harnesses."""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


def json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ).encode("utf-8")


def hash_text(value: str, length: int = 12) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def shape(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        keys = sorted(str(k) for k in value.keys())
        return {
            "type": "dict",
            "keys": keys,
            "values": {
                str(k): shape(v)
                for k, v in sorted(value.items(), key=lambda item: str(item[0]))
            },
        }
    if isinstance(value, list):
        return {
            "type": "list",
            "length": len(value),
            "items": [shape(item) for item in value[:5]],
            "truncated": len(value) > 5,
        }
    if isinstance(value, str):
        return {
            "type": "str",
            "length": len(value),
            "sha256_12": hash_text(value),
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


def payload_event_name(payload: dict[str, Any]) -> str:
    event_name = (
        payload.get("hook_event_name")
        or payload.get("event_name")
        or payload.get("event")
        or "unknown"
    )
    return str(event_name)


def safe_filename_token(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-._")
    return sanitized or "unknown"


def redacted_summary(
    payload: dict[str, Any],
    raw_sha256: str,
    *,
    event: str | None = None,
) -> dict[str, Any]:
    top_level_keys = sorted(str(k) for k in payload.keys())
    raw_event_name = payload_event_name(payload)
    top_level_shape = {
        str(k): shape(v)
        for k, v in sorted(payload.items(), key=lambda item: str(item[0]))
    }
    return {
        "schema_version": 1,
        "captured_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "event_name": str(event or raw_event_name),
        "raw_event_name": raw_event_name,
        "raw_sha256": raw_sha256,
        "top_level_keys": top_level_keys,
        "shape": top_level_shape,
    }


def capture_payload(
    payload: dict[str, Any],
    output_dir: Path,
    *,
    event: str | None = None,
    prefix: str = "hook-payload",
) -> int:
    """Write a raw hook payload and a redacted shape summary."""
    if not isinstance(payload, dict):
        return 0
    raw_bytes = json_bytes(payload)
    raw_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    event_token = safe_filename_token(str(event or payload_event_name(payload)))
    basename = f"{prefix}-{event_token}-{stamp}-{raw_sha256[:8]}"
    if prefix == "ups-payload":
        basename = f"{prefix}-{stamp}-{raw_sha256[:8]}"

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        raw_path = output_dir / f"{basename}.json"
        summary_path = output_dir / f"{basename}.summary.json"
        raw_path.write_bytes(raw_bytes + b"\n")
        summary = redacted_summary(payload, raw_sha256, event=event)
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError:
        return 0
    return 0


def settings_snippet(
    *,
    events: tuple[str, ...],
    script_path: Path,
    project_root: Path,
    output_dir: Path,
    include_matcher: bool,
) -> str:
    hooks: dict[str, list[dict[str, Any]]] = {}
    for event_name in events:
        command = (
            f'"{sys.executable}" "{script_path}" '
            f'--event "{event_name}" '
            f'--project-root "{project_root}" '
            f'--output-dir "{output_dir}"'
        )
        if len(events) == 1 and event_name == "UserPromptSubmit":
            command = (
                f'"{sys.executable}" "{script_path}" '
                f'--project-root "{project_root}" --output-dir "{output_dir}"'
            )
        entry: dict[str, Any] = {
            "hooks": [
                {
                    "type": "command",
                    "command": command,
                }
            ],
        }
        if include_matcher:
            entry["matcher"] = "*"
        hooks[event_name] = [entry]
    return json.dumps({"hooks": hooks}, ensure_ascii=False, indent=2)
