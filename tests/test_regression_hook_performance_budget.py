"""Regression tests for executable hook performance budgets."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "gates" / "check_hook_performance_budget.py"


def run_budget_gate(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )


def test_budget_gate_exists_and_reports_enabled_hooks() -> None:
    result = run_budget_gate("--json", "--samples", "1")

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    hook_ids = {entry["id"] for entry in report["hooks"]}

    assert "stop-verify-claims" in hook_ids
    assert "pretool-dispatcher" in hook_ids
    assert "posttool-evidence-sniffer" in hook_ids
    assert all(entry["status"] == "pass" for entry in report["hooks"])


def test_budget_gate_fails_when_budget_is_too_low() -> None:
    result = run_budget_gate(
        "--json",
        "--samples",
        "1",
        "--override-budget-ms",
        "stop-verify-claims=0",
    )

    assert result.returncode == 1
    report = json.loads(result.stdout)
    stop_entry = next(
        entry for entry in report["hooks"] if entry["id"] == "stop-verify-claims"
    )
    assert stop_entry["status"] == "fail"
    assert "budget" in stop_entry["reason"]
