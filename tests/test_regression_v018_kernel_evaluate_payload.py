"""Regression tests for v0.18.0 ``evaluate_payload()`` API extraction.

Covers the v0.18.0 refactor of ``scripts/hooks/pretool_kernel_guard.py``
that extracts the rule-evaluation core into a pure callable so the
PreToolUse dispatcher can invoke kernel-guard logic in-process without
re-shelling.

Invariants under test:

  1. ``evaluate_payload`` is importable and callable.
  2. Signature returns ``(exit_code, stderr_message)`` tuple.
  3. ``rm -rf /`` blocks (exit 2) — destructive Rule 1.
  4. Normal Bash command allows (exit 0).
  5. Sensitive file Read blocks (exit 2) — Rule 3.
  6. Normal file Read allows (exit 0).
  7. **v0.16.0 invariant preserved**: missing athanor.json keeps
     ``profile="standard"`` (fail-CLOSED) — ``rm -rf /`` still blocked.
  8. ``profile="off"`` bypasses the gate (opt-out).
  9. Malformed payload (non-dict / wrong shape) returns ``(0, "")``.
 10. Stderr message contains a useful substring on block.
 11. ``main()`` CLI entry continues to delegate via ``evaluate_payload``
     — exercised indirectly by the 23 v0.16 subprocess tests; this file
     adds in-process coverage as the new dispatcher path.

The Codex review of variant A flagged: kernel guard MUST NOT fail-open
when athanor.json is missing. The dedicated test
``test_missing_config_still_blocks_rm_rf_root`` locks that invariant
against any future regression in the runtime profile resolution path.
"""
from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_HOOKS = REPO_ROOT / "scripts" / "hooks"

if str(SCRIPTS_HOOKS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_HOOKS))


@pytest.fixture()
def kernel_guard(monkeypatch, tmp_path):
    """Import pretool_kernel_guard with an isolated working directory.

    The runtime profile helper walks up from cwd to find athanor.json.
    Isolating cwd to ``tmp_path`` (with no athanor.json present) lets the
    tests assert the "missing config → standard profile (fail-closed)"
    invariant without picking up the repo's own athanor.json.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    # Force a fresh import in case earlier tests cached a module bound to
    # the repo cwd. The module itself is stateless w.r.t. cwd, but
    # _athanor_hook_runtime caches nothing — the import reload is cheap
    # and avoids cross-test contamination.
    if "pretool_kernel_guard" in sys.modules:
        del sys.modules["pretool_kernel_guard"]
    module = importlib.import_module("pretool_kernel_guard")
    return module


def _bash(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def _file_tool(tool: str, path: str) -> dict:
    return {"tool_name": tool, "tool_input": {"file_path": path}}


# --- Importable + callable + signature shape ---------------------------------


def test_evaluate_payload_importable(kernel_guard):
    """The dispatcher target must exist as a module-level callable."""
    assert hasattr(kernel_guard, "evaluate_payload")
    assert callable(kernel_guard.evaluate_payload)


def test_evaluate_payload_returns_tuple(kernel_guard):
    """Return contract: (exit_code: int, stderr_message: str)."""
    result = kernel_guard.evaluate_payload(_bash("echo hello"))
    assert isinstance(result, tuple)
    assert len(result) == 2
    exit_code, stderr_message = result
    assert isinstance(exit_code, int)
    assert isinstance(stderr_message, str)


# --- Rule 1: destructive shell ----------------------------------------------


def test_rm_rf_root_blocked(kernel_guard):
    exit_code, stderr_message = kernel_guard.evaluate_payload(_bash("rm -rf /"))
    assert exit_code == 2
    assert "BLOCKED" in stderr_message
    assert "destructive" in stderr_message.lower()


def test_normal_bash_allowed(kernel_guard):
    exit_code, stderr_message = kernel_guard.evaluate_payload(
        _bash("ls -la")
    )
    assert exit_code == 0
    assert stderr_message == ""


def test_git_reset_hard_blocked(kernel_guard):
    exit_code, _ = kernel_guard.evaluate_payload(
        _bash("git reset --hard HEAD~1")
    )
    assert exit_code == 2


# --- Rule 2: force-push -----------------------------------------------------


def test_force_push_main_blocked(kernel_guard):
    exit_code, stderr_message = kernel_guard.evaluate_payload(
        _bash("git push --force origin main")
    )
    assert exit_code == 2
    assert "force-push" in stderr_message.lower() or "BLOCKED" in stderr_message


def test_force_push_feature_branch_allowed(kernel_guard):
    exit_code, _ = kernel_guard.evaluate_payload(
        _bash("git push --force origin feature/x")
    )
    assert exit_code == 0


# --- Rule 3: sensitive file --------------------------------------------------


def test_sensitive_env_read_blocked(kernel_guard):
    exit_code, stderr_message = kernel_guard.evaluate_payload(
        _file_tool("Read", ".env")
    )
    assert exit_code == 2
    assert "BLOCKED" in stderr_message
    assert "sensitive" in stderr_message.lower() or ".env" in stderr_message


def test_env_example_read_allowed(kernel_guard):
    exit_code, _ = kernel_guard.evaluate_payload(
        _file_tool("Read", ".env.example")
    )
    assert exit_code == 0


def test_credentials_write_blocked(kernel_guard):
    exit_code, _ = kernel_guard.evaluate_payload(
        _file_tool("Write", "credentials.json")
    )
    assert exit_code == 2


def test_normal_file_read_allowed(kernel_guard):
    exit_code, _ = kernel_guard.evaluate_payload(
        _file_tool("Read", "src/main.py")
    )
    assert exit_code == 0


# --- v0.16.0 fail-CLOSED invariant on missing config -------------------------


def test_missing_config_still_blocks_rm_rf_root(kernel_guard, tmp_path):
    """**Codex-review invariant lock**: kernel guard MUST NOT fail-open
    when athanor.json is missing.

    The ``kernel_guard`` fixture chdirs to a temporary directory with no
    athanor.json present and clears ``CLAUDE_PROJECT_DIR``. ``rm -rf /``
    must still block (exit 2) because the runtime helper defaults
    ``profile`` to ``"standard"`` whenever config lookup fails.
    """
    # Sanity: confirm there is no athanor.json reachable from this cwd.
    # The runtime helper walks up to .git or $HOME; this tmp_path is
    # outside the repo tree, so no athanor.json is found.
    assert not (tmp_path / "athanor.json").exists()

    exit_code, stderr_message = kernel_guard.evaluate_payload(
        _bash("rm -rf /")
    )
    assert exit_code == 2, (
        f"rm -rf / must block even with missing athanor.json "
        f"(fail-CLOSED invariant); got exit_code={exit_code} "
        f"stderr_message={stderr_message!r}"
    )
    assert "BLOCKED" in stderr_message


def test_missing_config_still_blocks_force_push(kernel_guard):
    """Same fail-CLOSED invariant, applied to Rule 2 (force-push)."""
    exit_code, _ = kernel_guard.evaluate_payload(
        _bash("git push --force origin main")
    )
    assert exit_code == 2


def test_missing_config_still_blocks_sensitive_read(kernel_guard):
    """Same fail-CLOSED invariant, applied to Rule 3 (sensitive file)."""
    exit_code, _ = kernel_guard.evaluate_payload(
        _file_tool("Read", ".env")
    )
    assert exit_code == 2


# --- profile=off opt-out ----------------------------------------------------


def test_profile_off_bypasses_kernel_guard(monkeypatch, tmp_path):
    """When ``hooks.profile == "off"`` the gate must exit 0 even for
    ``rm -rf /`` — same legacy opt-out semantics as the other hook scripts."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "athanor.json").write_text(
        json.dumps({"hooks": {"profile": "off"}}), encoding="utf-8"
    )
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project_dir))
    monkeypatch.chdir(project_dir)

    if "pretool_kernel_guard" in sys.modules:
        del sys.modules["pretool_kernel_guard"]
    module = importlib.import_module("pretool_kernel_guard")

    exit_code, stderr_message = module.evaluate_payload(_bash("rm -rf /"))
    assert exit_code == 0, (
        f"profile=off must bypass even for rm -rf /, got "
        f"exit_code={exit_code} stderr_message={stderr_message!r}"
    )
    assert stderr_message == ""


