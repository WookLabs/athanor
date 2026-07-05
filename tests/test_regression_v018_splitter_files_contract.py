"""Regression test for v0.18.0 R-B4 — Splitter `files:` field parser contract.

The v0.18.0 dynamic Freeze allowlist (`scripts/work/build_freeze_allowlist.py`,
S1.2) makes the Splitter `files:` declaration **load-bearing**: silent
format drift in the Splitter output silently breaks Freeze enforcement.
R-B4 mandates a contract regression test that pins the field shape.

This test exercises the canonical parser against the fixture corpus under
`tests/fixtures/splitter_contract/`:
- 8 valid fixtures (forms the parser MUST accept)
- 4 invalid fixtures (forms the parser MUST tolerate without crashing —
  graceful return of empty files for that subtask)

Contract reference: `tests/fixtures/splitter_contract/README.md`.

## Parser under test

The contract under test is the Splitter output shape documented in
`skills/work/references/splitter.md` §Output Format (lines ~130-148):
the `## Subtasks` block containing `- [ ] **Subtask N:**` checkboxes
with nested `  - files: [{paths}]` field lines.

This test exercises a **reference parser** (`_reference_parse_subtask_files`)
that embodies the canonical Splitter contract. The reference parser is
the contract definition for R-B4 purposes; any downstream parser
(`scripts/work/build_freeze_allowlist.parse_subtask_files` or any future
consumer of Splitter output) is contractually required to produce the
same outputs against these fixtures when reading canonical Splitter
output.

Note: the in-flight `scripts/work/build_freeze_allowlist.py` (S1.2)
may target a different input shape (e.g. the planner-A prose form of
`.athanor/sessions/<id>/plan.md` before the Splitter has run). Its
own per-shape conformance is locked by `test_regression_v018_freeze_allowlist_builder.py`
(separate test, S1.2 deliverable). This file (S1.4) pins the Splitter
contract independently — that's the R-B4 anti-drift lock.

Plan reference: `.athanor/sessions/2026-05-28-004/plan.md` §Subtask 1.4 +
R-B4 (Risks section, R-2).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "splitter_contract"
VALID_DIR = FIXTURES_DIR / "valid"
INVALID_DIR = FIXTURES_DIR / "invalid"


# ---------------------------------------------------------------------------
# Parser under test
# ---------------------------------------------------------------------------

def _resolve_parser():
    """Return the reference parser embodying the Splitter contract.

    Future cross-validation hook: once any downstream consumer agrees to
    accept canonical Splitter output as input, this resolver can be
    extended to validate that consumer's parser against the same fixtures
    via a parametrize. Today only the reference parser is in scope.
    """
    return _reference_parse_subtask_files


# ---------------------------------------------------------------------------
# Reference (inline canonical) parser
# ---------------------------------------------------------------------------
# This is the contract embodiment. When S1.2's parser exists and is
# importable, it MUST produce the same outputs against the fixtures.
# When S1.2 does not yet exist, this reference parser keeps the test
# meaningful (RED → GREEN on the fixtures themselves).


_SUBTASK_HEADER_RE = re.compile(
    r"^\-\s*\[\s*[ xX]?\s*\]\s*\*\*Subtask\s+(?P<id>[\w\.\-]+)\s*:.*?\*\*\s*$"
)
# A valid `files:` field line within a subtask block. The leading "  - "
# indentation is canonical per `skills/work/references/splitter.md` Output
# Format. We tolerate 2 or 4 leading spaces before the dash for resilience,
# but require the dash + `files:` shape exactly (with the colon).
_FILES_FIELD_RE = re.compile(
    r"^(?P<indent>\s{2,4})\-\s+files\s*:\s*(?P<value>.*?)\s*$"
)


def _normalize_path(raw: str) -> str:
    """Normalize one path entry.

    - Strip whitespace and surrounding quotes (single or double).
    - Drop a leading `./` prefix (project-relative POSIX form).
    - Glob patterns (containing `*`, `?`, `[`) preserved verbatim.
    """
    s = raw.strip().strip('"').strip("'")
    if s.startswith("./"):
        s = s[2:]
    return s


def _parse_files_value(value: str) -> list[str]:
    """Parse the right-hand side of a `files:` field declaration.

    Accepts (per README contract):
      - `[a, b, c]` — bracketed comma-separated list
      - `[]` — empty list
      - `path/to/file.py` — bare path (no brackets), single entry

    Returns the (possibly empty) list of normalized path strings.

    Tolerates:
      - bare unquoted strings that look like neither a path nor a list:
        wrapped as a single-entry list (the freeze builder will glob-match
        it; downstream consumers can detect the mismatch).
      - empty value (`files:`): returns [].
    """
    v = value.strip()
    if not v:
        return []
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        if not inner:
            return []
        parts = [p for p in (x.strip() for x in inner.split(",")) if p]
        return [_normalize_path(p) for p in parts]
    # Bare value form — single entry. We don't validate path-shape here;
    # graceful tolerance is the contract.
    return [_normalize_path(v)]


def _reference_parse_subtask_files(plan_md_path: str | Path) -> list[dict]:
    """Reference implementation of the v0.18.0 Splitter `files:` parser.

    Returns a list of `{"subtask_id": str, "files": list[str]}` records,
    one per subtask block discovered under `## Subtasks` in the plan file.

    Subtasks with no `files:` line: `files` is `[]`.
    Subtasks with malformed `files:` shapes: parser does not crash; the
    subtask is included with the best-effort `files` interpretation per
    `_parse_files_value`. Lines that fail the `_FILES_FIELD_RE` match
    (e.g., missing colon, broken indent) are silently ignored — the
    subtask's `files` stays `[]`.
    """
    path = Path(plan_md_path)
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    # Find the `## Subtasks` header; if absent, no records.
    start_idx: Optional[int] = None
    for i, line in enumerate(lines):
        if line.strip().lower().startswith("## subtasks"):
            start_idx = i + 1
            break
    if start_idx is None:
        return []

    records: list[dict] = []
    current_id: Optional[str] = None
    current_files: list[str] = []

    def _flush():
        nonlocal current_id, current_files
        if current_id is not None:
            records.append({"subtask_id": current_id, "files": current_files})
        current_id = None
        current_files = []

    for line in lines[start_idx:]:
        # New subtask header — flush previous, start a new one.
        m_hdr = _SUBTASK_HEADER_RE.match(line)
        if m_hdr:
            _flush()
            current_id = m_hdr.group("id")
            current_files = []
            continue
        # Files field line within the current subtask block.
        m_f = _FILES_FIELD_RE.match(line)
        if m_f and current_id is not None:
            current_files = _parse_files_value(m_f.group("value"))
            continue
        # Anything else (other fields, blank lines, etc.) — ignore.
    _flush()
    return records


# ---------------------------------------------------------------------------
# Helpers for tests
# ---------------------------------------------------------------------------

def _files_for_subtask(records: list[dict], subtask_id: str = "1") -> list[str]:
    """Return the files list for the named subtask, or [] if not present."""
    for r in records:
        if str(r.get("subtask_id")) == subtask_id:
            return list(r.get("files", []))
    return []


# ---------------------------------------------------------------------------
# Fixture sanity tests
# ---------------------------------------------------------------------------

def test_fixture_layout_exists():
    """MUST: fixture directory layout exists with README and valid/invalid dirs."""
    assert FIXTURES_DIR.is_dir(), f"missing fixture dir {FIXTURES_DIR}"
    assert (FIXTURES_DIR / "README.md").is_file(), "fixture README missing"
    assert VALID_DIR.is_dir(), "valid/ subdir missing"
    assert INVALID_DIR.is_dir(), "invalid/ subdir missing"


def test_eight_valid_fixtures_present():
    """MUST: at least 8 valid fixtures present (per dispatched task)."""
    valid = sorted(VALID_DIR.glob("valid_*.md"))
    assert len(valid) >= 8, (
        f"expected ≥ 8 valid fixtures, found {len(valid)}: {[p.name for p in valid]}"
    )


def test_four_invalid_fixtures_present():
    """MUST: 4 invalid fixtures present (per dispatched task)."""
    invalid = sorted(INVALID_DIR.glob("invalid_*.md"))
    assert len(invalid) >= 4, (
        f"expected ≥ 4 invalid fixtures, found {len(invalid)}: {[p.name for p in invalid]}"
    )


def test_readme_documents_contract():
    """MUST: README documents the parser contract (per acceptance criterion)."""
    readme = (FIXTURES_DIR / "README.md").read_text(encoding="utf-8")
    for token in ["files:", "Contract", "accepted forms", "rejected forms"]:
        assert token in readme, f"README missing contract token: {token!r}"


# ---------------------------------------------------------------------------
# Valid fixtures — parser MUST extract `files:` correctly
# ---------------------------------------------------------------------------

def test_valid_01_single_file():
    parse = _resolve_parser()
    records = parse(VALID_DIR / "valid_01_single_file.md")
    files = _files_for_subtask(records, "1")
    assert files == ["scripts/hooks/pretool_dispatcher.py"], files


def test_valid_02_multi_file():
    parse = _resolve_parser()
    records = parse(VALID_DIR / "valid_02_multi_file.md")
    files = _files_for_subtask(records, "1")
    assert files == [
        "scripts/hooks/_athanor_hook_runtime.py",
        "scripts/hooks/pretool_kernel_guard.py",
    ], files


def test_valid_03_bare_path():
    parse = _resolve_parser()
    records = parse(VALID_DIR / "valid_03_bare_path.md")
    files = _files_for_subtask(records, "1")
    # Bare path form returns a single-entry list (tolerated shorthand).
    assert files == ["path/to/file.py"], files


def test_valid_04_glob_patterns_preserved():
    parse = _resolve_parser()
    records = parse(VALID_DIR / "valid_04_glob_patterns.md")
    files = _files_for_subtask(records, "1")
    # Globs MUST survive verbatim — `_normalize_path` only strips quotes
    # and leading `./`, never glob metacharacters.
    assert files == ["src/**", "tests/**"], files


def test_valid_05_empty_array():
    parse = _resolve_parser()
    records = parse(VALID_DIR / "valid_05_empty_array.md")
    files = _files_for_subtask(records, "1")
    assert files == [], files


def test_valid_06_no_files_field():
    parse = _resolve_parser()
    records = parse(VALID_DIR / "valid_06_no_files_field.md")
    # Subtask present, but no files: field declared. Parser MUST still
    # record the subtask with an empty files list.
    assert len(records) == 1, records
    assert records[0]["subtask_id"] == "1"
    assert records[0]["files"] == []


def test_valid_07_multi_doc():
    parse = _resolve_parser()
    records = parse(VALID_DIR / "valid_07_multi_doc.md")
    files = _files_for_subtask(records, "1")
    assert files == ["docs/migration.md", "CHANGELOG.md"], files


def test_valid_08_long_path():
    parse = _resolve_parser()
    records = parse(VALID_DIR / "valid_08_long_path.md")
    files = _files_for_subtask(records, "1")
    # Hyphens/underscores/dots in path preserved verbatim.
    assert files == ["scripts/hooks/_athanor_hook_runtime.py"], files


# ---------------------------------------------------------------------------
# Invalid fixtures — parser MUST handle gracefully (no crash)
# ---------------------------------------------------------------------------

def test_invalid_01_unquoted_string_does_not_crash():
    parse = _resolve_parser()
    # MUST not raise. Tolerated as a single-entry bare path; the freeze
    # builder will simply not glob-match it (acceptable degradation).
    records = parse(INVALID_DIR / "invalid_01_unquoted_string.md")
    assert isinstance(records, list)
    assert len(records) >= 1
    # The bare value is captured as a single-entry list (resilience).
    files = _files_for_subtask(records, "1")
    assert files == ["not_a_path_or_list"], files


def test_invalid_02_empty_value_does_not_crash():
    parse = _resolve_parser()
    records = parse(INVALID_DIR / "invalid_02_empty_value.md")
    assert isinstance(records, list)
    # Subtask is present; `files:` line has no value → empty list.
    assert len(records) >= 1
    files = _files_for_subtask(records, "1")
    assert files == [], files


def test_invalid_03_missing_colon_does_not_crash():
    parse = _resolve_parser()
    records = parse(INVALID_DIR / "invalid_03_missing_colon.md")
    assert isinstance(records, list)
    # Line `  - files [...]` is NOT a valid `files:` field declaration
    # (missing colon). Parser does not match it. Subtask's files = [].
    assert len(records) >= 1
    files = _files_for_subtask(records, "1")
    assert files == [], files


def test_invalid_04_broken_indent_does_not_crash():
    parse = _resolve_parser()
    records = parse(INVALID_DIR / "invalid_04_broken_indent.md")
    assert isinstance(records, list)
    # The `files:` line is at the outer level (zero indent), not inside the
    # subtask block. Parser MUST NOT crash and MUST NOT attribute it to
    # the subtask — files for subtask 1 stays [].
    assert len(records) >= 1
    files = _files_for_subtask(records, "1")
    assert files == [], files


# ---------------------------------------------------------------------------
# Cross-cutting invariants
# ---------------------------------------------------------------------------

def test_parser_returns_list_of_dicts_on_all_fixtures():
    """MUST: parser return shape is uniform across the fixture corpus."""
    parse = _resolve_parser()
    for fixture in sorted(VALID_DIR.glob("*.md")) + sorted(INVALID_DIR.glob("*.md")):
        records = parse(fixture)
        assert isinstance(records, list), f"{fixture.name}: not a list"
        for r in records:
            assert isinstance(r, dict), f"{fixture.name}: record not a dict: {r!r}"
            assert "subtask_id" in r, f"{fixture.name}: missing subtask_id"
            assert "files" in r, f"{fixture.name}: missing files"
            assert isinstance(r["files"], list), (
                f"{fixture.name}: files is not a list: {r['files']!r}"
            )


def test_parser_handles_missing_file_gracefully():
    """MUST: nonexistent plan path returns empty list, no crash."""
    parse = _resolve_parser()
    records = parse(REPO_ROOT / "nonexistent" / "plan.md")
    assert records == []


def test_parser_handles_plan_without_subtasks_section():
    """MUST: plan with no `## Subtasks` section returns empty list."""
    parse = _resolve_parser()
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write("# Plan\n\nSome prose, but no subtasks section.\n")
        tmp = Path(f.name)
    try:
        records = parse(tmp)
        assert records == []
    finally:
        tmp.unlink(missing_ok=True)
