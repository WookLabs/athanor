"""Regression tests bounding persistent block/escalate states in the durable loop.

BLOCKER 1 (PR #65): ``block_failed_eval`` and ``run_scope_drift`` returned BEFORE the
no-progress accounting and ``apply_decision`` left state UNCHANGED for them, so a
persistent ``eval_status=fail`` / ``validator_status=invalid_steps_present`` loop emitted
the same block action forever and never reached terminal ``aborted``.

Decision (a) from ``.athanor/sessions/2026-06-24-001/plan.md``: fold blocks into the
EXISTING no-progress accounting. A block with ``progress_made != True`` advances
``no_progress_count``; reaching ``no_progress_threshold`` returns ``stop_no_progress``
(terminal ``aborted``). An explicit ``progress_made=true`` next cycle resets the counter.
A non-tripping block still EMITS the block action and moves ONLY ``no_progress_count``.
"""
from __future__ import annotations

import pytest

from scripts.loops.goal_loop_controller import (
    EvidenceSummary,
    LoopState,
    apply_decision,
    decide_next_action,
)

# Hard cap so a regression that re-introduces the unbounded loop fails LOUDLY (the test
# terminates and asserts it stopped well before the cap) instead of hanging CI.
RE_DRIVE_CAP = 10


def _state(**overrides) -> LoopState:
    data = {
        "schema_version": 1,
        "goal_id": "36470e54",
        "cycle_state": "cycle_n_complete",
        "cycle_phase": None,
        "current_cycle": 3,
        "max_iterations": 5,
        "no_progress_threshold": 2,
        "last_receipt_path": ".athanor/goals/36470e54/receipts/C003-lfg-receipt.md",
        "last_validator_status": "all_valid",
        "tier2_last_verdict": None,
        "aborted_reason": None,
        "no_progress_count": 0,
        "stop_reason": None,
        "updated_at": "2026-06-24T00:30:00Z",
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
        "progress_made": None,
        "references": [".athanor/goals/36470e54/receipts/C003-lfg-receipt.md"],
    }
    data.update(overrides)
    return EvidenceSummary.from_dict(data)


def _re_drive(state: LoopState, evidence: EvidenceSummary):
    """Drive decide_next_action -> apply_decision feeding the new state back.

    Returns ``(actions, final_state, iterations)``. Capped at ``RE_DRIVE_CAP`` so a
    re-introduced unbounded loop terminates the test (asserted below) rather than hangs.
    """
    actions: list[str] = []
    for iterations in range(1, RE_DRIVE_CAP + 1):
        decision = decide_next_action(state, evidence)
        actions.append(decision.action)
        state = apply_decision(state, decision)
        if state.cycle_state == "aborted":
            return actions, state, iterations
    return actions, state, RE_DRIVE_CAP


def test_persistent_failed_eval_aborts_within_no_progress_threshold() -> None:
    state = _state(
        cycle_state="cycle_n_complete",
        current_cycle=3,
        max_iterations=5,
        no_progress_threshold=2,
        no_progress_count=0,
    )
    evidence = _evidence(eval_status="fail", progress_made=None)

    actions, final_state, iterations = _re_drive(state, evidence)

    # Terminated before the cap => no infinite loop.
    assert iterations < RE_DRIVE_CAP, (
        f"loop did not terminate within {RE_DRIVE_CAP} iterations; actions={actions}"
    )
    # Aborts via stop_no_progress within the threshold (default 2).
    assert iterations <= state.no_progress_threshold, (
        f"expected abort within {state.no_progress_threshold} iters, took {iterations}; "
        f"actions={actions}"
    )
    assert actions[-1] == "stop_no_progress", actions
    assert actions[0] == "block_failed_eval", actions
    assert final_state.cycle_state == "aborted"
    assert final_state.stop_reason == "stop_no_progress"


def test_persistent_invalid_receipt_aborts_within_no_progress_threshold() -> None:
    state = _state(
        cycle_state="cycle_n_complete",
        current_cycle=3,
        max_iterations=5,
        no_progress_threshold=2,
        no_progress_count=0,
    )
    evidence = _evidence(
        eval_status="pass",
        validator_status="invalid_steps_present",
        progress_made=None,
    )

    actions, final_state, iterations = _re_drive(state, evidence)

    assert iterations < RE_DRIVE_CAP, (
        f"loop did not terminate within {RE_DRIVE_CAP} iterations; actions={actions}"
    )
    assert iterations <= state.no_progress_threshold, (
        f"expected abort within {state.no_progress_threshold} iters, took {iterations}; "
        f"actions={actions}"
    )
    assert actions[-1] == "stop_no_progress", actions
    assert actions[0] == "run_scope_drift", actions
    assert final_state.cycle_state == "aborted"
    assert final_state.stop_reason == "stop_no_progress"


