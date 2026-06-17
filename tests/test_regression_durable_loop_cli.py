"""Regression tests for durable loop controller CLI behavior."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.evals.workflow_trace import load_trace

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "scripts" / "loops" / "run_goal_loop_controller.py"


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _state(**overrides) -> dict:
    data = {
        "schema_version": 1,
        "goal_id": "36470e54",
        "cycle_state": "cycle_n_in_progress",
        "cycle_phase": "receipt_validated",
        "current_cycle": 2,
        "max_iterations": 5,
        "no_progress_threshold": 2,
        "last_receipt_path": ".athanor/goals/36470e54/receipts/C002-lfg-receipt.md",
        "last_validator_status": "all_valid",
        "tier2_last_verdict": None,
        "aborted_reason": None,
        "no_progress_count": 0,
        "stop_reason": None,
        "updated_at": "2026-06-17T08:30:00Z",
    }
    data.update(overrides)
    return data


def _evidence(**overrides) -> dict:
    data = {
        "eval_status": "pass",
        "validator_status": "all_valid",
        "tier1_passed": True,
        "tier2_goal_met": False,
        "tier3_user_response": None,
        "progress_made": True,
        "references": [".athanor/goals/36470e54/receipts/C002-lfg-receipt.md"],
    }
    data.update(overrides)
    return data


def _run_controller(
    state_path: Path,
    evidence_path: Path,
    *extra_args: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--state",
            str(state_path),
            "--evidence",
            str(evidence_path),
            "--json",
            *extra_args,
        ],
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


def test_loop_controller_cli_emits_json_decision(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    evidence_path = tmp_path / "evidence.json"
    _write_json(state_path, _state())
    _write_json(evidence_path, _evidence())

    proc = _run_controller(state_path, evidence_path)

    assert proc.returncode == 0, proc.stderr
    decision = json.loads(proc.stdout)
    assert decision["schema_version"] == 1
    assert decision["action"] == "run_tier1_check"
    assert decision["status"] == "pass"


def test_loop_controller_cli_appends_loop_decision_trace(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    evidence_path = tmp_path / "evidence.json"
    trace_path = tmp_path / "trace.jsonl"
    _write_json(state_path, _state())
    _write_json(evidence_path, _evidence())

    proc = _run_controller(
        state_path,
        evidence_path,
        "--trace-path",
        str(trace_path),
        "--trace-id",
        "goal-trace",
    )

    assert proc.returncode == 0, proc.stderr
    trace = load_trace(trace_path)
    assert trace[0]["trace_id"] == "goal-trace"
    assert trace[0]["event_type"] == "loop.decision"
    assert trace[0]["phase"] == "lfg-goal"
    assert trace[0]["evidence"]["action"] == "run_tier1_check"
    assert str(state_path) in trace[0]["references"][0]


def test_loop_controller_cli_write_state_persists_stop_decision(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    evidence_path = tmp_path / "evidence.json"
    _write_json(
        state_path,
        _state(cycle_state="cycle_n_complete", cycle_phase=None, current_cycle=5),
    )
    _write_json(evidence_path, _evidence())

    proc = _run_controller(state_path, evidence_path, "--write-state")

    assert proc.returncode == 1
    decision = json.loads(proc.stdout)
    assert decision["action"] == "stop_max_iterations"
    persisted = json.loads(state_path.read_text(encoding="utf-8"))
    assert persisted["cycle_state"] == "aborted"
    assert persisted["stop_reason"] == "stop_max_iterations"


def test_loop_controller_cli_exits_2_for_invalid_state(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    evidence_path = tmp_path / "evidence.json"
    _write_json(state_path, {"schema_version": 1})
    _write_json(evidence_path, _evidence())

    proc = _run_controller(state_path, evidence_path)

    assert proc.returncode == 2
    assert "missing required fields" in proc.stderr


def test_durable_loop_evidence_schema_defines_eval_status() -> None:
    schema = json.loads(
        Path("schemas/durable-loop-evidence.schema.json").read_text(encoding="utf-8")
    )

    assert schema["properties"]["schema_version"]["const"] == 1
    assert "eval_status" in schema["required"]
    assert "missing" in schema["properties"]["eval_status"]["enum"]
