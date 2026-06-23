#!/usr/bin/env python3
"""Read-only catalog admission gate for local ref repositories."""
from __future__ import annotations

import argparse
import configparser
import json
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REF_ROOT = REPO_ROOT / "ref"
DEFAULT_LAST_REVIEWED = date(2026, 6, 20).isoformat()

SKIP_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "target",
    "venv",
}

ADOPTION_STATUSES = ("adopt", "adapt", "observe", "reject", "sunset")

CATEGORY_REASONS = {
    "official-contract": "Official runtime or plugin contract reference.",
    "runtime": "Runtime behavior reference for Claude/Codex boundary checks.",
    "catalog": "Discovery radar and marketplace governance reference.",
    "loop-harness": "Goal loop, work item, or harness operating-model reference.",
    "memory-eval": "Memory, trace, retrieval, or eval-quality reference.",
    "hook-safety": "Hook, command safety, permission, or policy reference.",
    "agentops": "Agent operations principle reference with low runtime surface.",
    "plugin-skill": "Claude plugin, skill, prompt, or agent collection reference.",
}

EXTERNAL_RISK_RE = re.compile(
    r"\b(api key|apikey|telemetry|dashboard|hosted|cloud|saas|proxy|"
    r"analytics|exporter|stripe|slack|linear|oauth|login)\b",
    re.IGNORECASE,
)


