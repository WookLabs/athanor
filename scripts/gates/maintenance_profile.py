#!/usr/bin/env python3
"""Composite read-only maintenance profile gate for Athanor."""
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

from scripts.gates.distribution_smoke import (  # noqa: E402
    build_report as build_distribution_report,
)
from scripts.gates.entropy_cleanup import build_report as build_entropy_report  # noqa: E402
from scripts.gates.harness_decision_ledger import (  # noqa: E402
    DEFAULT_LEDGER_ROOT,
    build_report as build_ledger_report,
)
from scripts.gates.native_runtime_probe import (  # noqa: E402
    build_live_profile,
    build_probe as build_native_probe,
)
from scripts.observability.collect_trend_snapshot import (  # noqa: E402
    DEFAULT_HOOK_CATALOG,
    DEFAULT_HOOK_FIXTURES,
    DEFAULT_LOOP_FIXTURES,
    DEFAULT_WORKFLOW_SCENARIOS,
    collect_snapshot,
)


class MaintenanceProfileError(Exception):
    """Raised when a maintenance profile step cannot be evaluated."""


def _iso_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _step(
    *,
    step_id: str,
    title: str,
    command: str,
    status: str,
    summary: dict[str, Any],
    report: dict[str, Any],
    read_only: bool = True,
) -> dict[str, Any]:
    return {
        "id": step_id,
        "title": title,
        "status": status,
        "read_only": read_only,
        "command": command,
        "summary": summary,
        "report": report,
    }


def _status_from_steps(steps: list[dict[str, Any]]) -> str:
    statuses = {step["status"] for step in steps}
    if "fail" in statuses:
        return "fail"
    if "warn" in statuses:
        return "warn"
    return "pass"


def _operator(skip_claude: bool, samples: int, ref_warn_days: int) -> dict[str, str]:
    ci_command = (
        "python scripts/gates/maintenance_profile.py "
        f"{'--skip-claude ' if skip_claude else ''}"
        f"--ref-warn-days {ref_warn_days} --samples {samples} --json"
    ).strip()
    loop_prompt = (
        "/loop weekly: Run `"
        + ci_command
        + "` from the repository root, review the JSON summary, and take no "
        "irreversible actions without explicit user approval."
    )
    return {
        "profile": "weekly-read-only",
        "ci_command": ci_command,
        "loop_prompt": loop_prompt,
    }


def _distribution_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "checks": report.get("summary", {}).get("checks", 0),
        "errors": report.get("summary", {}).get("errors", 0),
        "agent_count": report.get("component_inventory", {}).get("agent_count", 0),
        "always_on_tokens": report.get("cost_surface", {}).get("always_on_tokens", 0),
    }


def _observability_status(snapshot: dict[str, Any]) -> str:
    statuses = [
        snapshot.get("workflow_eval", {}).get("status"),
        snapshot.get("hook_performance", {}).get("status"),
        snapshot.get("durable_loop", {}).get("status"),
    ]
    return "pass" if all(status == "pass" for status in statuses) else "fail"


def _observability_summary(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "workflow_status": snapshot.get("workflow_eval", {}).get("status"),
        "hook_status": snapshot.get("hook_performance", {}).get("status"),
        "loop_status": snapshot.get("durable_loop", {}).get("status"),
        "workflow_mean_score": snapshot.get("workflow_eval", {}).get("mean_score", 0.0),
        "hook_max_budget_ratio": snapshot.get("hook_performance", {}).get(
            "max_budget_ratio",
            0.0,
        ),
    }


