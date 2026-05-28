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
