"""Regression tests for scripts/hooks/hook_state.py — v0.7.9 U1.

Covers nonce-state lifecycle (write/read/freshness/delete) + stop-counter
state (read/write/reset) + session-ID path-traversal protection +
atomic-write resilience.

Plan reference: docs/plans/2026-05-18-002-feat-v0.7.9-stop-hook-hardening-plan.md §U1.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts" / "hooks"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import hook_state  # noqa: E402


# --- Session-ID validation -------------------------------------------------


def test_session_id_validation_accepts_alphanumeric():
    assert hook_state._validate_session_id("abc123")
    assert hook_state._validate_session_id("session_2026-05-18-001")
    assert hook_state._validate_session_id("a")
    assert hook_state._validate_session_id("A_B-1")


def test_session_id_validation_rejects_path_traversal():
    assert not hook_state._validate_session_id("../etc/passwd")
    assert not hook_state._validate_session_id("a/b")
    assert not hook_state._validate_session_id("a\\b")
    assert not hook_state._validate_session_id("./x")


def test_session_id_validation_rejects_empty_and_oversized():
    assert not hook_state._validate_session_id("")
    assert not hook_state._validate_session_id("a" * 129)


def test_session_id_validation_rejects_non_string():
    assert not hook_state._validate_session_id(None)  # type: ignore[arg-type]
    assert not hook_state._validate_session_id(123)  # type: ignore[arg-type]


def test_session_id_validation_rejects_shell_metacharacters():
    assert not hook_state._validate_session_id("a;b")
    assert not hook_state._validate_session_id("a b")
    assert not hook_state._validate_session_id("a$b")
    assert not hook_state._validate_session_id("a|b")


# --- get_state_dir --------------------------------------------------------


def test_get_state_dir_creates_directory(tmp_path):
    (tmp_path / ".athanor").mkdir()
    state_dir = hook_state.get_state_dir("s1", project_root=tmp_path)
    assert state_dir is not None
    assert state_dir == tmp_path / ".athanor" / "sessions" / "s1" / ".hook-state"
    assert state_dir.is_dir()


def test_get_state_dir_returns_none_for_invalid_session(tmp_path):
    (tmp_path / ".athanor").mkdir()
    assert hook_state.get_state_dir("../escape", project_root=tmp_path) is None


# --- Nonce state ----------------------------------------------------------


def test_nonce_state_happy_path(tmp_path):
    (tmp_path / ".athanor").mkdir()
    assert hook_state.write_nonce_state(
        "s1", "deadbeef" * 4, "abcd1234" * 8, project_root=tmp_path
    )
    state = hook_state.read_nonce_state("s1", project_root=tmp_path)
    assert state is not None
    assert state["nonce"] == "deadbeef" * 4
    assert state["body_hash"] == "abcd1234" * 8
    assert isinstance(state["timestamp"], int)


def test_nonce_state_read_missing_returns_none(tmp_path):
    (tmp_path / ".athanor").mkdir()
    assert hook_state.read_nonce_state("nonexistent", project_root=tmp_path) is None


def test_nonce_state_corrupt_json_returns_none(tmp_path):
    (tmp_path / ".athanor").mkdir()
    state_dir = hook_state.get_state_dir("s1", project_root=tmp_path)
    (state_dir / "nonce.json").write_text("{not valid json", encoding="utf-8")
    assert hook_state.read_nonce_state("s1", project_root=tmp_path) is None


def test_nonce_state_non_dict_returns_none(tmp_path):
    (tmp_path / ".athanor").mkdir()
    state_dir = hook_state.get_state_dir("s1", project_root=tmp_path)
    (state_dir / "nonce.json").write_text('["array", "not", "dict"]', encoding="utf-8")
    assert hook_state.read_nonce_state("s1", project_root=tmp_path) is None


def test_nonce_state_delete_removes_file(tmp_path):
    (tmp_path / ".athanor").mkdir()
    hook_state.write_nonce_state("s1", "x" * 32, "y" * 64, project_root=tmp_path)
    hook_state.delete_nonce_state("s1", project_root=tmp_path)
    assert hook_state.read_nonce_state("s1", project_root=tmp_path) is None


def test_nonce_state_delete_missing_is_silent(tmp_path):
    (tmp_path / ".athanor").mkdir()
    hook_state.delete_nonce_state("s1", project_root=tmp_path)


def test_is_nonce_fresh_within_ttl():
    state = {"nonce": "x", "body_hash": "y", "timestamp": int(time.time())}
    assert hook_state.is_nonce_fresh(state)


def test_is_nonce_fresh_outside_ttl():
    stale = {"nonce": "x", "body_hash": "y", "timestamp": int(time.time()) - 999}
    assert not hook_state.is_nonce_fresh(stale)


def test_is_nonce_fresh_future_timestamp_rejected():
    future = {"nonce": "x", "body_hash": "y", "timestamp": int(time.time()) + 999}
    assert not hook_state.is_nonce_fresh(future)


def test_is_nonce_fresh_missing_timestamp():
    assert not hook_state.is_nonce_fresh({"nonce": "x"})


def test_is_nonce_fresh_non_numeric_timestamp():
    assert not hook_state.is_nonce_fresh({"timestamp": "yesterday"})


# --- Stop-counter state ---------------------------------------------------


def test_stop_counter_starts_at_zero(tmp_path):
    (tmp_path / ".athanor").mkdir()
    assert hook_state.read_stop_counter("s1", project_root=tmp_path) == 0


def test_stop_counter_write_and_read(tmp_path):
    (tmp_path / ".athanor").mkdir()
    hook_state.write_stop_counter("s1", 2, project_root=tmp_path)
    assert hook_state.read_stop_counter("s1", project_root=tmp_path) == 2


def test_stop_counter_reset(tmp_path):
    (tmp_path / ".athanor").mkdir()
    hook_state.write_stop_counter("s1", 5, project_root=tmp_path)
    hook_state.reset_stop_counter("s1", project_root=tmp_path)
    assert hook_state.read_stop_counter("s1", project_root=tmp_path) == 0


def test_stop_counter_negative_clamped_to_zero(tmp_path):
    (tmp_path / ".athanor").mkdir()
    hook_state.write_stop_counter("s1", -5, project_root=tmp_path)
    assert hook_state.read_stop_counter("s1", project_root=tmp_path) == 0


def test_stop_counter_corrupt_file_returns_zero(tmp_path):
    (tmp_path / ".athanor").mkdir()
    state_dir = hook_state.get_state_dir("s1", project_root=tmp_path)
    (state_dir / "stop-counter.json").write_text("garbage", encoding="utf-8")
    assert hook_state.read_stop_counter("s1", project_root=tmp_path) == 0


def test_stop_counter_per_session_isolation(tmp_path):
    """Different session IDs have independent counters."""
    (tmp_path / ".athanor").mkdir()
    hook_state.write_stop_counter("s1", 3, project_root=tmp_path)
    hook_state.write_stop_counter("s2", 7, project_root=tmp_path)
    assert hook_state.read_stop_counter("s1", project_root=tmp_path) == 3
    assert hook_state.read_stop_counter("s2", project_root=tmp_path) == 7


# --- Atomic write resilience ---------------------------------------------


def test_atomic_write_overwrites_existing(tmp_path):
    """Writing twice replaces the file (atomic via os.replace)."""
    (tmp_path / ".athanor").mkdir()
    hook_state.write_nonce_state("s1", "nonce1", "hash1", project_root=tmp_path)
    hook_state.write_nonce_state("s1", "nonce2", "hash2", project_root=tmp_path)
    state = hook_state.read_nonce_state("s1", project_root=tmp_path)
    assert state["nonce"] == "nonce2"
    assert state["body_hash"] == "hash2"


def test_atomic_write_no_partial_files_left_behind(tmp_path):
    """After successful writes, no .tmp- prefixed files remain in state dir."""
    (tmp_path / ".athanor").mkdir()
    hook_state.write_nonce_state("s1", "x" * 32, "y" * 64, project_root=tmp_path)
    state_dir = hook_state.get_state_dir("s1", project_root=tmp_path)
    leftovers = [f for f in state_dir.iterdir() if f.name.startswith(".tmp-")]
    assert not leftovers, f"Found leftover tempfiles: {leftovers}"
