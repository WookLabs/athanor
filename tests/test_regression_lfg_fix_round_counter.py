"""Regression — /athanor:lfg Step 3/8 fix-round counter CLI exit-code contract.

Gap under lock (the T1-2 gap)
-----------------------------
`skills/lfg/SKILL.md` Step 3 (review-fix) + Step 8 (CI-fix) state the fix-round
limit is *"prose guidance for the leader; there is no programmatic counter."*
This single-cycle lfg loop has no counter — pure prose, no exit code the leader
can branch on (the documented T1-2 hole; cf. the lfg merge-readiness gate which
is the same advisory class).

`scripts/loops/lfg_fix_round_counter.py` is the small, single-purpose CLI that
closes it (Key Decision 3, labeled ADVISORY — leader-prose-bound; no
PreToolUse/Stop hook forces the leader to branch). It maintains
`.athanor/sessions/<id>/lfg-fix-rounds.json` and provides:

  * `bump --session <dir> --loop review|ci` — atomic read-increment-write
    (temp-then-rename, mirroring `goal_loop_controller.write_loop_state_atomic`);
    prints the new count; **exit 0 while `< max_rounds`, exit 3 when the bump
    reaches/exceeds `max_rounds`** (= "stop iterating", the cap signal).
  * `read --session <dir>` — prints the JSON state.

Fail-loud contract (Risk R7): malformed `lfg-fix-rounds.json` → **exit 2 +
stderr, and the counter is NEVER silently reset** (a silent reset would hide a
stuck loop, violating fail-loud). Deliberately NOT coupled to
`goal_loop_controller.py` — lfg is single-cycle (no `goal_id`/`cycle_state`/
`current_cycle`); folding it into the durable `LoopState` would be a category
error.

These tests are RED before Phase 3 (the CLI does not exist). Invocation style
mirrors the CLI/exit-code structure of the durable-loop CLI tests.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CLI = REPO_ROOT / "scripts" / "loops" / "lfg_fix_round_counter.py"
STATE_NAME = "lfg-fix-rounds.json"


def _session_dir(tmp_path: Path) -> Path:
    """A canonical-looking session dir under a tmp .athanor tree."""
    sdir = tmp_path / ".athanor" / "sessions" / "2026-06-25-001"
    sdir.mkdir(parents=True)
    return sdir


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


def _state_path(session: Path) -> Path:
    return session / STATE_NAME


# ---------------------------------------------------------------------------
# Smoke
# ---------------------------------------------------------------------------
def test_cli_file_exists():
    assert CLI.is_file(), f"CLI not at {CLI}"


# ---------------------------------------------------------------------------
# 1. bump exits 0 on rounds 1..(cap-1), exit 3 at round == cap (max_rounds=3).
# ---------------------------------------------------------------------------
def test_bump_exit_codes_review_loop(tmp_path):
    session = _session_dir(tmp_path)
    # Round 1 → count 1 < 3 → exit 0
    p1 = _run("bump", "--session", str(session), "--loop", "review")
    assert p1.returncode == 0, (
        f"round 1 must exit 0 (under cap); got {p1.returncode}, "
        f"stdout={p1.stdout!r} stderr={p1.stderr!r}"
    )
    assert "1" in p1.stdout, f"bump must print the new count (1); got {p1.stdout!r}"

    # Round 2 → count 2 < 3 → exit 0
    p2 = _run("bump", "--session", str(session), "--loop", "review")
    assert p2.returncode == 0, (
        f"round 2 must exit 0 (under cap); got {p2.returncode}, stderr={p2.stderr!r}"
    )
    assert "2" in p2.stdout, f"bump must print the new count (2); got {p2.stdout!r}"

    # Round 3 → count 3 == max_rounds → exit 3 (the cap signal "stop iterating")
    p3 = _run("bump", "--session", str(session), "--loop", "review")
    assert p3.returncode == 3, (
        f"round 3 (== max_rounds=3) must exit 3 (cap reached → stop iterating); "
        f"got {p3.returncode}, stdout={p3.stdout!r} stderr={p3.stderr!r}"
    )
    assert "3" in p3.stdout, f"bump must still print the new count (3); got {p3.stdout!r}"


def test_bump_beyond_cap_still_exit_3(tmp_path):
    """A bump that pushes the count ABOVE max_rounds also exits 3 (reaches/
    exceeds — the contract is >=, never an off-by-one that releases at cap+1)."""
    session = _session_dir(tmp_path)
    for _ in range(3):
        _run("bump", "--session", str(session), "--loop", "review")
    p4 = _run("bump", "--session", str(session), "--loop", "review")
    assert p4.returncode == 3, (
        f"a 4th bump (count 4 > max_rounds=3) must still exit 3, never release; "
        f"got {p4.returncode}, stdout={p4.stdout!r}"
    )


# ---------------------------------------------------------------------------
# 2. review and ci loops are independent counters.
# ---------------------------------------------------------------------------
def test_review_and_ci_loops_independent(tmp_path):
    session = _session_dir(tmp_path)
    # Bump review twice; ci must remain at 0 until bumped.
    _run("bump", "--session", str(session), "--loop", "review")
    _run("bump", "--session", str(session), "--loop", "review")
    pc = _run("bump", "--session", str(session), "--loop", "ci")
    assert pc.returncode == 0, (
        f"first ci bump must exit 0 even after two review bumps (independent "
        f"counters); got {pc.returncode}, stdout={pc.stdout!r}"
    )
    data = json.loads(_state_path(session).read_text(encoding="utf-8"))
    assert data["review_fix_rounds"] == 2, (
        f"review counter must be 2; got {data!r}"
    )
    assert data["ci_fix_rounds"] == 1, f"ci counter must be 1; got {data!r}"

    # Push review to cap → exit 3; ci stays under cap → exit 0 (independence
    # holds at the cap boundary too).
    _run("bump", "--session", str(session), "--loop", "review")  # review → 3
    pr = _run("bump", "--session", str(session), "--loop", "review")  # review still capped
    assert pr.returncode == 3, f"review at cap must exit 3; got {pr.returncode}"
    pc2 = _run("bump", "--session", str(session), "--loop", "ci")  # ci → 2 < 3
    assert pc2.returncode == 0, (
        f"ci must still exit 0 while review is capped (independent); got "
        f"{pc2.returncode}, stdout={pc2.stdout!r}"
    )


# ---------------------------------------------------------------------------
# 3. atomic round-trip: read reflects what bump wrote.
# ---------------------------------------------------------------------------
def test_read_reflects_bump_atomic_round_trip(tmp_path):
    session = _session_dir(tmp_path)
    _run("bump", "--session", str(session), "--loop", "review")
    _run("bump", "--session", str(session), "--loop", "ci")
    pr = _run("read", "--session", str(session))
    assert pr.returncode == 0, (
        f"read must exit 0 on a valid state; got {pr.returncode}, stderr={pr.stderr!r}"
    )
    data = json.loads(pr.stdout)
    assert data["review_fix_rounds"] == 1, f"read review count wrong: {data!r}"
    assert data["ci_fix_rounds"] == 1, f"read ci count wrong: {data!r}"
    assert data["max_rounds"] == 3, f"default max_rounds must be 3; got {data!r}"
    assert "schema_version" in data, f"state must carry schema_version; got {data!r}"


def test_read_before_any_bump_reports_zeroes(tmp_path):
    """`read` on a session with no state file yet must report a fresh
    zero-count state (exit 0), not crash — the leader may read before the first
    fix round."""
    session = _session_dir(tmp_path)
    pr = _run("read", "--session", str(session))
    assert pr.returncode == 0, (
        f"read on a fresh session must exit 0; got {pr.returncode}, "
        f"stderr={pr.stderr!r}"
    )
    data = json.loads(pr.stdout)
    assert data["review_fix_rounds"] == 0 and data["ci_fix_rounds"] == 0, (
        f"fresh read must report zero counts; got {data!r}"
    )


# ---------------------------------------------------------------------------
# 4. FAIL-LOUD: malformed JSON → exit 2 + stderr, counter NOT reset.
# ---------------------------------------------------------------------------
def test_malformed_json_bump_exit_2_no_reset(tmp_path):
    session = _session_dir(tmp_path)
    state = _state_path(session)
    state.write_text("{ this is not valid json ", encoding="utf-8")
    p = _run("bump", "--session", str(session), "--loop", "review")
    assert p.returncode == 2, (
        f"malformed lfg-fix-rounds.json on bump must exit 2 (fail-loud); got "
        f"{p.returncode}, stdout={p.stdout!r} stderr={p.stderr!r}"
    )
    assert p.stderr.strip(), "exit 2 must carry a stderr diagnostic (fail-loud)."
    # NEVER silently reset — the malformed bytes must remain untouched so a
    # stuck/corrupt loop stays visible (a silent reset would hide it).
    assert state.read_text(encoding="utf-8") == "{ this is not valid json ", (
        "malformed state must NOT be silently reset/overwritten — fail-loud "
        "keeps a stuck loop visible."
    )


def test_malformed_json_read_exit_2_no_reset(tmp_path):
    session = _session_dir(tmp_path)
    state = _state_path(session)
    state.write_text("not json at all", encoding="utf-8")
    p = _run("read", "--session", str(session))
    assert p.returncode == 2, (
        f"malformed lfg-fix-rounds.json on read must exit 2 (fail-loud); got "
        f"{p.returncode}, stderr={p.stderr!r}"
    )
    assert p.stderr.strip(), "exit 2 must carry a stderr diagnostic."
    assert state.read_text(encoding="utf-8") == "not json at all", (
        "read must never rewrite the malformed state."
    )


# ---------------------------------------------------------------------------
# 5. Bad arguments fail loudly (not a silent 0).
# ---------------------------------------------------------------------------
def test_invalid_loop_value_rejected(tmp_path):
    session = _session_dir(tmp_path)
    p = _run("bump", "--session", str(session), "--loop", "bogus")
    assert p.returncode != 0, (
        f"--loop bogus must be rejected with a non-zero exit; got {p.returncode}"
    )
    # Must NOT have created a state file as a side effect of a rejected arg.
    assert not _state_path(session).exists(), (
        "a rejected --loop value must not create a state file."
    )


def test_missing_session_arg_rejected():
    p = _run("bump", "--loop", "review")
    assert p.returncode != 0, (
        f"missing --session must be rejected with a non-zero exit; got {p.returncode}"
    )
