# P10 Live Trace Trends Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add local observability snapshots, trend reports, and trace-to-scenario promotion so Athanor's existing eval, hook, and loop evidence becomes trendable without expanding runtime defaults.

**Architecture:** Keep P10 as explicit CLI behavior under `scripts/observability/`. The collector imports existing P6/P7/P5 runners, writes summarized JSONL history under `.athanor/observability/`, the reporter reads that history, and the promotion command converts validated trace JSONL into deterministic scenario fixtures.

**Tech Stack:** Python standard library, existing Athanor Python runners, JSON Schema draft-07, pytest.

---

## File Map

- Create: `scripts/observability/__init__.py`
  - Marks observability helpers as an importable package.
- Create: `scripts/observability/collect_trend_snapshot.py`
  - Collects one local snapshot from workflow eval, hook budget, and durable loop reports.
- Create: `scripts/observability/report_trends.py`
  - Reads snapshot JSONL history and emits a compact trend report.
- Create: `scripts/observability/promote_trace_scenario.py`
  - Converts a validated workflow trace JSONL into a scenario fixture.
- Create: `schemas/observability-trend-snapshot.schema.json`
  - Locks the snapshot report shape.
- Create: `schemas/observability-trend-report.schema.json`
  - Locks the trend report shape.
- Create: `tests/test_regression_observability_trends.py`
  - Covers collector, reporter, schema validation, and promotion behavior.
- Create: `docs/observability-trends.md`
  - Documents P10 usage and boundaries.
- Modify: `.github/workflows/validate-plugin.yml`
  - Adds a named observability snapshot gate.
- Modify: `CHANGELOG.md`
  - Adds P10 release story.
- Modify: `tests/test_regression_v019_release_story.py`
  - Locks CI and changelog documentation.
- Modify: `docs/plans/2026-06-17-p10-live-trace-trends-plan.md`
  - Track task progress.

## Task 1: Snapshot Collector Contract

**Files:**
- Create: `tests/test_regression_observability_trends.py`
- Create: `schemas/observability-trend-snapshot.schema.json`
- Create: `scripts/observability/__init__.py`
- Create: `scripts/observability/collect_trend_snapshot.py`
- Modify: `docs/plans/2026-06-17-p10-live-trace-trends-plan.md`

- [ ] **Step 1: Write failing collector tests**

Create `tests/test_regression_observability_trends.py` with:

```python
"""Regression tests for local observability trend tooling."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
COLLECTOR = REPO_ROOT / "scripts" / "observability" / "collect_trend_snapshot.py"
SNAPSHOT_SCHEMA = REPO_ROOT / "schemas" / "observability-trend-snapshot.schema.json"


def _run(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )


def test_collect_snapshot_cli_emits_expected_summaries() -> None:
    proc = _run(COLLECTOR, "--json", "--samples", "1")

    assert proc.returncode == 0, proc.stderr
    snapshot = json.loads(proc.stdout)
    jsonschema.validate(snapshot, json.loads(SNAPSHOT_SCHEMA.read_text(encoding="utf-8")))
    assert snapshot["schema_version"] == 1
    assert snapshot["workflow_eval"]["status"] == "pass"
    assert snapshot["workflow_eval"]["scenario_count"] >= 4
    assert snapshot["workflow_eval"]["mean_score"] == 1.0
    hook_ids = {hook["id"] for hook in snapshot["hook_performance"]["hooks"]}
    assert "posttool-evidence-sniffer" in hook_ids
    assert snapshot["hook_performance"]["max_budget_ratio"] >= 0
    assert snapshot["durable_loop"]["actions"]["stop_no_progress"] == 1
    assert snapshot["durable_loop"]["decision_statuses"]["escalated"] == 1


def test_collect_snapshot_append_writes_one_jsonl_record(tmp_path: Path) -> None:
    history = tmp_path / "trends.jsonl"

    proc = _run(
        COLLECTOR,
        "--json",
        "--append",
        "--history",
        str(history),
        "--samples",
        "1",
    )

    assert proc.returncode == 0, proc.stderr
    stdout_snapshot = json.loads(proc.stdout)
    records = [
        json.loads(line)
        for line in history.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert records == [stdout_snapshot]
```

