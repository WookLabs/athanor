#!/usr/bin/env python3
"""
v0.10.0 vendor scaffold + content copy script.

Walks upstream CE v3.8.3 + superpowers v5.1.0 plugin caches, copies every
file under skills/ and agents/ into athanor's skills/vendored/ and
agents/vendored/ trees, and prepends the T2 provenance block to every
SKILL.md / *.agent.md file.

Outputs:
  - skills/vendored/ce/<skill>/...           (verbatim copies + provenance on SKILL.md)
  - skills/vendored/superpowers/<skill>/...  (same)
  - agents/vendored/ce/*.agent.md            (verbatim + provenance)
  - docs/plans/2026-05-19-003-feat-v0.10.0-absorb-ce-superpowers-plan-INVENTORY.md
  - .athanor/scratch/v010_manifest_entries.json (raw entries to merge into marketplace.json)

This script is NOT committed (lives under scripts/oneshot/, gitignored).
Only its outputs are committed.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

REPO = Path("/home/wook/work/06_athanor").resolve()
CE_BASE = Path(
    "/home/wook/.claude/plugins/cache/compound-engineering-plugin/compound-engineering/3.8.3"
).resolve()
SP_BASE = Path(
    "/home/wook/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0"
).resolve()

CE_VERSION = "3.8.3"
SP_VERSION = "5.1.0"
CE_COPYRIGHT = "Copyright (c) 2025 Kieran Klaassen / Every Inc"
SP_COPYRIGHT = "Copyright (c) 2025 Jesse Vincent"
CE_UPSTREAM_URL = "https://github.com/EveryInc/compound-engineering-plugin"
SP_UPSTREAM_URL = "https://github.com/obra/superpowers"

# D2 namespace collision policy: athanor-native skills keep the unprefixed
# slot; CE-vendored variants get /athanor:ce-<name>. Superpowers always
# /athanor:sp-<name>.
ATHANOR_NATIVE = {"plan", "work", "debug", "setup", "discuss", "analyze", "review",
                  "deep-plan", "lite-plan", "scope-drift"}


def make_provenance(source: str, upstream_rel: str, version: str, copyright_line: str,
                    url: str, modifications: str | None = None) -> str:
    """Build a T2 provenance HTML comment block."""
    if modifications is None:
        modifications = "none — verbatim copy under T2 vendoring pattern; provenance block inserted after frontmatter only"
    return f"""<!-- Provenance:
  upstream: {source}@{version} {upstream_rel}
  source-commit: vendored at athanor v0.10.0 release time from {source}@{version}
  upstream-url: {url}
  license: MIT ({copyright_line})
  modifications: {modifications}
  t0-t1-disproof:
    Why not T0/T1? {source} is shipped as a Claude Code plugin (T3 marketplace
    listing). T0 (install companion) is unavailable for per-skill reference files.
    T1 (require dependency) is reserved pending Claude Code plugin-spec `requires`
    field support. T2 (vendor) is the only feasible tier today.
-->

