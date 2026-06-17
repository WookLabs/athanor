#!/usr/bin/env python3
"""Report local Athanor observability trends from snapshot JSONL history."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_HISTORY = REPO_ROOT / ".athanor" / "observability" / "trends.jsonl"


def load_history(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ValueError(f"history does not exist: {path}")
    records: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"malformed JSONL line {lineno}: {exc.msg}") from exc
        if not isinstance(item, dict):
            raise ValueError(f"malformed JSONL line {lineno}: record is not an object")
        records.append(item)
    if not records:
        raise ValueError(f"history has no snapshots: {path}")
    return records


def _delta(first: Any, latest: Any) -> float:
    if not isinstance(first, (int, float)) or not isinstance(latest, (int, float)):
        return 0.0
    return round(float(latest) - float(first), 3)


def _latest_slowest_hook(latest: dict[str, Any]) -> str | None:
    hooks = latest.get("hook_performance", {}).get("hooks", [])
    if not isinstance(hooks, list):
        return None
    candidates = [hook for hook in hooks if isinstance(hook, dict)]
    if not candidates:
        return None
    slowest = max(candidates, key=lambda hook: hook.get("budget_ratio", 0))
    hook_id = slowest.get("id")
    return hook_id if isinstance(hook_id, str) else None


def build_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    first = records[0]
    latest = records[-1]
    statuses = latest.get("durable_loop", {}).get("decision_statuses", {})
    if not isinstance(statuses, dict):
        statuses = {}
    failure_or_escalation = int(statuses.get("failure", 0)) + int(
        statuses.get("escalated", 0)
    )
    failed = latest.get("workflow_eval", {}).get("failed_scenarios", [])
    if not isinstance(failed, list):
        failed = []

    concerns: list[str] = []
    if failed:
        concerns.append(f"workflow failed scenarios: {', '.join(str(item) for item in failed)}")
    latest_ratio = latest.get("hook_performance", {}).get("max_budget_ratio", 0.0)
    if isinstance(latest_ratio, (int, float)) and latest_ratio >= 0.8:
        concerns.append(f"hook budget ratio high: {latest_ratio}")
    if failure_or_escalation:
        concerns.append(f"durable loop failure/escalation count: {failure_or_escalation}")

    actions = latest.get("durable_loop", {}).get("actions", {})
    if not isinstance(actions, dict):
        actions = {}
    return {
        "schema_version": 1,
        "snapshot_count": len(records),
        "git": {
            "first_sha": str(first.get("git", {}).get("sha", "")),
            "latest_sha": str(latest.get("git", {}).get("sha", "")),
            "latest_branch": str(latest.get("git", {}).get("branch", "")),
        },
        "workflow_eval": {
            "latest_mean_score": float(
                latest.get("workflow_eval", {}).get("mean_score", 0.0)
            ),
            "mean_score_delta": _delta(
                first.get("workflow_eval", {}).get("mean_score"),
                latest.get("workflow_eval", {}).get("mean_score"),
            ),
            "latest_failed_scenarios": [str(item) for item in failed],
        },
        "hook_performance": {
            "latest_max_budget_ratio": float(latest_ratio)
            if isinstance(latest_ratio, (int, float))
            else 0.0,
            "max_budget_ratio_delta": _delta(
                first.get("hook_performance", {}).get("max_budget_ratio"),
                latest.get("hook_performance", {}).get("max_budget_ratio"),
            ),
            "slowest_latest_hook": _latest_slowest_hook(latest),
        },
        "durable_loop": {
            "latest_actions": {str(key): int(value) for key, value in actions.items()},
            "latest_decision_statuses": {
                str(key): int(value) for key, value in statuses.items()
            },
            "failure_or_escalation_count": failure_or_escalation,
        },
        "concerns": concerns,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Report Athanor observability trends.")
    parser.add_argument("--history", type=Path, default=DEFAULT_HISTORY)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    try:
        report = build_report(load_history(args.history))
    except ValueError as exc:
        print(f"observability trends: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            f"snapshots={report['snapshot_count']} "
            f"workflow_delta={report['workflow_eval']['mean_score_delta']} "
            f"hook_ratio={report['hook_performance']['latest_max_budget_ratio']}"
        )
        for concern in report["concerns"]:
            print(f"concern: {concern}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
