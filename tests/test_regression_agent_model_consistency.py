"""Regression tests — agent model-tier consistency (frontmatter ↔ dispatch).

Context
-------
Athanor agent definitions under `agents/*.md` carry a `model:` field in
their YAML frontmatter that declares the intended reasoning tier (per
CLAUDE.md §"Effort Level": Planner/Critic = highest, Executor/Analyst =
standard, Cleaner = minimal). The standalone @-mention path uses that
frontmatter; the in-pipeline path uses an INLINE dispatch prompt embedded
in the corresponding SKILL.md / reference file. Each `agents/*.md` file
explicitly warns: "Keep this file in sync with the dispatch prompts in the
corresponding SKILL.md."

A drift was found (Goal: lfg/lfg-goal doc-lifecycle audit, Wave 1):
`agents/cleaner.md` frontmatter declared `model: haiku` (matching
CLAUDE.md "Cleaner: minimal effort"), but the dispatch prompt in
`skills/work/references/learner-cleaner.md` Step 5 and the Step-5 line in
`skills/work/SKILL.md` both said `sonnet`. This test locks the three
sources to agree, for both the Cleaner and the Learner, so the tier
declared in the reference agent is the tier actually dispatched.

These tests are static text reads only — no subprocess, no file mutation.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LEARNER_CLEANER_REF = REPO_ROOT / "skills" / "work" / "references" / "learner-cleaner.md"
WORK_SKILL = REPO_ROOT / "skills" / "work" / "SKILL.md"


def _frontmatter_model(agent_rel_path: str) -> str | None:
    """Read the `model:` tier from an agent file's YAML frontmatter."""
    text = (REPO_ROOT / agent_rel_path).read_text(encoding="utf-8")
    parts = text.split("---", 2)
    frontmatter = parts[1] if len(parts) >= 3 else ""
    m = re.search(r"^\s*model:\s*(\S+)\s*$", frontmatter, re.MULTILINE)
    return m.group(1) if m else None


def _dispatch_model(section_heading: str) -> str | None:
    """Read the `model:` tier from a dispatch block in learner-cleaner.md.

    Returns the first `model:` value appearing after `section_heading`.
    """
    text = LEARNER_CLEANER_REF.read_text(encoding="utf-8")
    idx = text.find(section_heading)
    if idx == -1:
        return None
    m = re.search(r'model:\s*"?(\w+)"?', text[idx:])
    return m.group(1) if m else None


def _skill_line_model(role: str) -> str | None:
    """Read the tier from a `{Role} agent (tier)` mention in work/SKILL.md."""
    text = WORK_SKILL.read_text(encoding="utf-8")
    m = re.search(rf"{role} agent \((\w+)\)", text)
    return m.group(1) if m else None


def test_cleaner_model_consistency() -> None:
    """MUST — Cleaner tier agrees across frontmatter, dispatch, and skill line.

    CLAUDE.md §Effort Level pins Cleaner to minimal effort (haiku). The
    reference frontmatter, the inline dispatch prompt, and the work-skill
    Step-5 line must all declare the same tier.
    """
    fm = _frontmatter_model("agents/cleaner.md")
    disp = _dispatch_model("## Step 5 — Cleaner Dispatch")
    skill = _skill_line_model("Cleaner")
    assert fm is not None and disp is not None and skill is not None, (
        f"Could not parse a model tier for Cleaner "
        f"(frontmatter={fm!r}, dispatch={disp!r}, skill_line={skill!r})."
    )
    assert fm == disp == skill, (
        f"Cleaner model tier drift: agents/cleaner.md frontmatter='{fm}', "
        f"learner-cleaner.md Step 5 dispatch='{disp}', "
        f"work/SKILL.md 'Cleaner agent (...)'='{skill}'. All three must "
        f"agree — the reference agent file warns to keep the dispatch "
        f"prompt in sync, and CLAUDE.md §Effort Level pins Cleaner to "
        f"minimal effort (haiku)."
    )


def test_learner_model_consistency() -> None:
    """MUST — Learner tier agrees across frontmatter, dispatch, and skill line."""
    fm = _frontmatter_model("agents/learner.md")
    disp = _dispatch_model("## Step 4 — Learner Dispatch")
    skill = _skill_line_model("Learner")
    assert fm is not None and disp is not None and skill is not None, (
        f"Could not parse a model tier for Learner "
        f"(frontmatter={fm!r}, dispatch={disp!r}, skill_line={skill!r})."
    )
    assert fm == disp == skill, (
        f"Learner model tier drift: agents/learner.md frontmatter='{fm}', "
        f"learner-cleaner.md Step 4 dispatch='{disp}', "
        f"work/SKILL.md 'Learner agent (...)'='{skill}'. All three must agree."
    )
