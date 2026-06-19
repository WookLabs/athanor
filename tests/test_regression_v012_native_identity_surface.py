"""Regression tests for v0.12.0 native identity surface preservation.

Plan reference: docs/plans/2026-05-22-001-feat-v0.12.0-concept-kernel-cutover-plan-b.md
§Subtask 15.

The atomic v0.12.0 cut removes the vendored CE/superpowers surface
but the four athanor identity invariants survive intact:

  1. Thin Leader contract — leader dispatches; workers do the work.
  2. Cross-model adversarial planning — `/athanor:plan` runs
     Planner A (Claude) + Planner B (Codex) + Critic.
  3. Spec-then-TDD discipline — `/athanor:work` Splitter execution_note
     + conjunction-of-three Phase 3 gate.
  4. Stop hook runtime gate — `scripts/hooks/stop_verify_claims.py` fires
     on every Stop event with whitelist + paraphrase + homoglyph detection.

The current athanor-native Thin Leader skills (post-v0.17.0 / S07 collapse of
deep-plan + lite-plan into `/athanor:plan --depth=`, plus assess and prompt-gen) must continue to
exist at depth 1 under `skills/` for Claude Code auto-discovery. The
companion-fix arc (v0.11.3 → v0.11.7) scripts continue to live in
`scripts/hooks/`.

Voice constraint (D7): docstrings here use direct attribution to the
plan-of-record; no "translated", "interpreted", "we discovered", or
"natural maturation" framing.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
HOOK_SCRIPTS_DIR = REPO_ROOT / "scripts" / "hooks"

# Current athanor-native Thin Leader skills (per CLAUDE.md §Commands table).
# v0.17.0 / S07 collapsed `deep-plan` + `lite-plan` into `/athanor:plan
# --depth=<value>` (see `docs/v0.17.0-migration.md`); the tuple shrinks
# in lockstep with command-surface changes.
NATIVE_THIN_LEADER_SKILLS = (
    "assess",
    "analyze",
    "debug",
    "discuss",
    "lfg",
    "lfg-goal",
    "plan",
    "prompt-gen",
    "review",
    "setup",
    "work",
)


def test_thin_leader_skills_present():
    """MUST: all athanor-native Thin Leader skill directories exist.

    Each skill ships at `skills/<name>/SKILL.md` for Claude Code depth-1
    auto-discovery. Missing any one means a regression in the native
    surface (the very thing v0.12.0 promotes as the only product surface).
    """
    missing = []
    no_skill_md = []
    for name in NATIVE_THIN_LEADER_SKILLS:
        skill_dir = SKILLS_DIR / name
        if not skill_dir.is_dir():
            missing.append(name)
            continue
        if not (skill_dir / "SKILL.md").is_file():
            no_skill_md.append(name)
    assert not missing, (
        f"MUST: {len(missing)} of {len(NATIVE_THIN_LEADER_SKILLS)} athanor-"
        f"native Thin Leader skill directories absent: {missing!r}. "
        f"the current command surface is reflected in CLAUDE.md and "
        f"docs/runtime-surface-contract.json."
    )
    assert not no_skill_md, (
        f"MUST: athanor-native skill(s) missing SKILL.md: {no_skill_md!r}. "
        f"Claude Code auto-discovery requires the SKILL.md file."
    )


def test_identity_invariants_documented():
    """MUST: CLAUDE.md names all four identity invariants by their canonical
    labels.

    The labels appear in the §Defense Mechanisms table or the §Rules
    section (or the legacy §Vendored Surface body retained as historical
    context). Lower-case substring match is sufficient — the canonical
    phrasing is locked elsewhere; this test only pins presence.
    """
    body = CLAUDE_MD.read_text(encoding="utf-8").lower()
    invariants = (
        "thin leader",
        "cross-model adversarial",
        "spec-then-tdd",
        "stop hook",
    )
    missing = [needle for needle in invariants if needle not in body]
    assert not missing, (
        f"MUST: CLAUDE.md does not name identity invariant(s) {missing!r}. "
        f"The four invariants must remain documented post-v0.12.0; the "
        f"vendored surface section may have shrunk but the identity "
        f"surface body must still enumerate them."
    )


def test_companion_fix_arc_scripts_present():
    """MUST: the Stop hook companion-fix arc scripts (v0.11.3 → v0.11.7)
    live in `scripts/hooks/` post-v0.12.0.

    The atomic cut removes vendored skills + sub-agents; the runtime gate
    machinery is OUTSIDE that scope per D10 / D11 (companion-fix arc
    preserved intact).
    """
    required = (
        HOOK_SCRIPTS_DIR / "stop_verify_claims.py",  # v0.7.7 + v0.10.2/3 + v0.11.3 layers
        HOOK_SCRIPTS_DIR / "hook_state.py",  # v0.7.9 nonce-state circuit breaker
        HOOK_SCRIPTS_DIR / "sentinel_helper.py",  # v0.11.6 body-hash binding
    )
    missing = [str(p.relative_to(REPO_ROOT)) for p in required if not p.is_file()]
    assert not missing, (
        f"MUST: companion-fix arc script(s) missing: {missing!r}. v0.12.0 "
        f"keeps the Stop hook runtime gate intact (D10 / D11)."
    )
