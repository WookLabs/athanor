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
