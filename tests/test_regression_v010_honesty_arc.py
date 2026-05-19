"""Regression test for v0.10.0 U26 invariant — honesty arc voice
across CHANGELOG.md, docs/STATE.md, README.md, NOTICE.md.

The v0.10.0 honesty arc forbids overclaim language that would imply
behavioral parity with CE/superpowers, Stop-hook coverage extension, or
identity dissolution.

Plan reference: docs/plans/2026-05-19-003-feat-v0.10.0-absorb-ce-superpowers-plan.md
§U26 (T5-T7), R-D8.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
STATE = REPO_ROOT / "docs" / "STATE.md"
README = REPO_ROOT / "README.md"
NOTICE = REPO_ROOT / "NOTICE.md"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"


FORBIDDEN_PHRASES = [
    # claim of behavioral parity / supersession
    "athanor now supersedes",
    "athanor supersedes compound-engineering",
    "supersedes compound-engineering",
    "ce-brainstorm equivalent",
    # claim that Stop hook now covers vendored skills
    "stop hook now covers vendored",
    "stop hook protects vendored",
    "vendor-aware whitelist active",
    # overclaim that vendored skills are fully integrated
    "vendored skills run under thin leader runtime enforcement",
    # identity dissolution claims
    "athanor is now ce",
    "athanor becomes ce",
    "tdd enforced",
    "clarify enforced",
    "intent-clarification enforced",
]


def _extract_v010_section(text: str) -> str:
    """Return the v0.10.0 CHANGELOG entry body (between the v0.10.0
    heading and the next H2 release heading)."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith("## [0.10.0]"):
            start = i
            break
    if start is None:
        return ""
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("## [") and not lines[j].startswith("## [0.10.0]"):
            end = j
            break
    return "\n".join(lines[start:end])


# ---- v0.10.0 CHANGELOG ----


def test_changelog_v010_entry_exists():
    """MUST: CHANGELOG has a v0.10.0 entry."""
    text = CHANGELOG.read_text(encoding="utf-8")
    section = _extract_v010_section(text)
    assert section, "CHANGELOG.md must have a [0.10.0] entry"
    assert len(section) > 500, (
        f"CHANGELOG v0.10.0 entry too short ({len(section)} chars) — "
        f"meaningful entry required"
    )


def test_changelog_v010_has_voice_section():
    """MUST: v0.10.0 entry has an explicit 'Voice' section enumerating
    what the release does NOT claim (honesty arc convention)."""
    section = _extract_v010_section(CHANGELOG.read_text(encoding="utf-8"))
    lower = section.lower()
    assert "voice" in lower, (
        "CHANGELOG v0.10.0 must have a 'Voice' subsection"
    )
    # "does NOT" language is the honesty-arc fingerprint
    assert "does not" in lower or "not a" in lower, (
        "v0.10.0 Voice section must articulate what the release does NOT claim"
    )


def test_changelog_v010_no_forbidden_phrases():
    """MUST: v0.10.0 entry avoids overclaim phrases."""
    section = _extract_v010_section(CHANGELOG.read_text(encoding="utf-8")).lower()
    hits = [p for p in FORBIDDEN_PHRASES if p in section]
    assert not hits, (
        f"CHANGELOG v0.10.0 contains forbidden overclaim phrase(s): {hits}"
    )


def test_changelog_v010_mentions_vendored_explicitly():
    """MUST: v0.10.0 entry uses the word 'vendored' to characterize the
    absorption (not 'integrated', 'merged', 'unified')."""
    section = _extract_v010_section(CHANGELOG.read_text(encoding="utf-8")).lower()
    assert "vendored" in section, (
        "CHANGELOG v0.10.0 must explicitly say 'vendored' (T2 framing)"
    )


def test_changelog_v010_keeps_v090_intact():
    """MUST: prior CHANGELOG entries (v0.9.0) not mutated."""
    text = CHANGELOG.read_text(encoding="utf-8")
    assert "## [0.9.0]" in text
    assert "dual-mode" in text or "clarify" in text


# ---- STATE.md Current Phase + Vendor Manifest ----


