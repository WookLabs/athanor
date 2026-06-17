#!/usr/bin/env python3
"""Hook installer planner for Athanor.

The default mode remains read-only. P8 adds trusted apply behavior while keeping
dry-run output as the shared report shape for later remove support.
"""

from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.gates.hook_installer import (
    HookInstallerTrustError,
    build_hook_fingerprint,
    load_trust_state,
    trust_status,
)

INSTALLABLE_EVIDENCE = {"live-redacted", "replay-gated"}
SUMMARY_KEYS = ("already-present", "would-add", "applied", "blocked", "conflict")
VALID_MODES = {"apply", "dry-run", "remove"}


def _read_json(path: Path, label: str, *, missing_ok: bool = False) -> tuple[dict[str, Any] | None, str | None]:
    if missing_ok and not path.exists():
        return {}, None
    if not path.is_file():
        return None, f"{label} not found: {path}"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"{label} is not valid JSON: {exc}"
    except OSError as exc:
        return None, f"{label} read error: {exc}"
    if not isinstance(data, dict):
        return None, f"{label} must be a JSON object"
    return data, None


def _hook_entry(event: str, matcher: str, command: str) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "hooks": [
            {
                "type": "command",
                "command": command,
            }
        ]
    }
    if matcher:
        entry["matcher"] = matcher
    return entry


def _iter_manifest_hooks(data: dict[str, Any]) -> list[tuple[str, str, str]]:
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return []

    out: list[tuple[str, str, str]] = []
    for event, matcher_entries in hooks.items():
        if not isinstance(event, str) or not isinstance(matcher_entries, list):
            continue
        for matcher_entry in matcher_entries:
            if not isinstance(matcher_entry, dict):
                continue
            matcher = matcher_entry.get("matcher", "")
            if not isinstance(matcher, str):
                matcher = ""
            handlers = matcher_entry.get("hooks", [])
            if not isinstance(handlers, list):
                continue
            for handler in handlers:
                if not isinstance(handler, dict):
                    continue
                command = handler.get("command")
                if isinstance(command, str):
                    out.append((event, matcher, command))
    return out


def _settings_event_count(settings: dict[str, Any], event: str) -> int:
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return 0
    entries = hooks.get(event)
    if not isinstance(entries, list):
        return 0
    return len(entries)


def _summarize(actions: list[dict[str, Any]]) -> dict[str, int]:
    summary = {key: 0 for key in SUMMARY_KEYS}
    for action in actions:
        status = action.get("status")
        if status in summary:
            summary[str(status)] += 1
    return summary


def _catalog_entries(catalog: dict[str, Any], includes: list[str]) -> tuple[list[dict[str, Any]] | None, str | None]:
    raw_entries = catalog.get("hooks")
    if not isinstance(raw_entries, list):
        return None, "catalog hooks must be an array"

    entries = [entry for entry in raw_entries if isinstance(entry, dict)]
    by_id = {entry.get("id"): entry for entry in entries if isinstance(entry.get("id"), str)}
    missing = [hook_id for hook_id in includes if hook_id not in by_id]
    if missing:
        return None, f"unknown catalog hook id(s): {', '.join(missing)}"

    selected: list[dict[str, Any]] = [
        entry for entry in entries if entry.get("runtime_default") == "enabled"
    ]
    selected_ids = {entry.get("id") for entry in selected}
    for hook_id in includes:
        if hook_id not in selected_ids:
            selected.append(by_id[hook_id])
            selected_ids.add(hook_id)
    return selected, None


def _blocked_reason(entry: dict[str, Any]) -> str | None:
    runtime_default = str(entry.get("runtime_default", ""))
    evidence_level = str(entry.get("evidence_level", ""))
    command = entry.get("command")

    reasons: list[str] = []
    if runtime_default == "capture-only":
        reasons.append(
            "capture-only entries require live-redacted or replay-gated evidence before settings install"
        )
    elif runtime_default != "enabled":
        reasons.append(f"{runtime_default or 'non-enabled'} catalog entry is not installable")

    if evidence_level not in INSTALLABLE_EVIDENCE:
        reasons.append("requires live-redacted or replay-gated evidence")

    if not isinstance(command, str) or not command:
        reasons.append("command is missing")

    if reasons:
        return "; ".join(dict.fromkeys(reasons))
    return None