- [ ] **Step 2: Run collector tests to verify RED**

Run:

```bash
python -m pytest tests/test_regression_observability_trends.py::test_collect_snapshot_cli_emits_expected_summaries tests/test_regression_observability_trends.py::test_collect_snapshot_append_writes_one_jsonl_record -q
```

Expected: FAIL because `scripts/observability/collect_trend_snapshot.py` and the snapshot schema do not exist.

- [ ] **Step 3: Add snapshot schema**

Create `schemas/observability-trend-snapshot.schema.json` with draft-07 schema:

```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "title": "Athanor observability trend snapshot",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "captured_at",
    "git",
    "workflow_eval",
    "hook_performance",
    "durable_loop"
  ],
  "properties": {
    "schema_version": { "const": 1 },
    "captured_at": { "type": "string", "minLength": 1 },
    "git": {
      "type": "object",
      "additionalProperties": false,
      "required": ["branch", "sha"],
      "properties": {
        "branch": { "type": "string" },
        "sha": { "type": "string" }
      }
    },
    "workflow_eval": {
      "type": "object",
      "additionalProperties": false,
      "required": ["status", "scenario_count", "min_score", "mean_score", "failed_scenarios"],
      "properties": {
        "status": { "type": "string" },
        "scenario_count": { "type": "integer", "minimum": 0 },
        "min_score": { "type": "number" },
        "mean_score": { "type": "number" },
        "failed_scenarios": { "type": "array", "items": { "type": "string" } }
      }
    },
    "hook_performance": {
      "type": "object",
      "additionalProperties": false,
      "required": ["status", "hook_count", "max_budget_ratio", "hooks"],
      "properties": {
        "status": { "type": "string" },
        "hook_count": { "type": "integer", "minimum": 0 },
        "max_budget_ratio": { "type": "number" },
        "hooks": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["id", "event", "max_ms", "budget_ms", "budget_ratio", "status"],
            "properties": {
              "id": { "type": "string" },
              "event": { "type": "string" },
              "max_ms": { "type": ["number", "null"] },
              "budget_ms": { "type": ["number", "integer", "null"] },
              "budget_ratio": { "type": "number" },
              "status": { "type": "string" }
            }
          }
        }
      }
    },
    "durable_loop": {
      "type": "object",
      "additionalProperties": false,
      "required": ["status", "scenario_count", "actions", "decision_statuses"],
      "properties": {
        "status": { "type": "string" },
        "scenario_count": { "type": "integer", "minimum": 0 },
        "actions": { "type": "object", "additionalProperties": { "type": "integer" } },
        "decision_statuses": { "type": "object", "additionalProperties": { "type": "integer" } }
      }
    }
  }
}
```

- [ ] **Step 4: Implement collector**

Create `scripts/observability/__init__.py`:

```python
"""Local observability helpers for Athanor."""
```

Create `scripts/observability/collect_trend_snapshot.py`:

```python
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
    scores = [float(item.get("score", 0)) for item in scenarios if isinstance(item, dict)]
    failed = [
        str(item.get("id", "<missing-id>"))
        for item in scenarios
        if isinstance(item, dict) and item.get("status") != "pass"
    ]
    return {
        "status": str(report.get("status", "fail")),
        "scenario_count": len(scenarios),
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
        if isinstance(budget, (int, float)) and budget > 0 and isinstance(max_ms, (int, float)):
            ratio = round(float(max_ms) / float(budget), 3)
        hooks.append({
            "id": str(item.get("id", "<missing-id>")),
            "event": str(item.get("event", "")),
            "max_ms": max_ms if isinstance(max_ms, (int, float)) else None,
            "budget_ms": budget if isinstance(budget, (int, float)) else None,
            "budget_ratio": ratio,
            "status": str(item.get("status", "fail")),
        })
    return {
        "status": str(report.get("status", "fail")),
        "hook_count": len(hooks),
        "max_budget_ratio": round(max((hook["budget_ratio"] for hook in hooks), default=0.0), 3),
        "hooks": hooks,
    }


def _loop_summary(report: dict[str, Any]) -> dict[str, Any]:
    actions: Counter[str] = Counter()
    statuses: Counter[str] = Counter()
    scenarios = report.get("scenarios", [])
    for item in scenarios:
        if not isinstance(item, dict):
            continue
        action = item.get("action")
        status = item.get("decision_status")
        if isinstance(action, str) and action:
            actions[action] += 1
        if isinstance(status, str) and status:
            statuses[status] += 1
    return {
        "status": str(report.get("status", "fail")),
        "scenario_count": len(scenarios),
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
        "captured_at": captured_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
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
    parser = argparse.ArgumentParser(description="Collect one Athanor observability trend snapshot.")
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
```

