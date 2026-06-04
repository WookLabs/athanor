"""Regression — Cleaner ages out stale goals; the D13 reference is backed.

Context
-------
`skills/lfg-goal/SKILL.md` §Goal Storage Lifecycle states that
abandoned / blocked / max-iterations goals "stay in `.athanor/goals/` for
`lfgGoal.goalRetentionDays` (default 30) then cleaner agent ages them out
per D13." The lfg/lfg-goal doc-lifecycle audit found that the Cleaner
(`agents/cleaner.md`) had NO goals-cleaning step — its Step 4 only cleans
`.athanor/sessions/`. So the D13 reference was a *broken cross-reference*:
`.athanor/goals/<id>/` would never be aged out by any automatic path.

Wave 2 adds a 'Clean Old Goals' step to the Cleaner agent and synchronises
the inline dispatch prompt. These tests lock:

1. The Cleaner agent documents a goals-cleaning step bound to
   `goalRetentionDays`, and excludes `complete` goals (those are archived
   to `docs/goals-completed/` and their live tree needs user action).
2. The inline dispatch prompt (`learner-cleaner.md` Step 5) is in sync.
3. The reference↔implementation correspondence: if lfg-goal claims the
   cleaner ages out stale goals (D13), the Cleaner MUST have the step —
   so the promise cannot silently go dangling again.

Static text reads only — no subprocess, no file mutation.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLEANER = REPO_ROOT / "agents" / "cleaner.md"
LEARNER_CLEANER = REPO_ROOT / "skills" / "work" / "references" / "learner-cleaner.md"
LFG_GOAL = REPO_ROOT / "skills" / "lfg-goal" / "SKILL.md"


def test_cleaner_has_goals_cleaning_step() -> None:
    """MUST — Cleaner agent documents a retention-bound goals-cleaning step."""
    text = CLEANER.read_text(encoding="utf-8")
    assert re.search(r"clean\s+old\s+goals", text, re.IGNORECASE), (
        "agents/cleaner.md must add a 'Clean Old Goals' step — its Step 4 "
        "only cleans .athanor/sessions/, leaving .athanor/goals/ unmanaged."
    )
    low = text.lower()
    assert "goalretentiondays" in low, (
        "the goals-cleaning step must bind to lfgGoal.goalRetentionDays as "
        "its retention window."
    )
    assert "complete" in low and "never" in low, (
        "the goals-cleaning step must NEVER touch goals whose status is "
        "complete (archived to docs/goals-completed/; user action required "
        "to delete the live tree)."
    )


def test_cleaner_dispatch_prompt_syncs_goals_cleaning() -> None:
    """MUST — inline Cleaner dispatch prompt is in sync with the agent step."""
    text = LEARNER_CLEANER.read_text(encoding="utf-8")
    idx = text.find("## Step 5 — Cleaner Dispatch")
    assert idx != -1, "learner-cleaner.md must retain the Cleaner dispatch section."
    sub = text[idx:].lower()
    assert "goals" in sub and "goalretentiondays" in sub, (
        "learner-cleaner.md Cleaner dispatch prompt must be kept in sync "
        "with agents/cleaner.md's goals-cleaning step (goalsDir / "
        "goalRetentionDays); otherwise the in-pipeline cleaner won't age "
        "out stale goals."
    )


def test_d13_reference_is_backed_by_cleaner_step() -> None:
    """MUST — if lfg-goal cites the cleaner for goal aging, the step exists.

    Locks the broken-cross-reference class: a 'cleaner ages them out'
    claim in lfg-goal must have a real goals-cleaning step in the Cleaner.
    """
    skill = LFG_GOAL.read_text(encoding="utf-8").lower()
    cleaner = CLEANER.read_text(encoding="utf-8")
    references_cleaner = "cleaner agent ages them out" in skill or "per d13" in skill
    if references_cleaner:
        assert re.search(r"clean\s+old\s+goals", cleaner, re.IGNORECASE), (
            "skills/lfg-goal/SKILL.md claims the cleaner agent ages out "
            "stale goals (D13), but agents/cleaner.md has no goals-cleaning "
            "step — broken cross-reference. Add the 'Clean Old Goals' step "
            "or remove the claim."
        )
