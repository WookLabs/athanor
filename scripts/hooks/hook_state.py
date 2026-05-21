"""Per-session state helpers for the Stop-hook command script.

Athanor v0.7.9 introduces session-state files under
`.athanor/sessions/<id>/.hook-state/` to support:

  - **Nonce binding** (`nonce.json`): the verification-before-completion
    skill writes a fresh nonce + body-hash + timestamp on each invocation;
    `scripts/hooks/stop_verify_claims.py` reads, validates, and atomically
    deletes on successful Stop. Closes the v0.7.8 sentinel-forgery P0
    (review finding sec-001 / ADV-002): forging the sentinel now requires
    forging the state file with a matching SHA-256 body hash, raising
    bypass cost from "emit one string" to "compute hash + write JSON +
    emit sentinel".

  - **Circuit-breaker counter** (`stop-counter.json`): tracks consecutive
    exit-2 blocks per session. When the count exceeds `hooks.stopLoopThreshold`
    (default 3), the hook releases (exits 0) on the next invocation,
    breaking infinite-block loops when the verification skill misbehaves.
    Closes reliability rel-001 from PR #16 review.

Design notes:
  - All state writes are atomic via tempfile + os.replace (cross-platform
    safe; works on Windows where os.rename fails over existing files).
  - All reads tolerate missing/corrupt files (fall back to defaults).
  - Session IDs are whitelisted to `^[a-zA-Z0-9_-]+$` to prevent path
    traversal via crafted Stop event payloads.
  - State files are runtime artifacts; `.athanor/` is in `.gitignore`.

Forgery limitation: a model with file-system access can still write its
own state file and emit a matching sentinel. v0.7.9 raises forgery cost
substantially but does not eliminate it. Complete defense requires
Claude Code runtime transcript-event verification (deferred to v0.8.0+).
See docs/plans/2026-05-18-002-feat-v0.7.9-stop-hook-hardening-plan.md §KTD1.
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

# Whitelist for session IDs — anything outside this charset is rejected to
# prevent `../` traversal or shell metacharacter injection via crafted
# Stop event payloads.
SESSION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")

# Nonce TTL: a nonce older than this is treated as stale. Generous (60s)
# to tolerate normal latency between skill invocation and Stop event.
NONCE_TTL_SECONDS = 60

# Default counter threshold when hooks.stopLoopThreshold is unset or invalid.
DEFAULT_STOP_LOOP_THRESHOLD = 3


def _stderr(msg: str) -> None:
    """One-line stderr emit. Same convention as stop_verify_claims.py."""
    print(f"athanor (hook state): {msg}", file=sys.stderr)


def _project_dir(start: Path | None = None) -> Path | None:
    """Resolve project directory for state-file placement.

    Mirrors stop_verify_claims.py's config resolution but only needs to find
    a writable `.athanor/sessions/` parent. Walks up from `start` (default cwd)
    until it finds a `.athanor/` directory or hits a `.git/` boundary.
    Returns None if no suitable parent is found within depth 8.
    """
    if start is None:
        start = Path.cwd()
    cur = start.resolve()
    for _ in range(8):
        if (cur / ".athanor").is_dir():
            return cur
        if (cur / ".git").is_dir():
            # .git boundary — don't cross. If .athanor wasn't here, fall back
            # to cwd-as-project so we at least have somewhere to write state.
            return start.resolve()
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def _validate_session_id(session_id: str) -> bool:
    """Reject session IDs containing path traversal or shell metacharacters."""
    if not isinstance(session_id, str) or not session_id:
        return False
    if len(session_id) > 128:
        return False
    return bool(SESSION_ID_PATTERN.match(session_id))


def get_state_dir(session_id: str, project_root: Path | None = None) -> Path | None:
    """Return `.athanor/sessions/<session_id>/.hook-state/`, creating it if absent.

    Returns None if `session_id` fails validation or no project root can be
    found. Caller treats None as "no state available" and falls open.
    """
    if not _validate_session_id(session_id):
        _stderr(f"invalid session_id {session_id!r}; refusing to create state dir")
        return None
    root = project_root if project_root is not None else _project_dir()
    if root is None:
        return None
    state_dir = root / ".athanor" / "sessions" / session_id / ".hook-state"
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        _stderr(f"could not create {state_dir}: {e}")
        return None
    return state_dir


def _atomic_write_json(path: Path, data: dict) -> bool:
    """Write `data` to `path` atomically via tempfile + os.replace.

    Returns True on success, False on any I/O error (caller logs + falls open).
    """
    try:
        # NamedTemporaryFile in the same dir guarantees atomic rename works
        # (cross-device renames would fail).
        fd, tmp_path = tempfile.mkstemp(
            prefix=".tmp-", suffix=".json", dir=str(path.parent)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f)
            os.replace(tmp_path, path)
            return True
        except OSError:
            # Clean up tempfile on failure
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    except OSError as e:
        _stderr(f"could not write {path}: {e}")
        return False


def _read_json_safe(path: Path) -> dict | None:
    """Read JSON from `path`. Return None on missing/corrupt/permission errors."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


