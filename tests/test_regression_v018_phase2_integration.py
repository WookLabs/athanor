"""Regression tests for v0.18.0 Subtask 2.4 — Phase 2 integration tests.

End-to-end integration tests that exercise the full Phase 2 stack
(`pretool_dispatcher.py` + `pretool_kernel_guard.py` + `freeze_guard.py`)
via subprocess invocation against a synthetic project directory.

Where the per-module unit tests (test_regression_v018_pretool_dispatcher.py
and test_regression_v018_freeze_guard.py) cover each layer in isolation,
this file ties them together: dispatcher subprocess reads a real
`athanor.json` + a real `.athanor/sessions/<id>/freeze-allowlist.json`
written to disk by the test, then feeds in a realistic PreToolUse payload
on stdin.

Acceptance criteria locked here (per Subtask 2.4 plan-of-record):
  - MUST: integration tests pass end-to-end via subprocess
  - MUST: kernel FIRST verified by ordering test (rm -rf / blocks even
    with freeze mode=session AND no allowlist on disk — kernel never
    falls through to freeze)
  - MUST: D2 residual verified (subprocess writes not blocked
    end-to-end through the dispatcher → freeze guard path)

Additional invariants covered:
  - mode="off" → kernel runs, freeze skipped (subprocess test)
  - mode="warn" → freeze logs to violations.jsonl but allows
  - mode="session" → freeze blocks Edit/Write/Bash patterns not in
    allowlist
  - Bash `> file` redirect end-to-end
  - `mv X Y` where Y outside allowlist → blocked end-to-end
  - v0.16.0 fail-CLOSED via dispatcher subprocess invocation
    (`rm -rf /` blocked without athanor.json on disk)
  - Allowlist read from `.athanor/sessions/<id>/freeze-allowlist.json`
    end-to-end (no in-process injection)

Uses `tmp_path` for isolated synthetic project roots and passes
`CLAUDE_PROJECT_DIR` so the dispatcher's runtime helper resolves config
+ allowlist against the test directory rather than the athanor repo.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DISPATCHER = REPO_ROOT / "scripts" / "hooks" / "pretool_dispatcher.py"


# ---------------------------------------------------------------------------
# Subprocess + fixture helpers
# ---------------------------------------------------------------------------


def _run(payload, *, cwd, env) -> tuple[int, str, str]:
    """Invoke dispatcher with payload on stdin against `cwd` + `env`."""
    if isinstance(payload, dict):
        stdin_data = json.dumps(payload)
    elif payload is None:
        stdin_data = ""
    else:
        stdin_data = payload
    proc = subprocess.run(
        [sys.executable, str(DISPATCHER)],
        input=stdin_data,
        text=True,
        capture_output=True,
        cwd=cwd,
        env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _bash(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def _file_tool(tool: str, path: str) -> dict:
    return {"tool_name": tool, "tool_input": {"file_path": path}}


def _setup_project(
    tmp_path: Path,
    *,
    freeze_mode: str = "off",
    profile: str = "standard",
    extra_paths: list[str] | None = None,
    session_id: str = "2026-05-29-001",
    allowlist_paths: list[str] | None = None,
    write_allowlist: bool = True,
) -> tuple[Path, dict, Path]:
    """Build a synthetic project: athanor.json + session dir + allowlist.

    Returns (project_root, env, session_dir).
    """
    cfg: dict = {"hooks": {"profile": profile}}
    if freeze_mode != "off" or extra_paths is not None:
        cfg["hooks"]["freeze"] = {"mode": freeze_mode}
        if extra_paths is not None:
            cfg["hooks"]["freeze"]["extraAllowedPaths"] = list(extra_paths)
    (tmp_path / "athanor.json").write_text(
        json.dumps(cfg), encoding="utf-8"
    )

    session_dir = tmp_path / ".athanor" / "sessions" / session_id
    session_dir.mkdir(parents=True)

    if write_allowlist:
        defaults = [f".athanor/sessions/{session_id}/**", ".athanor/lessons/**"]
        extras = list(allowlist_paths or [])
        allowlist = {
            "session_id": session_id,
            "built_at": "2026-05-29T00:00:00Z",
            "allowed_paths": defaults + extras,
            "default_paths": defaults,
            "subtask_paths": extras,
            "extras": [],
            "built_from": "plan.md",
        }
        (session_dir / "freeze-allowlist.json").write_text(
            json.dumps(allowlist, indent=2), encoding="utf-8"
        )

    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
    return tmp_path, env, session_dir


# ---------------------------------------------------------------------------
# Kernel FIRST ordering — integration smoke (M2.4-MUST)
# ---------------------------------------------------------------------------


def test_kernel_runs_first_even_when_freeze_session_mode(tmp_path):
    """Kernel guard FIRST: rm -rf / must block even with freeze.mode=session
    AND a fully built allowlist on disk. Verifies dispatcher does NOT
    consult freeze before kernel."""
    root, env, _ = _setup_project(
        tmp_path, freeze_mode="session", allowlist_paths=["src/foo.py"]
    )
    rc, _, err = _run(_bash("rm -rf /"), cwd=str(root), env=env)
    assert rc == 2, (
        f"kernel guard must run FIRST and block rm -rf / regardless of "
        f"freeze mode; got rc={rc} stderr={err!r}"
    )
    # Stderr should originate from kernel guard (destructive class), not
    # freeze guard. Both use the same "athanor (pretool guard)" prefix,
    # but the kernel message says "destructive command" and freeze says
    # "freeze: ... not in session allowlist".
    assert "destructive" in err.lower() or "BLOCKED" in err
    assert "freeze:" not in err, (
        f"freeze layer must NOT see kernel-class violations; got: {err!r}"
    )


def test_kernel_runs_first_even_without_allowlist_on_disk(tmp_path):
    """Kernel FIRST + no allowlist: dispatcher must not crash trying to
    load the missing allowlist before kernel decides. rm -rf / still
    blocks."""
    root, env, _ = _setup_project(
        tmp_path, freeze_mode="session", write_allowlist=False
    )
    rc, _, err = _run(_bash("rm -rf /"), cwd=str(root), env=env)
    assert rc == 2, (
        f"missing allowlist must not unblock the kernel guard; "
        f"got rc={rc} stderr={err!r}"
    )


# ---------------------------------------------------------------------------
# mode="off" → kernel runs, freeze skipped (M2.4)
# ---------------------------------------------------------------------------


def test_mode_off_kernel_still_runs(tmp_path):
    """freeze.mode=off (default): kernel guard still enforces."""
    root, env, _ = _setup_project(
        tmp_path, freeze_mode="off", write_allowlist=False
    )
    rc, _, _ = _run(_bash("rm -rf /"), cwd=str(root), env=env)
    assert rc == 2, "kernel must run even with freeze off"


def test_mode_off_arbitrary_write_allowed(tmp_path):
    """freeze.mode=off + benign Write to an arbitrary path → exit 0
    (freeze never consulted; allowlist need not exist)."""
    root, env, _ = _setup_project(
        tmp_path, freeze_mode="off", write_allowlist=False
    )
    rc, _, err = _run(
        _file_tool("Write", "src/anywhere/random.py"), cwd=str(root), env=env
    )
    assert rc == 0, (
        f"freeze off must allow arbitrary writes, got rc={rc} stderr={err!r}"
    )


# ---------------------------------------------------------------------------
# mode="session" → freeze blocks Edit/Write outside allowlist (M2.4)
# ---------------------------------------------------------------------------


def test_session_mode_blocks_edit_outside_allowlist(tmp_path):
    """End-to-end: dispatcher loads freeze-allowlist.json from session
    dir; Edit to a path NOT in it blocks."""
    root, env, _ = _setup_project(
        tmp_path,
        freeze_mode="session",
        allowlist_paths=["src/foo.py"],
    )
    rc, _, err = _run(
        _file_tool("Edit", "src/secret.py"), cwd=str(root), env=env
    )
    assert rc == 2, (
        f"freeze must block Edit outside allowlist end-to-end; "
        f"got rc={rc} stderr={err!r}"
    )
    assert "freeze:" in err or "freeze" in err.lower()
    assert "src/secret.py" in err


def test_session_mode_allows_edit_inside_allowlist(tmp_path):
    """End-to-end: Edit to a path IN the allowlist exits 0."""
    root, env, _ = _setup_project(
        tmp_path,
        freeze_mode="session",
        allowlist_paths=["src/foo.py"],
    )
    rc, _, err = _run(
        _file_tool("Edit", "src/foo.py"), cwd=str(root), env=env
    )
    assert rc == 0, (
        f"freeze must allow Edit to in-allowlist path; "
        f"got rc={rc} stderr={err!r}"
    )


def test_session_mode_blocks_write_outside_allowlist(tmp_path):
    root, env, _ = _setup_project(
        tmp_path,
        freeze_mode="session",
        allowlist_paths=["src/foo.py"],
    )
    rc, _, _ = _run(
        _file_tool("Write", "src/other.py"), cwd=str(root), env=env
    )
    assert rc == 2


def test_session_mode_allows_write_into_session_dir_via_default(tmp_path):
    """Default allowlist entry `.athanor/sessions/<id>/**` allows writes
    into the session dir even with no extra allowlist paths."""
    sid = "2026-05-29-001"
    root, env, _ = _setup_project(
        tmp_path, freeze_mode="session", session_id=sid, allowlist_paths=[]
    )
    rc, _, err = _run(
        _file_tool("Write", f".athanor/sessions/{sid}/work-log.md"),
        cwd=str(root), env=env,
    )
    assert rc == 0, (
        f"default session-dir glob must allow writes; "
        f"got rc={rc} stderr={err!r}"
    )


# ---------------------------------------------------------------------------
# Bash conservative pattern gating end-to-end (M2.4)
# ---------------------------------------------------------------------------


def test_bash_redirect_overwrite_blocked_end_to_end(tmp_path):
    """Bash `echo > file` where file outside allowlist → exit 2."""
    root, env, _ = _setup_project(
        tmp_path,
        freeze_mode="session",
        allowlist_paths=["src/foo.py"],
    )
    rc, _, err = _run(
        _bash("echo 'data' > src/secret.py"), cwd=str(root), env=env
    )
    assert rc == 2, (
        f"Bash redirect outside allowlist must block; "
        f"got rc={rc} stderr={err!r}"
    )


def test_bash_mv_dest_outside_allowlist_blocked_end_to_end(tmp_path):
    """`mv X Y` where Y outside allowlist → blocked."""
    root, env, _ = _setup_project(
        tmp_path,
        freeze_mode="session",
        allowlist_paths=["src/foo.py"],
    )
    rc, _, err = _run(
        _bash("mv src/foo.py src/secret.py"), cwd=str(root), env=env
    )
    assert rc == 2, (
        f"mv to outside-allowlist destination must block; "
        f"got rc={rc} stderr={err!r}"
    )


def test_bash_no_write_passes_through_end_to_end(tmp_path):
    """`ls` / read-only bash invocations not gated by freeze."""
    root, env, _ = _setup_project(
        tmp_path,
        freeze_mode="session",
        allowlist_paths=["src/foo.py"],
    )
    rc, _, _ = _run(_bash("ls -la src/"), cwd=str(root), env=env)
    assert rc == 0


# ---------------------------------------------------------------------------
# D2 honesty residual end-to-end (M2.4-MUST)
# ---------------------------------------------------------------------------


def test_python_c_subprocess_write_not_blocked_end_to_end(tmp_path):
    """Subprocess writes via `python -c "open(...).write(...)"` are NOT
    visible to freeze guard's Bash sniffer end-to-end. D2 documented
    residual — subprocess writes pass through the dispatcher."""
    root, env, _ = _setup_project(
        tmp_path,
        freeze_mode="session",
        allowlist_paths=["src/foo.py"],
    )
    rc, _, err = _run(
        _bash("python -c \"open('src/secret.py','w').write('x')\""),
        cwd=str(root), env=env,
    )
    assert rc == 0, (
        f"D2 residual: subprocess writes must NOT be blocked end-to-end; "
        f"got rc={rc} stderr={err!r}"
    )


def test_make_build_subprocess_not_blocked_end_to_end(tmp_path):
    """`make build` produces files whose destinations are inside the
    Makefile, not the Bash command string. Pass-through end-to-end."""
    root, env, _ = _setup_project(
        tmp_path,
        freeze_mode="session",
        allowlist_paths=["src/foo.py"],
    )
    rc, _, _ = _run(_bash("make build"), cwd=str(root), env=env)
    assert rc == 0


# ---------------------------------------------------------------------------
# mode="warn" — logs but allows
# ---------------------------------------------------------------------------


def test_warn_mode_logs_violation_to_jsonl(tmp_path):
    """warn mode: violation appended to freeze-violations.jsonl, exit 0."""
    sid = "2026-05-29-001"
    root, env, session_dir = _setup_project(
        tmp_path,
        freeze_mode="warn",
        session_id=sid,
        allowlist_paths=["src/foo.py"],
    )
    rc, _, err = _run(
        _file_tool("Edit", "src/secret.py"), cwd=str(root), env=env
    )
    assert rc == 0, (
        f"warn mode must allow but log; got rc={rc} stderr={err!r}"
    )
    log_path = session_dir / "freeze-violations.jsonl"
    assert log_path.is_file(), (
        f"warn mode must write freeze-violations.jsonl at {log_path}"
    )
    line = log_path.read_text(encoding="utf-8").strip().splitlines()[0]
    record = json.loads(line)
    assert record["tool"] == "Edit"
    assert record["target"] == "src/secret.py"
    assert record["mode"] == "warn"


def test_warn_mode_then_session_mode_appends_both(tmp_path):
    """Atomic-append: subsequent violations append, prior lines preserved."""
    sid = "2026-05-29-001"
    root, env, session_dir = _setup_project(
        tmp_path,
        freeze_mode="warn",
        session_id=sid,
        allowlist_paths=["src/foo.py"],
    )
    # First violation under warn → logs + allows.
    _run(_file_tool("Edit", "src/secret1.py"), cwd=str(root), env=env)
    # Second violation under warn → appends.
    _run(_file_tool("Edit", "src/secret2.py"), cwd=str(root), env=env)
    log_path = session_dir / "freeze-violations.jsonl"
    lines = [l for l in log_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 2, (
        f"expected 2 jsonl lines after 2 warn violations, got {len(lines)}: "
        f"{lines!r}"
    )
    r1 = json.loads(lines[0])
    r2 = json.loads(lines[1])
    assert r1["target"] == "src/secret1.py"
    assert r2["target"] == "src/secret2.py"


# ---------------------------------------------------------------------------
# v0.16.0 fail-CLOSED preservation via dispatcher (M2.4)
# ---------------------------------------------------------------------------


def test_missing_athanor_json_blocks_rm_rf_root_via_dispatcher(tmp_path):
    """**Codex-review-of-A invariant lock**: dispatcher subprocess
    blocks rm -rf / even with no athanor.json on disk. Validates
    end-to-end fail-CLOSED kernel posture without the config file."""
    # tmp_path has no athanor.json — that's the point.
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
    rc, _, err = _run(_bash("rm -rf /"), cwd=str(tmp_path), env=env)
    assert rc == 2, (
        f"v0.16.0 fail-CLOSED: rm -rf / must block via dispatcher "
        f"subprocess even with no athanor.json; got rc={rc} stderr={err!r}"
    )


def test_missing_athanor_json_allows_benign_edit_via_dispatcher(tmp_path):
    """No athanor.json + benign Edit → exit 0 (kernel passes, freeze
    skipped because no config to read mode from)."""
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
    rc, _, err = _run(
        _file_tool("Edit", "src/random.py"), cwd=str(tmp_path), env=env
    )
    assert rc == 0, (
        f"benign Edit must pass with no athanor.json; "
        f"got rc={rc} stderr={err!r}"
    )


# ---------------------------------------------------------------------------
# Real on-disk allowlist file read end-to-end
# ---------------------------------------------------------------------------


def test_allowlist_read_from_session_dir_on_disk(tmp_path):
    """The dispatcher loads `.athanor/sessions/<id>/freeze-allowlist.json`
    from the session directory under CLAUDE_PROJECT_DIR. Modifying the
    on-disk allowlist between invocations must change the gate's
    behavior — proves the file is read at evaluation time, not baked in."""
    sid = "2026-05-29-001"
    root, env, session_dir = _setup_project(
        tmp_path,
        freeze_mode="session",
        session_id=sid,
        allowlist_paths=[],  # no extra paths initially
    )
    # First call: src/foo.py NOT in allowlist (only defaults) → blocks.
    rc1, _, _ = _run(
        _file_tool("Edit", "src/foo.py"), cwd=str(root), env=env
    )
    assert rc1 == 2, "without src/foo.py in allowlist, Edit must block"

    # Rewrite allowlist to include src/foo.py.
    al = json.loads(
        (session_dir / "freeze-allowlist.json").read_text(encoding="utf-8")
    )
    al["allowed_paths"].append("src/foo.py")
    al["subtask_paths"] = ["src/foo.py"]
    (session_dir / "freeze-allowlist.json").write_text(
        json.dumps(al, indent=2), encoding="utf-8"
    )

    # Second call: now allowed → exit 0.
    rc2, _, err = _run(
        _file_tool("Edit", "src/foo.py"), cwd=str(root), env=env
    )
    assert rc2 == 0, (
        f"after updating allowlist on disk, Edit must pass; "
        f"got rc={rc2} stderr={err!r}"
    )


# ---------------------------------------------------------------------------
# hooks.profile=off bypasses both kernel and freeze
# ---------------------------------------------------------------------------


def test_profile_off_bypasses_both_layers(tmp_path):
    """hooks.profile=off short-circuits both kernel and freeze: even
    rm -rf / passes."""
    root, env, _ = _setup_project(
        tmp_path, profile="off", freeze_mode="session"
    )
    rc, _, _ = _run(_bash("rm -rf /"), cwd=str(root), env=env)
    assert rc == 0, "profile=off must bypass kernel + freeze"
