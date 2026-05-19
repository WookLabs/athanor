#!/usr/bin/env python3
"""
check_vendor_drift.py — diff vendored skill trees against their upstream
plugin caches.

Walks every `skills/ce-*/` and `skills/sp-*/` directory, locates the
matching upstream cache directory under `~/.claude/plugins/cache/`, and
runs `diff -r`. Reports per-skill drift status.

Exit codes:
  0  — no drift detected across all vendored skills
  1  — drift detected (one or more skills differ from upstream)
  2  — upstream cache unreachable (no matching plugin cache found)

The script does NOT install or update upstream plugins. If a plugin cache
is missing, the script exits 2 with a clear message; the operator must
install or update the upstream plugin before re-running.

Drift detection skips the provenance block (the first HTML comment block
whose body starts with "Provenance:") since athanor adds that block during
vendoring and it never matches upstream by design.

Modes:
  default                 walk every vendored skill, run diff -r, print
                          per-skill verdict + final summary
  --cache-root PATH       override the plugin-cache root (default:
                          ~/.claude/plugins/cache/)
  --skill NAME            limit the diff to a single vendored skill
                          directory (e.g., `--skill ce-plan`)
  --ci                    suppress per-skill output; print only the final
                          one-line summary + exit code. Useful in CI to
                          surface drift as a warning without bricking the
                          build (caller decides whether to gate on the
                          exit code).

Stdlib only, Python 3.10+. All file I/O uses encoding='utf-8'.

Plan reference:
  docs/plans/2026-05-19-004-feat-v0.10.1-vendor-hygiene-plan.md §U1.
  v0.10.0 §Deferred A1.
"""
from __future__ import annotations

import argparse
import difflib
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
DEFAULT_CACHE_ROOT = Path.home() / ".claude" / "plugins" / "cache"

# Plugin-cache layout: each upstream has its own subdirectory with a single
# version directory inside (e.g., compound-engineering-plugin/compound-engineering/3.8.3).
# We probe known upstreams here. To add a new upstream, append a row.
UPSTREAM_REGISTRY = [
    {
        "name": "compound-engineering",
        "skill_prefix": "ce-",
        "cache_candidates": [
            "compound-engineering-plugin/compound-engineering",
        ],
        # CE upstream directories already carry `ce-` prefix
        # (e.g., upstream `skills/ce-plan/` ↔ athanor `skills/ce-plan/`).
        # Default: athanor directory name == upstream directory name.
        "strip_prefix_for_upstream": False,
        # Renames override the default. v0.10.0 renamed upstream `lfg` to
        # athanor `ce-lfg` for namespace clarity.
        "renames": {
            "ce-lfg": "lfg",
        },
    },
    {
        "name": "superpowers",
        "skill_prefix": "sp-",
        "cache_candidates": [
            "claude-plugins-official/superpowers",
        ],
        # Superpowers upstream is unprefixed (athanor adds `sp-` at vendor time).
        # Default: strip `sp-` to recover upstream directory name.
        "strip_prefix_for_upstream": True,
        "renames": {},
    },
]


def _find_cache_dir(cache_root: Path, candidate_relpath: str) -> Path | None:
    """Resolve a plugin's cache directory.

    Plugin caches use `<cache-root>/<candidate-relpath>/<version>/`.
    We probe for the cache root + a version subdirectory.
    """
    base = cache_root / candidate_relpath
    if not base.is_dir():
        return None
    # Find the version subdirectory (we accept whatever version is cached;
    # drift check is against the *currently installed* upstream, not a pinned one).
    versions = sorted([p for p in base.iterdir() if p.is_dir()])
    if not versions:
        return None
    return versions[-1]  # latest


def _strip_provenance_block(text: str) -> str:
    """Remove the first <!-- Provenance: ... --> block from text.

    Does NOT try to be clever about surrounding whitespace; downstream
    normalization (_collapse_blank_line_runs) handles that.
    """
    start = text.find("<!-- Provenance:")
    if start < 0:
        return text
    end = text.find("-->", start)
    if end < 0:
        return text
    end += len("-->")
    return text[:start] + text[end:]


