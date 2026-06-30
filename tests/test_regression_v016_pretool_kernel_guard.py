"""Regression tests for v0.16.0 PreToolUse kernel guard.

Covers `scripts/hooks/pretool_kernel_guard.py` — the new PreToolUse
runtime gate that blocks 3 catastrophic worker-hazard classes:

  1. Destructive shell commands (`rm -rf /`, `git reset --hard`,
     `git clean -f`, `git checkout .`).
  2. Force-push to protected branches (main/master).
  3. Sensitive credential file access (.env*, credentials.json,
     private_key, .ssh/, .aws/credentials).

Pattern mirrors `tests/test_regression_stop_hook_script.py`: pipe a
synthetic PreToolUse event JSON to the script via subprocess and assert
returncode. exit 2 = block, exit 0 = allow / fail-open.

Per ST7 plan: 23 behavioral test cases.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts/hooks/pretool_kernel_guard.py"


def _run(payload, *, cwd=None, env=None) -> tuple[int, str, str]:
    """Invoke the script with `payload` (dict or string) as stdin.

    Returns (returncode, stdout, stderr).
    """
    if isinstance(payload, dict):
        stdin_data = json.dumps(payload)
    elif payload is None:
        stdin_data = ""
    else:
        stdin_data = payload
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
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


def _notebook(path: str) -> dict:
    """NotebookEdit carries its target under `notebook_path`, not `file_path`."""
    return {"tool_name": "NotebookEdit", "tool_input": {"notebook_path": path}}


# --- Rule 1: Destructive shell commands ----------------------------------


def test_rm_rf_root_blocked():
    rc, _, err = _run(_bash("rm -rf /"))
    assert rc == 2, f"rm -rf / must be blocked, got rc={rc} stderr={err!r}"


def test_rm_rf_root_quoted_blocked():
    rc, _, err = _run(_bash('rm -rf "/"'))
    assert rc == 2, f'rm -rf "/" must be blocked, got rc={rc} stderr={err!r}'


def test_rm_rf_home_blocked():
    rc, _, err = _run(_bash("rm -rf ~/"))
    assert rc == 2, f"rm -rf ~/ must be blocked, got rc={rc} stderr={err!r}"


def test_rm_rf_subdir_allowed():
    rc, _, err = _run(_bash("rm -rf ./build/"))
    assert rc == 0, f"rm -rf ./build/ must be allowed, got rc={rc} stderr={err!r}"


def test_rm_rf_absolute_subdir_allowed():
    rc, _, err = _run(_bash("rm -rf /tmp/build"))
    assert rc == 0, (
        f"rm -rf /tmp/build must be allowed (false-positive guard), "
        f"got rc={rc} stderr={err!r}"
    )


def test_rm_f_single_file_allowed():
    rc, _, err = _run(_bash("rm -f file.txt"))
    assert rc == 0, f"rm -f file.txt must be allowed, got rc={rc} stderr={err!r}"


def test_git_reset_hard_blocked():
    rc, _, err = _run(_bash("git reset --hard"))
    assert rc == 2, f"git reset --hard must be blocked, got rc={rc} stderr={err!r}"


def test_git_clean_f_blocked():
    rc, _, err = _run(_bash("git clean -fd"))
    assert rc == 2, f"git clean -fd must be blocked, got rc={rc} stderr={err!r}"


def test_git_checkout_dot_blocked():
    rc, _, err = _run(_bash("git checkout ."))
    assert rc == 2, f"git checkout . must be blocked, got rc={rc} stderr={err!r}"


# --- Rule 2: Force-push to protected branches ----------------------------


def test_force_push_main_blocked():
    rc, _, err = _run(_bash("git push --force origin main"))
    assert rc == 2, (
        f"git push --force origin main must be blocked, "
        f"got rc={rc} stderr={err!r}"
    )


def test_force_push_with_lease_main_blocked():
    rc, _, err = _run(_bash("git push --force-with-lease origin main"))
    assert rc == 2, (
        f"git push --force-with-lease origin main must be blocked, "
        f"got rc={rc} stderr={err!r}"
    )


def test_force_push_feature_allowed():
    rc, _, err = _run(_bash("git push --force origin feature/x"))
    assert rc == 0, (
        f"git push --force origin feature/x must be allowed, "
        f"got rc={rc} stderr={err!r}"
    )


def test_normal_push_main_allowed():
    rc, _, err = _run(_bash("git push origin main"))
    assert rc == 0, (
        f"git push origin main (no force) must be allowed, "
        f"got rc={rc} stderr={err!r}"
    )


def test_force_push_main_prefixed_branch_allowed():
    """Guard — force-push to a branch whose name merely STARTS with
    `main`/`master` must be allowed. A bare `\\bmain\\b` boundary false-
    positived here (the `n`->`-` transition fires `\\b`); the trailing
    `(?![\\w-])` lookahead fixes it. Tokens followed by `-` or a word char
    are no longer treated as the protected branch.
    """
    for cmd in (
        "git push --force origin feature/main-update",
        "git push --force-with-lease origin release/master-rework",
        "git push -f origin main-fix",
    ):
        rc, _, err = _run(_bash(cmd))
        assert rc == 0, (
            f"{cmd!r} targets a branch only prefixed with main/master and "
            f"must be allowed, got rc={rc} stderr={err!r}"
        )


# --- v0.18.x: force-push segment-scoping (P13) ---------------------------
# The force-push gate must require the force flag AND the protected-branch
# token AND `git push` to co-occur within a SINGLE command segment (split on
# &&, ||, |, ;, newline). A whole-command-blob lookahead false-positived when
# a force-push to a feature branch was chained with a later command that
# merely mentions `main`/`master`.


def test_force_push_cross_segment_allowed():
    """Force flag and `main` live in DIFFERENT chained segments — ALLOWED.

    `git push --force origin feat && git switch main`: segment 1 is a
    force-push to `feat` (not protected); segment 2 switches to `main`
    (not a push). Neither segment satisfies all three tokens, so the
    whole command must be allowed. A single-blob lookahead over the full
    string false-positives here (force in seg1, `main` in seg2).
    """
    rc, _, err = _run(_bash("git push --force origin feat && git switch main"))
    assert rc == 0, (
        f"force-push to feat chained with `git switch main` must be allowed "
        f"(tokens in different segments), got rc={rc} stderr={err!r}"
    )


def test_force_push_same_segment_blocked():
    """Regression — force flag and `main` in the SAME segment stay BLOCKED.

    The segment-scoping refactor must not weaken the canonical hazard:
    `git push --force origin main` is a single segment satisfying all three
    tokens and must remain blocked.
    """
    rc, _, err = _run(_bash("git push --force origin main"))
    assert rc == 2, (
        f"git push --force origin main (same segment) must stay blocked, "
        f"got rc={rc} stderr={err!r}"
    )


def test_force_push_heredoc_data_allowed():
    """Quoted/heredoc data containing the force-push literal in a LATER
    segment must not trip the gate — ALLOWED.

    The real action (segment 1) is a benign `echo`; the force-push spelling
    appears only as quoted data after a `;`. Conservative segment splitting
    keeps the literal isolated to its own segment, and that segment is not a
    `git push` invocation, so the command is allowed (false-positive guard).
    """
    rc, _, err = _run(
        _bash("echo building ; echo 'git push --force origin main' >> notes.txt")
    )
    assert rc == 0, (
        f"force-push literal as echoed data in a later segment must be "
        f"allowed (no false-positive), got rc={rc} stderr={err!r}"
    )


def test_force_push_main_update_segment_allowed():
    """Round-1 boundary preserved under segment scoping — `feature/main-update`
    force-push stays ALLOWED.

    `feature/main-update` is a single segment with a force flag, but the
    `(?![\\w-])` trailing boundary means `main` is not the protected token
    (it is followed by `-`). The segment refactor must not regress this.
    """
    rc, _, err = _run(_bash("git push --force origin feature/main-update"))
    assert rc == 0, (
        f"git push --force origin feature/main-update must stay allowed "
        f"(round-1 boundary), got rc={rc} stderr={err!r}"
    )


# --- chore/fable5-audit R1: wrapper-prefix stripping (sudo/env) -----------
# The P13 segment-scoping anchored `^git\s+push` against the segment's RAW
# leading token, so privileged/env-wrapped pushes (`sudo git push …`,
# `env VAR=v git push …`) slipped the gate — and `sudo` is the canonical
# fat-finger prefix for a privileged force-push, exactly this guard's accident
# class. `_strip_force_push_wrappers` now peels a small safe wrapper set
# (`sudo [-flags]`, `env [VAR=val] [-flags]`) off the segment head BEFORE the
# anchor, so the force-push checks run against the stripped segment.


def test_force_push_sudo_main_blocked():
    """`sudo git push --force origin main` must be BLOCKED.

    Before R1 this slipped (the raw segment head was `sudo`, not `git`). The
    sudo-prefix strip exposes `git push …` to the anchor.
    """
    rc, _, err = _run(_bash("sudo git push --force origin main"))
    assert rc == 2, (
        f"sudo git push --force origin main must be blocked, "
        f"got rc={rc} stderr={err!r}"
    )


def test_force_push_sudo_dash_E_main_blocked():
    """`sudo -E git push -f origin main` must be BLOCKED.

    The strip consumes the leading `sudo` token plus its immediately-following
    bare option flag (`-E`), then the `-f` short force flag on `git push` is
    matched.
    """
    rc, _, err = _run(_bash("sudo -E git push -f origin main"))
    assert rc == 2, (
        f"sudo -E git push -f origin main must be blocked, "
        f"got rc={rc} stderr={err!r}"
    )


def test_force_push_env_var_main_blocked():
    """`env GIT_DIR=/tmp/x git push --force origin main` must be BLOCKED.

    The strip consumes the leading `env` token plus the `VAR=value`
    assignment, exposing `git push --force …` to the anchor.
    """
    rc, _, err = _run(_bash("env GIT_DIR=/tmp/x git push --force origin main"))
    assert rc == 2, (
        f"env GIT_DIR=/tmp/x git push --force origin main must be blocked, "
        f"got rc={rc} stderr={err!r}"
    )


def test_force_push_sudo_in_later_segment_blocked():
    """`cd /repo && sudo git push --force origin main` must be BLOCKED.

    The wrapper sits inside a LATER chained segment; segment scoping isolates
    `sudo git push --force origin main` as its own segment, and the wrapper
    strip then exposes the git-push head.
    """
    rc, _, err = _run(_bash("cd /repo && sudo git push --force origin main"))
    assert rc == 2, (
        f"cd /repo && sudo git push --force origin main must be blocked, "
        f"got rc={rc} stderr={err!r}"
    )


def test_force_push_sudo_dash_u_alice_allowed_accepted_residual():
    """`sudo -u alice git push --force origin main` is NOT blocked — this PINS
    the documented ACCEPTED residual so a future flip is visible.

    The simple strip stops at the non-flag `alice` token (option-with-argument
    form), leaving `-u alice git push …`, which the `^git\\s+push` anchor
    rejects. We deliberately do NOT build argument-aware option parsing (this
    is a fat-finger guardrail, not a security boundary — see the guard's module
    docstring). If a future change makes this BLOCK, update this pin and the
    docstring together.
    """
    rc, _, err = _run(_bash("sudo -u alice git push --force origin main"))
    assert rc == 0, (
        f"sudo -u alice git push --force origin main is the documented accepted "
        f"residual and must stay ALLOWED until argument-aware parsing is added; "
        f"got rc={rc} stderr={err!r}"
    )


def test_force_push_sudo_literal_in_commit_message_allowed():
    """`git commit -m "see: sudo git push --force origin main"` must NOT be
    blocked (false-positive guard).

    The force-push spelling (with a `sudo` prefix) appears only as quoted data
    in a commit message; the segment's command word is `git commit`, not
    `git push`, so the wrapper strip and anchor correctly ignore it.
    """
    rc, _, err = _run(
        _bash('git commit -m "see: sudo git push --force origin main"')
    )
    assert rc == 0, (
        f"sudo-prefixed force-push literal inside a commit message must be "
        f"allowed (false-positive guard), got rc={rc} stderr={err!r}"
    )


def test_force_push_sudo_no_force_flag_allowed():
    """`sudo git push origin main` (no force flag) must NOT be blocked.

    The wrapper strip exposes `git push origin main`, but with no force flag
    none of the FORCE_PUSH_PATTERNS match — a normal privileged push is fine.
    """
    rc, _, err = _run(_bash("sudo git push origin main"))
    assert rc == 0, (
        f"sudo git push origin main (no force) must be allowed, "
        f"got rc={rc} stderr={err!r}"
    )


# --- Rule 3: Sensitive credential file access ----------------------------


def test_env_file_read_blocked():
    rc, _, err = _run(_file_tool("Read", ".env"))
    assert rc == 2, f"Read .env must be blocked, got rc={rc} stderr={err!r}"


def test_env_local_read_blocked():
    rc, _, err = _run(_file_tool("Read", ".env.local"))
    assert rc == 2, f"Read .env.local must be blocked, got rc={rc} stderr={err!r}"


def test_env_example_read_allowed():
    rc, _, err = _run(_file_tool("Read", ".env.example"))
    assert rc == 0, (
        f"Read .env.example must be allowed (exception), "
        f"got rc={rc} stderr={err!r}"
    )


def test_env_test_read_allowed():
    rc, _, err = _run(_file_tool("Read", ".env.test"))
    assert rc == 0, (
        f"Read .env.test must be allowed (exception), "
        f"got rc={rc} stderr={err!r}"
    )


def test_credentials_json_write_blocked():
    rc, _, err = _run(_file_tool("Write", "credentials.json"))
    assert rc == 2, (
        f"Write credentials.json must be blocked, got rc={rc} stderr={err!r}"
    )


def test_normal_file_read_allowed():
    rc, _, err = _run(_file_tool("Read", "src/main.py"))
    assert rc == 0, (
        f"Read src/main.py must be allowed, got rc={rc} stderr={err!r}"
    )


def test_normal_file_write_allowed():
    rc, _, err = _run(_file_tool("Write", "src/app.py"))
    assert rc == 0, (
        f"Write src/app.py must be allowed, got rc={rc} stderr={err!r}"
    )


def test_bash_cat_env_blocked():
    rc, _, err = _run(_bash("cat .env"))
    assert rc == 2, (
        f"Bash `cat .env` must be blocked, got rc={rc} stderr={err!r}"
    )


# --- Subtask 8: write-tool coverage widening (WRITE_TOOLS) ----------------
# The credential gate previously covered only Read/Write/Edit, leaving
# MultiEdit and NotebookEdit able to touch a credential file. Both are now
# gated via the shared WRITE_TOOLS tuple + extract_target_path (NotebookEdit
# uses `notebook_path`). Read stays an explicit, separate reference.


def test_notebook_edit_env_blocked():
    """NotebookEdit targeting `.env` (via notebook_path) must be blocked.

    NotebookEdit was not in the gated tool set before Subtask 8, so a
    notebook write to a credential file slipped through. extract_target_path
    reads `notebook_path` for NotebookEdit so the credential check applies.
    """
    rc, _, err = _run(_notebook(".env"))
    assert rc == 2, (
        f"NotebookEdit notebook_path=.env must be blocked, "
        f"got rc={rc} stderr={err!r}"
    )


def test_multiedit_credential_blocked():
    """MultiEdit to a credential path must be blocked (was ungated)."""
    rc, _, err = _run(_file_tool("MultiEdit", "credentials.json"))
    assert rc == 2, (
        f"MultiEdit credentials.json must be blocked, "
        f"got rc={rc} stderr={err!r}"
    )


def test_read_credential_still_blocked():
    """Regression guard — Read of a credential path stays blocked after the
    WRITE_TOOLS widening (Read must NOT be folded into WRITE_TOOLS, but it
    must remain an explicit gated reference)."""
    rc, _, err = _run(_file_tool("Read", ".env"))
    assert rc == 2, (
        f"Read .env must STAY blocked after WRITE_TOOLS widening, "
        f"got rc={rc} stderr={err!r}"
    )


# --- Decision flow: fail-open + opt-out ----------------------------------


def test_malformed_stdin_failopen():
    """Empty / unparseable stdin must fail-open (exit 0) per script contract."""
    rc, _, _ = _run("")
    assert rc == 0, f"empty stdin must fail-open (exit 0), got rc={rc}"


def test_profile_off_bypasses(tmp_path):
    """When athanor.json `hooks.profile == "off"`, exit 0 even for hazardous
    invocations — same opt-out semantics as the Stop hook."""
    cfg_dir = tmp_path / "project"
    cfg_dir.mkdir()
    (cfg_dir / "athanor.json").write_text(
        json.dumps({"hooks": {"profile": "off"}}), encoding="utf-8"
    )
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(cfg_dir)
    rc, _, _ = _run(_bash("rm -rf /"), cwd=str(cfg_dir), env=env)
    assert rc == 0, (
        f"profile=off must bypass the kernel guard even for `rm -rf /`, "
        f"got rc={rc}"
    )


# --- v0.18.6: destructive-shell bypass fixes (bug hunt G1-G4) -------------
# Found by the deep-bug-hunt Workflow: the v0.16.0 regexes only matched the
# exact-spelling hazard and let equally-destructive variants through.


def test_rm_rf_root_glob_blocked():
    """G1 — `rm -rf /*` (shell-expanded root wipe) must be blocked.

    GNU rm does not require --no-preserve-root for the glob form, so `/*` is
    the most practical real-world root wipe — it must not slip the gate.
    """
    rc, _, err = _run(_bash("rm -rf /*"))
    assert rc == 2, f"rm -rf /* must be blocked, got rc={rc} stderr={err!r}"


def test_rm_rf_home_glob_blocked():
    """G1 — `rm -rf ~/*` (home glob wipe) must be blocked."""
    rc, _, err = _run(_bash("rm -rf ~/*"))
    assert rc == 2, f"rm -rf ~/* must be blocked, got rc={rc} stderr={err!r}"


def test_rm_rf_no_preserve_root_blocked():
    """G2 — `rm -rf --no-preserve-root /` (the GNU-canonical root wipe) blocked.

    Bare `rm -rf /` is refused by GNU rm; --no-preserve-root is exactly the
    form that actually destroys root, so an intervening option must not evade
    the gate.
    """
    rc, _, err = _run(_bash("rm -rf --no-preserve-root /"))
    assert rc == 2, (
        f"rm -rf --no-preserve-root / must be blocked, got rc={rc} stderr={err!r}"
    )


def test_rm_fr_flag_order_blocked():
    """G3 — `rm -fr /` (flag order f-before-r) must be blocked.

    POSIX bundled short flags are order-independent; -fr == -rf.
    """
    rc, _, err = _run(_bash("rm -fr /"))
    assert rc == 2, f"rm -fr / must be blocked, got rc={rc} stderr={err!r}"


def test_rm_fr_home_blocked():
    """G3 — `rm -fr ~/` flag-order home variant must be blocked."""
    rc, _, err = _run(_bash("rm -fr ~/"))
    assert rc == 2, f"rm -fr ~/ must be blocked, got rc={rc} stderr={err!r}"


def test_git_clean_force_long_blocked():
    """G4 — `git clean --force` (long form) must be blocked, not just `-f`."""
    rc, _, err = _run(_bash("git clean --force"))
    assert rc == 2, f"git clean --force must be blocked, got rc={rc} stderr={err!r}"


def test_credential_read_separate_value_option_blocked():
    """R1 — `head -n 5 .env` (option with a separate-token value) must be blocked.

    The flag-skip must account for value-taking options so the path candidate
    is `.env`, not the numeric value `5`.
    """
    rc, _, err = _run(_bash("head -n 5 .env"))
    assert rc == 2, f"head -n 5 .env must be blocked, got rc={rc} stderr={err!r}"
    rc, _, err = _run(_bash("tail -c 100 .env"))
    assert rc == 2, f"tail -c 100 .env must be blocked, got rc={rc} stderr={err!r}"


# --- v0.18.6: false-positive guards (must STAY allowed after the fix) -----


def test_rm_rf_home_subdir_allowed():
    """Guard — `rm -rf ~/projects/old` (home SUBDIR) must stay allowed."""
    rc, _, err = _run(_bash("rm -rf ~/projects/old"))
    assert rc == 0, (
        f"rm -rf ~/projects/old must be allowed (home subdir), "
        f"got rc={rc} stderr={err!r}"
    )


def test_rm_rf_relative_glob_allowed():
    """Guard — `rm -rf ./build/*` (relative glob) must stay allowed."""
    rc, _, err = _run(_bash("rm -rf ./build/*"))
    assert rc == 0, (
        f"rm -rf ./build/* must be allowed (relative subdir glob), "
        f"got rc={rc} stderr={err!r}"
    )


def test_git_clean_dry_run_allowed():
    """Guard — `git clean -n` (dry-run, no force) must stay allowed."""
    rc, _, err = _run(_bash("git clean -n"))
    assert rc == 0, (
        f"git clean -n (dry-run, no force) must be allowed, got rc={rc} stderr={err!r}"
    )


def test_head_normal_file_with_value_option_allowed():
    """Guard — `head -n 5 README.md` (value option, non-sensitive path) allowed."""
    rc, _, err = _run(_bash("head -n 5 README.md"))
    assert rc == 0, (
        f"head -n 5 README.md must be allowed (non-sensitive), "
        f"got rc={rc} stderr={err!r}"
    )


# --- Q1-2 (HIGH): destructive-shell segment-scope + anchor -----------------
# `_check_destructive_shell` previously ran each DESTRUCTIVE_PATTERN as a
# whole-command unanchored `.search`, which (a) MISSED `git checkout .` chained
# with a chain operator (the `\s*$` terminator never fired) and (b) FALSE-BLOCKED
# a safe command that merely MENTIONS a destructive spelling as quoted data. The
# fix segments the command and anchors each pattern (`pattern.match`) to the
# wrapper-stripped segment head, fixing both directions at once.


def test_checkout_dot_chained_blocked():
    """`git checkout .` chained with each operator must now be BLOCKED.

    Before the fix the chain operator sat where the pattern's `\\s*$` terminator
    expected end-of-string, so the destructive `git checkout .` slipped. Segment
    splitting isolates it as its own segment, which anchors and blocks.
    """
    for cmd in (
        "git checkout . && echo done",
        "git checkout . ; echo done",
        "git checkout . || echo done",
        "git checkout . | tee log",
    ):
        rc, _, err = _run(_bash(cmd))
        assert rc == 2, (
            f"{cmd!r} (chained `git checkout .`) must be blocked, "
            f"got rc={rc} stderr={err!r}"
        )


def test_destructive_preserved_blocks_after_segment_scoping():
    """Regression — the canonical destructive forms must STAY blocked under the
    segment-scope + anchor refactor (no weakening)."""
    for cmd in (
        "git reset --hard",
        "cd x && git reset --hard",
        "sudo git reset --hard",
        "git checkout .",
        "git clean -fd",
    ):
        rc, _, err = _run(_bash(cmd))
        assert rc == 2, (
            f"{cmd!r} must stay blocked after segment scoping, "
            f"got rc={rc} stderr={err!r}"
        )


def test_destructive_spelling_as_quoted_data_allowed():
    """False-positive guard — a safe command that merely MENTIONS a destructive
    spelling as quoted data (echo / commit message) must be ALLOWED.

    The segment's command word is `echo` / `git commit`, not the destructive
    subcommand, so the anchored per-segment match correctly does not fire.
    """
    for cmd in (
        'echo "git reset --hard"',
        "git commit -m 'cleanup: removed the old git clean -fd helper'",
        "git checkout ./path",
        "git checkout .gitignore",
    ):
        rc, _, err = _run(_bash(cmd))
        assert rc == 0, (
            f"{cmd!r} (destructive spelling only as data / non-`.` target) must "
            f"be allowed, got rc={rc} stderr={err!r}"
        )


# --- Q1-3: force-push `+refspec` form --------------------------------------
# Rule 2 missed the git-native `+refspec` force spelling (`git push origin
# +main`), which carries no `--force`/`-f` flag yet force-pushes. A 4th
# segment-scoped pattern now covers it, including the `+HEAD:main` /
# `+refs/heads/x:main` dst-ref forms.


def test_force_push_plus_refspec_blocked():
    for cmd in (
        "git push origin +main",
        "git push origin +HEAD:main",
        "git push origin +refs/heads/x:main",
    ):
        rc, _, err = _run(_bash(cmd))
        assert rc == 2, (
            f"{cmd!r} (+refspec force-push to a protected branch) must be "
            f"blocked, got rc={rc} stderr={err!r}"
        )


def test_force_push_plus_refspec_false_positive_guards_allowed():
    for cmd in (
        "git push origin +main-fix",  # branch merely PREFIXED with main
        "git push origin main",       # normal non-force push
    ):
        rc, _, err = _run(_bash(cmd))
        assert rc == 0, (
            f"{cmd!r} must be allowed (no force-push to a protected branch), "
            f"got rc={rc} stderr={err!r}"
        )


# --- Q1-4: `/test_` credential exception is now basename-scoped -------------
# The old `/test_` SUBSTRING exception fell open on a real `.env` secret living
# under a `test_`-prefixed DIRECTORY segment. The exception is now scoped to the
# basename, so only a `test_`-prefixed FILENAME (a fixture) is exempt.


def test_real_env_under_test_prefixed_directory_blocked():
    for path in ("config/test_env/.env", "test_data/.env"):
        rc, _, err = _run(_file_tool("Read", path))
        assert rc == 2, (
            f"Read {path!r} (real secret under a test_-prefixed directory) must "
            f"be blocked, got rc={rc} stderr={err!r}"
        )


def test_test_prefixed_fixture_basename_allowed():
    """A `test_`-prefixed BASENAME is a fixture filename and stays ALLOWED."""
    rc, _, err = _run(_file_tool("Read", "test_credentials.json"))
    assert rc == 0, (
        f"Read test_credentials.json (fixture basename) must be allowed, "
        f"got rc={rc} stderr={err!r}"
    )


def test_existing_dotenv_exceptions_still_allowed_after_test_underscore_removal():
    """Regression — the `.env.example` / `.env.test` / `fixtures/` exceptions are
    untouched by removing the `/test_` substring exception."""
    for path in (".env.example", ".env.template", ".env.test", ".env.sample",
                 "tests/fixtures/.env"):
        rc, _, err = _run(_file_tool("Read", path))
        assert rc == 0, (
            f"Read {path!r} must stay allowed (existing exception), "
            f"got rc={rc} stderr={err!r}"
        )
