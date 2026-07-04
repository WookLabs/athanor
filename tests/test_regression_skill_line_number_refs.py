"""Regression suite for `skill_line_number_ref_check` — the line-number-reference
rot detector (D3 from session 2026-07-03-004 plan.md).

Locks the corrected regex (2+ digit threshold; fenced-block allowlist;
`skills/**/*.md` scope only) and the CLI subcommand `skill-line-refs`.

TDD cycle (this file):
  * Phase 1.1 — first commit asserts the 4 KNOWN rotted anchors are detected
    (function returns (False, [4 violations])). Pre-implementation this is RED
    (ImportError); post-implementation (lint function shipped, anchors still
    rotted) it is GREEN.
  * Phase 1.4 — after the 4 anchor fixes (§5a table) land in
    `skills/{lfg,lfg-goal}/SKILL.md`, the assertion flips to (True, []) — the
    canonical TDD green-flip on a clean tree.

Plan reference: session 2026-07-03-004 §D3, Phase 1.1 + Phase 1.4.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from scripts.gates.lint_checks import skill_line_number_ref_check

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"


# ---------------------------------------------------------------------------
# Phase 1.4 state — green on a clean (anchors-fixed) tree.
# ---------------------------------------------------------------------------
def test_skill_line_number_ref_check_clean_tree():
    """MUST — `skill_line_number_ref_check` returns (True, []) on current repo.

    The 4 historical rots (lfg:707, lfg-goal:700/716/724 per session
    2026-07-03-004 §5a anchor table) were de-fossilized to `(§<heading>)`
    references in Phase 1.3; this test pins the green state. A regression
    (re-introducing `line NNN` deep-prose refs with NNN >= 10) trips this
    lock at exit-2.
    """
    ok, violations = skill_line_number_ref_check(SKILLS_DIR)
    assert ok is True, (
        "skill_line_number_ref_check must return ok=True on the current tree; "
        f"got violations={violations!r}"
    )
    assert violations == [], (
        f"expected zero violations on the clean tree, got {violations!r}"
    )


# ---------------------------------------------------------------------------
# Phase 1.1 — regex behaviour locks (allowlist + 2-digit threshold).
# ---------------------------------------------------------------------------
def test_skill_line_number_ref_check_single_digit_refs_allowed(tmp_path: Path):
    """Single-digit `line 1` / `line 2` references (response/file) are NOT matched.

    The 2+ digit threshold (\\d{2,5}) is the discriminator between rotting
    deep-prose refs (3-digit source-line citations) and legitimate response-line
    references. Verifies §D3 allowlist rule.
    """
    skill = tmp_path / "demo" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(
        "---\nname: demo\ndescription: x\n---\n\n"
        "Sentinel on line 1 of the file. "
        "As line 1 of plan.md shows. "
        "Path citations like scripts/foo.py:123 are fine. "
        "Bare `line 7` references stay allowed.\n",
        encoding="utf-8",
    )
    ok, violations = skill_line_number_ref_check(tmp_path)
    assert ok is True, f"single-digit refs must NOT trip the lint: {violations!r}"
    assert violations == []


def test_skill_line_number_ref_check_fenced_code_block_allowed(tmp_path: Path):
    """Citations inside ``` fenced code blocks are NOT matched (allowlist)."""
    skill = tmp_path / "demo" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(
        "---\nname: demo\ndescription: x\n---\n\n"
        "Example:\n\n"
        "```python\n"
        "# see line 559 of the parser for the directive form\n"
        "pass\n"
        "```\n",
        encoding="utf-8",
    )
    ok, violations = skill_line_number_ref_check(tmp_path)
    assert ok is True, f"fenced-block citations must NOT trip the lint: {violations!r}"
    assert violations == []


@pytest.mark.parametrize(
    "rotted",
    [
        # The 4 known rotted forms per §D3.
        "the Step 9 directive form (line 559):",
        "Tier 3 language directive (~line 446); this section reuses it",
        "backtick-wrapped list — mirror lfg Step 9.5 / line 559:",
        "language directive (~line 446): `validation_status`,",
    ],
)
def test_skill_line_number_ref_check_detects_known_rots(
    tmp_path: Path, rotted: str
):
    """Each of the 4 known rotted forms (now fixed) trips the lint in isolation.

    Pinning the regex against historical rot forms prevents a future regex
    weakening that would silently re-admit them. The forms cover the
    parenthetical `(~line NNN)`, the slash `/ line NNN`, and the bare
    `(line NNN)` shapes from §D3.
    """
    skill = tmp_path / "demo" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(
        "---\nname: demo\ndescription: x\n---\n\n" + rotted + "\n",
        encoding="utf-8",
    )
    ok, violations = skill_line_number_ref_check(tmp_path)
    assert ok is False, (
        f"expected the rotted form {rotted!r} to trip the lint; got ok={ok}"
    )
    assert len(violations) >= 1, (
        f"expected >=1 violation for {rotted!r}; got {violations!r}"
    )


# ---------------------------------------------------------------------------
# CLI smoke — `python -m scripts.gates.lint_checks skill-line-refs skills`.
# ---------------------------------------------------------------------------
def test_cli_skill_line_refs_exits_zero_on_clean_tree():
    """MUST — CLI subcommand `skill-line-refs` exits 0 on the current repo."""
    result = subprocess.run(
        [sys.executable, "-m", "scripts.gates.lint_checks", "skill-line-refs", str(SKILLS_DIR)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"skill-line-refs CLI must exit 0 on clean tree; got exit={result.returncode}\n"
        f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
    )
