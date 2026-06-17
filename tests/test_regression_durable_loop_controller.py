"""Regression tests for durable lfg-goal loop decisions."""
from __future__ import annotations

import pytest

from scripts.loops.goal_loop_controller import (
    EvidenceSummary,
    LoopState,
    apply_decision,
    decide_next_action,
)


def _state(**overrides) -> LoopState:
    data = {
        "schema_version": 1,
        "goal_id": "36470e54",
        "cycle_state": "cycle_n_in_progress",
        "cycle_phase": "not_started",
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
    return LoopState.from_dict(data)


def _evidence(**overrides) -> EvidenceSummary:
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
    return EvidenceSummary.from_dict(data)


@pytest.mark.parametrize(
    ("cycle_phase", "expected_action"),
    [
        ("not_started", "resume_cycle_from_start"),
        ("lfg_done_seen", "validate_receipt"),
        ("receipt_validated", "run_tier1_check"),
        ("tier1_checked", "run_tier2_judges"),
        ("tier2_checked", "prompt_tier3_user"),
        ("tier3_pending", "prompt_tier3_user"),
        ("tier3_ratified", "start_next_cycle"),
    ],
)
def test_decision_routes_each_cycle_phase(
    cycle_phase: str, expected_action: str
) -> None:
    decision = decide_next_action(_state(cycle_phase=cycle_phase), _evidence())

    assert decision.action == expected_action
    assert decision.status == "pass"
    assert decision.goal_id == "36470e54"


@pytest.mark.parametrize(
    ("cycle_state", "cycle_phase", "expected_action"),
    [
        ("bootstrapping", None, "bootstrap_goal"),
        ("cycle_n_complete", None, "start_next_cycle"),
        ("scope_change_pending", None, "resume_scope_change_review"),
    ],
)
def test_decision_routes_macro_states(
    cycle_state: str, cycle_phase: str | None, expected_action: str
) -> None:
    decision = decide_next_action(
        _state(cycle_state=cycle_state, cycle_phase=cycle_phase),
        _evidence(),
    )

    assert decision.action == expected_action
    assert decision.status == "pass"


@pytest.mark.parametrize("cycle_state", ["goal_complete", "aborted"])
def test_decision_refuses_terminal_states(cycle_state: str) -> None:
    decision = decide_next_action(
        _state(
            cycle_state=cycle_state,
            cycle_phase=None,
            aborted_reason=(
                "max iterations reached" if cycle_state == "aborted" else None
            ),
        ),
        _evidence(),
    )

    assert decision.action == "refuse_terminal_state"
    assert decision.status == "skipped"


def test_decision_stops_at_max_iterations_and_persists_abort() -> None:
    state = _state(
        cycle_state="cycle_n_complete",
        cycle_phase=None,
        current_cycle=5,
        max_iterations=5,
    )

    decision = decide_next_action(state, _evidence())
    next_state = apply_decision(state, decision)

    assert decision.action == "stop_max_iterations"
    assert decision.status == "failure"
    assert next_state.cycle_state == "aborted"
    assert next_state.cycle_phase is None
    assert next_state.stop_reason == "stop_max_iterations"
    assert "max iterations" in next_state.aborted_reason


def test_decision_stops_when_no_progress_threshold_is_reached() -> None:
    state = _state(no_progress_count=1, no_progress_threshold=2)

    decision = decide_next_action(state, _evidence(progress_made=False))
    next_state = apply_decision(state, decision)

    assert decision.action == "stop_no_progress"
    assert decision.status == "failure"
    assert next_state.cycle_state == "aborted"
    assert next_state.no_progress_count == 2
    assert next_state.stop_reason == "stop_no_progress"


def test_decision_requires_eval_evidence_for_evidence_gated_transition() -> None:
    decision = decide_next_action(
        _state(cycle_phase="receipt_validated"),
        _evidence(eval_status="missing"),
    )

    assert decision.action == "require_eval_evidence"
    assert decision.status == "escalated"
    assert decision.next_cycle_state == "cycle_n_in_progress"
    assert decision.next_cycle_phase == "receipt_validated"


def test_decision_handles_legacy_missing_phase_as_concern() -> None:
    data = _state().to_dict()
    data.pop("schema_version")
    data.pop("cycle_phase")
    legacy_state = LoopState.from_dict(data)

    decision = decide_next_action(legacy_state, _evidence())

    assert decision.action == "resume_cycle_from_start"
    assert decision.status == "concern"
    assert "coarse-grained resume" in decision.reason
