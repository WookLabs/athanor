#!/usr/bin/env python3
"""
scripts/gates/manifest_checks.py — shared manifest/hooks validation for Athanor.

Exported functions:
  duplicate_hooks_path_check(manifest_path: Path, repo_root: Path) -> tuple[bool, str]
    Checks if plugin.json declares a `hooks` field that canonicalizes to the same
    path as the auto-discovered `hooks/hooks.json`. Uses Path(...).resolve() as
    the canonical form (stronger than os.path.abspath: symlink-resolved,
    case-normalized on case-insensitive filesystems like macOS/Windows).

  hook_uniqueness_check(hooks_json_path: Path) -> tuple[bool, list[str]]
    Checks if any top-level event key in hooks.json has more than one handler
    entry. Returns (ok, violation_lines). Wraps JSONDecodeError cleanly.

    Scope lock (D1): duplicate = len(hooks[event]) > 1 for any event.
    Inner-hooks[] dedup is OUT OF SCOPE (different concern).
    Empty-event semantics are OUT OF SCOPE (Check #8 territory, not #9).

CLI dispatcher:
  python -m scripts.gates.manifest_checks uniqueness <hooks_json_path>
  python -m scripts.gates.manifest_checks duplicate-hooks <manifest_path> <repo_root>

  Exit 0 = pass, 1 = fail (violation line on stdout), 2 = argparse error.

Stdlib only. UTF-8 everywhere (Windows cp949 guard).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def duplicate_hooks_path_check(manifest_path: Path, repo_root: Path) -> tuple[bool, str]:
    """
    Check plugin.json's `hooks` field (if present) does not canonicalize to
    the same path as repo_root / 'hooks/hooks.json' (which Claude Code auto-
    discovers). Uses Path.resolve() for canonical-form comparison.
    """
    if not manifest_path.is_file():
        return False, f"manifest not found: {manifest_path}"
    try:
        with manifest_path.open(encoding="utf-8") as f:
            manifest = json.load(f)
    except json.JSONDecodeError as exc:
        return False, f"manifest is not valid JSON: {exc}"
    except OSError as exc:
        return False, f"manifest read error: {exc}"

    explicit = manifest.get("hooks")
    if explicit is None:
        return True, "no explicit hooks field in plugin.json"

    auto_path = repo_root / "hooks" / "hooks.json"
    if not auto_path.is_file():
        return True, "plugin.json declares hooks but hooks/hooks.json not auto-discovered"

    try:
        explicit_resolved = (repo_root / explicit).resolve()
    except OSError as exc:
        return False, f"plugin.json hooks path not resolvable: {explicit} ({exc})"
    auto_resolved = auto_path.resolve()

    if explicit_resolved == auto_resolved:
        return False, (
            "plugin.json declares hooks -> hooks/hooks.json which is "
            "auto-discovered; remove the field"
        )
    return True, f"plugin.json hooks -> {explicit} differs from auto-discovered hooks/hooks.json"


def hook_uniqueness_check(hooks_json_path: Path) -> tuple[bool, list[str]]:
    """
    Check hooks.json outer structure: each top-level event key in "hooks"
    must have at most one handler entry (len(hooks[event]) <= 1).

    Scope lock (D1): duplicate = outer-array length > 1. Inner hooks[] dedup
    is OUT OF SCOPE. Empty or missing event is OUT OF SCOPE (different
    concern — see Check #8).

    Returns (True, []) on pass, (False, [violation_lines]) on fail.
    Malformed JSON returns (False, [clean violation line]) — never raises.
    """
    if not hooks_json_path.is_file():
        return False, [f"hook-uniqueness violation: {hooks_json_path} not found"]
    try:
        with hooks_json_path.open(encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        return False, [f"hook-uniqueness violation: {hooks_json_path} is not valid JSON: {exc}"]
    except OSError as exc:
        return False, [f"hook-uniqueness violation: {hooks_json_path} read error: {exc}"]

    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return True, []  # no "hooks" dict or empty — out of scope here

    violations: list[str] = []
    for event, entries in hooks.items():
        if isinstance(entries, list) and len(entries) > 1:
            violations.append(
                f"hook-uniqueness violation: {hooks_json_path} registers "
                f"{event} event {len(entries)} times (expected 1)"
            )
    return (len(violations) == 0, violations)


def _cmd_uniqueness(args: argparse.Namespace) -> int:
    path = Path(args.hooks_json_path)
    ok, violations = hook_uniqueness_check(path)
    if ok:
        return 0
    for line in violations:
        print(line)
    return 1


def _cmd_duplicate_hooks(args: argparse.Namespace) -> int:
    manifest = Path(args.manifest_path)
    root = Path(args.repo_root)
    ok, msg = duplicate_hooks_path_check(manifest, root)
    if ok:
        return 0
    print(msg)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.gates.manifest_checks",
        description="Shared manifest/hooks validation for Athanor",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    u = sub.add_parser("uniqueness", help="Check hooks.json event-key uniqueness")
    u.add_argument("hooks_json_path")
    u.set_defaults(func=_cmd_uniqueness)

    d = sub.add_parser("duplicate-hooks", help="Check plugin.json hooks path collision")
    d.add_argument("manifest_path")
    d.add_argument("repo_root")
    d.set_defaults(func=_cmd_duplicate_hooks)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
