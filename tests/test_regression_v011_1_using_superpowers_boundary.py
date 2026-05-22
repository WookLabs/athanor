"""Regression tests for v0.11.1 invariants — `using-superpowers` boundary.

The boundary is documented in two places:
1. `CLAUDE.md §Defense Mechanisms` — status table row + detail paragraph.
2. 10 athanor-native Thin Leader SKILL.md preambles — same canonical text.

Carve-out (intentional, per plan §Scope):
- `scope-drift` and `verification-before-completion` occupy unprefixed
  skill slots but are vendored-content skills with non-Thin-Leader
  semantics. They keep their own voice (T2 modification minimization)
  and are explicitly excluded from R2.

v0.12.0 scope note: the vendored `sp-using-superpowers` SKILL.md is
REMOVED in the atomic cut. The boundary itself survives as concept —
declared in CLAUDE.md prose + restated in each of the 10 native
Thin Leader skill preambles + (per plan §Phase 1) tracked in the
`concepts/` registry. The pre-v0.12.0 shape of this file included a
`VENDORED_SP_USING_SUPERPOWERS` constant + `test_vendored_sp_using_
superpowers_file_present`; both are removed because the vendored
file is gone.

Plan reference: docs/plans/2026-05-22-001-feat-v0.12.0-concept-kernel-cutover-plan-b.md
§Subtask 15 (test rewrite scope).
Earlier plan: docs/plans/2026-05-20-001-feat-v0.11.1-using-superpowers-boundary-plan.md
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
SKILLS_DIR = REPO_ROOT / "skills"

# 10 native Thin Leader skills — R2 scope.
NATIVE_THIN_LEADER_SKILLS = (
    "analyze",
    "debug",
    "deep-plan",
    "discuss",
    "lfg",
    "lite-plan",
    "plan",
    "review",
    "setup",
    "work",
)

# 2 intentionally-excluded skills — vendored-content at unprefixed slot.
EXCLUDED_VENDORED_NATIVE_SKILLS = (
    "scope-drift",
    "verification-before-completion",
)

CANONICAL_PREAMBLE_HEADING = "### v0.11.1 using-superpowers boundary"
CANONICAL_PREAMBLE_SIGNALS = (
    "Thin Leader",
    "planner-classified discipline",
    "superpowers:using-superpowers",
    "SessionStart",
    "advisory here",
    "leader dispatch",
    "CLAUDE.md §Defense Mechanisms",
)


# ---- CLAUDE.md boundary documentation ----


def test_claude_md_has_using_superpowers_boundary_row():
    """MUST (R1): CLAUDE.md §Defense Mechanisms status table contains the
    `using-superpowers boundary` row."""
    body = CLAUDE_MD.read_text(encoding="utf-8")
    assert "using-superpowers boundary (v0.11.1)" in body, (
        "CLAUDE.md §Defense Mechanisms must contain a row labelled "
        "`using-superpowers boundary (v0.11.1)`"
    )


def test_claude_md_boundary_paragraph_has_required_signals():
    """MUST (R1, D4): CLAUDE.md boundary documentation includes 4 signal
    phrases — using-superpowers / SessionStart / advisory / leader dispatch
    (or close synonyms)."""
    body = CLAUDE_MD.read_text(encoding="utf-8")
    required = ("using-superpowers", "SessionStart", "advisory", "leader dispatch")
    missing = [s for s in required if s not in body]
    assert not missing, (
        f"CLAUDE.md boundary documentation missing signal phrases: {missing}"
    )


def test_claude_md_boundary_uses_advisory_label():
    """MUST (R5): boundary documentation uses an `advisory` label — NOT
    `enforced`. v0.11.1 ships no runtime gate so an enforced claim would
    break the honesty arc."""
    body = CLAUDE_MD.read_text(encoding="utf-8")
    boundary_line = next(
        (ln for ln in body.splitlines() if "using-superpowers boundary (v0.11.1)" in ln),
        None,
    )
    assert boundary_line is not None, "boundary row not found"
    assert "advisory" in boundary_line, (
        f"v0.11.1 boundary row must carry an `advisory` label; row: {boundary_line[:160]!r}"
    )
    assert "**enforced**" not in boundary_line and "(enforced)" not in boundary_line, (
        f"v0.11.1 boundary row must NOT claim `enforced` — no runtime gate ships. "
        f"row: {boundary_line[:160]!r}"
    )


# ---- 10 native Thin Leader SKILL.md preambles ----


def test_each_native_thin_leader_skill_has_canonical_preamble_heading():
    """MUST (R2): each of the 10 native Thin Leader skills carries the
    `### v0.11.1 using-superpowers boundary` heading exactly once."""
    failures: list[str] = []
    for skill_name in NATIVE_THIN_LEADER_SKILLS:
        skill_md = SKILLS_DIR / skill_name / "SKILL.md"
        body = skill_md.read_text(encoding="utf-8")
        count = body.count(CANONICAL_PREAMBLE_HEADING)
        if count != 1:
            failures.append(f"skills/{skill_name}/SKILL.md: heading count={count} (expected 1)")
    assert not failures, (
        "v0.11.1 R2 violation — canonical preamble heading not present exactly once.\n"
        + "\n".join(failures)
    )


def test_each_native_preamble_contains_all_canonical_signals():
    """MUST (R2 + D4): each native preamble paragraph contains the
    7 canonical signal phrases (Thin Leader / planner-classified discipline /
    using-superpowers / SessionStart / advisory here / leader dispatch /
    CLAUDE.md §Defense Mechanisms cross-reference)."""
    failures: list[str] = []
    for skill_name in NATIVE_THIN_LEADER_SKILLS:
        skill_md = SKILLS_DIR / skill_name / "SKILL.md"
        body = skill_md.read_text(encoding="utf-8")
        missing = [s for s in CANONICAL_PREAMBLE_SIGNALS if s not in body]
        if missing:
            failures.append(f"skills/{skill_name}/SKILL.md missing: {missing}")
    assert not failures, (
        "v0.11.1 canonical signals missing from native preambles:\n"
        + "\n".join(failures)
    )


def test_excluded_vendored_skills_do_not_carry_thin_leader_preamble():
    """MUST (KD2 + carve-out): scope-drift and verification-before-completion
    do NOT carry the `### v0.11.1 using-superpowers boundary` heading —
    they are vendored-content skills with non-Thin-Leader semantics."""
    failures: list[str] = []
    for skill_name in EXCLUDED_VENDORED_NATIVE_SKILLS:
        skill_md = SKILLS_DIR / skill_name / "SKILL.md"
        body = skill_md.read_text(encoding="utf-8")
        if CANONICAL_PREAMBLE_HEADING in body:
            failures.append(
                f"skills/{skill_name}/SKILL.md unexpectedly contains the Thin Leader "
                f"preamble heading (carve-out violated — would inject a false claim "
                f"into vendored-content body)"
            )
    assert not failures, "\n".join(failures)


# ---- Honesty-arc voice pins for v0.11.1 ----


V011_1_BOUNDARY_FORBIDDEN_PHRASES = (
    "using-superpowers deprecated",
    "superpowers deprecated",
    "athanor replaces superpowers",
    "athanor replaces using-superpowers",
    "supersedes using-superpowers",
    "supersedes superpowers",
    "do not use using-superpowers",
    "do not use superpowers",
    "using-superpowers is obsolete",
    "superpowers is obsolete",
)


def test_claude_md_boundary_no_forbidden_supersession_phrases():
    """MUST (R6): CLAUDE.md boundary documentation uses positive-commitment
    framing only — no deprecate/replace/supersede/obsolete framing of
    `using-superpowers` or `superpowers`."""
    body = CLAUDE_MD.read_text(encoding="utf-8").lower()
    hits = [p for p in V011_1_BOUNDARY_FORBIDDEN_PHRASES if p in body]
    assert not hits, (
        f"v0.11.1 honesty-arc violation in CLAUDE.md — forbidden phrases: {hits}"
    )


def test_changelog_v011_1_entry_no_forbidden_supersession_phrases():
    """MUST (R6): if CHANGELOG.md has a v0.11.1 entry, it must not contain
    forbidden supersession phrases."""
    changelog = REPO_ROOT / "CHANGELOG.md"
    body = changelog.read_text(encoding="utf-8")
    lines = body.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if ln.startswith("## ") and ("0.11.1" in ln):
            start = i
            break
    if start is None:
        return
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
    section = "\n".join(lines[start:end]).lower()
    hits = [p for p in V011_1_BOUNDARY_FORBIDDEN_PHRASES if p in section]
    assert not hits, (
        f"v0.11.1 CHANGELOG entry must not contain supersession framing. "
        f"Forbidden phrases found: {hits}"
    )
