#!/usr/bin/env python3
"""
Athanor v0.17.0 shared hook runtime — minimalist helpers used by both
`stop_verify_claims.py` and `pretool_kernel_guard.py`.

Per S06 scope (minimalist, Plan B-adopted):
  1. `read_stdin_payload()` — parse PreToolUse/Stop event JSON from stdin.
     Fail-open on malformed. Returns dict or None.
  2. `read_athanor_config()` — walk up from cwd to find athanor.json.
     Stops at .git boundary (v0.7.9 parent-dir hijack guard). Returns
     parsed dict or {} on any error.
  3. `is_hook_profile_off(config)` — returns True if
     `hooks.profile == "off"`. Used by all hooks for opt-out.
  4. `resolve_project_root()` — walk-up to find .git or athanor.json.
     Returns Path or None.

DESIGN PRINCIPLES (per C1 conflict resolution adopting Plan B):
  - No framework, no class hierarchy — bare module-level helpers.
  - No new behavior, no new policy. Each helper is a tightening of the
    minimal common slice between the two existing scripts.
  - Per-script defensive elaborations (audit-breadcrumb mechanisms,
    snapshot detection, etc.) STAY in their scripts. This module is the
    common floor, not a kitchen sink.

The hooks remain stdlib-only and importable as a sibling module via the
`SCRIPTS_DIR` sys.path insertion the scripts already perform.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ATHANOR_CONFIG_NAME = "athanor.json"
_WALK_UP_DEPTH = 8


# ---------------------------------------------------------------------------
# 1. read_stdin_payload
# ---------------------------------------------------------------------------


def read_stdin_payload() -> dict | None:
    """Read a Claude Code hook event payload from stdin.

    Returns the parsed dict, or ``None`` on any of:
      - stdin is a TTY (interactive invocation, not a hook event)
      - read error (OSError / ValueError)
      - empty body
      - JSON parse failure
      - JSON parses to a non-dict (events are always objects)

    Fail-open contract: a misconfigured pipeline must NOT brick the
    caller's session — callers translate ``None`` into ``exit 0``.
    """
    try:
        if sys.stdin.isatty():
            return None
    except (OSError, ValueError):
        # Some fake stdins don't implement isatty cleanly; tolerate it.
        pass
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


# ---------------------------------------------------------------------------
# 2. read_athanor_config / 4. resolve_project_root
# ---------------------------------------------------------------------------


def _walk_up_for(marker_check) -> Path | None:
    """Internal: walk up from cwd, invoking `marker_check(path)` per level.
    The first level where `marker_check` returns truthy wins; the returned
    Path is that level.

    Bounded by:
      - depth `_WALK_UP_DEPTH` (8)
      - $HOME
      - filesystem root
      - .git boundary (callers may treat .git as a stop themselves; this
        helper itself does not stop at .git — leaving that decision to the
        marker_check)
    """
    try:
        cur = Path.cwd().resolve()
    except (OSError, FileNotFoundError):
        return None
    try:
        home = Path.home().resolve()
    except (OSError, RuntimeError):
        home = None

    for _ in range(_WALK_UP_DEPTH):
        if marker_check(cur):
            return cur
        if home is not None and cur == home:
            break
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def resolve_project_root() -> Path | None:
    """Walk up from cwd to the first directory containing either ``.git/``
    or ``athanor.json``. Returns that Path, or ``None`` if nothing found
    within the walk-up bounds.

    Used by callers that want a stable reference dir (e.g., for resolving
    session paths). Does NOT consult ``$CLAUDE_PROJECT_DIR`` — that's
    config-resolution policy, kept inside the scripts that need it.
    """
    def _is_root(p: Path) -> bool:
        return (p / ".git").is_dir() or (p / ATHANOR_CONFIG_NAME).is_file()
    return _walk_up_for(_is_root)


def read_athanor_config() -> dict:
    """Locate the project's athanor.json (walk-up from cwd, stop at .git
    boundary upward) and return the parsed dict.

    Returns ``{}`` (never ``None``) on any of:
      - no athanor.json found within walk-up bounds
      - file read error
      - JSON parse error
      - top-level isn't an object

    v0.7.9 parent-dir hijack guard: walk-up STOPS at .git/ — an
    athanor.json above the repo root is NOT picked up from inside the
    repo.
    """
    config_path = _find_athanor_config_path()
    if config_path is None:
        return {}
    try:
        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def _find_athanor_config_path() -> Path | None:
    """Locate athanor.json with the v0.7.9 parent-dir hijack guard
    (walk-up stops at .git boundary upward).

    Resolution priority:
      1. ``$CLAUDE_PROJECT_DIR/athanor.json`` if env var set and file exists.
      2. Walk up from cwd; stop at .git boundary, $HOME, or depth 8.
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

    for _ in range(_WALK_UP_DEPTH):
        candidate = cur / ATHANOR_CONFIG_NAME
        has_git = (cur / ".git").is_dir()
        if candidate.is_file():
            return candidate
        if has_git:
            # Hit a .git boundary without finding athanor.json at this
            # level. Do NOT cross repo root upward (v0.7.8 hijack lesson).
            return None
        if home is not None and cur == home:
            break
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


# ---------------------------------------------------------------------------
# 3. is_hook_profile_off
# ---------------------------------------------------------------------------


def is_hook_profile_off(config) -> bool:
    """Return True iff the supplied athanor.json dict has
    ``hooks.profile == "off"``.

    Defensive on shape — non-dict ``config`` or non-dict ``hooks`` section
    or non-string ``profile`` returns False (NOT off, gate stays active).
    """
    if not isinstance(config, dict):
        return False
    hooks_section = config.get("hooks")
    if not isinstance(hooks_section, dict):
        return False
    profile = hooks_section.get("profile")
    if not isinstance(profile, str):
        return False
    return profile == "off"
