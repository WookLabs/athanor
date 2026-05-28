"""Regression tests for v0.12.0 honesty-voice prose updates (Subtask 17).

Plan reference: docs/plans/2026-05-22-001-feat-v0.12.0-concept-kernel-cutover-plan-b.md
§Phase 6 (Subtasks 18 + 19) — release prose voice updates.

All tests in this file are marked xfail with strict=False because the
prose surfaces they check (CHANGELOG.md, docs/STATE.md, CLAUDE.md) are
edited by Subtasks 18 and 19. The locks are landed here in Subtask 17
so the prose work in Phase 6 has a known target shape to flip green.

Invariants checked:

- CHANGELOG.md `## [0.12.0]` section names the v0.12.0 cutover as a
  "plan-of-record misread" event (D7 honesty discipline). This is the
  literal phrasing required by the plan-of-record.
- CHANGELOG.md `## [0.12.0]` section body contains none of the four
  forbidden D7 phrases ("translated", "interpreted", "we discovered",
  "natural maturation").
- docs/STATE.md §"Current Phase" references v0.12.0 by version literal
  so the project state honestly reflects the cutover release.
- docs/STATE.md content describing v0.12.0 also avoids the four
  forbidden D7 phrases.
- CLAUDE.md acknowledges the v0.12.0 scope correction explicitly so the
  project instructions match the post-cutover reality (the §"Vendored
  Surface" section needs a v0.12.0 update).

Voice constraints (D7): docstrings here use direct attribution to the
plan-of-record + the v0.12.0 honesty discipline. The forbidden D7
phrases ("translated", "interpreted", "we discovered", "natural
maturation") do not appear in this file's prose.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG_PATH = REPO_ROOT / "CHANGELOG.md"
STATE_MD_PATH = REPO_ROOT / "docs" / "STATE.md"
CLAUDE_MD_PATH = REPO_ROOT / "CLAUDE.md"

FORBIDDEN_PHRASES = (
    "translated",
    "interpreted",
    "we discovered",
    "natural maturation",
)


def _extract_v012_section(body: str) -> str:
    """Return the body of `## [0.12.0]` in CHANGELOG.md, or empty string."""
    # Match `## [0.12.0]` through the next `## [` heading (or end of file).
    pattern = re.compile(
        r"^##\s+\[0\.12\.0\][^\n]*\n(.*?)(?=^##\s+\[|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(body)
    return m.group(1) if m else ""


def test_changelog_v012_has_plan_of_record_misread():
    """MUST 2.a — CHANGELOG.md `## [0.12.0]` section contains literal
    'plan-of-record misread'.

    Pending Subtask 18. The phrase is the D7 honesty literal for the
    v0.12.0 cutover event.
    """
    body = CHANGELOG_PATH.read_text(encoding="utf-8")
    section = _extract_v012_section(body)
    assert section, (
        "CHANGELOG.md must have a '## [0.12.0]' section post-Subtask 18"
    )
    assert "plan-of-record misread" in section, (
        "CHANGELOG.md '## [0.12.0]' section must contain the literal "
        "'plan-of-record misread' phrase (D7 honesty discipline)"
    )


def test_changelog_v012_no_forbidden_phrases():
    """MUST 2.b — CHANGELOG.md `## [0.12.0]` section body avoids the four
    forbidden D7 phrases.

    Pending Subtask 18.
    """
    body = CHANGELOG_PATH.read_text(encoding="utf-8")
    section = _extract_v012_section(body)
    assert section, (
        "CHANGELOG.md must have a '## [0.12.0]' section post-Subtask 18"
    )
    section_lower = section.lower()
    hits = [phrase for phrase in FORBIDDEN_PHRASES if phrase in section_lower]
    assert not hits, (
        f"CHANGELOG.md '## [0.12.0]' section voice violation; "
        f"found forbidden phrase(s) {hits!r}"
    )


def test_state_md_v012_current_phase():
    """MUST 2.c — docs/STATE.md §"Current Phase" references a current
    series version (0.12.x / 0.13.x / 0.14.x) by version literal.

    Originally pinned to v0.12.0 (Subtask 19). Lock-step relaxed in
    v0.13.1 to accept 0.12.x or 0.13.x literals — Current Phase advances
    with each release; this test's role is to ensure §"Current Phase"
    is present and version-literal-anchored, not to pin one specific
    release forever. v0.14.3 extends to accept 0.14.x.
    """
    body = STATE_MD_PATH.read_text(encoding="utf-8")
    # Find §"Current Phase" heading + capture body to next sibling heading.
    pattern = re.compile(
        r"^##\s+Current Phase[^\n]*\n(.*?)(?=^##\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(body)
    assert m, (
        "docs/STATE.md must have a '## Current Phase' section "
        "post-Subtask 19"
    )
    # Include the matched heading line for version-literal scanning so the
    # heading-only form `## Current Phase: v0.14.x — ...` qualifies.
    current_phase_section = m.group(0)
    assert (
        "0.12." in current_phase_section
        or "0.13." in current_phase_section
        or "0.14." in current_phase_section
        or "0.15." in current_phase_section
        or "0.16." in current_phase_section
    ), (
        "docs/STATE.md '## Current Phase' must reference a current-series "
        "(0.12.x / 0.13.x / 0.14.x / 0.15.x / 0.16.x) version literal"
    )


def test_state_md_no_v012_forbidden_phrases():
    """MUST 2.d — docs/STATE.md content describing v0.12.0 avoids the four
    forbidden D7 phrases.

    Pending Subtask 19. Scans the whole file body — Subtask 19 prose may
    sit in §"Current Phase" or in a §"v0.12.0" detail subsection.
    """
    body = STATE_MD_PATH.read_text(encoding="utf-8")
    # Restrict to paragraphs that mention v0.12.0 — those are the lines
    # Subtask 19 introduces and must keep clean.
    lines = body.splitlines()
    v012_lines = [
        line for line in lines
        if "v0.12.0" in line or "0.12.0" in line
    ]
    assert v012_lines, (
        "docs/STATE.md must have at least one line mentioning v0.12.0 "
        "post-Subtask 19"
    )
    joined = "\n".join(v012_lines).lower()
    hits = [phrase for phrase in FORBIDDEN_PHRASES if phrase in joined]
    assert not hits, (
        f"docs/STATE.md v0.12.0-related content voice violation; "
        f"found forbidden phrase(s) {hits!r}"
    )


def test_claude_md_has_v012_acknowledgment():
    """MUST 2.e — CLAUDE.md mentions v0.12.0 scope-correction explicitly.

    Pending Subtask 19. The §"Vendored Surface" section needs a v0.12.0
    update to record the post-cutover reality (vendored carry-over =
    ce-test-browser only, with the bulk of v0.10.0 absorption removed).

    v0.16.0 retarget (ST15) note: per the test-migration catalog, the
    plan-of-record preference is to keep the 4-line CLAUDE.md summary
    honest about v0.12.0 inline (so this test stays GREEN unchanged)
    AND extend coverage to the archive — see
    `test_concept_absorption_archive_has_v012_acknowledgment` below.
    """
    body = CLAUDE_MD_PATH.read_text(encoding="utf-8")
    assert "v0.12.0" in body, (
        "CLAUDE.md must mention v0.12.0 by version literal post-Subtask 19"
    )
    # Loose adequacy check — the v0.12.0 mention should sit within the
    # Vendored Surface region or otherwise carry a scope-correction word.
    cutover_signals = (
        "v0.12.0",
        "concept-kernel",
        "scope correction",
        "cutover",
    )
    body_lower = body.lower()
    matching_signals = [s for s in cutover_signals if s.lower() in body_lower]
    assert len(matching_signals) >= 2, (
        f"CLAUDE.md must carry at least two v0.12.0 scope-correction "
        f"signals (e.g., 'v0.12.0', 'concept-kernel', 'cutover'); found "
        f"{matching_signals!r}"
    )


def test_concept_absorption_archive_has_v012_acknowledgment():
    """v0.16.0 ST15 extension — the canonical Concept Absorption archive
    must also carry the v0.12.0 acknowledgment signals.

    Per the test-migration catalog (ST9), the verbose §"Concept Absorption
    Surface" content moved from CLAUDE.md to
    `docs/archive/concept-absorption-surface.md`. The catalog notes that
    coverage of the v0.12.0 acknowledgment should be extended to the
    archive file (in addition to the preserved 4-line CLAUDE.md summary).
    """
    archive_path = REPO_ROOT / "docs" / "archive" / "concept-absorption-surface.md"
    body = archive_path.read_text(encoding="utf-8")
    assert "v0.12.0" in body, (
        "`docs/archive/concept-absorption-surface.md` must mention v0.12.0 "
        "by version literal — the post-cutover canonical home for the "
        "Concept Absorption narrative"
    )
    cutover_signals = (
        "v0.12.0",
        "concept-kernel",
        "scope correction",
        "cutover",
    )
    body_lower = body.lower()
    matching_signals = [s for s in cutover_signals if s.lower() in body_lower]
    assert len(matching_signals) >= 2, (
        f"`docs/archive/concept-absorption-surface.md` must carry at least "
        f"two v0.12.0 scope-correction signals (e.g., 'v0.12.0', "
        f"'concept-kernel', 'cutover'); found {matching_signals!r}"
    )
