"""Regression test for v0.9.0 U4 invariant — clarify mode Phase 4 handoff
menu (4 options: plan / synthesis chain / analyze / stop).

After requirements.md is written (Step 3-clarify-finalization), the leader
presents a 4-option menu and waits for explicit user selection. No auto-chain.

Codex review (2026-05-19) P1 #3: synthesis-chain re-entry must confirm the
derived Option A/B dilemma before dispatching workers (existing Step 2
contract expects parsed dilemma).

Plan reference: docs/plans/2026-05-19-002-feat-v0.9.0-discuss-clarify-mode-plan.md
§U4 + origin requirement R8.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DISCUSS_SKILL = REPO_ROOT / "skills" / "discuss" / "SKILL.md"


def _load():
    return DISCUSS_SKILL.read_text(encoding="utf-8")


def test_handoff_section_exists():
    """MUST: a Step 3-clarify-handoff (or equivalent) section exists."""
    body = _load()
    body_lower = body.lower()
    handoff_signals = [
        "step 3-clarify-handoff",
        "step 3 clarify handoff",
        "clarify-handoff",
        "## phase 4 menu",
        "phase 4 handoff",
    ]
    assert any(s in body_lower for s in handoff_signals), (
        f"Skill must include a Phase 4 handoff section after clarify "
        f"finalization. Expected one of: {handoff_signals}"
    )


def test_four_options_present():
    """MUST: handoff menu names all 4 options (plan / synthesis chain /
    analyze / stop)."""
    body = _load()
    body_lower = body.lower()
    # Option 1: plan
    assert "/athanor:plan" in body
    # Option 2: synthesis chain (back into same skill, synthesis mode)
    chain_signals = [
        "synthesis chain",
        "synthesis-chain",
        "synthesis 모드로 이어",
        "synthesis 재진입",
        "synthesis re-entry",
        "chain to synthesis",
    ]
    assert any(s in body_lower for s in chain_signals), (
        f"Handoff must include synthesis-chain option. Expected one of: {chain_signals}"
    )
    # Option 3: analyze
    assert "/athanor:analyze" in body
    # Option 4: stop / done
    stop_signals = ["일단 멈춤", "stop", "done", "종료"]
    assert any(s in body_lower for s in stop_signals), (
        f"Handoff must include stop/done option. Expected one of: {stop_signals}"
    )


def test_plan_option_mentions_requirements_md_inject():
    """MUST: plan option prose mentions auto-inject of requirements.md as
    input."""
    body = _load()
    body_lower = body.lower()
    # The plan option should mention requirements.md being auto-injected
    inject_signals = [
        "requirements.md를 input으로 자동 inject",
        "requirements.md를 input",
        "auto-inject requirements.md",
        "input으로 자동 inject",
        "requirements.md as input",
        "input으로 자동",
    ]
    assert any(s in body for s in inject_signals) or any(s in body_lower for s in inject_signals), (
        f"Plan option must mention requirements.md auto-inject. "
        f"Expected one of: {inject_signals}"
    )


def test_synthesis_chain_reuses_same_session():
    """SHOULD: synthesis-chain option uses the same session (not a new one)."""
    body = _load()
    body_lower = body.lower()
    same_session_signals = [
        "same session",
        "같은 session",
        "같은 세션",
        "re-entry into the same",
        "재진입",
    ]
    assert any(s in body for s in same_session_signals) or any(s in body_lower for s in same_session_signals), (
        f"Synthesis-chain option should clarify same-session re-entry. "
        f"Expected one of: {same_session_signals}"
    )


def test_askuserquestion_preference():
    """MUST (Covers AE5): handoff menu prefers AskUserQuestion with fallback
    to numbered list."""
    body = _load()
    body_lower = body.lower()
    # Anchor on the top-level Step 3-clarify-handoff heading (level-3 #'s
    # ONLY — sub-headings start with "####" so we exclude them by requiring
    # exactly "### step 3-clarify-handoff:" with colon).
    handoff_idx = body_lower.find("### step 3-clarify-handoff:")
    if handoff_idx < 0:
        return  # caught by test_handoff_section_exists
    window = body_lower[handoff_idx : handoff_idx + 3000]
    aq_signals = ["askuserquestion", "ask user question", "blocking question tool"]
    fallback_signals = ["numbered list", "fallback", "numbered chat"]
    has_aq = any(s in window for s in aq_signals)
    has_fallback = any(s in window for s in fallback_signals)
    assert has_aq, (
        f"Handoff menu must prefer AskUserQuestion. Expected one of: {aq_signals}"
    )
    assert has_fallback, (
        f"Handoff menu must name fallback to numbered list. "
        f"Expected one of: {fallback_signals}"
    )


def test_stop_option_no_skill_dispatch():
    """MUST: stop option explicitly does NOT auto-dispatch another skill."""
    body = _load()
    body_lower = body.lower()
    no_dispatch_signals = [
        "do not auto-dispatch",
        "no auto-dispatch",
        "종료 announcement",
        "save and stop",
        "save and end",
        "save and exit",
        "저장하고 종료",
        "저장하고 끝",
    ]
    assert any(s in body for s in no_dispatch_signals) or any(s in body_lower for s in no_dispatch_signals), (
        f"Stop option must clearly NOT auto-dispatch a follow-on skill. "
        f"Expected one of: {no_dispatch_signals}"
    )


def test_synthesis_chain_requires_dilemma_confirm():
    """MUST (Codex P1 #3): synthesis-chain re-entry must explicitly confirm
    Option A/B with the user before dispatching workers — the existing
    Step 2 contract assumes a parsed dilemma."""
    body = _load()
    body_lower = body.lower()
    # The synthesis chain option must explain that A/B confirmation happens
    # before worker dispatch
    confirm_signals = [
        "option a/b",
        "option a 또는",
        "a/b로 정리",
        "dilemma confirm",
        "step 1.4",
        "step 1 synthesis confirm",
        "정리해도 됩니까",
        "정리해도 될까",
    ]
    matches = [s for s in confirm_signals if s in body or s in body_lower]
    assert len(matches) >= 1, (
        f"Synthesis-chain re-entry must require Option A/B dilemma confirm "
        f"before dispatching workers (Codex P1 #3 fix). "
        f"Expected one of: {confirm_signals}"
    )
