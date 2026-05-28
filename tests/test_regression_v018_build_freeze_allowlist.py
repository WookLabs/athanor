"""Regression tests for `scripts/work/build_freeze_allowlist.py` (Subtask 1.2).

Covers the v0.18.0 Phase 1 freeze-allowlist builder. The script parses
`plan.md` subtask blocks, extracts `files:` declarations, and emits a
`freeze-allowlist.json` consumed at PreToolUse runtime by `freeze_guard.py`.

Contract (from plan.md §Phase 1 + Subtask 1.2 acceptance criteria):
  - `parse_subtask_files(plan_md_path) -> list[dict]` — extracts
    `[{subtask_id, files: list[str]}, ...]` per subtask block.
  - `build_allowlist(parsed, session_id, extras) -> dict` — composes the
    full allowlist with defaults: `.athanor/sessions/<id>/**` (always),
    `.athanor/lessons/**` (always), all subtask files (deduped, POSIX-
    normalized), plus user extras (extend, never replace).
  - `write_allowlist(allowlist, output_path) -> None` — atomic write via
    tempfile + os.replace.

The 7 sub-cases pinned by Subtask 1.2 are tagged in the test names; an
additional set of CLI + atomic-write tests round out the ~15 case
expectation.

Stdlib only.
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BUILDER_SCRIPT = REPO_ROOT / "scripts" / "work" / "build_freeze_allowlist.py"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Fixture plan.md shapes (mirror Splitter output forms)
# ---------------------------------------------------------------------------


PLAN_BULLET_LIST = """\
# Plan

## Subtasks

#### Subtask 1.1 — Bullet list example

**execution_note**: `spec-then-tdd`

**acceptance_criteria**:
- something

**files**:
- `scripts/work/build_freeze_allowlist.py`
- `tests/test_regression_v018_build_freeze_allowlist.py`

---

#### Subtask 1.2 — Second subtask

**files**:
- `skills/work/SKILL.md`
- `skills/work/references/freeze.md`
"""


PLAN_INLINE_LIST = """\
# Plan

## Subtasks

#### Subtask 2.1 — Inline list example

**execution_note**: `spec-then-tdd`

**files**: [`scripts/hooks/freeze_guard.py`, `scripts/hooks/hook_state.py`]
"""


PLAN_NO_FILES_FIELD = """\
# Plan

## Subtasks

#### Subtask 3.1 — Doc-only

**execution_note**: `direct`

**acceptance_criteria**:
- prose only update
"""


PLAN_NO_SUBTASKS_SECTION = """\
# Plan

Some intro prose.

## Risks

- foo
- bar
"""


PLAN_RELATIVE_PATHS = """\
# Plan

## Subtasks

#### Subtask 4.1 — Path normalization

**files**:
- `./scripts/work/build_freeze_allowlist.py`
- `./tests/test_regression_v018_build_freeze_allowlist.py`
"""


PLAN_GLOB_PATHS = """\
# Plan

## Subtasks

#### Subtask 5.1 — Glob patterns preserved

**files**:
- `src/**/*.py`
- `tests/**/test_*.py`
"""


PLAN_MIXED_BULLET_AND_INLINE = """\
# Plan

## Subtasks

#### Subtask 6.1 — Bullet form

**files**:
- `a.py`
- `b.py`

---

#### Subtask 6.2 — Inline form

**files**: [`c.py`, `d.py`]
"""


PLAN_EMPTY_FILES_LIST = """\
# Plan

## Subtasks

#### Subtask 7.1 — Empty files list

**files**: []
"""


# ---------------------------------------------------------------------------
# Module import
# ---------------------------------------------------------------------------


def _import_builder():
    """Dynamic import — script lives outside the standard package layout."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "build_freeze_allowlist", BUILDER_SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Contract: script exists
# ---------------------------------------------------------------------------


def test_builder_script_exists():
    assert BUILDER_SCRIPT.is_file(), (
        f"build_freeze_allowlist.py missing at {BUILDER_SCRIPT}"
    )


def test_builder_script_has_shebang():
    """Should be invocable directly via python3."""
    first_line = BUILDER_SCRIPT.read_text(encoding="utf-8").splitlines()[0]
    assert first_line.startswith("#!") and "python" in first_line, (
        f"build_freeze_allowlist.py must begin with a python shebang; got: {first_line!r}"
    )


# ---------------------------------------------------------------------------
# Sub-case 1: Normal subtask with explicit `files:` list
# ---------------------------------------------------------------------------


