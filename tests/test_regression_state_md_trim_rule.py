"""Regression — STATE.md rotation carries a bounded-history trim rule.

Context
-------
The releaser ceremony Step 3 rotates `## Current Phase` → `## Previous
Phase` in `docs/STATE.md`. That rotation is append-only, so STATE.md
grows monotonically (the lfg/lfg-loop doc-lifecycle audit found 28 phase
sections / ~1336 lines with no trimming). Wave 1 adds a documented
bounded-history trim rule: once the retained `## Previous Phase` section
count exceeds a numeric cap, the oldest surplus sections are MOVED
(verbatim, no content loss) to `docs/archive/STATE-history.md`.

This test locks the trim rule into `agents/releaser.md` so a future
rewrite cannot silently drop it back to append-only. It does NOT assert a
section-count ceiling on the current STATE.md — the existing 28-section
backlog is trimmed progressively by the releaser on the next release, not
surgically in this change (risk-proportionate to a Low-severity finding).

Static text reads only — no subprocess, no file mutation.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RELEASER = REPO_ROOT / "agents" / "releaser.md"


def test_releaser_step3_documents_archive_move() -> None:
    """MUST — Step 3 trim rule routes surplus phases to STATE-history.md."""
    text = RELEASER.read_text(encoding="utf-8")
    assert "STATE-history.md" in text, (
        "agents/releaser.md Step 3 must document moving surplus STATE.md "
        "phase sections to docs/archive/STATE-history.md — without it, "
        "STATE.md rotation stays append-only and grows unbounded."
    )


def test_releaser_trim_rule_is_a_capped_nondestructive_move() -> None:
    """MUST — trim rule names a numeric cap and is a move, not a delete."""
    text = RELEASER.read_text(encoding="utf-8")
    assert "Previous Phase" in text and re.search(r"\b5\b", text), (
        "releaser.md trim rule must state a numeric cap (5) on retained "
        "'## Previous Phase' sections."
    )
    lowered = text.lower()
    assert "move" in lowered and ("not a delete" in lowered or "not a drop" in lowered), (
        "releaser.md trim rule must specify archival is a MOVE (verbatim, "
        "no content loss), not a destructive delete/drop."
    )
