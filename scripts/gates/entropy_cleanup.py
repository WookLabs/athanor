#!/usr/bin/env python3
"""Read-only entropy cleanup report gate for Athanor."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.gates.runtime_conformance import (  # noqa: E402
    ConformanceInputError,
    build_report as build_runtime_conformance_report,
)

PLAN_DATE_RE = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})-")
CHECKBOX_RE = re.compile(r"^\s*-\s+\[[ xX]\]")
UNCHECKED_RE = re.compile(r"^\s*-\s+\[\s\]")


class EntropyInputError(Exception):
    """Raised when required entropy report input cannot be read."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _iso_now() -> str:
    return _utc_now().isoformat().replace("+00:00", "Z")


def _parse_date(raw: str) -> datetime.date:
    return datetime.strptime(raw, "%Y-%m-%d").date()


def _parse_iso_datetime(raw: str) -> datetime:
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def _today_from_generated_at(raw: str) -> datetime.date:
    try:
        return _parse_iso_datetime(raw).date()
    except ValueError:
        return _utc_now().date()


def _read_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise EntropyInputError(f"{label} not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EntropyInputError(f"{label} is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise EntropyInputError(f"{label} read error: {exc}") from exc
    if not isinstance(data, dict):
        raise EntropyInputError(f"{label} must be a JSON object")
    return data


def _add_check(
    checks: list[dict[str, Any]],
    check_id: str,
    category: str,
    status: str,
    message: str,
    **extra: Any,
) -> None:
    item = {
        "id": check_id,
        "category": category,
        "status": status,
        "message": message,
    }
    item.update({key: value for key, value in extra.items() if value is not None})
    checks.append(item)


def _add_action(
    actions: list[dict[str, Any]],
    action_id: str,
    severity: str,
    category: str,
    target: str,
    recommendation: str,
    **extra: Any,
) -> None:
    item = {
        "id": action_id,
        "severity": severity,
        "category": category,
        "target": target,
        "recommendation": recommendation,
    }
    item.update({key: value for key, value in extra.items() if value is not None})
    actions.append(item)


def _rel(repo_root: Path, path: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def _scan_plans(
    *,
    repo_root: Path,
    today: datetime.date,
    plan_warn_days: int,
    checks: list[dict[str, Any]],
    actions: list[dict[str, Any]],
) -> dict[str, Any]:
    plan_dir = repo_root / "docs" / "plans"
    files = sorted(plan_dir.glob("*.md")) if plan_dir.is_dir() else []
    missing_dates: list[dict[str, Any]] = []
    open_plans: list[dict[str, Any]] = []
    stale_open: list[dict[str, Any]] = []

    for path in files:
        text = path.read_text(encoding="utf-8")
        checked = 0
        unchecked = 0
        for line in text.splitlines():
            if not CHECKBOX_RE.match(line):
                continue
            if UNCHECKED_RE.match(line):
                unchecked += 1
            else:
                checked += 1

        match = PLAN_DATE_RE.match(path.name)
        if not match:
            if unchecked:
                missing_dates.append({"path": _rel(repo_root, path), "unchecked": unchecked})
            continue

        plan_date = _parse_date(match.group("date"))
        age_days = (today - plan_date).days
        if unchecked:
            item = {
                "path": _rel(repo_root, path),
                "age_days": age_days,
                "checked": checked,
                "unchecked": unchecked,
            }
            open_plans.append(item)
            if age_days > plan_warn_days:
                stale_open.append(item)

    if missing_dates:
        _add_check(
            checks,
            "plans.date_prefix",
            "plans",
            "warn",
            "Some open plan files do not carry a YYYY-MM-DD filename prefix",
            details={"plans": missing_dates},
        )
        _add_action(
            actions,
            "normalize-plan-filenames",
            "warn",
            "plans",
            "docs/plans",
            "Rename open plan files with a YYYY-MM-DD prefix or archive them.",
            plans=missing_dates,
        )
    else:
        _add_check(
            checks,
            "plans.date_prefix",
            "plans",
            "pass",
            "Open plan files carry dated filename prefixes",
        )

    if stale_open:
        _add_check(
            checks,
            "plans.open_stale",
            "plans",
            "warn",
            "Some dated plans have unchecked steps beyond the warning age",
            threshold_days=plan_warn_days,
            details={"plans": stale_open},
        )
        _add_action(
            actions,
            "review-open-plans",
            "warn",
            "plans",
            "docs/plans",
            "Review stale open plans, close completed steps, archive historical plans, or create follow-up work.",
            plans=stale_open,
        )
    else:
        _add_check(
            checks,
            "plans.open_stale",
            "plans",
            "pass",
            "No open dated plans exceed the warning age",
            threshold_days=plan_warn_days,
        )

    return {
        "plan_count": len(files),
        "open_plan_count": len(open_plans),
        "stale_open_plan_count": len(stale_open),
        "missing_date_prefix_count": len(missing_dates),
    }


def _scan_hook_candidates(
    *,
    repo_root: Path,
    today: datetime.date,
    checks: list[dict[str, Any]],
    actions: list[dict[str, Any]],
) -> dict[str, Any]:
    catalog_path = repo_root / "hooks" / "catalog.json"
    catalog = _read_json(catalog_path, "hook catalog")
    hooks = catalog.get("hooks")
    if not isinstance(hooks, list):
        raise EntropyInputError("hook catalog must contain hooks[]")

    candidates = [
        item
        for item in hooks
        if isinstance(item, dict) and item.get("runtime_default") == "capture-only"
    ]
    missing: list[dict[str, Any]] = []
    stale: list[dict[str, Any]] = []

    for entry in candidates:
        hook_id = str(entry.get("id", "<missing-id>"))
        for field in ("candidate_since", "review_after_days"):
            if field not in entry:
                missing.append({"id": hook_id, "field": field})
        source_refs = entry.get("source_refs")
        if not isinstance(source_refs, list) or not source_refs:
            missing.append({"id": hook_id, "field": "source_refs"})
        if any(item["id"] == hook_id for item in missing):
            continue

        since = entry["candidate_since"]
        review_after = entry["review_after_days"]
        if not isinstance(since, str):
            missing.append({"id": hook_id, "field": "candidate_since"})
            continue
        if not isinstance(review_after, int) or review_after < 0:
            missing.append({"id": hook_id, "field": "review_after_days"})
            continue
        try:
            age_days = (today - _parse_date(since)).days
        except ValueError:
            missing.append({"id": hook_id, "field": "candidate_since"})
            continue
        if age_days > review_after:
            stale.append(
                {
                    "id": hook_id,
                    "age_days": age_days,
                    "review_after_days": review_after,
                    "candidate_since": since,
                }
            )

    if missing:
        _add_check(
            checks,
            "hook_candidates.lifecycle_metadata",
            "hook_candidates",
            "fail",
            "Capture-only hook candidates must carry lifecycle metadata",
            details={"missing": missing},
        )
        _add_action(
            actions,
            "fix-hook-candidate-metadata",
            "fail",
            "hook_candidates",
            "hooks/catalog.json",
            "Add candidate_since, review_after_days, and source_refs to capture-only hook candidates.",
            missing=missing,
        )
    else:
        _add_check(
            checks,
            "hook_candidates.lifecycle_metadata",
            "hook_candidates",
            "pass",
            "Capture-only hook candidates carry lifecycle metadata",
        )

    if stale:
        _add_check(
            checks,
            "hook_candidates.review_age",
            "hook_candidates",
            "warn",
            "Some capture-only hook candidates are beyond their review age",
            details={"candidates": stale},
        )
        _add_action(
            actions,
            "review-hook-candidates",
            "warn",
            "hook_candidates",
            "hooks/catalog.json",
            "Review aging capture-only hook candidates and either promote, refresh, or remove them.",
            candidates=stale,
        )
    else:
        _add_check(
            checks,
            "hook_candidates.review_age",
            "hook_candidates",
            "pass",
            "No capture-only hook candidate exceeds its review age",
        )

    return {
        "candidate_count": len(candidates),
        "stale_candidate_count": len(stale),
        "metadata_error_count": len(missing),
    }


def _git_value(path: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(path), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def _is_git_repo(path: Path) -> bool:
    return _git_value(path, "rev-parse", "--is-inside-work-tree") == "true"


def _branch_from_decorations(raw: str) -> str:
    for item in raw.split(", "):
        if item.startswith("HEAD -> "):
            return item.removeprefix("HEAD -> ")
    return ""


def _git_head_info(path: Path) -> dict[str, str] | None:
    raw = _git_value(path, "show", "-s", "--format=%cI%x00%h%x00%D", "HEAD")
    parts = raw.split("\x00", 2)
    if len(parts) < 2 or not parts[0] or not parts[1]:
        return None
    decorations = parts[2] if len(parts) > 2 else ""
    return {
        "last_commit": parts[0],
        "sha": parts[1],
        "branch": _branch_from_decorations(decorations),
    }


def _scan_refs(
    *,
    repo_root: Path,
    today: datetime.date,
    ref_warn_days: int,
    checks: list[dict[str, Any]],
    actions: list[dict[str, Any]],
) -> dict[str, Any]:
    ref_dir = repo_root / "ref"
    children = sorted(item for item in ref_dir.iterdir()) if ref_dir.is_dir() else []
    refs: list[dict[str, Any]] = []
    stale: list[dict[str, Any]] = []
    non_git: list[str] = []

    for child in children:
        if not child.is_dir():
            continue
        git_info = _git_head_info(child)
        if git_info is None:
            non_git.append(_rel(repo_root, child))
            continue
        commit_date = git_info["last_commit"]
        age_days = None
        if commit_date:
            age_days = (today - _parse_iso_datetime(commit_date).date()).days
        item = {
            "path": _rel(repo_root, child),
            "branch": git_info["branch"],
            "sha": git_info["sha"],
            "last_commit": commit_date,
            "age_days": age_days,
        }
        refs.append(item)
        if age_days is None or age_days > ref_warn_days:
            stale.append(item)

    if non_git:
        _add_check(
            checks,
            "refs.git_shape",
            "refs",
            "warn",
            "Some ref children are not git repositories",
            details={"paths": non_git},
        )
        _add_action(
            actions,
            "review-non-git-refs",
            "warn",
            "refs",
            "ref",
            "Remove non-git ref children or document why they are intentionally kept.",
            paths=non_git,
        )
    else:
        _add_check(
            checks,
            "refs.git_shape",
            "refs",
            "pass",
            "All ref children are git repositories",
        )

    if stale:
        _add_check(
            checks,
            "refs.freshness",
            "refs",
            "warn",
            "Some local ref repositories exceed the freshness warning age",
            threshold_days=ref_warn_days,
            details={"refs": stale},
        )
        _add_action(
            actions,
            "refresh-ref-repositories",
            "warn",
            "refs",
            "ref",
            "Review stale local ref repositories before relying on them for new research.",
            refs=stale,
        )
    else:
        _add_check(
            checks,
            "refs.freshness",
            "refs",
            "pass",
            "No local ref repository exceeds the freshness warning age",
            threshold_days=ref_warn_days,
        )

    return {
        "ref_count": len(refs),
        "stale_ref_count": len(stale),
        "non_git_count": len(non_git),
        "refs": refs,
    }


def _scan_mirrors(
    *,
    repo_root: Path,
    checks: list[dict[str, Any]],
    actions: list[dict[str, Any]],
) -> dict[str, Any]:
    contract_path = repo_root / "docs" / "runtime-surface-contract.json"
    try:
        report, _exit_code = build_runtime_conformance_report(repo_root, contract_path)
    except ConformanceInputError as exc:
        _add_check(
            checks,
            "mirrors.runtime_conformance",
            "mirrors",
            "fail",
            "Runtime conformance inputs could not be read",
            details={"error": str(exc)},
        )
        _add_action(
            actions,
            "fix-runtime-conformance-inputs",
            "fail",
            "mirrors",
            "docs/runtime-surface-contract.json",
            "Restore runtime conformance inputs before relying on mirror drift results.",
            error=str(exc),
        )
        return {"status": "fail", "checks": 0, "errors": 1}

    failed = [
        str(item.get("id", "<missing-id>"))
        for item in report.get("checks", [])
        if isinstance(item, dict) and item.get("status") == "fail"
    ]
    if failed:
        _add_check(
            checks,
            "mirrors.runtime_conformance",
            "mirrors",
            "fail",
            "Runtime conformance gate reports drift",
            details={"failed_checks": failed},
        )
        _add_action(
            actions,
            "fix-runtime-conformance-drift",
            "fail",
            "mirrors",
            "docs/runtime-surface-contract.json",
            "Run the runtime conformance gate and repair Claude/Codex/hook surface drift.",
            failed_checks=failed,
        )
    else:
        _add_check(
            checks,
            "mirrors.runtime_conformance",
            "mirrors",
            "pass",
            "Runtime conformance gate passes",
            details={"checks": report.get("summary", {}).get("checks", 0)},
        )

    return {
        "status": str(report.get("status", "fail")),
        "checks": int(report.get("summary", {}).get("checks", 0)),
        "errors": int(report.get("summary", {}).get("errors", len(failed))),
    }


def build_report(
    *,
    repo_root: Path,
    generated_at: str | None = None,
    plan_warn_days: int = 30,
    ref_warn_days: int = 45,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    generated = generated_at or _iso_now()
    today = _today_from_generated_at(generated)
    checks: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []

    categories = {
        "plans": _scan_plans(
            repo_root=repo_root,
            today=today,
            plan_warn_days=plan_warn_days,
            checks=checks,
            actions=actions,
        ),
        "hook_candidates": _scan_hook_candidates(
            repo_root=repo_root,
            today=today,
            checks=checks,
            actions=actions,
        ),
        "refs": _scan_refs(
            repo_root=repo_root,
            today=today,
            ref_warn_days=ref_warn_days,
            checks=checks,
            actions=actions,
        ),
        "mirrors": _scan_mirrors(repo_root=repo_root, checks=checks, actions=actions),
    }

    errors = sum(1 for item in checks if item["status"] == "fail")
    warnings = sum(1 for item in checks if item["status"] == "warn")
    if errors:
        status = "fail"
    elif warnings:
        status = "warn"
    else:
        status = "pass"
    return {
        "schema_version": 1,
        "status": status,
        "summary": {
            "checks": len(checks),
            "warnings": warnings,
            "errors": errors,
            "actions": len(actions),
        },
        "generated_at": generated,
        "categories": categories,
        "checks": checks,
        "actions": actions,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Report read-only Athanor harness entropy cleanup signals."
    )
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--plan-warn-days", type=int, default=30)
    parser.add_argument("--ref-warn-days", type=int, default=45)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    if args.plan_warn_days < 0:
        print("entropy cleanup: --plan-warn-days must be >= 0", file=sys.stderr)
        return 2
    if args.ref_warn_days < 0:
        print("entropy cleanup: --ref-warn-days must be >= 0", file=sys.stderr)
        return 2
    try:
        report = build_report(
            repo_root=args.repo_root,
            plan_warn_days=args.plan_warn_days,
            ref_warn_days=args.ref_warn_days,
        )
    except EntropyInputError as exc:
        print(f"entropy cleanup: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        summary = report["summary"]
        print(
            "entropy "
            f"status={report['status']} "
            f"checks={summary['checks']} "
            f"warnings={summary['warnings']} "
            f"errors={summary['errors']} "
            f"actions={summary['actions']}"
        )

    if report["status"] == "fail":
        return 1
    if args.strict and report["status"] == "warn":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
