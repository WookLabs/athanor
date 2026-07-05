"""Regression tests for the lfg-loop adaptive controller model."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

from scripts.loops.lfg_loop_controller import (
    EvidenceSummary,
    LoopState,
    LoopStateError,
    apply_decision,
    decide_next_action,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "scripts" / "loops" / "run_lfg_loop_controller.py"
SCHEMA_PATH = REPO_ROOT / "schemas" / "durable-loop-evidence.schema.json"


def _state(**overrides) -> LoopState:
    data = {
        "schema_version": 1,
        "loop_id": "36470e54",
        "cycle_state": "cycle_n_complete",
        "cycle_phase": None,
        "current_cycle": 1,
        "max_iterations": 5,
        "no_progress_threshold": 2,
        "last_receipt_path": ".athanor/loops/36470e54/receipts/C001-lfg-receipt.md",
        "last_validator_status": "all_valid",
        "tier2_last_verdict": None,
        "aborted_reason": None,
        "no_progress_count": 0,
        "stop_reason": None,
        "updated_at": "2026-06-24T00:30:00Z",
    }
    data.update(overrides)
    return LoopState.from_dict(data)


def _target(overrides: dict | None = None) -> dict:
    data = {
        "overall_score": 90,
        "min_dimension_score": 80,
    }
    if overrides:
        data.update(overrides)
    return data


def _assessment(**overrides) -> dict:
    data = {
        "kind": "delta",
        "report_path": ".athanor/sessions/2026-06-24-001/assess.md",
        "overall_score": 82,
        "min_dimension_score": 70,
        "target_met": False,
        "priority_plan_items": ["Raise test coverage on adaptive routing"],
        "dimensions": {
            "testing": {
                "score": 70,
                "target": 80,
                "floor": 75,
                "target_met": False,
                "regressed": False,
            },
            "goal_fit": {
                "score": 88,
                "target": 85,
                "floor": 80,
                "target_met": True,
                "regressed": False,
            },
        },
    }
    data.update(overrides)
    return data


def _evidence(**overrides) -> EvidenceSummary:
    data = {
        "eval_status": "pass",
        "validator_status": "all_valid",
        "tier1_passed": True,
        "tier2_completion_met": False,
        "tier3_user_response": None,
        "progress_made": True,
        "references": [".athanor/loops/36470e54/receipts/C001-lfg-receipt.md"],
        "score_target": _target(),
    }
    data.update(overrides)
    return EvidenceSummary.from_dict(data)


def test_score_target_bootstrap_without_baseline_runs_baseline_assess() -> None:
    decision = decide_next_action(
        _state(
            cycle_state="bootstrapping",
            cycle_phase=None,
            current_cycle=0,
            last_receipt_path=None,
            last_validator_status="not_yet_run",
        ),
        _evidence(assessment=None, progress_made=None),
    )

    assert decision.action == "run_baseline_assess"
    assert decision.status == "pass"
    assert decision.evidence["score_target"]["overall_score"] == 90
    assert "baseline" in decision.reason


def test_valid_cycle_receipt_without_delta_assessment_runs_delta_assess() -> None:
    decision = decide_next_action(
        _state(last_validator_status="all_valid"),
        _evidence(assessment=None),
    )

    assert decision.action == "run_delta_assess"
    assert decision.status == "pass"
    assert decision.evidence["blocked_action"] == "run_lfg_cycle"
    assert "delta assessment" in decision.reason


def test_below_target_delta_with_progress_runs_next_lfg_cycle_with_targets() -> None:
    state = _state(last_validator_status="completed_with_residuals")
    decision = decide_next_action(
        state,
        _evidence(
            validator_status="completed_with_residuals",
            assessment=_assessment(),
            progress_made=True,
        ),
    )
    next_state = apply_decision(state, decision)

    assert decision.action == "run_lfg_cycle"
    assert decision.status == "pass"
    assert decision.evidence["target_dimensions"] == ["testing"]
    assert decision.evidence["priority_plan_items"] == [
        "Raise test coverage on adaptive routing"
    ]
    assert next_state.cycle_state == "cycle_n_in_progress"
    assert next_state.cycle_phase == "not_started"
    assert next_state.current_cycle == 2


def test_score_target_without_completion_gates_required_parses_and_gate_fires() -> None:
    """Q1-10: `completion_gates_required` was an inert no-op (parsed/validated/
    echoed but never read) — it was REMOVED rather than wired, because the
    tier1+tier2 completion gate fires UNCONDITIONALLY (always-apply 3-tier
    invariant). A score_target dict WITHOUT the key must parse cleanly and carry
    no such key, and the completion gate must still fire — guarding against a
    future re-introduction as a live toggle.
    """
    final_assessment = _assessment(
        kind="final",
        overall_score=93,
        min_dimension_score=84,
        target_met=True,
        priority_plan_items=[],
        dimensions={
            "testing": {
                "score": 84,
                "target": 80,
                "floor": 75,
                "target_met": True,
                "regressed": False,
            }
        },
    )
    evidence = _evidence(
        score_target={"overall_score": 90, "min_dimension_score": 80},
        assessment=final_assessment,
        tier1_passed=True,
        tier2_completion_met=True,
    )

    # Parses cleanly; the parsed target carries no completion_gates_required key.
    assert evidence.score_target == {"overall_score": 90, "min_dimension_score": 80}
    assert "completion_gates_required" not in evidence.score_target

    # The 3-tier completion gate fires unconditionally (no toggle gates it).
    decision = decide_next_action(_state(last_validator_status="all_valid"), evidence)
    assert decision.action == "prompt_tier3_user"
    assert decision.status == "pass"
    assert "completion_gates_required" not in decision.evidence.get("score_target", {})


def test_final_assessment_meeting_target_prompts_tier3_user() -> None:
    final_assessment = _assessment(
        kind="final",
        overall_score=93,
        min_dimension_score=84,
        target_met=True,
        priority_plan_items=[],
        dimensions={
            "testing": {
                "score": 84,
                "target": 80,
                "floor": 75,
                "target_met": True,
                "regressed": False,
            }
        },
    )

    decision = decide_next_action(
        _state(last_validator_status="all_valid"),
        _evidence(
            assessment=final_assessment,
            tier1_passed=True,
            tier2_completion_met=True,
        ),
    )

    assert decision.action == "prompt_tier3_user"
    assert decision.status == "pass"
    assert decision.next_cycle_state == "cycle_n_in_progress"
    assert decision.next_cycle_phase == "tier3_pending"
    assert decision.evidence["assessment"]["kind"] == "final"


def test_final_target_met_contradiction_blocks_tier3_prompt() -> None:
    contradictory_assessment = _assessment(
        kind="final",
        overall_score=10,
        min_dimension_score=84,
        target_met=True,
        priority_plan_items=[],
        dimensions={
            "testing": {
                "score": 84,
                "target": 80,
                "floor": 75,
                "target_met": True,
                "regressed": False,
            }
        },
    )

    decision = decide_next_action(
        _state(last_validator_status="all_valid"),
        _evidence(
            assessment=contradictory_assessment,
            score_target=_target({"overall_score": 95, "min_dimension_score": 80}),
            tier1_passed=True,
            tier2_completion_met=True,
        ),
    )

    assert decision.action == "require_assessment_evidence"
    assert decision.status == "escalated"
    assert "assessment target contradiction" in decision.reason
    assert "overall_score_below_target" in decision.evidence["assessment_contradictions"]


def test_final_target_met_with_regressed_dimension_blocks_tier3_prompt() -> None:
    contradictory_assessment = _assessment(
        kind="final",
        overall_score=96,
        min_dimension_score=90,
        target_met=True,
        priority_plan_items=[],
        dimensions={
            "testing": {
                "score": 90,
                "target": 80,
                "floor": 75,
                "target_met": True,
                "regressed": True,
            }
        },
    )

    decision = decide_next_action(
        _state(last_validator_status="all_valid"),
        _evidence(
            assessment=contradictory_assessment,
            score_target=_target({"overall_score": 95, "min_dimension_score": 80}),
            tier1_passed=True,
            tier2_completion_met=True,
        ),
    )

    assert decision.action == "require_assessment_evidence"
    assert decision.status == "escalated"
    assert "dimension_regressed:testing" in decision.evidence[
        "assessment_contradictions"
    ]


def test_current_invalid_receipt_evidence_blocks_stale_valid_state() -> None:
    decision = decide_next_action(
        _state(last_validator_status="all_valid"),
        _evidence(
            validator_status="invalid_steps_present",
            assessment=_assessment(),
        ),
    )

    assert decision.action == "run_scope_drift"
    assert decision.status == "escalated"
    assert decision.evidence["validator_status"] == "invalid_steps_present"
    assert decision.evidence["state_validator_status"] == "all_valid"


def test_current_invalid_receipt_evidence_blocks_legacy_start_next_cycle() -> None:
    decision = decide_next_action(
        _state(cycle_state="cycle_n_complete", last_validator_status="all_valid"),
        _evidence(
            score_target=None,
            validator_status="invalid_steps_present",
            assessment=None,
        ),
    )

    assert decision.action == "run_scope_drift"
    assert decision.status == "escalated"
    assert decision.next_cycle_state == "cycle_n_complete"
    assert decision.evidence["blocked_action"] == "start_next_cycle"
    assert decision.evidence["validator_status"] == "invalid_steps_present"


def test_failed_eval_status_blocks_adaptive_continuation() -> None:
    decision = decide_next_action(
        _state(last_validator_status="all_valid"),
        _evidence(
            eval_status="fail",
            assessment=_assessment(),
        ),
    )

    assert decision.action == "block_failed_eval"
    assert decision.status == "failure"
    assert decision.evidence["blocked_action"] == "run_lfg_cycle"


@pytest.mark.parametrize("cycle_phase", ["tier2_checked", "tier3_pending"])
def test_max_iterations_do_not_block_legacy_tier3_prompt(
    cycle_phase: str,
) -> None:
    decision = decide_next_action(
        _state(
            cycle_state="cycle_n_in_progress",
            cycle_phase=cycle_phase,
            current_cycle=5,
            max_iterations=5,
            last_validator_status="all_valid",
        ),
        _evidence(score_target=None, assessment=None),
    )

    assert decision.action == "prompt_tier3_user"
    assert decision.status == "pass"


def test_final_completion_can_prompt_on_last_allowed_cycle() -> None:
    final_assessment = _assessment(
        kind="final",
        overall_score=93,
        min_dimension_score=84,
        target_met=True,
        priority_plan_items=[],
        dimensions={
            "testing": {
                "score": 84,
                "target": 80,
                "floor": 75,
                "target_met": True,
                "regressed": False,
            }
        },
    )

    decision = decide_next_action(
        _state(current_cycle=5, max_iterations=5, last_validator_status="all_valid"),
        _evidence(
            assessment=final_assessment,
            tier1_passed=True,
            tier2_completion_met=True,
        ),
    )

    assert decision.action == "prompt_tier3_user"
    assert decision.status == "pass"


def test_final_target_false_contradiction_blocks_another_loop() -> None:
    contradictory_assessment = _assessment(
        kind="final",
        overall_score=96,
        min_dimension_score=88,
        target_met=False,
        priority_plan_items=[],
        dimensions={
            "testing": {
                "score": 88,
                "target": 80,
                "floor": 75,
                "target_met": True,
                "regressed": False,
            },
            "goal_fit": {
                "score": 94,
                "target": 85,
                "floor": 80,
                "target_met": True,
                "regressed": False,
            },
        },
    )

    decision = decide_next_action(
        _state(last_validator_status="all_valid"),
        _evidence(
            assessment=contradictory_assessment,
            score_target=_target({"overall_score": 95, "min_dimension_score": 80}),
            tier1_passed=True,
            tier2_completion_met=True,
        ),
    )

    assert decision.action == "require_assessment_evidence"
    assert decision.status == "escalated"
    assert "assessment target contradiction" in decision.reason
    assert decision.evidence["assessment_contradictions"] == [
        "target_met_false_but_scores_satisfy_target"
    ]


def test_claimed_min_dimension_score_disagrees_with_actual_dimension_scores() -> None:
    contradictory_assessment = _assessment(
        kind="final",
        overall_score=96,
        min_dimension_score=90,
        target_met=True,
        priority_plan_items=[],
        dimensions={
            "testing": {
                "score": 10,
                "target": None,
                "floor": None,
                "target_met": True,
                "regressed": False,
            },
            "goal_fit": {
                "score": 94,
                "target": 85,
                "floor": 80,
                "target_met": True,
                "regressed": False,
            },
        },
    )

    decision = decide_next_action(
        _state(last_validator_status="all_valid"),
        _evidence(
            assessment=contradictory_assessment,
            score_target=_target({"overall_score": 95, "min_dimension_score": 80}),
            tier1_passed=True,
            tier2_completion_met=True,
        ),
    )

    assert decision.action == "require_assessment_evidence"
    assert decision.status == "escalated"
    assert "assessment target contradiction" in decision.reason
    assert (
        "min_dimension_score_mismatch:claimed=90,computed=10"
        in decision.evidence["assessment_contradictions"]
    )
    assert "min_dimension_score_below_target" in decision.evidence[
        "assessment_contradictions"
    ]


def test_claimed_min_dimension_score_mismatch_blocks_when_target_not_met() -> None:
    contradictory_assessment = _assessment(
        kind="delta",
        overall_score=96,
        min_dimension_score=90,
        target_met=False,
        priority_plan_items=["Reconcile assessment evidence"],
        dimensions={
            "testing": {
                "score": 10,
                "target": None,
                "floor": None,
                "target_met": True,
                "regressed": False,
            },
            "goal_fit": {
                "score": 94,
                "target": None,
                "floor": None,
                "target_met": True,
                "regressed": False,
            },
        },
    )

    decision = decide_next_action(
        _state(last_validator_status="all_valid"),
        _evidence(
            assessment=contradictory_assessment,
            score_target=_target({"overall_score": 95, "min_dimension_score": 0}),
        ),
    )

    assert decision.action == "require_assessment_evidence"
    assert decision.status == "escalated"
    assert "assessment target contradiction" in decision.reason
    assert decision.evidence["assessment_contradictions"] == [
        "min_dimension_score_mismatch:claimed=90,computed=10"
    ]


def test_next_cycle_target_dimensions_are_ordered_by_lowest_score() -> None:
    assessment = _assessment(
        min_dimension_score=52,
        dimensions={
            "docs": {
                "score": 79,
                "target": 85,
                "floor": 80,
                "target_met": False,
                "regressed": False,
            },
            "testing": {
                "score": 52,
                "target": 85,
                "floor": 80,
                "target_met": False,
                "regressed": False,
            },
            "security": {
                "score": 68,
                "target": 85,
                "floor": 80,
                "target_met": False,
                "regressed": False,
            },
        }
    )

    decision = decide_next_action(
        _state(last_validator_status="all_valid"),
        _evidence(assessment=assessment),
    )

    assert decision.action == "run_lfg_cycle"
    assert decision.evidence["target_dimensions"] == ["testing", "security", "docs"]


def test_invalid_assessment_evidence_is_rejected_loudly() -> None:
    with pytest.raises(LoopStateError, match="assessment.target_met must be a boolean"):
        _evidence(assessment=_assessment(target_met="yes"))


def test_assessment_packet_schema_accepts_structured_score_evidence() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    packet = _evidence(assessment=_assessment()).to_dict()

    errors = sorted(Draft7Validator(schema).iter_errors(packet), key=str)

    assert errors == []
    assert schema["properties"]["assessment"]["properties"]["kind"]["enum"] == [
        "baseline",
        "delta",
        "final",
    ]


def test_cli_emits_machine_readable_adaptive_next_action(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    evidence_path = tmp_path / "evidence.json"
    state_path.write_text(
        json.dumps(_state().to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    evidence_path.write_text(
        json.dumps(_evidence(assessment=None).to_dict(), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )

    proc = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--state",
            str(state_path),
            "--evidence",
            str(evidence_path),
            "--json",
        ],
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )

    assert proc.returncode == 0, proc.stderr
    decision = json.loads(proc.stdout)
    assert decision["action"] == "run_delta_assess"
    assert decision["evidence"]["score_target"]["min_dimension_score"] == 80