def _plan_action(
    entry: dict[str, Any],
    runtime_hooks: set[tuple[str, str, str]],
    settings_hooks: set[tuple[str, str, str]],
    settings: dict[str, Any],
    repo_root: Path,
    trust_state: dict[str, Any],
) -> dict[str, Any]:
    hook_id = str(entry.get("id", ""))
    event = str(entry.get("event", ""))
    matcher = str(entry.get("matcher", ""))
    command = entry.get("command")
    command_text = command if isinstance(command, str) else ""

    action: dict[str, Any] = {
        "id": hook_id,
        "event": event,
        "matcher": matcher,
        "command": command_text,
        "runtime_default": str(entry.get("runtime_default", "")),
        "policy_mode": str(entry.get("policy_mode", "")),
        "evidence_level": str(entry.get("evidence_level", "")),
    }
    fingerprint = build_hook_fingerprint(entry, repo_root)
    trust = trust_status(entry, fingerprint, trust_state)
    action.update(
        {
            "command_hash": trust["command_hash"],
            "source_hashes": trust["source_hashes"],
            "missing_sources": trust["missing_sources"],
            "trust_status": trust["trust_status"],
            "trust_reason": trust["reason"],
        }
    )

    blocked = _blocked_reason(entry)
    if blocked is not None:
        action["status"] = "blocked"
        action["reason"] = blocked
        return action

    key = (event, matcher, command_text)
    if key in runtime_hooks:
        action["status"] = "already-present"
        action["reason"] = "catalog entry already present in hooks/hooks.json"
        return action

    if key in settings_hooks:
        action["status"] = "already-present"
        action["reason"] = "catalog entry already present in settings"
        return action

    existing_count = _settings_event_count(settings, event)
    if existing_count:
        action["status"] = "conflict"
        action["reason"] = "settings already has existing hook entries for this event; refusing to clobber"
        action["existing_count"] = existing_count
        return action

    action["status"] = "would-add"
    action["reason"] = "settings has no matching or conflicting entry"
    action["proposed_entry"] = _hook_entry(event, matcher, command_text)
    return action