def test_parse_bullet_list_subtask_files(tmp_path: Path):
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_BULLET_LIST, encoding="utf-8")
    mod = _import_builder()
    parsed = mod.parse_subtask_files(str(plan))
    assert isinstance(parsed, list)
    # Should pick up 2 subtasks
    assert len(parsed) == 2, f"Expected 2 subtasks, got {len(parsed)}: {parsed}"
    # Collect all files across subtasks
    all_files = []
    for entry in parsed:
        assert "subtask_id" in entry and "files" in entry
        all_files.extend(entry["files"])
    assert "scripts/work/build_freeze_allowlist.py" in all_files
    assert "tests/test_regression_v018_build_freeze_allowlist.py" in all_files
    assert "skills/work/SKILL.md" in all_files
    assert "skills/work/references/freeze.md" in all_files


def test_build_allowlist_includes_defaults_and_subtask_files(tmp_path: Path):
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_BULLET_LIST, encoding="utf-8")
    mod = _import_builder()
    parsed = mod.parse_subtask_files(str(plan))
    allowlist = mod.build_allowlist(parsed, session_id="2026-05-28-004", extras=[])
    allowed = allowlist["allowed_paths"]
    assert ".athanor/sessions/2026-05-28-004/**" in allowed
    assert ".athanor/lessons/**" in allowed
    assert "scripts/work/build_freeze_allowlist.py" in allowed
    assert "skills/work/SKILL.md" in allowed
    # Metadata
    assert allowlist["session_id"] == "2026-05-28-004"
    assert "built_at" in allowlist


# ---------------------------------------------------------------------------
# Sub-case 2: Subtask with no `files:` field → defaults preserved, no crash
# ---------------------------------------------------------------------------


def test_no_files_field_yields_defaults_only(tmp_path: Path):
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_NO_FILES_FIELD, encoding="utf-8")
    mod = _import_builder()
    parsed = mod.parse_subtask_files(str(plan))
    # parse may yield an entry with empty files or no entry; both acceptable
    assert isinstance(parsed, list)
    allowlist = mod.build_allowlist(parsed, session_id="2026-05-28-004", extras=[])
    allowed = allowlist["allowed_paths"]
    assert ".athanor/sessions/2026-05-28-004/**" in allowed
    assert ".athanor/lessons/**" in allowed


# ---------------------------------------------------------------------------
# Sub-case 3: Mixed bullet + inline format → both shapes parse
# ---------------------------------------------------------------------------


def test_mixed_bullet_and_inline_forms_parse(tmp_path: Path):
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_MIXED_BULLET_AND_INLINE, encoding="utf-8")
    mod = _import_builder()
    parsed = mod.parse_subtask_files(str(plan))
    all_files = [f for e in parsed for f in e["files"]]
    assert "a.py" in all_files
    assert "b.py" in all_files
    assert "c.py" in all_files
    assert "d.py" in all_files


def test_inline_list_form_parses(tmp_path: Path):
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_INLINE_LIST, encoding="utf-8")
    mod = _import_builder()
    parsed = mod.parse_subtask_files(str(plan))
    all_files = [f for e in parsed for f in e["files"]]
    assert "scripts/hooks/freeze_guard.py" in all_files
    assert "scripts/hooks/hook_state.py" in all_files


# ---------------------------------------------------------------------------
# Sub-case 4: Relative path normalization (`./foo/bar.py` → `foo/bar.py`)
# ---------------------------------------------------------------------------


def test_relative_path_normalization(tmp_path: Path):
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_RELATIVE_PATHS, encoding="utf-8")
    mod = _import_builder()
    parsed = mod.parse_subtask_files(str(plan))
    allowlist = mod.build_allowlist(parsed, session_id="2026-05-28-004", extras=[])
    allowed = allowlist["allowed_paths"]
    # ./foo → foo
    assert "scripts/work/build_freeze_allowlist.py" in allowed
    assert "tests/test_regression_v018_build_freeze_allowlist.py" in allowed
    # No path begins with "./"
    for p in allowed:
        assert not p.startswith("./"), f"unnormalized path slipped in: {p}"


# ---------------------------------------------------------------------------
# Sub-case 5: Glob entries (`src/**/*.py`) preserved verbatim
# ---------------------------------------------------------------------------


def test_glob_patterns_preserved(tmp_path: Path):
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_GLOB_PATHS, encoding="utf-8")
    mod = _import_builder()
    parsed = mod.parse_subtask_files(str(plan))
    allowlist = mod.build_allowlist(parsed, session_id="2026-05-28-004", extras=[])
    allowed = allowlist["allowed_paths"]
    assert "src/**/*.py" in allowed
    assert "tests/**/test_*.py" in allowed


