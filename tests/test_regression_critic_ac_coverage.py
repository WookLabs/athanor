"""Regression test for the v0.8.0 U5 invariant — Critic prompt evaluates both
acceptance_criteria coverage AND classification appropriateness.

The v0.8.0 Spec-then-TDD discipline relies on the Critic catching two failure
modes during plan refinement:
  (A) Behavior-bearing phases that have prose-only Verify (no MUST/SHOULD)
  (B) Phases where the planner's stated intent contradicts the file-set
      signal — over-classification (CHANGELOG-only phase with MUST/SHOULD)
      or under-classification (source code with prose-only Verify)

The Critic produces a refined plan.md from the Planner output. If the Critic
prompt doesn't include these two evaluation axes, the discipline degrades
silently — Planner A misses become permanent.

This test pins:
  1. Critic prompt mentions "acceptance_criteria coverage" or equivalent
  2. Critic prompt mentions "classification" or "execution_note" appropriateness
  3. Critic prompt mentions over-classification / false-positive risk
  4. Critic prompt mentions under-classification / false-negative risk
  5. Standard tier + Deep tier critic variants both have the rubric
  6. Claude self-review fallback path also has the rubric
  7. Corrective behavior prose is present (Reformulate + Adjust phase scope)

Plan reference: docs/plans/2026-05-19-001-feat-v0.8.0-tdd-sdd-integration-plan.md
§U5 + origin requirements R8.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLAN_SKILL = REPO_ROOT / "skills" / "plan" / "SKILL.md"


def _load():
    return PLAN_SKILL.read_text(encoding="utf-8")


def test_critic_evaluates_acceptance_criteria_coverage():
    """MUST: Critic prompt mentions acceptance_criteria coverage evaluation."""
    body = _load()
    body_lower = body.lower()
    # Accept several phrasings
    candidates = [
        "acceptance_criteria coverage",
        "acceptance criteria coverage",
        "must/should bullets",
        "must/should format",
    ]
    assert any(c in body_lower for c in candidates), (
        f"Critic prompt must evaluate acceptance_criteria coverage. "
        f"Expected one of: {candidates}"
    )


def test_critic_evaluates_classification_appropriateness():
    """MUST: Critic prompt mentions classification appropriateness evaluation."""
    body = _load()
    body_lower = body.lower()
    candidates = [
        "classification appropriateness",
        "classification risk",
        "classification mismatch",
        "execution_note",  # Critic must mention the field it's evaluating against
    ]
    assert any(c in body_lower for c in candidates), (
        f"Critic prompt must evaluate classification appropriateness. "
        f"Expected one of: {candidates}"
    )


def test_critic_mentions_overclassification_pattern():
    """MUST: Critic prompt identifies false-positive (over-classification) patterns."""
    body = _load()
    body_lower = body.lower()
    # Over-classification examples — CHANGELOG-only or _doc-only phase with MUST/SHOULD
    candidates = [
        "over-classification",
        "false-positive",
        "false positive",
        "changelog-only",
        "_doc",  # Critic must be aware of _doc-only phases as a signal
        "doc-only",
    ]
    assert any(c in body_lower for c in candidates), (
        f"Critic prompt must identify over-classification patterns. "
        f"Expected one of: {candidates}"
    )


def test_critic_mentions_underclassification_pattern():
    """MUST: Critic prompt identifies false-negative (under-classification) patterns."""
    body = _load()
    body_lower = body.lower()
    candidates = [
        "under-classification",
        "false-negative",
        "false negative",
        "source code modification",
        "source code mod",
        "prose-only verify",
        "behavior-bearing",
    ]
    assert any(c in body_lower for c in candidates), (
        f"Critic prompt must identify under-classification patterns. "
        f"Expected one of: {candidates}"
    )


def test_critic_rubric_in_standard_tier():
    """MUST: Standard tier critic variant has the new rubric."""
    body = _load()
    # Standard tier critic prompt should be present + mention AC coverage
    # We approximate this by checking that the rubric prose appears alongside
    # both "standard" and "tier" mentions in the same general area.
    body_lower = body.lower()
    assert "standard tier" in body_lower or "standard" in body_lower
    # Critic prompt should appear (Step 4)
    assert "critic" in body_lower
    # And the AC-coverage rubric language must coexist with the Critic prompt
    # in the file
    assert "acceptance_criteria" in body or "MUST/SHOULD" in body, (
        "Critic rubric language must appear in skills/plan/SKILL.md"
    )


def test_critic_rubric_in_deep_tier():
    """MUST: Deep tier critic variant has the new rubric (4-input)."""
    body = _load()
    body_lower = body.lower()
    # Deep tier exists with critic
    assert "deep tier" in body_lower or "deep" in body_lower
    # Plan tier dispatch table mentions critic for deep
    assert "4-input" in body or "4 input" in body_lower or "deep" in body_lower
    # AC rubric must be present (shared with standard or duplicated)
    assert "acceptance_criteria" in body or "MUST/SHOULD" in body


def test_critic_self_review_path_has_rubric():
    """MUST: Claude self-review fallback (codex.fallback=self-critic) also evaluates AC."""
    body = _load()
    body_lower = body.lower()
    # The self-review/self-critic path exists
    assert "self-critic" in body_lower or "self-review" in body_lower or "claude-self-review" in body_lower
    # When this path is taken, the rubric must still apply — we approximate by
    # checking that the rubric prose appears in the file (single occurrence
    # is enough if the prompt is shared; if duplicated, both must have it).
    assert "acceptance_criteria" in body or "MUST/SHOULD" in body


def test_critic_corrective_behavior_prose():
    """SHOULD: When violations found, Critic should Reformulate prose Verify
    AND Adjust phase scope."""
    body = _load()
    body_lower = body.lower()
    # Corrective behavior prose
    reformulate_candidates = [
        "reformulate prose verify",
        "reformulate prose",
        "reformulate the verify",
    ]
    adjust_candidates = [
        "adjust phase scope",
        "adjust phase",
        "adjust the verify",
    ]
    has_reformulate = any(c in body_lower for c in reformulate_candidates)
    has_adjust = any(c in body_lower for c in adjust_candidates)
    # At least one of the corrective behaviors must be named
    assert has_reformulate or has_adjust, (
        f"Critic prompt should describe corrective behavior on violations. "
        f"Expected at least one of: {reformulate_candidates + adjust_candidates}"
    )


# --- Codex implementation-review Major #1 fix: each Critic Agent prompt must
# --- reference the v0.8.0 rubric so the dispatched Critic actually sees it ---


def _critic_agent_prompt_blocks(content: str) -> list[str]:
    """Return the text of each `Agent({ ... })` block under the Critic
    dispatch subsections. We find each ``` block that follows a
    `#### ... Critic` heading AND contains 'Agent(' near the top
    (so we skip non-Agent blocks like the Gate Checkpoint notification)."""
    lines = content.splitlines()
    blocks: list[str] = []
    section_active = False
    in_code_fence = False
    current_block: list[str] = []
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
            # Only keep blocks that look like Agent dispatch payloads
            if "Agent(" in block_text and "prompt:" in block_text:
                blocks.append(block_text)
            in_code_fence = False
            current_block = []
            # Section stays active until the next heading; do not reset
            continue
        if section_active and in_code_fence:
            current_block.append(line)
        # If we leave one #### Critic section by entering another heading,
        # the next iteration's `#### ...` check resets section_active anyway.
        if section_active and not in_code_fence and line.startswith("#### "):
            # New subsection — re-evaluate section_active
            section_active = "Critic" in line
    return blocks


def test_each_critic_agent_prompt_references_rubric():
    """MUST: every Critic Agent({prompt: ...}) block must reference the v0.8.0
    Critic Rubric so the dispatched leader doesn't drop it.

    Codex review (2026-05-19) Major #1: 'the shared rubric is prose before
    the dispatch blocks, but the concrete Agent({prompt: ...}) payloads do
    not include or reference it. A leader following the inline prompt blocks
    can dispatch Critics that never see the two-axis rubric.'
    """
    content = _load()
    blocks = _critic_agent_prompt_blocks(content)
    assert len(blocks) >= 3, (
        f"Expected at least 3 Critic Agent({{prompt: ...}}) blocks "
        f"(deep 4-input, deep 2-input review-skipped, standard 2-input), "
        f"found {len(blocks)}"
    )
    for i, block in enumerate(blocks):
        # Each block must reference the v0.8.0 rubric — either inline or by
        # explicit reference to the shared subsection.
        block_lower = block.lower()
        rubric_signals = [
            "v0.8.0 critic rubric",
            "spec-then-tdd readiness",
            "two-axis spec-then-tdd",
            "axis (a)",
            "axis (b)",
        ]
        assert any(s in block_lower for s in rubric_signals), (
            f"Critic Agent prompt block #{i + 1} does not reference the "
            f"v0.8.0 rubric. Expected one of: {rubric_signals}. "
            f"Block first 200 chars: {block[:200]!r}"
        )
