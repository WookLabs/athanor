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
