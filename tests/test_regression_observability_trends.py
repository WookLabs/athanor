"""Regression tests for local observability trend tooling."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
COLLECTOR = REPO_ROOT / "scripts" / "observability" / "collect_trend_snapshot.py"
REPORTER = REPO_ROOT / "scripts" / "observability" / "report_trends.py"
SNAPSHOT_SCHEMA = REPO_ROOT / "schemas" / "observability-trend-snapshot.schema.json"
TREND_SCHEMA = REPO_ROOT / "schemas" / "observability-trend-report.schema.json"


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
                _snapshot(
                    sha="aaa1111",
                    mean_score=1.0,
                    failed_scenarios=[],
                    hook_ratio=0.10,
                ),
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
