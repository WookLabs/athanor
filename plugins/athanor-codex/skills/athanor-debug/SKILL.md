---
name: athanor-debug
description: Triage-first debugging for failures, errors, regressions, broken tests, or root-cause investigation using Athanor's Codex-native workflow.
---

# Athanor Debug

Diagnose before fixing. The goal is a verified root cause, then the smallest
safe correction.

## Protocol

1. Capture the failure exactly: command, error text, affected path, expected
   behavior, actual behavior, and recent changes.
2. Reproduce or narrow the failure with the smallest command available.
3. Trace from symptom to cause using code, tests, logs, and git history as
   needed. Do not stop at the first plausible explanation.
4. State the root cause with evidence. If confidence is incomplete, say what is
   known and what remains uncertain.
5. Propose or implement the minimal fix only after the cause is grounded.
6. Verify with the narrow failing command first, then broader relevant checks.

## Codex Constraints

- Do not edit files before reproducing or otherwise grounding the failure.
- Do not treat unrelated existing failures as solved. Separate them from the
  target failure.
- Use sub-agents only when the user explicitly requested parallel
  investigation.
