"""Regression — portable interpreter resolution for active hooks (N1).

Gap under lock (v0.24.3)
------------------------
`hooks/hooks.json` used to invoke enforced hooks with bare `python3`.
LIVE INCIDENT (2026-07-01, Windows host): the Windows Store App-Execution-
Alias recreated `python3` as a stub that PRINTS "Python was not found" and
exits non-2, yielding a visible hook error while passing through. The portable
launcher keeps that failure loud rather than silent.

The fix: every enabled hook command routes through the portable launcher
shim `scripts/hooks/run_hook.sh`, which resolves a WORKING Python >= 3.10 by
FUNCTIONALITY probe (`<cand> -c "import sys; ..."` — the Store stub exists on
PATH but cannot run code, so presence checks pass on it and the probe does
not), in candidate order `python3` -> `python` -> `py -3`, then `exec`s the
winner with original stdin/stdout/stderr so exit-code semantics (exit 2 =
block) propagate unchanged. No working interpreter => exit 1 LOUD-PASS
(visible hook error + branded stderr; never a bricked session, never a
silent fail-open).

This file carries:
  - static locks on hooks.json command shape, shim content, and line endings;
  - behavioral subprocess locks (exit-2/stdin propagation, broken-stub
    fall-through = the incident replay, no-interpreter loud-pass, and the
    SHIPPED hooks.json command string end-to-end).

Behavioral tests need a POSIX shell; GH Actions windows-latest ships Git
Bash so BOTH CI matrix legs execute them (skipif only fires on hosts with
no sh/bash at all).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS_JSON = REPO_ROOT / "hooks" / "hooks.json"
SHIM = REPO_ROOT / "scripts" / "hooks" / "run_hook.sh"
GITATTRIBUTES = REPO_ROOT / ".gitattributes"

_EXPECTED_COMMAND_RE = re.compile(
    r'^sh "\$\{CLAUDE_PLUGIN_ROOT\}/scripts/hooks/run_hook\.sh" '
    r'"\$\{CLAUDE_PLUGIN_ROOT\}/scripts/hooks/[a-z0-9_]+\.py"$'
)


def _posix_shell() -> str | None:
    for shell in (shutil.which("sh"), shutil.which("bash")):
        if shell is None:
            continue
        if "windowsapps" in shell.lower():
            continue
        try:
            probe = subprocess.run(
                [shell, "-c", "echo ATHANOR_SH_OK"],
                text=True,
                capture_output=True,
                cwd=str(REPO_ROOT),
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if probe.returncode == 0 and "ATHANOR_SH_OK" in probe.stdout:
            return shell
    return None


needs_posix_shell = pytest.mark.skipif(
    _posix_shell() is None,
    reason=(
        "behavioral shim tests need a POSIX shell (sh or bash); GH Actions "
        "ubuntu-latest AND windows-latest (Git Bash) both have one, so both "
        "CI legs execute these — this skip only fires on unusual hosts"
    ),
)


def _hook_commands() -> list[str]:
    data = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
    commands: list[str] = []
    for _event, entries in data["hooks"].items():
        for entry in entries:
            for hook in entry.get("hooks", []):
                commands.append(hook["command"])
    return commands


def _shim_text() -> str:
    return SHIM.read_text(encoding="utf-8")


def _run_shim(
    target: Path,
    *,
    stdin_text: str = "{}",
    extra_path_prefix: Path | None = None,
    path_override: str | None = None,
    timeout: int = 60,
) -> subprocess.CompletedProcess:
    """Run the real shim via the POSIX shell (by ABSOLUTE path, so a
    restricted PATH cannot break the shell itself)."""
    shell = _posix_shell()
    assert shell is not None
    env = os.environ.copy()
    if path_override is not None:
        env["PATH"] = path_override
    elif extra_path_prefix is not None:
        env["PATH"] = str(extra_path_prefix) + os.pathsep + env["PATH"]
    return subprocess.run(
        [shell, str(SHIM), str(target)],
        input=stdin_text,
        text=True,
        capture_output=True,
        env=env,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Static locks
# ---------------------------------------------------------------------------


def test_all_enabled_hook_commands_use_sh_launcher():
    """Every hooks.json inner command routes through the portable shim."""
    commands = _hook_commands()
    assert len(commands) == 2, (
        f"expected exactly 2 registered hook commands (PreToolUse and "
        f"PostToolUse); got {len(commands)}"
    )
    for cmd in commands:
        assert _EXPECTED_COMMAND_RE.fullmatch(cmd), (
            f"hook command must use the portable sh launcher form "
            f'`sh "${{CLAUDE_PLUGIN_ROOT}}/scripts/hooks/run_hook.sh" '
            f'"${{CLAUDE_PLUGIN_ROOT}}/scripts/hooks/<target>.py"`; '
            f"got: {cmd!r}"
        )


def test_no_bare_python3_hook_command_remains():
    """Revert lock — a bare `python3 …` hook command reproduces the
    2026-07-01 Store-stub fail-open incident. Pairs with the perf gate's
    strict `_SH_LAUNCHER_COMMAND` regex so a revert fails twice."""
    for cmd in _hook_commands():
        assert not cmd.lstrip().startswith("python3"), (
            f"hooks.json command reverted to bare `python3` — that is the "
            f"2026-07-01 silent fail-open incident shape (Windows Store "
            f"App-Execution-Alias stub). Route through "
            f"scripts/hooks/run_hook.sh instead. Got: {cmd!r}"
        )


def test_hook_command_triplet_is_uniform():
    """Sync lock — the active commands are identical after normalizing the
    target `.py` basename (one drifting command = partial coverage)."""
    normalized = {
        re.sub(r"[a-z0-9_]+\.py", "<TARGET>.py", cmd) for cmd in _hook_commands()
    }
    assert len(normalized) == 1, (
        f"the active hook commands must be identical apart from the target .py "
        f"basename; got divergent forms: {sorted(normalized)}"
    )


def test_shim_exists_and_is_lf_only():
    """CRLF in the shim breaks `sh` tokenization on autocrlf checkouts —
    `.gitattributes` must pin `*.sh text eol=lf` and the working-tree bytes
    must carry no `\\r`."""
    assert SHIM.is_file(), f"portable launcher shim not found at {SHIM}"
    raw = SHIM.read_bytes()
    assert b"\r" not in raw, (
        "scripts/hooks/run_hook.sh contains CR bytes — a CRLF checkout "
        "breaks sh tokenization; check .gitattributes `*.sh text eol=lf`"
    )
    assert GITATTRIBUTES.is_file(), (
        ".gitattributes must exist at repo root to pin LF endings for *.sh "
        "(this host-class checks out with core.autocrlf=true)"
    )
    attrs = GITATTRIBUTES.read_text(encoding="utf-8")
    assert "*.sh text eol=lf" in attrs, (
        ".gitattributes must contain `*.sh text eol=lf` so the shim survives "
        "autocrlf checkouts"
    )


def test_shim_probes_functionality_not_presence():
    """The Store stub EXISTS on PATH but cannot run code — presence checks
    (`command -v`) pass on it. Lock the functionality probe + version floor
    + stdin discipline + exec + candidate order."""
    text = _shim_text()
    assert "-c" in text and "version_info >= (3, 10)" in text, (
        "shim must probe FUNCTIONALITY via `-c` with a >= (3, 10) version "
        "floor (presence checks pass on the WindowsApps stub — the incident)"
    )
    probe_lines = [
        line for line in text.splitlines() if "$PROBE" in line and "-c" in line
    ]
    assert probe_lines and all("</dev/null" in line for line in probe_lines), (
        "the probe invocation must read stdin from /dev/null so the hook's "
        "JSON payload is never consumed by a probe"
    )
    assert re.search(r"^\s*exec \$CAND", text, re.M), (
        "the winning interpreter must be exec'd so fd 0/1/2 and exit codes "
        "(incl. blocking exit 2) propagate unchanged"
    )
    for_line = next(
        (line for line in text.splitlines() if line.strip().startswith("for CAND in")),
        "",
    )
    assert re.search(r'for CAND in python3 python "py -3"', for_line), (
        f"candidate order must be python3 -> python -> \"py -3\" (python3 "
        f"first keeps mac/linux byte-equivalent to the pre-shim behavior; "
        f"py -3 is Windows-only). Got: {for_line!r}"
    )


def test_shim_missing_interpreter_is_loud_pass_exit_1():
    """Terminal behavior lock — no-interpreter path is `exit 1` LOUD-PASS:
    never `exit 2` (bricks python-less sessions on every hook call),
    never a silent success (the failure mode this shim fixes)."""
    text = _shim_text()
    code_lines = [
        line for line in text.splitlines() if not line.strip().startswith("#")
    ]
    code = "\n".join(code_lines)
    assert re.search(r"^\s*exit 1\s*$", code, re.M), (
        "shim must terminate the no-interpreter path with `exit 1`"
    )
    assert not re.search(r"^\s*exit 2\b", code, re.M), (
        "shim must NEVER exit 2 itself — exit 2 blocks active hook calls and "
        "would brick every session on python-less hosts"
    )
    assert not re.search(r"^\s*exit 0\b", code, re.M), (
        "shim must not exit 0 on its own — a silent success IS the "
        "2026-07-01 fail-open failure mode"
    )
    last_exit = [line for line in code_lines if line.strip()][-1]
    assert last_exit.strip() == "exit 1", (
        f"the shim's final statement must be `exit 1`; got: {last_exit!r}"
    )
    assert "INACTIVE" in text and "Active hooks" in text, (
        "the no-interpreter stderr message must say the gate is INACTIVE and "
        "name the active hooks that did not run"
    )


# ---------------------------------------------------------------------------
# Behavioral locks (subprocess through the real shim)
# ---------------------------------------------------------------------------


@needs_posix_shell
def test_shim_exit2_and_stdin_propagate(tmp_path: Path) -> None:
    """D6 lock — the hook payload on stdin reaches the target intact and a
    blocking exit 2 from the target comes back as 2 through the shim."""
    fixture = tmp_path / "exit2_fixture.py"
    fixture.write_text(
        "import sys\n"
        "payload = sys.stdin.read()\n"
        "print('FIXTURE_MARKER payload=' + payload.strip(), file=sys.stderr)\n"
        "sys.exit(2 if payload.strip() == '{\"block\": true}' else 0)\n",
        encoding="utf-8",
    )
    proc = _run_shim(fixture, stdin_text='{"block": true}')
    assert proc.returncode == 2, (
        f"exit 2 from the target hook must propagate through the shim "
        f"(blocking contract); got rc={proc.returncode}, "
        f"stderr={proc.stderr!r}"
    )
    assert "FIXTURE_MARKER" in proc.stderr
    assert '{"block": true}' in proc.stderr, (
        "the stdin payload must reach the target unconsumed (probes must "
        "read from /dev/null)"
    )
    # Non-matching payload → exit 0 also propagates.
    proc0 = _run_shim(fixture, stdin_text="{}")
    assert proc0.returncode == 0, (
        f"exit 0 must also propagate; got rc={proc0.returncode}"
    )


@needs_posix_shell
def test_shim_falls_through_broken_stub(tmp_path: Path) -> None:
    """Incident replay — a `python3` on PATH that exists but cannot run code
    (the Windows Store App-Execution-Alias shape) is skipped and the shim
    still runs the target via a later working interpreter."""
    stub_dir = tmp_path / "stubbin"
    stub_dir.mkdir()
    stub = stub_dir / "python3"
    stub.write_text(
        '#!/bin/sh\necho "Python was not found" >&2\nexit 9009\n',
        encoding="utf-8",
        newline="\n",
    )
    stub.chmod(0o755)
    fixture = tmp_path / "ok_fixture.py"
    fixture.write_text(
        "import sys\nprint('RAN_VIA_FALLBACK', file=sys.stderr)\nsys.exit(0)\n",
        encoding="utf-8",
    )
    proc = _run_shim(fixture, extra_path_prefix=stub_dir)
    assert proc.returncode == 0, (
        f"shim must fall through the broken python3 stub to a working "
        f"interpreter (2026-07-01 incident replay); got "
        f"rc={proc.returncode}, stderr={proc.stderr!r}"
    )
    assert "RAN_VIA_FALLBACK" in proc.stderr
    assert "INACTIVE" not in proc.stderr


@needs_posix_shell
def test_shim_no_interpreter_exit1_behavioral(tmp_path: Path) -> None:
    """No working interpreter anywhere on PATH → rc 1 + INACTIVE stderr
    (loud-pass, not a brick, not silence)."""
    empty_dir = tmp_path / "emptybin"
    empty_dir.mkdir()
    fixture = tmp_path / "never_runs.py"
    fixture.write_text("import sys\nsys.exit(0)\n", encoding="utf-8")
    proc = _run_shim(fixture, path_override=str(empty_dir))
    assert proc.returncode == 1, (
        f"no-interpreter path must exit 1 (loud-pass); got "
        f"rc={proc.returncode}, stderr={proc.stderr!r}"
    )
    assert "INACTIVE" in proc.stderr
    assert "python3, python, py -3" in proc.stderr


@needs_posix_shell
def test_hooks_json_command_end_to_end(tmp_path: Path) -> None:
    """The shipped PreToolUse command string (verbatim from hooks.json) resolves,
    execs, and propagates exit codes when CLAUDE_PLUGIN_ROOT points at a
    plugin tree — proves the deployed string, not a reconstruction."""
    data = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
    command = data["hooks"]["PreToolUse"][0]["hooks"][0]["command"]

    plugin_root = tmp_path / "plugin"
    hooks_dir = plugin_root / "scripts" / "hooks"
    hooks_dir.mkdir(parents=True)
    shutil.copyfile(SHIM, hooks_dir / "run_hook.sh")
    (hooks_dir / "pretool_dispatcher.py").write_text(
        "import sys\nsys.exit(7)\n", encoding="utf-8"
    )

    shell = _posix_shell()
    assert shell is not None
    env = os.environ.copy()
    # Forward slashes: valid on POSIX, and Git Bash + Windows Python both
    # accept C:/-style paths.
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root).replace("\\", "/")
    proc = subprocess.run(
        [shell, "-c", command],
        input="{}",
        text=True,
        capture_output=True,
        env=env,
        timeout=60,
    )
    assert proc.returncode == 7, (
        f"the shipped hooks.json PreToolUse command must resolve an interpreter "
        f"and propagate the target's exit code (7); got "
        f"rc={proc.returncode}, stderr={proc.stderr!r}"
    )


@needs_posix_shell
def test_shim_completes_promptly(tmp_path: Path) -> None:
    """Hang-guard — happy path (probe + exec) completes well under 5s.
    (The 500ms per-hook SLA remains the perf-budget gate's job, which
    measures the target script hermetically; this guards the shim itself
    against pathological probe stalls.)"""
    fixture = tmp_path / "fast_fixture.py"
    fixture.write_text("import sys\nsys.exit(0)\n", encoding="utf-8")
    start = time.perf_counter()
    proc = _run_shim(fixture, timeout=30)
    elapsed = time.perf_counter() - start
    assert proc.returncode == 0
    assert elapsed < 5.0, (
        f"shim happy path took {elapsed:.2f}s (>= 5s) — probe overhead has "
        f"regressed pathologically"
    )