# --- Nonce state -----------------------------------------------------------


def write_nonce_state(
    session_id: str,
    nonce: str,
    body_hash: str,
    project_root: Path | None = None,
) -> bool:
    """Write the verification-skill nonce state for `session_id`.

    `nonce` is a hex string (16 random bytes → 32 hex chars by convention,
    enforced by SENTINEL_PATTERN in stop_verify_claims.py).
    `body_hash` is hex SHA-256 of the canonical UTF-8 message body.
    Timestamp captured at write time.

    Returns True if write succeeded.
    """
    state_dir = get_state_dir(session_id, project_root)
    if state_dir is None:
        return False
    return _atomic_write_json(
        state_dir / "nonce.json",
        {"nonce": nonce, "body_hash": body_hash, "timestamp": int(time.time())},
    )


def read_nonce_state(
    session_id: str, project_root: Path | None = None
) -> dict | None:
    """Read the nonce state for `session_id` or None if absent/corrupt."""
    state_dir = get_state_dir(session_id, project_root)
    if state_dir is None:
        return None
    return _read_json_safe(state_dir / "nonce.json")


def delete_nonce_state(
    session_id: str, project_root: Path | None = None
) -> None:
    """Delete the nonce state (one-shot consumption). Silent on missing file."""
    state_dir = get_state_dir(session_id, project_root)
    if state_dir is None:
        return
    try:
        os.unlink(state_dir / "nonce.json")
    except FileNotFoundError:
        pass
    except OSError as e:
        _stderr(f"could not delete nonce.json for session {session_id}: {e}")


def is_nonce_fresh(state: dict) -> bool:
    """True iff state['timestamp'] is within NONCE_TTL_SECONDS of now."""
    ts = state.get("timestamp")
    if not isinstance(ts, (int, float)):
        return False
    age = time.time() - ts
    return 0 <= age <= NONCE_TTL_SECONDS


# --- Stop-counter state ----------------------------------------------------


def read_stop_counter(
    session_id: str, project_root: Path | None = None
) -> int:
    """Read consecutive-blocks count. Returns 0 if absent or corrupt."""
    state_dir = get_state_dir(session_id, project_root)
    if state_dir is None:
        return 0
    data = _read_json_safe(state_dir / "stop-counter.json")
    if data is None:
        return 0
    count = data.get("consecutive_blocks")
    if not isinstance(count, int) or count < 0:
        return 0
    return count


def write_stop_counter(
    session_id: str, count: int, project_root: Path | None = None
) -> bool:
    """Write consecutive-blocks count atomically."""
    state_dir = get_state_dir(session_id, project_root)
    if state_dir is None:
        return False
    return _atomic_write_json(
        state_dir / "stop-counter.json",
        {"consecutive_blocks": max(0, int(count)), "last_updated": int(time.time())},
    )


def reset_stop_counter(
    session_id: str, project_root: Path | None = None
) -> None:
    """Reset counter to 0. Fires after successful sentinel validation."""
    write_stop_counter(session_id, 0, project_root)


# --- Profile-snapshot state (v0.11.7 B1 minimal closure) ------------------
#
# Detects mid-session mutation of `hooks.profile` in athanor.json: on the
# first Stop event of a session, the Stop-hook script snapshots a SHA-256
# of the profile value and persists it here; on every subsequent Stop in
# the same session, the script compares the current value against the
# stored snapshot. On mismatch, a stderr warning fires.
#
# Scope (v0.11.7): detection only. The warning does NOT block the gate,
# does NOT override the off-profile bypass, and does NOT auto-revert. Full
# architectural mitigation (file-lock vs. cached-checksum-key vs. opt-in
# cross-session edit block) is deferred to v0.11.8+. Per-session isolation
# is provided by the underlying `get_state_dir(session_id, ...)` layout
# (state files live under `.athanor/sessions/<id>/.hook-state/`), so two
# separate sessions get independent snapshots.


def read_profile_snapshot(
    session_id: str, project_root: Path | None = None
) -> dict | None:
    """Read the profile-snapshot state for `session_id` or None if absent."""
    state_dir = get_state_dir(session_id, project_root)
    if state_dir is None:
        return None
    return _read_json_safe(state_dir / "profile-snapshot.json")


def write_profile_snapshot(
    session_id: str,
    profile_hash: str,
    project_root: Path | None = None,
) -> bool:
    """Write the profile-snapshot state for `session_id`.

    `profile_hash` is a SHA-256 hex digest of the canonical-JSON
    serialization of the `hooks.profile` value (or the full `hooks` block —
    caller decides). Returns True if write succeeded.
    """
    state_dir = get_state_dir(session_id, project_root)
    if state_dir is None:
        return False
    return _atomic_write_json(
        state_dir / "profile-snapshot.json",
        {"profile_hash": profile_hash, "timestamp": int(time.time())},
    )
