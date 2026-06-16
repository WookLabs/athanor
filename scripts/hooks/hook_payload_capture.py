#!/usr/bin/env python3
"""Log-only generic hook payload capture harness.

This script is deliberately not registered in repo `hooks/hooks.json`.
Operators can copy the printed settings snippet into user-global Claude
settings for a one-off Stop/PreToolUse/PostToolUse live payload capture.
The script never blocks and never emits stdout in hook mode.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import hook_capture_utils

CORE_EVENTS = ("Stop", "PreToolUse", "PostToolUse", "FileChanged")


def capture_payload(payload: dict[str, Any], output_dir: Path, event: str | None = None) -> int:
    """Write a raw hook payload and a redacted shape summary."""
    return hook_capture_utils.capture_payload(payload, output_dir, event=event)


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
    return hook_capture_utils.settings_snippet(
        events=CORE_EVENTS,
        script_path=Path(__file__).resolve(),
        project_root=project_root,
        output_dir=output_dir,
        include_matcher=True,
    )


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture Stop/PreToolUse/PostToolUse payloads for opt-in live fixture review."
    )
    parser.add_argument("--event", default=None)
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
        else project_root / ".athanor" / "spikes" / "hook-payloads"
    )
    if args.print_settings_snippet:
        sys.stdout.write(_settings_snippet(project_root, output_dir) + "\n")
        return 0

    payload = _read_stdin_payload()
    if payload is None:
        return 0
    return capture_payload(payload, output_dir, event=args.event)


if __name__ == "__main__":
    raise SystemExit(main())
