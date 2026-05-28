"""Regression test for the v0.7.7 M5 finding — plan/SKILL.md tier-aware Step 3/4 intros.

Pins the rewrite of Step 3 and Step 4 introductions to be tier-aware. The
old prose ("After BOTH planners return...", "After BOTH reviewers return...")
was deep-tier-presumptive and silently misled standard/lite tier readers.

Covers:
  - Step 3 intro names all three tiers (Deep / Standard / Lite)
  - Step 4 intro names all three tiers (Deep / Standard / Lite)
  - "After BOTH planners return" phrase absent at top level
  - "After BOTH reviewers return" phrase absent at top level

Plan reference: `.athanor/sessions/2026-05-18-001/plan.md` §4 M5.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLAN_SKILL = REPO_ROOT / "skills" / "plan" / "SKILL.md"


def _load_plan_skill() -> str:
    """Load skills/plan/SKILL.md spliced with all references/*.md.

    S02 (v0.17.x) split the plan skill into a thin router (<=300 lines)
    + references/. Existing prose-level checks scan the combined surface
    so the tier-prose invariants (Step 2/3/4 tier-aware preambles)
    remain locked across the split. Reference files are concatenated in
    sorted order — Step 2 prose lives in SKILL.md, Step 3/4 detail in
    `references/{planner,reviewer,critic-*}.md`.
    """
    text = PLAN_SKILL.read_text(encoding="utf-8")
    references_dir = PLAN_SKILL.parent / "references"
    if references_dir.is_dir():
        for ref in sorted(references_dir.glob("*.md")):
            text += "\n\n" + ref.read_text(encoding="utf-8")
    return text


def extract_section(content: str, start_heading: str, *end_patterns: str) -> str:
    """Slice content between a starting heading line and the first end-pattern line.

    `start_heading` and `end_patterns` are matched as line-prefixes (a line
    that starts with the given string). Returns the slice including the
    start_heading line and up to (but not including) the first matching end
    line. If no end pattern matches, returns to end-of-file.
    """
    lines = content.splitlines()
    start_idx = None
    for i, line in enumerate(lines):
        if line.startswith(start_heading):
            start_idx = i
            break
    if start_idx is None:
        return ""
    end_idx = len(lines)
    for j in range(start_idx + 1, len(lines)):
        for pat in end_patterns:
            if lines[j].startswith(pat):
                end_idx = j
                break
        if end_idx != len(lines):
            break
    return "\n".join(lines[start_idx:end_idx])


# ---- tests ----

def test_step_3_intro_has_tier_labels():
    """Step 3 intro (between `### Step 3:` and first `####` or `### Step 4:`) must name all three tiers."""
    content = _load_plan_skill()
    intro = extract_section(content, "### Step 3:", "#### ", "### Step 4:")
    assert intro, "Step 3 section not found in skills/plan/SKILL.md"
    missing = [
        label for label in ("Deep tier:", "Standard tier:", "Lite tier:")
        if label not in intro
    ]
    assert not missing, (
        f"Step 3 intro must name all three tiers; missing labels: {missing}.\n"
        f"v0.7.7 M5 requires tier-aware preamble (Deep / Standard / Lite)."
    )


def test_step_4_intro_has_tier_labels():
    """Step 4 intro (between `### Step 4:` and next heading) must name all three tiers."""
    content = _load_plan_skill()
    # End at Step 5 (next H3 sibling) or the next H2 — spec: "end-of-file or
    # next top-level heading". Either form keeps all three tier labels in slice.
    intro = extract_section(content, "### Step 4:", "### Step 5:", "## ")
    assert intro, "Step 4 section not found in skills/plan/SKILL.md"
    missing = [
        label for label in ("Deep tier:", "Standard tier:", "Lite tier:")
        if label not in intro
    ]
    assert not missing, (
        f"Step 4 intro must name all three tiers; missing labels: {missing}.\n"
        f"v0.7.7 M5 requires tier-aware preamble (Deep / Standard / Lite)."
    )


def test_step_2_intro_has_tier_labels():
    """Step 2 intro must name all three tiers (v0.7.8 U8 — PR #10 review residual).

    v0.7.7 fixed Step 3 + Step 4 intros but missed Step 2, which still said
    "Dispatch TWO planners simultaneously" — true only for deep tier; misled
    standard/lite readers. v0.7.8 U8 closes the residual.
    """
    content = _load_plan_skill()
    intro = extract_section(content, "### Step 2:", "#### ", "### Step 3:")
    assert intro, "Step 2 section not found in skills/plan/SKILL.md"
    missing = [
        label for label in ("Deep tier:", "Standard tier:", "Lite tier:")
        if label not in intro
    ]
    assert not missing, (
        f"Step 2 intro must name all three tiers; missing labels: {missing}.\n"
        f"v0.7.8 U8 (PR #10 review residual) requires tier-aware preamble "
        f"parallel to the Step 3/4 fix."
    )


def test_step_2_intro_does_not_unconditionally_say_dispatch_two():
    """The v0.7.7 generic preamble 'Dispatch TWO planners **simultaneously**.'
    must not appear in the Step 2 intro (it's deep-tier-only behavior)."""
    content = _load_plan_skill()
    intro = extract_section(content, "### Step 2:", "#### ", "### Step 3:")
    assert intro, "Step 2 section not found in skills/plan/SKILL.md"
    # The exact v0.7.7 phrasing (with markdown emphasis) is the forbidden form
    assert "Dispatch TWO planners **simultaneously**" not in intro, (
        "Step 2 intro contains the v0.7.7 generic preamble. v0.7.8 U8 should "
        "have replaced this with the tier-aware Deep/Standard/Lite preamble."
    )


def test_no_generic_after_both_planners():
    """The deep-tier-presumptive phrase 'After BOTH planners return' must NOT appear."""
    content = _load_plan_skill()
    assert "After BOTH planners return" not in content, (
        "Found 'After BOTH planners return' in skills/plan/SKILL.md — this is "
        "the deep-tier-presumptive prose that v0.7.7 M5 explicitly removed."
    )


def test_no_generic_after_both_reviewers():
    """The deep-tier-presumptive phrase 'After BOTH reviewers return' must NOT appear."""
    content = _load_plan_skill()
    assert "After BOTH reviewers return" not in content, (
        "Found 'After BOTH reviewers return' in skills/plan/SKILL.md — this is "
        "the deep-tier-presumptive prose that v0.7.7 M5 explicitly removed."
    )