def test_escalate_once_then_progress_does_not_abort_and_resets_counter() -> None:
    state = _state(
        cycle_state="cycle_n_complete",
        current_cycle=3,
        max_iterations=5,
        no_progress_threshold=2,
        no_progress_count=0,
    )

    # First cycle: eval fails -> block emitted, counter advances to 1 (not tripped).
    block_decision = decide_next_action(
        state, _evidence(eval_status="fail", progress_made=None)
    )
    assert block_decision.action == "block_failed_eval"
    after_block = apply_decision(state, block_decision)
    assert after_block.no_progress_count == 1
    assert after_block.cycle_state == "cycle_n_complete"

    # Next cycle: user fixed it; progress reported -> counter resets to 0, no abort.
    progress_decision = decide_next_action(
        after_block, _evidence(eval_status="pass", progress_made=True)
    )
    assert progress_decision.action != "stop_no_progress"
    after_progress = apply_decision(after_block, progress_decision)
    assert after_progress.no_progress_count == 0
    assert after_progress.cycle_state != "aborted"


def test_non_tripping_block_advances_only_no_progress_count() -> None:
    state = _state(
        cycle_state="cycle_n_complete",
        cycle_phase=None,
        current_cycle=3,
        max_iterations=5,
        no_progress_threshold=3,  # high so a single block never trips
        no_progress_count=0,
    )

    decision = decide_next_action(
        state, _evidence(eval_status="fail", progress_made=None)
    )
    next_state = apply_decision(state, decision)

    # The block still escalates once.
    assert decision.action == "block_failed_eval"
    # Only the no-progress accumulator moves.
    assert next_state.no_progress_count == 1
    # Cycle counter / state / phase untouched.
    assert next_state.current_cycle == state.current_cycle
    assert next_state.cycle_state == state.cycle_state
    assert next_state.cycle_phase == state.cycle_phase


def test_non_tripping_invalid_receipt_block_advances_only_no_progress_count() -> None:
    state = _state(
        cycle_state="cycle_n_complete",
        cycle_phase=None,
        current_cycle=3,
        max_iterations=5,
        no_progress_threshold=3,
        no_progress_count=0,
    )

    decision = decide_next_action(
        state,
        _evidence(
            eval_status="pass",
            validator_status="invalid_steps_present",
            progress_made=None,
        ),
    )
    next_state = apply_decision(state, decision)

    assert decision.action == "run_scope_drift"
    assert next_state.no_progress_count == 1
    assert next_state.current_cycle == state.current_cycle
    assert next_state.cycle_state == state.cycle_state
    assert next_state.cycle_phase == state.cycle_phase


def test_block_on_final_cycle_stops_via_max_iterations() -> None:
    # Secondary safety net: a block on the last allowed cycle aborts even if the
    # no-progress threshold has not been reached yet.
    state = _state(
        cycle_state="cycle_n_complete",
        cycle_phase=None,
        current_cycle=5,
        max_iterations=5,
        no_progress_threshold=10,  # high so no-progress is NOT the terminator here
        no_progress_count=0,
    )

    decision = decide_next_action(
        state, _evidence(eval_status="fail", progress_made=None)
    )
    next_state = apply_decision(state, decision)

    assert decision.action == "stop_max_iterations"
    assert next_state.cycle_state == "aborted"
    assert next_state.stop_reason == "stop_max_iterations"


def test_single_block_on_non_final_cycle_still_escalates() -> None:
    # The legitimate "block once on a non-final cycle" path must NOT be turned into an
    # abort by the max-iter safety net.
    state = _state(
        cycle_state="cycle_n_complete",
        cycle_phase=None,
        current_cycle=2,
        max_iterations=5,
        no_progress_threshold=3,
        no_progress_count=0,
    )

    decision = decide_next_action(
        state, _evidence(eval_status="fail", progress_made=None)
    )

    assert decision.action == "block_failed_eval"
    assert decision.status == "failure"


def test_block_with_explicit_progress_true_does_not_advance_counter() -> None:
    # A block cycle that nonetheless reports progress_made=True must not advance the
    # counter (only progress_made != True counts).
    state = _state(
        cycle_state="cycle_n_complete",
        cycle_phase=None,
        current_cycle=3,
        max_iterations=5,
        no_progress_threshold=2,
        no_progress_count=0,
    )

    decision = decide_next_action(
        state, _evidence(eval_status="fail", progress_made=True)
    )
    next_state = apply_decision(state, decision)

    assert decision.action == "block_failed_eval"
    assert next_state.no_progress_count == 0
    assert next_state.cycle_state == "cycle_n_complete"
