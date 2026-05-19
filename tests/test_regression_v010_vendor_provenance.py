"""Regression test for v0.10.0 U23 invariant — every vendored markdown
file under `skills/ce-*/`, `skills/sp-*/`, and `agents/vendored/ce/`
carries a valid T2 provenance block.

The provenance block is an HTML comment (`<!-- Provenance: ... -->`) inserted
after the YAML frontmatter (when present) or at the top of the file. Required
fields: upstream / source-commit / upstream-url / license / modifications /
t0-t1-disproof.

If a future contributor adds a new vendored file without provenance, or
removes the block from an existing file, this test fires.

Plan reference: docs/plans/2026-05-19-003-feat-v0.10.0-absorb-ce-superpowers-plan.md
§U23.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


REQUIRED_FIELDS = ("upstream:", "source-commit:", "upstream-url:", "license:",
                   "modifications:", "t0-t1-disproof:")


def _iter_vendored_markdown_files() -> list[Path]:
    """Find every vendored markdown file."""
    paths: list[Path] = []
    skills_dir = REPO_ROOT / "skills"
    for entry in sorted(skills_dir.iterdir()):
        if not entry.is_dir():
            continue
        if not (entry.name.startswith("ce-") or entry.name.startswith("sp-")):
            continue
        for p in entry.rglob("*.md"):
            paths.append(p)
    agents_vendored = REPO_ROOT / "agents" / "vendored" / "ce"
    if agents_vendored.is_dir():
        for p in agents_vendored.rglob("*.md"):
            paths.append(p)
    return paths


def _find_provenance_block(text: str) -> str:
    """Locate the first HTML comment block whose content starts with
    'Provenance:'. Returns the block (including the opening/closing
    markers) or empty string if not found."""
    start_marker = "<!-- Provenance:"
    end_marker = "-->"
    start = text.find(start_marker)
    if start < 0:
        return ""
    end = text.find(end_marker, start)
    if end < 0:
        return ""
    return text[start : end + len(end_marker)]


def test_vendored_markdown_count_meets_expectation():
    """MUST: vendor surface includes a meaningful number of files
    (regression catches a script that silently shipped 0 vendored files)."""
    files = _iter_vendored_markdown_files()
    assert len(files) >= 200, (
        f"Expected at least 200 vendored markdown files (CE + superpowers + "
        f"sub-agents); found {len(files)}. Did the M1 scaffold regress?"
    )


def test_every_vendored_markdown_has_provenance_block():
    """MUST: every vendored markdown file contains a `<!-- Provenance: ... -->`
    block."""
    files = _iter_vendored_markdown_files()
    missing: list[str] = []
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        block = _find_provenance_block(text)
        if not block:
            missing.append(str(f.relative_to(REPO_ROOT)))
    assert not missing, (
        f"{len(missing)} vendored markdown file(s) missing provenance block. "
        f"Sample: {missing[:5]}"
    )


def test_provenance_block_has_required_fields():
    """MUST: each provenance block contains all 6 required fields."""
    files = _iter_vendored_markdown_files()
    incomplete: list[tuple[str, list[str]]] = []
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        block = _find_provenance_block(text)
        if not block:
            continue  # already caught by the previous test
        missing_fields = [field for field in REQUIRED_FIELDS if field not in block]
        if missing_fields:
            incomplete.append((str(f.relative_to(REPO_ROOT)), missing_fields))
    assert not incomplete, (
        f"{len(incomplete)} vendored file(s) have incomplete provenance "
        f"blocks. Sample: {incomplete[:3]}"
    )


def test_provenance_license_is_mit():
    """MUST: every vendored file's license field is MIT (CE and superpowers
    upstreams are both MIT)."""
    files = _iter_vendored_markdown_files()
    non_mit: list[str] = []
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        block = _find_provenance_block(text)
        if not block:
            continue
        # Find the license line
        for line in block.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("license:"):
                if "mit" not in stripped.lower():
                    non_mit.append(f"{f.relative_to(REPO_ROOT)} → {stripped}")
                break
    assert not non_mit, (
        f"Non-MIT license found in vendored provenance: {non_mit}"
    )


def test_native_skills_not_affected():
    """MUST: athanor-native skills (skills/discuss/, plan/, work/, etc.) are
    NOT mutated to look like vendored files (would mean we accidentally
    overwrote native content)."""
    native_skills = ["discuss", "plan", "work", "analyze", "debug", "review",
                     "deep-plan", "lite-plan", "setup", "scope-drift"]
    for name in native_skills:
        skill_md = REPO_ROOT / "skills" / name / "SKILL.md"
        if not skill_md.exists():
            continue
        text = skill_md.read_text(encoding="utf-8")
        # Native skills must NOT have a "vendored from ce@" or "vendored from
        # superpowers@" provenance line. The scope-drift skill is vendored
        # from claude-octopus (acceptable); but native skills from athanor
        # must not be misclassified.
        if name == "scope-drift":
            continue  # known vendor (claude-octopus)
        if "vendored from ce@" in text.lower() or "vendored at athanor v0.10.0" in text:
            raise AssertionError(
                f"Athanor-native skill {name}/SKILL.md has been mutated to "
                f"contain v0.10.0 vendor provenance — content was clobbered."
            )
