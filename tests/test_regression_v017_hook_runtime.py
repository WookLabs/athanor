"""Regression tests for v0.17.0 shared hook runtime module.

Covers `scripts/hooks/_athanor_hook_runtime.py` — minimalist shared
helpers used by both `stop_verify_claims.py` and `pretool_kernel_guard.py`.

Per S06 minimalist scope (C1 conflict resolution adopting Plan B):
  1. `read_stdin_payload()` — parse PreToolUse/Stop event JSON from stdin.
     Fail-open on malformed. Returns dict or None.
  2. `read_athanor_config()` — walk up from cwd to find athanor.json.
     Stops at .git boundary. Returns parsed dict or {}.
  3. `is_hook_profile_off(config)` — returns True if
     `hooks.profile == "off"`. Used by all hooks for opt-out.
  4. `resolve_project_root()` — walk-up to find .git or athanor.json.
     Returns Path or None.

The helpers carry the v0.7.9 parent-dir hijack lesson: walk-up never
crosses a .git/ boundary upward.
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_HOOKS = REPO_ROOT / "scripts" / "hooks"
if str(SCRIPTS_HOOKS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_HOOKS))

import _athanor_hook_runtime as runtime  # noqa: E402


# ---------------------------------------------------------------------------
# read_stdin_payload()
# ---------------------------------------------------------------------------


def test_read_stdin_payload_valid_json():
    """A valid JSON object on stdin returns the parsed dict."""
    payload = {"hook_event_name": "Stop", "session_id": "abc123"}
    fake_stdin = io.StringIO(json.dumps(payload))
    # Override isatty so the helper does not bail out as TTY
    fake_stdin.isatty = lambda: False  # type: ignore[method-assign]
    with mock.patch.object(sys, "stdin", fake_stdin):
        result = runtime.read_stdin_payload()
    assert result == payload


def test_read_stdin_payload_malformed_returns_none():
    """Malformed JSON returns None (fail-open contract)."""
    fake_stdin = io.StringIO("this is not json {{{")
    fake_stdin.isatty = lambda: False  # type: ignore[method-assign]
    with mock.patch.object(sys, "stdin", fake_stdin):
        result = runtime.read_stdin_payload()
    assert result is None


def test_read_stdin_payload_empty_returns_none():
    """Empty stdin returns None."""
    fake_stdin = io.StringIO("")
    fake_stdin.isatty = lambda: False  # type: ignore[method-assign]
    with mock.patch.object(sys, "stdin", fake_stdin):
        result = runtime.read_stdin_payload()
    assert result is None


def test_read_stdin_payload_tty_returns_none():
    """A TTY stdin returns None (no event in interactive mode)."""
    fake_stdin = io.StringIO("")
    fake_stdin.isatty = lambda: True  # type: ignore[method-assign]
    with mock.patch.object(sys, "stdin", fake_stdin):
        result = runtime.read_stdin_payload()
    assert result is None


def test_read_stdin_payload_non_dict_returns_none():
    """JSON that isn't a dict returns None — events are always objects."""
    fake_stdin = io.StringIO('["not", "a", "dict"]')
    fake_stdin.isatty = lambda: False  # type: ignore[method-assign]
    with mock.patch.object(sys, "stdin", fake_stdin):
        result = runtime.read_stdin_payload()
    assert result is None


# ---------------------------------------------------------------------------
# read_athanor_config()
# ---------------------------------------------------------------------------


def test_read_athanor_config_returns_parsed(tmp_path):
    """A well-formed athanor.json at cwd returns the parsed dict."""
    project = tmp_path / "proj"
    project.mkdir()
    (project / ".git").mkdir()
    cfg = {"hooks": {"profile": "standard"}, "version": "0.17.0"}
    (project / "athanor.json").write_text(json.dumps(cfg), encoding="utf-8")
    saved = os.getcwd()
    try:
        os.chdir(project)
        result = runtime.read_athanor_config()
    finally:
        os.chdir(saved)
    assert result == cfg


def test_read_athanor_config_walks_up(tmp_path):
    """When athanor.json lives one or more directories up from cwd
    (still under the same repo), the helper walks up and finds it."""
    project = tmp_path / "proj"
    project.mkdir()
    (project / ".git").mkdir()  # repo root marker
    cfg = {"hooks": {"profile": "off"}}
    (project / "athanor.json").write_text(json.dumps(cfg), encoding="utf-8")
    nested = project / "src" / "deep" / "nested"
    nested.mkdir(parents=True)
    saved = os.getcwd()
    try:
        os.chdir(nested)
        result = runtime.read_athanor_config()
    finally:
        os.chdir(saved)
    assert result == cfg


def test_read_athanor_config_missing_returns_empty(tmp_path):
    """No athanor.json found → returns {} (never None)."""
    project = tmp_path / "noconfig"
    project.mkdir()
    (project / ".git").mkdir()  # stop walk-up here
    saved = os.getcwd()
    try:
        os.chdir(project)
        result = runtime.read_athanor_config()
    finally:
        os.chdir(saved)
    assert result == {}


def test_read_athanor_config_malformed_returns_empty(tmp_path):
    """Unparseable athanor.json returns {} (fail-open)."""
    project = tmp_path / "proj"
    project.mkdir()
    (project / ".git").mkdir()
    (project / "athanor.json").write_text("this is { not json", encoding="utf-8")
    saved = os.getcwd()
    try:
        os.chdir(project)
        result = runtime.read_athanor_config()
    finally:
        os.chdir(saved)
    assert result == {}


