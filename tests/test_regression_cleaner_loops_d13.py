"""Regression — Cleaner ages out stale loops; the D13 reference is backed.

Context
-------
`skills/lfg-loop/SKILL.md` §Loop Storage Lifecycle states that
abandoned / blocked / max-iterations loops "stay in `.athanor/loops/` for
`lfgLoop.loopRetentionDays` (default 30) then cleaner agent ages them out
per D13." The lfg/lfg-loop doc-lifecycle audit found that the Cleaner
(`docs/agent-roles/cleaner.md`) had NO loops-cleaning step — its Step 4 only cleans
`.athanor/sessions/`. So the D13 reference was a *broken cross-reference*:
`.athanor/loops/<id>/` would never be aged out by any automatic path.

Wave 2 adds a 'Clean Old Loops' step to the Cleaner agent and synchronises
the inline dispatch prompt. These tests lock:

1. The Cleaner agent documents a loops-cleaning step bound to
   `loopRetentionDays`, and excludes `complete` loops (those are archived
   to `docs/loops-completed/` and their live tree needs user action).
2. The inline dispatch prompt (`learner-cleaner.md` Step 5) is in sync.
3. The reference↔implementation correspondence: if lfg-loop claims the
   cleaner ages out stale goals (D13), the Cleaner MUST have the step —
   so the promise cannot silently go dangling again.

Static text reads only — no subprocess, no file mutation.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLEANER = REPO_ROOT / "docs" / "agent-roles" / "cleaner.md"
LEARNER_CLEANER = REPO_ROOT / "skills" / "work" / "references" / "learner-cleaner.md"
LFG_LOOP = REPO_ROOT / "skills" / "lfg-loop" / "SKILL.md"


def test_cleaner_has_loops_cleaning_step() -> None:
    """MUST — Cleaner agent documents a retention-bound loops-cleaning step."""
    text = CLEANER.read_text(encoding="utf-8")
    assert re.search(r"clean\s+old\s+loops", text, re.IGNORECASE), (
        "docs/agent-roles/cleaner.md must add a 'Clean Old Loops' step — its Step 4 "
        "only cleans .athanor/sessions/, leaving .athanor/loops/ unmanaged."
    )
    low = text.lower()
    assert "loopretentiondays" in low, (
        "the loops-cleaning step must bind to lfgLoop.loopRetentionDays as "
        "its retention window."
    )
    assert "complete" in low and "never" in low, (
        "the loops-cleaning step must NEVER touch loops whose status is "
        "complete (archived to docs/loops-completed/; user action required "
        "to delete the live tree)."
    )


def test_cleaner_dispatch_prompt_syncs_loops_cleaning() -> None:
    """MUST — inline Cleaner dispatch prompt is in sync with the agent step."""
    text = LEARNER_CLEANER.read_text(encoding="utf-8")
    idx = text.find("## Step 5 — Cleaner Dispatch")
    assert idx != -1, "learner-cleaner.md must retain the Cleaner dispatch section."
    sub = text[idx:].lower()
    assert "loops" in sub and "loopretentiondays" in sub, (
        "learner-cleaner.md Cleaner dispatch prompt must be kept in sync "
        "with docs/agent-roles/cleaner.md's loops-cleaning step (loopsDir / "
        "loopRetentionDays); otherwise the in-pipeline cleaner won't age "
        "out stale loops."
    )


def test_d13_reference_is_backed_by_cleaner_step() -> None:
    """MUST — if lfg-loop cites the cleaner for loop aging, the step exists.

    Locks the broken-cross-reference class: a 'cleaner ages them out'
    claim in lfg-loop must have a real loops-cleaning step in the Cleaner.
    """
    skill = LFG_LOOP.read_text(encoding="utf-8").lower()
    cleaner = CLEANER.read_text(encoding="utf-8")
    references_cleaner = "cleaner agent ages them out" in skill or "per d13" in skill
    if references_cleaner:
        assert re.search(r"clean\s+old\s+loops", cleaner, re.IGNORECASE), (
            "skills/lfg-loop/SKILL.md claims the cleaner agent ages out "
            "stale loops (D13), but docs/agent-roles/cleaner.md has no loops-cleaning "
            "step — broken cross-reference. Add the 'Clean Old Loops' step "
            "or remove the claim."
        )
