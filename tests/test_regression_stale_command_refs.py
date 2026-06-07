"""Regression — no dead command/flag references in user-facing docs.

Context
-------
The ref-adoption + cleanup audit (v0.18.3) found two stale references that
survived earlier surface changes:

- `README.md` advertised `/athanor:deep-plan` and `/athanor:lite-plan` as
  live commands, but v0.17.0 (S07) folded both into
  `/athanor:plan --depth={deep|lite}`. CLAUDE.md and the plan skill use the
  flag form; only README lagged.
- `skills/discuss/SKILL.md` promised the `--new-session` flag, which was
  reclassified a broken-promise in v0.11.7 (originally a v0.8.0 release-note
  promise, never implemented). CLAUDE.md §Session Lookup Convention already
  drops the flag from the stale-session announcement; discuss lagged.

These tests lock the dead references out so they can't drift back in.
Static text reads only — no subprocess, no file mutation.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"
DISCUSS = REPO_ROOT / "skills" / "discuss" / "SKILL.md"
DESIGN = REPO_ROOT / "docs" / "DESIGN.md"


def test_readme_no_dead_plan_commands() -> None:
    """MUST — README uses /athanor:plan --depth=, not deep-plan/lite-plan."""
    body = README.read_text(encoding="utf-8")
    for dead in ("/athanor:deep-plan", "/athanor:lite-plan"):
        assert dead not in body, (
            f"README.md references the dead command {dead!r}; v0.17.0 folded "
            f"it into '/athanor:plan --depth='. Use the flag form."
        )
    assert "--depth=" in body, (
        "README.md must document the '--depth=' flag form of /athanor:plan."
    )


def test_design_no_dead_plan_commands() -> None:
    """MUST — docs/DESIGN.md uses the --depth= flag form, not deep-plan/lite-plan.

    v0.18.7 plugin-diet: DESIGN.md (referenced by README/STATE/ROADMAP) still
    showed the v0.17.0-removed `/athanor:deep-plan` / `/athanor:lite-plan`
    commands in its pipeline diagrams + tier table. Lock the dead forms out.
    """
    body = DESIGN.read_text(encoding="utf-8")
    for dead in ("/athanor:deep-plan", "/athanor:lite-plan"):
        assert dead not in body, (
            f"docs/DESIGN.md references the dead command {dead!r}; v0.17.0 (S07) "
            f"folded it into '/athanor:plan --depth='. Use the flag form."
        )
    assert "--depth=" in body, (
        "docs/DESIGN.md must document the '--depth=' flag form of /athanor:plan."
    )


def test_discuss_no_new_session_flag_promise() -> None:
    """MUST — discuss does not promise the broken-promise --new-session flag."""
    body = DISCUSS.read_text(encoding="utf-8")
    assert "--new-session flag" not in body, (
        "skills/discuss/SKILL.md must not promise the '--new-session flag' "
        "(reclassified a broken-promise in v0.11.7). The stale-session "
        "announcement should point to manual session creation only, matching "
        "CLAUDE.md §Session Lookup Convention."
    )
