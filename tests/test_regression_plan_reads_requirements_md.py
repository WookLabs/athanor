"""Regression test for v0.9.0 U5 invariant — /athanor:plan Step 1 auto-loads
session requirements.md and Critic Rubric gains axis (C) R-ID traceback
coverage.

When the same session has a requirements.md (clarify-mode artifact from U3),
plan Step 1 must inject its content into the Planner A prompt so phase
Verify fields can cite-back origin R/A/F/AE-IDs. The Critic Rubric is
extended with axis (C) to flag missing cite-backs during plan refinement.

Plan reference: docs/plans/2026-05-19-002-feat-v0.9.0-discuss-clarify-mode-plan.md
§U5 + origin requirement R9.

Codex review (2026-05-19) P1 #5: R-ID traceback is likely weak in practice
unless Critic actively reviews for it — hence axis (C).
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLAN_SKILL = REPO_ROOT / "skills" / "plan" / "SKILL.md"


def _load():
    return PLAN_SKILL.read_text(encoding="utf-8")


# --- U5: Step 1 reads requirements.md ---


def test_plan_step_1_mentions_requirements_md():
    """MUST: /athanor:plan Step 1 explicitly names requirements.md as an
    input source alongside discuss.md / analyze.md."""
    body = _load()
    # Step 1 area is around line 110-117 in skills/plan/SKILL.md
    body_lower = body.lower()
    assert "requirements.md" in body_lower, (
        "Plan skill must reference requirements.md as a Step 1 input source"
    )


def test_plan_step_1_mentions_inject_to_planner_a():
    """MUST: Plan Step 1 prose says requirements.md content gets inject into
    the Planner A prompt (not just read)."""
    body = _load()
    body_lower = body.lower()
    inject_signals = [
        "inject",
        "into planner a",
        "context for planners",
        "planner a's prompt",
        "planner a context",
    ]
    assert any(s in body_lower for s in inject_signals), (
        f"Plan Step 1 must mention injecting context to Planner A. "
        f"Expected one of: {inject_signals}"
    )


def test_plan_step_1_backwards_compat_when_absent():
    """MUST: Plan Step 1 prose handles requirements.md absence gracefully —
    backwards compat with pre-v0.9.0 sessions."""
    body = _load()
    body_lower = body.lower()
    bc_signals = [
        "backwards compat",
        "backwards-compat",
        "backward compat",
        "if absent",
        "if they exist",
        "부재 시",
        "absent → current",
    ]
    # The Step 1 already says "If they exist, read them" — that handles
    # backwards compat naturally. We just need at least one such signal.
    matches = [s for s in bc_signals if s in body_lower]
    assert len(matches) >= 1, (
        f"Plan Step 1 must handle requirements.md absence gracefully. "
        f"Expected one of: {bc_signals}"
    )


def test_plan_step_1_mentions_r_id_traceback():
    """MUST: Plan Step 1 instructs Planner A to cite-back R-IDs (or A/F/AE
    IDs) in phase Verify fields when requirements.md is present. This is
    the compound effect with v0.8.0 MUST/SHOULD Verify discipline."""
    body = _load()
    body_lower = body.lower()
    # R-ID traceback prose
    traceback_signals = [
        "cite-back",
        "cite back",
        "r-id",
        "r-ids",
        "r/a/f/ae",
        "trace back",
        "traceback",
    ]
    matches = [s for s in traceback_signals if s in body_lower]
    assert len(matches) >= 1, (
        f"Plan Step 1 (or v0.9.0 integration prose) must mention R-ID "
        f"cite-back. Expected one of: {traceback_signals}"
    )


def test_plan_step_1_mentions_v0_9_0_or_introduction_marker():
    """MUST (Covers AE3): Plan Step 1 prose marks the v0.9.0 introduction of
    requirements.md input — either by version tag or by 'NEW' marker."""
    body = _load()
    body_lower = body.lower()
    marker_signals = [
        "v0.9.0",
        "new (v0.9.0)",
        "new in v0.9.0",
        "v0.9.0 input",
        "(new)",
    ]
    matches = [s for s in marker_signals if s in body_lower]
    assert len(matches) >= 1, (
        f"Plan Step 1 must mark requirements.md as a v0.9.0 new input. "
        f"Expected one of: {marker_signals}"
    )


# --- U5 + Codex P1 #5: Critic Rubric axis (C) ---


def test_critic_rubric_includes_r_id_cite_back_axis():
    """MUST (Codex P1 #5): Critic Rubric mentions axis (C) — R-ID cite-back
    coverage — when requirements.md is present."""
    body = _load()
    body_lower = body.lower()
    # Find the v0.8.0 Critic Rubric section anchor
    rubric_idx = body_lower.find("v0.8.0 critic rubric")
    assert rubric_idx >= 0, (
        "Critic Rubric section (v0.8.0) not found in plan skill"
    )
    # Within the rubric section, axis (C) should be mentioned
    window = body_lower[rubric_idx : rubric_idx + 5000]
    axis_c_signals = [
        "axis (c)",
        "axis c)",
        "(c) r-id",
        "(c) cite-back",
        "(c) trace",
        "r-id cite-back",
        "r-id traceback",
    ]
    matches = [s for s in axis_c_signals if s in window]
    assert len(matches) >= 1, (
        f"Critic Rubric must include axis (C) R-ID cite-back coverage. "
        f"Expected one of: {axis_c_signals}"
    )


def test_planner_a_prompt_template_lists_requirements_md():
    """MUST (Codex implementation review P1 #1): Planner A's actual Agent
    prompt template — not just Step 1 prose — must include requirements.md
    in its 'Context from Previous Stages' file list. Without this, the
    dispatched Planner A worker never reads requirements.md."""
    body = _load()
    # Find the Planner A prompt — anchor on "Athanor Planner A" inside an
    # Agent({...}) block.
    pa_idx = body.find("Athanor Planner A")
    assert pa_idx >= 0, "Planner A prompt block not found"
    # The Context section follows shortly after. Search forward from pa_idx.
    window = body[pa_idx : pa_idx + 4000]
    assert "requirements.md" in window, (
        "Planner A prompt template must reference requirements.md in its "
        "Context section (not just in Step 1 prose). Without this, the "
        "dispatched worker never sees the requirements doc."
    )


def test_codex_planner_b_prompt_lists_requirements_md():
    """MUST (Codex implementation review P1 #1): Codex Planner B's
    dispatched prompt must also mention requirements.md so the contrarian
    plan also traces back to origin requirements."""
    body = _load()
    # Find the Codex Planner B prompt — anchor on the Codex exec command.
    # Flag-agnostic regex anchor — survives future flag changes (per v0.13.1 review).
    m = re.search(r'codex .*\bexec\b.*--ephemeral.*-o \.athanor/sessions', body)
    assert m, "Codex Planner B dispatch not found"
    codex_idx = m.start()
    window = body[codex_idx : codex_idx + 3000]
    assert "requirements.md" in window, (
        "Codex Planner B prompt must reference requirements.md in its "
        "Context. Without this, contrarian plans skip the origin trace."
    )


def test_all_three_critic_agent_prompts_read_requirements_md():
    """MUST (Codex implementation review P1 #2): all 3 Critic Agent prompts
    must list requirements.md as a conditional input file. Without this,
    Critic axis (C) rubric cannot evaluate cite-back coverage because the
    Critic never reads requirements.md."""
    body = _load()
    # Find all 3 Critic Agent prompt blocks via existing parser logic
    lines = body.splitlines()
    blocks = []
    section_active = False
    in_code_fence = False
    current_block = []
    for line in lines:
        if line.startswith("#### ") and "Critic" in line:
            section_active = True
            continue
        if section_active and not in_code_fence and line.startswith("```"):
            in_code_fence = True
            current_block = []
            continue
        if section_active and in_code_fence and line.startswith("```"):
            block_text = "\n".join(current_block)
            if "Agent(" in block_text and "prompt:" in block_text:
                blocks.append(block_text)
            in_code_fence = False
            current_block = []
            continue
        if section_active and in_code_fence:
            current_block.append(line)
        if section_active and not in_code_fence and line.startswith("#### "):
            section_active = "Critic" in line

    assert len(blocks) >= 3, (
        f"Expected at least 3 Critic Agent prompt blocks; found {len(blocks)}"
    )
    for i, block in enumerate(blocks):
        assert "requirements.md" in block, (
            f"Critic Agent prompt block #{i + 1} must list requirements.md "
            f"as conditional input so axis (C) rubric can actually evaluate "
            f"R-ID cite-back coverage. Without this, the rubric exists but "
            f"the Critic can't apply it."
        )


def test_all_three_critic_agent_prompts_include_axis_c():
    """MUST (Codex P1 #5): all 3 Critic Agent prompt blocks (deep 4-input,
    deep 2-input review-skipped, standard 2-input) reference axis (C) so
    the dispatched leader actually sees the R-ID rubric."""
    body = _load()
    # Locate each Critic Agent({prompt: ...}) block using the same parser
    # logic as test_regression_critic_ac_coverage.py
    lines = body.splitlines()
    blocks = []
    section_active = False
    in_code_fence = False
    current_block = []
    for line in lines:
        if line.startswith("#### ") and "Critic" in line:
            section_active = True
            continue
        if section_active and not in_code_fence and line.startswith("```"):
            in_code_fence = True
            current_block = []
            continue
        if section_active and in_code_fence and line.startswith("```"):
            block_text = "\n".join(current_block)
            if "Agent(" in block_text and "prompt:" in block_text:
                blocks.append(block_text)
            in_code_fence = False
            current_block = []
            continue
        if section_active and in_code_fence:
            current_block.append(line)
        if section_active and not in_code_fence and line.startswith("#### "):
            section_active = "Critic" in line

    assert len(blocks) >= 3, (
        f"Expected at least 3 Critic Agent prompt blocks; found {len(blocks)}"
    )
    for i, block in enumerate(blocks):
        block_lower = block.lower()
        # Each block must reference axis (C) R-ID rubric inline (so the
        # dispatched Critic sees it, not just the shared subsection)
        axis_c_signals = [
            "axis (c)",
            "r-id cite-back",
            "r-id traceback",
            "cite-back r-id",
            "traceback coverage",
        ]
        assert any(s in block_lower for s in axis_c_signals), (
            f"Critic Agent prompt block #{i + 1} must reference axis (C) "
            f"R-ID rubric inline. Expected one of: {axis_c_signals}. "
            f"Block first 300 chars: {block[:300]!r}"
        )
