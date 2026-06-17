#!/usr/bin/env python3
"""Read-only cross-runtime conformance gate for Athanor."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]


class ConformanceInputError(Exception):
    """Raised when a required conformance input cannot be read."""


def _read_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise ConformanceInputError(f"{label} not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConformanceInputError(f"{label} is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise ConformanceInputError(f"{label} read error: {exc}") from exc
    if not isinstance(data, dict):
        raise ConformanceInputError(f"{label} must be a JSON object")
    return data


def _rel(root: Path, value: str) -> Path:
    return root / value


def _list_dirs(path: Path) -> list[str]:
    if not path.is_dir():
        return []
    return sorted(
        item.name
        for item in path.iterdir()
        if item.is_dir() and not item.name.startswith(".")
    )


def _check(
    checks: list[dict[str, Any]],
    check_id: str,
    passed: bool,
    message: str,
    *,
    expected: Any = None,
    actual: Any = None,
) -> None:
    item: dict[str, Any] = {
        "id": check_id,
        "status": "pass" if passed else "fail",
        "message": message,
    }
    if expected is not None:
        item["expected"] = expected
    if actual is not None:
        item["actual"] = actual
    checks.append(item)


def _manifest_hook_triples(hooks_manifest: dict[str, Any]) -> list[dict[str, str]]:
    hooks = hooks_manifest.get("hooks")
    if not isinstance(hooks, dict):
        return []

    triples: list[dict[str, str]] = []
    for event, entries in hooks.items():
        if not isinstance(event, str) or not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            matcher = entry.get("matcher", "")
            if not isinstance(matcher, str):
                matcher = ""
            handlers = entry.get("hooks")
            if not isinstance(handlers, list):
                continue
            for handler in handlers:
                if not isinstance(handler, dict):
                    continue
                if handler.get("type") != "command":
                    continue
                command = handler.get("command")
                if isinstance(command, str):
                    triples.append(
                        {
                            "event": event,
                            "matcher": matcher,
                            "command": command,
                        }
                    )
    return sorted(triples, key=lambda item: (item["event"], item["matcher"], item["command"]))


def _catalog_enabled_triples(catalog: dict[str, Any]) -> list[dict[str, str]]:
    entries = catalog.get("hooks")
    if not isinstance(entries, list):
        return []

    triples: list[dict[str, str]] = []
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("runtime_default") != "enabled":
            continue
        event = entry.get("event")
        command = entry.get("command")
        matcher = entry.get("matcher", "")
        if not isinstance(event, str) or not isinstance(command, str):
            continue
        if not isinstance(matcher, str):
            matcher = ""
        triples.append({"event": event, "matcher": matcher, "command": command})
    return sorted(triples, key=lambda item: (item["event"], item["matcher"], item["command"]))


def _enabled_events(triples: list[dict[str, str]]) -> list[str]:
    return sorted({item["event"] for item in triples})


def build_report(repo_root: Path, contract_path: Path) -> tuple[dict[str, Any], int]:
    contract = _read_json(contract_path, "runtime surface contract")
    claude_contract = contract.get("claude_plugin")
    codex_contract = contract.get("codex_companion")
    hook_contract = contract.get("hook_catalog")
    if not isinstance(claude_contract, dict):
        raise ConformanceInputError("contract claude_plugin must be an object")
    if not isinstance(codex_contract, dict):
        raise ConformanceInputError("contract codex_companion must be an object")
    if not isinstance(hook_contract, dict):
        raise ConformanceInputError("contract hook_catalog must be an object")

    claude_manifest = _read_json(_rel(repo_root, str(claude_contract["manifest"])), "Claude manifest")
    codex_manifest = _read_json(_rel(repo_root, str(codex_contract["manifest"])), "Codex manifest")
    hooks_manifest = _read_json(_rel(repo_root, str(claude_contract["hook_manifest"])), "hooks manifest")
    hook_catalog = _read_json(_rel(repo_root, str(hook_contract["catalog"])), "hook catalog")

    checks: list[dict[str, Any]] = []

    expected_claude_name = str(claude_contract["name"])
    actual_claude_name = claude_manifest.get("name")
    _check(
        checks,
        "claude.plugin_name",
        actual_claude_name == expected_claude_name,
        "Claude plugin name matches runtime contract",
        expected=expected_claude_name,
        actual=actual_claude_name,
    )

    claude_forbidden = ["hooks", "mcpServers", "apps"]
    claude_present_forbidden = [key for key in claude_forbidden if key in claude_manifest]
    _check(
        checks,
        "claude.forbidden_manifest_keys",
        not claude_present_forbidden,
        "Claude manifest does not duplicate runtime hook or app surfaces",
        expected=[],
        actual=claude_present_forbidden,
    )

    expected_claude_skills = sorted(
        list(claude_contract.get("native_skills", []))
        + list(claude_contract.get("vendored_claude_only_skills", []))
    )
    actual_claude_skills = _list_dirs(repo_root / "skills")
    _check(
        checks,
        "claude.skills",
        actual_claude_skills == expected_claude_skills,
        "Claude skill directories match runtime contract",
        expected=expected_claude_skills,
        actual=actual_claude_skills,
    )

    expected_codex_name = str(codex_contract["name"])
    actual_codex_name = codex_manifest.get("name")
    _check(
        checks,
        "codex.plugin_name",
        actual_codex_name == expected_codex_name,
        "Codex companion plugin name matches runtime contract",
        expected=expected_codex_name,
        actual=actual_codex_name,
    )

    codex_forbidden = [
        str(key) for key in codex_contract.get("forbidden_manifest_keys", [])
    ]
    codex_present_forbidden = [key for key in codex_forbidden if key in codex_manifest]
    _check(
        checks,
        "codex.forbidden_manifest_keys",
        not codex_present_forbidden,
        "Codex companion manifest stays hook/MCP/app free",
        expected=[],
        actual=codex_present_forbidden,
    )

    expected_codex_skills = sorted(str(skill) for skill in codex_contract.get("skills", []))
    actual_codex_skills = _list_dirs(repo_root / "plugins" / "athanor-codex" / "skills")
    _check(
        checks,
        "codex.skills",
        actual_codex_skills == expected_codex_skills,
        "Codex companion skill directories match runtime contract",
        expected=expected_codex_skills,
        actual=actual_codex_skills,
    )

    catalog_triples = _catalog_enabled_triples(hook_catalog)
    manifest_triples = _manifest_hook_triples(hooks_manifest)
    expected_events = sorted(str(event) for event in hook_contract.get("enabled_runtime_events", []))
    actual_events = _enabled_events(catalog_triples)
    _check(
        checks,
        "hooks.enabled_events",
        actual_events == expected_events,
        "Enabled catalog events match runtime contract",
        expected=expected_events,
        actual=actual_events,
    )
    _check(
        checks,
        "hooks.enabled_runtime_manifest",
        manifest_triples == catalog_triples,
        "hooks/hooks.json exactly matches enabled catalog hook entries",
        expected=catalog_triples,
        actual=manifest_triples,
    )

    errors = sum(1 for check in checks if check["status"] == "fail")
    status = "pass" if errors == 0 else "fail"
    report = {
        "schema_version": 1,
        "status": status,
        "summary": {
            "checks": len(checks),
            "errors": errors,
        },
        "surfaces": {
            "claude": {
                "plugin_name": actual_claude_name,
                "skills": actual_claude_skills,
            },
            "codex": {
                "plugin_name": actual_codex_name,
                "skills": actual_codex_skills,
            },
            "hooks": {
                "enabled_events": actual_events,
                "runtime_events": _enabled_events(manifest_triples),
            },
        },
        "checks": checks,
    }
    return report, 0 if status == "pass" else 1


def _human_report(report: dict[str, Any]) -> str:
    lines = [
        "Athanor cross-runtime conformance",
        f"status: {report['status']}",
        f"checks: {report['summary']['checks']}",
        f"errors: {report['summary']['errors']}",
    ]
    for check in report["checks"]:
        lines.append(f"- [{check['status']}] {check['id']}: {check['message']}")
    return "\n".join(lines) + "\n"


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Athanor cross-runtime conformance.")
    parser.add_argument("--repo-root", default=".", help="Repository root. Defaults to cwd.")
    parser.add_argument(
        "--contract",
        default="docs/runtime-surface-contract.json",
        help="Runtime surface contract JSON path.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON report.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    repo_root = Path(args.repo_root).resolve()
    contract_path = Path(args.contract)
    if not contract_path.is_absolute():
        contract_path = repo_root / contract_path

    try:
        report, exit_code = build_report(repo_root, contract_path)
    except ConformanceInputError as exc:
        report = {
            "schema_version": 1,
            "status": "fail",
            "summary": {"checks": 1, "errors": 1},
            "surfaces": {"claude": {}, "codex": {}, "hooks": {}},
            "checks": [
                {
                    "id": "input",
                    "status": "fail",
                    "message": str(exc),
                }
            ],
        }
        exit_code = 1

    if args.json:
        sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    else:
        output = _human_report(report)
        if exit_code:
            sys.stderr.write(output)
        else:
            sys.stdout.write(output)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
