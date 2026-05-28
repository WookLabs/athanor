"""Regression tests for v0.16.0 — CLAUDE.md contract index invariants.

Context
-------
The v0.16.0 release (Phase 3.5) bundles a CLAUDE.md token-diet rewrite
that slimmed the file from ~534 lines down to a 145-175 line "contract
index" + 3 archive companion docs under `docs/archive/`. The new
top-level file is meant to be a navigational contract surface — not the
single-source-of-truth prose dump it had become through v0.7.x → v0.15.x.

This regression test pins the invariants of that rewrite:

1. Line count stays in the 145-175 band — guards against re-bloat
   (regressing back into the source-of-truth role) and against
   over-aggressive trimming (losing the contract anchors that
   skills cross-reference).
2. The four navigational anchors are present:
   - §"Session Lookup Convention"
   - §"Defense Mechanisms" + its §"Status table" subsection
   - The 4 identity invariants enumeration (Thin Leader,
     cross-model adversarial planning, Spec-then-TDD, Stop hook)
3. The 3 archive companion files exist at the canonical paths under
   `docs/archive/` so the cross-reference links from CLAUDE.md resolve.

These tests are static text reads only. They do NOT invoke any subprocess
or modify any file.

Plan reference
--------------
v0.16.0 Phase 3.5 (Subtask ST16).
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
ARCHIVE_DIR = REPO_ROOT / "docs" / "archive"

LINE_COUNT_MIN = 145
LINE_COUNT_MAX = 175


def _read_claude_md() -> str:
    assert CLAUDE_MD.is_file(), (
        f"CLAUDE.md not found at {CLAUDE_MD} — contract index missing"
    )
    return CLAUDE_MD.read_text(encoding="utf-8")


def test_claude_md_line_count_in_target_range() -> None:
    """MUST — CLAUDE.md line count in the [145, 175] band.

    v0.16.0 token-diet rewrite: ~534 → ~175 lines. Re-bloat past 175
    means the file is sliding back toward source-of-truth role;
    going below 145 means we've lost contract anchors.

    Counts physical newlines (matches `wc -l` semantics).
    """
    body = _read_claude_md()
    # wc -l counts newline characters, matching the plan packet semantics.
    line_count = body.count("\n")
    assert LINE_COUNT_MIN <= line_count <= LINE_COUNT_MAX, (
        f"CLAUDE.md line count {line_count} is outside the target band "
        f"[{LINE_COUNT_MIN}, {LINE_COUNT_MAX}]. v0.16.0 contract: the "
        f"file is a navigational index, not a prose dump — re-bloat "
        f"suggests content should move to docs/archive/, while under-"
        f"shoot suggests an essential anchor section was deleted."
    )


def test_claude_md_has_session_lookup_convention() -> None:
    """MUST — §"Session Lookup Convention" heading present.

    This section is the canonical rule for `<LATEST>` resolution across
    skills (`/athanor:plan`, `/athanor:work`, `/athanor:analyze`,
    `/athanor:debug`, `/athanor:review`, `/athanor:scope-drift`). Per
    v0.7.7 M4 finding the rule lives in CLAUDE.md to prevent per-skill
    semantic drift.
    """
    body = _read_claude_md()
    assert "## Session Lookup Convention" in body, (
        "CLAUDE.md must contain the '## Session Lookup Convention' "
        "section — skills cross-reference this anchor for <LATEST> "
        "resolution semantics (v0.7.7 M4)."
    )


def test_claude_md_has_defense_mechanisms_status_table() -> None:
    """MUST — §"Defense Mechanisms" heading + §"Status table" subsection.

    The Defense Mechanisms section indexes the five defense layers
    (Completion-Claim Verification, Stop-Phrase Detection, Read-Before-
    Edit, Scope Drift Detection, Spec-then-TDD, using-superpowers
    boundary). The Status table subsection lists each mechanism's
    enforcement level (enforced vs advisory) — honesty discipline that
    must not silently disappear in a rewrite.
    """
    body = _read_claude_md()
    assert "## Defense Mechanisms" in body, (
        "CLAUDE.md must contain the '## Defense Mechanisms' section — "
        "this is the contract index for runtime gates vs advisory rules."
    )
    assert "### Status table" in body, (
        "CLAUDE.md must contain the '### Status table' subsection under "
        "Defense Mechanisms — the enforcement-level honesty index."
    )


def test_claude_md_has_4_identity_invariants() -> None:
    """MUST — All 4 identity invariants enumerated by literal name.

    The four invariants (per v0.12.0 §"Identity guard layer" cutover):
    1. Thin Leader contract
    2. Cross-model adversarial planning
    3. Spec-then-TDD discipline
    4. Stop hook runtime gate

    Each must appear by literal phrase so the contract index reflects
    them. They are the survival surface from the v0.12.0 vendoring
    cutover and must not be elided in a rewrite.
    """
    body = _read_claude_md()
    # Use case-sensitive substring checks for the canonical phrasing.
    required_phrases = {
        "Thin Leader": [
            "Thin Leader",
        ],
        "cross-model adversarial planning": [
            "Cross-model adversarial",
            "cross-model adversarial",
        ],
        "Spec-then-TDD": [
            "Spec-then-TDD",
        ],
        "Stop hook": [
            "Stop hook",
        ],
    }
    missing = []
    for label, candidates in required_phrases.items():
        if not any(c in body for c in candidates):
            missing.append(label)
    assert not missing, (
        f"CLAUDE.md is missing identity invariant phrases: {missing}. "
        f"All 4 identity invariants (Thin Leader / cross-model adversarial / "
        f"Spec-then-TDD / Stop hook) must be present by literal name — they "
        f"are the survival surface from the v0.12.0 vendoring cutover."
    )


def test_archive_files_exist() -> None:
    """MUST — 3 archive companion files exist at canonical paths.

    The v0.16.0 token-diet rewrite moved the heavyweight prose out of
    CLAUDE.md into 3 archive docs under `docs/archive/`. The cross-
    references in CLAUDE.md point at these paths; missing files would
    break the contract index's navigational role.
    """
    required = [
        "stop-hook-postmortem.md",
        "concept-absorption-surface.md",
        "defense-mechanisms-detail.md",
    ]
    missing = [name for name in required if not (ARCHIVE_DIR / name).is_file()]
    assert not missing, (
        f"Missing archive companion files under {ARCHIVE_DIR}: {missing}. "
        f"v0.16.0 contract: CLAUDE.md cross-references these via "
        f"`docs/archive/<name>` links — they must exist on disk."
    )
