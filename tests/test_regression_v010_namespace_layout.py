"""Regression test for v0.10.0 U24 invariant — vendored skill namespace
policy + flat skill layout.

D2 policy from the plan:
- Athanor-native skills (plan, work, debug, setup, discuss, analyze,
  review, deep-plan, lite-plan, scope-drift, verification-before-completion)
  keep the unprefixed slot at `skills/<name>/`.
- CE-vendored skills land at `skills/ce-<name>/` (depth 1) for Claude Code
  auto-discovery; e.g., `/athanor:ce-plan`.
- Superpowers-vendored skills land at `skills/sp-<name>/` (depth 1);
  e.g., `/athanor:sp-brainstorming`.
- Every vendored SKILL.md has YAML frontmatter `name:` matching its
  directory name.

Plan reference: docs/plans/2026-05-19-003-feat-v0.10.0-absorb-ce-superpowers-plan.md
§U24, D2.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"

ATHANOR_NATIVE = {
    "analyze", "debug", "deep-plan", "discuss", "lite-plan", "plan",
    "review", "scope-drift", "setup", "verification-before-completion",
    "work",
}


def _list_skill_dirs() -> list[Path]:
    return [p for p in sorted(SKILLS_DIR.iterdir()) if p.is_dir()]


def _extract_frontmatter_name(skill_md: Path) -> str:
    text = skill_md.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].rstrip() != "---":
        return ""
    for line in lines[1:]:
        if line.rstrip() == "---":
            break
        m = re.match(r"^\s*name:\s*['\"]?([^'\"]+)['\"]?\s*$", line)
        if m:
            return m.group(1).strip()
    return ""


def test_vendor_skill_count_meets_expectation():
    """MUST: vendored skill directories count matches plan §M3+M4 (≥37 CE
    + ≥13 sp = ≥50). Catches a regression where the script silently
    skipped a batch."""
    dirs = _list_skill_dirs()
    ce = [d for d in dirs if d.name.startswith("ce-")]
    sp = [d for d in dirs if d.name.startswith("sp-")]
    assert len(ce) >= 37, f"Expected at least 37 ce-* skills; found {len(ce)}"
    assert len(sp) >= 13, f"Expected at least 13 sp-* skills; found {len(sp)}"


def test_every_vendored_skill_has_skill_md():
    """MUST: each ce-* and sp-* skill directory has a SKILL.md."""
    missing: list[str] = []
    for d in _list_skill_dirs():
        if d.name.startswith("ce-") or d.name.startswith("sp-"):
            if not (d / "SKILL.md").exists():
                missing.append(d.name)
    assert not missing, f"Vendored skills without SKILL.md: {missing}"


def test_native_skills_preserve_unprefixed_slot():
    """MUST: athanor-native skills keep their unprefixed directory at
    skills/<n>/."""
    dirs = {d.name for d in _list_skill_dirs()}
    missing_native = [n for n in ATHANOR_NATIVE if n not in dirs]
    assert not missing_native, (
        f"Athanor-native skill(s) missing: {missing_native}. "
        f"D2 policy requires native skills to keep the unprefixed slot."
    )


def test_no_namespace_id_duplication():
    """MUST: no two skill directories produce the same `athanor:<n>`
    invocation."""
    dirs = [d.name for d in _list_skill_dirs()]
    assert len(dirs) == len(set(dirs)), (
        f"Duplicate skill directory names detected: {dirs}"
    )


def test_vendored_skill_frontmatter_name_matches_directory():
    """MUST: each vendored SKILL.md's YAML frontmatter `name:` field matches
    its directory name. Claude Code skill auto-discovery requires this
    alignment to expose the skill as `/athanor:<name>`."""
    mismatches: list[str] = []
    for d in _list_skill_dirs():
        if not (d.name.startswith("ce-") or d.name.startswith("sp-")):
            continue
        skill_md = d / "SKILL.md"
        if not skill_md.exists():
            continue
        fm_name = _extract_frontmatter_name(skill_md)
        if not fm_name:
            mismatches.append(f"{d.name}: no frontmatter name found")
            continue
        if fm_name != d.name:
            mismatches.append(f"{d.name}: frontmatter name='{fm_name}'")
    assert not mismatches, (
        f"Frontmatter name/directory mismatch in {len(mismatches)} file(s). "
        f"Sample: {mismatches[:5]}"
    )


def test_marketplace_version_in_0_10_x_series():
    """MUST: marketplace.json plugin version is in the 0.10.x series.

    v0.10.1 generalization: pinned to "0.10.0" originally; relaxed to the
    minor series so v0.10.1+ patch releases don't have to keep editing
    this test. v0.11.0+ will need an explicit update.
    """
    import json
    mp = json.loads((REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text())
    versions = [p.get("version") for p in mp.get("plugins", [])]
    in_series = [v for v in versions if v and v.startswith("0.10.")]
    assert in_series, (
        f"marketplace.json plugin version must be in 0.10.x series; got {versions}"
    )


def test_plugin_manifest_version_matches_marketplace():
    """MUST: plugin.json version matches marketplace.json version (single
    source-of-truth across the two manifests)."""
    import json
    pj = json.loads((REPO_ROOT / ".claude-plugin" / "plugin.json").read_text())
    mp = json.loads((REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text())
    pj_version = pj.get("version")
    mp_versions = [p.get("version") for p in mp.get("plugins", [])]
    assert pj_version in mp_versions, (
        f"plugin.json version {pj_version!r} not found in marketplace.json "
        f"plugin versions {mp_versions}"
    )
    assert pj_version and pj_version.startswith("0.10."), (
        f"plugin.json version must be in 0.10.x series; got {pj_version!r}"
    )
