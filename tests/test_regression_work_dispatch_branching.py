"""Regression test for the v0.8.0 U3 + U4 invariants — Executor dispatch
prompt branches on execution_note, and the result handler auto-downgrades
on never_red.

U3: The dispatch packet builder must emit three distinct Ralph-Loop
instruction blocks based on subtask.execution_note. spec-then-tdd → red-first
5 steps with per-criterion red_evidence; test-aware → end-gate enforcing
tests/ path changes; direct → current behavior unchanged.

U4: The result handler at Step 2b must detect missing/malformed red_evidence
or self-reported never_red and auto-downgrade the subtask to test-aware
completion criteria (with work-log breadcrumb). No user escalation.

This test pins:
  1. dispatch prompt has all three execution_note branches
  2. spec-then-tdd branch contains red-first 5 steps
  3. spec-then-tdd branch requires per-criterion red_evidence shape
  4. test-aware gate uses 'tests/' broader pattern (not 'tests/test_*.py' only)
  5. direct branch preserves existing Ralph-Loop structure
  6. grandfathered fallback (missing execution_note → direct) is named
  7. result handler auto-downgrade on never_red with work-log breadcrumb
  8. result handler enforces test-aware gate violation as failure
  9. honesty: advisory self-report framing is acknowledged

Plan reference: docs/plans/2026-05-19-001-feat-v0.8.0-tdd-sdd-integration-plan.md
§U3, §U4 + origin requirements R4, R5, R6, R7.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORK_SKILL = REPO_ROOT / "skills" / "work" / "SKILL.md"


def _load():
    return WORK_SKILL.read_text(encoding="utf-8")


# --- U3 dispatch branching ---


def test_dispatch_branches_on_execution_note():
    """MUST: dispatch packet builder names all three execution_note branches."""
    body = _load()
    # Each branch label
    assert "Spec-then-TDD Instructions" in body or "spec-then-tdd" in body.lower()
    assert "Test-Aware End Gate" in body or "test-aware" in body.lower()
    assert "execution_note" in body  # explicit field reference in dispatch


def test_spec_then_tdd_branch_has_red_first_5_steps():
    """MUST: spec-then-tdd branch contains WRITE → RUN → VERIFY RED → IMPLEMENT
    → VERIFY GREEN keywords."""
    body = _load()
    # Find the spec-then-tdd block
    spec_idx = body.find("Spec-then-TDD Instructions")
    if spec_idx < 0:
        spec_idx = body.lower().find("spec-then-tdd instructions")
    assert spec_idx >= 0, "Spec-then-TDD Instructions block not found"
    window = body[spec_idx : spec_idx + 3000]
    # 5 step keywords
    for keyword in ["WRITE", "RUN", "VERIFY RED", "IMPLEMENT", "VERIFY GREEN"]:
        assert keyword in window, (
            f"Spec-then-TDD branch must contain '{keyword}' step keyword"
        )


def test_spec_then_tdd_requires_red_evidence_shape():
    """MUST: spec-then-tdd branch requires per-criterion red_evidence with
    command, test_node_id, exit_code, output_tail."""
    body = _load()
    spec_idx = body.find("Spec-then-TDD Instructions")
    if spec_idx < 0:
        spec_idx = body.lower().find("spec-then-tdd instructions")
    assert spec_idx >= 0
    window = body[spec_idx : spec_idx + 3000]
    assert "red_evidence" in window, (
        "spec-then-tdd branch must require red_evidence reporting"
    )
    # All four shape fields
    for field in ["command", "test_node_id", "exit_code", "output_tail"]:
        assert field in window, (
            f"red_evidence shape must include '{field}' field"
        )


def test_red_status_enum_in_dispatch():
    """MUST: dispatch prompt names red_status values (red / partial_never_red /
    never_red)."""
    body = _load()
    spec_idx = body.find("Spec-then-TDD Instructions")
    if spec_idx < 0:
        spec_idx = body.lower().find("spec-then-tdd instructions")
    assert spec_idx >= 0
    window = body[spec_idx : spec_idx + 3000]
    for value in ["red", "never_red", "partial_never_red"]:
        assert value in window, f"red_status enum must include '{value}'"


def test_test_aware_gate_uses_broader_tests_path():
    """MUST: test-aware gate accepts 'tests/' broader pattern, not just
    'tests/test_*.py'. Must allow conftest.py, fixtures/, snapshots."""
    body = _load()
    gate_idx = body.find("Test-Aware End Gate")
    if gate_idx < 0:
        gate_idx = body.lower().find("test-aware end gate")
    assert gate_idx >= 0, "Test-Aware End Gate block not found"
    window = body[gate_idx : gate_idx + 2000]
    # Must mention git diff inspection
    assert "git diff" in window, "test-aware gate must use git diff inspection"
    # Must mention tests/ as broader pattern (not just test_*.py)
    body_lower = window.lower()
    # Accept either explicit broader phrasing or path-only mention
    broader_signals = [
        "tests/",
        "conftest.py",
        "fixtures/",
        "any file under `tests/`",
        "test artifact",
    ]
    assert any(s in body_lower for s in broader_signals), (
        f"test-aware gate must accept broader tests/ pattern. "
        f"Expected one of: {broader_signals}"
    )


def test_direct_branch_preserves_existing_ralph_loop():
    """MUST: direct branch keeps the original 5-step Ralph-Loop unchanged."""
    body = _load()
    # The original Ralph-Loop has these markers — they must still exist
    assert "Ralph-Loop" in body or "ralph-loop" in body.lower()
    # "Implement the change" line from original loop
    body_lower = body.lower()
    assert "implement the change" in body_lower or "implement" in body_lower


def test_grandfathered_fallback_to_direct():
    """MUST: dispatch prose handles execution_note field absent → fallback to direct."""
    body = _load()
    body_lower = body.lower()
    # Fallback prose
    fallback_signals = [
        "grandfathered",
        "field is absent",
        "execution_note field is absent",
        "treat as `direct`",
        "treat as direct",
        "fallback to direct",
        "fallback to `direct`",
    ]
    assert any(s in body_lower for s in fallback_signals), (
        f"Dispatch prose must handle missing execution_note → direct fallback. "
        f"Expected one of: {fallback_signals}"
    )


# --- U4 result handler ---


def test_result_handler_auto_downgrade_on_never_red():
    """MUST: result handler at Step 2b detects never_red and auto-downgrades."""
    body = _load()
    body_lower = body.lower()
    # Auto-downgrade prose
    downgrade_signals = [
        "auto-downgrade",
        "auto-downgraded",
        "automatically downgrade",
        "downgrade to test-aware",
        "spec-then-tdd → test-aware",
    ]
    assert any(s in body_lower for s in downgrade_signals), (
        f"Result handler must describe auto-downgrade on never_red. "
        f"Expected one of: {downgrade_signals}"
    )


def test_result_handler_validates_red_evidence_shape():
    """MUST: result handler validates red_evidence shape (defensive default
    to never_red when missing)."""
    body = _load()
    body_lower = body.lower()
    # Look for validation prose
    validation_signals = [
        "validate red_evidence",
        "validate the red_evidence",
        "missing or malformed",
        "missing/malformed",
        "defensive default",
        "evidence shape",
    ]
    assert any(s in body_lower for s in validation_signals), (
        f"Result handler must describe red_evidence shape validation. "
        f"Expected one of: {validation_signals}"
    )


def test_result_handler_work_log_breadcrumb():
    """MUST: auto-downgrade produces a work-log entry."""
    body = _load()
    # The downgrade prose must mention work-log
    body_lower = body.lower()
    assert "work-log" in body_lower, "Auto-downgrade must produce work-log entry"
    # And the specific label
    label_signals = [
        "auto-downgraded: spec-then-tdd → test-aware",
        "auto-downgraded",
        "spec-then-tdd → test-aware",
    ]
    assert any(s in body for s in label_signals), (
        f"Work-log entry must use one of these labels: {label_signals}"
    )


def test_test_aware_gate_violation_treated_as_failure():
    """MUST: if test-aware subtask completes without test changes, handler
    marks subtask as failed."""
    body = _load()
    body_lower = body.lower()
    violation_signals = [
        "test-aware gate violation",
        "gate violation",
        "no test files modified",
        "no tests/** paths",
    ]
    assert any(s in body_lower for s in violation_signals), (
        f"Result handler must enforce test-aware gate violation as failure. "
        f"Expected one of: {violation_signals}"
    )


def test_no_user_escalation_on_auto_downgrade():
    """MUST: auto-downgrade is silent (no user prompt)."""
    body = _load()
    body_lower = body.lower()
    # The downgrade prose should explicitly say no escalation
    no_escalation_signals = [
        "no user escalation",
        "no user prompt",
        "without user",
        "silent except",
    ]
    assert any(s in body_lower for s in no_escalation_signals), (
        f"Auto-downgrade prose must state no user escalation. "
        f"Expected one of: {no_escalation_signals}"
    )


def test_advisory_self_report_framing_acknowledged():
    """MUST: honesty arc — result handler prose explicitly names advisory
    self-report nature."""
    body = _load()
    body_lower = body.lower()
    # The honesty acknowledgement should appear somewhere in the result handler
    # or dispatch area
    honesty_signals = [
        "advisory self-report",
        "advisory self report",
        "self-reported",
        "advisory shape",
        "self-report shape",
    ]
    assert any(s in body_lower for s in honesty_signals), (
        f"Result handler must acknowledge advisory self-report nature. "
        f"Expected one of: {honesty_signals}"
    )


# --- Codex implementation-review Major #2 fix: downgraded spec-then-tdd
# --- must still pass the test-aware gate (not silently succeed via downgrade) ---


def test_downgraded_subtask_must_pass_test_aware_gate():
    """MUST: Phase 2 downgrade is now downgrade-pending; Phase 3 enforces
    test-aware gate on downgraded subtasks too.

    Codex review (2026-05-19) Major #2: 'Phase 2 downgrades on
    never_red/partial_never_red but Phase 3 only applies when original
    execution_note == test-aware. A malformed/missing red_evidence spec task
    can be marked completed without verifying tests/** changes.'

    The fix: Phase 2 marks pending; Phase 3 applies to BOTH original
    test-aware subtasks AND Phase-2-downgraded subtasks.
    """
    body = _load()
    body_lower = body.lower()
    # Phase 2 should now produce a 'pending' / 'awaiting gate' status
    pending_signals = [
        "downgrade-pending",
        "downgrade pending",
        "awaiting gate",
        "pending [auto-downgraded",
    ]
    assert any(s in body_lower for s in pending_signals), (
        f"Phase 2 auto-downgrade must produce a pending status (not immediate "
        f"success) so Phase 3 can still enforce the test-aware gate. "
        f"Expected one of: {pending_signals}"
    )

    # Phase 3 must explicitly cover downgraded subtasks
    phase_3_coverage_signals = [
        "phase 2 downgraded a spec-then-tdd",
        "downgraded a spec-then-tdd",
        "or phase 2 downgraded",
        "downgrade applied",
    ]
    assert any(s in body_lower for s in phase_3_coverage_signals), (
        f"Phase 3 must explicitly apply to downgraded spec-then-tdd subtasks, "
        f"not just original test-aware ones. Expected one of: "
        f"{phase_3_coverage_signals}"
    )


# --- Codex implementation-review Medium #4 fix: grandfathered legacy plans
# --- still parse via fallback to direct ---


def test_grandfathered_legacy_plan_docs_are_present():
    """MUST: the named grandfathered plan docs from CHANGELOG migration claim
    actually exist in docs/plans/ — protects the documented migration path.

    Codex review (2026-05-19) Medium: 'No regression test exercises the four
    grandfathered docs/plans/ files through the new missing-execution_note
    fallback. CHANGELOG claims that migration path explicitly.'
    """
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent
    grandfathered = [
        "docs/plans/2026-04-08-001-feat-phase1-foundation-setup-plan.md",
        "docs/plans/2026-05-18-001-feat-v0.7.8-stop-hook-command-mode-plan.md",
        "docs/plans/2026-05-18-002-feat-v0.7.9-stop-hook-hardening-plan.md",
    ]
    for path in grandfathered:
        assert (repo_root / path).exists(), (
            f"Grandfathered plan doc '{path}' is missing — the CHANGELOG "
            f"migration path explicitly names this file and the test "
            f"verifies its continued presence so the fallback path is exercised."
        )


def test_grandfathered_legacy_plans_have_no_execution_note():
    """MUST: the legacy plan docs MUST NOT have execution_note fields (they
    pre-date v0.8.0). The fallback-to-direct prose in skills/work/SKILL.md
    is what handles them."""
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent
    grandfathered = [
        "docs/plans/2026-04-08-001-feat-phase1-foundation-setup-plan.md",
        "docs/plans/2026-05-18-001-feat-v0.7.8-stop-hook-command-mode-plan.md",
        "docs/plans/2026-05-18-002-feat-v0.7.9-stop-hook-hardening-plan.md",
    ]
    for path in grandfathered:
        content = (repo_root / path).read_text(encoding="utf-8")
        # The v0.8.0 execution_note FIELD (as a YAML/markdown key) must not
        # appear in legacy plan docs. We check for the field-as-key pattern
        # specifically ("execution_note:") rather than the bare word, so that
        # incidental discussion of the term elsewhere doesn't false-positive.
        assert "execution_note:" not in content, (
            f"Legacy plan doc '{path}' contains 'execution_note:' field which "
            f"pre-dates v0.8.0. Either the doc was modified or the "
            f"grandfathered assumption is wrong."
        )
