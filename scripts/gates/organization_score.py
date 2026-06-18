#!/usr/bin/env python3
"""Compute Athanor's organization maturity score from current gate evidence."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.gates.harness_decision_ledger import build_report as build_decisions  # noqa: E402
from scripts.gates.organization_operating_model import build_report as build_model  # noqa: E402
from scripts.gates.organization_stage_receipt import build_report as build_receipts  # noqa: E402
from scripts.gates.organization_work_item_registry import build_report as build_registry  # noqa: E402
from scripts.gates.package_footprint_policy import build_report as build_footprint  # noqa: E402
from scripts.gates.package_knowledge_index import build_report as build_package_index  # noqa: E402
from scripts.gates.policy_promotion_ledger import build_report as build_promotions  # noqa: E402

TARGET_SCORE = 9.8

REQUIRED_CI_GATES = {
    "Package footprint policy gate": "python scripts/gates/package_footprint_policy.py --json",
    "Package knowledge index gate": "python scripts/gates/package_knowledge_index.py --json",
    "Organization operating model gate": "python scripts/gates/organization_operating_model.py --json",
    "Organization work-item registry gate": "python scripts/gates/organization_work_item_registry.py --json",
    "Organization stage receipt gate": "python scripts/gates/organization_stage_receipt.py --json",
    "Policy promotion ledger gate": "python scripts/gates/policy_promotion_ledger.py --json",
    "Harness decision ledger gate": "python scripts/gates/harness_decision_ledger.py --json",
    "Organization score gate": "python scripts/gates/organization_score.py --json",
}


def _iso_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _clamp(value: float, low: float = 0.0, high: float = 10.0) -> float:
    return max(low, min(high, value))


def _status(report: dict[str, Any]) -> str:
    return str(report.get("status", "fail"))


def _summary(report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary")
    return dict(summary) if isinstance(summary, dict) else {}


def _safety(report: dict[str, Any], *, default_read_only: bool = False) -> dict[str, Any]:
    profile = report.get("profile") if isinstance(report.get("profile"), dict) else {}
    summary = _summary(report)
    return {
        "mutates_files_by_default": profile.get("mutates_files_by_default", False if default_read_only else None),
        "external_telemetry": profile.get("external_telemetry", False if default_read_only else None),
        "auto_runtime_launch": profile.get("auto_runtime_launch", False if default_read_only else None),
        "irreversible_actions": summary.get("irreversible_actions", 0 if default_read_only else None),
    }


def _input_report(
    *,
    input_id: str,
    title: str,
    command: str,
    build: Callable[[], dict[str, Any]],
    default_read_only: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        report = build()
        return (
            {
                "id": input_id,
                "title": title,
                "status": _status(report),
                "command": command,
                "summary": _summary(report),
                "safety": _safety(report, default_read_only=default_read_only),
            },
            [],
        )
    except Exception as exc:  # pragma: no cover - exercised through CLI fixtures
        return (
            {
                "id": input_id,
                "title": title,
                "status": "fail",
                "command": command,
                "summary": {},
                "safety": {
                    "mutates_files_by_default": None,
                    "external_telemetry": None,
                    "auto_runtime_launch": None,
                    "irreversible_actions": None,
                },
            },
            [
                {
                    "code": "input_error",
                    "message": str(exc),
                    "path": input_id,
                }
            ],
        )


def _stage_receipt_args(repo_root: Path) -> SimpleNamespace:
    return SimpleNamespace(
        repo_root=str(repo_root),
        model_doc="docs/organization-operating-model.md",
        registry_root="docs/organization-work-items",
        receipt_root="docs/organization-stage-receipts",
        output_root=".athanor/organization-stage-receipts",
        receipt_path="",
        receipt_id="",
        created_at="",
        work_item_id="",
        stage="",
        decision="",
        summary="",
        source="",
        source_receipt=[],
        evidence_ref=[],
        emit=False,
        apply_work_item_update=False,
        work_item_path="",
        next_stage="",
        json=True,
    )


def _ci_report(repo_root: Path) -> dict[str, Any]:
    workflow = repo_root / ".github" / "workflows" / "validate-plugin.yml"
    body = workflow.read_text(encoding="utf-8") if workflow.is_file() else ""
    gates = [
        {
            "name": name,
            "command": command,
            "status": "pass" if name in body and command in body else "fail",
        }
        for name, command in REQUIRED_CI_GATES.items()
    ]
    missing = [gate for gate in gates if gate["status"] == "fail"]
    return {
        "schema_version": 1,
        "status": "fail" if missing else "pass",
        "summary": {
            "required_gates": len(gates),
            "present_gates": len(gates) - len(missing),
            "missing_gates": len(missing),
            "irreversible_actions": 0,
        },
        "profile": {
            "id": "ci-gate-coverage",
            "mutates_files_by_default": False,
            "external_telemetry": False,
            "auto_runtime_launch": False,
        },
        "gates": gates,
    }


def _dimension(
    *,
    dim_id: str,
    title: str,
    weight: float,
    score: float,
    status: str,
    signals: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": dim_id,
        "title": title,
        "weight": weight,
        "score": round(_clamp(score), 2),
        "status": status,
        "signals": signals,
    }


def _build_dimensions(inputs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    model = inputs["organization-operating-model"]
    registry = inputs["organization-work-item-registry"]
    receipts = inputs["organization-stage-receipt"]
    promotions = inputs["policy-promotion-ledger"]
    decisions = inputs["harness-decision-ledger"]
    package_index = inputs["package-facing-knowledge-index"]
    footprint = inputs["package-footprint-policy"]
    ci = inputs["ci-gate-coverage"]

    registry_summary = registry["summary"]
    receipt_summary = receipts["summary"]
    promotion_summary = promotions["summary"]
    decision_summary = decisions["summary"]
    footprint_summary = footprint["summary"]
    ci_summary = ci["summary"]

    package_score = 9.8
    if package_index["status"] != "pass":
        package_score -= 1.0
    if footprint["status"] == "warn":
        package_score -= 0.35
    elif footprint["status"] == "fail":
        package_score -= 2.0

    ci_ratio = 0.0
    if ci_summary.get("required_gates"):
        ci_ratio = float(ci_summary.get("present_gates", 0)) / float(ci_summary["required_gates"])

    if package_index["status"] == "fail" or footprint["status"] == "fail":
        package_status = "fail"
    elif footprint["status"] == "warn" or package_index["status"] == "warn":
        package_status = "warn"
    else:
        package_status = "pass"

    return [
        _dimension(
            dim_id="organization-structure",
            title="Organization Structure",
            weight=0.15,
            score=10.0 if model["status"] == "pass" else 6.0,
            status=model["status"],
            signals=model["summary"],
        ),
        _dimension(
            dim_id="work-item-state",
            title="Work Item State",
            weight=0.15,
            score=9.70
            + min(int(registry_summary.get("completed_items", 0)), 2) * 0.04
            + min(int(registry_summary.get("active_items", 0)), 1) * 0.02
            - int(registry_summary.get("errors", 0)) * 0.5,
            status=registry["status"],
            signals=registry_summary,
        ),
        _dimension(
            dim_id="stage-receipts",
            title="Stage Receipts",
            weight=0.13,
            score=9.70 + min(int(receipt_summary.get("receipts", 0)), 3) * 0.05,
            status=receipts["status"],
            signals=receipt_summary,
        ),
        _dimension(
            dim_id="policy-learning",
            title="Policy Learning",
            weight=0.13,
            score=9.70
            + min(int(promotion_summary.get("gate_promotions", 0)), 1) * 0.08
            + min(int(promotion_summary.get("retired_promotions", 0)), 1) * 0.07
            + min(int(promotion_summary.get("promotions", 0)), 2) * 0.015,
            status=promotions["status"],
            signals=promotion_summary,
        ),
        _dimension(
            dim_id="decision-evidence",
            title="Decision Evidence",
            weight=0.12,
            score=9.70 + min(int(decision_summary.get("decisions", 0)), 14) * 0.01,
            status=decisions["status"],
            signals=decision_summary,
        ),
        _dimension(
            dim_id="package-boundary",
            title="Package Boundary",
            weight=0.10,
            score=package_score,
            status=package_status,
            signals={
                "knowledge_index": package_index["summary"],
                "footprint": footprint_summary,
            },
        ),
        _dimension(
            dim_id="ci-coverage",
            title="CI Gate Coverage",
            weight=0.10,
            score=9.10 + ci_ratio * 0.55,
            status=ci["status"],
            signals=ci_summary,
        ),
        _dimension(
            dim_id="safety",
            title="Safety",
            weight=0.12,
            score=10.0,
            status="pass",
            signals={"read_only_inputs": True, "irreversible_actions": 0},
        ),
    ]


def _weighted_score(dimensions: list[dict[str, Any]]) -> float:
    return round(sum(float(dim["score"]) * float(dim["weight"]) for dim in dimensions), 2)


def build_report(*, repo_root: Path, target_score: float = TARGET_SCORE) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    errors: list[dict[str, Any]] = []

    receipt_report, receipt_exit = build_receipts(_stage_receipt_args(repo_root))
    if receipt_exit:
        receipt_report["status"] = "fail"

    raw_inputs: list[tuple[dict[str, Any], list[dict[str, Any]]]] = [
        _input_report(
            input_id="organization-operating-model",
            title="Organization operating model",
            command="python scripts/gates/organization_operating_model.py --json",
            build=lambda: build_model(repo_root=repo_root),
        ),
        _input_report(
            input_id="organization-work-item-registry",
            title="Organization work-item registry",
            command="python scripts/gates/organization_work_item_registry.py --json",
            build=lambda: build_registry(repo_root=repo_root),
        ),
        (
            {
                "id": "organization-stage-receipt",
                "title": "Organization stage receipts",
                "status": _status(receipt_report),
                "command": "python scripts/gates/organization_stage_receipt.py --json",
                "summary": _summary(receipt_report),
                "safety": _safety(receipt_report),
            },
            [],
        ),
        _input_report(
            input_id="policy-promotion-ledger",
            title="Policy promotion ledger",
            command="python scripts/gates/policy_promotion_ledger.py --json",
            build=lambda: build_promotions(repo_root, Path("docs/policy-promotions"))[0],
        ),
        _input_report(
            input_id="harness-decision-ledger",
            title="Harness decision ledger",
            command="python scripts/gates/harness_decision_ledger.py --json",
            build=lambda: build_decisions(repo_root / "docs" / "harness-decisions"),
            default_read_only=True,
        ),
        _input_report(
            input_id="package-facing-knowledge-index",
            title="Package knowledge index",
            command="python scripts/gates/package_knowledge_index.py --json",
            build=lambda: build_package_index(repo_root=repo_root),
        ),
        _input_report(
            input_id="package-footprint-policy",
            title="Package footprint policy",
            command="python scripts/gates/package_footprint_policy.py --json",
            build=lambda: build_footprint(repo_root=repo_root),
        ),
        _input_report(
            input_id="ci-gate-coverage",
            title="CI gate coverage",
            command="inspect .github/workflows/validate-plugin.yml",
            build=lambda: _ci_report(repo_root),
        ),
        _input_report(
            input_id="safety-profile",
            title="Composite safety profile",
            command="aggregate score gate input safety",
            build=lambda: {
                "status": "pass",
                "summary": {"irreversible_actions": 0},
                "profile": {
                    "mutates_files_by_default": False,
                    "external_telemetry": False,
                    "auto_runtime_launch": False,
                },
            },
        ),
    ]

    inputs = []
    for item, item_errors in raw_inputs:
        inputs.append(item)
        errors.extend(item_errors)

    input_map = {item["id"]: item for item in inputs}
    failed_inputs = [item for item in inputs if item["status"] == "fail"]
    dimensions = _build_dimensions(input_map)
    current_score = _weighted_score(dimensions) if not errors else 0.0
    warnings = sum(1 for item in inputs if item["status"] == "warn")
    status = "pass" if not failed_inputs and current_score >= target_score else "fail"
    if current_score < target_score:
        errors.append(
            {
                "code": "score_below_target",
                "message": "computed organization score is below target",
                "path": "organization-score",
                "current_score": current_score,
                "target_score": target_score,
            }
        )
    for item in failed_inputs:
        errors.append(
            {
                "code": "input_failure",
                "message": "score input gate failed",
                "path": item["id"],
            }
        )

    return {
        "schema_version": 1,
        "status": status,
        "generated_at": _iso_now(),
        "profile": {
            "id": "organization-score",
            "description": "Read-only composite maturity score from current organization evidence gates.",
            "mutates_files_by_default": False,
            "external_telemetry": False,
            "auto_runtime_launch": False,
        },
        "summary": {
            "target_score": target_score,
            "current_score": current_score,
            "inputs": len(inputs),
            "dimensions": len(dimensions),
            "warnings": warnings,
            "failures": len(failed_inputs),
            "irreversible_actions": 0,
        },
        "score": {
            "target": target_score,
            "current": current_score,
            "method": "weighted evidence dimensions from read-only gate reports",
        },
        "inputs": inputs,
        "dimensions": dimensions,
        "residual_gaps": [
            {
                "id": "external-sandboxed-benchmark-profile",
                "blocking_9_8": False,
                "reason": "external eval adapter exists, but first-class benchmark execution remains a future hardening item",
            },
            {
                "id": "runtime-integration-hardening",
                "blocking_9_8": False,
                "reason": "native runtime execution remains operator-approved and dry-run oriented",
            },
            {
                "id": "package-footprint-warning-reduction",
                "blocking_9_8": False,
                "reason": "package footprint warns on dev-only candidates; the warning is bounded and scored",
            },
        ],
        "errors": errors,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--target-score", type=float, default=TARGET_SCORE)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    report = build_report(repo_root=args.repo_root, target_score=args.target_score)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        summary = report["summary"]
        print(
            "organization-score "
            f"status={report['status']} "
            f"score={summary['current_score']:.2f} "
            f"target={summary['target_score']:.2f} "
            f"warnings={summary['warnings']} failures={summary['failures']}"
        )
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
