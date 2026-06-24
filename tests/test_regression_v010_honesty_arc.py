"""Regression test for the v0.10.0 → v0.12.0 honesty arc voice.

The v0.10.0 honesty arc forbids overclaim language that would imply
behavioral parity with CE/superpowers, Stop-hook coverage extension, or
identity dissolution. v0.11.8 added the "plan-of-record misread"
attribution shape that v0.12.0 carries forward via:

  - CHANGELOG.md v0.11.8 entry (already shipped) and v0.12.0 entry
    (future-shipped — gated by version-string presence so this test
    stays GREEN through v0.11.x cycles).
  - docs/archive/v010-v011-vendoring-scope-correction.md as the
    canonical retrospective.

The vendored-surface assertions from the pre-v0.12.0 shape of this file
are removed in Subtask 15 (the vendored CE/superpowers directories
themselves are gone). The voice-arc and honesty-ledger pins survive
because they apply to athanor-native prose (CLAUDE.md, README.md,
CHANGELOG.md, STATE.md, NOTICE.md), not to vendored content.

Plan reference: docs/plans/2026-05-22-001-feat-v0.12.0-concept-kernel-cutover-plan-b.md
§Subtask 15 (test rewrite scope).
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
STATE = REPO_ROOT / "docs" / "STATE.md"
README = REPO_ROOT / "README.md"
NOTICE = REPO_ROOT / "NOTICE.md"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
ARCHIVE_LEDGER = (
    REPO_ROOT / "docs" / "archive" / "v010-v011-vendoring-scope-correction.md"
)


FORBIDDEN_PHRASES = [
    # claim of behavioral parity / supersession
    "athanor now supersedes",
    "athanor supersedes compound-engineering",
    "supersedes compound-engineering",
    "ce-brainstorm equivalent",
    # claim that Stop hook now covers vendored skills
    "stop hook now covers vendored",
    "stop hook protects vendored",
    # overclaim that vendored skills are fully integrated
    "vendored skills run under thin leader runtime enforcement",
    # identity dissolution claims
    "athanor is now ce",
    "athanor becomes ce",
    "tdd enforced",
    "clarify enforced",
    "intent-clarification enforced",
]


def _extract_changelog_section(text: str, version: str) -> str:
    """Return the CHANGELOG section body for `## [<version>]` (any suffix).

    Boundaries: starts at the matching H2 heading line; ends just before
    the next `## [` heading. Returns "" if not found.
    """
    lines = text.splitlines()
    start = None
    target = f"## [{version}]"
    for i, line in enumerate(lines):
        if line.startswith(target):
            start = i
            break
    if start is None:
        return ""
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("## [") and not lines[j].startswith(target):
            end = j
            break
    return "\n".join(lines[start:end])


def _extract_v010_section(text: str) -> str:
    return _extract_changelog_section(text, "0.10.0")


def _extract_v011_section(text: str) -> str:
    return _extract_changelog_section(text, "0.11.0")


# ---- v0.10.0 CHANGELOG (prior honesty-arc claims still valid) ----


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
    assert "voice" in lower, "CHANGELOG v0.10.0 must have a 'Voice' subsection"
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


# ---- v0.11.x honesty arc continuity ----


# v0.11.0 extends FORBIDDEN_PHRASES with LFG-specific deprecation framing
# that the wrapper release must avoid (origin §R4: positive commitment only).
V011_FORBIDDEN_PHRASES = FORBIDDEN_PHRASES + [
    "ce-lfg deprecated",
    "supersedes ce-lfg",
    "athanor lfg replaces ce-lfg",
    "do not use ce-lfg",
    "do not use compound-engineering",
]


def test_changelog_v011_entry_exists_when_version_is_0_11_x():
    """MUST: if plugin.json is at 0.11.x, CHANGELOG has a [0.11.x] entry."""
    import json
    pj = json.loads(
        (REPO_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    pj_version = pj.get("version") or ""
    if not pj_version.startswith("0.11."):
        return
    section = _extract_v011_section(CHANGELOG.read_text(encoding="utf-8"))
    assert section, (
        "CHANGELOG.md must have a [0.11.0] entry when plugin.json is at 0.11.x"
    )
    assert len(section) > 500, (
        f"CHANGELOG v0.11.0 entry too short ({len(section)} chars)"
    )


def test_changelog_v011_no_forbidden_phrases():
    """MUST: v0.11.0 CHANGELOG entry uses positive commitment only."""
    import json
    pj = json.loads(
        (REPO_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    pj_version = pj.get("version") or ""
    if not pj_version.startswith("0.11."):
        return
    section = _extract_v011_section(CHANGELOG.read_text(encoding="utf-8")).lower()
    hits = [p for p in V011_FORBIDDEN_PHRASES if p in section]
    assert not hits, (
        f"CHANGELOG v0.11.0 contains forbidden overclaim phrase(s): {hits}"
    )


def test_state_md_v011_no_forbidden_phrases():
    """MUST: STATE.md Current Phase + body has no CE-deprecate phrases at
    v0.11.0."""
    import json
    pj = json.loads(
        (REPO_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    pj_version = pj.get("version") or ""
    if not pj_version.startswith("0.11."):
        return
    text = STATE.read_text(encoding="utf-8").lower()
    hits = [p for p in V011_FORBIDDEN_PHRASES if p in text]
    assert not hits, (
        f"STATE.md contains forbidden overclaim phrase(s) at v0.11.0: {hits}"
    )


# ---- v0.11.8 / v0.12.0 plan-of-record misread attribution ----


def test_changelog_v011_8_mentions_plan_of_record_misread():
    """MUST: v0.11.8 CHANGELOG entry uses the 'plan-of-record misread'
    attribution shape — direct ownership rather than ambient framing.

    The phrase is the honesty-arc anchor introduced in v0.11.8 to attribute
    the over-scoped v0.10.0 vendoring to the plan itself (D7).
    """
    text = CHANGELOG.read_text(encoding="utf-8")
    section = _extract_changelog_section(text, "0.11.8")
    if not section:
        return  # pre-v0.11.8 branch — skip (gate keeps test GREEN earlier)
    assert "plan-of-record misread" in section.lower(), (
        "CHANGELOG v0.11.8 entry must contain the phrase "
        "'plan-of-record misread' (the honesty-arc attribution shape "
        "carried forward into v0.12.0)."
    )


def test_changelog_v012_uses_plan_of_record_misread_when_shipped():
    """SHOULD: when CHANGELOG.md gets a [0.12.0] section, it uses the
    same 'plan-of-record misread' attribution shape that v0.11.8 set.

    Until v0.12.0 ships its CHANGELOG entry, this test no-ops; once the
    entry is present, the phrase must be there."""
    text = CHANGELOG.read_text(encoding="utf-8")
    section = _extract_changelog_section(text, "0.12.0")
    if not section:
        return
    assert "plan-of-record misread" in section.lower(), (
        "CHANGELOG v0.12.0 entry must carry the honesty-arc 'plan-of-record "
        "misread' attribution shape established in v0.11.8."
    )


# ---- v0.10-v0.11 vendoring-scope-correction archive ----


def test_archive_ledger_exists():
    """MUST: docs/archive/v010-v011-vendoring-scope-correction.md exists.

    The ledger is the canonical retrospective documenting v0.10.0 → v0.11.7
    as the seven-release window that shipped on the v0.10.0 plan-of-record
    misread.
    """
    assert ARCHIVE_LEDGER.is_file(), (
        f"v0.12.0 archive ledger missing at {ARCHIVE_LEDGER}; the "
        f"retrospective is required by the v0.12.0 plan §Phase 0."
    )


def test_archive_ledger_contains_canonical_phrases():
    """MUST: archive ledger uses the three canonical honesty-arc phrases:
      1. 'plan-of-record misread' (direct attribution).
      2. 'the work was real' (preservation framing).
      3. 'the product surface was wrong' (correction framing).
    """
    if not ARCHIVE_LEDGER.is_file():
        return  # paired with the existence test above
    text = ARCHIVE_LEDGER.read_text(encoding="utf-8").lower()
    required = (
        "plan-of-record misread",
        "the work was real",
        "the product surface was wrong",
    )
    missing = [p for p in required if p not in text]
    assert not missing, (
        f"docs/archive/v010-v011-vendoring-scope-correction.md missing "
        f"canonical honesty-arc phrases: {missing!r}."
    )


# ---- STATE.md Current Phase + Vendor Manifest ----


def test_state_md_current_phase_in_0_10_or_0_11_or_0_12_or_0_13_or_0_14_or_0_15_or_0_16_x_series():
    """MUST: docs/STATE.md Current Phase mentions a 0.10.x / 0.11.x / 0.12.x /
    0.13.x / 0.14.x / 0.15.x / 0.16.x / 0.17.x / 0.18.x / 0.19.x / 0.20.x / 0.21.x / 0.22.x version.
    v0.18.0 extension accepted to keep the test stable through the Freeze
    infrastructure release; v0.20.0 extension at the ref-optimization + uv
    tooling release; v0.21.0 extension at the opt-in lfg auto-merge release;
    v0.22.0 extension at the default-on lfg auto-merge + strengthened
    lfg-goal loop release."""
    text = STATE.read_text(encoding="utf-8")
    found_current = False
    in_series = False
    for line in text.splitlines():
        if line.startswith("## Current Phase"):
            found_current = True
            if (
                "0.10." in line
                or "0.11." in line
                or "0.12." in line
                or "0.13." in line
                or "0.14." in line
                or "0.15." in line
                    or "0.16." in line
                    or "0.17." in line
                    or "0.18." in line
                    or "0.19." in line
                    or "0.20." in line
                    or "0.21." in line
                    or "0.22." in line
                ):
                in_series = True
            break
    assert found_current, "STATE.md must have Current Phase section"
    assert in_series, (
        "Current Phase must reference a 0.10.x / 0.11.x / 0.12.x / 0.13.x / 0.14.x / 0.15.x / 0.16.x / 0.17.x / 0.18.x / 0.19.x / 0.20.x / 0.21.x / 0.22.x version"
    )


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


# ---- NOTICE.md attribution (vendored markdown is gone, but NOTICE
# remains for licensing transparency for the work that shipped) ----


def test_notice_md_has_both_upstreams():
    """MUST: NOTICE.md still names compound-engineering and superpowers
    upstreams. v0.10.0 vendoring is part of athanor's permanent record
    even though the bulk of vendored material is removed in v0.12.0."""
    text = NOTICE.read_text(encoding="utf-8")
    assert "compound-engineering" in text.lower()
    assert "superpowers" in text.lower()
    # MIT license text reproduced
    assert text.count("MIT License") >= 2


# ---- CLAUDE.md honesty (cross-cutting) ----


def test_claude_md_no_forbidden_phrases():
    """MUST: CLAUDE.md avoids overclaim phrases."""
    text = CLAUDE_MD.read_text(encoding="utf-8").lower()
    hits = [p for p in FORBIDDEN_PHRASES if p in text]
    assert not hits, (
        f"CLAUDE.md contains forbidden overclaim phrase(s): {hits}"
    )


# ---- README absorption framing (general — vendored-specific
# claims removed since the v0.12.0 cut deletes the surface) ----


def test_readme_no_forbidden_phrases():
    """MUST: README.md avoids overclaim phrases."""
    text = README.read_text(encoding="utf-8").lower()
    hits = [p for p in FORBIDDEN_PHRASES if p in text]
    assert not hits, (
        f"README.md contains forbidden overclaim phrase(s): {hits}"
    )
