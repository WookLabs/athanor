#!/usr/bin/env python3
"""Sentinel-emission helper invoked by the verification-before-completion skill.

The skill (markdown prose) tells the model:
  1. Compute your evidence text (verification commands, output, exit codes).
  2. Pipe it through this helper:
       echo "<evidence>" | python3 scripts/hooks/sentinel_helper.py emit
  3. The helper prints the sentinel line; emit it as line 1 of your response,
     followed by your evidence verbatim.

The helper generates a random nonce, hashes the piped body, writes
`{nonce, body_hash, timestamp}` to the project's hook-state directory, then
prints `<!-- athanor:verification-emission v=2 nonce=<hex> -->` to stdout.

When the Stop hook fires on the model's response, it:
  - Extracts the sentinel + nonce from line 1
  - Reads the same state file
  - Verifies the nonce matches AND the body content (after the sentinel) hashes
    to the stored value AND the timestamp is within TTL
  - On all-pass: atomic-delete the state file (one-shot) and exit 0
  - On any-fail: fall through to material-claim detection

This raises forgery cost from "emit one string" (v0.7.8) to "write JSON with
matching hash + emit matching sentinel" (v0.7.9). Not eliminated — the model
can in principle write the state file itself via Bash. Complete defense
requires Claude Code transcript-event introspection (v0.8.0+ work).
"""
from __future__ import annotations

import hashlib
import secrets
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import hook_state  # noqa: E402

# v0.7.9 ships a single project-wide state file (session_id="active").
# Per-Claude-Code-session state plumbing is deferred to v0.7.10+ when the
# session-id correlation between skill invocation and Stop event becomes
# verified. The project-wide single state is sufficient for the typical
# one-session-per-project workflow.
ACTIVE_SESSION = "active"


def _stderr(msg: str) -> None:
    print(f"athanor (sentinel helper): {msg}", file=sys.stderr)


def emit() -> int:
    """Read body from stdin, write nonce state, print sentinel to stdout.

    Exit 0 on success. Exit 1 on state-write failure (with stderr).
    """
    try:
        body = sys.stdin.read()
    except (OSError, ValueError) as e:
        _stderr(f"could not read stdin: {e}")
        return 1
    nonce = secrets.token_hex(16)  # 32 hex chars
    # v0.11.6: normalize body (strip leading/trailing whitespace) before hashing
    # so the round-trip pipe→helper→emit vs model→transcript→re-extract is
    # tolerant of trailing-newline differences. Heredoc input typically has
    # a trailing \n; Claude Code transcripts strip trailing whitespace on
    # response capture. The script's validate_emission_sentinel() applies
    # the same .strip() before hashing so both sides agree on the canonical
    # form. Content forgery still raises hash mismatch — whitespace is not
    # a security boundary. Companion-fix to v0.11.3/4/5 runtime+doc arc.
    # errors="surrogatepass": a lone surrogate (e.g. PowerShell mangling an
    # em-dash at the shell→python pipe boundary) would otherwise raise
    # UnicodeEncodeError here and crash emit. The validator side
    # (stop_verify_claims.py validate_emission_sentinel) encodes the SAME
    # canonical body with the SAME handler, so both hashes agree on identical
    # input.
    body_hash = hashlib.sha256(
        body.strip().encode("utf-8", errors="surrogatepass")
    ).hexdigest()
    if not hook_state.write_nonce_state(ACTIVE_SESSION, nonce, body_hash):
        _stderr("could not write nonce state — sentinel will fail validation")
        return 1
    print(f"<!-- athanor:verification-emission v=2 nonce={nonce} -->")
    return 0


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] != "emit":
        _stderr("usage: sentinel_helper.py emit < body")
        return 1
    return emit()


if __name__ == "__main__":
    sys.exit(main())