"""


def is_markdown_file(p: Path) -> bool:
    return p.suffix.lower() in {".md", ".markdown"}


def insert_provenance_after_frontmatter(content: str, header: str) -> str:
    """Insert provenance block. If content begins with YAML frontmatter
    (`---\\n ... \\n---\\n`), insert the block immediately after the closing
    `---`. Otherwise prepend to the top of the file.

    Claude Code skill discovery REQUIRES the YAML frontmatter at line 1, so
    we cannot prepend the provenance block above frontmatter. This mirrors
    the existing athanor vendoring precedent at
    `skills/verification-before-completion/SKILL.md`.
    """
    lines = content.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\n") != "---":
        # No frontmatter — safe to prepend
        return header + content
    # Find the closing --- (second occurrence of "---" as a complete line)
    close_idx = None
    for i in range(1, len(lines)):
        if lines[i].rstrip("\n") == "---":
            close_idx = i
            break
    if close_idx is None:
        # Malformed frontmatter — prepend defensively
        return header + content
    # Insert after the closing --- and any trailing newline that follows
    insert_at = close_idx + 1
    return "".join(lines[:insert_at]) + "\n" + header + "".join(lines[insert_at:])


def rewrite_skill_name_in_frontmatter(content: str, new_name: str) -> tuple[str, bool]:
    """If content has YAML frontmatter with `name: <old>`, rewrite to `name: <new>`.

    Returns (new_content, did_change).
    """
    lines = content.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\n") != "---":
        return content, False
    close_idx = None
    for i in range(1, len(lines)):
        if lines[i].rstrip("\n") == "---":
            close_idx = i
            break
    if close_idx is None:
        return content, False
    did_change = False
    for i in range(1, close_idx):
        stripped = lines[i].lstrip()
        if stripped.startswith("name:"):
            indent = lines[i][: len(lines[i]) - len(stripped)]
            lines[i] = f"{indent}name: {new_name}\n"
            did_change = True
            break
    return "".join(lines), did_change


def vendor_one_tree(src_root: Path, dst_root: Path, source: str, version: str,
                    copyright_line: str, url: str,
                    skill_rename: tuple[str, str] | None = None) -> list[dict]:
    """Recursively copy src_root → dst_root, adding provenance to markdown files.

    skill_rename: if (old_name, new_name) is provided, rewrites the YAML
    frontmatter `name:` field in any SKILL.md found at the root of dst_root.
    This is required when the vendor target directory is renamed (e.g.,
    `brainstorming` → `sp-brainstorming`) — Claude Code expects the
    frontmatter `name:` to match the directory.
    """
    rows: list[dict] = []
    if not src_root.exists():
        print(f"WARN: source missing {src_root}", file=sys.stderr)
        return rows
    for src_file in src_root.rglob("*"):
        if src_file.is_dir():
            continue
        rel = src_file.relative_to(src_root)
        if any(part.startswith(".") or part == "__pycache__" for part in rel.parts):
            continue
        dst_file = dst_root / rel
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        if is_markdown_file(src_file):
            content = src_file.read_text(encoding="utf-8", errors="replace")
            modifications = None
            # Rewrite SKILL.md frontmatter name if this is the root SKILL.md and
            # a rename is requested
            if skill_rename and src_file.name == "SKILL.md" and rel.parent == Path("."):
                old, new = skill_rename
                content, did = rewrite_skill_name_in_frontmatter(content, new)
                if did:
                    modifications = (f"frontmatter `name:` rewritten `{old}` → `{new}` "
                                     f"to match athanor namespace-prefixed directory "
                                     f"(`skills/{new}/`). Body content otherwise verbatim. "
                                     f"Provenance block inserted after frontmatter.")
            header = make_provenance(source, str(rel), version, copyright_line, url,
                                     modifications=modifications)
            new_content = insert_provenance_after_frontmatter(content, header)
            dst_file.write_text(new_content, encoding="utf-8")
        else:
            shutil.copy2(src_file, dst_file)
        rows.append({
            "source": source,
            "upstream_path": str(rel),
            "target_path": str(dst_file.relative_to(REPO)),
            "is_markdown": is_markdown_file(src_file),
            "size_bytes": dst_file.stat().st_size,
        })
    return rows


def build_skill_manifest_entries(rows: list[dict]) -> list[dict]:
    """Derive skill manifest entries from flat-layout vendor outputs.

    Pattern (flat layout): skills/<ce-name|sp-name>/SKILL.md
    """
    entries: list[dict] = []
    seen_skills: set[str] = set()
    for row in rows:
        target = Path(row["target_path"])
        parts = target.parts
        if len(parts) < 3:
            continue
        if parts[0] == "skills" and target.name == "SKILL.md":
            skill_dir = parts[1]  # e.g., "ce-plan", "sp-brainstorming"
            if skill_dir in seen_skills:
                continue
            seen_skills.add(skill_dir)
            if skill_dir.startswith("ce-"):
                source = "ce"
                version = CE_VERSION
            elif skill_dir.startswith("sp-"):
                source = "superpowers"
                version = SP_VERSION
            else:
                continue  # athanor-native; not a vendor entry
            name = f"athanor:{skill_dir}"
            entries.append({
                "name": name,
                "source": source,
                "skill_dir": skill_dir,
                "path": str(target.parent),
                "description": f"[vendored from {source}@{version}] {skill_dir}",
            })
    return entries


def write_inventory(rows: list[dict], skill_entries: list[dict]) -> None:
    """Write the U1 inventory markdown file."""
    inv_path = REPO / "docs" / "plans" / "2026-05-19-003-feat-v0.10.0-absorb-ce-superpowers-plan-INVENTORY.md"
    ce_skills = [e for e in skill_entries if e["source"] == "ce"]
    sp_skills = [e for e in skill_entries if e["source"] == "superpowers"]
    ce_agents = [r for r in rows if r["target_path"].startswith("agents/vendored/ce/")]
    # Layout note: flat skills/ce-<n>/ + skills/sp-<n>/ for Claude Code skill auto-discovery
    # (which requires SKILL.md at depth 1 under skills/). Agents stay nested at
    # agents/vendored/ce/ because they're not user-invocable commands.
    lines = [
        "---",
        "title: 'v0.10.0 vendor inventory (U1 output)'",
        "date: 2026-05-19",
        "kind: appendix",
        "parent_plan: docs/plans/2026-05-19-003-feat-v0.10.0-absorb-ce-superpowers-plan.md",
        "---",
        "",
        "# v0.10.0 vendor inventory",
        "",
        "Generated by `scripts/oneshot/v010_vendor.py` at athanor v0.10.0 release time.",
        f"Total files vendored: **{len(rows)}** ({len(ce_skills)} CE skills, {len(sp_skills)} superpowers skills, {len(ce_agents)} CE sub-agent files).",
        "",
        "## CE skills (target namespace `/athanor:ce-*`)",
        "",
        "| Skill | Target path | Athanor command |",
        "|---|---|---|",
    ]
    for e in sorted(ce_skills, key=lambda x: x["skill_dir"]):
        lines.append(f"| {e['skill_dir']} | `{e['path']}` | `/{e['name']}` |")
    lines += [
        "",
        "## Superpowers skills (target namespace `/athanor:sp-*`)",
        "",
        "| Skill | Target path | Athanor command |",
        "|---|---|---|",
    ]
    for e in sorted(sp_skills, key=lambda x: x["skill_dir"]):
        lines.append(f"| {e['skill_dir']} | `{e['path']}` | `/{e['name']}` |")
    lines += [
        "",
        "## CE sub-agents",
        "",
        "| Agent file | Target path |",
        "|---|---|",
    ]
    for r in sorted(ce_agents, key=lambda x: x["target_path"]):
        if r["target_path"].endswith(".agent.md"):
            lines.append(f"| {Path(r['target_path']).name} | `{r['target_path']}` |")
    lines += [
        "",
        "## Naming/collision notes (D2 policy)",
        "",
        "- Athanor-native skills keep the unprefixed `/athanor:<n>` slot: "
        + ", ".join(sorted(ATHANOR_NATIVE)) + ".",
        "- CE vendored variants: `/athanor:ce-<name>` (CE upstream names already carry `ce-` prefix; preserved verbatim).",
        "- Superpowers vendored: `/athanor:sp-<name>` (`sp-` prefix added at namespace registration; upstream skills are unprefixed).",
        "- Special case: superpowers `verification-before-completion` is NOT re-vendored — athanor already has it under `skills/verification-before-completion/` from v0.7.8. The newer superpowers v5.1.0 variant is intentionally skipped here.",
        "",
        "## License and provenance summary",
        "",
        "- CE: MIT, " + CE_COPYRIGHT + " — " + CE_UPSTREAM_URL,
        "- superpowers: MIT, " + SP_COPYRIGHT + " — " + SP_UPSTREAM_URL,
        "- Every vendored markdown file carries the T2 provenance block (see `skills/vendored/ce/ce-plan/SKILL.md` first 14 lines for canonical shape).",
        "",
    ]
    inv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Inventory written: {inv_path.relative_to(REPO)}")


def write_manifest_scratch(skill_entries: list[dict]) -> None:
    """Write the raw manifest entries to .athanor/scratch/ so the user can
    merge them into marketplace.json manually."""
    scratch = REPO / ".athanor" / "scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    out = scratch / "v010_manifest_entries.json"
    out.write_text(json.dumps(skill_entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Manifest scratch: {out.relative_to(REPO)}")


def main() -> int:
    print(f"REPO: {REPO}")
    print(f"CE source: {CE_BASE} (v{CE_VERSION})")
    print(f"SP source: {SP_BASE} (v{SP_VERSION})")

    # Sanity
    if not CE_BASE.exists():
        print(f"FATAL: CE source missing: {CE_BASE}", file=sys.stderr)
        return 1
    if not SP_BASE.exists():
        print(f"FATAL: SP source missing: {SP_BASE}", file=sys.stderr)
        return 1

    rows: list[dict] = []

    # 1. CE skills → skills/ce-<name>/ (flat, depth-1 for Claude Code auto-discovery)
    # CE upstream skills are already prefixed with `ce-` so we keep their directory
    # names as-is (one exception: `lfg` → `ce-lfg` for namespace clarity).
    print("\n=== Vendoring CE skills (flat layout) ===")
    ce_skills_root = CE_BASE / "skills"
    for skill_dir in sorted(ce_skills_root.iterdir()):
        if not skill_dir.is_dir():
            continue
        if skill_dir.name.startswith("."):
            continue
        original_name = skill_dir.name
        target_name = original_name
        rename = None
        if not target_name.startswith("ce-"):
            target_name = f"ce-{target_name}"
            rename = (original_name, target_name)
        rows += vendor_one_tree(
            skill_dir,
            REPO / "skills" / target_name,
            source="ce",
            version=CE_VERSION,
            copyright_line=CE_COPYRIGHT,
            url=CE_UPSTREAM_URL,
            skill_rename=rename,
        )

    # 2. CE agents → agents/vendored/ce/ (agents are read by skills, not user-invocable;
    # nesting is fine here).
    print("=== Vendoring CE agents ===")
    rows += vendor_one_tree(
        CE_BASE / "agents",
        REPO / "agents" / "vendored" / "ce",
        source="ce",
        version=CE_VERSION,
        copyright_line=CE_COPYRIGHT,
        url=CE_UPSTREAM_URL,
    )

    # 3. Superpowers skills → skills/sp-<name>/ (flat layout, `sp-` prefix added).
    # SKIP verification-before-completion (already at skills/verification-before-completion/)
    print("=== Vendoring superpowers skills (flat layout) ===")
    sp_skills_root = SP_BASE / "skills"
    for skill_dir in sorted(sp_skills_root.iterdir()):
        if not skill_dir.is_dir():
            continue
        if skill_dir.name == "verification-before-completion":
            print(f"  SKIP {skill_dir.name} (already vendored at athanor v0.7.8)")
            continue
        original_name = skill_dir.name
        target_name = f"sp-{original_name}"
        rows += vendor_one_tree(
            skill_dir,
            REPO / "skills" / target_name,
            source="superpowers",
            version=SP_VERSION,
            copyright_line=SP_COPYRIGHT,
            url=SP_UPSTREAM_URL,
            skill_rename=(original_name, target_name),
        )

    print(f"\nTotal files vendored: {len(rows)}")

    # Build manifest entries
    skill_entries = build_skill_manifest_entries(rows)
    print(f"Skill entries derived: {len(skill_entries)}")

    # Write artifacts
    write_inventory(rows, skill_entries)
    write_manifest_scratch(skill_entries)

    print("\nDONE.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
