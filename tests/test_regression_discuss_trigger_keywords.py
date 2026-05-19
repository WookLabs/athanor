"""Regression test for v0.9.0 U6 invariant — /athanor:discuss skill
description trigger keywords properly extended (qualified clarify-direction
triggers without debug overlap).

Codex review (2026-05-19) P1 #4: bare '헷갈려' is too broad and may overlap
with /athanor:debug or general conversational use. Replace with qualified
phrases like '요구사항이 헷갈려', '무엇을 만들지 헷갈려'.

Plan reference: docs/plans/2026-05-19-002-feat-v0.9.0-discuss-clarify-mode-plan.md
§U6 + origin requirements R10, R11.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DISCUSS_SKILL = REPO_ROOT / "skills" / "discuss" / "SKILL.md"


def _load_skill():
    return DISCUSS_SKILL.read_text(encoding="utf-8")


def _extract_frontmatter(content: str) -> str:
    """Extract the YAML frontmatter (between first --- and next ---) from
    the skill file."""
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return ""
    return "\n".join(lines[1:end_idx])


# --- Trigger keyword extensions ---


def test_frontmatter_includes_clarify_triggers():
    """MUST: frontmatter description contains clarify-direction trigger
    keywords (R10)."""
    fm = _extract_frontmatter(_load_skill())
    assert fm, "frontmatter not found"
    fm_lower = fm.lower()
    # At least 2 of the 4 qualified clarify triggers must be present
    clarify_signals = [
        "의도 명확화",
        "요구사항이 헷갈려",
        "무엇을 만들지 헷갈려",
        "뭘 해야할지 모르겠어",
        "명확히 정리해줘",
    ]
    matches = [s for s in clarify_signals if s in fm]
    assert len(matches) >= 2, (
        f"frontmatter must include at least 2 qualified clarify triggers. "
        f"Found: {matches}. Expected at least 2 of: {clarify_signals}"
    )


def test_existing_synthesis_triggers_preserved():
    """MUST: existing synthesis-direction trigger keywords from pre-v0.9.0
    are preserved (R10)."""
    fm = _extract_frontmatter(_load_skill())
    existing_triggers = [
        "논의",
        "이런게 좋을까",
        "어떻게 할까",
        "장단점",
        "A vs B",
        "브레인스토밍",
    ]
    missing = [t for t in existing_triggers if t not in fm]
    assert not missing, (
        f"Existing synthesis triggers must be preserved. Missing: {missing}"
    )


def test_clarify_triggers_are_qualified():
    """MUST (Codex P1 #4): bare '헷갈려' (single-word, debug-overlapping)
    must NOT appear as a trigger; only qualified phrases like '요구사항이
    헷갈려' / '무엇을 만들지 헷갈려' are permitted."""
    fm = _extract_frontmatter(_load_skill())
    # Bare "헷갈려" should not appear in trigger list contexts. The
    # description string lists triggers separated by commas inside quotes
    # like '...', '...', '헷갈려', '...'. We check that '헷갈려' only
    # appears as part of a qualified phrase (preceded by other words).
    import re

    # Find all trigger-like quoted strings (single-quoted in the description)
    quoted_triggers = re.findall(r"'([^']+)'", fm)
    bare_heggalryeo = [t for t in quoted_triggers if t.strip() == "헷갈려"]
    assert not bare_heggalryeo, (
        f"Bare '헷갈려' is too broad and overlaps with debug/conversational "
        f"use. Use qualified phrases like '요구사항이 헷갈려' or '무엇을 "
        f"만들지 헷갈려' instead. Found bare occurrences: {bare_heggalryeo}"
    )


def test_negative_triggers_for_debug_overlap():
    """MUST (Codex P1 #4 negative): debug-ish keywords ('에러 뜨는데',
    '왜 안 되지') must NOT appear in /athanor:discuss frontmatter trigger
    list (those belong to /athanor:debug)."""
    fm = _extract_frontmatter(_load_skill())
    debug_overlap = [
        "에러 뜨는데",
        "왜 안 되지",
        "에러 떴어",
        "버그",
        "디버깅",
        "오류 나는데",
    ]
    found = [d for d in debug_overlap if d in fm]
    assert not found, (
        f"/athanor:discuss frontmatter must NOT include debug-domain "
        f"triggers (those belong to /athanor:debug). Found: {found}"
    )


def test_no_overclaim_in_description():
    """MUST (Covers AE6): description must NOT use overclaim framing like
    'intent-clarification enforced' or 'ce-brainstorm equivalent'."""
    fm = _extract_frontmatter(_load_skill()).lower()
    forbidden = [
        "intent-clarification enforced",
        "intent clarification enforced",
        "ce-brainstorm equivalent",
        "ce brainstorm equivalent",
        "clarify enforced",
        "tdd enforced",
    ]
    for phrase in forbidden:
        assert phrase not in fm, (
            f"frontmatter contains overclaim phrase '{phrase}' — v0.9.0 "
            f"honesty arc requires advisory framing"
        )
