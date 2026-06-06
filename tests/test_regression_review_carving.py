"""Regression — /athanor:review lens personas carved to a section file (A-2/A-3).

Adopted pattern from gstack v1.56 section-based skill carving (STOP-Read):
move heavy lens-persona + doc-review prose out of skills/review/SKILL.md
into skills/review/references/review-sections.md, loaded on demand after
Step 1.5 lens selection rather than always-loaded. A-3 (carving safety):
the consolidation decision-brief format (Lens Scores + Executive Summary)
must stay intact in the skeleton so behavior is preserved. Static reads only.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REVIEW_SKILL = REPO_ROOT / "skills" / "review" / "SKILL.md"
REVIEW_SECTIONS = REPO_ROOT / "skills" / "review" / "references" / "review-sections.md"

PERSONAS = (
    "correctness",
    "security",
    "performance",
    "testing",
    "maintainability",
    "adversarial",
)


def test_review_sections_reference_has_all_personas_and_doc_mode() -> None:
    """MUST — carved section file retains the 6 personas + doc-review mode."""
    assert REVIEW_SECTIONS.is_file(), (
        "skills/review/references/review-sections.md must exist after carving."
    )
    low = REVIEW_SECTIONS.read_text(encoding="utf-8").lower()
    for p in PERSONAS:
        assert f"persona: {p}" in low, (
            f"review-sections.md must retain the '{p}' persona verbatim "
            f"(carving is a MOVE, not a drop)."
        )
    assert "doc review mode" in low, (
        "review-sections.md must retain the doc-review mode section."
    )


def test_review_skill_stop_read_pointer() -> None:
    """MUST — skill router points to the section file as on-demand load."""
    body = REVIEW_SKILL.read_text(encoding="utf-8")
    assert "review-sections.md" in body, (
        "skills/review/SKILL.md must reference references/review-sections.md."
    )
    assert "on demand" in body.lower() or "stop-read" in body.lower(), (
        "the pointer must mark the load as on-demand / STOP-Read, not "
        "always-loaded."
    )


def test_review_skill_preserves_decision_brief_format() -> None:
    """MUST (A-3) — carving preserves the consolidation decision-brief format."""
    body = REVIEW_SKILL.read_text(encoding="utf-8")
    for anchor in ("## Lens Scores", "## Executive Summary"):
        assert anchor in body, (
            f"carving must not remove the '{anchor}' consolidation anchor — "
            f"the decision-brief format is behavior, not movable prose."
        )


def test_review_skill_personas_not_duplicated_inline() -> None:
    """SHOULD — persona rubric bodies no longer live inline in the skill."""
    body = REVIEW_SKILL.read_text(encoding="utf-8")
    # The skeleton may mention persona names in the manifest, but the full
    # '### Persona: <name>' rubric headers should have moved to the section file.
    inline = sum(f"### Persona: {p}" in body for p in PERSONAS)
    assert inline == 0, (
        f"{inline} persona rubric headers still inline in SKILL.md; they "
        f"should be carved to references/review-sections.md."
    )


def test_review_skill_router_line_cap() -> None:
    """MUST (CG2, v0.18.5) — review/SKILL.md stays a thin router under a hard cap.

    The v0.18.5 adversarial enforcement audit found a complexity-gate gap:
    work/SKILL.md (≤250) and plan/SKILL.md (≤300) are line-capped by regression
    tests, but review/SKILL.md had NO cap and had already drifted to 311 lines.
    Ceiling 320 locks the current size against re-bloat; ratchet toward plan's
    300 budget as lens/persona prose carves into references/review-sections.md
    (the spill target already exists). Closes the gap the audit confirmed.
    """
    n = len(REVIEW_SKILL.read_text(encoding="utf-8").splitlines())
    assert n <= 320, (
        f"skills/review/SKILL.md is {n} lines (cap 320) — carve lens/persona "
        f"prose into references/review-sections.md to keep it a thin router "
        f"(matches the work≤250 / plan≤300 complexity gates)."
    )
