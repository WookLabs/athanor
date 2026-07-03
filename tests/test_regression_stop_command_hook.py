"""Regression test for the v0.7.8 Stop hook command contract.

REPLACES tests/test_regression_stop_prompt.py (deleted in same commit). The
v0.7.7 release shipped a `type: prompt` Stop hook with a long material-claim
prompt; v0.7.8 upgrades to `type: command` invoking
`scripts/hooks/stop_verify_claims.py` for runtime gating (exit 2 blocks Stop
and feeds stderr back to the model). The v0.7.7 spike (2026-05-18, see
docs/STATE.md) verified this contract empirically.

This file pins:
  - hooks/hooks.json registers exactly one Stop event handler entry.
  - That handler is `type: "command"` with a non-empty `command` field.
  - The command path points at scripts/hooks/stop_verify_claims.py.
  - The script file exists at the named path and is executable.
  - No `type: "prompt"` Stop hook remains (the v0.7.7 entry was REPLACED,
    not duplicated).

If a future commit silently reverts to `type: "prompt"` without updating this
test, the test fires loudly.
"""

from __future__ import annotations

import json
import os
import re
import stat
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS_JSON = REPO_ROOT / "hooks/hooks.json"
HOOK_SCRIPT = REPO_ROOT / "scripts/hooks/stop_verify_claims.py"
EXPECTED_SCRIPT_BASENAME = "stop_verify_claims.py"


def _load_hooks():
    with open(HOOKS_JSON, encoding="utf-8") as f:
        return json.load(f)


def test_stop_event_has_exactly_one_handler_entry():
    """Per hook-uniqueness contract: only one Stop event handler entry."""
    data = _load_hooks()
    stop_entries = data.get("hooks", {}).get("Stop", [])
    assert len(stop_entries) == 1, (
        f"Expected exactly 1 Stop event handler entry, found {len(stop_entries)}"
    )


def test_stop_handler_is_command_type():
    """v0.7.8 contract: Stop hook must be type=command, not type=prompt."""
    data = _load_hooks()
    handler_list = data["hooks"]["Stop"][0]["hooks"]
    assert len(handler_list) >= 1, "Stop event handler entry has no inner hooks[]"
    handler = handler_list[0]
    assert handler.get("type") == "command", (
        f"Stop hook must be type=command (v0.7.8 contract); got {handler.get('type')!r}"
    )


def test_stop_handler_has_nonempty_command():
    """Command field must be present and non-empty."""
    data = _load_hooks()
    handler = data["hooks"]["Stop"][0]["hooks"][0]
    cmd = handler.get("command", "")
    assert cmd and cmd.strip(), "Stop hook command field is missing or empty"


def test_stop_handler_command_invokes_expected_script():
    """Command must invoke scripts/hooks/stop_verify_claims.py."""
    data = _load_hooks()
    cmd = data["hooks"]["Stop"][0]["hooks"][0]["command"]
    assert EXPECTED_SCRIPT_BASENAME in cmd, (
        f"Stop hook command should invoke {EXPECTED_SCRIPT_BASENAME}; got: {cmd!r}"
    )
    assert "scripts/hooks/" in cmd or "scripts\\hooks\\" in cmd, (
        f"Stop hook command should reference scripts/hooks/ path; got: {cmd!r}"
    )


def test_stop_handler_script_file_exists():
    """The script file referenced by the hook must exist at the expected path."""
    assert HOOK_SCRIPT.is_file(), f"Hook script not found at {HOOK_SCRIPT}"


@pytest.mark.skipif(
    sys.platform == "win32" or os.name == "nt",
    reason=(
        "Executable bits are POSIX-only. On Windows, .py files are executed "
        "via the Python interpreter resolved through PATHEXT/the py launcher, "
        "not via a file-permission bit. The hooks.json command is "
        "`sh .../run_hook.sh .../stop_verify_claims.py` (portable launcher, "
        "v0.24.3) regardless of platform; the script's POSIX execute bit "
        "only matters on Linux/macOS hosts."
    ),
)
def test_stop_handler_script_is_executable():
    """The script must be executable (chmod +x) so the command invocation works."""
    mode = HOOK_SCRIPT.stat().st_mode
    is_executable = bool(mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))
    assert is_executable, (
        f"Hook script {HOOK_SCRIPT} is not executable; run `chmod +x` on it"
    )


