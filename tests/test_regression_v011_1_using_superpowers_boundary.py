"""Regression tests for v0.11.1 invariants — `using-superpowers` boundary.

The boundary is documented in two places:
1. `CLAUDE.md §Defense Mechanisms` — status table row + canonical declaration
   subsection (`### using-superpowers boundary (v0.11.1) — canonical declaration`).
2. Native Thin Leader SKILL.md preambles — each carries a brief pointer
   (heading `### using-superpowers boundary` + 1-line cross-reference to
   CLAUDE.md). No verbatim restatement.

Carve-out (intentional, per plan §Scope):
- `scope-drift` and `verification-before-completion` occupy unprefixed
  skill slots but are vendored-content skills with non-Thin-Leader
  semantics. They keep their own voice (T2 modification minimization)
  and are explicitly excluded from R2.

v0.12.0 scope note: the vendored `sp-using-superpowers` SKILL.md is
REMOVED in the atomic cut. The boundary itself survives as concept —
declared in CLAUDE.md prose + pointed-to from each of the native
Thin Leader skill preambles + (per plan §Phase 1) tracked in the
`concepts/` registry. The pre-v0.12.0 shape of this file included a
`VENDORED_SP_USING_SUPERPOWERS` constant + `test_vendored_sp_using_
superpowers_file_present`; both are removed because the vendored
file is gone.

v0.13.0 scope extension: `lfg-goal` joined the boundary lock list as
the 11th native Thin Leader skill at the time. It is the goal-bounded
N-cycle orchestrator that wraps `/athanor:lfg` and itself respects the
Thin Leader contract. Per D11 (decisions.md 2026-05-22-002), lfg-goal
does NOT introduce a fifth identity invariant — it is an orchestration
layer composed of the existing four.

v0.17.0 / S07 scope contraction: `deep-plan` + `lite-plan` were
collapsed into `/athanor:plan --depth=<value>`; their skill directories
were removed. The native Thin Leader roster shrank 11 → 9. The later
`assess` skill extends the current boundary roster to 10 (assess, analyze,
debug, discuss, lfg, lfg-goal, plan, review, setup, work).

v0.17.0 / S04 scope shift (hoist): the verbatim 6-line boundary
subsection that was inlined in each of the native skill preambles
through v0.16.x has been hoisted to a single canonical anchor in
CLAUDE.md. Each native skill now carries a brief 2-line pointer
(heading `### using-superpowers boundary` + 1-line "See CLAUDE.md …"
cross-reference). R2 in this file is rewritten accordingly: the
verbatim-content checks are replaced with pointer-presence checks,
and a new CLAUDE.md canonical-anchor check is added (R1+).

Plan references:
- docs/plans/2026-05-22-001-feat-v0.13.0-lfg-goal-skill-plan.md
  §Subtask 11 (test list extension 10 → 11).
- docs/plans/2026-05-20-001-feat-v0.11.1-using-superpowers-boundary-plan.md
- docs/plans/2026-05-22-001-feat-v0.12.0-concept-kernel-cutover-plan-b.md
- S04 hoist task + S07 depth-flag collapse (v0.17.0).
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
SKILLS_DIR = REPO_ROOT / "skills"

# 10 native Thin Leader skills — R2 scope (post-S07 plus assess).
# v0.13.0 added `lfg-goal` per plan §Subtask 11 (11-entry roster).
# v0.17.0 / S07 collapsed `deep-plan` + `lite-plan` into `/athanor:plan
# --depth=<value>`. The assess skill later joined this boundary roster.
NATIVE_THIN_LEADER_SKILLS = (
    "assess",
    "analyze",
    "debug",
    "discuss",
    "lfg",
    "lfg-goal",
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

# v0.17.0 pointer shape — what each native skill must carry post-hoist.
POINTER_HEADING = "### using-superpowers boundary"
POINTER_CROSSREF_SIGNALS = (
    "CLAUDE.md",
    "using-superpowers boundary",
)

# v0.17.0 canonical anchor in CLAUDE.md — single source of truth.
CANONICAL_ANCHOR_HEADING = (
    "### using-superpowers boundary (v0.11.1) — canonical declaration"
)
CANONICAL_ANCHOR_SIGNALS = (
    "Thin Leader",
    "planner-classified discipline",
    "superpowers:using-superpowers",
    "SessionStart",
    "advisory here",
    "leader dispatch",
)

# Legacy heading — must NO LONGER appear in any native skill body.
# (It may still appear in CLAUDE.md as a label, e.g. the status-table row
# `using-superpowers boundary (v0.11.1)` — that is a different shape.)
LEGACY_VERBATIM_HEADING = "### v0.11.1 using-superpowers boundary"


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


def test_claude_md_has_canonical_anchor_subsection():
    """MUST (R1+, v0.17.0 / S04 hoist): CLAUDE.md carries a canonical anchor
    subsection that holds the boundary text in full. Per-skill pointers
    rely on this anchor as the single source of truth."""
    body = CLAUDE_MD.read_text(encoding="utf-8")
    assert CANONICAL_ANCHOR_HEADING in body, (
        f"CLAUDE.md must carry the canonical anchor heading "
        f"`{CANONICAL_ANCHOR_HEADING}` as the single source of truth "
        f"for the using-superpowers boundary text."
    )


def test_claude_md_canonical_anchor_contains_full_signal_set():
    """MUST (R1+, v0.17.0 / S04 hoist): the canonical anchor subsection in
    CLAUDE.md contains the full canonical-signal phrase set
    (Thin Leader / planner-classified discipline / superpowers:using-superpowers /
    SessionStart / advisory here / leader dispatch). Per-skill pointers no
    longer carry these phrases verbatim — CLAUDE.md must."""
    body = CLAUDE_MD.read_text(encoding="utf-8")
    lines = body.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if ln.strip() == CANONICAL_ANCHOR_HEADING:
            start = i
            break
    assert start is not None, (
        f"canonical anchor heading `{CANONICAL_ANCHOR_HEADING}` not found"
    )
    end = len(lines)
    for j in range(start + 1, len(lines)):
        stripped = lines[j].lstrip()
        if stripped.startswith("## ") or stripped.startswith("### "):
            end = j
            break
    anchor_section = "\n".join(lines[start:end])
    missing = [s for s in CANONICAL_ANCHOR_SIGNALS if s not in anchor_section]
    assert not missing, (
        f"CLAUDE.md canonical anchor subsection missing signal phrases: {missing}"
    )


# ---- native Thin Leader SKILL.md pointers (v0.17.0 / S04 hoist) ----


def test_each_native_thin_leader_skill_has_pointer_heading():
    """MUST (R2, v0.17.0 / S04 hoist): each native Thin Leader skill carries
    the `### using-superpowers boundary` pointer heading exactly once.
    v0.13.0 extended the list 10 → 11 by adding `lfg-goal`; v0.17.0 / S07
    contracted the list 11 → 9 by collapsing `deep-plan` + `lite-plan`
    into `/athanor:plan --depth=<value>`; assess later extends it to 10."""
    failures: list[str] = []
    for skill_name in NATIVE_THIN_LEADER_SKILLS:
        skill_md = SKILLS_DIR / skill_name / "SKILL.md"
        body = skill_md.read_text(encoding="utf-8")
        count = sum(
            1 for ln in body.splitlines() if ln.strip() == POINTER_HEADING
        )
        if count != 1:
            failures.append(
                f"skills/{skill_name}/SKILL.md: pointer heading count={count} (expected 1)"
            )
    assert not failures, (
        "v0.17.0 R2 violation — pointer heading not present exactly once.\n"
        + "\n".join(failures)
    )


def test_each_native_skill_pointer_cross_references_claude_md():
    """MUST (R2 + v0.17.0 / S04 hoist): each pointer body cross-references
    CLAUDE.md so the reader can find the canonical declaration. The
    cross-reference must mention `CLAUDE.md` AND `using-superpowers
    boundary` (the anchor label). Located within 5 lines after the
    pointer heading."""
    failures: list[str] = []
    for skill_name in NATIVE_THIN_LEADER_SKILLS:
        skill_md = SKILLS_DIR / skill_name / "SKILL.md"
        lines = skill_md.read_text(encoding="utf-8").splitlines()
        heading_idx = next(
            (i for i, ln in enumerate(lines) if ln.strip() == POINTER_HEADING),
            None,
        )
        if heading_idx is None:
            failures.append(f"skills/{skill_name}/SKILL.md: pointer heading missing")
            continue
        window = "\n".join(lines[heading_idx + 1 : heading_idx + 6])
        missing = [s for s in POINTER_CROSSREF_SIGNALS if s not in window]
        if missing:
            failures.append(
                f"skills/{skill_name}/SKILL.md: pointer cross-reference missing "
                f"signals {missing} in 5-line window after heading"
            )
    assert not failures, (
        "v0.17.0 pointer cross-reference incomplete:\n" + "\n".join(failures)
    )


def test_each_native_skill_pointer_section_is_brief():
    """MUST (R2 + v0.17.0 / S04 hoist): the pointer subsection MUST be brief
    (heading + body ≤ 3 non-blank content lines) — the whole point of S04
    is removing verbatim restatement. Anything longer means the verbatim
    block has crept back in."""
    failures: list[str] = []
    for skill_name in NATIVE_THIN_LEADER_SKILLS:
        skill_md = SKILLS_DIR / skill_name / "SKILL.md"
        lines = skill_md.read_text(encoding="utf-8").splitlines()
        heading_idx = next(
            (i for i, ln in enumerate(lines) if ln.strip() == POINTER_HEADING),
            None,
        )
        if heading_idx is None:
            failures.append(f"skills/{skill_name}/SKILL.md: pointer heading missing")
            continue
        # Walk forward until we hit any markdown heading or `---` rule.
        end = len(lines)
        for j in range(heading_idx + 1, len(lines)):
            stripped = lines[j].lstrip()
            if stripped.startswith("#"):
                end = j
                break
            if stripped.startswith("---"):
                end = j
                break
        body_lines = [ln for ln in lines[heading_idx + 1 : end] if ln.strip()]
        if len(body_lines) > 3:
            failures.append(
                f"skills/{skill_name}/SKILL.md: pointer subsection body has "
                f"{len(body_lines)} non-blank lines (expected ≤3). "
                f"Verbatim block likely crept back in."
            )
    assert not failures, (
        "v0.17.0 pointer-brevity violation:\n" + "\n".join(failures)
    )


def test_no_native_skill_carries_legacy_verbatim_heading():
    """MUST (R2 + v0.17.0 / S04 hoist): the legacy `### v0.11.1
    using-superpowers boundary` heading must no longer appear in any
    native skill body. Presence indicates the verbatim subsection
    survived the hoist."""
    failures: list[str] = []
    for skill_name in NATIVE_THIN_LEADER_SKILLS:
        skill_md = SKILLS_DIR / skill_name / "SKILL.md"
        body = skill_md.read_text(encoding="utf-8")
        if LEGACY_VERBATIM_HEADING in body:
            failures.append(
                f"skills/{skill_name}/SKILL.md still contains legacy heading "
                f"`{LEGACY_VERBATIM_HEADING}` — hoist incomplete"
            )
    assert not failures, "\n".join(failures)


def test_excluded_vendored_skills_do_not_carry_thin_leader_pointer():
    """MUST (KD2 + carve-out): scope-drift and verification-before-completion
    do NOT carry the `### using-superpowers boundary` pointer heading or
    the legacy verbatim heading — they are vendored-content skills with
    non-Thin-Leader semantics."""
    failures: list[str] = []
    for skill_name in EXCLUDED_VENDORED_NATIVE_SKILLS:
        skill_md = SKILLS_DIR / skill_name / "SKILL.md"
        body = skill_md.read_text(encoding="utf-8")
        lines = body.splitlines()
        if any(ln.strip() == POINTER_HEADING for ln in lines):
            failures.append(
                f"skills/{skill_name}/SKILL.md unexpectedly contains the Thin Leader "
                f"pointer heading (carve-out violated — would inject a false claim "
                f"into vendored-content body)"
            )
        if LEGACY_VERBATIM_HEADING in body:
            failures.append(
                f"skills/{skill_name}/SKILL.md unexpectedly contains the legacy "
                f"verbatim Thin Leader heading (carve-out violated)"
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