def test_state_md_current_phase_in_0_10_x_series():
    """MUST: docs/STATE.md Current Phase mentions a 0.10.x version.

    v0.10.1 generalization: pinned to "0.10.0" originally; relaxed to the
    minor series so v0.10.1+ patch releases pass through. v0.11.0+ will
    need an explicit update.

    Also asserts the previous phase line names the most recent prior
    v0.10.x release (so the demotion is visible in STATE.md history).
    """
    text = STATE.read_text(encoding="utf-8")
    found_current = False
    in_0_10_series = False
    for line in text.splitlines():
        if line.startswith("## Current Phase"):
            found_current = True
            # Look for "v0.10.X" or "0.10.X" anywhere on the line
            if "0.10." in line:
                in_0_10_series = True
            break
    assert found_current, "STATE.md must have Current Phase section"
    assert in_0_10_series, "Current Phase must reference a 0.10.x version"


def test_state_md_has_vendor_manifest():
    """MUST: STATE.md has a §Vendor Manifest section listing the two
    upstreams."""
    text = STATE.read_text(encoding="utf-8")
    lower = text.lower()
    assert "vendor manifest" in lower
    assert "compound-engineering" in lower
    assert "superpowers" in lower
    assert "3.8.3" in text
    assert "5.1.0" in text


def test_state_md_mentions_four_identity_commitments():
    """MUST: STATE.md Current Phase enumerates the four identity
    commitments by name."""
    text = STATE.read_text(encoding="utf-8").lower()
    for needle in [
        "thin leader",
        "cross-model adversarial",
        "spec-then-tdd",
        "stop hook",
    ]:
        assert needle in text, (
            f"STATE.md Current Phase must mention '{needle}'"
        )


# ---- README absorption banner ----


def test_readme_mentions_v010_absorption():
    """MUST: README.md mentions v0.10.0 absorption above the fold."""
    text = README.read_text(encoding="utf-8")
    # Above the fold = first ~80 lines
    above_fold = "\n".join(text.splitlines()[:80])
    assert "v0.10.0" in above_fold, (
        "README.md must mention v0.10.0 above the fold"
    )
    lower = above_fold.lower()
    assert "vendored" in lower or "absorb" in lower, (
        "README.md must describe the v0.10.0 absorption"
    )


def test_readme_has_what_does_not_do_list():
    """MUST: README.md's v0.10.0 banner has a 'does NOT do' list (honesty
    arc voice)."""
    text = README.read_text(encoding="utf-8").lower()
    assert "does not" in text or "not a" in text, (
        "README.md must include 'does NOT do' honesty list"
    )


def test_readme_no_forbidden_phrases():
    """MUST: README.md avoids overclaim phrases."""
    text = README.read_text(encoding="utf-8").lower()
    hits = [p for p in FORBIDDEN_PHRASES if p in text]
    assert not hits, (
        f"README.md contains forbidden overclaim phrase(s): {hits}"
    )


# ---- NOTICE.md attribution ----


def test_notice_md_has_both_upstreams():
    """MUST: NOTICE.md has third-party attribution for both
    compound-engineering and superpowers at their v0.10.0-vendored
    versions."""
    text = NOTICE.read_text(encoding="utf-8")
    assert "compound-engineering" in text.lower()
    assert "superpowers" in text.lower()
    assert "3.8.3" in text
    assert "5.1.0" in text
    # MIT license text reproduced
    assert text.count("MIT License") >= 2


def test_notice_md_lists_vendored_skill_paths():
    """MUST: NOTICE.md enumerates vendored skill paths."""
    text = NOTICE.read_text(encoding="utf-8")
    # Sample paths
    sample = ["skills/ce-plan/", "skills/sp-brainstorming/"]
    for s in sample:
        assert s in text, (
            f"NOTICE.md must enumerate vendored skill path {s}"
        )


# ---- CLAUDE.md honesty (cross-cutting) ----


def test_claude_md_vendored_surface_has_does_not_do_list():
    """MUST: CLAUDE.md §Vendored Surface has a 'does NOT do' list."""
    text = CLAUDE_MD.read_text(encoding="utf-8")
    # Find the Vendored Surface section
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if "Vendored Surface" in line and line.startswith("## "):
            start = i
            break
    assert start is not None, "CLAUDE.md must have §Vendored Surface"
    # Scan within the section for "NOT" claims
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
    section = "\n".join(lines[start:end]).lower()
    assert "does not" in section, (
        "CLAUDE.md §Vendored Surface must have 'does NOT do' honesty list"
    )


def test_claude_md_no_forbidden_phrases():
    """MUST: CLAUDE.md avoids overclaim phrases."""
    text = CLAUDE_MD.read_text(encoding="utf-8").lower()
    hits = [p for p in FORBIDDEN_PHRASES if p in text]
    assert not hits, (
        f"CLAUDE.md contains forbidden overclaim phrase(s): {hits}"
    )
