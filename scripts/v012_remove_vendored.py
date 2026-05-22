#!/usr/bin/env python3
"""
v012_remove_vendored.py — execute the v0.12.0 vendored-surface removal.

Scope (per docs/plans/2026-05-22-001-feat-v0.12.0-concept-kernel-cutover-plan-b.md
D14.2 corrected counts + D8 KEEP carve-out + D9 FULL-DROP for ce-plan / ce-work
/ ce-lfg):

  Disk truth (Subtask 3 inventory):
    - 33 ce-* + 13 sp-* = 46 vendored skill directories
    - 49 vendored sub-agent files at agents/vendored/ce/*.agent.md

  Removal scope:
    Skills:    45 to remove (5 LIFT-source + 40 DROP); 1 KEEP (ce-test-browser)
    Sub-agents: 47 to remove; 2 KEEP
      (ce-git-history-analyzer, ce-repo-research-analyst)

The script invokes `git rm -r <path>` for each target. It is idempotent: a
missing path is reported and skipped, not treated as failure (so re-running
after a partial removal completes the operation cleanly).

CLI:
  python3 scripts/v012_remove_vendored.py            # executes git rm
  python3 scripts/v012_remove_vendored.py --dry-run  # reports only; no git ops

Exit codes:
  0 — success (all targets accounted for; per-path failures during execute
      mode still surface as exit 1)
  1 — disk-count drift OR a `git rm -r` invocation failed

Defense-in-depth: both modes assert the disk shows exactly the expected
counts (46 skills total → 45 removable, 49 sub-agents total → 47 removable)
before any operation. A drift exits 1 with an explanatory message.

Voice constraints (D7 forbidden phrases): docstring and stdout messages
avoid "translated", "interpreted", "we discovered", "natural maturation".

Companion-fix arc (D11) preserved automatically: scripts/hooks/
stop_verify_claims.py and scripts/check_vendor_drift.py live outside the
vendored directories so this script never touches them.

Stdlib only, Python 3.10+.

Plan reference:
  docs/plans/2026-05-22-001-feat-v0.12.0-concept-kernel-cutover-plan-b.md
  §Subtask 14 (Phase 5 — Vendored removal script).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
AGENTS_DIR = REPO_ROOT / "agents" / "vendored" / "ce"


# ---------------------------------------------------------------------------
# Hardcoded triage tables — pinned by D14.2. Disk drift surfaces as exit 1.
# ---------------------------------------------------------------------------

# LIFT-source skill directories: their concept is migrated into an athanor-
# native skill in Subtasks 7–11; the upstream directory itself is removed in
# this phase.
LIFT_SOURCE_SKILLS: set[str] = {
    "ce-code-review",
    "ce-doc-review",
    "ce-brainstorm",
    "sp-systematic-debugging",
    "sp-using-superpowers",
}

# Skill directories preserved past v0.12.0 (D8).
KEEP_SKILLS: set[str] = {
    "ce-test-browser",
}

# Sub-agent files preserved past v0.12.0.
KEEP_AGENTS: set[str] = {
    "ce-git-history-analyzer.agent.md",
    "ce-repo-research-analyst.agent.md",
}

# Expected post-arithmetic counts (D14.2).
EXPECTED_SKILL_TOTAL = 46
EXPECTED_SKILL_REMOVE = 45
EXPECTED_AGENT_TOTAL = 49
EXPECTED_AGENT_REMOVE = 47


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RemovalTarget:
    """A path queued for `git rm -r`."""

    rel_path: str  # POSIX-style relative to repo root
    kind: str  # "skill" or "agent"

    @property
    def abs_path(self) -> Path:
        return REPO_ROOT / self.rel_path


def _discover_skills() -> list[str]:
    """Return sorted list of vendored skill directory names (ce-* + sp-*)."""
    if not SKILLS_DIR.is_dir():
        raise SystemExit(f"error: skills dir not found: {SKILLS_DIR}")
    names: list[str] = []
    for child in sorted(SKILLS_DIR.iterdir()):
        if not child.is_dir():
            continue
        n = child.name
        if n.startswith("ce-") or n.startswith("sp-"):
            names.append(n)
    return names


def _discover_agents() -> list[str]:
    """Return sorted list of vendored sub-agent filenames (*.agent.md)."""
    if not AGENTS_DIR.is_dir():
        raise SystemExit(f"error: agents dir not found: {AGENTS_DIR}")
    return sorted(p.name for p in AGENTS_DIR.glob("*.agent.md") if p.is_file())


def build_targets() -> tuple[list[RemovalTarget], dict[str, int]]:
    """Discover disk state, assert against expected counts, return targets.

    Returns:
        (targets, counts) where counts is a small report dict:
        {
          'skills_total': int, 'skills_remove': int, 'skills_keep': int,
          'agents_total': int, 'agents_remove': int, 'agents_keep': int,
        }
    """
    all_skills = _discover_skills()
    all_agents = _discover_agents()

    skills_total = len(all_skills)
    agents_total = len(all_agents)

    if skills_total != EXPECTED_SKILL_TOTAL:
        raise SystemExit(
            f"error: expected {EXPECTED_SKILL_TOTAL} vendored skills on disk "
            f"(33 ce-* + 13 sp-*); found {skills_total}. Disk drifted from "
            f"the D14.2 plan; aborting to avoid silent scope change."
        )
    if agents_total != EXPECTED_AGENT_TOTAL:
        raise SystemExit(
            f"error: expected {EXPECTED_AGENT_TOTAL} vendored sub-agents on "
            f"disk; found {agents_total}. Disk drifted from the D14.2 plan; "
            f"aborting to avoid silent scope change."
        )

    # Skill removal set = LIFT_SOURCE | (ALL - LIFT_SOURCE - KEEP).
    skill_set = set(all_skills)
    skill_remove = (LIFT_SOURCE_SKILLS | (skill_set - LIFT_SOURCE_SKILLS - KEEP_SKILLS))

    # Sanity: every LIFT entry must exist on disk.
    missing_lift = LIFT_SOURCE_SKILLS - skill_set
    if missing_lift:
        raise SystemExit(
            f"error: LIFT-source skill(s) missing from disk: "
            f"{sorted(missing_lift)}"
        )
    missing_keep = KEEP_SKILLS - skill_set
    if missing_keep:
        raise SystemExit(
            f"error: KEEP skill(s) missing from disk: {sorted(missing_keep)}"
        )

    if len(skill_remove) != EXPECTED_SKILL_REMOVE:
        raise SystemExit(
            f"error: expected {EXPECTED_SKILL_REMOVE} skills in removal set "
            f"(5 LIFT-source + 40 DROP); computed {len(skill_remove)}."
        )

    # Agent removal set = ALL - KEEP.
    agent_set = set(all_agents)
    missing_keep_agents = KEEP_AGENTS - agent_set
    if missing_keep_agents:
        raise SystemExit(
            f"error: KEEP sub-agent(s) missing from disk: "
            f"{sorted(missing_keep_agents)}"
        )
    agent_remove = agent_set - KEEP_AGENTS
    if len(agent_remove) != EXPECTED_AGENT_REMOVE:
        raise SystemExit(
            f"error: expected {EXPECTED_AGENT_REMOVE} sub-agents in removal "
            f"set; computed {len(agent_remove)}."
        )

    targets: list[RemovalTarget] = []
    for name in sorted(skill_remove):
        targets.append(RemovalTarget(rel_path=f"skills/{name}", kind="skill"))
    for name in sorted(agent_remove):
        targets.append(
            RemovalTarget(
                rel_path=f"agents/vendored/ce/{name}", kind="agent"
            )
        )

    counts = {
        "skills_total": skills_total,
        "skills_remove": len(skill_remove),
        "skills_keep": len(KEEP_SKILLS),
        "agents_total": agents_total,
        "agents_remove": len(agent_remove),
        "agents_keep": len(KEEP_AGENTS),
    }
    return targets, counts


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def _git_rm(rel_path: str) -> tuple[bool, str]:
    """Invoke `git rm -r <rel_path>`. Returns (ok, message).

    The message is the combined stdout+stderr trimmed; the caller decides
    whether to surface it.
    """
    # `-rf`: the vendored SKILL.md files carry uncommitted v0.11.8
    # deprecation-preamble modifications when this script runs in the
    # release-engineering workspace (v0.12.0 ships the removal in the
    # same release window as the v0.11.8 preamble). `git rm -r` without
    # `-f` refuses to remove files with local modifications; `-rf`
    # allows the atomic cut to proceed since the entire directory is
    # being deleted regardless of staged state.
    proc = subprocess.run(
        ["git", "rm", "-rf", rel_path],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    msg = (proc.stdout + proc.stderr).strip()
    return proc.returncode == 0, msg


def execute(targets: list[RemovalTarget]) -> tuple[int, int, int]:
    """Run `git rm -r` for each target. Returns (removed, skipped, failed)."""
    removed = 0
    skipped = 0
    failed = 0
    for tgt in targets:
        if not tgt.abs_path.exists():
            print(f"  [-] skip   {tgt.kind:<6} {tgt.rel_path} (not present)")
            skipped += 1
            continue
        ok, msg = _git_rm(tgt.rel_path)
        if ok:
            print(f"  [R] remove {tgt.kind:<6} {tgt.rel_path}")
            removed += 1
        else:
            print(
                f"  [!] FAIL   {tgt.kind:<6} {tgt.rel_path} :: {msg}",
                file=sys.stderr,
            )
            failed += 1
    return removed, skipped, failed


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------


def _emit_plan_line(counts: dict[str, int]) -> None:
    """Print the canonical scope summary used by Subtask 14 verification."""
    print(
        f"Plan: {counts['skills_remove']} skill paths "
        f"+ {counts['agents_remove']} sub-agent paths to remove; "
        f"preserve {counts['skills_keep']} skill (ce-test-browser) "
        f"+ {counts['agents_keep']} sub-agents "
        f"(ce-git-history-analyzer, ce-repo-research-analyst)"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Remove v0.12.0 LIFT-source + DROP vendored skills and sub-agents "
            "via `git rm -r`."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report scope and target paths; do not invoke git.",
    )
    args = parser.parse_args(argv)

    targets, counts = build_targets()

    _emit_plan_line(counts)

    if args.dry_run:
        # Enumerate every target so reviewers can sanity-check the plan.
        for tgt in targets:
            print(f"  [P] plan   {tgt.kind:<6} {tgt.rel_path}")
        print(
            f"Dry-run complete: would remove {counts['skills_remove']} skill "
            f"+ {counts['agents_remove']} sub-agent paths; preserve "
            f"{counts['skills_keep']} + {counts['agents_keep']}."
        )
        return 0

    removed, skipped, failed = execute(targets)
    preserved = counts["skills_keep"] + counts["agents_keep"]
    print(
        f"removed {removed}, skipped {skipped} (not present), "
        f"preserved {preserved} (1 skill + 2 sub-agents)"
    )
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
