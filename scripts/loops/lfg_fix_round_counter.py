#!/usr/bin/env python3
"""Session-scoped fix-round counter CLI for /athanor:lfg Step 3 / Step 8.

Closes the documented T1-2 gap: lfg Step 3 (review-fix) and Step 8 (CI-fix)
previously had a fix-round limit that was *prose guidance for the leader; no
programmatic counter*. This is the small, single-purpose counter the leader
branches on via an exit code (Key Decision 3).

Honesty label: ADVISORY — leader-prose-bound. A real exit code now exists (a
strict upgrade over pure prose), but NO PreToolUse/Stop runtime hook forces the
leader to branch (same enforcement class as the lfg merge-readiness gate).

State file: ``.athanor/sessions/<id>/lfg-fix-rounds.json``::

    {"schema_version": 1, "review_fix_rounds": N, "ci_fix_rounds": M,
     "max_rounds": 3}

Subcommands:
  * ``bump --session <dir> --loop review|ci`` — atomic read-increment-write
    (temp-then-rename, mirroring goal_loop_controller.write_loop_state_atomic);
    prints the new count. Exit 0 while ``< max_rounds``, exit 3 when the bump
    reaches/exceeds ``max_rounds`` (= "stop iterating", the cap signal).
  * ``read --session <dir>`` — prints the JSON state (a fresh session reports
    zero counts; exit 0).

Fail-loud (Risk R7): a malformed (present-but-unparseable) state file → exit 2
+ stderr, and the counter is NEVER silently reset/overwritten — a silent reset
would hide a stuck loop. Deliberately NOT coupled to goal_loop_controller.py:
lfg is single-cycle (no goal_id/cycle_state/current_cycle), so folding it into
the durable LoopState would be a category error.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
DEFAULT_MAX_ROUNDS = 3
STATE_FILENAME = "lfg-fix-rounds.json"
LOOP_FIELDS = {"review": "review_fix_rounds", "ci": "ci_fix_rounds"}

EXIT_OK = 0
EXIT_MALFORMED = 2
EXIT_CAP_REACHED = 3


class CounterError(ValueError):
    """Raised when the fix-round state file is malformed or contradictory."""


def _stderr(msg: str) -> None:
    print(f"lfg fix-round counter: {msg}", file=sys.stderr)


def _default_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "review_fix_rounds": 0,
        "ci_fix_rounds": 0,
        "max_rounds": DEFAULT_MAX_ROUNDS,
    }


def _require_count(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CounterError(f"{field} must be a non-negative integer")
    return value


def _load_state(state_path: Path) -> dict[str, Any]:
    """Load and validate the state file.

    A missing file returns a fresh zero-count default (the leader may read/bump
    before the first fix round). A present-but-malformed file raises
    CounterError → the caller exits 2 WITHOUT writing (never a silent reset).
    """
    if not state_path.exists():
        return _default_state()
    try:
        raw = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CounterError(f"malformed state JSON in {state_path}: {exc.msg}") from exc
    except OSError as exc:
        raise CounterError(f"could not read state file: {state_path}") from exc
    if not isinstance(raw, dict):
        raise CounterError("state root must be an object")
    if raw.get("schema_version") != SCHEMA_VERSION:
        raise CounterError(f"schema_version must be {SCHEMA_VERSION}")
    state = _default_state()
    state["review_fix_rounds"] = _require_count(
        raw.get("review_fix_rounds", 0), "review_fix_rounds"
    )
    state["ci_fix_rounds"] = _require_count(raw.get("ci_fix_rounds", 0), "ci_fix_rounds")
    max_rounds = raw.get("max_rounds", DEFAULT_MAX_ROUNDS)
    if isinstance(max_rounds, bool) or not isinstance(max_rounds, int) or max_rounds < 1:
        raise CounterError("max_rounds must be a positive integer")
    state["max_rounds"] = max_rounds
    return state


def _write_state_atomic(state_path: Path, state: dict[str, Any]) -> None:
    """Temp-then-rename atomic write, mirroring write_loop_state_atomic."""
    state_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = state_path.with_name(f"{state_path.name}.tmp")
    temp_path.write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temp_path.replace(state_path)


def _state_path(session: Path) -> Path:
    return session / STATE_FILENAME


def _cmd_bump(session: Path, loop: str) -> int:
    state = _load_state(_state_path(session))  # raises CounterError on malformed
    field = LOOP_FIELDS[loop]
    new_count = state[field] + 1
    state[field] = new_count
    _write_state_atomic(_state_path(session), state)
    print(new_count)
    # Exit 3 when the bump reaches/exceeds the cap (>=, never an off-by-one that
    # would release at cap+1); exit 0 while still under the cap.
    return EXIT_CAP_REACHED if new_count >= state["max_rounds"] else EXIT_OK


def _cmd_read(session: Path) -> int:
    state = _load_state(_state_path(session))  # raises CounterError on malformed
    print(json.dumps(state, indent=2, sort_keys=True))
    return EXIT_OK


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Session-scoped /athanor:lfg fix-round counter (advisory)."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    bump = sub.add_parser("bump", help="Increment a fix-round counter.")
    bump.add_argument("--session", type=Path, required=True)
    bump.add_argument("--loop", choices=sorted(LOOP_FIELDS), required=True)

    read = sub.add_parser("read", help="Print the fix-round state JSON.")
    read.add_argument("--session", type=Path, required=True)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    try:
        if args.command == "bump":
            return _cmd_bump(args.session, args.loop)
        return _cmd_read(args.session)
    except CounterError as exc:
        _stderr(str(exc))
        return EXIT_MALFORMED


if __name__ == "__main__":
    raise SystemExit(main())
