"""Regression — CLAUDE.md declares the engineering-quality principle (v0.18.4).

The user's standing principle: code must WORK, but stay low-complexity /
maintainable, and must NOT use indiscriminate fallbacks — an error that
should be fixed must not be silently swallowed by a fallback (fail-loud
over silent fallback). This locks the principle into CLAUDE.md §Core
Principle so it is a first-class athanor commitment, not merely an advisory
review heuristic. Static reads only.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"


def _core_principle_section() -> str:
    body = CLAUDE_MD.read_text(encoding="utf-8")
    m = re.search(r"##\s+Core Principle\s*\n(.*?)(?=\n##\s)", body, re.S)
    return m.group(1) if m else ""


def test_core_principle_declares_fail_loud_no_indiscriminate_fallback() -> None:
    """MUST — §Core Principle states fail-loud over silent fallback."""
    section = _core_principle_section().lower()
    assert section, "CLAUDE.md must have a §Core Principle section."
    assert "fail-loud" in section, (
        "§Core Principle must state 'fail-loud over silent fallback' — errors "
        "that should be fixed must not be swallowed by a fallback."
    )
    assert "fallback" in section, (
        "§Core Principle must address indiscriminate fallback explicitly."
    )


def test_core_principle_declares_low_complexity() -> None:
    """MUST — §Core Principle states low complexity / maintainability."""
    section = _core_principle_section().lower()
    assert "복잡도" in section or "complexity" in section, (
        "§Core Principle must state the low-complexity / maintainability "
        "commitment (works is the floor, not the ceiling)."
    )
