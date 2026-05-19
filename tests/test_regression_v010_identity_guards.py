"""Regression test for v0.10.0 U25 invariants — the four identity
preservation guards (T1-T4) stay in place after the v0.10.0 absorption.

T1: Thin Leader contract — CLAUDE.md §Vendored Surface documents that
    vendored skills run through athanor's worker-dispatch pattern. No
    vendored SKILL.md content is mutated to remove "agent" voice.
T2: Cross-model adversarial planning — `/athanor:plan` continues to
    dispatch Planner A + Planner B + Critic; not silently downgraded to
    CE-vendored single-agent flow.
T3: Spec-then-TDD discipline — `/athanor:work` retains Splitter
    execution_note classification and the conjunction-of-three Phase 3
    gate; vendored ce-work and sp-test-driven-development are explicitly
    OUTSIDE.
T4: Stop hook scope — gate triggers on every Stop; honesty disclosure
    in CLAUDE.md acknowledges vendor-aware whitelist is v0.10.1+ work.

Plan reference: docs/plans/2026-05-19-003-feat-v0.10.0-absorb-ce-superpowers-plan.md
§U25 (T1-T4).
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
PLAN_SKILL = REPO_ROOT / "skills" / "plan" / "SKILL.md"
WORK_SKILL = REPO_ROOT / "skills" / "work" / "SKILL.md"
STOP_HOOK = REPO_ROOT / "scripts" / "hooks" / "stop_verify_claims.py"


# ---- T1: Thin Leader guard ----


def test_claude_md_has_vendored_surface_section():
    """T1: CLAUDE.md contains a section explicitly enumerating the
    identity guard layer for vendored content."""
    text = CLAUDE_MD.read_text(encoding="utf-8")
    lower = text.lower()
    assert "vendored surface" in lower, (
        "CLAUDE.md must contain a §'Vendored Surface' section"
    )
    assert "identity guard layer" in lower, (
        "CLAUDE.md §Vendored Surface must use the phrase 'identity guard layer'"
    )


def test_claude_md_names_all_four_identity_commitments():
    """T1: The four identity commitments are enumerated by name."""
    text = CLAUDE_MD.read_text(encoding="utf-8")
    lower = text.lower()
    for needle in [
        "thin leader",
        "cross-model adversarial planning",
        "spec-then-tdd",
        "stop hook",
    ]:
        assert needle in lower, (
            f"CLAUDE.md §Vendored Surface must mention '{needle}'"
        )


def test_no_vendored_skill_content_was_mutated_to_remove_agent_voice():
    """T1: T2 vendor provenance requires verbatim copies. Spot-check three
    vendored CE skills retain upstream prose voice."""
    sample_paths = [
        REPO_ROOT / "skills" / "ce-plan" / "SKILL.md",
        REPO_ROOT / "skills" / "ce-work" / "SKILL.md",
        REPO_ROOT / "skills" / "ce-brainstorm" / "SKILL.md",
    ]
    for p in sample_paths:
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        # CE skills speak in agent-direct voice ("you", "the agent"). If
        # ALL such voice tokens were stripped, that means we forked
        # instead of vendoring.
        lower = text.lower()
        assert any(t in lower for t in ["you ", "agent", "this skill"]), (
            f"{p.name}: vendored content seems mutated — no agent-voice "
            f"tokens detected; T2 provenance violated"
        )


# ---- T2: Cross-model adversarial planning default ----


def test_athanor_plan_skill_still_dispatches_cross_model():
    """T2: skills/plan/SKILL.md keeps dispatching Planner A + Planner B
    via Codex; no silent downgrade to CE single-agent."""
    text = PLAN_SKILL.read_text(encoding="utf-8")
    lower = text.lower()
    assert "planner a" in lower
    assert "planner b" in lower
    assert "codex" in lower
    # The matrix terms (codex_available / codex.enabled / codex.fallback)
    # signal the cross-model dispatch decision tree is intact
    matrix_signals = ["codex_available", "codex.enabled", "codex.fallback", "self-critic"]
    found = [s for s in matrix_signals if s in text or s in lower]
    assert len(found) >= 2, (
        f"Cross-model dispatch matrix must remain. Found: {found}"
    )


def test_athanor_plan_skill_has_v010_identity_lock():
    """T2: skills/plan/SKILL.md §Identity has a v0.10.0 vendored-surface
    relationship note pinning the cross-model default."""
    text = PLAN_SKILL.read_text(encoding="utf-8")
    lower = text.lower()
    assert "v0.10.0 vendored-surface" in lower, (
        "skills/plan/SKILL.md must declare v0.10.0 identity lock"
    )
    assert "/athanor:ce-plan" in text, (
        "skills/plan/SKILL.md must reference /athanor:ce-plan as the "
        "CE-vendored alternative"
    )


def test_claude_md_commands_table_separates_native_from_vendored():
    """T2: CLAUDE.md Commands table has athanor-native vs vendored
    subsections (or comparable structure) so the cross-model default is
    visible to plugin users."""
    text = CLAUDE_MD.read_text(encoding="utf-8")
    lower = text.lower()
    assert "athanor-native" in lower or "vendored" in lower, (
        "CLAUDE.md Commands table must distinguish native vs vendored"
    )


# ---- T3: Spec-then-TDD discipline native default ----


def test_athanor_work_skill_still_has_splitter():
    """T3: skills/work/SKILL.md retains Spec-then-TDD discipline
    machinery (Splitter, execution_note, conjunction-of-three gate)."""
    text = WORK_SKILL.read_text(encoding="utf-8")
    lower = text.lower()
    assert "splitter" in lower
    assert "execution_note" in lower or "execution-note" in lower
    # Phase 3 gate language
    assert "conjunction" in lower or "phase 3" in lower or "test-aware" in lower


def test_athanor_work_skill_has_v010_identity_lock():
    """T3: skills/work/SKILL.md §Identity has a v0.10.0 vendored-surface
    relationship note explicitly placing /athanor:ce-work and
    /athanor:sp-test-driven-development OUTSIDE the discipline."""
    text = WORK_SKILL.read_text(encoding="utf-8")
    lower = text.lower()
    assert "v0.10.0 vendored-surface" in lower
    assert "/athanor:ce-work" in text
    assert "/athanor:sp-test-driven-development" in text
    assert "outside" in lower


# ---- T4: Stop hook scope honesty ----


def test_stop_hook_docstring_has_v010_scope_disclosure():
    """T4: scripts/hooks/stop_verify_claims.py docstring mentions v0.10.0
    scope (vendor-surface whitelist false-negative honesty)."""
    text = STOP_HOOK.read_text(encoding="utf-8")
    lower = text.lower()
    assert "v0.10.0" in text
    # Look for honesty-arc language
    honesty_signals = [
        "vendor-aware whitelist",
        "vendored prose",
        "false negative",
        "best-effort",
    ]
    found = [s for s in honesty_signals if s in lower]
    assert found, (
        f"stop_verify_claims.py docstring must include v0.10.0 honesty "
        f"language. Found none of: {honesty_signals}"
    )


def test_claude_md_stop_hook_row_has_v010_scope_clarification():
    """T4: CLAUDE.md Stop-hook Defense Mechanisms row has v0.10.0 scope
    disclosure (vendor-aware whitelist is v0.10.1+ work)."""
    text = CLAUDE_MD.read_text(encoding="utf-8")
    # Locate the Stop-hook row (within Defense Mechanisms)
    lines = text.splitlines()
    in_defense = False
    stop_row = ""
    for line in lines:
        if line.startswith("## Defense Mechanisms"):
            in_defense = True
            continue
        if in_defense and line.startswith("## ") and not line.startswith("## Defense"):
            break
        if in_defense and "Completion-Claim Verification" in line and line.lstrip().startswith("|"):
            stop_row = line
            break
    assert stop_row, "CLAUDE.md must have Completion-Claim Verification row in Defense Mechanisms"
    lower = stop_row.lower()
    assert "v0.10.0" in lower or "vendor" in lower, (
        f"Stop-hook row must include v0.10.0 scope clarification. Row: {stop_row[:200]}"
    )
