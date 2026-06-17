#!/usr/bin/env python3
"""Collect one local Athanor observability trend snapshot."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evals.run_workflow_scenarios import evaluate_root as evaluate_workflow_root
from scripts.gates.check_hook_performance_budget import check_budgets
from scripts.loops.run_goal_loop_fixtures import evaluate_root as evaluate_loop_root

DEFAULT_HISTORY = REPO_ROOT / ".athanor" / "observability" / "trends.jsonl"
DEFAULT_WORKFLOW_SCENARIOS = REPO_ROOT / "tests" / "fixtures" / "workflow_evals"
DEFAULT_HOOK_CATALOG = REPO_ROOT / "hooks" / "catalog.json"
DEFAULT_HOOK_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "hooks"
DEFAULT_LOOP_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "durable_loops"


def _git_value(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def _workflow_summary(report: dict[str, Any]) -> dict[str, Any]:
    scenarios = report.get("scenarios", [])
    scenario_items = [item for item in scenarios if isinstance(item, dict)]
    scores = [float(item.get("score", 0)) for item in scenario_items]
    failed = [
        str(item.get("id", "<missing-id>"))
        for item in scenario_items
        if item.get("status") != "pass"
    ]
    return {
        "status": str(report.get("status", "fail")),
        "scenario_count": len(scenario_items),
        "min_score": round(min(scores), 3) if scores else 0.0,
        "mean_score": round(sum(scores) / len(scores), 3) if scores else 0.0,
        "failed_scenarios": failed,
    }


def _hook_summary(report: dict[str, Any]) -> dict[str, Any]:
    hooks = []
    for item in report.get("hooks", []):
        if not isinstance(item, dict):
            continue
        budget = item.get("budget_ms")
        max_ms = item.get("max_ms")
        ratio = 0.0
        if (
            isinstance(budget, (int, float))
            and budget > 0
            and isinstance(max_ms, (int, float))
        ):
            ratio = round(float(max_ms) / float(budget), 3)
        hooks.append(
            {
                "id": str(item.get("id", "<missing-id>")),
                "event": str(item.get("event", "")),
                "max_ms": max_ms if isinstance(max_ms, (int, float)) else None,
                "budget_ms": budget if isinstance(budget, (int, float)) else None,
                "budget_ratio": ratio,
                "status": str(item.get("status", "fail")),
            }
        )
    return {
        "status": str(report.get("status", "fail")),
        "hook_count": len(hooks),
        "max_budget_ratio": round(
            max((hook["budget_ratio"] for hook in hooks), default=0.0),
            3,
        ),
        "hooks": hooks,
    }


def _loop_summary(report: dict[str, Any]) -> dict[str, Any]:
    actions: Counter[str] = Counter()
    statuses: Counter[str] = Counter()
    scenarios = report.get("scenarios", [])
    scenario_items = [item for item in scenarios if isinstance(item, dict)]
    for item in scenario_items:
        action = item.get("action")
        status = item.get("decision_status")
        if isinstance(action, str) and action:
            actions[action] += 1
        if isinstance(status, str) and status:
            statuses[status] += 1
    return {
        "status": str(report.get("status", "fail")),
        "scenario_count": len(scenario_items),
        "actions": dict(sorted(actions.items())),
        "decision_statuses": dict(sorted(statuses.items())),
    }


def collect_snapshot(
    *,
    workflow_scenario_root: Path,
    hook_catalog: Path,
    hook_fixture_root: Path,
    loop_fixture_root: Path,
    samples: int,
    captured_at: str | None = None,
) -> dict[str, Any]:
    workflow_report = evaluate_workflow_root(workflow_scenario_root)
    hook_report = check_budgets(
        catalog_path=hook_catalog,
        fixture_root=hook_fixture_root,
        samples=samples,
        overrides={},
    )
    loop_report = evaluate_loop_root(loop_fixture_root)
    return {
        "schema_version": 1,
        "captured_at": captured_at
        or datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "git": {
            "branch": _git_value("branch", "--show-current"),
            "sha": _git_value("rev-parse", "--short", "HEAD"),
        },
        "workflow_eval": _workflow_summary(workflow_report),
        "hook_performance": _hook_summary(hook_report),
        "durable_loop": _loop_summary(loop_report),
    }


def append_snapshot(path: Path, snapshot: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(snapshot, sort_keys=True) + "\n")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect one Athanor observability trend snapshot."
    )
    parser.add_argument("--workflow-scenario-root", type=Path, default=DEFAULT_WORKFLOW_SCENARIOS)
    parser.add_argument("--hook-catalog", type=Path, default=DEFAULT_HOOK_CATALOG)
    parser.add_argument("--hook-fixture-root", type=Path, default=DEFAULT_HOOK_FIXTURES)
    parser.add_argument("--loop-fixture-root", type=Path, default=DEFAULT_LOOP_FIXTURES)
    parser.add_argument("--history", type=Path, default=DEFAULT_HISTORY)
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--append", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    if args.samples < 1:
        print("observability snapshot: --samples must be >= 1", file=sys.stderr)
        return 2
    try:
        snapshot = collect_snapshot(
            workflow_scenario_root=args.workflow_scenario_root,
            hook_catalog=args.hook_catalog,
            hook_fixture_root=args.hook_fixture_root,
            loop_fixture_root=args.loop_fixture_root,
            samples=args.samples,
        )
    except ValueError as exc:
        print(f"observability snapshot: {exc}", file=sys.stderr)
        return 2
    if args.append:
        append_snapshot(args.history, snapshot)
    if args.json:
        print(json.dumps(snapshot, indent=2, sort_keys=True))
    else:
        print(
            "snapshot "
            f"workflow={snapshot['workflow_eval']['status']} "
            f"hooks={snapshot['hook_performance']['status']} "
            f"loops={snapshot['durable_loop']['status']}"
        )
    statuses = [
        snapshot["workflow_eval"]["status"],
        snapshot["hook_performance"]["status"],
        snapshot["durable_loop"]["status"],
    ]
    return 0 if all(status == "pass" for status in statuses) else 1


if __name__ == "__main__":
    raise SystemExit(main())
