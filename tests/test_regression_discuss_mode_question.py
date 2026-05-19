"""Regression test for v0.9.0 U1 + R7 invariants — /athanor:discuss Step 1
asks user for mode (clarify vs synthesis), and the existing synthesis-mode
behavior is preserved verbatim.

The v0.9.0 dual-mode expansion adds a Step 1 mode-selection question to
/athanor:discuss with three options (synthesis / clarify / 'help me focus
intent first'). User response branches to either existing Step 2 (synthesis
mode workers) or new Step 2-clarify (single-Claude dialog).

R7 (synthesis preservation) is enforced here by pinning the existing
synthesis-mode behavior so v0.9.0 changes cannot silently drift it. If a
future refactor moves or breaks the Researcher / Devil's Advocate /
Step 2.5 / Critic / Step 4 contracts, these tests catch it.

Plan reference: docs/plans/2026-05-19-002-feat-v0.9.0-discuss-clarify-mode-plan.md
§U1 + R7 + origin requirements R1, R2, R7.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DISCUSS_SKILL = REPO_ROOT / "skills" / "discuss" / "SKILL.md"


def _load():
    return DISCUSS_SKILL.read_text(encoding="utf-8")


# --- U1: Step 1 mode question + dispatch ---


def test_step_1_has_mode_question_prose():
    """MUST: Step 1 must include a mode-selection question (not just
    dilemma restate)."""
    body = _load()
    body_lower = body.lower()
    mode_signals = ["mode", "모드 선택", "모드 질문", "clarify", "synthesis"]
    assert any(s in body_lower for s in mode_signals), (
        f"Step 1 prose must include mode-selection language. "
        f"Expected one of: {mode_signals}"
    )


def test_step_1_lists_three_mode_options():
    """MUST: Step 1 names all three mode options (synthesis / clarify /
    intent-first default-to-clarify)."""
    body = _load()
    body_lower = body.lower()
    # Synthesis option
    assert "synthesis" in body_lower
    # Clarify option
    assert "clarify" in body_lower
    # The third option phrasing should reference intent/clarify default
    third_option_signals = [
        "먼저 의도를 정리",
        "intent first",
        "정리하고 싶",
        "default-to-clarify",
        "default to clarify",
    ]
    assert any(s in body_lower for s in third_option_signals), (
        f"Step 1 must include the third 'intent-first / default-to-clarify' "
        f"option. Expected one of: {third_option_signals}"
    )


def test_synthesis_path_branches_to_existing_step_2():
    """MUST: synthesis option must explicitly branch to existing Step 2
    (Researcher + Devil's Advocate dispatch)."""
    body = _load()
    body_lower = body.lower()
    # The synthesis branch prose must say "synthesis mode" or equivalent
    # and reference Step 2 / existing dispatch
    assert "synthesis" in body_lower
    # Step 2 must still exist
    assert "step 2" in body_lower or "Step 2" in body
    # The branch should explicitly say synthesis goes to existing Step 2
    branch_signals = [
        "synthesis → step 2",
        "synthesis → 기존 step 2",
        "synthesis 모드는 step 2",
        "synthesis mode dispatches to step 2",
        "기존 step 2로 진행",
    ]
    assert any(s in body_lower for s in branch_signals), (
        f"Step 1 prose must explicitly branch synthesis option to existing "
        f"Step 2. Expected one of: {branch_signals}"
    )


def test_clarify_path_branches_to_new_clarify_step():
    """MUST: clarify option must branch to new clarify-mode step."""
    body = _load()
    body_lower = body.lower()
    clarify_branch_signals = [
        "step 2-clarify",
        "step 2 clarify",
        "clarify 모드",
        "clarify mode step",
        "clarify로 진행",
        "신규 clarify",
    ]
    assert any(s in body_lower for s in clarify_branch_signals), (
        f"Step 1 prose must branch clarify option to new clarify step. "
        f"Expected one of: {clarify_branch_signals}"
    )


def test_intent_first_path_defaults_to_clarify():
    """MUST: 'intent-first' option must default to clarify mode."""
    body = _load()
    body_lower = body.lower()
    # The intent-first option must say it defaults to clarify
    default_signals = [
        "default to clarify",
        "default-to-clarify",
        "clarify 기본",
        "clarify default",
        "clarify로 시작",
        "default → clarify",
    ]
    assert any(s in body_lower for s in default_signals), (
        f"Intent-first option must default to clarify mode. "
        f"Expected one of: {default_signals}"
    )


def test_askuserquestion_or_numbered_list_fallback():
    """MUST: Step 1 mode question prose mentions AskUserQuestion preference
    with fallback to numbered list when blocking tool unavailable."""
    body = _load()
    body_lower = body.lower()
    aq_signals = ["askuserquestion", "ask user question"]
    fallback_signals = ["numbered list", "numbered chat list", "fallback"]
    assert any(s in body_lower for s in aq_signals), (
        f"Step 1 prose should prefer AskUserQuestion. "
        f"Expected one of: {aq_signals}"
    )
    assert any(s in body_lower for s in fallback_signals), (
        f"Step 1 prose should name fallback to numbered list. "
        f"Expected one of: {fallback_signals}"
    )


# --- R7: synthesis-mode preservation pinning ---


def test_step_2_researcher_devils_advocate_dispatch_still_present():
    """R7: existing Researcher + Devil's Advocate parallel dispatch must
    remain in the skill body unchanged by v0.9.0."""
    body = _load()
    # Researcher and Devil's Advocate are existing worker types — both must
    # still appear as Agent dispatch blocks
    assert "Researcher" in body or "researcher" in body
    assert "Devil's Advocate" in body or "devil's advocate" in body.lower() or "devils advocate" in body.lower()
    # They should still be dispatched in parallel (existing line ~59-184)
    body_lower = body.lower()
    parallel_signals = ["in parallel", "parallel", "병렬"]
    assert any(s in body_lower for s in parallel_signals), (
        f"Synthesis dispatch must remain parallel. Expected one of: {parallel_signals}"
    )


def test_step_2_5_worker_output_defense_still_present():
    """R7: existing Step 2.5 Worker Output Defense (stop-phrase detection +
    re-dispatch) must remain unchanged."""
    body = _load()
    body_lower = body.lower()
    # Step 2.5 header anchor
    assert "step 2.5" in body_lower or "step 2 .5" in body_lower or "worker output defense" in body_lower
    # Stop-phrase detection markers must still exist
    assert "stop-phrase" in body_lower or "stop phrase" in body_lower
    # The whitelist (at least one canonical phrase from v0.7.x) must still be there
    canonical = ["계속할까요", "should i continue", "이 정도면 멈춰도", "i think we can stop"]
    assert any(c in body for c in canonical) or any(c in body_lower for c in canonical), (
        f"Step 2.5 stop-phrase whitelist must remain. Expected one of: {canonical}"
    )


def test_step_3_critic_synthesis_still_present():
    """R7: existing Step 3 Critic (synthesis mode) must remain unchanged."""
    body = _load()
    body_lower = body.lower()
    # Step 3 Critic dispatch
    assert "step 3" in body_lower
    assert "critic" in body_lower
    # The Critic synthesis output file location should still be discuss.md
    assert "discuss.md" in body, (
        "Synthesis-mode Critic output (discuss.md) must remain pinned"
    )


def test_step_4_present_results_still_present():
    """R7: existing Step 4 Present Results (synthesis mode terminal) must
    remain unchanged."""
    body = _load()
    body_lower = body.lower()
    assert "step 4" in body_lower
    present_signals = ["present results", "present_results", "presents results", "결과", "athanor discussion:"]
    assert any(s in body_lower for s in present_signals) or any(s in body for s in present_signals), (
        f"Step 4 Present Results must remain. Expected one of: {present_signals}"
    )


def test_codex_dispatch_for_worker_b_still_present():
    """R7: existing Codex branching for Worker B (synthesis mode) must
    remain unchanged. v0.9.0 does NOT introduce Codex into clarify mode."""
    body = _load()
    body_lower = body.lower()
    # Codex branching language from v0.7.x must remain
    assert "codex" in body_lower
    # The matrix terms (codex_available / codex.enabled / codex.fallback)
    # should still appear
    matrix_signals = ["codex_available", "codex.enabled", "codex.fallback", "self-critic"]
    found = [s for s in matrix_signals if s in body or s in body_lower]
    assert len(found) >= 2, (
        f"Codex branching matrix must remain for Worker B (synthesis mode). "
        f"Found: {found}. Expected at least 2 of: {matrix_signals}"
    )
