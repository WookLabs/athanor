#!/bin/sh
# Athanor portable hook launcher (v0.24.3, N1).
# Usage: sh run_hook.sh "<abs path to hook .py>"
# Invoked from hooks/hooks.json; the harness runs hook commands through a
# POSIX shell on every OS (proven by ${CLAUDE_PLUGIN_ROOT} expanding today),
# so `sh` is guaranteed — no chicken/egg.
#
# Resolves a WORKING Python >= 3.10 by FUNCTIONALITY probe, not PATH
# presence: the Windows Store App-Execution-Alias `python3` stub exists on
# PATH but cannot run code (2026-07-01 fail-open incident). Probes read
# stdin from /dev/null so the hook's JSON payload is never consumed; the
# winning interpreter is exec'd with original stdin/stdout/stderr so hook
# exit-code semantics (exit 2 = block) propagate unchanged.
#
# No working interpreter => exit 1 LOUD-PASS: non-2 exits pass through the
# harness gate, but Claude Code surfaces the hook error + this stderr line
# visibly. Never exit 2 here (would brick python-less sessions on every
# hook call); never exit 0 silently (the failure mode this file fixes).
# Locked by tests/test_regression_portable_hook_interpreter.py.

TARGET="$1"
if [ -z "$TARGET" ]; then
  echo "athanor run_hook.sh: missing target hook script argument" >&2
  exit 1
fi

PROBE='import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'

# NOTE: $CAND is intentionally unquoted at use sites so "py -3" word-splits.
for CAND in python3 python "py -3"; do
  if $CAND -c "$PROBE" </dev/null >/dev/null 2>&1; then
    exec $CAND "$TARGET"
  fi
done

echo "athanor hook gate INACTIVE: no working Python >= 3.10 on PATH (tried: python3, python, py -3). Active hooks (kernel guard, evidence sniffer) did NOT run. Install Python 3.10+ (https://www.python.org/downloads/)." >&2
exit 1
