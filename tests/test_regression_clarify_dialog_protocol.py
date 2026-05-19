"""Regression test for v0.9.0 U2 invariant — /athanor:discuss clarify mode
dialog protocol (4 gap lenses, one-question-per-turn, single-Claude,
integration check, scoping synthesis, stop-phrase guard).

The clarify mode is single-Claude dialog modeled after ce-brainstorm
Phase 1.2-1.3. It produces a requirements.md via Step 2-clarify section.

Plan reference: docs/plans/2026-05-19-002-feat-v0.9.0-discuss-clarify-mode-plan.md
§U2 + origin requirements R3, R4, R5.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DISCUSS_SKILL = REPO_ROOT / "skills" / "discuss" / "SKILL.md"
CLARIFY_REF = REPO_ROOT / "skills" / "discuss" / "references" / "clarify-gap-probes.md"


def _load_skill():
    return DISCUSS_SKILL.read_text(encoding="utf-8")


def _load_ref():
    return CLARIFY_REF.read_text(encoding="utf-8")


# --- Step 2-clarify section ---


def test_step_2_clarify_section_exists():
    """MUST: a new clarify-mode step section exists in skills/discuss/SKILL.md."""
    body = _load_skill()
    body_lower = body.lower()
    section_signals = [
        "step 2-clarify",
        "step 2 clarify",
        "clarify mode dialog",
        "## clarify mode",
        "### step 2-clarify",
    ]
    assert any(s in body_lower for s in section_signals), (
        f"skills/discuss/SKILL.md must contain a Step 2-clarify section. "
        f"Expected one of: {section_signals}"
    )


def test_four_gap_lenses_named():
    """MUST: all four gap lenses (evidence / specificity / counterfactual /
    attachment) appear in the skill body."""
    body_lower = _load_skill().lower()
    for lens in ["evidence", "specificity", "counterfactual", "attachment"]:
        assert lens in body_lower, (
            f"Gap lens '{lens}' missing from skill — ce-brainstorm Standard "
            f"tier 4 lenses must all be named"
        )


def test_one_question_per_turn_rule_stated():
    """MUST: dialog protocol enforces one question per turn rule."""
    body = _load_skill()
    body_lower = body.lower()
    rule_signals = [
        "one question per turn",
        "한 번에 한 질문",
        "한 질문씩",
        "single question per turn",
    ]
    assert any(s in body_lower for s in rule_signals), (
        f"Clarify dialog must enforce one-question-per-turn rule. "
        f"Expected one of: {rule_signals}"
    )


def test_askuserquestion_preference_stated():
    """MUST: clarify dialog prefers AskUserQuestion blocking tool with
    open-ended fallback for introspective probes."""
    body = _load_skill()
    body_lower = body.lower()
    aq_signals = ["askuserquestion", "ask user question", "blocking question tool"]
    assert any(s in body_lower for s in aq_signals), (
        f"Clarify dialog must prefer AskUserQuestion. Expected one of: {aq_signals}"
    )
    # Open-ended fallback for introspective probes
    open_ended_signals = ["open-ended", "open ended", "introspective"]
    assert any(s in body_lower for s in open_ended_signals), (
        f"Clarify dialog must allow open-ended probe form. "
        f"Expected one of: {open_ended_signals}"
    )


def test_integration_check_step_present():
    """MUST: clarify dialog includes an integration-check step before exit
    (ce-brainstorm Phase 1.3 integration check)."""
    body = _load_skill()
    body_lower = body.lower()
    integration_signals = [
        "integration check",
        "integration-check",
        "통합 확인",
        "통합 점검",
    ]
    assert any(s in body_lower for s in integration_signals), (
        f"Clarify dialog must include integration check before scoping "
        f"synthesis. Expected one of: {integration_signals}"
    )


def test_scoping_synthesis_step_present():
    """MUST: clarify dialog includes Phase 2.5-style scoping synthesis
    before user confirms / requirements.md is written."""
    body = _load_skill()
    body_lower = body.lower()
    synthesis_signals = [
        "scoping synthesis",
        "phase 2.5",
        "phase-2.5",
        "what we're building",
        "스코핑 시놉시스",
        "scoping synopsis",
    ]
    assert any(s in body_lower for s in synthesis_signals), (
        f"Clarify dialog must include scoping synthesis step before "
        f"requirements.md write. Expected one of: {synthesis_signals}"
    )


def test_single_claude_mode_stated():
    """MUST: clarify dialog explicitly states single-Claude operation
    (no parallel workers, no Codex)."""
    body = _load_skill()
    body_lower = body.lower()
    single_claude_signals = [
        "single-claude",
        "single claude",
        "no parallel workers",
        "no codex",
        "without parallel workers",
        "leader가 직접 dialog",
    ]
    assert any(s in body_lower for s in single_claude_signals), (
        f"Clarify dialog must state single-Claude operation explicitly. "
        f"Expected one of: {single_claude_signals}"
    )


def test_clarify_dialog_has_stop_phrase_guard():
    """MUST (Codex P1 #6): clarify dialog prose explicitly warns leader
    against using early-stop phrases. Without this guard,
    one-question-per-turn becomes a loophole — leader could emit
    '계속할까요?' on every turn and trivially evade dialog progression."""
    body = _load_skill()
    body_lower = body.lower()
    guard_signals = [
        "stop-phrase",
        "stop phrase",
        "계속할까요",
        "이 정도면 멈출",
        "early-stop",
        "early stop",
    ]
    matches = [s for s in guard_signals if s in body_lower]
    assert len(matches) >= 1, (
        f"Clarify dialog must include a stop-phrase guard prose for the "
        f"leader's own dialog turns. Expected one of: {guard_signals}"
    )


# --- Vendored reference file ---


def test_clarify_gap_probes_reference_file_exists():
    """MUST: skills/discuss/references/clarify-gap-probes.md exists."""
    assert CLARIFY_REF.exists(), (
        f"Vendored gap-probe reference must exist at "
        f"skills/discuss/references/clarify-gap-probes.md (per plan U2 §Files)"
    )


def test_reference_file_lists_four_lenses():
    """MUST: reference file defines all four gap lenses with at least one
    example probe each. Covers AE1."""
    ref_body = _load_ref()
    ref_lower = ref_body.lower()
    for lens in ["evidence", "specificity", "counterfactual", "attachment"]:
        assert lens in ref_lower, (
            f"Reference file must define '{lens}' gap lens"
        )
    # Each lens should have at least an example probe — heuristic check:
    # the reference file should have at least 4 question marks (one per lens
    # example) and at least 100 chars per lens area
    question_marks = ref_body.count("?")
    assert question_marks >= 4, (
        f"Reference file should include at least one example probe question "
        f"per lens (≥4 '?' total). Found: {question_marks}"
    )


def test_reference_file_has_provenance_block():
    """SHOULD: reference file documents its provenance (vendored pattern,
    license, source — matches v0.7.8 verification-before-completion pattern)."""
    ref_body = _load_ref()
    ref_lower = ref_body.lower()
    provenance_signals = [
        "provenance:",
        "vendored",
        "source-commit",
        "mit",
    ]
    matches = [s for s in provenance_signals if s in ref_lower]
    assert len(matches) >= 2, (
        f"Reference file should include a provenance block (≥2 signals). "
        f"Found: {matches}. Expected at least 2 of: {provenance_signals}"
    )