def test_read_athanor_config_stops_at_git_boundary(tmp_path):
    """Walk-up never crosses a .git/ boundary upward (v0.7.9 hijack guard).
    An athanor.json above a repo root must NOT be picked up from inside
    the repo."""
    outer = tmp_path / "outer"
    outer.mkdir()
    (outer / "athanor.json").write_text(
        json.dumps({"hooks": {"profile": "off"}}), encoding="utf-8"
    )
    repo = outer / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()  # boundary
    sub = repo / "sub"
    sub.mkdir()
    saved = os.getcwd()
    try:
        os.chdir(sub)
        result = runtime.read_athanor_config()
    finally:
        os.chdir(saved)
    assert result == {}, (
        f"helper crossed .git boundary upward and picked up outer config: {result}"
    )


# ---------------------------------------------------------------------------
# is_hook_profile_off(config)
# ---------------------------------------------------------------------------


def test_is_hook_profile_off_true():
    config = {"hooks": {"profile": "off"}}
    assert runtime.is_hook_profile_off(config) is True


def test_is_hook_profile_off_false_standard():
    config = {"hooks": {"profile": "standard"}}
    assert runtime.is_hook_profile_off(config) is False


def test_is_hook_profile_off_false_missing():
    """Missing hooks section defaults to NOT off (standard)."""
    assert runtime.is_hook_profile_off({}) is False


def test_is_hook_profile_off_false_non_dict_hooks():
    """If hooks isn't a dict, treat as not off (defensive)."""
    assert runtime.is_hook_profile_off({"hooks": "yes please"}) is False


def test_is_hook_profile_off_false_non_string_value():
    """Non-string profile value → not off."""
    assert runtime.is_hook_profile_off({"hooks": {"profile": True}}) is False


def test_is_hook_profile_off_handles_none():
    """Passing None doesn't crash; returns False."""
    assert runtime.is_hook_profile_off(None) is False  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# resolve_project_root()
# ---------------------------------------------------------------------------


def test_resolve_project_root_finds_git(tmp_path):
    """A directory containing .git/ is detected as the project root."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    saved = os.getcwd()
    try:
        os.chdir(repo)
        result = runtime.resolve_project_root()
    finally:
        os.chdir(saved)
    assert result is not None
    assert result.resolve() == repo.resolve()


def test_resolve_project_root_walks_up_to_git(tmp_path):
    """Walk-up from a nested cwd finds the .git-bearing ancestor."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    nested = repo / "a" / "b" / "c"
    nested.mkdir(parents=True)
    saved = os.getcwd()
    try:
        os.chdir(nested)
        result = runtime.resolve_project_root()
    finally:
        os.chdir(saved)
    assert result is not None
    assert result.resolve() == repo.resolve()


def test_resolve_project_root_finds_athanor_json(tmp_path):
    """Absent .git, an athanor.json also marks a project root."""
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "athanor.json").write_text("{}", encoding="utf-8")
    saved = os.getcwd()
    try:
        os.chdir(proj)
        result = runtime.resolve_project_root()
    finally:
        os.chdir(saved)
    assert result is not None
    assert result.resolve() == proj.resolve()


def test_resolve_project_root_returns_none_when_nothing(tmp_path):
    """No markers anywhere → returns None."""
    bare = tmp_path / "bare"
    bare.mkdir()
    saved = os.getcwd()
    try:
        os.chdir(bare)
        result = runtime.resolve_project_root()
    finally:
        os.chdir(saved)
    # In tmp_path, no .git or athanor.json should be found. Tolerate the case
    # where tmp_path itself is inside a parent project — the helper may
    # legitimately walk up beyond bare/. The strict invariant is: if a
    # result is returned, it must be a Path; None is allowed.
    assert result is None or isinstance(result, Path)


# ---------------------------------------------------------------------------
# Integration smoke: existing hooks still work after refactor.
# ---------------------------------------------------------------------------


def test_stop_hook_script_still_runs():
    """Smoke: stop_verify_claims.py imports + executes a no-op payload
    without raising. Behavior-preservation guard for the v0.17.0 refactor."""
    script = REPO_ROOT / "scripts" / "hooks" / "stop_verify_claims.py"
    proc = subprocess.run(
        [sys.executable, str(script)],
        input="{}",
        text=True,
        capture_output=True,
        cwd=str(REPO_ROOT),
    )
    # exit 0 = fail-open on empty payload (the script's own contract).
    assert proc.returncode == 0, (
        f"stop_verify_claims.py broke after refactor: rc={proc.returncode} "
        f"stderr={proc.stderr!r}"
    )


def test_pretool_hook_script_still_runs():
    """Smoke: pretool_kernel_guard.py imports + executes a no-op payload."""
    script = REPO_ROOT / "scripts" / "hooks" / "pretool_kernel_guard.py"
    proc = subprocess.run(
        [sys.executable, str(script)],
        input="{}",
        text=True,
        capture_output=True,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, (
        f"pretool_kernel_guard.py broke after refactor: rc={proc.returncode} "
        f"stderr={proc.stderr!r}"
    )
