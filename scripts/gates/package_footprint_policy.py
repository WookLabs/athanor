#!/usr/bin/env python3
"""Read-only package footprint policy gate for Athanor."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.gates.distribution_smoke import _package_footprint  # noqa: E402

DEFAULT_MAX_FILES = 600
DEFAULT_MAX_TOTAL_BYTES = 4_750_000
DEFAULT_MAX_LARGE_FILE_BYTES = 250_000
DEFAULT_CANDIDATE_LIMIT = 20

DEV_ONLY_PREFIXES: tuple[tuple[str, str], ...] = (
    ("tests/", "regression tests are development-only for the default ship profile"),
    ("docs/plans/", "historical implementation plans are development history"),
    ("docs/archive/", "archived historical docs are development history"),
    ("docs/goals-completed/", "completed goal receipts are development history"),
    ("docs/architecture/", "research and architecture review docs are development history"),
    (".github/", "CI workflows are repository operations, not runtime plugin surface"),
)


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


def _bucket_for_path(path: str) -> str:
    if path.startswith("skills/") or path.startswith("agents/") or path.startswith("hooks/"):
        return "runtime"
    if path.startswith(".claude-plugin/") or path in {
        "athanor.json",
        "templates/athanor.json",
        "README.md",
        "CHANGELOG.md",
        "LICENSE",
        "NOTICE.md",
        "SECURITY.md",
        "CODE_OF_CONDUCT.md",
        "CONTRIBUTING.md",
    }:
        return "distribution_metadata"
    if path.startswith("scripts/hooks/") or path.startswith("scripts/work/"):
        return "runtime_support"
    if path.startswith("scripts/gates/") or path.startswith("scripts/observability/"):
        return "maintenance"
    if path.startswith("scripts/evals/") or path.startswith("scripts/loops/"):
        return "evals"
    if path.startswith("schemas/"):
        return "schemas"
    if path.startswith(".github/"):
        return "development_ci"
    if path.startswith("tests/"):
        return "tests"
    if path.startswith(("docs/plans/", "docs/archive/", "docs/goals-completed/", "docs/architecture/")):
        return "development_history"
    if path.startswith("docs/"):
        return "docs"
    return "other"


def _candidate_reason(path: str) -> str | None:
    for prefix, reason in DEV_ONLY_PREFIXES:
        if path.startswith(prefix):
            return reason
    return None


def _file_records(repo_root: Path) -> list[dict[str, Any]]:
    footprint = _package_footprint(repo_root)
    records: list[dict[str, Any]] = []
    # Distribution smoke truncates largest_files, so do a full scan here while
    # preserving its exclusion policy through _package_footprint.
    excluded_dirs = set(footprint.get("excluded_dirs", []))
    for path in repo_root.rglob("*"):
        rel_parts = path.relative_to(repo_root).parts
        if any(part in excluded_dirs for part in rel_parts):
            continue
        if not path.is_file():
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        rel = path.relative_to(repo_root).as_posix()
        records.append({"path": rel, "bytes": size, "bucket": _bucket_for_path(rel)})
    records.sort(key=lambda item: item["path"])
    return records


def _classifications(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    for record in records:
        bucket = record["bucket"]
        summary = buckets.setdefault(bucket, {"bucket": bucket, "files": 0, "bytes": 0})
        summary["files"] += 1
        summary["bytes"] += record["bytes"]
    return sorted(buckets.values(), key=lambda item: item["bucket"])


def _dev_only_candidates(
    records: list[dict[str, Any]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for record in records:
        reason = _candidate_reason(record["path"])
        if reason is None:
            continue
        candidates.append(
            {
                "path": record["path"],
                "bytes": record["bytes"],
                "bucket": record["bucket"],
                "reason": reason,
                "recommended_action": "exclude-from-ship-profile",
            }
        )
    candidates.sort(key=lambda item: (-int(item["bytes"]), item["path"]))
    return candidates[:limit]


def _status_from_checks(checks: list[dict[str, Any]]) -> str:
    statuses = {check["status"] for check in checks}
    if "fail" in statuses:
        return "fail"
    if "warn" in statuses:
        return "warn"
    return "pass"


def build_report(
    *,
    repo_root: Path,
    max_files: int = DEFAULT_MAX_FILES,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
    max_large_file_bytes: int = DEFAULT_MAX_LARGE_FILE_BYTES,
    candidate_limit: int = DEFAULT_CANDIDATE_LIMIT,
    generated_at: str | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    footprint = _package_footprint(repo_root)
    records = _file_records(repo_root)
    classifications = _classifications(records)
    dev_only_candidates = _dev_only_candidates(records, limit=candidate_limit)
    largest_files = sorted(
        ({"path": record["path"], "bytes": record["bytes"]} for record in records),
        key=lambda item: (-int(item["bytes"]), item["path"]),
    )[:10]
    over_large = [
        item for item in largest_files if int(item["bytes"]) > max_large_file_bytes
    ]

    checks: list[dict[str, Any]] = []
    _check(
        checks,
        "footprint.file_budget",
        "pass" if footprint["file_count"] <= max_files else "fail",
        "package file count stays within the ship-profile budget",
        expected={"max_files": max_files},
        actual=footprint["file_count"],
    )
    _check(
        checks,
        "footprint.total_bytes_budget",
        "pass" if footprint["total_bytes"] <= max_total_bytes else "fail",
        "package total bytes stay within the ship-profile budget",
        expected={"max_total_bytes": max_total_bytes},
        actual=footprint["total_bytes"],
    )
    _check(
        checks,
        "footprint.large_file_budget",
        "pass" if not over_large else "fail",
        "largest package files stay within the per-file budget",
        expected={"max_large_file_bytes": max_large_file_bytes},
        actual=over_large,
    )
    _check(
        checks,
        "footprint.dev_only_candidates",
        "warn" if dev_only_candidates else "pass",
        "development-only candidates are reported for ship-profile review",
        actual=len(dev_only_candidates),
    )
    _check(
        checks,
        "footprint.irreversible_actions_zero",
        "pass",
        "package footprint policy is read-only",
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
            "id": "default-read-only-ship-footprint",
            "description": "Read-only package footprint policy for separating repo-local assets from the default ship profile.",
            "mutates_files_by_default": False,
            "external_telemetry": False,
        },
        "budgets": {
            "max_files": max_files,
            "max_total_bytes": max_total_bytes,
            "max_large_file_bytes": max_large_file_bytes,
            "candidate_limit": candidate_limit,
        },
        "summary": {
            "checks": len(checks),
            "warnings": warnings,
            "failures": failures,
            "dev_only_candidates": len(dev_only_candidates),
            "irreversible_actions": 0,
        },
        "package": {
            **footprint,
            "largest_files": largest_files,
        },
        "classifications": classifications,
        "dev_only_candidates": dev_only_candidates,
        "recommendations": [
            "Keep development history repo-local, but exclude it from the default marketplace ship profile where packaging supports it.",
            "Review dev-only candidates before deleting or moving files; this gate never mutates the repository.",
            "Treat tests, docs/plans, docs/archive, docs/architecture, docs/goals-completed, and .github as ship-profile review candidates.",
        ],
        "checks": checks,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Athanor package footprint policy checks.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    parser.add_argument("--max-total-bytes", type=int, default=DEFAULT_MAX_TOTAL_BYTES)
    parser.add_argument("--max-large-file-bytes", type=int, default=DEFAULT_MAX_LARGE_FILE_BYTES)
    parser.add_argument("--candidate-limit", type=int, default=DEFAULT_CANDIDATE_LIMIT)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    if args.max_files < 1:
        print("package footprint policy: --max-files must be >= 1", file=sys.stderr)
        return 2
    if args.max_total_bytes < 1:
        print("package footprint policy: --max-total-bytes must be >= 1", file=sys.stderr)
        return 2
    if args.max_large_file_bytes < 1:
        print("package footprint policy: --max-large-file-bytes must be >= 1", file=sys.stderr)
        return 2
    if args.candidate_limit < 1:
        print("package footprint policy: --candidate-limit must be >= 1", file=sys.stderr)
        return 2

    report = build_report(
        repo_root=args.repo_root,
        max_files=args.max_files,
        max_total_bytes=args.max_total_bytes,
        max_large_file_bytes=args.max_large_file_bytes,
        candidate_limit=args.candidate_limit,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        summary = report["summary"]
        print(
            "package-footprint-policy "
            f"status={report['status']} "
            f"files={report['package']['file_count']} "
            f"bytes={report['package']['total_bytes']} "
            f"candidates={summary['dev_only_candidates']} "
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
