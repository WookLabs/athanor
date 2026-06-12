#!/usr/bin/env python3
"""
Athanor v0.17.0 shared hook runtime — minimalist helpers used by both
`stop_verify_claims.py` and `pretool_kernel_guard.py`.

Surface (items 1–4 are the original S06 scope, minimalist, Plan B-adopted;
5–6 were added by later audit rounds):
  1. `read_stdin_payload()` — parse PreToolUse/Stop event JSON from stdin.
     Fail-open on malformed. Returns dict or None.
  2. `read_athanor_config()` — walk up from cwd to find athanor.json.
     Stops at .git boundary (v0.7.9 parent-dir hijack guard). Returns
     parsed dict or {} on any error.
  3. `is_hook_profile_off(config)` — returns True if
     `hooks.profile == "off"`. Used by all hooks for opt-out.
  4. `resolve_project_root()` — walk-up to find .git or athanor.json.
     Returns Path or None. Memoized on (cwd, $HOME) (v0.18.8 M7).
  5. `_walk_up(...) -> WalkResult` — the unified bounded walk-up core
     (v0.18.8 P1) behind 2./4. here and hook_state's `_athanor_opt_in` /
     `_project_dir`; the frozen `WalkResult` record preserves each call
     site's divergent `.git`/`$HOME`-stop disposition.
  6. `WRITE_TOOLS` / `extract_target_path(tool_name, tool_input)` — the
     mutating-tool name tuple + per-tool target-path extraction shared by
     the PreToolUse guards (kernel cred gate, freeze write gate).

DESIGN PRINCIPLES (per C1 conflict resolution adopting Plan B):
  - No framework, no class hierarchy beyond the single frozen `WalkResult`
    result dataclass — otherwise bare module-level helpers.
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
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable, Optional

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


@dataclass(frozen=True)
class WalkResult:
    """Outcome of a single ``_walk_up`` traversal.

    Fields:
      - ``match``: the first directory where ``marker_check`` returned truthy,
        or ``None`` if the walk halted (depth / git / home / fs-root) without
        a hit.
      - ``stopped_at_git``: True iff the walk halted because it reached a
        ``.git/`` boundary (only possible when ``stop_at_git=True``).
      - ``stopped_at_home``: True iff the walk halted at ``$HOME`` (only
        possible when ``stop_at_home=True``).

    The three fields let the four call sites recover their *divergent*
    ``.git``-hit dispositions over ONE walker without collapsing them:
    ``_find_athanor_config_path`` returns ``None`` on a git stop,
    ``resolve_project_root`` never stops at git, ``_athanor_opt_in`` maps a
    git stop to ``False``, and ``_project_dir`` maps a git stop to a
    ``start.resolve()`` boundary fallback. A bare ``match`` would erase that
    distinction; the flags preserve it.
    """

    match: Optional[Path]
    stopped_at_git: bool
    stopped_at_home: bool


def _walk_up(
    start: Path | None = None,
    marker_check: Callable[[Path], bool] | None = None,
    *,
    stop_at_git: bool,
    stop_at_home: bool,
    depth: int = _WALK_UP_DEPTH,
) -> WalkResult:
    """Walk up from ``start`` (default ``cwd``), invoking ``marker_check`` per
    level, returning a :class:`WalkResult`.

    Order of checks at each level (this ordering is contractual — the marker
    is consulted BEFORE the git/home stops so an ``athanor.json`` AT a
    ``.git`` boundary, or a ``.git`` dir used as a *marker*, is still found):

      1. ``marker_check(cur)`` truthy → ``WalkResult(match=cur, ...)``.
      2. ``stop_at_git`` and ``cur/.git`` is a dir → halt,
         ``WalkResult(match=None, stopped_at_git=True, ...)``.
      3. ``stop_at_home`` and ``cur == $HOME`` → halt,
         ``WalkResult(match=None, stopped_at_home=True)``.
      4. filesystem root (``cur.parent == cur``) → halt, no flags.

    Bounded by ``depth`` levels (default ``_WALK_UP_DEPTH`` — the SOLE named
    walk-up depth constant). All four of ``_walk_up``'s unified call sites
    flow their bound from here; no ``range(8)`` literal survives at any of
    them (the Stop-hook and capability-probe walkers retain their own
    independent loops — out of this consolidation's scope).
    """
    if marker_check is None:  # pragma: no cover - defensive; all callers pass one
        raise TypeError("_walk_up requires a marker_check callable")
    if start is None:
        start = Path.cwd()
    try:
        cur = start.resolve()
    except (OSError, FileNotFoundError):
        return WalkResult(match=None, stopped_at_git=False, stopped_at_home=False)
    try:
        home = Path.home().resolve()
    except (OSError, RuntimeError):
        home = None

    for _ in range(depth):
        if marker_check(cur):
            return WalkResult(
                match=cur, stopped_at_git=False, stopped_at_home=False
            )
        if stop_at_git and (cur / ".git").is_dir():
            return WalkResult(
                match=None, stopped_at_git=True, stopped_at_home=False
            )
        if stop_at_home and home is not None and cur == home:
            return WalkResult(
                match=None, stopped_at_git=False, stopped_at_home=True
            )
        if cur.parent == cur:
            break
        cur = cur.parent
    return WalkResult(match=None, stopped_at_git=False, stopped_at_home=False)


@lru_cache(maxsize=None)
def _resolve_project_root_cached(cwd: str, home: str | None) -> Path | None:
    """Memoized core of :func:`resolve_project_root`, keyed on
    ``(cwd, $HOME)`` so the walk-up runs once per (cwd, home) pair.

    ``cwd`` / ``home`` are passed in as strings (hashable, and they form the
    cache identity), and the walk below starts from ``Path(cwd)`` — the same
    string that forms the cache key — so the memo key and the traversal
    origin are identical by construction.
    """

    def _is_root(p: Path) -> bool:
        return (p / ".git").is_dir() or (p / ATHANOR_CONFIG_NAME).is_file()

    # resolve_project_root historically does NOT stop at .git (git IS the
    # marker) and DOES respect the $HOME ceiling.
    return _walk_up(
        start=Path(cwd),
        marker_check=_is_root,
        stop_at_git=False,
        stop_at_home=True,
    ).match


def resolve_project_root() -> Path | None:
    """Walk up from cwd to the first directory containing either ``.git/``
    or ``athanor.json``. Returns that Path, or ``None`` if nothing found
    within the walk-up bounds.

    Memoized on ``(cwd, $HOME)`` (v0.18.8): the cache key is stable for the
    process lifetime, and hooks run as one-shot subprocesses, so the memo's
    production value is bounded — it guards against repeat resolution within
    a single hook process, not across events. Call
    ``resolve_project_root.cache_clear()`` to drop the memo if the repo
    layout can change under a long-lived process (tests do this).

    Used by callers that want a stable reference dir (e.g., for resolving
    session paths). Does NOT consult ``$CLAUDE_PROJECT_DIR`` — that's
    config-resolution policy, kept inside the scripts that need it.
    """
    try:
        cwd = str(Path.cwd())
    except (OSError, FileNotFoundError):
        return None
    home = os.environ.get("HOME")
    return _resolve_project_root_cached(cwd, home)


# Expose cache_clear on the public callable (the memo lives on the cached core).
resolve_project_root.cache_clear = _resolve_project_root_cached.cache_clear  # type: ignore[attr-defined]


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
      2. Walk up from cwd via the unified ``_walk_up`` (stop at .git boundary,
         $HOME, or depth ``_WALK_UP_DEPTH``). A .git or $HOME stop yields no
         match → ``None`` (the hijack guard: do not cross the repo root).
    """
    env_proj = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_proj:
        candidate = Path(env_proj) / ATHANOR_CONFIG_NAME
        if candidate.is_file():
            return candidate.resolve()

    def _has_config(p: Path) -> bool:
        return (p / ATHANOR_CONFIG_NAME).is_file()

    # match → the athanor.json-bearing dir; git/home stop → match is None.
    result = _walk_up(
        marker_check=_has_config, stop_at_git=True, stop_at_home=True
    )
    if result.match is None:
        return None
    return result.match / ATHANOR_CONFIG_NAME


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


# ---------------------------------------------------------------------------
# 5. WRITE_TOOLS / extract_target_path
# ---------------------------------------------------------------------------

# The mutating tool names a hook may want to treat uniformly when it inspects
# the file a tool is about to write. ``Read`` is deliberately EXCLUDED — it is
# not a write tool; callers that also care about reads (e.g. the kernel-guard
# credential check) keep ``Read`` as a separate, explicit reference rather than
# folding it in here.
WRITE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")


def extract_target_path(tool_name, tool_input) -> str | None:
    """Return the filesystem path a tool invocation targets.

    ``NotebookEdit`` carries its target under ``notebook_path``; every other
    tool (``Write``/``Edit``/``MultiEdit``/``Read``/…) uses ``file_path``.

    Returns the raw value from ``tool_input`` (a ``str`` when present). When
    the expected key is absent — or ``tool_input`` is not a mapping — returns
    ``None``, leaving the fail-open decision to the caller.
    """
    if not isinstance(tool_input, dict):
        return None
    key = "notebook_path" if tool_name == "NotebookEdit" else "file_path"
    return tool_input.get(key)
