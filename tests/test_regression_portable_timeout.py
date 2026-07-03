"""Regression — portable `timeout` resolver for autonomous command fences (N2).

Gap under lock (v0.24.3, companion-fix to v0.24.2)
--------------------------------------------------
v0.24.2 shipped bare `timeout NNNs` wrappers around unattended git/gh/codex
invocations in `skills/lfg/SKILL.md`, `agents/ci-watcher.md`, and
`agents/codex-dispatcher.md`. Stock macOS/BSD ships NO GNU coreutils
`timeout` (and no `gtimeout` unless `brew install coreutils`), so the
wrapper exits 127 BEFORE git/gh/codex ever runs — cross-model planning and
the CI-autofix loop silently degrade on stock macOS.

The fix (per-site rewrite, D7): every fenced block that uses the wrapper
restates a one-line resolver preamble as its first command —

    TIMEOUT_CMD=$(command -v timeout || command -v gtimeout) || { echo
    "FATAL: … install GNU coreutils …" >&2; exit 127; }

— then invokes `"$TIMEOUT_CMD" NNNs …`. POSIX-correct: `VAR=$(a || b)`
carries the substitution's exit status, so the `|| { …; exit 127; }` fires
exactly when both candidates are missing. Never silently drops the timeout,
never runs the autonomous command unbounded. The codex-dispatcher exit
table gains a `127` row (resolver failed loud OR `codex` not found — GNU
timeout's own 127 semantics; stderr distinguishes).

Static locks pin the three files' prose; behavioral locks run the actual
preamble through a POSIX shell (both CI legs execute — GH windows-latest
ships Git Bash).
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
LFG = REPO_ROOT / "skills" / "lfg" / "SKILL.md"
CI_WATCHER = REPO_ROOT / "agents" / "ci-watcher.md"
CODEX = REPO_ROOT / "agents" / "codex-dispatcher.md"
N2_FILES = (LFG, CI_WATCHER, CODEX)

RESOLVER = "command -v timeout || command -v gtimeout"

PREAMBLE = (
    'TIMEOUT_CMD=$(command -v timeout || command -v gtimeout) || { echo '
    '"FATAL: neither timeout nor gtimeout on PATH - install GNU coreutils" '
    ">&2; exit 127; }"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _posix_shell() -> str | None:
    return shutil.which("sh") or shutil.which("bash")


needs_posix_shell = pytest.mark.skipif(
    _posix_shell() is None,
    reason=(
        "behavioral resolver tests need a POSIX shell (sh or bash); both CI "
        "matrix legs have one (windows-latest ships Git Bash)"
    ),
)


# ---------------------------------------------------------------------------
# Static locks
# ---------------------------------------------------------------------------


def test_no_bare_gnu_timeout_invocations() -> None:
    """Negative lock — a bare `timeout NNNs` / `gtimeout NNNs` wrapper
    (literal seconds OR the `{timeout_sec}` template placeholder) is
    GNU-coreutils-only and exits 127 before the wrapped command runs on
    stock macOS/BSD. The portable `"$TIMEOUT_CMD" NNNs` form cannot match
    this pattern."""
    for path in N2_FILES:
        body = _read(path)
        match = re.search(
            r'(^|[^$"\w])(?:gtimeout|timeout)\s+(?:\d+|\{timeout_sec\})s',
            body,
            re.M,
        )
        assert match is None, (
            f"{path.relative_to(REPO_ROOT)} contains a bare GNU-only timeout "
            f"wrapper ({match.group(0).strip()!r}) — use the resolved "
            f'`"$TIMEOUT_CMD" NNNs` form with the per-block resolver preamble '
            f"(v0.24.3 N2)."
        )


def test_resolver_preamble_present_and_fail_loud() -> None:
    """Each N2 file carries the resolver preamble AND its fail-loud terminal
    behavior (exit 127 naming GNU coreutils — never a silent unbounded run)."""
    for path in N2_FILES:
        body = _read(path)
        rel = path.relative_to(REPO_ROOT)
        assert RESOLVER in body, (
            f"{rel} must carry the portable resolver "
            f"`TIMEOUT_CMD=$({RESOLVER})`"
        )
        assert "exit 127" in body, (
            f"{rel} resolver must FAIL LOUD with exit 127 when neither "
            f"timeout nor gtimeout exists"
        )
        assert "coreutils" in body, (
            f"{rel} fail-loud message must name GNU coreutils (actionable "
            f"install hint, e.g. `brew install coreutils`)"
        )


def test_timeout_cmd_adjacent_to_guarded_commands() -> None:
    """Locality lock (same philosophy as `_HARDENED_PUSH_RE` in
    test_regression_lfg_git_hardening.py) — the resolved wrapper sits ON the
    command lines it guards, not floating in prose."""
    lfg = _read(LFG)
    assert re.search(
        r'GIT_TERMINAL_PROMPT=0 "\$TIMEOUT_CMD" \d+s git (?:push|commit)', lfg
    ), (
        'lfg git plumbing must run `GIT_TERMINAL_PROMPT=0 "$TIMEOUT_CMD" NNNs '
        "git push|commit` on one line"
    )
    assert '"$TIMEOUT_CMD" 600s gh pr checks --watch' in lfg, (
        'the lfg Step 8 CI watch must be `"$TIMEOUT_CMD" 600s gh pr checks '
        "--watch` (bounded, portable)"
    )
    watcher = _read(CI_WATCHER)
    assert re.search(
        r'GIT_TERMINAL_PROMPT=0 "\$TIMEOUT_CMD" \d+s git (?:push|commit)', watcher
    ), (
        "ci-watcher Step 4 commit/push must carry the portable resolved "
        "wrapper on the command lines"
    )
    codex = _read(CODEX)
    assert re.search(r'\| "\$TIMEOUT_CMD" \{timeout_sec\}s codex', codex), (
        'codex-dispatcher Step 4 must pipe the heredoc into `"$TIMEOUT_CMD" '
        "{timeout_sec}s codex …`"
    )


def test_codex_exit_table_has_127_row() -> None:
    """The codex-dispatcher exit table must disposition 127 (resolver failed
    loud OR `codex` binary missing — GNU timeout's not-found semantics) with
    the coreutils hint; the existing 124 timeout row stays."""
    body = _read(CODEX)
    row_127 = next(
        (
            line
            for line in body.splitlines()
            if line.lstrip().startswith("|") and "`127`" in line
        ),
        "",
    )
    assert row_127, (
        "codex-dispatcher exit table must carry a `127` row — without it, a "
        "missing timeout/gtimeout (or codex binary) lands in the generic "
        "'Other' row and cross-model planning silently degrades on stock macOS"
    )
    assert "coreutils" in row_127, (
        f"the 127 row must name GNU coreutils as the install hint; got: "
        f"{row_127!r}"
    )
    assert any(
        "`124`" in line and "imeout" in line
        for line in body.splitlines()
        if line.lstrip().startswith("|")
    ), "the existing `124` timeout row must remain in the exit table"


def test_lfg_step8_prose_names_exit_127() -> None:
    """The lfg Step 8 watch prose must distinguish exit 124 (CI-still-pending
    → continue) from exit 127 (resolver/`gh` missing → environment failure,
    NOT CI-pending)."""
    body = _read(LFG)
    step8_start = body.find("### Step 8")
    step85_start = body.find("### Step 8.5")
    assert step8_start >= 0 and step85_start >= 0
    step8 = body[step8_start:step85_start]
    assert "124" in step8, "Step 8 must keep the exit-124 (pending) disposition"
    assert "127" in step8, (
        "Step 8 watch prose must disposition exit 127 (resolver failed loud / "
        "gh missing) separately from 124"
    )
    assert "not" in step8.lower() and "pending" in step8.lower(), (
        "Step 8 must say exit 127 is NOT to be treated as CI-pending"
    )


# ---------------------------------------------------------------------------
# Behavioral locks (the actual preamble semantics through a POSIX shell)
# ---------------------------------------------------------------------------

# The canonical preamble as shipped in the three files (echo message elided
# to a short marker — the POSIX semantics under test are identical).
_PREAMBLE_SCRIPT = (
    "TIMEOUT_CMD=$(command -v timeout || command -v gtimeout) || "
    '{ echo "FATAL: neither timeout nor gtimeout on PATH - install GNU '
    'coreutils" >&2; exit 127; }; printf %s "$TIMEOUT_CMD"'
)


@needs_posix_shell
def test_preamble_resolves_gtimeout_fallback(tmp_path: Path) -> None:
    """With only `gtimeout` on PATH (the brew-coreutils macOS shape), the
    resolver must fall back to it."""
    shell = _posix_shell()
    assert shell is not None
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "gtimeout"
    fake.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8", newline="\n")
    fake.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = str(bin_dir)
    proc = subprocess.run(
        [shell, "-c", _PREAMBLE_SCRIPT],
        text=True,
        capture_output=True,
        env=env,
        timeout=30,
    )
    assert proc.returncode == 0, (
        f"resolver must succeed when gtimeout exists; rc={proc.returncode}, "
        f"stderr={proc.stderr!r}"
    )
    assert proc.stdout.strip().endswith("gtimeout"), (
        f"TIMEOUT_CMD must resolve to the gtimeout fallback; got "
        f"{proc.stdout!r}"
    )


@needs_posix_shell
def test_preamble_fails_loud_when_neither_exists(tmp_path: Path) -> None:
    """With neither on PATH (stock macOS/BSD shape), the resolver must exit
    127 with the coreutils hint — never proceed to run unbounded."""
    shell = _posix_shell()
    assert shell is not None
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    env = os.environ.copy()
    env["PATH"] = str(empty_dir)
    proc = subprocess.run(
        [shell, "-c", _PREAMBLE_SCRIPT],
        text=True,
        capture_output=True,
        env=env,
        timeout=30,
    )
    assert proc.returncode == 127, (
        f"resolver must exit 127 when neither timeout nor gtimeout exists "
        f"(fail loud, never unbounded); got rc={proc.returncode}"
    )
    assert "coreutils" in proc.stderr, (
        f"fail-loud stderr must name coreutils; got {proc.stderr!r}"
    )
