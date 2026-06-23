"""Regression test for v0.10.0 U24 invariant — vendored skill namespace
policy + flat skill layout.

D2 policy from the plan:
- Athanor-native skills (plan, deep-plan, lite-plan, prompt-gen, work,
  debug, setup, discuss, analyze, review, lfg, lfg-goal, scope-drift,
  verification-before-completion) keep the unprefixed slot at
  `skills/<name>/`. v0.17.0 / S07 collapsed `deep-plan` + `lite-plan`
  into `/athanor:plan --depth=`, then the current surface restored them as
  thin wrappers over the canonical plan protocol.
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
    "analyze", "assess", "debug", "deep-plan", "discuss", "lfg", "lfg-goal",
    "lite-plan", "plan", "prompt-gen", "review", "scope-drift", "setup",
    "verification-before-completion", "work",
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
    """MUST: vendored skill directories count matches the post-cut expectation.

    v0.10.0 originally vendored 37 ce-* + 13 sp-* skills. v0.11.2 hygiene cut
    removed 4 CE-plugin-lifecycle skills (`ce-update`, `ce-report-bug`,
    `ce-release-notes`, `ce-setup`). v0.12.0 atomic cut (per D8 KEEP) leaves
    exactly 1 ce-* (`ce-test-browser`) and 0 sp-* on disk.

    Post-v0.12.0 expectation: exactly 1 ce-*, 0 sp-*. The pre-v0.12.0
    `>= 33 ce-*` / `>= 13 sp-*` floor is replaced by a fixed ceiling that
    pins the D8 carve-out.
    """
    dirs = _list_skill_dirs()
    ce = [d.name for d in dirs if d.name.startswith("ce-")]
    sp = [d.name for d in dirs if d.name.startswith("sp-")]
    assert ce == ["ce-test-browser"], (
        f"Expected exactly 1 ce-* (`ce-test-browser` per D8 KEEP); "
        f"found {ce!r}"
    )
    assert sp == [], (
        f"Expected 0 sp-* skills post-v0.12.0; found {sp!r}"
    )


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


def test_marketplace_version_in_0_10_or_0_11_or_0_12_or_0_13_or_0_14_or_0_15_or_0_16_x_series():
    """MUST: marketplace.json plugin version is in the 0.10.x / 0.11.x / 0.12.x / 0.13.x / 0.14.x / 0.15.x / 0.16.x / 0.17.x / 0.18.x / 0.19.x / 0.20.x series.

    v0.10.1 generalization → v0.11.0 extension → v0.12.0 extension →
    v0.13.0 extension → v0.14.0 extension → v0.15.0 extension → v0.16.0
    extension → v0.17.0 extension → v0.18.0 extension: pinned to "0.10.0"
    originally; relaxed to 0.10.x at v0.10.1; extended to 0.10.x or 0.11.x
    at v0.11.0; extended to include 0.12.x at v0.12.0 (concept-kernel
    cutover release); extended to include 0.13.x at v0.13.0 (lfg-goal
    release); extended to include 0.14.x at v0.14.0 (native agent
    definitions); extended to include 0.15.x at v0.15.0 (LFG pipeline
    contract reconciliation); extended to include 0.16.x at v0.16.0
    (multi-status executor + PreToolUse Kernel Guard + CLAUDE.md token
    diet); extended to include 0.17.x at v0.17.0 (surface cut + capability
    spikes); extended to include 0.18.x at v0.18.0 (Freeze infrastructure);
    extended to include 0.19.x at v0.19.0 (evidence harness + organization
    model); extended to include 0.20.x at v0.20.0 (ref optimization + uv
    tooling migration).
    """
    import json
    mp = json.loads(
        (REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
    )
    versions = [p.get("version") for p in mp.get("plugins", [])]
    in_series = [v for v in versions
                 if v and (
                     v.startswith("0.10.")
                     or v.startswith("0.11.")
                     or v.startswith("0.12.")
                     or v.startswith("0.13.")
                     or v.startswith("0.14.")
                     or v.startswith("0.15.")
                        or v.startswith("0.16.")
                        or v.startswith("0.17.")
                        or v.startswith("0.18.")
                        or v.startswith("0.19.")
                        or v.startswith("0.20.")
                     )]
    assert in_series, (
        f"marketplace.json plugin version must be in 0.10.x / 0.11.x / 0.12.x / 0.13.x / 0.14.x / 0.15.x / 0.16.x / 0.17.x / 0.18.x / 0.19.x / 0.20.x series; "
        f"got {versions}"
    )


def test_plugin_manifest_version_matches_marketplace():
    """MUST: plugin.json version matches marketplace.json version (single
    source-of-truth across the two manifests)."""
    import json
    pj = json.loads(
        (REPO_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    mp = json.loads(
        (REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
    )
    pj_version = pj.get("version")
    mp_versions = [p.get("version") for p in mp.get("plugins", [])]
    assert pj_version in mp_versions, (
        f"plugin.json version {pj_version!r} not found in marketplace.json "
        f"plugin versions {mp_versions}"
    )
    assert pj_version and (
        pj_version.startswith("0.10.")
        or pj_version.startswith("0.11.")
        or pj_version.startswith("0.12.")
        or pj_version.startswith("0.13.")
        or pj_version.startswith("0.14.")
        or pj_version.startswith("0.15.")
            or pj_version.startswith("0.16.")
            or pj_version.startswith("0.17.")
            or pj_version.startswith("0.18.")
            or pj_version.startswith("0.19.")
            or pj_version.startswith("0.20.")
        ), (
            f"plugin.json version must be in 0.10.x / 0.11.x / 0.12.x / 0.13.x / 0.14.x / 0.15.x / 0.16.x / 0.17.x / 0.18.x / 0.19.x / 0.20.x series; "
            f"got {pj_version!r}"
        )
