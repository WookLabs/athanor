#!/usr/bin/env python3
"""Read-only package-facing knowledge index gate for Athanor."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INDEX = Path("docs/package-knowledge-index.md")
MAX_LINES = 120
MAX_WORDS = 1200

REQUIRED_SECTIONS = (
    "Runtime Surface",
    "Operator Gate Map",
    "Safety Contracts",
    "Ship Profile Boundary",
    "Freshness",
)

REQUIRED_REFS: tuple[tuple[str, str, str], ...] = (
    ("distribution_smoke_doc", "doc", "docs/distribution-smoke.md"),
    ("package_footprint_doc", "doc", "docs/package-footprint-policy.md"),
    ("package_footprint_reduction_doc", "doc", "docs/package-footprint-reduction.md"),
    ("maintenance_profile_doc", "doc", "docs/maintenance-profile.md"),
    ("harness_decision_ledger_doc", "doc", "docs/harness-decision-ledger.md"),
    ("native_runtime_probe_doc", "doc", "docs/native-runtime-probe.md"),
    ("native_runtime_playbook_doc", "doc", "docs/native-runtime-playbook.md"),
    ("reactive_channel_fixture_doc", "doc", "docs/reactive-channel-fixtures.md"),
    ("work_item_stage_transitions_doc", "doc", "docs/work-item-stage-transitions.md"),
    ("memory_index_doc", "doc", "docs/memory-index.md"),
    ("memory_retrieval_eval_doc", "doc", "docs/memory-retrieval-eval.md"),
    ("workflow_trace_evals_doc", "doc", "docs/workflow-trace-evals.md"),
    ("handoff_artifact_doc", "doc", "docs/handoff-artifact.md"),
    ("durable_loop_controller_doc", "doc", "docs/durable-loop-controller.md"),
    ("catalog_admission_policy_doc", "doc", "docs/catalog-admission-policy.md"),
    ("codex_mirror_source_map_doc", "doc", "docs/codex-mirror-source-map.md"),
    ("agent_topology_doc", "doc", "docs/agent-topology.md"),
    ("distribution_smoke_gate", "gate", "scripts/gates/distribution_smoke.py"),
    ("package_footprint_gate", "gate", "scripts/gates/package_footprint_policy.py"),
    ("maintenance_profile_gate", "gate", "scripts/gates/maintenance_profile.py"),
    ("harness_decision_ledger_gate", "gate", "scripts/gates/harness_decision_ledger.py"),
    ("native_runtime_probe_gate", "gate", "scripts/gates/native_runtime_probe.py"),
    ("native_runtime_playbook_gate", "gate", "scripts/gates/native_runtime_playbook.py"),
    ("reactive_channel_fixture_gate", "gate", "scripts/gates/reactive_channel_fixture.py"),
    ("work_item_stage_gate", "gate", "scripts/gates/work_item_stage.py"),
    ("memory_index_gate", "gate", "scripts/gates/memory_index.py"),
    ("memory_retrieval_eval_gate", "gate", "scripts/gates/memory_retrieval_eval.py"),
    ("workflow_trace_query_cli", "gate", "scripts/evals/workflow_trace_query.py"),
    ("loop_run_log_helper", "gate", "scripts/loops/loop_run_log.py"),
    ("catalog_admission_gate", "gate", "scripts/gates/catalog_admission.py"),
    ("codex_mirror_parity_gate", "gate", "scripts/gates/codex_mirror_parity.py"),
    ("agent_topology_gate", "gate", "scripts/gates/agent_topology.py"),
)

ENTRY_POINTS = ("README.md", "CLAUDE.md")

FORBIDDEN_PREFIXES: tuple[tuple[str, str], ...] = (
    ("docs/plans/", "implementation plans are repo-local development history"),
    ("docs/archive/", "archived docs are repo-local development history"),
    ("docs/architecture/", "architecture reviews are repo-local development history"),
    ("tests/", "tests are development-only for the default package-facing index"),
    ("ref/", "reference clones are repo-local research inputs"),
    (".github/", "CI workflow files are repository operations"),
    (".athanor/", "runtime state is local and gitignored"),
)

LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def _iso_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _check(
    checks: list[dict[str, Any]],
    check_id: str,
    status: str,
    message: str,
    *,
    expected: Any = None,
    actual: Any = None,
) -> None:
    item: dict[str, Any] = {
        "id": check_id,
        "status": status,
        "message": message,
    }
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


def _is_external_target(target: str) -> bool:
    parsed = urlparse(target)
    return bool(parsed.scheme and parsed.scheme not in {"", "file"}) or target.startswith("//")


def _clean_target(target: str) -> str:
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc:
        return target
    cleaned = unquote(parsed.path)
    if cleaned == "" and parsed.fragment:
        return "#" + parsed.fragment
    return cleaned


def _repo_relative(path: Path, repo_root: Path) -> str | None:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return None


def _local_links(markdown: str, *, base_dir: Path, repo_root: Path) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []
    for raw in LINK_RE.findall(markdown):
        if _is_external_target(raw):
            links.append({"target": raw, "kind": "external", "status": "skip"})
            continue
        cleaned = _clean_target(raw)
        if cleaned.startswith("#"):
            links.append({"target": raw, "kind": "anchor", "status": "skip"})
            continue
        resolved = (base_dir / cleaned).resolve()
        rel = _repo_relative(resolved, repo_root)
        if rel is None:
            links.append(
                {
                    "target": raw,
                    "kind": "local",
                    "path": cleaned,
                    "status": "fail",
                    "reason": "link escapes repository root",
                }
            )
            continue
        links.append(
            {
                "target": raw,
                "kind": "local",
                "path": rel,
                "status": "pass" if resolved.exists() else "fail",
                "exists": resolved.exists(),
            }
        )
    return links


def _required_ref_reports(link_paths: set[str], repo_root: Path) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for ref_id, kind, rel in REQUIRED_REFS:
        exists = (repo_root / rel).is_file()
        linked = rel in link_paths
        reports.append(
            {
                "id": ref_id,
                "kind": kind,
                "path": rel,
                "exists": exists,
                "linked": linked,
                "status": "pass" if exists and linked else "fail",
            }
        )
    return reports


def _entry_point_reports(repo_root: Path) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for rel in ENTRY_POINTS:
        path = repo_root / rel
        exists = path.is_file()
        body = path.read_text(encoding="utf-8") if exists else ""
        links = _local_links(body, base_dir=repo_root, repo_root=repo_root)
        linked_paths = sorted(
            {
                link["path"]
                for link in links
                if link.get("kind") == "local" and isinstance(link.get("path"), str)
            }
        )
        reports.append(
            {
                "path": rel,
                "exists": exists,
                "links": linked_paths,
                "status": "pass" if exists and DEFAULT_INDEX.as_posix() in linked_paths else "fail",
            }
        )
    return reports


def _forbidden_refs(links: list[dict[str, Any]]) -> list[dict[str, Any]]:
    forbidden: list[dict[str, Any]] = []
    for link in links:
        path = link.get("path")
        if not isinstance(path, str):
            continue
        for prefix, reason in FORBIDDEN_PREFIXES:
            if path.startswith(prefix):
                forbidden.append({"path": path, "reason": reason})
                break
    return forbidden


def _section_statuses(body: str) -> list[dict[str, Any]]:
    headings = set(re.findall(r"^#{2,3}\s+(.+?)\s*$", body, re.MULTILINE))
    return [
        {
            "section": section,
            "status": "pass" if section in headings else "fail",
        }
        for section in REQUIRED_SECTIONS
    ]


def build_report(
    *,
    repo_root: Path,
    index_path: Path = DEFAULT_INDEX,
    generated_at: str | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    index_abs = (repo_root / index_path).resolve()
    index_rel = _repo_relative(index_abs, repo_root) or index_path.as_posix()
    body = index_abs.read_text(encoding="utf-8") if index_abs.is_file() else ""
    links = _local_links(body, base_dir=index_abs.parent, repo_root=repo_root) if body else []
    link_paths = {
        link["path"]
        for link in links
        if link.get("kind") == "local" and isinstance(link.get("path"), str)
    }
    required_refs = _required_ref_reports(link_paths, repo_root)
    entry_points = _entry_point_reports(repo_root)
    forbidden_refs = _forbidden_refs(links)
    unresolved_links = [
        link
        for link in links
        if link.get("kind") == "local" and link.get("status") == "fail"
    ]
    section_statuses = _section_statuses(body)
    line_count = len(body.splitlines())
    word_count = len(re.findall(r"\S+", body))

    checks: list[dict[str, Any]] = []
    _check(
        checks,
        "knowledge_index.exists",
        "pass" if index_abs.is_file() else "fail",
        "package-facing knowledge index exists",
        expected=index_path.as_posix(),
        actual=index_rel,
    )
    _check(
        checks,
        "knowledge_index.size",
        "pass" if line_count <= MAX_LINES and word_count <= MAX_WORDS else "fail",
        "package-facing knowledge index stays short",
        expected={"max_lines": MAX_LINES, "max_words": MAX_WORDS},
        actual={"lines": line_count, "words": word_count},
    )
    _check(
        checks,
        "knowledge_index.sections",
        "pass" if all(item["status"] == "pass" for item in section_statuses) else "fail",
        "package-facing knowledge index has required sections",
        expected=list(REQUIRED_SECTIONS),
        actual=section_statuses,
    )
    _check(
        checks,
        "knowledge_index.required_refs",
        "pass" if all(item["status"] == "pass" for item in required_refs) else "fail",
        "package-facing knowledge index links current docs and gates",
        expected=[path for _, _, path in REQUIRED_REFS],
        actual=required_refs,
    )
    _check(
        checks,
        "knowledge_index.entry_points",
        "pass" if all(item["status"] == "pass" for item in entry_points) else "fail",
        "runtime entry points link back to the package-facing index",
        expected=list(ENTRY_POINTS),
        actual=entry_points,
    )
    _check(
        checks,
        "knowledge_index.forbidden_refs",
        "pass" if not forbidden_refs else "fail",
        "package-facing index does not link development-history surfaces",
        expected=0,
        actual=len(forbidden_refs),
    )
    _check(
        checks,
        "knowledge_index.local_links_resolve",
        "pass" if not unresolved_links else "fail",
        "local package-facing index links resolve inside the repository",
        expected=0,
        actual=len(unresolved_links),
    )
    _check(
        checks,
        "knowledge_index.irreversible_actions_zero",
        "pass",
        "package knowledge index gate is read-only",
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
            "id": "package-facing-knowledge-index",
            "description": "Read-only gate for the short current package-facing knowledge index.",
            "mutates_files_by_default": False,
            "external_telemetry": False,
        },
        "summary": {
            "checks": len(checks),
            "warnings": warnings,
            "failures": failures,
            "required_refs": len(required_refs),
            "missing_required_refs": sum(1 for item in required_refs if item["status"] == "fail"),
            "forbidden_refs": len(forbidden_refs),
            "unresolved_links": len(unresolved_links),
            "entry_points": len(entry_points),
            "irreversible_actions": 0,
        },
        "index": {
            "path": index_rel,
            "line_count": line_count,
            "word_count": word_count,
            "max_lines": MAX_LINES,
            "max_words": MAX_WORDS,
        },
        "entry_points": entry_points,
        "required_refs": required_refs,
        "links": links,
        "forbidden_refs": forbidden_refs,
        "unresolved_links": unresolved_links,
        "sections": section_statuses,
        "checks": checks,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Athanor package knowledge index checks.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--index-path", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    report = build_report(repo_root=args.repo_root, index_path=args.index_path)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        summary = report["summary"]
        print(
            "package-knowledge-index "
            f"status={report['status']} "
            f"refs={summary['required_refs']} "
            f"missing={summary['missing_required_refs']} "
            f"forbidden={summary['forbidden_refs']} "
            f"unresolved={summary['unresolved_links']}"
        )
        for check in report["checks"]:
            print(f"- {check['id']}: {check['status']}")
    return 1 if report["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