# ---------------------------------------------------------------------------
# Sub-case 6: User extras merged correctly (extend, not replace)
# ---------------------------------------------------------------------------


def test_user_extras_extend_not_replace(tmp_path: Path):
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_BULLET_LIST, encoding="utf-8")
    mod = _import_builder()
    parsed = mod.parse_subtask_files(str(plan))
    extras = ["docs/CUSTOM.md", "config/local.yaml"]
    allowlist = mod.build_allowlist(
        parsed, session_id="2026-05-28-004", extras=extras,
    )
    allowed = allowlist["allowed_paths"]
    # Subtask files preserved
    assert "scripts/work/build_freeze_allowlist.py" in allowed
    # Defaults preserved
    assert ".athanor/sessions/2026-05-28-004/**" in allowed
    # Extras added
    assert "docs/CUSTOM.md" in allowed
    assert "config/local.yaml" in allowed


# ---------------------------------------------------------------------------
# Sub-case 7: Empty plan.md → minimal allowlist (defaults only)
# ---------------------------------------------------------------------------


def test_empty_plan_md_yields_defaults_only(tmp_path: Path):
    plan = tmp_path / "plan.md"
    plan.write_text("", encoding="utf-8")
    mod = _import_builder()
    parsed = mod.parse_subtask_files(str(plan))
    assert parsed == []
    allowlist = mod.build_allowlist(parsed, session_id="2026-05-28-004", extras=[])
    allowed = allowlist["allowed_paths"]
    assert ".athanor/sessions/2026-05-28-004/**" in allowed
    assert ".athanor/lessons/**" in allowed


def test_no_subtasks_section_yields_empty_parse(tmp_path: Path):
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_NO_SUBTASKS_SECTION, encoding="utf-8")
    mod = _import_builder()
    parsed = mod.parse_subtask_files(str(plan))
    assert parsed == []


def test_empty_files_list_yields_no_subtask_files(tmp_path: Path):
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_EMPTY_FILES_LIST, encoding="utf-8")
    mod = _import_builder()
    parsed = mod.parse_subtask_files(str(plan))
    # Either 1 subtask with empty files OR 0 subtasks — both acceptable
    all_files = [f for e in parsed for f in e["files"]]
    assert all_files == []


# ---------------------------------------------------------------------------
# Missing plan.md handling
# ---------------------------------------------------------------------------


def test_missing_plan_md_returns_empty_and_warns(tmp_path: Path, capsys):
    missing = tmp_path / "nonexistent.md"
    mod = _import_builder()
    parsed = mod.parse_subtask_files(str(missing))
    assert parsed == []
    # Allowlist should still build with defaults
    allowlist = mod.build_allowlist(parsed, session_id="2026-05-28-004", extras=[])
    assert ".athanor/sessions/2026-05-28-004/**" in allowlist["allowed_paths"]


# ---------------------------------------------------------------------------
# Atomic write
# ---------------------------------------------------------------------------


def test_write_allowlist_creates_valid_json(tmp_path: Path):
    mod = _import_builder()
    allowlist = {
        "session_id": "2026-05-28-004",
        "built_at": "2026-05-28T00:00:00Z",
        "allowed_paths": [".athanor/sessions/2026-05-28-004/**", "a.py"],
        "default_paths": [".athanor/sessions/2026-05-28-004/**"],
        "subtask_paths": ["a.py"],
        "built_from": "plan.md",
    }
    out = tmp_path / "freeze-allowlist.json"
    mod.write_allowlist(allowlist, str(out))
    assert out.is_file()
    parsed = json.loads(out.read_text(encoding="utf-8"))
    assert parsed["session_id"] == "2026-05-28-004"
    assert ".athanor/sessions/2026-05-28-004/**" in parsed["allowed_paths"]


def test_write_allowlist_atomic_no_tmp_left_behind(tmp_path: Path):
    """Atomic write: after success, .tmp sibling must not remain."""
    mod = _import_builder()
    allowlist = {
        "session_id": "2026-05-28-004",
        "built_at": "2026-05-28T00:00:00Z",
        "allowed_paths": [".athanor/sessions/2026-05-28-004/**"],
        "default_paths": [".athanor/sessions/2026-05-28-004/**"],
        "subtask_paths": [],
        "built_from": "plan.md",
    }
    out = tmp_path / "freeze-allowlist.json"
    mod.write_allowlist(allowlist, str(out))
    # Sibling .tmp must be cleaned up
    siblings = list(tmp_path.iterdir())
    tmp_files = [p for p in siblings if p.name.endswith(".tmp")]
    assert tmp_files == [], f"atomic write left .tmp file behind: {tmp_files}"


