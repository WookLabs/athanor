"""Regression suite for `skill_size_cap_check` -- the D2 regrowth-brake size
ratchet from session 2026-07-03-004 plan.md.

Locks:
  * `skill_size_cap_check` returns (True, []) on the current repo -- no skill
    has grown past its measured baseline + 5% headroom.
  * The CLI subcommand `skill-size-cap` exits 0.
  * A skill that exceeds its cap trips the lint (fail-loud).

Honest scope (D2 docstring): this is a *regrowth brake*, NOT a shrink enforcer.
The diet itself is delivered by Phase-2 relocation and verified by char-count
acceptance criteria. The cap is `current + 5%` measured against the post-diet
baseline; to lower a cap, a future release must relocate load-bearing prose
AND retarget the cap constant in the same change.

Plan reference: session 2026-07-03-004 §D2, Phase 1.2 + Phase 3 cap refresh.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from scripts.gates.lint_checks import SKILL_SIZE_CAPS, skill_size_cap_check

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"


def test_skill_size_cap_check_passes_on_current_repo():
    """MUST -- every capped skill is at or below its baseline + 5% headroom.

    A failure here means a skill body grew past its cap. The fix is EITHER
    relocate load-bearing prose into `references/*.md` (preferred) OR raise
    the cap with a documented justification in the same change (last resort).
    """
    ok, violations = skill_size_cap_check(SKILLS_DIR)
    assert ok is True, (
        "skill_size_cap_check must return ok=True on the current tree; "
        f"got violations={violations!r}"
    )
    assert violations == [], (
        f"expected zero violations on the current tree, got {violations!r}"
    )


def test_skill_size_cap_check_trips_when_skill_exceeds_cap(tmp_path: Path):
    """A skill body that exceeds its cap must trip the lint (fail-loud)."""
    skills_dir = tmp_path / "skills"
    # Use one of the capped skill names so the cap dict hits it.
    skill_md = skills_dir / "work" / "SKILL.md"
    skill_md.parent.mkdir(parents=True)
    # Cap for "work" is SKILL_SIZE_CAPS["work"]; write a body just over it.
    cap = SKILL_SIZE_CAPS["work"]
    body = "x" * (cap + 1)
    skill_md.write_text(body, encoding="utf-8")
    ok, violations = skill_size_cap_check(skills_dir)
    assert ok is False, (
        f"expected ok=False when 'work' body exceeds cap={cap}; got ok={ok}"
    )
    assert len(violations) == 1, (
        f"expected exactly one violation; got {violations!r}"
    )
    assert "skill-size-cap violation" in violations[0]
    assert "work" in violations[0]


def test_skill_size_cap_check_skips_uncapped_skills(tmp_path: Path):
    """Skills not in SKILL_SIZE_CAPS are skipped (no aspirational target)."""
    skills_dir = tmp_path / "skills"
    skill_md = skills_dir / "uncapped-skill" / "SKILL.md"
    skill_md.parent.mkdir(parents=True)
    skill_md.write_text("x" * 100_000, encoding="utf-8")  # huge, but uncapped
    ok, violations = skill_size_cap_check(skills_dir)
    assert ok is True, (
        f"uncapped skill must NOT trip the lint; got violations={violations!r}"
    )
    assert violations == []


# ---------------------------------------------------------------------------
# CLI smoke -- `python -m scripts.gates.lint_checks skill-size-cap skills`.
# ---------------------------------------------------------------------------
def test_cli_skill_size_cap_exits_zero_on_current_repo():
    """MUST -- CLI subcommand `skill-size-cap` exits 0 on the current repo."""
    result = subprocess.run(
        [sys.executable, "-m", "scripts.gates.lint_checks", "skill-size-cap", str(SKILLS_DIR)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"skill-size-cap CLI must exit 0 on current repo; got exit={result.returncode}\n"
        f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
    )
