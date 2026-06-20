"""Regression — no stale command/flag references in user-facing docs.

Context
-------
The ref-adoption + cleanup audit (v0.18.3) found two stale references that
survived earlier surface changes:

- `README.md` once advertised `/athanor:deep-plan` and `/athanor:lite-plan`
  as independent commands after v0.17.0 (S07) folded both into
  `/athanor:plan --depth={deep|lite}`. They are live again as thin wrappers,
  but user-facing docs must identify them as wrappers over the canonical
  `/athanor:plan` depth pipeline.
- `skills/discuss/SKILL.md` promised the `--new-session` flag, which was
  reclassified a broken-promise in v0.11.7 (originally a v0.8.0 release-note
  promise, never implemented). CLAUDE.md §Session Lookup Convention already
  drops the flag from the stale-session announcement; discuss lagged.

These tests lock stale independent-command framing out so it can't drift back in.
Static text reads only — no subprocess, no file mutation.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"
DISCUSS = REPO_ROOT / "skills" / "discuss" / "SKILL.md"
DESIGN = REPO_ROOT / "docs" / "DESIGN.md"
SKILLS_DIR = REPO_ROOT / "skills"

_LIVE_PLAN_WRAPPERS = ("/athanor:deep-plan", "/athanor:lite-plan")
_WRAPPER_SKILLS = {"deep-plan", "lite-plan"}
_ALLOWED_PLAN_REFERENCE_SKILLS = {"plan", "prompt-gen", *_WRAPPER_SKILLS}


def test_readme_documents_plan_wrappers_as_depth_aliases() -> None:
    """MUST — README names the wrappers and the canonical depth form."""
    body = README.read_text(encoding="utf-8")
    for command in _LIVE_PLAN_WRAPPERS:
        assert command in body, f"README.md must document live wrapper {command!r}."
    assert "--depth=" in body, (
        "README.md must document the '--depth=' flag form of /athanor:plan."
    )
    assert "thin wrapper" in body.lower(), (
        "README.md must identify deep/lite plan commands as thin wrappers, "
        "not independent planning implementations."
    )


def test_design_documents_plan_wrappers_as_depth_aliases() -> None:
    """MUST — docs/DESIGN.md names wrappers as aliases over --depth=."""
    body = DESIGN.read_text(encoding="utf-8")
    for command in _LIVE_PLAN_WRAPPERS:
        assert command in body, f"docs/DESIGN.md must document live wrapper {command!r}."
    assert "--depth=" in body, (
        "docs/DESIGN.md must document the '--depth=' flag form of /athanor:plan."
    )
    assert "thin wrapper" in body.lower(), (
        "docs/DESIGN.md must identify deep/lite plan commands as thin wrappers, "
        "not independent planning implementations."
    )


def test_only_plan_and_wrapper_skills_name_plan_wrappers() -> None:
    """MUST — routing suggestions use `/athanor:plan --depth=` unless they
    are the canonical plan skill or one of the thin wrapper SKILL.md files.
    """
    offenders: list[str] = []
    for skill_md in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        if skill_md.parent.name in _ALLOWED_PLAN_REFERENCE_SKILLS:
            continue
        body = skill_md.read_text(encoding="utf-8")
        for command in _LIVE_PLAN_WRAPPERS:
            if command in body:
                offenders.append(f"{skill_md.parent.name}: {command}")
    assert not offenders, (
        "Skills outside plan/deep-plan/lite-plan must route planning depth "
        f"through '/athanor:plan --depth=' to avoid duplicate entrypoint drift. "
        f"Offenders: {offenders}"
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