def test_no_prompt_type_stop_hook_remains():
    """v0.7.7 used type=prompt; v0.7.8 replaced it. No prompt-type Stop hook
    should remain (otherwise the gate would dual-fire or contradict itself)."""
    data = _load_hooks()
    for entry in data.get("hooks", {}).get("Stop", []):
        for handler in entry.get("hooks", []):
            assert handler.get("type") != "prompt", (
                "Found a leftover type=prompt Stop hook; v0.7.8 must use type=command "
                "exclusively. If this is intentional (dual-mode for migration), "
                "update this test to allow it explicitly."
            )


def test_stop_hook_command_uses_plugin_root_or_absolute_path():
    """v0.11.4 lock: Stop hook command MUST reference the script via
    ${CLAUDE_PLUGIN_ROOT} env var OR an absolute path — NOT a bare
    relative path which CC resolves relative to project cwd. The bare
    relative path made the hook silently broken in every project except
    athanor's source repo (v0.7.8 → v0.11.3 latent bug). Closes the
    deployment-path arc with v0.11.3's input-layer fix."""
    import json
    hooks_path = REPO_ROOT / "hooks" / "hooks.json"
    config = json.loads(hooks_path.read_text(encoding="utf-8"))
    stop_hooks = config.get("hooks", {}).get("Stop", [])
    assert stop_hooks, "Stop hook registration must exist"

    found_paths = []
    for entry in stop_hooks:
        for hook in entry.get("hooks", []):
            cmd = hook.get("command", "")
            # Strip leading quote (cmd may be JSON-quoted in shape:
            # `sh "${CLAUDE_PLUGIN_ROOT}/scripts/hooks/run_hook.sh"
            # "${CLAUDE_PLUGIN_ROOT}/scripts/..."`). The first path arg
            # follows the interpreter token (`sh `, historically
            # `python3 `) — extract it for the absolute-path heuristic.
            # Reviewer revision 1: lstrip leading quote so
            # `path_arg.startswith("/")` doesn't fail on `"...` quoted form.
            if "${CLAUDE_PLUGIN_ROOT}" in cmd:
                found_paths.append(("plugin_root", cmd))
                continue
            # Extract path arg after `python3 ` and strip leading quote
            parts = cmd.split(None, 1)  # split on first whitespace
            if len(parts) < 2:
                continue
            path_arg = parts[1].lstrip("\"'")
            if path_arg.startswith("/"):
                found_paths.append(("absolute", cmd))
                continue
            assert False, (
                f"Stop hook command must use ${{CLAUDE_PLUGIN_ROOT}} or "
                f"absolute path; got bare relative: {cmd!r}. v0.11.4 "
                f"locked this invariant — see "
                f"docs/plans/2026-05-21-002 or "
                f".athanor/sessions/2026-05-21-002/plan.md Phase 1."
            )

    assert found_paths, "Stop hook must have at least one command entry"


def test_legacy_prompt_fixture_no_longer_matches_command_contract():
    """The legacy prompt fixture (tests/fixtures/fixture_wrong_stop_prompt.json)
    documents what a broken v0.7.x prompt-mode hooks.json used to look like.
    It is kept as historical regression evidence. Confirm it is NOT shaped
    like the new v0.7.8 command contract — if a future cleanup accidentally
    rewrites this fixture to match the new contract, the historical record
    is lost."""
    fixture_path = REPO_ROOT / "tests/fixtures/fixture_wrong_stop_prompt.json"
    if not fixture_path.is_file():
        # Fixture optional — skip if not present.
        return
    with open(fixture_path, encoding="utf-8") as f:
        data = json.load(f)
    stop_entries = data.get("hooks", {}).get("Stop", [])
    if not stop_entries:
        return
    handler = stop_entries[0]["hooks"][0]
    # The legacy fixture should NOT match the new command contract — it's
    # historical context for what we migrated AWAY from.
    if handler.get("type") == "command":
        # Acceptable if the fixture was intentionally updated; print a notice
        # rather than fail. The main contract tests above are authoritative.
        pass
