"""Regression test for the v0.7.8 R10/U10 invariant — work skill detects the
`<!-- athanor:review-skipped -->` marker prepended to plan.md when the Critic
pass was skipped (e.g., codex.fallback=skip with no review files).

Producer side: `skills/plan/SKILL.md`
  - Standard tier pass-through prepends the marker when review_strategy=none.
  - Deep tier 2-input Critic variant (v0.7.8 U9) instructs the Critic to
    prepend the marker.

Consumer side: `skills/work/SKILL.md` Step 0 sub-step 2a
  - Greps for the marker on plan.md line 1 (`head -1 | grep -Fq`).
  - Announces a warning if found, then continues normal flow.

Without this consumer detection the producer contract is orphaned — exactly
the v0.7.7 PR #10 review residual that v0.7.8 U10 was supposed to close.

This test pins:
  1. work/SKILL.md contains the marker literal.
  2. work/SKILL.md announces "Working from an unreviewed plan" (or
     equivalent advisory wording).
  3. The detection logic appears in Step 0 area (before Step 1 dispatch),
     so the announcement fires before any work begins.
  4. work/SKILL.md cites the Bash one-liner for the check (`head -1 ... grep`).
  5. plan/SKILL.md (producer side) still prepends the marker in both
     standard-tier pass-through AND deep-tier 2-input Critic variant.

Plan reference: docs/plans/2026-05-18-001-feat-v0.7.8-stop-hook-command-mode-plan.md
§R10 + §U10.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORK_SKILL = REPO_ROOT / "skills/work/SKILL.md"
PLAN_SKILL = REPO_ROOT / "skills/plan/SKILL.md"

MARKER_LITERAL = "<!-- athanor:review-skipped -->"


def _load(path):
    return path.read_text(encoding="utf-8")


def _extract_step_0(content):
    """Return the body between '### Step 0:' and the next '### Step '."""
    lines = content.splitlines()
    start_idx = None
    for i, line in enumerate(lines):
        if line.startswith("### Step 0"):
            start_idx = i
            break
    if start_idx is None:
        return ""
    end_idx = len(lines)
    for j in range(start_idx + 1, len(lines)):
        if lines[j].startswith("### Step ") and "Step 0" not in lines[j]:
            end_idx = j
            break
    return "\n".join(lines[start_idx:end_idx])


# --- Consumer side: work skill -----------------------------------------------


def test_work_skill_contains_marker_literal():
    content = _load(WORK_SKILL)
    assert MARKER_LITERAL in content, (
        f"work/SKILL.md must contain the literal marker {MARKER_LITERAL!r} "
        f"so the consumer detection grep matches the producer output."
    )


def test_work_skill_announces_unreviewed_plan():
    content = _load(WORK_SKILL)
    # Accept either the exact spec phrase or a clear equivalent.
    announcement_signals = [
        "Working from an unreviewed plan",
        "unreviewed plan",
        "review_strategy=none",
        "Critic refinement pass",
    ]
    assert any(s in content for s in announcement_signals), (
        f"work/SKILL.md must announce one of {announcement_signals} when "
        f"detecting the review-skipped marker — otherwise the user has no "
        f"signal they're executing an unreviewed plan."
    )


def test_marker_detection_lives_in_step_0():
    """The detection must fire before Step 1 dispatch so the announcement
    is visible before any work begins."""
    content = _load(WORK_SKILL)
    step_0_body = _extract_step_0(content)
    assert MARKER_LITERAL in step_0_body, (
        "Marker detection must be in Step 0 (before dispatch). Found marker "
        "literal elsewhere or not at all."
    )


def test_marker_detection_cites_bash_grep_reference():
    """The detection prose must show the Bash one-liner so a leader can
    implement the check directly."""
    content = _load(WORK_SKILL)
    step_0_body = _extract_step_0(content)
    # The reference Bash is `head -1 ... | grep -Fq '<!-- athanor:review-skipped -->'`
    assert "head -1" in step_0_body, (
        "Step 0 marker-detection should cite `head -1` Bash reference for "
        "the check (so it operates on line 1 only — sentinel-anchor parity "
        "with the Stop hook script)."
    )
    assert "grep" in step_0_body, "Step 0 must cite `grep` for the marker match."


# --- Producer side: plan skill -----------------------------------------------


def test_plan_skill_standard_tier_passthrough_prepends_marker():
    """Standard tier pass-through (review_strategy=none) writes plan.md with
    the marker as line 1. This was v0.7.7's contract; v0.7.8 preserves it."""
    content = _load(PLAN_SKILL)
    assert MARKER_LITERAL in content, (
        f"plan/SKILL.md must reference the marker literal {MARKER_LITERAL!r} "
        f"so the consumer (work/SKILL.md) and producer agree on the contract."
    )
    # Also assert the Bash pass-through uses printf to prepend the marker
    assert "printf" in content and "review-skipped" in content, (
        "plan/SKILL.md Step 4 pass-through should use `printf '<!-- "
        "athanor:review-skipped -->\\n'` to prepend the marker on line 1."
    )


def test_plan_skill_deep_tier_2_input_critic_variant_exists():
    """v0.7.8 U9 adds the explicit deep-tier 2-input Critic dispatch for
    review_strategy=none. Without this, the deep-tier dispatch hardcodes
    4 input files and silently fails when reviews are absent."""
    content = _load(PLAN_SKILL)
    # The variant subsection should be present and named explicitly
    assert "Deep Tier: 2-Input Synthesis Critic" in content, (
        "plan/SKILL.md must contain `#### Deep Tier: 2-Input Synthesis Critic` "
        "subsection (v0.7.8 U9) — the 4-input variant alone leaves the "
        "review_strategy=none deep-tier path malformed."
    )


def test_plan_skill_2_input_variant_instructs_marker_prepend():
    """The deep-tier 2-input Critic must prepend the marker so /work detects."""
    content = _load(PLAN_SKILL)
    # Find the 2-Input section
    import re as _re
    match = _re.search(
        r"#### Deep Tier: 2-Input Synthesis Critic.*?(?=####|\Z)",
        content,
        _re.DOTALL,
    )
    assert match, "Deep Tier 2-Input Synthesis Critic subsection not found"
    section = match.group(0)
    assert MARKER_LITERAL in section, (
        "The deep-tier 2-input Critic variant must instruct the Critic to "
        "prepend the review-skipped marker — otherwise /work can't detect "
        "the deep-tier-no-reviews case."
    )
