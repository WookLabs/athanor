#!/usr/bin/env python3
"""
v011_8_deprecation_preamble.py — inject the v0.11.8 deprecation sentinel +
preamble into all LIFT- and DROP-class vendored skill SKILL.md files.

Scope (per docs/plans/2026-05-22-001-feat-v0.12.0-concept-kernel-cutover-plan-b.md
D14.1/D14.2 + Subtask 3 disk-truth inventory):

  Disk truth: 33 ce-* + 13 sp-* = 46 vendored SKILL.md files.
  Triage classes:
    LIFT  (5)  → migration target stated explicitly in preamble
    DROP  (40) → "no athanor-native migration" preamble
    KEEP  (1)  → ce-test-browser is the only KEEP; this script skips it
  Total deprecation-eligible: 5 + 40 = 45.

The script is idempotent. Running it twice produces zero additional diff.
Idempotency check: a file already containing the sentinel
    <!-- athanor:deprecated v=1 since=0.11.8 removal=0.12.0 -->
is treated as already-deprecated and skipped.

Insertion point:
  AFTER the closing YAML `---` frontmatter delimiter, AND
  AFTER the closing `-->` of the T2 provenance HTML comment block.
The T2 provenance block's `modifications:` line is updated to append
    v0.11.8 deprecation preamble added; body otherwise verbatim
(preserving prior entries — `none` becomes the new entry; an existing
modifications string is suffixed with `; v0.11.8 deprecation preamble
added; body otherwise verbatim`).

CLI:
  python3 scripts/v011_8_deprecation_preamble.py            # writes files
  python3 scripts/v011_8_deprecation_preamble.py --dry-run  # reports only

Exit codes:
  0  — success (planned set processed; idempotent skips counted separately)
  1  — unexpected error (file missing, T2 block malformed, etc.)

Voice constraints (D7 forbidden phrases): the generated preamble text does
NOT use "translated", "interpreted", "we discovered", or "natural
maturation". Migration text is direct and factual.

Stdlib only, Python 3.10+. UTF-8 throughout.

Plan reference:
  docs/plans/2026-05-22-001-feat-v0.12.0-concept-kernel-cutover-plan-b.md
  §Subtask 4 (Phase 2 — Deprecation preamble injection).
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"

SENTINEL = "<!-- athanor:deprecated v=1 since=0.11.8 removal=0.12.0 -->"
MODIFICATIONS_NOTE = (
    "v0.11.8 deprecation preamble added; body otherwise verbatim"
)


# ---------------------------------------------------------------------------
# Triage tables — D14.2 corrected counts. Hardcoded so disk drift cannot
# change scope silently. Subtask 5 regression tests pin this set.
# ---------------------------------------------------------------------------

LIFT_TARGETS: dict[str, dict[str, str]] = {
    # skill_dir : {rationale, migration}
    "ce-code-review": {
        "rationale": "Multi-lens review semantics already covered by athanor-native /athanor:review.",
        "migration": "Use /athanor:review (the review.personas[] mechanism subsumes ce-code-review's lens pattern).",
    },
    "ce-doc-review": {
        "rationale": "Documentation review is one lens of athanor-native /athanor:review.",
        "migration": "Use /athanor:review (the lens system covers the docs lens).",
    },
    "ce-brainstorm": {
        "rationale": "Brainstorm dialog overlaps with athanor-native /athanor:discuss clarify mode.",
        "migration": "Use /athanor:discuss in clarify mode (R/A/F/AE-IDs handle the same intent-capture surface).",
    },
    "sp-systematic-debugging": {
        "rationale": "Iron Law + Four Phases debugging discipline subsumed by athanor-native /athanor:debug.",
        "migration": "Use /athanor:debug (the Iron Law + Four Phases subsection in the skill body carries forward).",
    },
    "sp-using-superpowers": {
        "rationale": "Skill-discovery preamble is replaced by athanor's own preamble + CLAUDE.md Defense Mechanisms.",
        "migration": "See athanor preamble and CLAUDE.md §Defense Mechanisms for the athanor-native equivalent.",
    },
}

KEEP_SKILLS: set[str] = {
    # KEEP per D8 — preamble NOT injected.
    "ce-test-browser",
}

DROP_RATIONALE = (
    "Out of athanor's identity scope; removed in v0.12.0 to keep the surface "
    "focused on the three athanor identities (cross-model planning, "
    "Spec-then-TDD execution, multi-lens review)."
)
DROP_MIGRATION = (
    "No athanor-native migration — install the upstream compound-engineering "
    "or superpowers plugin directly if you need this skill."
)


# ---------------------------------------------------------------------------
# Planned-set discovery
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Target:
    skill_dir: str  # e.g. "ce-plan"
    triage: str  # "LIFT" or "DROP"
    rationale: str
    migration: str

    @property
    def path(self) -> Path:
        return SKILLS_DIR / self.skill_dir / "SKILL.md"


def discover_targets() -> list[Target]:
    """Walk skills/ and produce the deprecation-eligible target list.

    Disk truth (Subtask 3): 33 ce-* + 13 sp-* = 46 vendored skills.
    Subtract KEEP (1) → 45 deprecation-eligible. Subtract LIFT_TARGETS (5)
    → 40 DROP-class. Returns LIFT entries first, then DROP entries
    sorted by directory name for stable output.
    """
    if not SKILLS_DIR.is_dir():
        raise SystemExit(f"error: skills dir not found: {SKILLS_DIR}")

    vendored_dirs: list[str] = []
    for child in sorted(SKILLS_DIR.iterdir()):
        if not child.is_dir():
            continue
        name = child.name
        if name.startswith("ce-") or name.startswith("sp-"):
            vendored_dirs.append(name)

    targets: list[Target] = []

    # LIFT entries first.
    for name in sorted(LIFT_TARGETS):
        if name not in vendored_dirs:
            raise SystemExit(
                f"error: LIFT skill '{name}' missing from skills/ on disk"
            )
        entry = LIFT_TARGETS[name]
        targets.append(
            Target(
                skill_dir=name,
                triage="LIFT",
                rationale=entry["rationale"],
                migration=entry["migration"],
            )
        )

    # DROP entries (sorted, deterministic).
    for name in vendored_dirs:
        if name in LIFT_TARGETS or name in KEEP_SKILLS:
            continue
        targets.append(
            Target(
                skill_dir=name,
                triage="DROP",
                rationale=DROP_RATIONALE,
                migration=DROP_MIGRATION,
            )
        )

    return targets


# ---------------------------------------------------------------------------
# Preamble rendering + insertion
# ---------------------------------------------------------------------------


def render_preamble(target: Target) -> str:
    """Return the 4-line preamble block (sentinel + 3 body lines)."""
    return (
        f"{SENTINEL}\n"
        f"⚠ DEPRECATION: This skill is removed in athanor v0.12.0.\n"
        f"Rationale: {target.rationale}\n"
        f"Migration: {target.migration}\n"
    )


# YAML frontmatter: line 1 is `---`, then content, then another `---`.
_YAML_DELIM = "---"

# T2 provenance block: HTML comment opening `<!-- Provenance:` and closing `-->`.
_T2_OPEN_RE = re.compile(r"^<!--\s*Provenance:\s*$")
_T2_CLOSE_RE = re.compile(r"^-->\s*$")


def _find_insertion_index(lines: list[str], path: Path) -> int:
    """Return the line index AFTER the YAML frontmatter and T2 block.

    The returned index points to the first line at which the preamble will
    be inserted. If the file has no T2 block (defense-in-depth — should be
    impossible per disk inspection but handled), insertion happens right
    after the YAML close.

    Raises SystemExit on malformed structure.
    """
    if not lines or lines[0].rstrip("\n") != _YAML_DELIM:
        raise SystemExit(f"error: {path} does not start with YAML frontmatter")

    # Find YAML close.
    yaml_close_idx: int | None = None
    for i in range(1, len(lines)):
        if lines[i].rstrip("\n") == _YAML_DELIM:
            yaml_close_idx = i
            break
    if yaml_close_idx is None:
        raise SystemExit(f"error: {path} YAML frontmatter has no closing '---'")

    # Look for T2 block opening after the YAML close. Skip blank lines.
    scan = yaml_close_idx + 1
    while scan < len(lines) and lines[scan].strip() == "":
        scan += 1
    if scan >= len(lines) or not _T2_OPEN_RE.match(lines[scan].rstrip("\n")):
        # No T2 block — insert right after the YAML close (and any blanks).
        # Return position after the YAML close line (preamble goes on its own line block).
        return yaml_close_idx + 1

    # Find T2 block close.
    t2_close_idx: int | None = None
    for j in range(scan + 1, len(lines)):
        if _T2_CLOSE_RE.match(lines[j].rstrip("\n")):
            t2_close_idx = j
            break
    if t2_close_idx is None:
        raise SystemExit(
            f"error: {path} T2 provenance block opens but never closes"
        )

    return t2_close_idx + 1


def _update_modifications_line(lines: list[str]) -> None:
    """Update the T2 `modifications:` line in place.

    Appends MODIFICATIONS_NOTE. If the existing value is literally `none`
    (verbatim per ce-plan etc.), it is REPLACED by MODIFICATIONS_NOTE.
    Otherwise the note is suffixed with `; `.

    If no `modifications:` line exists, the file is left unchanged (defense-
    in-depth: every disk-inspected SKILL.md has the field, so absence is a
    structural issue caller should notice via diff).
    """
    pattern = re.compile(r"^(\s*modifications:\s*)(.*)$")
    for idx, line in enumerate(lines):
        m = pattern.match(line.rstrip("\n"))
        if not m:
            continue
        prefix, value = m.group(1), m.group(2).strip()
        if MODIFICATIONS_NOTE in value:
            # Idempotent: already updated.
            return
        if value == "" or value.lower() == "none":
            new_value = MODIFICATIONS_NOTE
        else:
            # Append with separator; trim any trailing period to keep parity
            # with existing style (ce/sp upstream entries use no trailing period).
            base = value.rstrip(".")
            new_value = f"{base}; {MODIFICATIONS_NOTE}"
        lines[idx] = f"{prefix}{new_value}\n"
        return


def inject_preamble(target: Target, dry_run: bool) -> str:
    """Inject (or report) the deprecation preamble for a single file.

    Returns a one-of:
      "modified" — preamble inserted and modifications line updated
      "skipped"  — sentinel already present (idempotent no-op)
    """
    path = target.path
    if not path.is_file():
        raise SystemExit(f"error: SKILL.md missing for target {target.skill_dir}: {path}")

    text = path.read_text(encoding="utf-8")
    if SENTINEL in text:
        return "skipped"

    lines = text.splitlines(keepends=True)
    insert_idx = _find_insertion_index(lines, path)

    # Compose the preamble. Add a leading blank line for visual separation
    # from the T2 block, and a trailing blank line so the next existing
    # content (typically blank or `# Title`) starts cleanly.
    preamble_block = "\n" + render_preamble(target) + "\n"

    new_lines = lines[:insert_idx] + [preamble_block] + lines[insert_idx:]
    _update_modifications_line(new_lines)
    new_text = "".join(new_lines)

    if not dry_run:
        path.write_text(new_text, encoding="utf-8")
    return "modified"


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------


def _emit_plan_line() -> None:
    """Print the constant plan summary required by Subtask 4 verification."""
    print(
        "Plan: 45 files to deprecate (5 LIFT + 40 DROP); "
        "1 KEEP skipped (ce-test-browser)"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inject v0.11.8 deprecation preamble into LIFT+DROP vendored skills."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report which files would be modified; do not write.",
    )
    args = parser.parse_args(argv)

    targets = discover_targets()
    if len(targets) != 45:
        # Defense-in-depth: D14.2 nails the count to 45. If disk drift
        # changes this, callers should know immediately rather than silently
        # ship a different scope.
        print(
            f"error: expected 45 deprecation targets (5 LIFT + 40 DROP); "
            f"found {len(targets)}",
            file=sys.stderr,
        )
        return 1

    _emit_plan_line()

    modified = 0
    skipped = 0
    per_file: list[tuple[str, str, str]] = []  # (status, triage, skill_dir)
    for tgt in targets:
        status = inject_preamble(tgt, dry_run=args.dry_run)
        if status == "modified":
            modified += 1
        else:
            skipped += 1
        per_file.append((status, tgt.triage, tgt.skill_dir))

    verb = "would modify" if args.dry_run else "modified"
    print(f"{verb}: {modified} files; skipped (already deprecated): {skipped}")

    # Per-file lines so dry-run is reviewable.
    for status, triage, name in per_file:
        marker = "M" if status == "modified" else "-"
        print(f"  [{marker}] {triage:<4}  {name}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