- [ ] **Step 5: Run collector tests to verify GREEN**

Run:

```bash
python -m pytest tests/test_regression_observability_trends.py::test_collect_snapshot_cli_emits_expected_summaries tests/test_regression_observability_trends.py::test_collect_snapshot_append_writes_one_jsonl_record -q
```

Expected: PASS.

- [ ] **Step 6: Commit collector**

```bash
git add scripts/observability/__init__.py scripts/observability/collect_trend_snapshot.py schemas/observability-trend-snapshot.schema.json tests/test_regression_observability_trends.py docs/plans/2026-06-17-p10-live-trace-trends-plan.md
git commit -m "feat: collect local observability trend snapshots"
```

## Task 2: Trend Reporter

**Files:**
- Modify: `tests/test_regression_observability_trends.py`
- Create: `schemas/observability-trend-report.schema.json`
- Create: `scripts/observability/report_trends.py`
- Modify: `docs/plans/2026-06-17-p10-live-trace-trends-plan.md`

- [ ] **Step 1: Write failing trend reporter tests**

Append to `tests/test_regression_observability_trends.py`:

```python
REPORTER = REPO_ROOT / "scripts" / "observability" / "report_trends.py"
TREND_SCHEMA = REPO_ROOT / "schemas" / "observability-trend-report.schema.json"


def _snapshot(
    *,
    sha: str,
    mean_score: float,
    failed_scenarios: list[str],
    hook_ratio: float,
    hook_id: str = "posttool-evidence-sniffer",
    actions: dict[str, int] | None = None,
    statuses: dict[str, int] | None = None,
) -> dict:
    return {
        "schema_version": 1,
        "captured_at": f"2026-06-17T12:00:0{len(failed_scenarios)}Z",
        "git": {"branch": "test", "sha": sha},
        "workflow_eval": {
            "status": "pass" if not failed_scenarios else "fail",
            "scenario_count": 4,
            "min_score": mean_score,
            "mean_score": mean_score,
            "failed_scenarios": failed_scenarios,
        },
        "hook_performance": {
            "status": "pass",
            "hook_count": 1,
            "max_budget_ratio": hook_ratio,
            "hooks": [
                {
                    "id": hook_id,
                    "event": "PostToolUse",
                    "max_ms": hook_ratio * 500,
                    "budget_ms": 500,
                    "budget_ratio": hook_ratio,
                    "status": "pass",
                }
            ],
        },
        "durable_loop": {
            "status": "pass",
            "scenario_count": 5,
            "actions": actions or {"run_tier1_check": 1},
            "decision_statuses": statuses or {"pass": 1},
        },
    }


def test_report_trends_detects_score_latency_and_loop_deltas(tmp_path: Path) -> None:
    history = tmp_path / "trends.jsonl"
    history.write_text(
        "\n".join(
            json.dumps(item, sort_keys=True)
            for item in [
                _snapshot(sha="aaa1111", mean_score=1.0, failed_scenarios=[], hook_ratio=0.10),
                _snapshot(
                    sha="bbb2222",
                    mean_score=0.75,
                    failed_scenarios=["work-missing-evidence-escalates"],
                    hook_ratio=0.40,
                    actions={"stop_no_progress": 2},
                    statuses={"failure": 1, "escalated": 2},
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    proc = _run(REPORTER, "--history", str(history), "--json")

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    jsonschema.validate(report, json.loads(TREND_SCHEMA.read_text(encoding="utf-8")))
    assert report["schema_version"] == 1
    assert report["snapshot_count"] == 2
    assert report["workflow_eval"]["mean_score_delta"] == -0.25
    assert report["workflow_eval"]["latest_failed_scenarios"] == [
        "work-missing-evidence-escalates"
    ]
    assert report["hook_performance"]["max_budget_ratio_delta"] == 0.3
    assert report["hook_performance"]["slowest_latest_hook"] == "posttool-evidence-sniffer"
    assert report["durable_loop"]["failure_or_escalation_count"] == 3
    assert report["durable_loop"]["latest_actions"]["stop_no_progress"] == 2


def test_report_trends_exits_two_for_missing_history(tmp_path: Path) -> None:
    proc = _run(REPORTER, "--history", str(tmp_path / "missing.jsonl"), "--json")

    assert proc.returncode == 2
    assert "history does not exist" in proc.stderr
```