def build_report(
    *,
    repo_root: Path,
    skip_claude: bool = False,
    samples: int = 1,
    plan_warn_days: int = 30,
    ref_warn_days: int = 45,
    generated_at: str | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    generated = generated_at or _iso_now()

    entropy = build_entropy_report(
        repo_root=repo_root,
        generated_at=generated,
        plan_warn_days=plan_warn_days,
        ref_warn_days=ref_warn_days,
    )
    distribution, _distribution_exit = build_distribution_report(
        repo_root,
        skip_claude=skip_claude,
        max_always_on_tokens=2200,
        timeout=20,
    )
    snapshot = collect_snapshot(
        workflow_scenario_root=DEFAULT_WORKFLOW_SCENARIOS,
        hook_catalog=DEFAULT_HOOK_CATALOG,
        hook_fixture_root=DEFAULT_HOOK_FIXTURES,
        loop_fixture_root=DEFAULT_LOOP_FIXTURES,
        samples=samples,
        captured_at=generated,
    )
    native_probe = build_native_probe(build_live_profile())
    ledger = build_ledger_report(DEFAULT_LEDGER_ROOT)

    entropy_command = (
        "python scripts/gates/entropy_cleanup.py "
        f"--plan-warn-days {plan_warn_days} --ref-warn-days {ref_warn_days} --json"
    )
    distribution_command = "python scripts/gates/distribution_smoke.py --json"
    if skip_claude:
        distribution_command = "python scripts/gates/distribution_smoke.py --skip-claude --json"

    steps = [
        _step(
            step_id="entropy-cleanup",
            title="Entropy cleanup",
            command=entropy_command,
            status=str(entropy.get("status", "fail")),
            summary=dict(entropy.get("summary", {})),
            report=entropy,
        ),
        _step(
            step_id="distribution-smoke",
            title="Distribution smoke",
            command=distribution_command,
            status=str(distribution.get("status", "fail")),
            summary=_distribution_summary(distribution),
            report=distribution,
        ),
        _step(
            step_id="observability-snapshot",
            title="Observability snapshot",
            command=(
                "python scripts/observability/collect_trend_snapshot.py "
                f"--samples {samples} --json"
            ),
            status=_observability_status(snapshot),
            summary=_observability_summary(snapshot),
            report=snapshot,
        ),
        _step(
            step_id="native-runtime-probe",
            title="Native runtime probe",
            command="python scripts/gates/native_runtime_probe.py --json",
            status=str(native_probe.get("status", "fail")),
            summary=dict(native_probe.get("summary", {})),
            report=native_probe,
        ),
        _step(
            step_id="harness-decision-ledger",
            title="Harness decision ledger",
            command="python scripts/gates/harness_decision_ledger.py --json",
            status=str(ledger.get("status", "fail")),
            summary=dict(ledger.get("summary", {})),
            report=ledger,
        ),
    ]

    warnings = sum(1 for step in steps if step["status"] == "warn")
    failures = sum(1 for step in steps if step["status"] == "fail")
    return {
        "schema_version": 1,
        "status": _status_from_steps(steps),
        "generated_at": generated,
        "profile": {
            "id": "weekly-read-only",
            "description": "Read-only Athanor maintenance profile for CI and Claude /loop use.",
            "mutates_files_by_default": False,
            "external_telemetry": False,
        },
        "summary": {
            "steps": len(steps),
            "passed": sum(1 for step in steps if step["status"] == "pass"),
            "warnings": warnings,
            "failures": failures,
            "irreversible_actions": 0,
        },
        "operator": _operator(skip_claude=skip_claude, samples=samples, ref_warn_days=ref_warn_days),
        "steps": steps,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Athanor maintenance profile.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--skip-claude", action="store_true")
    parser.add_argument("--samples", type=int, default=1)
    parser.add_argument("--plan-warn-days", type=int, default=30)
    parser.add_argument("--ref-warn-days", type=int, default=45)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    if args.samples < 1:
        print("maintenance profile: --samples must be >= 1", file=sys.stderr)
        return 2
    if args.plan_warn_days < 0:
        print("maintenance profile: --plan-warn-days must be >= 0", file=sys.stderr)
        return 2
    if args.ref_warn_days < 0:
        print("maintenance profile: --ref-warn-days must be >= 0", file=sys.stderr)
        return 2
    try:
        report = build_report(
            repo_root=args.repo_root,
            skip_claude=args.skip_claude,
            samples=args.samples,
            plan_warn_days=args.plan_warn_days,
            ref_warn_days=args.ref_warn_days,
        )
    except (OSError, ValueError, MaintenanceProfileError) as exc:
        print(f"maintenance profile: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        summary = report["summary"]
        print(
            "maintenance-profile "
            f"status={report['status']} "
            f"steps={summary['steps']} "
            f"warnings={summary['warnings']} "
            f"failures={summary['failures']}"
        )
        for step in report["steps"]:
            print(f"- {step['id']}: {step['status']}")

    if report["status"] == "fail":
        return 1
    if args.strict and report["status"] == "warn":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

