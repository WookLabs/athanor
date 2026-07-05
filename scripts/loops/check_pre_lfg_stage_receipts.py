#!/usr/bin/env python3
"""Check pre-LFG stage receipts for lfg-loop readiness."""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class StageSpec:
    stage: str
    filename: str
    evidence_keywords: tuple[str, ...]


STAGES = (
    StageSpec(
        stage="research",
        filename="R000-research-receipt.md",
        evidence_keywords=(
            "source files",
            "external references",
            "unresolved facts",
            "findings",
        ),
    ),
    StageSpec(
        stage="planning",
        filename="P000-planning-receipt.md",
        evidence_keywords=(
            "accepted plan path",
            "acceptance markers",
            "verification commands",
            "cycle boundaries",
            "known risks",
        ),
    ),
    StageSpec(
        stage="architecture",
        filename="A000-architecture-receipt.md",
        evidence_keywords=(
            "public contracts",
            "cross-module design decisions",
            "rejected alternatives",
            "follow-up constraints",
        ),
    ),
)

NON_CONCRETE_REASONS = {
    "",
    "n/a",
    "na",
    "none",
    "skip",
    "skipped",
    "tbd",
    "todo",
    "unknown",
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold()).strip()


def _extract_field(body: str, field_name: str) -> str | None:
    pattern = rf"(?im)^\s*{re.escape(field_name)}\s*:\s*(.+?)\s*$"
    match = re.search(pattern, body)
    return match.group(1).strip() if match else None


def _extract_reason(body: str) -> str | None:
    for field_name in ("reason", "skip_reason", "skipped_reason"):
        value = _extract_field(body, field_name)
        if value is not None:
            return value
    return None


def _has_concrete_reason(reason: str | None) -> bool:
    if reason is None:
        return False
    normalized = _normalize(reason).strip(".:- ")
    if normalized in NON_CONCRETE_REASONS:
        return False
    return len(normalized) >= 12


def check_stage(loop_dir: Path, spec: StageSpec) -> dict[str, Any]:
    path = loop_dir / "receipts" / spec.filename
    errors: list[str] = []
    missing_keywords: list[str] = []
    receipt_status: str | None = None
    skipped_reason: str | None = None

    checks: dict[str, bool | None] = {
        "exists": path.is_file(),
        "nonempty": False,
        "has_status": False,
        "references_loop_md": False,
        "has_stage_evidence_keywords": False,
        "skipped_has_concrete_reason": None,
    }

    if not checks["exists"]:
        errors.append("missing_receipt")
        return {
            "stage": spec.stage,
            "status": "fail",
            "path": str(path),
            "receipt_status": receipt_status,
            "checks": checks,
            "missing_keywords": list(spec.evidence_keywords),
            "errors": errors,
        }

    body = path.read_text(encoding="utf-8")
    normalized_body = _normalize(body)

    checks["nonempty"] = bool(body.strip())
    if not checks["nonempty"]:
        errors.append("empty_receipt")

    status_value = _extract_field(body, "status")
    if status_value:
        receipt_status = status_value
        checks["has_status"] = True
    else:
        errors.append("missing_status")

    checks["references_loop_md"] = "loop.md" in normalized_body
    if not checks["references_loop_md"]:
        errors.append("missing_loop_md_reference")

    is_skipped = bool(receipt_status and _normalize(receipt_status) == "skipped")

    if is_skipped:
        checks["has_stage_evidence_keywords"] = None
        skipped_reason = _extract_reason(body)
        checks["skipped_has_concrete_reason"] = _has_concrete_reason(skipped_reason)
        if not checks["skipped_has_concrete_reason"]:
            errors.append("skipped_without_concrete_reason")
    else:
        missing_keywords = [
            keyword for keyword in spec.evidence_keywords if keyword not in normalized_body
        ]
        checks["has_stage_evidence_keywords"] = not missing_keywords
        if missing_keywords:
            errors.append("missing_stage_evidence_keywords")

    return {
        "stage": spec.stage,
        "status": "fail" if errors else "pass",
        "path": str(path),
        "receipt_status": receipt_status,
        "checks": checks,
        "missing_keywords": missing_keywords,
        "skipped_reason": skipped_reason,
        "errors": errors,
    }


def check_loop(loop_dir: Path) -> dict[str, Any]:
    stages = [check_stage(loop_dir, spec) for spec in STAGES]
    return {
        "schema_version": 1,
        "status": "pass" if all(stage["status"] == "pass" for stage in stages) else "fail",
        "loop_dir": str(loop_dir),
        "stages": stages,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check pre-LFG research/planning/architecture receipts."
    )
    parser.add_argument("--loop-dir", type=Path, required=True)
    parser.add_argument("--json", action="store_true", help="Emit JSON report.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    report = check_loop(args.loop_dir)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"{report['status']}: {args.loop_dir}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