# --- Malformed payload shapes -----------------------------------------------


def test_non_dict_payload_failopen(kernel_guard):
    """Non-dict payload yields fail-open ``(0, "")`` — matches v0.16.0 CLI."""
    exit_code, stderr_message = kernel_guard.evaluate_payload(
        "this is not a dict"  # type: ignore[arg-type]
    )
    assert exit_code == 0
    assert stderr_message == ""


def test_missing_tool_name_failopen(kernel_guard):
    exit_code, _ = kernel_guard.evaluate_payload({"tool_input": {}})
    assert exit_code == 0


def test_unknown_tool_failopen(kernel_guard):
    exit_code, _ = kernel_guard.evaluate_payload(
        {"tool_name": "SomeUnknownTool", "tool_input": {"x": 1}}
    )
    assert exit_code == 0


def test_bash_empty_command_failopen(kernel_guard):
    exit_code, _ = kernel_guard.evaluate_payload(_bash(""))
    assert exit_code == 0


# --- main() CLI entry preserved (smoke) -------------------------------------


def test_main_entry_point_still_exists(kernel_guard):
    """``main()`` is the v0.16.0 CLI entry; v0.18.0 keeps it and delegates
    to ``evaluate_payload``. The 23 subprocess-driven tests in
    ``test_regression_v016_pretool_kernel_guard.py`` cover end-to-end
    behavior; this test simply locks the public symbol so the dispatcher
    coexists with the CLI path."""
    assert hasattr(kernel_guard, "main")
    assert callable(kernel_guard.main)


def test_project_root_parameter_accepted(kernel_guard, tmp_path):
    """Signature accepts ``project_root`` as documented in the docstring.

    The current implementation does not yet override config resolution
    from this argument (the runtime helper owns the lookup), but the
    keyword must be accepted so the v0.18.0 dispatcher can pass it
    without TypeError. Future per-call overrides will land on this
    parameter.
    """
    exit_code, _ = kernel_guard.evaluate_payload(
        _bash("echo hello"), project_root=tmp_path
    )
    assert exit_code == 0
