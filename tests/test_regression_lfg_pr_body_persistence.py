"""Regression — lfg PR body persists work-log + review summaries.

Context
-------
The lfg/lfg-goal doc-lifecycle audit found a persistence gap: the core
work record (`work-log.md`) and review record (`review.md`) live only in
the gitignored `.athanor/sessions/<id>/` tree. When the session is later
cleaned (cleaner Step 4, >30 days), the work narrative is lost — only the
commit/PR/plan-link survive in git.

Wave 3 closes the gap without changing the ephemeral-session design: the
lfg Step 7 PR body template gains a work summary slot and a review summary
slot, so the durable git artifact (the PR description) carries the record
forward. These tests lock those slots into Step 7.

Static text reads only — no subprocess, no file mutation.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LFG = REPO_ROOT / "skills" / "lfg" / "SKILL.md"


def _step7_block(text: str) -> str:
    """Return the Step 7 section body (until Step 8)."""
    start = text.find("### Step 7")
    if start == -1:
        return ""
    end = text.find("### Step 8", start)
    return text[start : end if end != -1 else len(text)]


def test_lfg_step7_pr_body_has_work_summary_slot() -> None:
    """MUST — Step 7 PR body summarizes the work-log."""
    block = _step7_block(LFG.read_text(encoding="utf-8")).lower()
    assert block, "skills/lfg/SKILL.md must retain a '### Step 7' section."
    assert "work-log" in block or "work summary" in block, (
        "lfg Step 7 PR body must include a work summary slot sourced from "
        ".athanor/sessions/<id>/work-log.md — otherwise the work record "
        "dies with the gitignored session tree."
    )


def test_lfg_step7_pr_body_has_review_summary_slot() -> None:
    """MUST — Step 7 PR body summarizes the review."""
    block = _step7_block(LFG.read_text(encoding="utf-8")).lower()
    assert "review" in block and ("summary" in block or "score" in block or "residual" in block), (
        "lfg Step 7 PR body must include a review summary slot (per-lens "
        "scores / residual findings from .athanor/sessions/<id>/review.md)."
    )
