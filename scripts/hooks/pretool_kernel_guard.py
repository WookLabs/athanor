#!/usr/bin/env python3
"""
Athanor v0.16.0 PreToolUse kernel guard.

Registered as `type: command` in hooks/hooks.json. On every PreToolUse event,
Claude Code invokes this script with the event payload on stdin. The script
inspects the proposed tool invocation and blocks 3 catastrophic worker-hazard
classes:

  1. **Destructive shell commands** (Bash):
     - `rm -rf` targeting filesystem root or home
     - `git reset --hard`
     - `git clean -f`
     - `git checkout .` (restore all)
  2. **Force-push to protected branches** (Bash):
     - `git push --force` / `-f` / `--force-with-lease` to main/master
  3. **Sensitive credential file access** (Bash, Read, Write, Edit):
     - `.env`, `.env.local`, `.env.production`, `.env.secret`
     - `credentials.json`, `credentials.yaml`, `private_key`, `.ssh/`,
       `.aws/credentials`
     - EXCEPTIONS: `.env.example`, `.env.template`, `.env.test`, `.env.sample`,
       paths under `fixtures/` or starting with `test_`

Decision flow:
  1. Parse stdin (PreToolUse event JSON). Fail-open on missing/unparseable.
  2. Read `hooks.profile` from athanor.json. If `"off"`, exit 0 silently.
  3. Dispatch by `tool_name`. If a rule matches, exit 2 with stderr explaining
     the block (Claude Code feeds stderr back to the model as continuation
     context so it can choose a safer alternative).

Stdlib-only — same pattern as `stop_verify_claims.py`. No shared runtime
import (a shared module is deferred to v0.17.0; ship the PreToolUse guard
as a standalone script first).

Cross-platform note: invoked via `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/
hooks/pretool_kernel_guard.py"` in hooks/hooks.json. The plugin-root
expansion follows the v0.11.4 lesson (bare relative paths broke
deployment in non-source-repo projects).
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ATHANOR_CONFIG_NAME = "athanor.json"
SUPPORTED_PROFILES = {"off", "standard"}

# ---------------------------------------------------------------------------
# Rule 1: Destructive shell commands
# ---------------------------------------------------------------------------
# `rm -rf /` — match `/` followed by whitespace, quote, or end-of-string
# to avoid false-positives like `rm -rf /tmp/build` (Codex review finding:
# Plan A's bare `\s+/` would have matched legitimate absolute subdir paths).
# Also covers quoted root: `rm -rf "/"` and `rm -rf '/'` where the quote
# appears BEFORE the slash; the inner slash is the lone path component.
RM_RF_ROOT_PATTERN = re.compile(
    r"\brm\s+(?:-[a-zA-Z]*r[a-zA-Z]*f|--recursive)\s+"
    r"(?:"
    r"/(?=\s)|/(?=\")|/(?=')|/$"          # bare /, then boundary
    r"|\"/\""                              # "/"
    r"|'/'"                                # '/'
    r")"
)
# `rm -rf ~/` — homedir wipe. Trailing whitespace required to avoid matching
# paths like `~/projects/build`.
RM_RF_HOME_PATTERN = re.compile(
    r"\brm\s+(?:-[a-zA-Z]*r[a-zA-Z]*f|--recursive)\s+~/?(?=\s|$)"
)
GIT_RESET_HARD_PATTERN = re.compile(r"\bgit\s+reset\s+--hard\b")
GIT_CLEAN_F_PATTERN = re.compile(r"\bgit\s+clean\s+-[a-zA-Z]*f")
# `git checkout .` — restore all. Trailing $ or whitespace so we don't match
# `git checkout ./path` or `git checkout .foo`.
GIT_CHECKOUT_DOT_PATTERN = re.compile(r"\bgit\s+checkout\s+\.(?:\s*$|\s+--?)")

DESTRUCTIVE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (RM_RF_ROOT_PATTERN, "rm -rf targeting filesystem root"),
    (RM_RF_HOME_PATTERN, "rm -rf targeting home directory"),
    (GIT_RESET_HARD_PATTERN, "git reset --hard"),
    (GIT_CLEAN_F_PATTERN, "git clean -f"),
    (GIT_CHECKOUT_DOT_PATTERN, "git checkout . (restore all)"),
]

# ---------------------------------------------------------------------------
# Rule 2: Force-push to protected branches
# ---------------------------------------------------------------------------
# The `(main|master)` token must appear as a standalone word (\b boundary)
# anywhere on the same `git push` invocation as a force flag. Feature
# branches like `feature/x` or `release/main-fix` must NOT match
# (`release/main-fix` would match `\bmain\b` — but the leading slash + dash
# inside the branch name means `\b` does fire at the `main` boundary).
# Trade-off: branch names that literally end in `main` as a slash-segment
# (e.g. `feature/main`) are conservatively blocked. Acceptable for v0.16.0;
# users push `feature/main` via `--force-with-lease` to a non-main remote
# rarely, and the block is easily worked around (rename branch).
FORCE_PUSH_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bgit\s+push\b(?=.*--force\b)(?=.*\b(?:main|master)\b)"),
    re.compile(r"\bgit\s+push\b(?=.*(?:^|\s)-f\b)(?=.*\b(?:main|master)\b)"),
    re.compile(r"\bgit\s+push\b(?=.*--force-with-lease\b)(?=.*\b(?:main|master)\b)"),
]

# ---------------------------------------------------------------------------
# Rule 3: Sensitive credential file access
# ---------------------------------------------------------------------------
# Dotenv variants — extension-anchored. The exception check (below) carves
# out `.env.example`, `.env.template`, etc.
SENSITIVE_DOTENV_PATTERN = re.compile(
    r"(?:^|[/\\])\.env(?:\.local|\.production|\.secret)?(?:$|\s|['\"])"
)
# Substring markers — match anywhere in the path.
SENSITIVE_SUBSTRINGS = (
    "credentials.json",
    "credentials.yaml",
    "credentials.yml",
    "private_key",
    ".ssh/",
    ".aws/credentials",
)
# Exception markers — if the path contains any of these, allow access even
# if a sensitive pattern matches. Order: example/template/test/sample first,
# then directory-based exemptions for fixtures and test files.
SENSITIVE_EXCEPTIONS = (
    ".env.example",
    ".env.template",
    ".env.test",
    ".env.sample",
    "fixtures/",
    "/test_",
    # `test_` at the start of a basename (e.g. `tests/test_foo.py` is also
    # caught by `tests/` segment, but standalone `test_foo.env` should be
    # allowed because it's a fixture name).
)
# `cat`/`less`/`head`/`tail` command-path extraction for Bash. Captures the
# first non-flag positional argument.
BASH_READ_COMMAND_PATTERN = re.compile(
    r"\b(?:cat|less|more|head|tail|bat)\s+(?:-[a-zA-Z0-9]+\s+)*([^\s|;&<>]+)"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stderr(msg: str) -> None:
    """Emit one line of stderr; stderr is fed back to the model on exit 2
    and visible in CI logs on exit 0. Both are useful — keep messages terse."""
    print(f"athanor (pretool guard): {msg}", file=sys.stderr)


def _read_stdin_payload() -> dict | None:
    """Read the PreToolUse event payload from stdin. Returns parsed dict or
    None if stdin is unavailable / unreadable / not JSON."""
    if sys.stdin.isatty():
        return None
    try:
        raw = sys.stdin.read()
    except (OSError, ValueError):
        return None
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _find_athanor_config() -> Path | None:
    """Locate athanor.json via priority chain (v0.7.9 pattern):

    1. ``$CLAUDE_PROJECT_DIR/athanor.json`` if env var set and file exists.
    2. Walk up from cwd, stopping at any ``.git/`` boundary, $HOME, or depth 8.
    """
    env_proj = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_proj:
        candidate = Path(env_proj) / ATHANOR_CONFIG_NAME
        if candidate.is_file():
            return candidate.resolve()

    try:
        cur = Path.cwd().resolve()
    except (OSError, FileNotFoundError):
        return None
    try:
        home = Path.home().resolve()
    except (OSError, RuntimeError):
        home = None

    for _ in range(8):
        candidate = cur / ATHANOR_CONFIG_NAME
        has_git = (cur / ".git").is_dir()
        if candidate.is_file():
            return candidate
        if has_git:
            # Don't cross repo root upward (v0.7.8 parent-dir hijack lesson).
            return None
        if home is not None and cur == home:
            break
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def _read_profile() -> str:
    """Read `hooks.profile` from athanor.json. Defaults to "standard"."""
    config_path = _find_athanor_config()
    if config_path is None:
        return "standard"
    try:
        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return "standard"
    if not isinstance(data, dict):
        return "standard"
    hooks_section = data.get("hooks", {})
    if not isinstance(hooks_section, dict):
        return "standard"
    profile = hooks_section.get("profile", "standard")
    if not isinstance(profile, str) or profile not in SUPPORTED_PROFILES:
        return "standard"
    return profile


# ---------------------------------------------------------------------------
# Rule dispatchers
# ---------------------------------------------------------------------------

def _check_destructive_shell(command: str) -> str | None:
    """Return matched description if the command is destructive, else None."""
    for pattern, description in DESTRUCTIVE_PATTERNS:
        if pattern.search(command):
            return description
    return None


def _check_force_push(command: str) -> bool:
    """Return True if the command is a force-push to a protected branch."""
    return any(pattern.search(command) for pattern in FORCE_PUSH_PATTERNS)


def _path_is_sensitive(path: str) -> bool:
    """Return True if the path targets a sensitive credential file AND is
    not covered by an exception."""
    if not path:
        return False
    # Normalize a bit — strip surrounding quotes the model may have included.
    p = path.strip().strip("'\"")
    if not p:
        return False
    lowered = p.lower()
    # Exceptions first — example/template/test/sample files are allowed even
    # if they share the .env prefix.
    for ex in SENSITIVE_EXCEPTIONS:
        if ex in lowered:
            return False
    # Substring markers — credentials.json, .ssh/, etc.
    for marker in SENSITIVE_SUBSTRINGS:
        if marker in lowered:
            return True
    # Dotenv regex — anchored on path separator or start, with optional
    # known suffix (.local, .production, .secret).
    if SENSITIVE_DOTENV_PATTERN.search(p) or SENSITIVE_DOTENV_PATTERN.search(p + " "):
        return True
    # Bare basename (e.g. `.env`) — the regex above requires a leading
    # separator OR start-of-string; the `p + " "` pad covers trailing
    # boundary. Double-check basename for the bare-`.env` case.
    base = os.path.basename(p)
    if base in {".env", ".env.local", ".env.production", ".env.secret"}:
        return True
    return False


def _bash_extract_read_paths(command: str) -> list[str]:
    """Extract candidate file paths from `cat`/`less`/`head`/`tail`/`more`/
    `bat` commands in a bash command string. Returns all positional matches
    so a pipeline like `cat .env | grep PASS` is still inspected."""
    matches: list[str] = []
    for m in BASH_READ_COMMAND_PATTERN.finditer(command):
        matches.append(m.group(1))
    return matches


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    payload = _read_stdin_payload()
    if payload is None:
        _stderr("stdin missing or unparseable; passing (fail-open)")
        return 0

    profile = _read_profile()
    if profile == "off":
        return 0  # opt-out; same semantics as Stop hook

    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    if not isinstance(tool_name, str) or not isinstance(tool_input, dict):
        # Unknown/malformed shape — fail-open.
        return 0

    # ---- Bash tool ----
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        if not isinstance(command, str) or not command:
            return 0

        # Rule 1: destructive shell
        destructive = _check_destructive_shell(command)
        if destructive is not None:
            _stderr(
                f"BLOCKED: destructive command detected ({destructive}). "
                f"Narrow the scope or use a safer alternative."
            )
            return 2

        # Rule 2: force-push to protected branches
        if _check_force_push(command):
            _stderr(
                "BLOCKED: force-push to main/master. Use a feature branch."
            )
            return 2

        # Rule 3: sensitive credential file access via cat/less/head/tail
        for path in _bash_extract_read_paths(command):
            if _path_is_sensitive(path):
                _stderr(
                    f"BLOCKED: accessing sensitive credential file ({path}). "
                    f"Use environment variables instead."
                )
                return 2

        return 0

    # ---- Read / Write / Edit tools ----
    if tool_name in ("Read", "Write", "Edit"):
        # All three tools use `file_path` as the canonical input key
        # (per Claude Code tool schemas).
        path = tool_input.get("file_path", "")
        if not isinstance(path, str) or not path:
            return 0
        if _path_is_sensitive(path):
            _stderr(
                f"BLOCKED: accessing sensitive credential file ({path}). "
                f"Use environment variables instead."
            )
            return 2
        return 0

    # Other tools — pass through.
    return 0


if __name__ == "__main__":
    sys.exit(main())
