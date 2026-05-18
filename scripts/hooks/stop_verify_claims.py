#!/usr/bin/env python3
"""
Athanor v0.7.8 spike: command-hook Stop blocking feasibility test.

Phase 0 (spike): no-op stub. Always exit 0 unless the marker flag
/tmp/athanor-spike-block.flag exists, in which case exit 2 ONCE
(one-shot via /tmp/athanor-spike-done.flag) to test whether Claude
Code's runtime honors command-hook Stop blocking.

Phase 1 (v0.7.8 if spike passes): replaced with real material-claim
detection + verification-skill-invocation check.

Every invocation logs to /tmp/athanor-spike.log for empirical observation.
"""
import json
import os
import sys
import time

LOG = "/tmp/athanor-spike.log"
BLOCK_FLAG = "/tmp/athanor-spike-block.flag"
DONE_FLAG = "/tmp/athanor-spike-done.flag"


def log(msg: str) -> None:
    try:
        with open(LOG, "a") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except OSError:
        pass


def main() -> int:
    payload_raw = ""
    if not sys.stdin.isatty():
        try:
            payload_raw = sys.stdin.read()
        except (OSError, ValueError):
            payload_raw = ""

    event = "?"
    try:
        if payload_raw:
            event = json.loads(payload_raw).get("hook_event_name", "?")
    except json.JSONDecodeError:
        event = "?(non-json)"

    log(f"invoked event={event} payload_bytes={len(payload_raw)} argv={sys.argv}")

    if os.path.exists(BLOCK_FLAG) and not os.path.exists(DONE_FLAG):
        try:
            open(DONE_FLAG, "w").close()
        except OSError:
            pass
        log("BLOCKING (exit 2) — one-shot, done flag created")
        print(
            "athanor spike: blocking Stop to test command-hook gating semantics. "
            "This stderr message demonstrates whether type=command Stop hooks "
            "feed exit-2 stderr back to the model as continuation context.",
            file=sys.stderr,
        )
        return 2

    log("PASSING (exit 0)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
