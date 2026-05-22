"""Regression: contract for v0.13.0 LFG-goal receipt-validator + receipt fixtures.

This test file asserts two contracts that Subtasks 7 (receipt-validator
worker dispatch prompt) and 9 (receipt fixture set) MUST satisfy. Neither
the validator agent file nor the fixture .md files exist yet at the time
this file is authored (Subtask 3 of the v0.13.0 plan); every underlying
assertion would fail today. Each test is therefore decorated
``@pytest.mark.xfail(strict=False)`` so the suite remains green during
the rest of the v0.13.0 work session. Subtasks 7 and 9 will REMOVE the
xfail decorators after landing their respective artifacts, flipping
XFAIL -> regular GREEN.

The v0.12.0 deprecation-test subtasks (5+17) used the same
xfail-then-remove pattern; Subtask 2 mirrored it for the `lfg-goal`
SKILL.md contract; this file mirrors it for the receipt-contract surface.

``strict=False`` is intentional: if a later subtask lands a passing
implementation but forgets to remove a decorator, the test reports XPASS
rather than failing the suite.

Decision references (see ``.athanor/sessions/2026-05-22-002/decisions.md``):

- D3 -- receipt is a durable .md artifact (not ephemeral console output)
- D7 -- voice guard: 0 forbidden phrases (none asserted here directly;
  the voice surface is locked by other regression files)

Unlock map (per Subtask 3 dispatch packet "Cross-subtask coordination"):

- Receipt fixtures (tests 1-3) unlock at **Subtask 9**.
- Receipt-validator 9-step verification table (test 4) unlocks at
  **Subtask 7**.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "lfg_goal"
RECEIPT_VALID = FIXTURE_DIR / "receipt_valid.md"
RECEIPT_INVALID_MISSING_STEP3 = FIXTURE_DIR / "receipt_invalid_missing_step3.md"
RECEIPT_PARTIAL_WITH_RESIDUALS = FIXTURE_DIR / "receipt_partial_with_residuals.md"
VALIDATOR_AGENT_PATH = (
    REPO_ROOT / "skills" / "lfg-goal" / "references" / "receipt-validator.md"
)


# ---------------------------------------------------------------------------
# Test 1 -- valid receipt fixture exists
# ---------------------------------------------------------------------------


def test_valid_receipt_fixture_exists():
    """MUST: ``tests/fixtures/lfg_goal/receipt_valid.md`` exists.

    Plan v0.13.0 §Phase 5 ships a triplet of receipt fixtures: one valid
    happy-path receipt, one invalid receipt with a missing Step 3 row,
    and one partial receipt that declares residual work. The
    receipt-validator regression suite consumes them; this contract
    asserts the valid fixture is present so downstream validator tests
    can rely on its path.
    """
    assert RECEIPT_VALID.is_file(), (
        f"Expected receipt fixture at "
        f"{RECEIPT_VALID.relative_to(REPO_ROOT)}; Subtask 9 has not "
        "created it yet."
    )


# ---------------------------------------------------------------------------
# Test 2 -- invalid (missing Step 3) receipt fixture exists
# ---------------------------------------------------------------------------


def test_invalid_missing_step3_fixture_exists():
    """MUST: ``tests/fixtures/lfg_goal/receipt_invalid_missing_step3.md`` exists.

    Plan v0.13.0 §Phase 5 names the structural-violation fixture: a
    receipt that drops the Step 3 row from the 9-step verification
    table. The validator must reject this shape; the fixture is the
    negative test input.
    """
    assert RECEIPT_INVALID_MISSING_STEP3.is_file(), (
        f"Expected receipt fixture at "
        f"{RECEIPT_INVALID_MISSING_STEP3.relative_to(REPO_ROOT)}; "
        "Subtask 9 has not created it yet."
    )


# ---------------------------------------------------------------------------
# Test 3 -- partial-with-residuals receipt fixture exists
# ---------------------------------------------------------------------------


def test_partial_with_residuals_fixture_exists():
    """MUST: ``tests/fixtures/lfg_goal/receipt_partial_with_residuals.md`` exists.

    Plan v0.13.0 §Phase 5 names the residual-declaration fixture: a
    receipt that completes the 9-step table but explicitly carries
    forward unresolved items into the residual list. The validator must
    accept the structural shape while propagating residuals into the
    next cycle's input; the fixture is the lower-bound acceptance
    input.
    """
    assert RECEIPT_PARTIAL_WITH_RESIDUALS.is_file(), (
        f"Expected receipt fixture at "
        f"{RECEIPT_PARTIAL_WITH_RESIDUALS.relative_to(REPO_ROOT)}; "
        "Subtask 9 has not created it yet."
    )


# ---------------------------------------------------------------------------
# Test 4 -- receipt-validator has 9-step verification table
# ---------------------------------------------------------------------------


def test_receipt_validator_has_9_step_verification_table():
    """MUST: ``skills/lfg-goal/references/receipt-validator.md`` declares the 9-step verification table.

    Plan v0.13.0 §Layer 2 §Adversarial 3-tier check makes the
    receipt-validator the sole authority for cycle DONE. The validator
    worker dispatch prompt must enumerate all 9 LFG steps (Step 1 plan,
    Step 2 work, ... Step 9 release) in a verification table whose rows
    pair each step with a concrete Bash verification command and a
    "Required Evidence" column. This test locks the contract.

    Heuristics (each MUST hold):

    1. The validator dispatch prompt file exists at
       ``skills/lfg-goal/references/receipt-validator.md``. (Subtask 7
       canonical path; the Subtask 3 working assumption pointed at
       ``agents/`` which is the directory for Claude Code registered
       agents — receipt-validator is a worker-prompt template embedded
       in Agent() dispatch by the lfg-goal skill leader, so the
       ``skills/<name>/references/`` convention is correct.)
    2. The table headings ``Required Evidence`` and
       ``Verification Command`` both appear (case-sensitive substring).
    3. Each of the literal labels ``Step 1 plan``, ``Step 2 work``,
       ``Step 3 review``, ``Step 4 review-fix commit``,
       ``Step 5 residual handoff``, ``Step 6 browser test``,
       ``Step 7 commit-push-PR``, ``Step 8 CI watch``, ``Step 9 DONE``
       appears in the file body (substring match). Labels are the
       SKILL.md §"Cycle Receipt Format" canonical 9-step taxonomy
       (matching the actual /athanor:lfg step sequence).
    """
    assert VALIDATOR_AGENT_PATH.is_file(), (
        f"Expected validator dispatch prompt at "
        f"{VALIDATOR_AGENT_PATH.relative_to(REPO_ROOT)}; Subtask 7 has "
        "not created it yet."
    )
    body = VALIDATOR_AGENT_PATH.read_text(encoding="utf-8")
    assert "Required Evidence" in body, (
        "validator body must contain the literal 'Required Evidence' table heading"
    )
    assert "Verification Command" in body, (
        "validator body must contain the literal 'Verification Command' table heading"
    )
    step_labels = [
        "Step 1 plan",
        "Step 2 work",
        "Step 3 review",
        "Step 4 review-fix commit",
        "Step 5 residual handoff",
        "Step 6 browser test",
        "Step 7 commit-push-PR",
        "Step 8 CI watch",
        "Step 9 DONE",
    ]
    missing = [label for label in step_labels if label not in body]
    assert not missing, (
        "validator body must enumerate all 9 LFG step labels; missing: "
        f"{missing}"
    )


# ---------------------------------------------------------------------------
# Tests 5-8 -- Subtask 8 (Phase 4b) reference files exist and are well-formed
# ---------------------------------------------------------------------------
#
# These four smoke tests lock the four reference files shipped by Subtask 8:
# - judge-rubric.md (Tier 2 cross-model judge rubric)
# - scope-change-critic.md (mid-flight goal.md modification critic)
# - state-shape.md (state.json persistence shape with cycle_state enum)
# - goal-md-template.md (canonical goal.md structure)
#
# No xfail decorators — impl lands in Subtask 8 alongside these tests
# (test-aware execution_note; tests are GREEN immediately).


def test_judge_rubric_exists_and_has_rubric_axes():
    p = REPO_ROOT / "skills" / "lfg-goal" / "references" / "judge-rubric.md"
    assert p.is_file()
    body = p.read_text(encoding="utf-8")
    assert "R-ID" in body
    assert "AE-ID" in body or "AE-IDs" in body
    assert "cannot infer" in body.lower() or "MUST NOT infer" in body


def test_scope_change_critic_exists():
    p = (
        REPO_ROOT
        / "skills"
        / "lfg-goal"
        / "references"
        / "scope-change-critic.md"
    )
    assert p.is_file()
    body = p.read_text(encoding="utf-8")
    assert "accept" in body.lower()
    assert "reject" in body.lower()
    assert "escalate" in body.lower()


def test_state_shape_has_cycle_state_enum():
    p = REPO_ROOT / "skills" / "lfg-goal" / "references" / "state-shape.md"
    assert p.is_file()
    body = p.read_text(encoding="utf-8")
    assert "cycle_state" in body
    # >=7 fields requirement (heuristic — search for bullet/field markers)
    # The state-shape document enumerates required fields as backtick-quoted
    # identifiers; count distinct ones as a lower-bound sanity check.
    required_fields = [
        "goal_id",
        "cycle_state",
        "current_cycle",
        "last_receipt_path",
        "last_validator_status",
        "tier2_last_verdict",
        "aborted_reason",
    ]
    missing = [f for f in required_fields if f not in body]
    assert not missing, f"state-shape.md missing required field(s): {missing}"


def test_goal_md_template_has_mandatory_sections():
    p = (
        REPO_ROOT
        / "skills"
        / "lfg-goal"
        / "references"
        / "goal-md-template.md"
    )
    assert p.is_file()
    body = p.read_text(encoding="utf-8")
    assert "Verify command" in body
    assert "Test-count command" in body
    assert "scope_change" in body