- [ ] **Step 2: Run reporter tests to verify RED**

Run:

```bash
python -m pytest tests/test_regression_observability_trends.py::test_report_trends_detects_score_latency_and_loop_deltas tests/test_regression_observability_trends.py::test_report_trends_exits_two_for_missing_history -q
```

Expected: FAIL because `report_trends.py` and report schema do not exist.

- [ ] **Step 3: Add trend report schema**

Create `schemas/observability-trend-report.schema.json` with:

```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "title": "Athanor observability trend report",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "snapshot_count",
    "git",
    "workflow_eval",
    "hook_performance",
    "durable_loop",
    "concerns"
  ],
  "properties": {
    "schema_version": { "const": 1 },
    "snapshot_count": { "type": "integer", "minimum": 0 },
    "git": {
      "type": "object",
      "additionalProperties": false,
      "required": ["first_sha", "latest_sha", "latest_branch"],
      "properties": {
        "first_sha": { "type": "string" },
        "latest_sha": { "type": "string" },
        "latest_branch": { "type": "string" }
      }
    },
    "workflow_eval": {
      "type": "object",
      "additionalProperties": false,
      "required": ["latest_mean_score", "mean_score_delta", "latest_failed_scenarios"],
      "properties": {
        "latest_mean_score": { "type": "number" },
        "mean_score_delta": { "type": "number" },
        "latest_failed_scenarios": { "type": "array", "items": { "type": "string" } }
      }
    },
    "hook_performance": {
      "type": "object",
      "additionalProperties": false,
      "required": ["latest_max_budget_ratio", "max_budget_ratio_delta", "slowest_latest_hook"],
      "properties": {
        "latest_max_budget_ratio": { "type": "number" },
        "max_budget_ratio_delta": { "type": "number" },
        "slowest_latest_hook": { "type": ["string", "null"] }
      }
    },
    "durable_loop": {
      "type": "object",
      "additionalProperties": false,
      "required": ["latest_actions", "latest_decision_statuses", "failure_or_escalation_count"],
      "properties": {
        "latest_actions": { "type": "object", "additionalProperties": { "type": "integer" } },
        "latest_decision_statuses": { "type": "object", "additionalProperties": { "type": "integer" } },
        "failure_or_escalation_count": { "type": "integer", "minimum": 0 }
      }
    },
    "concerns": { "type": "array", "items": { "type": "string" } }
  }
}
```

- [ ] **Step 4: Implement trend reporter**

Create `scripts/observability/report_trends.py` with:

```python
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


def build_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    first = records[0]
    latest = records[-1]
    latest_hooks = latest.get("hook_performance", {}).get("hooks", [])
    slowest = None
    if isinstance(latest_hooks, list) and latest_hooks:
        sorted_hooks = sorted(
            [hook for hook in latest_hooks if isinstance(hook, dict)],
            key=lambda hook: hook.get("budget_ratio", 0),
            reverse=True,
        )
        if sorted_hooks:
            slowest = sorted_hooks[0].get("id")
    statuses = latest.get("durable_loop", {}).get("decision_statuses", {})
    failure_or_escalation = 0
    if isinstance(statuses, dict):
        failure_or_escalation = int(statuses.get("failure", 0)) + int(statuses.get("escalated", 0))
    concerns: list[str] = []
    failed = latest.get("workflow_eval", {}).get("failed_scenarios", [])
    if isinstance(failed, list) and failed:
        concerns.append(f"workflow failed scenarios: {', '.join(str(item) for item in failed)}")
    latest_ratio = latest.get("hook_performance", {}).get("max_budget_ratio", 0.0)
    if isinstance(latest_ratio, (int, float)) and latest_ratio >= 0.8:
        concerns.append(f"hook budget ratio high: {latest_ratio}")
    if failure_or_escalation:
        concerns.append(f"durable loop failure/escalation count: {failure_or_escalation}")
    return {
        "schema_version": 1,
        "snapshot_count": len(records),
        "git": {
            "first_sha": str(first.get("git", {}).get("sha", "")),
            "latest_sha": str(latest.get("git", {}).get("sha", "")),
            "latest_branch": str(latest.get("git", {}).get("branch", "")),
        },
        "workflow_eval": {
            "latest_mean_score": float(latest.get("workflow_eval", {}).get("mean_score", 0.0)),
            "mean_score_delta": _delta(
                first.get("workflow_eval", {}).get("mean_score"),
                latest.get("workflow_eval", {}).get("mean_score"),
            ),
            "latest_failed_scenarios": list(latest.get("workflow_eval", {}).get("failed_scenarios", [])),
        },
        "hook_performance": {
            "latest_max_budget_ratio": float(latest.get("hook_performance", {}).get("max_budget_ratio", 0.0)),
            "max_budget_ratio_delta": _delta(
                first.get("hook_performance", {}).get("max_budget_ratio"),
                latest.get("hook_performance", {}).get("max_budget_ratio"),
            ),
            "slowest_latest_hook": slowest,
        },
        "durable_loop": {
            "latest_actions": dict(latest.get("durable_loop", {}).get("actions", {})),
            "latest_decision_statuses": dict(statuses if isinstance(statuses, dict) else {}),
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
```

- [ ] **Step 5: Run reporter tests to verify GREEN**

Run:

```bash
python -m pytest tests/test_regression_observability_trends.py::test_report_trends_detects_score_latency_and_loop_deltas tests/test_regression_observability_trends.py::test_report_trends_exits_two_for_missing_history -q
```

Expected: PASS.

- [ ] **Step 6: Commit reporter**

```bash
git add scripts/observability/report_trends.py schemas/observability-trend-report.schema.json tests/test_regression_observability_trends.py docs/plans/2026-06-17-p10-live-trace-trends-plan.md
git commit -m "feat: report local observability trends"
```

## Task 3: Trace Promotion

**Files:**
- Modify: `tests/test_regression_observability_trends.py`
- Create: `scripts/observability/promote_trace_scenario.py`
- Modify: `docs/plans/2026-06-17-p10-live-trace-trends-plan.md`

- [ ] **Step 1: Write failing promotion tests**

Append to `tests/test_regression_observability_trends.py`:

```python
PROMOTER = REPO_ROOT / "scripts" / "observability" / "promote_trace_scenario.py"
EVAL_RUNNER = REPO_ROOT / "scripts" / "evals" / "run_workflow_scenarios.py"


def _trace_record(seq: int, event_type: str, status: str, *, references: list[str] | None = None) -> dict:
    record = {
        "schema_version": 1,
        "trace_id": "live-trace-demo",
        "seq": seq,
        "phase": "work",
        "event_type": event_type,
        "actor": "leader" if event_type.startswith("workflow.") else "gate",
        "status": status,
        "message": f"{event_type} {status}",
    }
    if references is not None:
        record["references"] = references
    return record


def test_promote_trace_scenario_writes_valid_fixture(tmp_path: Path) -> None:
    trace_path = tmp_path / "trace.jsonl"
    output = tmp_path / "promoted.json"
    records = [
        _trace_record(1, "workflow.started", "started"),
        _trace_record(
            2,
            "verifier.result",
            "pass",
            references=[".athanor/sessions/live/.hook-state/test-evidence.jsonl"],
        ),
        _trace_record(3, "workflow.finished", "pass"),
    ]
    trace_path.write_text(
        "\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n",
        encoding="utf-8",
    )

    proc = _run(
        PROMOTER,
        "--trace",
        str(trace_path),
        "--scenario-id",
        "promoted-work-trace",
        "--description",
        "Promoted work trace",
        "--output",
        str(output),
        "--json",
    )

    assert proc.returncode == 0, proc.stderr
    promoted = json.loads(output.read_text(encoding="utf-8"))
    assert promoted["schema_version"] == 1
    assert promoted["scenarios"][0]["id"] == "promoted-work-trace"
    assert any(
        grader["kind"] == "require_reference" and grader["reference"] == "test-evidence.jsonl"
        for grader in promoted["scenarios"][0]["graders"]
    )
    eval_proc = _run(EVAL_RUNNER, "--scenario-root", str(output), "--json")
    assert eval_proc.returncode == 0, eval_proc.stderr


def test_promote_trace_scenario_refuses_existing_output_without_force(tmp_path: Path) -> None:
    trace_path = tmp_path / "trace.jsonl"
    output = tmp_path / "promoted.json"
    trace_path.write_text(
        json.dumps(_trace_record(1, "workflow.started", "started")) + "\n"
        + json.dumps(_trace_record(2, "workflow.finished", "pass")) + "\n",
        encoding="utf-8",
    )
    output.write_text("{}", encoding="utf-8")

    proc = _run(
        PROMOTER,
        "--trace",
        str(trace_path),
        "--scenario-id",
        "existing-output",
        "--description",
        "Existing output",
        "--output",
        str(output),
    )

    assert proc.returncode == 2
    assert "already exists" in proc.stderr
```

- [ ] **Step 2: Run promotion tests to verify RED**

Run:

```bash
python -m pytest tests/test_regression_observability_trends.py::test_promote_trace_scenario_writes_valid_fixture tests/test_regression_observability_trends.py::test_promote_trace_scenario_refuses_existing_output_without_force -q
```

Expected: FAIL because `promote_trace_scenario.py` does not exist.

- [ ] **Step 3: Implement trace promotion**

Create `scripts/observability/promote_trace_scenario.py` with:

```python
#!/usr/bin/env python3
"""Promote a validated workflow trace JSONL file into a scenario fixture."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evals.workflow_trace import load_trace


def _matches(record: dict[str, Any], event_type: str) -> dict[str, str]:
    return {"event_type": event_type, "phase": str(record["phase"])}


def build_scenario(*, trace: list[dict[str, Any]], scenario_id: str, description: str) -> dict[str, Any]:
    if not trace:
        raise ValueError("trace has no records")
    started = next((item for item in trace if item["event_type"] == "workflow.started"), None)
    finished = next((item for item in reversed(trace) if item["event_type"] == "workflow.finished"), None)
    if started is None:
        raise ValueError("trace must contain workflow.started")
    if finished is None:
        raise ValueError("trace must contain workflow.finished")
    graders: list[dict[str, Any]] = [
        {
            "id": "workflow-started",
            "kind": "require_event",
            "match": _matches(started, "workflow.started"),
        },
        {
            "id": "workflow-finished",
            "kind": "require_event",
            "match": _matches(finished, "workflow.finished"),
        },
        {
            "id": "started-before-finished",
            "kind": "require_order",
            "before": _matches(started, "workflow.started"),
            "after": _matches(finished, "workflow.finished"),
        },
    ]
    escalation = next((item for item in trace if item["event_type"] == "escalation.required"), None)
    if escalation is not None:
        graders.append({
            "id": "escalation-recorded",
            "kind": "require_event",
            "match": _matches(escalation, "escalation.required"),
        })
    verifier = next(
        (
            item
            for item in trace
            if item["event_type"] == "verifier.result" and item.get("references")
        ),
        None,
    )
    if verifier is not None:
        reference = Path(str(verifier["references"][0])).name
        graders.append({
            "id": "verifier-reference-present",
            "kind": "require_reference",
            "match": _matches(verifier, "verifier.result"),
            "reference": reference,
        })
    return {
        "schema_version": 1,
        "scenarios": [
            {
                "id": scenario_id,
                "description": description,
                "min_score": 1.0,
                "trace": trace,
                "graders": graders,
            }
        ],
    }


def write_fixture(path: Path, scenario_file: dict[str, Any], *, force: bool) -> None:
    if path.exists() and not force:
        raise ValueError(f"output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(scenario_file, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Promote workflow trace JSONL to scenario fixture.")
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--scenario-id", required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    try:
        scenario_file = build_scenario(
            trace=load_trace(args.trace),
            scenario_id=args.scenario_id,
            description=args.description,
        )
        write_fixture(args.output, scenario_file, force=args.force)
    except ValueError as exc:
        print(f"promote trace scenario: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({
            "schema_version": 1,
            "status": "pass",
            "output": str(args.output),
            "scenario_id": args.scenario_id,
            "graders": len(scenario_file["scenarios"][0]["graders"]),
        }, indent=2, sort_keys=True))
    else:
        print(f"promoted {args.scenario_id} -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run promotion tests to verify GREEN**

Run:

```bash
python -m pytest tests/test_regression_observability_trends.py::test_promote_trace_scenario_writes_valid_fixture tests/test_regression_observability_trends.py::test_promote_trace_scenario_refuses_existing_output_without_force -q
```

Expected: PASS.

- [ ] **Step 5: Commit promotion**

```bash
git add scripts/observability/promote_trace_scenario.py tests/test_regression_observability_trends.py docs/plans/2026-06-17-p10-live-trace-trends-plan.md
git commit -m "feat: promote workflow traces into eval scenarios"
```

## Task 4: Documentation, CI, And Release Story

**Files:**
- Create: `docs/observability-trends.md`
- Modify: `.github/workflows/validate-plugin.yml`
- Modify: `CHANGELOG.md`
- Modify: `tests/test_regression_v019_release_story.py`
- Modify: `docs/plans/2026-06-17-p10-live-trace-trends-plan.md`

- [ ] **Step 1: Add failing release-story tests**

Append to `tests/test_regression_v019_release_story.py`:

```python
def test_ci_runs_observability_trend_snapshot_gate():
    """P10 observability snapshots should be checked before broad pytest."""
    workflow = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
    assert "Observability trend snapshot gate" in workflow
    assert "python scripts/observability/collect_trend_snapshot.py --json --samples 1" in workflow


def test_unreleased_documents_observability_trends():
    """The Unreleased story must name local observability trend tooling."""
    section = _unreleased_section()
    required = [
        "Observability trend snapshots",
        "scripts/observability/collect_trend_snapshot.py",
        "trace-to-scenario promotion",
        ".athanor/observability/trends.jsonl",
    ]
    missing = [token for token in required if token not in section]
    assert not missing, (
        "CHANGELOG [Unreleased] must explain P10 observability trends; "
        f"missing: {missing}"
    )
```

- [ ] **Step 2: Run release-story tests to verify RED**

Run:

```bash
python -m pytest tests/test_regression_v019_release_story.py::test_ci_runs_observability_trend_snapshot_gate tests/test_regression_v019_release_story.py::test_unreleased_documents_observability_trends -q
```

Expected: FAIL until workflow and changelog are updated.

- [ ] **Step 3: Add documentation**

Create `docs/observability-trends.md` covering:

````markdown
# Observability Trends

P10 adds local-only observability trend tooling. It does not enable new hooks,
mutate settings, or export to an external service.

## Collect A Snapshot

Run:

```bash
python scripts/observability/collect_trend_snapshot.py --json
python scripts/observability/collect_trend_snapshot.py --append --json
```

The default history path is `.athanor/observability/trends.jsonl`, which is
ignored local runtime state.

## Report Trends

Run:

```bash
python scripts/observability/report_trends.py --json
```

The report summarizes workflow scenario score deltas, hook budget ratio
deltas, durable loop actions, and failure/escalation counts.

## Promote A Trace

Run:

```bash
python scripts/observability/promote_trace_scenario.py \
  --trace .athanor/traces/example.jsonl \
  --scenario-id promoted-example \
  --description "Promoted example trace" \
  --output tests/fixtures/workflow_evals/promoted-example.json
