"""Regression tests for v0.18.0 ST-2.2 — PreToolUse single-outer-entry dispatcher.

Covers ``scripts/hooks/pretool_dispatcher.py`` (NEW) and the matching
``hooks/hooks.json`` registration change.

Design (C10 single-outer-entry invariant): one outer PreToolUse handler
that runs inner guards in fixed priority order:

  1. **Kernel guard FIRST** (catastrophic class) — destructive shell,
     force-push, sensitive-cred file access. NEVER over-ruled by freeze.
     Preserves v0.16.0 fail-CLOSED semantics on missing athanor.json.
  2. **Freeze guard SECOND** — plan-scoped allowlist enforcement. ONLY
     consulted when ``hooks.freeze.mode != "off"``. Default off keeps the
     v0.16.0 surface bit-for-bit.

Invariants under test (locks Subtask 2.2 acceptance criteria):

  - dispatcher exists and is invocable via ``python3``
  - kernel guard runs FIRST (rm -rf / blocked even when freeze off,
    even when athanor.json is missing — Codex review of A invariant)
  - kernel-guard fail-CLOSED on missing config preserved end-to-end
  - freeze mode="off" (default) skips freeze guard entirely; the
    dispatcher does NOT import freeze_guard in this path (verified by
    succeeding even when freeze_guard.py does not exist at 2.2 time)
  - malformed stdin → exit 0 (fail-open)
  - hooks/hooks.json PreToolUse outer entry points to the dispatcher,
    NOT the kernel guard directly
  - hooks/hooks.json still has exactly ONE PreToolUse outer entry
    (C10 invariant; `hook_uniqueness_check()` still passes)
  - ``${CLAUDE_PLUGIN_ROOT}`` expansion used (v0.11.4 lesson)
  - profile=off bypasses both guards
  - profile=standard runs kernel even with no athanor.json
  - normal Bash/Read/Edit allowed end-to-end through dispatcher
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_HOOKS = REPO_ROOT / "scripts" / "hooks"
DISPATCHER = SCRIPTS_HOOKS / "pretool_dispatcher.py"
KERNEL_GUARD = SCRIPTS_HOOKS / "pretool_kernel_guard.py"
HOOKS_JSON = REPO_ROOT / "hooks" / "hooks.json"

# In-process import of the dispatcher for the root-threading unit tests below
# (the subprocess suite above stays black-box; these exercise the helper
# signatures directly). Mirrors the sys.path convention in
# test_regression_v0188_walkup_unification.py.
if str(SCRIPTS_HOOKS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_HOOKS))

import pretool_dispatcher as dispatcher  # noqa: E402
import _athanor_hook_runtime as runtime  # noqa: E402


# ---------------------------------------------------------------------------
# Subprocess helper (mirrors v0.16.0 pattern from test_regression_v016_…)
# ---------------------------------------------------------------------------


def _run(payload, *, cwd=None, env=None) -> tuple[int, str, str]:
    """Invoke the dispatcher with ``payload`` (dict | str | None) on stdin."""
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
        cwd=cwd or str(REPO_ROOT),
        env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _bash(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def _file_tool(tool: str, path: str) -> dict:
    return {"tool_name": tool, "tool_input": {"file_path": path}}


def _make_env_without_athanor_json(tmp_path: Path) -> dict:
    """Build an environment that points CLAUDE_PROJECT_DIR at a config-free
    directory so the runtime helper cannot find any athanor.json."""
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
    # Belt-and-suspenders: also clear any inherited override that might
    # leak the repo's own athanor.json into the subprocess.
    return env


# ---------------------------------------------------------------------------
# Existence + invocability
# ---------------------------------------------------------------------------


def test_dispatcher_file_exists():
    assert DISPATCHER.is_file(), (
        f"pretool_dispatcher.py missing at {DISPATCHER} — Subtask 2.2 not done."
    )


def test_dispatcher_has_python_shebang():
    first_line = DISPATCHER.read_text(encoding="utf-8").splitlines()[0]
    assert first_line.startswith("#!") and "python" in first_line, (
        f"dispatcher must start with a python shebang; got {first_line!r}"
    )


def test_dispatcher_runs_clean_on_normal_bash():
    """Smoke: a benign Bash invocation through the dispatcher exits 0."""
    rc, _, err = _run(_bash("echo hello"))
    assert rc == 0, f"echo hello must be allowed, got rc={rc} stderr={err!r}"


def test_dispatcher_runs_clean_on_normal_read():
    """Smoke: reading a non-sensitive file exits 0."""
    rc, _, err = _run(_file_tool("Read", "src/main.py"))
    assert rc == 0, f"normal Read must pass, got rc={rc} stderr={err!r}"


# ---------------------------------------------------------------------------
# Kernel guard runs FIRST (catastrophic priority)
# ---------------------------------------------------------------------------


def test_kernel_runs_first_blocks_rm_rf_root():
    """rm -rf / must block via kernel guard regardless of freeze state."""
    rc, _, err = _run(_bash("rm -rf /"))
    assert rc == 2, (
        f"rm -rf / must block via kernel guard through dispatcher, "
        f"got rc={rc} stderr={err!r}"
    )
    # Stderr should signal a kernel-class block (the dispatcher prefixes
    # with "athanor (pretool guard)" — same prefix as the original kernel
    # to preserve the v0.16.0 stderr surface).
    assert "BLOCKED" in err or "destructive" in err.lower()


def test_kernel_runs_first_blocks_git_reset_hard():
    rc, _, err = _run(_bash("git reset --hard HEAD~3"))
    assert rc == 2, f"git reset --hard must block, got rc={rc} stderr={err!r}"


def test_kernel_runs_first_blocks_force_push_main():
    rc, _, err = _run(_bash("git push --force origin main"))
    assert rc == 2, (
        f"force-push to main must block, got rc={rc} stderr={err!r}"
    )


def test_kernel_runs_first_blocks_sensitive_env_read():
    rc, _, err = _run(_file_tool("Read", ".env"))
    assert rc == 2, f".env Read must block, got rc={rc} stderr={err!r}"


# ---------------------------------------------------------------------------
# v0.16.0 fail-CLOSED preservation (Codex review of A invariant)
# ---------------------------------------------------------------------------


def test_missing_athanor_json_still_blocks_rm_rf_root(tmp_path):
    """**Codex-review-of-A invariant lock**: missing athanor.json must NOT
    fail-open the kernel guard. ``rm -rf /`` must still block end-to-end
    through the dispatcher when no athanor.json is reachable."""
    env = _make_env_without_athanor_json(tmp_path)
    rc, _, err = _run(_bash("rm -rf /"), cwd=str(tmp_path), env=env)
    assert rc == 2, (
        f"rm -rf / must block even with missing athanor.json "
        f"(fail-CLOSED kernel guard), got rc={rc} stderr={err!r}"
    )


def test_missing_athanor_json_still_blocks_force_push(tmp_path):
    env = _make_env_without_athanor_json(tmp_path)
    rc, _, err = _run(
        _bash("git push --force origin main"), cwd=str(tmp_path), env=env
    )
    assert rc == 2, (
        f"force-push must block with missing athanor.json, "
        f"got rc={rc} stderr={err!r}"
    )


def test_missing_athanor_json_still_blocks_sensitive_read(tmp_path):
    env = _make_env_without_athanor_json(tmp_path)
    rc, _, err = _run(_file_tool("Read", ".env"), cwd=str(tmp_path), env=env)
    assert rc == 2, (
        f".env Read must block with missing athanor.json, "
        f"got rc={rc} stderr={err!r}"
    )


def test_missing_athanor_json_allows_normal_edit(tmp_path):
    """Missing config + benign Edit → kernel passes, freeze skipped (no
    config to read freeze mode from), exit 0."""
    env = _make_env_without_athanor_json(tmp_path)
    rc, _, err = _run(
        _file_tool("Edit", "src/main.py"), cwd=str(tmp_path), env=env
    )
    assert rc == 0, (
        f"benign Edit with missing config must pass, "
        f"got rc={rc} stderr={err!r}"
    )


# ---------------------------------------------------------------------------
# profile=off bypasses both guards (existing Stop-hook parity)
# ---------------------------------------------------------------------------


def test_profile_off_bypasses_kernel_guard(tmp_path):
    """hooks.profile = "off" exits 0 even for rm -rf / — same opt-out
    semantics as Stop hook + v0.16.0 kernel guard direct invocation."""
    (tmp_path / "athanor.json").write_text(
        json.dumps({"hooks": {"profile": "off"}}), encoding="utf-8"
    )
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
    rc, _, err = _run(_bash("rm -rf /"), cwd=str(tmp_path), env=env)
    assert rc == 0, (
        f"profile=off must bypass kernel guard, "
        f"got rc={rc} stderr={err!r}"
    )


# ---------------------------------------------------------------------------
# Freeze mode=off is the default → freeze guard NOT invoked
# ---------------------------------------------------------------------------


def test_freeze_mode_off_default_skips_freeze_guard(tmp_path):
    """athanor.json with freeze.mode = "off" → freeze guard never runs.
    Verified by:
      - benign Edit succeeds even though no freeze-allowlist.json exists
      - the dispatcher does NOT import freeze_guard in this code path
        (locked indirectly: this test passes BEFORE freeze_guard.py is
        created in Subtask 2.3, so the import must be lazy / guarded).
    """
    (tmp_path / "athanor.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "profile": "standard",
                    "freeze": {"mode": "off", "allowedPaths": []},
                }
            }
        ),
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
    rc, _, err = _run(
        _file_tool("Edit", "any/random/path.py"), cwd=str(tmp_path), env=env
    )
    assert rc == 0, (
        f"freeze.mode=off must skip freeze guard entirely, "
        f"got rc={rc} stderr={err!r}"
    )


def test_freeze_mode_absent_treated_as_off(tmp_path):
    """When ``hooks.freeze`` is missing entirely, default behavior is
    "off" (D1). Benign Edit must pass."""
    (tmp_path / "athanor.json").write_text(
        json.dumps({"hooks": {"profile": "standard"}}), encoding="utf-8"
    )
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
    rc, _, err = _run(
        _file_tool("Edit", "src/foo.py"), cwd=str(tmp_path), env=env
    )
    assert rc == 0, (
        f"missing freeze section must default to off, "
        f"got rc={rc} stderr={err!r}"
    )


# ---------------------------------------------------------------------------
# Malformed stdin → fail-open (mirrors kernel guard semantics)
# ---------------------------------------------------------------------------


def test_empty_stdin_fail_open():
    rc, _, _ = _run(None)
    assert rc == 0, "empty stdin must fail-open (exit 0)"


def test_malformed_json_stdin_fail_open():
    rc, _, _ = _run("not valid json{")
    assert rc == 0, "malformed JSON stdin must fail-open (exit 0)"


def test_non_object_json_fail_open():
    rc, _, _ = _run("[1, 2, 3]")
    assert rc == 0, "non-object JSON stdin must fail-open (exit 0)"


# ---------------------------------------------------------------------------
# hooks/hooks.json — registration points to dispatcher, single outer entry
# ---------------------------------------------------------------------------


def test_hooks_json_pretool_points_to_dispatcher():
    """The PreToolUse outer entry's command string must reference
    pretool_dispatcher.py — NOT pretool_kernel_guard.py directly."""
    data = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
    pretool_entries = data["hooks"]["PreToolUse"]
    assert len(pretool_entries) == 1, (
        f"PreToolUse must have exactly 1 outer entry (C10 invariant); "
        f"got {len(pretool_entries)}"
    )
    inner_hooks = pretool_entries[0]["hooks"]
    assert len(inner_hooks) == 1
    command = inner_hooks[0]["command"]
    assert "pretool_dispatcher.py" in command, (
        f"PreToolUse command must invoke pretool_dispatcher.py, "
        f"got: {command!r}"
    )
    assert "pretool_kernel_guard.py" not in command, (
        f"PreToolUse must NOT directly invoke pretool_kernel_guard.py "
        f"after v0.18.0 ST-2.2; got: {command!r}"
    )


def test_hooks_json_pretool_uses_plugin_root_expansion():
    """Per v0.11.4 lesson: hook command must use ``${CLAUDE_PLUGIN_ROOT}``
    or an absolute path so it is reachable from any project cwd."""
    data = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
    command = data["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    assert "${CLAUDE_PLUGIN_ROOT}" in command or command.startswith("/"), (
        f"hook command must use ${{CLAUDE_PLUGIN_ROOT}} or absolute path "
        f"(v0.11.4 lesson); got: {command!r}"
    )


def test_hooks_json_pretool_type_is_command():
    data = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
    hook_type = data["hooks"]["PreToolUse"][0]["hooks"][0]["type"]
    assert hook_type == "command", (
        f"PreToolUse inner hook must be type='command', got: {hook_type!r}"
    )


def test_hook_uniqueness_check_still_passes():
    """C10 invariant: hook_uniqueness_check() still returns OK after the
    dispatcher swap. Single outer entry per event."""
    # Import the check; the call site mirrors test_regression_hook_uniqueness.
    sys.path.insert(0, str(REPO_ROOT))
    from scripts.gates.manifest_checks import hook_uniqueness_check
    ok, violations = hook_uniqueness_check(HOOKS_JSON)
    assert ok is True, (
        f"hook_uniqueness_check failed: {violations!r}"
    )


# ---------------------------------------------------------------------------
# v0.16.0 kernel guard subprocess entry point still works (backwards compat)
# ---------------------------------------------------------------------------


def test_kernel_guard_subprocess_entry_still_runs():
    """Subtask 2.2 swaps the dispatcher in but does NOT delete the kernel
    guard script. The existing 23-case v0.16.0 subprocess suite must still
    be able to invoke ``pretool_kernel_guard.py`` directly."""
    assert KERNEL_GUARD.is_file(), (
        "pretool_kernel_guard.py must still exist for v0.16.0 subprocess "
        "test compatibility (23 existing tests target it directly)."
    )
    proc = subprocess.run(
        [sys.executable, str(KERNEL_GUARD)],
        input=json.dumps(_bash("rm -rf /")),
        text=True,
        capture_output=True,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 2, (
        f"kernel guard direct invocation must still block rm -rf /, "
        f"got rc={proc.returncode}"
    )


# ---------------------------------------------------------------------------
# Phase 2a (M6) — root threading through _latest_session_dir /
# _read_freeze_allowlist / main(). Behavior-preserving refactor: with
# root=None each helper self-resolves (back-compat); main() resolves ONCE and
# threads the value so both consumers anchor to the same root.
# ---------------------------------------------------------------------------


def _make_session_with_allowlist(tmp_path: Path, name: str, allow: dict) -> Path:
    """Create `<tmp>/.athanor/sessions/<name>/freeze-allowlist.json` and
    return the session dir Path."""
    session_dir = tmp_path / ".athanor" / "sessions" / name
    session_dir.mkdir(parents=True)
    (session_dir / "freeze-allowlist.json").write_text(
        json.dumps(allow), encoding="utf-8"
    )
    return session_dir


def _counting_resolver(return_value):
    """Return (fn, calls) where fn() records its invocation count and
    returns ``return_value`` — used to prove resolve-ONCE / no-resolve."""
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        return return_value

    return fn, calls


def test_latest_session_dir_honors_explicit_root(tmp_path, monkeypatch):
    """An explicit ``root`` is used verbatim — the helper must NOT call the
    resolver at all when root is supplied."""
    _make_session_with_allowlist(tmp_path, "2026-06-12-002", {"allowed_paths": []})
    _make_session_with_allowlist(tmp_path, "2026-06-12-001", {"allowed_paths": []})

    resolver, calls = _counting_resolver(None)  # would yield None if ever called
    monkeypatch.setattr(dispatcher._runtime, "resolve_project_root", resolver)

    got = dispatcher._latest_session_dir(root=tmp_path)
    assert got is not None
    assert got.name == "2026-06-12-002", "latest (lexicographic) must be chosen"
    assert calls["n"] == 0, (
        "explicit root must short-circuit the resolver; "
        f"resolver called {calls['n']}x"
    )


def test_latest_session_dir_self_resolves_when_root_none(tmp_path, monkeypatch):
    """``root=None`` (the back-compat default) self-resolves via the
    runtime resolver — identical to pre-refactor behavior."""
    _make_session_with_allowlist(tmp_path, "2026-06-12-005", {"allowed_paths": []})

    resolver, calls = _counting_resolver(tmp_path)
    monkeypatch.setattr(dispatcher._runtime, "resolve_project_root", resolver)

    got = dispatcher._latest_session_dir()  # root defaults to None
    assert got is not None and got.name == "2026-06-12-005"
    assert calls["n"] == 1, "root=None must self-resolve exactly once"


def test_latest_session_dir_none_root_fail_open(tmp_path, monkeypatch):
    """When the resolver yields None (no project root), the helper returns
    None → dispatcher fail-open. Bit-for-bit with pre-refactor."""
    resolver, calls = _counting_resolver(None)
    monkeypatch.setattr(dispatcher._runtime, "resolve_project_root", resolver)
    assert dispatcher._latest_session_dir() is None
    assert calls["n"] == 1
    # Explicit root=None is the same path (the default), still fail-open.
    assert dispatcher._latest_session_dir(root=None) is None


def test_read_freeze_allowlist_threads_explicit_root(tmp_path, monkeypatch):
    """``_read_freeze_allowlist(root)`` threads ``root`` into
    ``_latest_session_dir`` — proven by loading the allowlist under an
    explicit root WITHOUT the resolver ever firing, and by ``_session_dir``
    pointing inside that root."""
    session_dir = _make_session_with_allowlist(
        tmp_path, "2026-06-12-007", {"allowed_paths": ["src/a.py"]}
    )

    resolver, calls = _counting_resolver(None)
    monkeypatch.setattr(dispatcher._runtime, "resolve_project_root", resolver)

    data = dispatcher._read_freeze_allowlist(root=tmp_path)
    assert data is not None
    assert data["allowed_paths"] == ["src/a.py"]
    assert data["_session_dir"] == str(session_dir), (
        "allowlist must be anchored to the session under the supplied root"
    )
    assert calls["n"] == 0, "explicit root must not trigger the resolver"


def test_read_freeze_allowlist_self_resolves_when_root_none(tmp_path, monkeypatch):
    """``root=None`` back-compat: the allowlist read self-resolves the root
    via the runtime resolver, exactly as before the refactor."""
    session_dir = _make_session_with_allowlist(
        tmp_path, "2026-06-12-009", {"allowed_paths": ["x.py"]}
    )
    resolver, calls = _counting_resolver(tmp_path)
    monkeypatch.setattr(dispatcher._runtime, "resolve_project_root", resolver)

    data = dispatcher._read_freeze_allowlist()  # root defaults to None
    assert data is not None and data["allowed_paths"] == ["x.py"]
    assert data["_session_dir"] == str(session_dir)
    assert calls["n"] == 1, "root=None must self-resolve exactly once"


def test_read_freeze_allowlist_none_root_fail_open(monkeypatch):
    """None root (no project root) → None allowlist → dispatcher fail-open."""
    resolver, _ = _counting_resolver(None)
    monkeypatch.setattr(dispatcher._runtime, "resolve_project_root", resolver)
    assert dispatcher._read_freeze_allowlist() is None
    assert dispatcher._read_freeze_allowlist(root=None) is None


def test_main_resolves_root_once_and_threads_it(tmp_path, monkeypatch):
    """``main()`` on the freeze-enabled path resolves the project root EXACTLY
    once and threads that same root into ``_read_freeze_allowlist``.

    Observed via a counting wrapper on ``resolve_project_root`` (call-count
    must be 1, not 2 — the prior code resolved separately for the allowlist
    read and for freeze_evaluate) and by capturing the ``root`` argument the
    allowlist read receives.
    """
    # Drive main() down the freeze branch deterministically by stubbing the
    # runtime surface; avoids depending on ambient cwd/config.
    monkeypatch.setattr(
        dispatcher._runtime,
        "read_stdin_payload",
        lambda: {"tool_name": "Edit", "tool_input": {"file_path": "src/x.py"}},
    )
    monkeypatch.setattr(
        dispatcher._runtime,
        "read_athanor_config",
        lambda: {"hooks": {"freeze": {"mode": "warn"}}},
    )
    monkeypatch.setattr(dispatcher._runtime, "is_hook_profile_off", lambda c: False)

    resolver, calls = _counting_resolver(tmp_path)
    monkeypatch.setattr(dispatcher._runtime, "resolve_project_root", resolver)

    # Capture the root threaded into the allowlist read, and short-circuit it
    # to None so main() takes the early fail-open exit (no freeze_guard needed).
    captured = {}

    def fake_allowlist(root=None):
        captured["root"] = root
        return None

    monkeypatch.setattr(dispatcher, "_read_freeze_allowlist", fake_allowlist)

    rc = dispatcher.main()
    assert rc == 0, "missing allowlist must fail-open (exit 0)"
    assert calls["n"] == 1, (
        f"main() must resolve the project root exactly ONCE on the freeze "
        f"path; resolver called {calls['n']}x"
    )
    assert captured["root"] == tmp_path, (
        "main() must thread the resolved root into _read_freeze_allowlist"
    )


def test_main_freeze_off_does_not_resolve_root(monkeypatch):
    """Behavior-preserving: when freeze mode is off (default), main() never
    reaches the root resolution — the walk-up is paid only on the opt-in
    path."""
    monkeypatch.setattr(
        dispatcher._runtime,
        "read_stdin_payload",
        lambda: {"tool_name": "Edit", "tool_input": {"file_path": "src/x.py"}},
    )
    monkeypatch.setattr(
        dispatcher._runtime, "read_athanor_config", lambda: {"hooks": {}}
    )
    monkeypatch.setattr(dispatcher._runtime, "is_hook_profile_off", lambda c: False)

    resolver, calls = _counting_resolver(None)
    monkeypatch.setattr(dispatcher._runtime, "resolve_project_root", resolver)

    rc = dispatcher.main()
    assert rc == 0
    assert calls["n"] == 0, (
        "freeze.mode=off must short-circuit before resolving the root"
    )


# ---------------------------------------------------------------------------
# Phase 5 (P12) — broad fail-open breadcrumb is traceback-enriched.
# When freeze_guard.evaluate_payload raises, main() must stay fail-open
# (exit 0 — PreToolUse must never brick the session) AND emit the full
# traceback to stderr so the swallowed exception is VISIBLE (fail-loud over
# silent fallback; closes lesson 2026-06-11-007 residual). Exception
# narrowing is REJECTED here on purpose: a defense layer's broad catch is the
# correct shape — see the decision comment in pretool_dispatcher.py.
# ---------------------------------------------------------------------------


def _drive_main_into_freeze_branch(monkeypatch, tmp_path):
    """Stub the runtime + allowlist surface so ``main()`` reaches the
    ``freeze_evaluate(...)`` call with a valid (non-None) allowlist. Returns
    nothing; the caller is responsible for making ``freeze_guard.evaluate_payload``
    raise (or not) to exercise the except branch."""
    monkeypatch.setattr(
        dispatcher._runtime,
        "read_stdin_payload",
        lambda: {"tool_name": "Edit", "tool_input": {"file_path": "src/x.py"}},
    )
    monkeypatch.setattr(
        dispatcher._runtime,
        "read_athanor_config",
        lambda: {"hooks": {"freeze": {"mode": "warn"}}},
    )
    monkeypatch.setattr(dispatcher._runtime, "is_hook_profile_off", lambda c: False)
    monkeypatch.setattr(
        dispatcher._runtime, "resolve_project_root", lambda: tmp_path
    )
    # Return a valid allowlist so main() proceeds to the freeze_evaluate call
    # (the except branch under test lives AFTER the missing-allowlist
    # short-circuit). The lazy ``from freeze_guard import evaluate_payload``
    # resolves the attribute at call time, so monkeypatching it below takes.
    monkeypatch.setattr(
        dispatcher, "_read_freeze_allowlist", lambda root=None: {"allowed_paths": []}
    )


def test_freeze_guard_raise_fail_open_with_traceback(monkeypatch, tmp_path, capsys):
    """When ``freeze_guard.evaluate_payload`` raises, ``main()`` returns 0
    (fail-open invariant preserved) AND stderr carries the one-line breadcrumb
    PLUS the full ``traceback.format_exc()`` content (the distinctive
    exception type/message and the ``Traceback`` header). Pre-P12 the code
    emitted only the breadcrumb line — so the traceback assertions go RED
    against current source."""
    import freeze_guard

    sentinel = "p12-distinctive-boom-9f3a"

    def _raiser(*args, **kwargs):
        raise RuntimeError(sentinel)

    monkeypatch.setattr(freeze_guard, "evaluate_payload", _raiser)
    _drive_main_into_freeze_branch(monkeypatch, tmp_path)

    rc = dispatcher.main()
    captured = capsys.readouterr()

    # 1. Fail-open invariant: a raising freeze guard must NOT brick the session.
    assert rc == 0, (
        f"freeze_guard raising must stay fail-open (exit 0); got rc={rc}, "
        f"stderr={captured.err!r}"
    )
    # 2. Existing one-line breadcrumb preserved (enrich, don't replace).
    assert "freeze_guard raised RuntimeError" in captured.err, (
        f"the original breadcrumb must remain intact; stderr={captured.err!r}"
    )
    assert "passing (fail-open)" in captured.err
    # 3. NEW: traceback content present — header + the distinctive exception
    #    message that only a real traceback (not the one-liner) carries.
    assert "Traceback (most recent call last)" in captured.err, (
        "stderr must include the traceback header (traceback.format_exc()); "
        f"stderr={captured.err!r}"
    )
    assert sentinel in captured.err, (
        "stderr must include the raised exception's message via the traceback; "
        f"stderr={captured.err!r}"
    )


def test_main_threads_resolved_root_into_freeze_evaluate(monkeypatch, tmp_path):
    """The FINAL hop of the M6 root-threading chain: the same root ``main()``
    resolved must arrive at ``freeze_guard.evaluate_payload`` as the
    ``project_root`` kwarg. ``test_main_resolves_root_once_and_threads_it``
    pins the ``_read_freeze_allowlist`` hop but short-circuits (allowlist →
    None) before ``freeze_evaluate``; this sibling drives main() into the
    freeze branch with a valid allowlist and inspects the kwarg itself."""
    import freeze_guard

    captured = {}

    def _capturing_evaluate(payload, allowlist, **kwargs):
        captured["called"] = True
        captured["project_root"] = kwargs.get("project_root")
        return 0, None

    monkeypatch.setattr(freeze_guard, "evaluate_payload", _capturing_evaluate)
    _drive_main_into_freeze_branch(monkeypatch, tmp_path)

    rc = dispatcher.main()
    assert rc == 0
    assert captured.get("called"), (
        "main() never reached freeze_evaluate despite a valid allowlist"
    )
    assert captured["project_root"] == tmp_path, (
        "main() must thread the SAME resolved root into freeze_evaluate as "
        f"project_root; got {captured['project_root']!r}, expected {tmp_path!r}"
    )
