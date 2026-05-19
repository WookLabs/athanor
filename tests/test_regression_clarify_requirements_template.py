"""Regression test for v0.9.0 U3 invariant — clarify mode requirements.md
output structure and the vendored requirements-capture template.

When clarify dialog finalizes (user confirms scoping synthesis), the leader
writes .athanor/sessions/{id}/requirements.md using the ce-brainstorm
requirements-capture template (vendored to skills/discuss/references/).

Plan reference: docs/plans/2026-05-19-002-feat-v0.9.0-discuss-clarify-mode-plan.md
§U3 + origin requirement R6.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DISCUSS_SKILL = REPO_ROOT / "skills" / "discuss" / "SKILL.md"
CAPTURE_REF = REPO_ROOT / "skills" / "discuss" / "references" / "requirements-capture.md"


def _load_skill():
    return DISCUSS_SKILL.read_text(encoding="utf-8")


def _load_ref():
    return CAPTURE_REF.read_text(encoding="utf-8")


# --- Step 3-clarify-finalization section ---


def test_finalization_step_exists():
    """MUST: skill prose includes a clarify-finalization step that writes
    requirements.md."""
    body = _load_skill()
    body_lower = body.lower()
    finalization_signals = [
        "step 3-clarify-finalization",
        "step 3 clarify finalization",
        "step 2-clarify finalization",
        "clarify finalization",
        "finalization (clarify",
        "finalization step",
    ]
    matches = [s for s in finalization_signals if s in body_lower]
    assert len(matches) >= 1, (
        f"Skill prose must include a clarify-finalization step. "
        f"Expected one of: {finalization_signals}"
    )


def test_output_path_named_correctly():
    """MUST: skill explicitly names the output path
    `.athanor/sessions/{id}/requirements.md`."""
    body = _load_skill()
    output_signals = [
        ".athanor/sessions/{id}/requirements.md",
        ".athanor/sessions/{session-id}/requirements.md",
        "/requirements.md",
    ]
    assert any(s in body for s in output_signals), (
        f"Skill must name the requirements.md output path. "
        f"Expected one of: {output_signals}"
    )


def test_all_eleven_sections_listed():
    """MUST: skill or reference enumerates the requirements-capture template
    sections. (Summary, Problem Frame, Actors, Key Flows, Requirements,
    Acceptance Examples, Success Criteria, Scope Boundaries, Key Decisions,
    Dependencies, Outstanding Questions = 11 sections.)"""
    # Either the skill body OR the reference file must list all sections
    combined = (_load_skill() + "\n" + _load_ref()).lower()
    required_sections = [
        "summary",
        "problem frame",
        "actors",
        "key flows",
        "requirements",
        "acceptance examples",
        "success criteria",
        "scope boundaries",
        "key decisions",
        "dependencies",
        "outstanding questions",
    ]
    missing = [s for s in required_sections if s not in combined]
    assert not missing, (
        f"Requirements-capture template must enumerate all 11 sections. "
        f"Missing: {missing}"
    )


def test_id_naming_convention_present():
    """MUST: skill or reference describes the ID convention (A-IDs for
    Actors, F-IDs for Flows, R-IDs for Requirements, AE-IDs for Acceptance
    Examples)."""
    combined = _load_skill() + "\n" + _load_ref()
    combined_lower = combined.lower()
    id_signals = ["a-id", "f-id", "r-id", "ae-id"]
    matches = [s for s in id_signals if s in combined_lower]
    assert len(matches) >= 3, (
        f"Template must describe stable-ID naming for at least 3 of the 4 "
        f"prefixes (A/F/R/AE). Found: {matches}"
    )


def test_frontmatter_fields_named():
    """MUST: template specifies the requirements.md frontmatter fields
    (date, topic)."""
    combined = _load_skill() + "\n" + _load_ref()
    combined_lower = combined.lower()
    # frontmatter or YAML keys: date and topic
    assert "date" in combined_lower
    assert "topic" in combined_lower
    # frontmatter format mention
    fm_signals = ["frontmatter", "front matter", "yaml frontmatter", "---\ndate"]
    assert any(s in combined_lower for s in fm_signals) or any(s in combined for s in fm_signals), (
        f"Template must describe frontmatter / YAML header. "
        f"Expected one of: {fm_signals}"
    )


# --- Vendored requirements-capture reference ---


def test_requirements_capture_reference_file_exists():
    """MUST: skills/discuss/references/requirements-capture.md exists."""
    assert CAPTURE_REF.exists(), (
        f"Vendored requirements-capture template must exist at "
        f"skills/discuss/references/requirements-capture.md (per plan U3)"
    )


def test_reference_file_has_provenance_block():
    """MUST: reference file documents its provenance (T2 vendoring pattern,
    MIT license, source — matches v0.7.8 verification-before-completion
    + v0.9.0 clarify-gap-probes pattern)."""
    ref_body = _load_ref()
    ref_lower = ref_body.lower()
    provenance_signals = [
        "provenance:",
        "vendored",
        "source-commit",
        "mit",
        "license",
    ]
    matches = [s for s in provenance_signals if s in ref_lower]
    assert len(matches) >= 2, (
        f"Reference file must include a provenance block. "
        f"Found: {matches}. Expected at least 2 of: {provenance_signals}"
    )


def test_finalization_handoff_to_phase_4():
    """MUST (Covers AE2): after requirements.md is written, the
    finalization step must hand off to the Phase 4 menu (Step 3-clarify-
    handoff, defined in U4)."""
    body = _load_skill()
    body_lower = body.lower()
    handoff_signals = [
        "step 3-clarify-handoff",
        "step 3 clarify handoff",
        "phase 4 menu",
        "phase 4 handoff",
        "clarify-handoff",
        "다음 단계 메뉴",
        "next-step menu",
    ]
    matches = [s for s in handoff_signals if s in body_lower]
    assert len(matches) >= 1, (
        f"Finalization step must explicitly hand off to Phase 4 menu. "
        f"Expected one of: {handoff_signals}"
    )


def test_reference_describes_section_purposes():
    """SHOULD: reference enumerates the per-section purpose/contents so the
    leader can write each section without re-inventing what goes there."""
    ref_body = _load_ref()
    ref_lower = ref_body.lower()
    # Check for section purpose discussion — at least 3 of the section names
    # appear as #/## headings in the reference itself (indicating they're
    # explained, not just listed)
    section_headings = [
        "## summary",
        "## problem frame",
        "## actors",
        "## key flows",
        "## requirements",
        "## acceptance examples",
        "## success criteria",
        "## scope boundaries",
    ]
    found_headings = [h for h in section_headings if h in ref_lower]
    assert len(found_headings) >= 4, (
        f"Reference should explain section purposes via per-section headings "
        f"(at least 4 of {len(section_headings)}). Found: {found_headings}"
    )