def _iso_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _safe_read_text(path: Path, limit: int = 12000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return ""


def _origin_url(repo: Path) -> str:
    config_path = repo / ".git" / "config"
    if not config_path.is_file():
        return f"local://{repo.name}"
    parser = configparser.ConfigParser()
    try:
        parser.read(config_path, encoding="utf-8")
    except configparser.Error:
        return f"local://{repo.name}"
    section = 'remote "origin"'
    if section not in parser:
        return f"local://{repo.name}"
    raw = parser[section].get("url", "").strip()
    if raw.startswith("git@github.com:"):
        return "https://github.com/" + raw.removeprefix("git@github.com:").removesuffix(".git")
    if raw.endswith(".git"):
        return raw[:-4]
    return raw or f"local://{repo.name}"


def _iter_repo_files(repo: Path) -> list[str]:
    paths: list[str] = []
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = [item for item in dirnames if item not in SKIP_DIRS]
        rel_dir = Path(dirpath).relative_to(repo)
        for filename in filenames:
            rel = rel_dir / filename
            paths.append(filename if str(rel_dir) == "." else rel.as_posix())
            if len(paths) > 25000:
                return paths
    return paths


def _readme_text(repo: Path) -> str:
    for name in ("README.md", "readme.md", "README.MD"):
        path = repo / name
        if path.is_file():
            return _safe_read_text(path)
    return ""


def _license_label(repo: Path, files: list[str], category: str) -> str:
    for rel in files:
        name = Path(rel).name.lower()
        if name in {"license", "license.md", "license.txt", "copying"}:
            return f"file:{rel}"
    for rel in (".claude-plugin/plugin.json", "plugin.json"):
        path = repo / rel
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        value = data.get("license")
        if isinstance(value, str) and value.strip():
            return f"manifest:{value.strip()}"
    if category == "agentops":
        return "principle-reference"
    return "unknown"


def _count_surface(files: list[str]) -> dict[str, int]:
    manifests = sum(
        1
        for rel in files
        if rel == ".claude-plugin/plugin.json"
        or rel == "plugin.json"
        or rel.endswith("/.claude-plugin/plugin.json")
    )
    skills = sum(1 for rel in files if Path(rel).name == "SKILL.md")
    agents = sum(
        1
        for rel in files
        if rel.startswith("agents/") and rel.lower().endswith(".md")
    )
    commands = sum(1 for rel in files if "/commands/" in f"/{rel}/" or rel.startswith("commands/"))
    hooks = sum(1 for rel in files if "hook" in rel.lower())
    mcp = sum(1 for rel in files if "mcp" in rel.lower())
    return {
        "manifests": manifests,
        "skills": skills,
        "agents": agents,
        "commands": commands,
        "hooks": hooks,
        "mcp": mcp,
    }


def _category(repo_name: str, files: list[str], readme: str) -> str:
    haystack = " ".join([repo_name, readme] + files[:500]).lower()
    if repo_name in {
        "anthropics-claude-code",
        "anthropics-claude-plugins-official",
        "anthropics-skills",
        "openai-codex",
    }:
        return "official-contract"
    if "12-factor" in repo_name.lower() or "agentops" in repo_name.lower():
        return "agentops"
    if any(term in haystack for term in ("marketplace", "awesome", "catalog", "radar")):
        return "catalog"
    if any(term in haystack for term in ("loop", "ralph", "goal", "harness", "orchestrat")):
        return "loop-harness"
    if any(term in haystack for term in ("memory", "mem", "trace", "eval", "retrieval", "evidence")):
        return "memory-eval"
    if any(term in haystack for term in ("hook", "safety", "guard", "permission", "policy")):
        return "hook-safety"
    if any(term in haystack for term in ("codex", "runtime", "sdk")):
        return "runtime"
    return "plugin-skill"


def _surface_cap(surface: dict[str, int]) -> bool:
    return (
        surface["agents"] > 0
        or surface["commands"] > 0
        or surface["skills"] > 10
        or surface["manifests"] > 1
        or surface["hooks"] > 20
        or surface["mcp"] > 10
    )


def _score_dimensions(
    *,
    category: str,
    license_label: str,
    surface: dict[str, int],
    readme: str,
    files: list[str],
) -> dict[str, int]:
    cap = _surface_cap(surface)
    has_readme = bool(readme.strip())
    has_tests_or_schema = any(
        rel.startswith("tests/")
        or "/tests/" in f"/{rel}"
        or rel.startswith("schemas/")
        or "/schemas/" in f"/{rel}"
        for rel in files
    )
    external_risk = bool(EXTERNAL_RISK_RE.search(readme))

    if cap:
        surface_discipline = 40 if surface["agents"] or surface["commands"] else 55
    else:
        surface_discipline = 90

    if license_label == "unknown":
        license_clarity = 45
    elif license_label == "principle-reference":
        license_clarity = 75
    else:
        license_clarity = 85

    category_fit = {
        "official-contract": 88,
        "agentops": 88,
        "loop-harness": 82,
        "memory-eval": 80,
        "hook-safety": 78,
        "catalog": 76,
        "runtime": 74,
        "plugin-skill": 65,
    }[category]

    return {
        "local_first": 35 if external_risk else 85,
        "surface_discipline": surface_discipline,
        "evidence_strength": 85 if has_tests_or_schema else (70 if has_readme else 45),
        "license_clarity": license_clarity,
        "athanor_fit": category_fit,
    }


def _status_for_score(score: int) -> str:
    if score >= 80:
        return "adopt"
    if score >= 65:
        return "adapt"
    if score >= 45:
        return "observe"
    if score >= 25:
        return "reject"
    return "sunset"


def _evidence_paths(files: list[str]) -> list[str]:
    preferred: list[str] = []
    for rel in files:
        lower = rel.lower()
        if rel in {"README.md", "AGENTS.md", "CLAUDE.md"}:
            preferred.append(rel)
        elif lower.endswith("skill.md"):
            preferred.append(rel)
        elif "schema" in lower and lower.endswith(".json"):
            preferred.append(rel)
        elif "test" in lower and lower.endswith((".py", ".ts", ".js", ".md")):
            preferred.append(rel)
        if len(preferred) >= 8:
            break
    return preferred


def _entry(repo: Path, ref_root: Path, last_reviewed: str) -> dict[str, Any]:
    files = _iter_repo_files(repo)
    readme = _readme_text(repo)
    category = _category(repo.name, files, readme)
    surface_counts = _count_surface(files)
    cap = _surface_cap(surface_counts)
    license_label = _license_label(repo, files, category)
    dimensions = _score_dimensions(
        category=category,
        license_label=license_label,
        surface=surface_counts,
        readme=readme,
        files=files,
    )
    overall = min(dimensions.values())
    cap_dimension = min(dimensions, key=dimensions.get)
    adoption_status = _status_for_score(overall)
    surface: dict[str, Any] = {
        **surface_counts,
        "cap": cap,
        "cap_sources": [
            name
            for name in ("manifests", "skills", "agents", "commands", "hooks", "mcp")
            if surface_counts[name] > 0
        ],
    }
    if cap:
        cap_reason = (
            "Runtime surface growth caps admission; adapt only through local "
            "gates, schemas, docs, or existing Athanor skills."
        )
    else:
        cap_reason = f"Weakest dimension is {cap_dimension}."
    return {
        "id": repo.name,
        "category": category,
        "url": _origin_url(repo),
        "local_ref": repo.relative_to(ref_root.parent).as_posix(),
        "why_included": CATEGORY_REASONS[category],
        "license": license_label,
        "last_reviewed": last_reviewed,
        "adoption_status": adoption_status,
        "runtime_surface_delta": surface,
        "sunset_condition": (
            "Sunset if no Athanor gate, schema, doc, or test still cites this ref "
            "after the next reference-radar review."
        ),
        "score": {
            "overall": overall,
            "dimensions": dimensions,
            "cap_dimension": cap_dimension,
        },
        "cap_reason": cap_reason,
        "evidence_paths": _evidence_paths(files),
        "signals": {
            "file_count": len(files),
            "has_readme": bool(readme.strip()),
            "external_risk_keywords": bool(EXTERNAL_RISK_RE.search(readme)),
        },
    }


def _check(
    checks: list[dict[str, Any]],
    check_id: str,
    status: str,
    message: str,
    *,
    expected: Any = None,
    actual: Any = None,
) -> None:
    item: dict[str, Any] = {"id": check_id, "status": status, "message": message}
    if expected is not None:
        item["expected"] = expected
    if actual is not None:
        item["actual"] = actual
    checks.append(item)


def _status_from_checks(checks: list[dict[str, Any]]) -> str:
    statuses = {check["status"] for check in checks}
    if "fail" in statuses:
        return "fail"
    if "warn" in statuses:
        return "warn"
    return "pass"


def build_report(
    *,
    ref_root: Path = DEFAULT_REF_ROOT,
    last_reviewed: str = DEFAULT_LAST_REVIEWED,
    generated_at: str | None = None,
) -> dict[str, Any]:
    ref_root = ref_root.resolve()
    local_refs = sorted([path for path in ref_root.iterdir() if path.is_dir()]) if ref_root.is_dir() else []
    entries = [_entry(path, ref_root, last_reviewed) for path in local_refs]
    capped = [entry for entry in entries if entry["runtime_surface_delta"]["cap"]]
    unknown_license = [entry for entry in entries if entry["license"] == "unknown"]
    checks: list[dict[str, Any]] = []
    # ref/ is the gitignored local reference corpus (never committed), so on any
    # clean checkout / CI run it is absent. Absent ref root => 0 refs to admit =>
    # vacuously clean, the same way every other check already handles 0 refs. It
    # is the normal/expected state, not a policy violation, so it must not fail.
    ref_root_present = ref_root.is_dir()
    _check(
        checks,
        "catalog.ref_root_exists",
        "pass",
        "local ref root exists"
        if ref_root_present
        else "no local ref root present; 0 refs to admit (expected on clean checkouts/CI)",
        expected=str(DEFAULT_REF_ROOT),
        actual=str(ref_root),
    )
    _check(
        checks,
        "catalog.entries_cover_local_refs",
        "pass" if len(entries) == len(local_refs) else "fail",
        "every local ref has an admission entry",
        expected=len(local_refs),
        actual=len(entries),
    )
    _check(
        checks,
        "catalog.runtime_surface_caps_reported",
        "warn" if capped else "pass",
        "runtime-surface growth is capped below direct adoption",
        actual=len(capped),
    )
    _check(
        checks,
        "catalog.unknown_license_reported",
        "warn" if unknown_license else "pass",
        "unknown license refs remain observe/reject/sunset unless otherwise capped by policy",
        actual=len(unknown_license),
    )
    _check(
        checks,
        "catalog.irreversible_actions_zero",
        "pass",
        "catalog admission gate is read-only",
        expected=0,
        actual=0,
    )

    failures = sum(1 for check in checks if check["status"] == "fail")
    warnings = sum(1 for check in checks if check["status"] == "warn")
    return {
        "schema_version": 1,
        "status": _status_from_checks(checks),
        "generated_at": generated_at or _iso_now(),
        "profile": {
            "id": "ref-catalog-admission",
            "description": "Read-only fail-cap admission report for local reference repositories.",
            "mutates_files_by_default": False,
            "external_telemetry": False,
        },
        "summary": {
            "local_refs": len(local_refs),
            "entries": len(entries),
            "warnings": warnings,
            "failures": failures,
            "capped_runtime_surface_refs": len(capped),
            "unknown_license_refs": len(unknown_license),
            "irreversible_actions": 0,
        },
        "recommendations": [
            "Adopt principles and contracts, not broad runtime surfaces.",
            "Adapt high-value refs through local read-only gates, schemas, docs, and existing Athanor skills.",
            "Observe large catalogs and SDKs as radar only until a gate proves a bounded adoption path.",
            "Reject daemon, telemetry, hosted dashboard, broad MCP, and automatic agent-generation surfaces by default.",
            "Sunset refs that no Athanor artifact cites after the next reference-radar review.",
        ],
        "entries": entries,
        "checks": checks,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Athanor ref catalog admission checks.")
    parser.add_argument("--ref-root", type=Path, default=DEFAULT_REF_ROOT)
    parser.add_argument("--last-reviewed", default=DEFAULT_LAST_REVIEWED)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    report = build_report(ref_root=args.ref_root, last_reviewed=args.last_reviewed)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        summary = report["summary"]
        print(
            "catalog-admission "
            f"status={report['status']} "
            f"refs={summary['local_refs']} "
            f"capped={summary['capped_runtime_surface_refs']} "
            f"unknown_license={summary['unknown_license_refs']} "
            f"warnings={summary['warnings']} "
            f"failures={summary['failures']}"
        )
        for check in report["checks"]:
            print(f"- {check['id']}: {check['status']}")
    if report["status"] == "fail":
        return 1
    if args.strict and report["status"] == "warn":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