def _collapse_blank_line_runs(text: str) -> str:
    """Collapse runs of 2+ consecutive blank lines into a single blank line,
    and strip leading + trailing blank lines.

    The vendor script's provenance-insertion + provenance-stripping leaves
    a slightly different blank-line count between athanor and upstream
    even though the content is byte-identical otherwise (different leading
    blanks for files without frontmatter; different trailing blanks for
    files with frontmatter). Normalize both sides to compare meaningful
    body content.
    """
    # Strip leading + trailing blank lines first
    stripped = text.strip("\n")
    out_lines: list[str] = []
    blank_run = 0
    for line in stripped.splitlines(keepends=True):
        if line.strip() == "":
            blank_run += 1
            if blank_run == 1:
                out_lines.append(line)
        else:
            blank_run = 0
            out_lines.append(line)
    return "".join(out_lines)


def _strip_frontmatter_name_rewrite(athanor_text: str, upstream_text: str) -> tuple[str, str]:
    """Some vendored SKILL.md files have their YAML `name:` field rewritten
    to match the athanor namespace-prefixed directory (e.g., upstream
    `name: brainstorming` → athanor `name: sp-brainstorming`). For drift
    purposes, normalize both sides to compare the rest of the frontmatter
    and body.

    Returns (normalized_athanor, normalized_upstream).
    """
    def _normalize(text: str) -> str:
        lines = text.splitlines(keepends=True)
        if not lines or lines[0].rstrip("\n") != "---":
            return text
        for i in range(1, len(lines)):
            if lines[i].rstrip("\n") == "---":
                break
            stripped = lines[i].lstrip()
            if stripped.startswith("name:"):
                indent = lines[i][: len(lines[i]) - len(stripped)]
                lines[i] = f"{indent}name: <NAME-REDACTED>\n"
                break
        return "".join(lines)
    return _normalize(athanor_text), _normalize(upstream_text)


def _diff_skill(athanor_dir: Path, upstream_dir: Path) -> list[str]:
    """Return a list of human-readable diff lines for one skill directory,
    or empty list if no meaningful drift detected.

    Skips:
      - the provenance block at the top of each vendored markdown
      - any frontmatter `name:` field rewrite recorded in the provenance
        block's modifications field
    """
    drift_lines: list[str] = []
    # Iterate every file under athanor_dir
    for athanor_file in sorted(athanor_dir.rglob("*")):
        if athanor_file.is_dir():
            continue
        rel = athanor_file.relative_to(athanor_dir)
        upstream_file = upstream_dir / rel
        if not upstream_file.exists():
            drift_lines.append(f"  + {rel} (only in athanor; upstream lacks it)")
            continue
        a_text = athanor_file.read_text(encoding="utf-8", errors="replace")
        u_text = upstream_file.read_text(encoding="utf-8", errors="replace")
        if athanor_file.suffix.lower() in {".md", ".markdown"}:
            a_text = _strip_provenance_block(a_text)
            a_text, u_text = _strip_frontmatter_name_rewrite(a_text, u_text)
        # Final normalization: collapse blank-line runs on both sides so
        # the provenance-strip side-effects don't show as drift.
        a_norm = _collapse_blank_line_runs(a_text)
        u_norm = _collapse_blank_line_runs(u_text)
        if a_norm == u_norm:
            continue
        a_text, u_text = a_norm, u_norm
        # Body differs. Surface a short unified diff (max 10 lines).
        diff = list(difflib.unified_diff(
            u_text.splitlines(keepends=True),
            a_text.splitlines(keepends=True),
            fromfile=f"upstream/{rel}",
            tofile=f"athanor/{rel}",
            n=2,
        ))[:12]
        drift_lines.append(f"  ~ {rel}: body diff ({len(diff)} lines)")
        for line in diff:
            drift_lines.append(f"      {line.rstrip()}")
    # Also flag files in upstream but missing from athanor
    for upstream_file in sorted(upstream_dir.rglob("*")):
        if upstream_file.is_dir():
            continue
        rel = upstream_file.relative_to(upstream_dir)
        athanor_file = athanor_dir / rel
        if not athanor_file.exists():
            drift_lines.append(f"  - {rel} (only in upstream; athanor lacks it)")
    return drift_lines