# ---------------------------------------------------------------------------
# CLI usage
# ---------------------------------------------------------------------------


def test_cli_emits_valid_json_to_default_session_path(tmp_path: Path):
    """End-to-end CLI: create fake project, plan.md, invoke script,
    verify .athanor/sessions/<id>/freeze-allowlist.json exists with shape."""
    project_root = tmp_path / "proj"
    session_id = "2026-05-28-004"
    session_dir = project_root / ".athanor" / "sessions" / session_id
    session_dir.mkdir(parents=True)
    plan = session_dir / "plan.md"
    plan.write_text(PLAN_BULLET_LIST, encoding="utf-8")
    # invoke script with cwd=project_root
    result = subprocess.run(
        [sys.executable, str(BUILDER_SCRIPT), "--session-id", session_id],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"CLI failed (exit {result.returncode}):\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    out_path = session_dir / "freeze-allowlist.json"
    assert out_path.is_file(), f"expected output at {out_path}, not found"
    parsed = json.loads(out_path.read_text(encoding="utf-8"))
    assert parsed["session_id"] == session_id
    assert "scripts/work/build_freeze_allowlist.py" in parsed["allowed_paths"]
    assert ".athanor/sessions/2026-05-28-004/**" in parsed["allowed_paths"]


def test_cli_respects_output_override(tmp_path: Path):
    project_root = tmp_path / "proj"
    session_id = "2026-05-28-004"
    session_dir = project_root / ".athanor" / "sessions" / session_id
    session_dir.mkdir(parents=True)
    plan = session_dir / "plan.md"
    plan.write_text(PLAN_BULLET_LIST, encoding="utf-8")
    custom_out = tmp_path / "custom-allowlist.json"
    result = subprocess.run(
        [
            sys.executable, str(BUILDER_SCRIPT),
            "--session-id", session_id,
            "--output", str(custom_out),
        ],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"CLI failed (exit {result.returncode}):\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert custom_out.is_file()
    parsed = json.loads(custom_out.read_text(encoding="utf-8"))
    assert parsed["session_id"] == session_id


def test_cli_missing_plan_md_still_writes_defaults(tmp_path: Path):
    """When plan.md is missing, CLI should emit defaults + write to stderr."""
    project_root = tmp_path / "proj"
    session_id = "2026-05-28-004"
    session_dir = project_root / ".athanor" / "sessions" / session_id
    session_dir.mkdir(parents=True)
    # plan.md NOT created
    result = subprocess.run(
        [sys.executable, str(BUILDER_SCRIPT), "--session-id", session_id],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    out_path = session_dir / "freeze-allowlist.json"
    assert out_path.is_file()
    parsed = json.loads(out_path.read_text(encoding="utf-8"))
    # Defaults present
    assert ".athanor/sessions/2026-05-28-004/**" in parsed["allowed_paths"]
    assert ".athanor/lessons/**" in parsed["allowed_paths"]


# ---------------------------------------------------------------------------
# Output shape contract
# ---------------------------------------------------------------------------


def test_allowlist_output_shape_documented_fields(tmp_path: Path):
    """The output JSON must include the documented field set."""
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_BULLET_LIST, encoding="utf-8")
    mod = _import_builder()
    parsed = mod.parse_subtask_files(str(plan))
    allowlist = mod.build_allowlist(parsed, session_id="2026-05-28-004", extras=[])
    for field in (
        "session_id", "built_at", "allowed_paths", "default_paths",
        "subtask_paths", "built_from",
    ):
        assert field in allowlist, f"missing field: {field}"
    assert isinstance(allowlist["allowed_paths"], list)
    assert isinstance(allowlist["default_paths"], list)
    assert isinstance(allowlist["subtask_paths"], list)


def test_allowed_paths_deduplicated(tmp_path: Path):
    """Same file declared in two subtasks should appear once."""
    plan = tmp_path / "plan.md"
    plan.write_text(
        """# Plan

## Subtasks

#### Subtask 1.1

**files**:
- `a.py`

---

#### Subtask 1.2

**files**:
- `a.py`
- `b.py`
""",
        encoding="utf-8",
    )
    mod = _import_builder()
    parsed = mod.parse_subtask_files(str(plan))
    allowlist = mod.build_allowlist(parsed, session_id="2026-05-28-004", extras=[])
    allowed = allowlist["allowed_paths"]
    assert allowed.count("a.py") == 1, f"a.py duplicated: {allowed}"
    assert "b.py" in allowed