```

Review the generated fixture before committing it.
````

- [ ] **Step 4: Add CI gate**

In `.github/workflows/validate-plugin.yml`, add before broad pytest:

```yaml
      - name: Observability trend snapshot gate
        shell: bash
        run: python scripts/observability/collect_trend_snapshot.py --json --samples 1
```

- [ ] **Step 5: Add changelog entry**

In `CHANGELOG.md` Unreleased Added, add:

```markdown
- **Observability trend snapshots.** Adds
  `scripts/observability/collect_trend_snapshot.py`,
  `scripts/observability/report_trends.py`, and trace-to-scenario promotion so
  workflow eval scores, hook latency ratios, durable loop actions, and
  escalations can be tracked in local `.athanor/observability/trends.jsonl`
  history without enabling new hooks or external telemetry.
```

- [ ] **Step 6: Run docs/release tests**

Run:

```bash
python -m pytest tests/test_regression_observability_trends.py tests/test_regression_v019_release_story.py -q
python scripts/observability/collect_trend_snapshot.py --json --samples 1
git diff --check
```

Expected: all commands exit 0.

- [ ] **Step 7: Commit documentation and CI**

```bash
git add docs/observability-trends.md .github/workflows/validate-plugin.yml CHANGELOG.md tests/test_regression_v019_release_story.py docs/plans/2026-06-17-p10-live-trace-trends-plan.md
git commit -m "docs: wire observability trends into release story"
```

## Task 5: Final Verification And Merge

**Files:**
- Modify: `docs/plans/2026-06-17-p10-live-trace-trends-plan.md`

- [ ] **Step 1: Run targeted P10 verification**

Run:

```bash
python -m pytest tests/test_regression_observability_trends.py -q
python scripts/observability/collect_trend_snapshot.py --json --samples 1
```

Expected: PASS and collector JSON status fields are `pass`.

- [ ] **Step 2: Run existing P9/P6/P7 gates**

Run:

```bash
python scripts/gates/runtime_conformance.py --json
python scripts/evals/run_workflow_scenarios.py --scenario-root tests/fixtures/workflow_evals --json
python scripts/loops/run_goal_loop_fixtures.py --fixture-root tests/fixtures/durable_loops --json
python scripts/gates/check_hook_performance_budget.py --json --samples 1
```

Expected: all commands exit 0.

- [ ] **Step 3: Run full verification**

Run:

```bash
python -m pytest tests/ -q
git diff --check
```

Expected: full suite passes and whitespace check exits 0.

- [ ] **Step 4: Mark Task 5 verification checkboxes and commit**

```bash
git add docs/plans/2026-06-17-p10-live-trace-trends-plan.md
git commit -m "docs: record observability trends verification"
```

- [ ] **Step 5: Fast-forward merge to main and push**

```bash
git checkout main
git pull --ff-only origin main
git merge --ff-only feat/p10-live-trace-trends
python -m pytest tests/ -q
git diff --check
git push origin main
```

- [ ] **Step 6: Mark merge complete, commit, push, and delete feature branch**

```bash
git add docs/plans/2026-06-17-p10-live-trace-trends-plan.md
git commit -m "docs: mark p10 merge complete"
git push origin main
git branch --delete feat/p10-live-trace-trends
```

## Self-Review

- Spec coverage: tasks cover snapshot collection, trend reporting, trace promotion, docs, CI, release story, and merge verification.
- Placeholder scan: no placeholder tokens or open-ended implementation step remains.
- Type consistency: snapshot/report fields used by tests match the schemas and CLI outputs.
- Scope check: live slash-command instrumentation and external telemetry remain explicitly out of P10 scope, matching the design boundary.
