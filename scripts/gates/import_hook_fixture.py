#!/usr/bin/env python3
"""Import a reviewed live hook payload into the replay fixture corpus."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "hooks" / "catalog.json"
REPLAYABLE_EVENTS = {"Stop", "PreToolUse", "PostToolUse"}

_WINDOWS_HOME = re.compile(r"\b[A-Za-z]:\\Users\\[^\\/\s\"']+((?:\\[^\\\s\"']+)*)")
_POSIX_HOME = re.compile(r"/home/[^/\s\"']+((?:/[^/\s\"']+)*)")
_CLAUDE_PROJECT_WINDOWS_HOME_SLUG = re.compile(r"C--Users-[A-Za-z0-9_.-]+")
_SECRET_TOKEN = re.compile(r"sk-[A-Za-z0-9_-]{8,}|sk-live_[A-Za-z0-9_]+")
_PRIVATE_IMAGE_URL = re.compile(
    r"https?://private-user-images\.githubusercontent\.com/[^\s\"']+"
)
_PRIVATE_KEY_BLOCK = re.compile(
    r"-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----",
    re.DOTALL,
)


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"could not load JSON {path}: {exc}") from exc


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _replace_home(match: re.Match[str]) -> str:
    suffix = match.group(1).replace("\\", "/")
    return f"<REDACTED_HOME>{suffix}"


def _redact_string(value: str, rules: set[str]) -> str:
    redacted = _WINDOWS_HOME.sub(_replace_home, value)
    if redacted != value:
        rules.add("home_path")
    value = redacted

    redacted = _POSIX_HOME.sub(_replace_home, value)
    if redacted != value:
        rules.add("home_path")
    value = redacted

    redacted = _CLAUDE_PROJECT_WINDOWS_HOME_SLUG.sub("<REDACTED_HOME_SLUG>", value)
    if redacted != value:
        rules.add("claude_project_slug")
    value = redacted

    redacted = _SECRET_TOKEN.sub("<REDACTED_SECRET>", value)
    if redacted != value:
        rules.add("secret_token")
    value = redacted

    redacted = _PRIVATE_IMAGE_URL.sub("<REDACTED_PRIVATE_URL>", value)
    if redacted != value:
        rules.add("private_url")
    value = redacted

    redacted = _PRIVATE_KEY_BLOCK.sub("<REDACTED_PRIVATE_KEY>", value)
    if redacted != value:
        rules.add("private_key")
    return redacted


def redact_payload(value: Any, rules: set[str] | None = None) -> tuple[Any, list[str]]:
    """Return a recursively redacted copy plus applied rule names."""
    applied: set[str] = set() if rules is None else rules
    if isinstance(value, str):
        return _redact_string(value, applied), sorted(applied)
    if isinstance(value, list):
        return [redact_payload(item, applied)[0] for item in value], sorted(applied)
    if isinstance(value, dict):
        return {
            key: redact_payload(item, applied)[0]
            for key, item in value.items()
        }, sorted(applied)
    return value, sorted(applied)


def _load_index(fixture_root: Path) -> dict:
    index_path = fixture_root / "index.json"
    parsed = _load_json(index_path)
    if not isinstance(parsed, dict):
        raise ValueError("fixture index root must be an object")
    fixtures = parsed.get("fixtures")
    if not isinstance(fixtures, list):
        raise ValueError("fixture index must contain fixtures[]")
    return parsed


def _load_catalog(path: Path = CATALOG_PATH) -> dict:
    parsed = _load_json(path)
    if not isinstance(parsed, dict):
        raise ValueError("hook catalog root must be an object")
    hooks = parsed.get("hooks")
    if not isinstance(hooks, list):
        raise ValueError("hook catalog must contain hooks[]")
    return parsed


def _capture_only_events(catalog_path: Path = CATALOG_PATH) -> set[str]:
    catalog = _load_catalog(catalog_path)
    events: set[str] = set()
    for entry in catalog["hooks"]:
        if not isinstance(entry, dict):
            continue
        event = entry.get("event")
        runtime_default = entry.get("runtime_default")
        if isinstance(event, str) and runtime_default == "capture-only":
            events.add(event)
    return events


def _allowed_events() -> set[str]:
    return REPLAYABLE_EVENTS | _capture_only_events()


def import_fixture(
    *,
    fixture_root: Path,
    fixture_id: str,
    event: str,
    payload_path: Path,
    expected_path: Path,
) -> dict:
    allowed_events = _allowed_events()
    if event not in allowed_events:
        raise ValueError(f"unsupported event {event!r}")
    replayable = event in REPLAYABLE_EVENTS
    index = _load_index(fixture_root)
    fixtures = index["fixtures"]
    if any(item.get("id") == fixture_id for item in fixtures if isinstance(item, dict)):
        raise ValueError(f"duplicate fixture id: {fixture_id}")

    raw_payload = _load_json(payload_path)
    raw_expected = _load_json(expected_path)
    if not isinstance(raw_payload, dict):
        raise ValueError("payload JSON must be an object")
    if not isinstance(raw_expected, dict):
        raise ValueError("expected JSON must be an object")

    rules: set[str] = set()
    payload, _ = redact_payload(raw_payload, rules)
    expected, applied_rules = redact_payload(raw_expected, rules)
    fixture = {
        "id": fixture_id,
        "event": event,
        "replayable": replayable,
        "source_level": "live-redacted",
        "redaction": {
            "applied": bool(applied_rules),
            "rules": applied_rules,
            "review_required": True,
        },
        "payload": payload,
        "expected": expected,
    }
    fixtures.append(fixture)
    _write_json(fixture_root / "index.json", index)
    return fixture


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import a redacted live hook payload fixture."
    )
    parser.add_argument(
        "--fixture-root",
        type=Path,
        default=REPO_ROOT / "tests" / "fixtures" / "hooks",
    )
    parser.add_argument("--id", required=True, help="Unique fixture id.")
    parser.add_argument("--event", required=True, choices=sorted(_allowed_events()))
    parser.add_argument("--payload", required=True, type=Path)
    parser.add_argument("--expected-json", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    try:
        fixture = import_fixture(
            fixture_root=args.fixture_root,
            fixture_id=args.id,
            event=args.event,
            payload_path=args.payload,
            expected_path=args.expected_json,
        )
    except ValueError as exc:
        print(f"hook fixture import: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"status": "ok", "id": fixture["id"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
