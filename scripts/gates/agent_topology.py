#!/usr/bin/env python3
"""Read-only agent/skill topology gate for Athanor."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACT = Path("docs/agent-topology-contract.json")
DEFAULT_DOC = Path("docs/agent-topology.md")


class TopologyInputError(Exception):
    """Raised when a required topology input cannot be read."""


def _read_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise TopologyInputError(f"{label} not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TopologyInputError(f"{label} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise TopologyInputError(f"{label} must be a JSON object")
    return data


def _read_text(path: Path, label: str) -> str:
    if not path.is_file():
        raise TopologyInputError(f"{label} not found: {path}")
    return path.read_text(encoding="utf-8")


def _frontmatter(path: Path) -> str:
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    return parts[1] if len(parts) >= 3 else ""


def _has_frontmatter_key(path: Path, key: str) -> bool:
    pattern = rf"^\s*{re.escape(key)}\s*:\s*\S+"
    return bool(re.search(pattern, _frontmatter(path), re.MULTILINE))


def _list_md_stems(path: Path) -> list[str]:
    if not path.is_dir():
        return []
    return sorted(item.stem for item in path.iterdir() if item.is_file() and item.suffix == ".md")


def _list_skill_dirs(path: Path) -> list[str]:
    if not path.is_dir():
        return []
    return sorted(item.name for item in path.iterdir() if item.is_dir() and not item.name.startswith("."))


def _names(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []
    names: list[str] = []
    for item in items:
        if isinstance(item, dict) and isinstance(item.get("name"), str):
            names.append(item["name"])
    return sorted(names)


def _route_names(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []
    names: list[str] = []
    for item in items:
        if isinstance(item, dict) and isinstance(item.get("skill"), str):
            names.append(item["skill"])
    return sorted(names)


def _route_by_skill(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    routes: dict[str, dict[str, Any]] = {}
    for item in contract.get("skill_routes", []):
        if isinstance(item, dict) and isinstance(item.get("skill"), str):
            routes[item["skill"]] = item
    return routes


def _list_diff(expected: list[Any], actual: list[Any]) -> dict[str, Any]:
    return {
        "missing": [item for item in expected if item not in actual],
        "unexpected": [item for item in actual if item not in expected],
    }


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


def _invalid_refs(
    routes: dict[str, dict[str, Any]],
    *,
    field: str,
    allowed: set[str],
) -> list[dict[str, str]]:
    invalid: list[dict[str, str]] = []
    for skill, route in sorted(routes.items()):
        refs = route.get(field, [])
        if not isinstance(refs, list):
            invalid.append({"skill": skill, "value": f"{field} is not a list"})
            continue
        for ref in refs:
            if not isinstance(ref, str) or ref not in allowed:
                invalid.append({"skill": skill, "value": str(ref)})
    return invalid


def _owner_skill_drift(
    contract: dict[str, Any],
    routes: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    actual: dict[str, set[str]] = {}
    for skill, route in routes.items():
        for role in route.get("reference_roles", []):
            if isinstance(role, str):
                actual.setdefault(role, set()).add(skill)

    drift: list[dict[str, Any]] = []
    for role in contract.get("reference_roles", []):
        if not isinstance(role, dict) or not isinstance(role.get("name"), str):
            continue
        expected = sorted(str(item) for item in role.get("owner_skills", []))
        seen = sorted(actual.get(role["name"], set()))
        if expected != seen:
            drift.append({"role": role["name"], "expected": expected, "actual": seen})
    return drift


def _entry_point_link_reports(repo_root: Path) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    targets = {
        "CLAUDE.md": "docs/agent-topology.md",
        "README.md": "docs/agent-topology.md",
        "docs/package-knowledge-index.md": "agent-topology.md",
    }
    for rel, token in targets.items():
        path = repo_root / rel
        exists = path.is_file()
        body = path.read_text(encoding="utf-8") if exists else ""
        reports.append(
            {
                "path": rel,
                "token": token,
                "exists": exists,
                "linked": token in body,
                "status": "pass" if exists and token in body else "fail",
            }
        )
    return reports


def build_report(
    *,
    repo_root: Path,
    contract_path: Path = DEFAULT_CONTRACT,
    doc_path: Path = DEFAULT_DOC,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    contract_abs = (repo_root / contract_path).resolve()
    doc_abs = (repo_root / doc_path).resolve()
    contract = _read_json(contract_abs, "agent topology contract")
    doc = _read_text(doc_abs, "agent topology doc")

    registered_contract = _names(contract.get("registered_agents"))
    reference_contract = _names(contract.get("reference_roles"))
    routes = _route_by_skill(contract)
    route_contract = sorted(routes)

    actual_registered = _list_md_stems(repo_root / "agents")
    actual_reference = _list_md_stems(repo_root / "docs" / "agent-roles")
    actual_skills = _list_skill_dirs(repo_root / "skills")

    reference_with_name = sorted(
        role
        for role in actual_reference
        if _has_frontmatter_key(repo_root / "docs" / "agent-roles" / f"{role}.md", "name")
    )
    registered_without_name = sorted(
        agent
        for agent in actual_registered
        if not _has_frontmatter_key(repo_root / "agents" / f"{agent}.md", "name")
    )

    registered_set = set(registered_contract)
    reference_set = set(reference_contract)
    invalid_registered_refs = _invalid_refs(
        routes,
        field="registered_agents",
        allowed=registered_set,
    )
    invalid_reference_refs = _invalid_refs(
        routes,
        field="reference_roles",
        allowed=reference_set,
    )
    owner_drift = _owner_skill_drift(contract, routes)

    prompt_route = routes.get("prompt-gen", {})
    prompt_handoffs = prompt_route.get("next_skill_handoffs", [])
    prompt_ok = (
        prompt_route.get("leader_kind") == "intake-framing"
        and prompt_route.get("registered_agents") == []
        and isinstance(prompt_handoffs, list)
        and {"plan", "discuss", "work"}.issubset(set(prompt_handoffs))
    )

    entry_points = _entry_point_link_reports(repo_root)
    doc_tokens = [
        "80/100",
        "92/100",
        "No new registered agent",
        "agent-topology-contract.json",
    ]
    missing_doc_tokens = [token for token in doc_tokens if token not in doc]

    checks: list[dict[str, Any]] = []
    _check(
        checks,
        "contract.schema_version",
        contract.get("schema_version") == 1,
        "agent topology contract schema version is current",
        expected=1,
        actual=contract.get("schema_version"),
    )
    _check(
        checks,
        "registered_agents.files",
        actual_registered == registered_contract,
        "plugin-root agents directory matches registered-agent contract",
        expected=registered_contract,
        actual=actual_registered,
        extra=_list_diff(registered_contract, actual_registered),
    )
    _check(
        checks,
        "registered_agents.frontmatter",
        not registered_without_name,
        "registered agent files keep name: frontmatter",
        expected=[],
        actual=registered_without_name,
    )
    _check(
        checks,
        "reference_roles.files",
        actual_reference == reference_contract,
        "reference role directory matches topology contract",
        expected=reference_contract,
        actual=actual_reference,
        extra=_list_diff(reference_contract, actual_reference),
    )
    _check(
        checks,
        "reference_roles.not_registered",
        not reference_with_name,
        "reference roles stay reference-only with no name: frontmatter",
        expected=[],
        actual=reference_with_name,
    )
    _check(
        checks,
        "skills.routes_cover_actual",
        route_contract == actual_skills,
        "every skill directory has exactly one topology route",
        expected=actual_skills,
        actual=route_contract,
        extra=_list_diff(actual_skills, route_contract),
    )
    _check(
        checks,
        "skill_routes.registered_refs",
        not invalid_registered_refs,
        "skill routes reference only declared registered agents",
        expected=[],
        actual=invalid_registered_refs,
    )
    _check(
        checks,
        "skill_routes.reference_refs",
        not invalid_reference_refs,
        "skill routes reference only declared reference roles",
        expected=[],
        actual=invalid_reference_refs,
    )
    _check(
        checks,
        "reference_roles.owner_skills",
        not owner_drift,
        "reference role owner_skills match skill route usage",
        expected=[],
        actual=owner_drift,
    )
    _check(
        checks,
        "prompt_gen.intake_route",
        prompt_ok,
        "prompt-gen stays an intake-framing skill with no registered agent",
        expected={
            "leader_kind": "intake-framing",
            "registered_agents": [],
            "required_handoffs": ["discuss", "plan", "work"],
        },
        actual=prompt_route,
    )
    _check(
        checks,
        "docs.topology_tokens",
        not missing_doc_tokens,
        "agent topology doc includes score and no-new-agent decisions",
        expected=doc_tokens,
        actual=[token for token in doc_tokens if token in doc],
        extra={"missing": missing_doc_tokens, "unexpected": []},
    )
    _check(
        checks,
        "docs.entry_point_links",
        all(item["status"] == "pass" for item in entry_points),
        "entry points link to the agent topology doc",
        expected=["CLAUDE.md", "README.md", "docs/package-knowledge-index.md"],
        actual=entry_points,
    )
    _check(
        checks,
        "gate.read_only",
        True,
        "agent topology gate is read-only",
        expected=0,
        actual=0,
    )

    errors = sum(1 for check in checks if check["status"] == "fail")
    status = "pass" if errors == 0 else "fail"
    return {
        "schema_version": 1,
        "status": status,
        "profile": {
            "id": "agent-topology",
            "mutates_files_by_default": False,
            "external_telemetry": False,
        },
        "summary": {
            "checks": len(checks),
            "errors": errors,
            "registered_agents": len(actual_registered),
            "reference_roles": len(actual_reference),
            "skill_routes": len(route_contract),
            "irreversible_actions": 0,
        },
        "surfaces": {
            "registered_agents": actual_registered,
            "reference_roles": actual_reference,
            "skills": actual_skills,
        },
        "checks": checks,
    }


def _human_report(report: dict[str, Any]) -> str:
    lines = [
        "Athanor agent topology",
        f"status: {report['status']}",
        f"checks: {report['summary']['checks']}",
        f"errors: {report['summary']['errors']}",
    ]
    for check in report["checks"]:
        lines.append(f"- [{check['status']}] {check['id']}: {check['message']}")
    return "\n".join(lines) + "\n"


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Athanor agent/skill topology.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    try:
        report = build_report(
            repo_root=args.repo_root,
            contract_path=args.contract,
            doc_path=args.doc,
        )
    except TopologyInputError as exc:
        report = {
            "schema_version": 1,
            "status": "fail",
            "profile": {
                "id": "agent-topology",
                "mutates_files_by_default": False,
                "external_telemetry": False,
            },
            "summary": {
                "checks": 1,
                "errors": 1,
                "registered_agents": 0,
                "reference_roles": 0,
                "skill_routes": 0,
                "irreversible_actions": 0,
            },
            "surfaces": {
                "registered_agents": [],
                "reference_roles": [],
                "skills": [],
            },
            "checks": [
                {
                    "id": "input",
                    "status": "fail",
                    "message": str(exc),
                }
            ],
        }

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        output = _human_report(report)
        if report["status"] == "fail":
            sys.stderr.write(output)
        else:
            sys.stdout.write(output)
    return 1 if report["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