def _write_settings_atomic(settings_path: Path, settings: dict[str, Any]) -> list[dict[str, str]]:
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    writes: list[dict[str, str]] = []
    if settings_path.is_file():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup_path = settings_path.with_name(f"{settings_path.name}.bak-{stamp}")
        backup_path.write_text(settings_path.read_text(encoding="utf-8"), encoding="utf-8")
        writes.append({"kind": "backup", "path": str(backup_path.resolve())})

    temp_path = settings_path.with_name(f".{settings_path.name}.tmp")
    temp_path.write_text(
        json.dumps(settings, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(settings_path)
    writes.append({"kind": "settings", "path": str(settings_path.resolve())})
    return writes


def _apply_actions(
    actions: list[dict[str, Any]],
    settings: dict[str, Any],
    settings_path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    next_settings = copy.deepcopy(settings)
    changed = False

    for action in actions:
        if action.get("status") != "would-add":
            continue
        if action.get("trust_status") != "trusted":
            action["status"] = "blocked"
            action["reason"] = f"trust state is not trusted: {action.get('trust_reason', '')}"
            action.pop("proposed_entry", None)
            continue

        hooks = next_settings.setdefault("hooks", {})
        if not isinstance(hooks, dict):
            action["status"] = "blocked"
            action["reason"] = "settings hooks must be an object"
            action.pop("proposed_entry", None)
            continue
        event = str(action.get("event", ""))
        event_entries = hooks.setdefault(event, [])
        if not isinstance(event_entries, list):
            action["status"] = "blocked"
            action["reason"] = "settings event hooks must be an array"
            action.pop("proposed_entry", None)
            continue

        event_entries.append(action["proposed_entry"])
        action["status"] = "applied"
        action["reason"] = "trusted hook entry written to settings"
        changed = True

    if not changed:
        return actions, []
    return actions, _write_settings_atomic(settings_path, next_settings)


def build_report(
    *,
    repo_root: Path,
    catalog_path: Path,
    hooks_path: Path,
    settings_path: Path,
    trust_state_path: Path | None = None,
    includes: list[str],
    mode: str = "dry-run",
) -> tuple[dict[str, Any], int]:
    if mode not in VALID_MODES:
        mode = "dry-run"
    if trust_state_path is None:
        trust_state_path = repo_root / ".athanor" / "hook-installer-trust.json"

    catalog, error = _read_json(catalog_path, "catalog")
    if error:
        return _error_report(
            error, mode, repo_root, catalog_path, hooks_path, settings_path, trust_state_path
        ), 1
    assert catalog is not None

    hooks, error = _read_json(hooks_path, "hooks")
    if error:
        return _error_report(
            error, mode, repo_root, catalog_path, hooks_path, settings_path, trust_state_path
        ), 1
    assert hooks is not None

    settings, error = _read_json(settings_path, "settings", missing_ok=True)
    if error:
        return _error_report(
            error, mode, repo_root, catalog_path, hooks_path, settings_path, trust_state_path
        ), 1
    assert settings is not None

    try:
        trust_state = load_trust_state(trust_state_path)
    except HookInstallerTrustError as exc:
        return _error_report(
            str(exc), mode, repo_root, catalog_path, hooks_path, settings_path, trust_state_path
        ), 1

    entries, error = _catalog_entries(catalog, includes)
    if error:
        return _error_report(
            error, mode, repo_root, catalog_path, hooks_path, settings_path, trust_state_path
        ), 1
    assert entries is not None

    runtime_hooks = set(_iter_manifest_hooks(hooks))
    settings_hooks = set(_iter_manifest_hooks(settings))
    actions = [
        _plan_action(entry, runtime_hooks, settings_hooks, settings, repo_root, trust_state)
        for entry in entries
    ]
    writes: list[dict[str, str]] = []
    if mode == "remove":
        return _error_report(
            "remove mode is not implemented yet",
            mode,
            repo_root,
            catalog_path,
            hooks_path,
            settings_path,
            trust_state_path,
        ), 1
    if mode == "apply":
        actions, writes = _apply_actions(actions, settings, settings_path)

    return {
        "schema_version": 2,
        "status": "ok",
        "mode": mode,
        "repo_root": str(repo_root),
        "catalog_path": str(catalog_path),
        "hooks_path": str(hooks_path),
        "settings_path": str(settings_path),
        "trust_state_path": str(trust_state_path),
        "includes": includes,
        "summary": _summarize(actions),
        "actions": actions,
        "writes": writes,
    }, 0


def _error_report(
    error: str,
    mode: str,
    repo_root: Path,
    catalog_path: Path,
    hooks_path: Path,
    settings_path: Path,
    trust_state_path: Path,
) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "status": "error",
        "mode": mode,
        "repo_root": str(repo_root),
        "catalog_path": str(catalog_path),
        "hooks_path": str(hooks_path),
        "settings_path": str(settings_path),
        "trust_state_path": str(trust_state_path),
        "summary": {key: 0 for key in SUMMARY_KEYS},
        "actions": [],
        "writes": [],
        "error": error,
    }


def _format_human(report: dict[str, Any]) -> str:
    lines = [
        "Athanor hook install dry-run",
        f"status: {report['status']}",
        f"catalog: {report['catalog_path']}",
        f"hooks: {report['hooks_path']}",
        f"settings: {report['settings_path']}",
        f"trust-state: {report['trust_state_path']}",
    ]
    if report["status"] == "error":
        lines.append(f"error: {report['error']}")
        lines.append("writes: 0")
        return "\n".join(lines) + "\n"

    summary = report["summary"]
    for key in SUMMARY_KEYS:
        lines.append(f"{key}: {summary[key]}")
    lines.append(f"writes: {len(report['writes'])}")
    for action in report["actions"]:
        lines.append(
            f"- [{action['status']}] {action['id']} ({action['event']}): {action['reason']}"
        )
    return "\n".join(lines) + "\n"


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preview or apply Athanor hook settings changes.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root. Defaults to cwd.")
    parser.add_argument("--catalog", help="Hook catalog JSON path.")
    parser.add_argument("--hooks", help="Runtime hooks JSON path.")
    parser.add_argument("--settings", help="Claude settings JSON path.")
    parser.add_argument("--trust-state", help="Hook installer trust state JSON path.")
    parser.add_argument(
        "--mode",
        choices=sorted(VALID_MODES),
        default="dry-run",
        help="Installer operation mode. Defaults to dry-run.",
    )
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        help="Additional catalog hook id to evaluate for settings install.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    repo_root = Path(args.repo_root).resolve()
    catalog_path = Path(args.catalog).resolve() if args.catalog else repo_root / "hooks" / "catalog.json"
    hooks_path = Path(args.hooks).resolve() if args.hooks else repo_root / "hooks" / "hooks.json"
    settings_path = (
        Path(args.settings).resolve()
        if args.settings
        else repo_root / ".claude" / "settings.json"
    )
    trust_state_path = (
        Path(args.trust_state).resolve()
        if args.trust_state
        else repo_root / ".athanor" / "hook-installer-trust.json"
    )

    report, exit_code = build_report(
        repo_root=repo_root,
        catalog_path=catalog_path,
        hooks_path=hooks_path,
        settings_path=settings_path,
        trust_state_path=trust_state_path,
        includes=list(args.include),
        mode=args.mode,
    )
    if args.json:
        sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    else:
        output = _format_human(report)
        if report["status"] == "error":
            sys.stderr.write(output)
        else:
            sys.stdout.write(output)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
