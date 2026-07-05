"""Regression tests for durable loop controller CLI behavior."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.evals.workflow_trace import load_trace

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "scripts" / "loops" / "run_lfg_loop_controller.py"
FIXTURE_RUNNER = REPO_ROOT / "scripts" / "loops" / "run_lfg_loop_fixtures.py"


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _state(**overrides) -> dict:
    data = {
        "schema_version": 1,
        "loop_id": "36470e54",
        "cycle_state": "cycle_n_in_progress",
        "cycle_phase": "receipt_validated",
        "current_cycle": 2,
        "max_iterations": 5,
        "no_progress_threshold": 2,
        "last_receipt_path": ".athanor/loops/36470e54/receipts/C002-lfg-receipt.md",
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
        "tier2_completion_met": False,
        "tier3_user_response": None,
        "progress_made": True,
        "references": [".athanor/loops/36470e54/receipts/C002-lfg-receipt.md"],
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
    assert trace[0]["phase"] == "lfg-loop"
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


def test_loop_controller_cli_exits_1_for_block_failed_eval(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    evidence_path = tmp_path / "evidence.json"
    _write_json(state_path, _state())
    _write_json(evidence_path, _evidence(eval_status="fail", progress_made=True))

    proc = _run_controller(state_path, evidence_path)

    assert proc.returncode == 1, proc.stdout + proc.stderr
    decision = json.loads(proc.stdout)
    assert decision["action"] == "block_failed_eval"
    assert decision["status"] == "failure"


def test_loop_controller_cli_exits_1_for_run_scope_drift(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    evidence_path = tmp_path / "evidence.json"
    _write_json(state_path, _state())
    _write_json(
        evidence_path,
        _evidence(validator_status="invalid_steps_present", progress_made=True),
    )

    proc = _run_controller(state_path, evidence_path)

    assert proc.returncode == 1, proc.stdout + proc.stderr
    decision = json.loads(proc.stdout)
    assert decision["action"] == "run_scope_drift"


def test_loop_controller_cli_exits_1_for_require_receipt_validation(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "state.json"
    evidence_path = tmp_path / "evidence.json"
    _write_json(
        state_path,
        _state(
            cycle_state="cycle_n_complete",
            cycle_phase=None,
            last_validator_status="not_yet_run",
        ),
    )
    _write_json(
        evidence_path,
        _evidence(
            validator_status="not_yet_run",
            progress_made=True,
            score_target={"overall_score": 90, "min_dimension_score": 80},
        ),
    )

    proc = _run_controller(state_path, evidence_path)

    assert proc.returncode == 1, proc.stdout + proc.stderr
    decision = json.loads(proc.stdout)
    assert decision["action"] == "require_receipt_validation"


def test_loop_controller_cli_exits_1_for_require_assessment_evidence(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "state.json"
    evidence_path = tmp_path / "evidence.json"
    _write_json(
        state_path,
        _state(cycle_state="bootstrapping", cycle_phase=None, current_cycle=0),
    )
    _write_json(
        evidence_path,
        _evidence(
            progress_made=True,
            score_target={"overall_score": 90, "min_dimension_score": 80},
            assessment={
                "kind": "delta",
                "report_path": ".athanor/loops/36470e54/assess/delta.md",
                "overall_score": 70,
                "min_dimension_score": 60,
                "target_met": False,
                "priority_plan_items": [],
                "dimensions": {
                    "quality": {
                        "score": 60,
                        "target": 80,
                        "floor": None,
                        "target_met": False,
                        "regressed": False,
                    }
                },
            },
        ),
    )

    proc = _run_controller(state_path, evidence_path)

    assert proc.returncode == 1, proc.stdout + proc.stderr
    decision = json.loads(proc.stdout)
    assert decision["action"] == "require_assessment_evidence"


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


def test_committed_durable_loop_fixtures_pass() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(FIXTURE_RUNNER),
            "--fixture-root",
            str(REPO_ROOT / "tests" / "fixtures" / "durable_loops"),
            "--json",
        ],
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["status"] == "pass"
    scenarios = report["scenarios"]
    assert all(item["status"] == "pass" for item in scenarios), [
        item for item in scenarios if item["status"] != "pass"
    ]
    assert {item["id"] for item in scenarios} == {
        "resume-after-receipt-validated",
        "terminal-goal-complete-refuses-reentry",
        "max-iterations-stops",
        "no-progress-threshold-stops",
        "missing-eval-evidence-escalates",
        "score-target-bootstrap-runs-baseline-assess",
        "valid-receipt-runs-delta-assess",
        "below-target-delta-runs-next-lfg-cycle",
        "failed-eval-blocks",
        "persistent-failed-eval-aborts",
        "invalid-receipt-runs-scope-drift",
    }
