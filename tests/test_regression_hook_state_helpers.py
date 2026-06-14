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
    (tmp_path / "athanor.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".athanor").mkdir()
    state_dir = hook_state.get_state_dir("s1", project_root=tmp_path)
    assert state_dir is not None
    assert state_dir == tmp_path / ".athanor" / "sessions" / "s1" / ".hook-state"
    assert state_dir.is_dir()


def test_get_state_dir_returns_none_for_invalid_session(tmp_path):
    (tmp_path / "athanor.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".athanor").mkdir()
    assert hook_state.get_state_dir("../escape", project_root=tmp_path) is None


# --- get_state_dir opt-in gate + create=False (Phase 4, S16/S18) ----------
#
# Phase 4 makes state-dir creation OPT-IN: a repo with no `athanor.json`
# never gets a `.athanor/` tree materialized as a hook side effect (closes
# the P15 `/tmp/.athanor` debris incident). Read paths are create-free via
# `create=False`.


def test_get_state_dir_no_athanor_json_returns_none_and_creates_nothing(tmp_path):
    """Opt-in gate (S16/S18 (a)): no athanor.json → None AND no .athanor."""
    # Deliberately NO athanor.json — this is the opted-OUT scenario.
    assert hook_state.get_state_dir("s1", project_root=tmp_path) is None
    assert not (tmp_path / ".athanor").exists(), (
        "get_state_dir must NOT create .athanor/ when the repo has not "
        "opted in via athanor.json (P15 debris regression)"
    )


def test_get_state_dir_with_athanor_json_creates_and_returns_path(tmp_path):
    """S16 AC: athanor.json present + create=True → dir created, path returned.

    Doubles as the positive control for the .git-boundary test below:
    athanor.json AT the repo root IS honored.
    """
    (tmp_path / "athanor.json").write_text("{}", encoding="utf-8")
    state_dir = hook_state.get_state_dir("s1", project_root=tmp_path, create=True)
    assert state_dir is not None
    assert state_dir == tmp_path / ".athanor" / "sessions" / "s1" / ".hook-state"
    assert state_dir.is_dir()


def test_get_state_dir_opt_in_stops_at_git_boundary(tmp_path):
    """Review finding R2 (A): _athanor_opt_in must NOT honor an athanor.json
    ABOVE a .git repo root from inside the repo (v0.7.9 parent-dir hijack
    guard). Untested direction — a regression here re-materializes the P15
    `/tmp/.athanor` debris incident.

    Mirrors test_read_athanor_config_stops_at_git_boundary in
    tests/test_regression_v017_hook_runtime.py for the hook_state copy of
    the walk-up.
    """
    outer = tmp_path
    (outer / "athanor.json").write_text("{}", encoding="utf-8")
    repo = outer / "repo"
    (repo / ".git").mkdir(parents=True)  # boundary

    result = hook_state.get_state_dir("2026-06-11-001", project_root=repo, create=True)

    assert result is None, (
        "opt-in crossed the .git boundary upward and honored the outer "
        f"athanor.json: {result}"
    )
    assert not (repo / ".athanor").exists(), (
        "no .athanor/ may be materialized inside the repo when only an "
        "ancestor (above .git) carries athanor.json"
    )
    assert not (outer / ".athanor").exists(), (
        "no .athanor/ may be materialized in the outer dir either"
    )


def test_get_state_dir_create_false_returns_none_when_absent(tmp_path):
    """S16 AC: create=False returns None when the dir does not yet exist
    (even in an opted-in repo) and creates nothing."""
    (tmp_path / "athanor.json").write_text("{}", encoding="utf-8")
    assert hook_state.get_state_dir("s1", project_root=tmp_path, create=False) is None
    assert not (tmp_path / ".athanor" / "sessions" / "s1" / ".hook-state").exists(), (
        "create=False must not materialize the state dir"
    )


def test_get_state_dir_create_false_returns_path_when_present(tmp_path):
    """create=False returns the existing path without creating anything new."""
    (tmp_path / "athanor.json").write_text("{}", encoding="utf-8")
    created = hook_state.get_state_dir("s1", project_root=tmp_path, create=True)
    assert created is not None and created.is_dir()
    found = hook_state.get_state_dir("s1", project_root=tmp_path, create=False)
    assert found == created
    assert found.is_dir()


def test_pure_read_in_opted_in_stateless_repo_creates_no_dir(tmp_path):
    """S18 (b): a pure read in an opted-in repo with no prior state returns
    empty/None and creates no `.hook-state` directory."""
    (tmp_path / "athanor.json").write_text("{}", encoding="utf-8")
    # Reads against a stateless (but opted-in) repo.
    assert hook_state.read_nonce_state("s1", project_root=tmp_path) is None
    assert hook_state.read_stop_counter("s1", project_root=tmp_path) == 0
    assert hook_state.read_profile_snapshot("s1", project_root=tmp_path) is None
    assert not (tmp_path / ".athanor" / "sessions" / "s1" / ".hook-state").exists(), (
        "read helpers must use create=False — no dir should be materialized "
        "by a pure read"
    )


def test_pure_read_in_opted_out_repo_creates_no_dir(tmp_path):
    """A pure read in a repo with NO athanor.json returns empty/None and
    creates no .athanor tree (fail-open, opt-in gate)."""
    assert hook_state.read_nonce_state("s1", project_root=tmp_path) is None
    assert hook_state.read_stop_counter("s1", project_root=tmp_path) == 0
    assert not (tmp_path / ".athanor").exists()


def test_state_round_trips_in_opted_in_repo(tmp_path):
    """S18 (c): with athanor.json present, the state dir is created on write
    and state round-trips (write → read returns the written value)."""
    (tmp_path / "athanor.json").write_text("{}", encoding="utf-8")
    assert hook_state.write_stop_counter("s1", 4, project_root=tmp_path)
    assert hook_state.read_stop_counter("s1", project_root=tmp_path) == 4
    assert hook_state.write_nonce_state(
        "s1", "n" * 32, "h" * 64, project_root=tmp_path
    )
    state = hook_state.read_nonce_state("s1", project_root=tmp_path)
    assert state is not None and state["nonce"] == "n" * 32
    assert (tmp_path / ".athanor" / "sessions" / "s1" / ".hook-state").is_dir()


# --- Nonce state ----------------------------------------------------------


def test_nonce_state_happy_path(tmp_path):
    (tmp_path / "athanor.json").write_text("{}", encoding="utf-8")
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
    (tmp_path / "athanor.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".athanor").mkdir()
    assert hook_state.read_nonce_state("nonexistent", project_root=tmp_path) is None


def test_nonce_state_corrupt_json_returns_none(tmp_path):
    (tmp_path / "athanor.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".athanor").mkdir()
    state_dir = hook_state.get_state_dir("s1", project_root=tmp_path)
    (state_dir / "nonce.json").write_text("{not valid json", encoding="utf-8")
    assert hook_state.read_nonce_state("s1", project_root=tmp_path) is None


def test_nonce_state_non_dict_returns_none(tmp_path):
    (tmp_path / "athanor.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".athanor").mkdir()
    state_dir = hook_state.get_state_dir("s1", project_root=tmp_path)
    (state_dir / "nonce.json").write_text('["array", "not", "dict"]', encoding="utf-8")
    assert hook_state.read_nonce_state("s1", project_root=tmp_path) is None


def test_nonce_state_delete_removes_file(tmp_path):
    (tmp_path / "athanor.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".athanor").mkdir()
    hook_state.write_nonce_state("s1", "x" * 32, "y" * 64, project_root=tmp_path)
    hook_state.delete_nonce_state("s1", project_root=tmp_path)
    assert hook_state.read_nonce_state("s1", project_root=tmp_path) is None


def test_nonce_state_delete_missing_is_silent(tmp_path):
    (tmp_path / "athanor.json").write_text("{}", encoding="utf-8")
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
    (tmp_path / "athanor.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".athanor").mkdir()
    assert hook_state.read_stop_counter("s1", project_root=tmp_path) == 0


def test_stop_counter_write_and_read(tmp_path):
    (tmp_path / "athanor.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".athanor").mkdir()
    hook_state.write_stop_counter("s1", 2, project_root=tmp_path)
    assert hook_state.read_stop_counter("s1", project_root=tmp_path) == 2


def test_stop_counter_reset(tmp_path):
    (tmp_path / "athanor.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".athanor").mkdir()
    hook_state.write_stop_counter("s1", 5, project_root=tmp_path)
    hook_state.reset_stop_counter("s1", project_root=tmp_path)
    assert hook_state.read_stop_counter("s1", project_root=tmp_path) == 0


def test_stop_counter_negative_clamped_to_zero(tmp_path):
    (tmp_path / "athanor.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".athanor").mkdir()
    hook_state.write_stop_counter("s1", -5, project_root=tmp_path)
    assert hook_state.read_stop_counter("s1", project_root=tmp_path) == 0


def test_stop_counter_corrupt_file_returns_zero(tmp_path):
    (tmp_path / "athanor.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".athanor").mkdir()
    state_dir = hook_state.get_state_dir("s1", project_root=tmp_path)
    (state_dir / "stop-counter.json").write_text("garbage", encoding="utf-8")
    assert hook_state.read_stop_counter("s1", project_root=tmp_path) == 0


def test_stop_counter_per_session_isolation(tmp_path):
    """Different session IDs have independent counters."""
    (tmp_path / "athanor.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".athanor").mkdir()
    hook_state.write_stop_counter("s1", 3, project_root=tmp_path)
    hook_state.write_stop_counter("s2", 7, project_root=tmp_path)
    assert hook_state.read_stop_counter("s1", project_root=tmp_path) == 3
    assert hook_state.read_stop_counter("s2", project_root=tmp_path) == 7


# --- Atomic write resilience ---------------------------------------------


def test_atomic_write_overwrites_existing(tmp_path):
    """Writing twice replaces the file (atomic via os.replace)."""
    (tmp_path / "athanor.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".athanor").mkdir()
    hook_state.write_nonce_state("s1", "nonce1", "hash1", project_root=tmp_path)
    hook_state.write_nonce_state("s1", "nonce2", "hash2", project_root=tmp_path)
    state = hook_state.read_nonce_state("s1", project_root=tmp_path)
    assert state["nonce"] == "nonce2"
    assert state["body_hash"] == "hash2"


def test_atomic_write_no_partial_files_left_behind(tmp_path):
    """After successful writes, no .tmp- prefixed files remain in state dir."""
    (tmp_path / "athanor.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".athanor").mkdir()
    hook_state.write_nonce_state("s1", "x" * 32, "y" * 64, project_root=tmp_path)
    state_dir = hook_state.get_state_dir("s1", project_root=tmp_path)
    leftovers = [f for f in state_dir.iterdir() if f.name.startswith(".tmp-")]
    assert not leftovers, f"Found leftover tempfiles: {leftovers}"
