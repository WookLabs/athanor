"""Regression tests for executable hook performance budgets."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.gates import check_hook_performance_budget as budget_gate

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

    assert "pretool-dispatcher" in hook_ids
    assert "posttool-evidence-sniffer" in hook_ids
    assert all(entry["status"] == "pass" for entry in report["hooks"])


def test_budget_gate_fails_when_budget_is_too_low() -> None:
    result = run_budget_gate(
        "--json",
        "--samples",
        "1",
        "--override-budget-ms",
        "pretool-dispatcher=0",
    )

    assert result.returncode == 1
    report = json.loads(result.stdout)
    pretool_entry = next(
        entry for entry in report["hooks"] if entry["id"] == "pretool-dispatcher"
    )
    assert pretool_entry["status"] == "fail"
    assert "budget" in pretool_entry["reason"]


def test_budget_gate_uses_median_for_status_and_reports_max(monkeypatch) -> None:
    durations = iter([900.0, 100.0, 700.0, 110.0])

    def fake_run_once(command, payload, hook_id):
        return {
            "duration_ms": next(durations),
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
        }

    monkeypatch.setattr(budget_gate, "_run_once", fake_run_once)
    report = budget_gate._measure_hook(
        hook={
            "id": "pretool-dispatcher",
            "event": "PreToolUse",
            "command": (
                'sh "${CLAUDE_PLUGIN_ROOT}/scripts/hooks/run_hook.sh" '
                '"${CLAUDE_PLUGIN_ROOT}/scripts/hooks/pretool_dispatcher.py"'
            ),
            "performance_budget_ms": 500,
        },
        fixtures=[
            {
                "id": "fast-a",
                "event": "PreToolUse",
                "source_level": "synthetic",
                "payload": {"hook_event_name": "PreToolUse"},
            },
            {
                "id": "slow-startup",
                "event": "PreToolUse",
                "source_level": "synthetic",
                "payload": {"hook_event_name": "PreToolUse"},
            },
            {
                "id": "fast-b",
                "event": "PreToolUse",
                "source_level": "synthetic",
                "payload": {"hook_event_name": "PreToolUse"},
            },
        ],
        samples=3,
        overrides={},
    )

    assert report["status"] == "pass"
    assert report["median_ms"] == 110.0
    assert report["max_ms"] == 700.0
    assert "median" in report["reason"]
