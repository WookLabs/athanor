#!/usr/bin/env python3
"""Read-only distribution smoke gate for Athanor's Claude plugin surface."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

EXPECTED_AGENTS = ["ci-watcher", "codex-dispatcher", "learner", "releaser"]
EXCLUDED_PACKAGE_DIRS = {
    ".athanor",
    ".git",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "ref",
}


class DistributionInputError(Exception):
    """Raised when a required distribution input is unreadable."""


def _read_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise DistributionInputError(f"{label} not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DistributionInputError(f"{label} is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise DistributionInputError(f"{label} read error: {exc}") from exc
    if not isinstance(data, dict):
        raise DistributionInputError(f"{label} must be a JSON object")
    return data


def _check(
    checks: list[dict[str, Any]],
    check_id: str,
    passed: bool,
    message: str,
    *,
    expected: Any = None,
    actual: Any = None,
    extra: dict[str, Any] | None = None,
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
    if extra:
        item.update(extra)
    checks.append(item)


def _list_diff(expected: list[Any], actual: list[Any]) -> dict[str, list[Any]]:
    return {
        "missing": [item for item in expected if item not in actual],
        "unexpected": [item for item in actual if item not in expected],
    }


def _marketplace_plugin(marketplace: dict[str, Any], plugin_name: str) -> dict[str, Any] | None:
    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list):
        return None
    for plugin in plugins:
        if isinstance(plugin, dict) and plugin.get("name") == plugin_name:
            return plugin
    return None


def _agent_name_from_manifest_path(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    path = value.replace("\\", "/").rstrip("/")
    if not path.endswith(".md"):
        return None
    return Path(path).stem


def _manifest_agents(repo_root: Path, manifest: dict[str, Any]) -> list[str]:
    agents = manifest.get("agents")
    if isinstance(agents, list):
        names = [_agent_name_from_manifest_path(item) for item in agents]
        return sorted(name for name in names if name)
    if isinstance(agents, str):
        name = _agent_name_from_manifest_path(agents)
        return [name] if name else []

    agents_dir = repo_root / "agents"
    if not agents_dir.is_dir():
        return []
    return sorted(path.stem for path in agents_dir.glob("*.md"))


def _package_footprint(repo_root: Path) -> dict[str, Any]:
    file_count = 0
    total_bytes = 0
    largest_files: list[dict[str, Any]] = []
    paths, skipped_dirs = _package_file_paths(repo_root)

    for path in paths:
        try:
            size = path.stat().st_size
        except OSError:
            continue
        file_count += 1
        total_bytes += size
        largest_files.append(
            {
                "path": path.relative_to(repo_root).as_posix(),
                "bytes": size,
            }
        )

    largest_files.sort(key=lambda item: item["bytes"], reverse=True)
    return {
        "file_count": file_count,
        "total_bytes": total_bytes,
        "excluded_dirs": sorted(skipped_dirs | EXCLUDED_PACKAGE_DIRS),
        "largest_files": largest_files[:10],
    }


def _package_file_paths(repo_root: Path) -> tuple[list[Path], set[str]]:
    paths: list[Path] = []
    skipped_dirs: set[str] = set()
    for dirpath, dirnames, filenames in os.walk(repo_root):
        excluded = sorted(name for name in dirnames if name in EXCLUDED_PACKAGE_DIRS)
        skipped_dirs.update(excluded)
        dirnames[:] = sorted(name for name in dirnames if name not in EXCLUDED_PACKAGE_DIRS)
        base = Path(dirpath)
        for filename in sorted(filenames):
            paths.append(base / filename)
    paths.sort(key=lambda path: path.relative_to(repo_root).as_posix())
    return paths, skipped_dirs


def _run_command(args: list[str], cwd: Path, timeout: int) -> dict[str, Any]:
    try:
        result = subprocess.run(
            args,
            cwd=cwd,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "status": "error",
            "args": args,
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
            "warnings": [],
        }

    combined = "\n".join(part for part in (result.stdout, result.stderr) if part)
    warnings = [
        line.strip()
        for line in combined.splitlines()
        if "warning" in line.lower() or line.lstrip().startswith("‼")
    ]
    return {
        "status": "pass" if result.returncode == 0 else "fail",
        "args": args,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "warnings": warnings,
    }


def _claude_version(repo_root: Path, timeout: int) -> str | None:
    result = _run_command(["claude", "--version"], repo_root, timeout)
    if result["returncode"] != 0:
        return None
    first = str(result["stdout"]).strip().splitlines()
    return first[0] if first else None


def _parse_component_names(raw: str) -> list[str]:
    raw = raw.strip()
    if not raw or raw.startswith("("):
        return []
    raw = re.sub(r"\s+\(.*$", "", raw)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _parse_plugin_details(output: str) -> dict[str, Any]:
    counts: dict[str, int] = {}
    names: dict[str, list[str]] = {}

    for line in output.splitlines():
        match = re.match(
            r"^\s*(Skills|Agents|Hooks|MCP servers|LSP servers)\s+\((\d+)\)\s*(.*)$",
            line,
        )
        if not match:
            continue
        label = match.group(1)
        key = label.lower().replace(" ", "_")
        counts[key] = int(match.group(2))
        names[key] = _parse_component_names(match.group(3))

    token_match = re.search(r"Always-on:\s+~?\s*([\d,]+)\s+tok", output)
    always_on_tokens = int(token_match.group(1).replace(",", "")) if token_match else None

    return {
        "counts": counts,
        "names": names,
        "always_on_tokens": always_on_tokens,
    }


def _build_claude_surface(
    repo_root: Path,
    plugin_name: str,
    *,
    skip_claude: bool,
    timeout: int,
) -> dict[str, Any]:
    if skip_claude:
        return {"status": "skipped", "reason": "--skip-claude set"}
    if shutil.which("claude") is None:
        return {"status": "skipped", "reason": "claude CLI not found on PATH"}

    plugin_validate = _run_command(
        ["claude", "plugin", "validate", str(repo_root / ".claude-plugin" / "plugin.json")],
        repo_root,
        timeout,
    )
    marketplace_validate = _run_command(
        ["claude", "plugin", "validate", str(repo_root / ".claude-plugin" / "marketplace.json")],
        repo_root,
        timeout,
    )
    details = _run_command(
        ["claude", "--plugin-dir", str(repo_root), "plugin", "details", plugin_name],
        repo_root,
        timeout,
    )
    details_output = "\n".join(part for part in (details["stdout"], details["stderr"]) if part)
    parsed_details = _parse_plugin_details(details_output) if details["returncode"] == 0 else {
        "counts": {},
        "names": {},
        "always_on_tokens": None,
    }

    return {
        "status": "pass"
        if plugin_validate["returncode"] == 0
        and marketplace_validate["returncode"] == 0
        and details["returncode"] == 0
        else "fail",
        "version": _claude_version(repo_root, timeout),
        "plugin_validate": plugin_validate,
        "marketplace_validate": marketplace_validate,
        "details": details,
        "parsed_details": parsed_details,
    }


def build_report(
    repo_root: Path,
    *,
    skip_claude: bool,
    max_always_on_tokens: int,
    timeout: int,
) -> tuple[dict[str, Any], int]:
    manifest_path = repo_root / ".claude-plugin" / "plugin.json"
    marketplace_path = repo_root / ".claude-plugin" / "marketplace.json"
    manifest = _read_json(manifest_path, "plugin manifest")
    marketplace = _read_json(marketplace_path, "marketplace manifest")

    plugin_name = manifest.get("name")
    manifest_version = manifest.get("version")
    marketplace_entry = _marketplace_plugin(marketplace, str(plugin_name))
    marketplace_version = marketplace_entry.get("version") if marketplace_entry else None
    marketplace_source = marketplace_entry.get("source") if marketplace_entry else None
    marketplace_description = marketplace.get("description")
    manifest_agents = _manifest_agents(repo_root, manifest)
    footprint = _package_footprint(repo_root)
    claude_surface = _build_claude_surface(
        repo_root,
        str(plugin_name),
        skip_claude=skip_claude,
        timeout=timeout,
    )

    checks: list[dict[str, Any]] = []
    _check(
        checks,
        "manifest.plugin_name",
        plugin_name == "athanor",
        "plugin manifest name is athanor",
        expected="athanor",
        actual=plugin_name,
    )
    _check(
        checks,
        "manifest.marketplace_entry",
        marketplace_entry is not None,
        "marketplace contains an athanor plugin entry",
        expected="athanor",
        actual=plugin_name if marketplace_entry else None,
    )
    _check(
        checks,
        "manifest.marketplace_version",
        manifest_version == marketplace_version,
        "plugin and marketplace versions match",
        expected=manifest_version,
        actual=marketplace_version,
    )
    _check(
        checks,
        "manifest.marketplace_source",
        marketplace_source == "./",
        "marketplace source points at plugin root",
        expected="./",
        actual=marketplace_source,
    )
    _check(
        checks,
        "manifest.marketplace_description",
        isinstance(marketplace_description, str) and bool(marketplace_description.strip()),
        "marketplace has a user-facing description",
        expected="non-empty string",
        actual=marketplace_description,
    )
    _check(
        checks,
        "manifest.agent_surface",
        manifest_agents == EXPECTED_AGENTS,
        "plugin-root agents directory exposes exactly the intended loader-visible agents",
        expected=EXPECTED_AGENTS,
        actual=manifest_agents,
        extra=_list_diff(EXPECTED_AGENTS, manifest_agents),
    )
    _check(
        checks,
        "package.footprint_nonempty",
        footprint["file_count"] > 0 and footprint["total_bytes"] > 0,
        "package footprint contains tracked plugin files",
        actual={"file_count": footprint["file_count"], "total_bytes": footprint["total_bytes"]},
    )

    live_agents = manifest_agents
    live_agent_count = len(live_agents)
    source = "manifest"
    always_on_tokens = 0
    cost_status = "skipped"

    if claude_surface["status"] == "skipped":
        pass
    else:
        _check(
            checks,
            "claude.validate.plugin",
            claude_surface["plugin_validate"]["returncode"] == 0,
            "claude plugin validate passes for plugin manifest",
            actual=claude_surface["plugin_validate"]["returncode"],
            extra={"warnings": claude_surface["plugin_validate"].get("warnings", [])},
        )
        _check(
            checks,
            "claude.validate.marketplace",
            claude_surface["marketplace_validate"]["returncode"] == 0,
            "claude plugin validate passes for marketplace manifest",
            actual=claude_surface["marketplace_validate"]["returncode"],
            extra={"warnings": claude_surface["marketplace_validate"].get("warnings", [])},
        )
        details = claude_surface["details"]
        parsed = claude_surface["parsed_details"]
        live_agents = sorted(parsed["names"].get("agents", []))
        live_agent_count = int(parsed["counts"].get("agents", len(live_agents)))
        source = "claude-plugin-details"
        always_on_tokens = parsed.get("always_on_tokens")
        cost_status = "observed" if isinstance(always_on_tokens, int) else "unavailable"

        _check(
            checks,
            "claude.details",
            details["returncode"] == 0,
            "claude plugin details is available for local plugin-dir smoke",
            actual=details["returncode"],
        )
        _check(
            checks,
            "claude.agent_inventory",
            live_agents == EXPECTED_AGENTS and live_agent_count == len(EXPECTED_AGENTS),
            "live Claude loader reports exactly the intended 4-agent surface",
            expected=EXPECTED_AGENTS,
            actual=live_agents,
            extra={
                "agent_count": live_agent_count,
                **_list_diff(EXPECTED_AGENTS, live_agents),
            },
        )
        _check(
            checks,
            "claude.always_on_tokens",
            isinstance(always_on_tokens, int) and always_on_tokens <= max_always_on_tokens,
            "live Claude loader always-on token estimate stays within budget",
            expected={"max_always_on_tokens": max_always_on_tokens},
            actual=always_on_tokens,
        )

    failures = sum(1 for check in checks if check["status"] == "fail")
    status = "pass" if failures == 0 else "fail"
    report = {
        "schema_version": 1,
        "status": status,
        "summary": {
            "checks": len(checks),
            "errors": failures,
        },
        "plugin": {
            "name": plugin_name,
            "manifest_version": manifest_version,
            "marketplace_version": marketplace_version,
            "manifest_path": manifest_path.relative_to(repo_root).as_posix(),
            "marketplace_path": marketplace_path.relative_to(repo_root).as_posix(),
        },
        "claude_cli": {
            "status": claude_surface["status"],
            "version": claude_surface.get("version"),
            "reason": claude_surface.get("reason"),
            "plugin_validate_warnings": claude_surface.get("plugin_validate", {}).get("warnings", []),
            "marketplace_validate_warnings": claude_surface.get("marketplace_validate", {}).get("warnings", []),
        },
        "component_inventory": {
            "source": source,
            "expected_agents": EXPECTED_AGENTS,
            "agents": live_agents,
            "agent_count": live_agent_count,
        },
        "cost_surface": {
            "status": cost_status,
            "always_on_tokens": always_on_tokens,
            "max_always_on_tokens": max_always_on_tokens,
        },
        "package": footprint,
        "checks": checks,
    }
    return report, 0 if status == "pass" else 1


def _human_report(report: dict[str, Any]) -> str:
    lines = [
        "Athanor distribution smoke",
        f"status: {report['status']}",
        f"checks: {report['summary']['checks']}",
        f"errors: {report['summary']['errors']}",
        f"agents: {report['component_inventory']['agent_count']}",
        f"always_on_tokens: {report['cost_surface']['always_on_tokens']}",
    ]
    for check in report["checks"]:
        lines.append(f"- [{check['status']}] {check['id']}: {check['message']}")
    return "\n".join(lines) + "\n"


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Athanor plugin distribution smoke checks.")
    parser.add_argument("--repo-root", default=".", help="Repository root. Defaults to cwd.")
    parser.add_argument("--json", action="store_true", help="Emit JSON report.")
    parser.add_argument("--skip-claude", action="store_true", help="Skip optional Claude CLI checks.")
    parser.add_argument(
        "--max-always-on-tokens",
        type=int,
        default=2200,
        help="Maximum allowed always-on token estimate from claude plugin details.",
    )
    parser.add_argument("--timeout", type=int, default=20, help="Per-Claude-command timeout in seconds.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    repo_root = Path(args.repo_root).resolve()
    try:
        report, exit_code = build_report(
            repo_root,
            skip_claude=args.skip_claude,
            max_always_on_tokens=args.max_always_on_tokens,
            timeout=args.timeout,
        )
    except DistributionInputError as exc:
        report = {
            "schema_version": 1,
            "status": "fail",
            "summary": {"checks": 1, "errors": 1},
            "plugin": {},
            "claude_cli": {"status": "not-run"},
            "component_inventory": {
                "source": "none",
                "expected_agents": EXPECTED_AGENTS,
                "agents": [],
                "agent_count": 0,
            },
            "cost_surface": {
                "status": "not-run",
                "always_on_tokens": 0,
                "max_always_on_tokens": args.max_always_on_tokens,
            },
            "package": {"file_count": 0, "total_bytes": 0, "excluded_dirs": [], "largest_files": []},
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
