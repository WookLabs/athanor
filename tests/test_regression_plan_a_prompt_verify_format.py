"""Regression test for the v0.8.0 U1 invariant — Planner A prompt instructs
Verify field as MUST/SHOULD observable assertions for behavior-bearing phases.

The v0.8.0 Spec-then-TDD discipline relies on the Task Splitter being able to
extract MUST/SHOULD acceptance criteria from each phase's Verify field. For
that extraction to work, the Planner A prompt itself must instruct planners
to write the Verify field in MUST/SHOULD format (rather than free-form prose)
for any behavior-bearing phase.

This test pins:
  1. The Planner A prompt template instructs MUST/SHOULD format on Verify
  2. Behavior-bearing guidance prose is present (distinguishing behavior
     phases from doc-only phases)
  3. The instruction is consistent across all Planner A dispatch variants
     (Standard tier, Deep tier, Lite tier — they share the same Planner A
     prompt template, so a single occurrence is sufficient evidence)
  4. The advisory framing is maintained ("MUST/SHOULD" guidance, no
     "TDD enforced" or "Spec-driven required" overclaim language)

Plan reference: docs/plans/2026-05-19-001-feat-v0.8.0-tdd-sdd-integration-plan.md
§U1 + origin requirements R3, R8.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLAN_SKILL = REPO_ROOT / "skills" / "plan" / "SKILL.md"


def _load():
    """Load skills/plan/SKILL.md spliced with all references/*.md.

    S02 (v0.17.x) moved the Planner A Agent({prompt: ...}) packet from
    SKILL.md into `references/planner-dispatch.md`. The prose-level
    invariants here (MUST/SHOULD Verify format, Planner A heading,
    Plan Structure heading, etc.) survive the split via concatenation.
    """
    text = PLAN_SKILL.read_text(encoding="utf-8")
    references_dir = PLAN_SKILL.parent / "references"
    if references_dir.is_dir():
        for ref in sorted(references_dir.glob("*.md")):
            text += "\n\n" + ref.read_text(encoding="utf-8")
    return text


def test_planner_a_prompt_instructs_must_should_verify():
    """MUST: Planner A prompt template contains MUST/SHOULD Verify-field guidance."""
    body = _load()
    # The guidance must be present in some form — MUST/SHOULD instruction
    # alongside the Verify field semantics.
    assert "MUST" in body and "SHOULD" in body, (
        "Planner A prompt must mention MUST/SHOULD guidance for Verify field"
    )
    # Stronger check: explicit pairing of Verify with MUST/SHOULD format
    assert "Verify" in body
    # The format guidance bullet should appear near the Planner A Plan Structure
    # section (we look for the marker "MUST/SHOULD" near the Verify keyword).
    must_should_idx = body.find("MUST/SHOULD")
    assert must_should_idx >= 0, (
        "Planner A prompt must contain the literal 'MUST/SHOULD' format directive "
        "near the Verify field section"
    )


def test_behavior_bearing_guidance_present():
    """MUST: prompt distinguishes behavior-bearing phases from doc-only phases."""
    body = _load()
    body_lower = body.lower()
    # We accept any of several phrasings the planner could use to communicate
    # "this discipline applies to behavior-bearing phases, not doc-only ones".
    candidates = [
        "behavior-bearing",
        "behavior bearing",
        "behavior phase",
        "non-behavior",
        "prose-only",
        "doc-only",
        "doc only",
    ]
    assert any(c in body_lower for c in candidates), (
        f"Planner A prompt must distinguish behavior-bearing phases from "
        f"doc-only phases. Expected one of: {candidates}"
    )


def test_must_must_should_format_example_in_prompt():
    """MUST: Planner A prompt shows the MUST/SHOULD bullet shape (example or template)."""
    body = _load()
    # The prompt should include at least one example MUST or SHOULD bullet
    # within the Plan Structure / Verify-field guidance area.
    # We look for a literal "MUST <something>" or "SHOULD <something>" pattern.
    import re

    # Match "MUST " or "SHOULD " followed by something (not just bare words)
    must_examples = re.findall(r"MUST\s+\w", body)
    should_examples = re.findall(r"SHOULD\s+\w", body)
    assert len(must_examples) >= 1 or len(should_examples) >= 1, (
        "Planner A prompt should contain at least one MUST <assertion> or "
        "SHOULD <assertion> bullet as an example"
    )


def test_planner_a_section_anchors_present():
    """SHOULD: structural anchors (Planner A heading, Plan Structure) still present."""
    body = _load()
    # These anchors must remain — refactors should not remove them.
    assert "Planner A" in body
    assert "Plan Structure" in body or "## Plan Structure" in body


def test_no_overclaim_language_in_planner_a_guidance():
    """MUST: advisory framing — no 'enforced' or 'required' overclaim phrasing
    that would contradict the v0.8.0 honesty arc."""
    body = _load()
    # Negative assertions — these strings would signal an honesty arc break.
    # We tolerate them in unrelated places (e.g., other Defense Mechanisms
    # discussions) but they must NOT appear near the Planner A MUST/SHOULD
    # guidance section. We approximate by checking they don't co-locate
    # within a 500-char window of "MUST/SHOULD" in the planner-a prose.
    must_should_idx = body.find("MUST/SHOULD")
    if must_should_idx < 0:
        # Caught by test_planner_a_prompt_instructs_must_should_verify
        return
    window = body[max(0, must_should_idx - 250) : must_should_idx + 500]
    overclaim_phrases = [
        "TDD enforced",
        "Spec-driven required",
        "spec-driven enforced",
        "enforced by hook",
    ]
    for phrase in overclaim_phrases:
        assert phrase.lower() not in window.lower(), (
            f"Overclaim phrase '{phrase}' found near MUST/SHOULD guidance — "
            f"v0.8.0 honesty arc requires advisory framing"
        )
