"""Regression test for the v0.7.7 M4 finding — canonical session-lookup convention.

Pins:
  (a) CLAUDE.md contains the canonical `## Session Lookup Convention` section
      with the lexicographic-selection rule + Bash reference.
  (b) All 6 session-touching skills reference the canonical section and do
      NOT carry the old "today's date" prose that caused per-skill drift.

The literal phrase `today's date` MAY appear in the canonical "stale-session
announcement" wording (which compares <LATEST> date against today's date).
The forbidden forms are the OLD per-skill prose phrasings — see
`test_no_skill_uses_old_today_prose`.

Plan reference: `.athanor/sessions/2026-05-18-001/plan.md` §4 M4.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"

SESSION_SKILLS = ["work", "plan", "discuss", "analyze", "debug", "review"]


def _skill_path(name: str) -> Path:
    return REPO_ROOT / "skills" / name / "SKILL.md"


def _load(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _claude_md_session_section(content: str) -> str:
    """Return the body between `## Session Lookup Convention` and the next `## `."""
    lines = content.splitlines()
    start_idx = None
    for i, line in enumerate(lines):
        if line.startswith("## Session Lookup Convention"):
            start_idx = i
            break
    if start_idx is None:
        return ""
    end_idx = len(lines)
    for j in range(start_idx + 1, len(lines)):
        if lines[j].startswith("## "):
            end_idx = j
            break
    return "\n".join(lines[start_idx:end_idx])


# ---- tests ----

def test_claude_md_has_session_lookup_section():
    """CLAUDE.md must contain the canonical `## Session Lookup Convention` heading."""
    content = _load(CLAUDE_MD)
    assert "## Session Lookup Convention" in content, (
        "CLAUDE.md must define the canonical `## Session Lookup Convention` "
        "section per v0.7.7 M4."
    )


def test_session_convention_includes_lexicographic_rule():
    """The canonical section must mention the lexicographic selection rule."""
    section = _claude_md_session_section(_load(CLAUDE_MD))
    assert section, "Session Lookup Convention section not found in CLAUDE.md"
    assert "lexicographic" in section, (
        "Session Lookup Convention must mention 'lexicographic' "
        "(the canonical selection rule)."
    )


def test_session_convention_includes_bash_reference():
    """The canonical section must include the canonical Bash regex one-liner."""
    section = _claude_md_session_section(_load(CLAUDE_MD))
    assert section, "Session Lookup Convention section not found in CLAUDE.md"
    expected_regex = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{3}$"
    assert expected_regex in section, (
        "Session Lookup Convention must include the canonical Bash regex "
        f"reference pattern: {expected_regex!r}"
    )


def test_all_6_skills_reference_convention():
    """Each of the 6 session-touching skills must reference the canonical convention."""
    missing = []
    for skill in SESSION_SKILLS:
        path = _skill_path(skill)
        assert path.exists(), f"Skill file missing: {path}"
        content = _load(path)
        if "Session Lookup Convention" not in content:
            missing.append(skill)
    assert not missing, (
        f"These session-touching skills do NOT reference "
        f"'Session Lookup Convention': {missing}. v0.7.7 M4 requires all 6 "
        f"to defer to the canonical CLAUDE.md section."
    )


def test_no_skill_uses_old_today_prose():
    """No session-touching skill may carry the OLD per-skill 'today' prose.

    `today's date` (literal) MAY appear in the canonical stale-session
    announcement wording — that is canonical, not the bug. The forbidden
    forms are the older prose patterns that caused drift between skills.

    v0.7.8 widens the blocklist to include the paraphrase `earlier today`
    (PR #10 dual review caught the analyze:301 escapee that v0.7.7's
    narrower blocklist missed).
    """
    forbidden = [
        "matching today's date",
        "most recent today",
        "existing session from today",
        "earlier today",
        "user ran /athanor",  # any "user ran /athanor:<x> ... today" variant
    ]
    offenders = []
    for skill in SESSION_SKILLS:
        path = _skill_path(skill)
        content = _load(path)
        for phrase in forbidden:
            if phrase in content:
                offenders.append((skill, phrase))
    assert not offenders, (
        "Found OLD per-skill 'today' prose (forbidden by v0.7.7 M4 "
        f"canonical-lookup rule, widened in v0.7.8 PR #10 review): {offenders}. "
        "Defer to CLAUDE.md §Session Lookup Convention instead."
    )