def _resolve_upstream_name(skill_dir_name: str, registry_entry: dict) -> str:
    """Map an athanor skill directory name to its upstream directory name."""
    renames = registry_entry.get("renames", {})
    if skill_dir_name in renames:
        return renames[skill_dir_name]
    if registry_entry.get("strip_prefix_for_upstream", False):
        prefix = registry_entry["skill_prefix"]
        if skill_dir_name.startswith(prefix):
            return skill_dir_name[len(prefix):]
    return skill_dir_name


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cache-root", type=Path, default=DEFAULT_CACHE_ROOT)
    parser.add_argument("--skill", help="Limit to a single vendored skill directory")
    parser.add_argument("--ci", action="store_true",
                        help="Suppress per-skill output; print one-line summary only")
    args = parser.parse_args()

    if not args.cache_root.is_dir():
        print(f"FATAL: plugin cache root not found: {args.cache_root}",
              file=sys.stderr)
        print("Install the upstream plugins (compound-engineering, superpowers) "
              "or pass --cache-root <path> to point at a different cache.",
              file=sys.stderr)
        return 2

    # Resolve cache directories for each upstream
    cache_for_upstream: dict[str, Path | None] = {}
    for entry in UPSTREAM_REGISTRY:
        resolved = None
        for candidate in entry["cache_candidates"]:
            resolved = _find_cache_dir(args.cache_root, candidate)
            if resolved:
                break
        cache_for_upstream[entry["name"]] = resolved
        if resolved is None:
            print(f"WARN: upstream {entry['name']} cache not found "
                  f"under {args.cache_root}", file=sys.stderr)

    # Walk vendored skill directories
    drifted: list[tuple[str, list[str]]] = []
    unchanged: list[str] = []
    unreachable: list[str] = []
    total = 0
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        if args.skill and skill_dir.name != args.skill:
            continue
        # Identify which upstream this belongs to
        registry_entry = None
        for entry in UPSTREAM_REGISTRY:
            if skill_dir.name.startswith(entry["skill_prefix"]):
                registry_entry = entry
                break
        if registry_entry is None:
            continue  # athanor-native skill, skip
        total += 1
        upstream_cache = cache_for_upstream[registry_entry["name"]]
        if upstream_cache is None:
            unreachable.append(skill_dir.name)
            continue
        # Locate the upstream skill directory inside the cache
        upstream_name = _resolve_upstream_name(skill_dir.name, registry_entry)
        upstream_skill = upstream_cache / "skills" / upstream_name
        if not upstream_skill.is_dir():
            unreachable.append(f"{skill_dir.name} (upstream `{upstream_name}/` missing under {upstream_cache})")
            continue
        diff_lines = _diff_skill(skill_dir, upstream_skill)
        if diff_lines:
            drifted.append((skill_dir.name, diff_lines))
        else:
            unchanged.append(skill_dir.name)

    # Report
    if not args.ci:
        if drifted:
            print(f"\n=== Drift detected in {len(drifted)} skill(s) ===")
            for name, lines in drifted:
                print(f"\n[{name}]")
                for line in lines:
                    print(line)
        if unreachable:
            print(f"\n=== Unreachable: {len(unreachable)} skill(s) ===")
            for name in unreachable:
                print(f"  ? {name}")
        if unchanged and not drifted and not unreachable:
            print(f"All {len(unchanged)} vendored skills match upstream.")

    summary = (f"check_vendor_drift: total={total} unchanged={len(unchanged)} "
               f"drifted={len(drifted)} unreachable={len(unreachable)}")
    print(summary)

    if unreachable:
        return 2
    if drifted:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
