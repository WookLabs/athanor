"""Regression — CLAUDE.md §Rules 5 honestly labels the memory mechanism.

Context
-------
§Rules 5 read "작업 완료 시 자동으로 메모리를 저장한다 (2-tier: permanent +
working)", which suggests a permanent-tier persistence (mem-search MCP) is
wired. The v0.18.3 audit confirmed `scripts/` make ZERO
mem-search/memory_add calls — only frontmatter `importance` marking +
`.athanor/lessons/` files exist. STATE.md Known gaps already records this;
this test makes §Rules 5 itself honest so the contract index doesn't
over-claim. Static text reads only.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"


def test_rule5_names_lessons_and_labels_mem_search_unimplemented() -> None:
    """MUST — §Rules 5 describes lessons + flags mem-search as unimplemented."""
    body = CLAUDE_MD.read_text(encoding="utf-8")
    m = re.search(r"^5\.\s*(.+)$", body, re.MULTILINE)
    assert m, "CLAUDE.md §Rules must contain item 5"
    rule5 = m.group(1).lower()
    assert "lessons" in rule5, (
        "§Rules 5 must name the actual mechanism (lessons in "
        ".athanor/lessons/) rather than an unqualified 'auto memory save'."
    )
    assert "mem-search" in rule5 or "미구현" in rule5, (
        "§Rules 5 must label mem-search permanent persistence as "
        "unimplemented — scripts/ make zero mem-search calls (STATE.md "
        "Known gaps)."
    )
