---
name: athanor-verify
description: Verify material completion claims before final responses, commits, PRs, releases, migrations, or deployment statements using concrete Codex evidence.
---

# Athanor Verify

Use this before making a material claim that work is complete, tests pass, a
release is ready, a migration is safe, or a deployment succeeded.

## Protocol

1. Identify the material claim exactly.
2. List the evidence needed to prove it: files changed, tests, commands,
   rendered behavior, install status, logs, or external checks.
3. Run or inspect the narrowest checks that directly cover the claim.
4. Broaden verification when the blast radius requires it.
5. Report results as evidence, not confidence language. Include failed,
   skipped, unavailable, or irrelevant checks.
6. If evidence is incomplete, do not claim completion. State what remains.

## Evidence Checklist

- Source state: `git status`, targeted diffs, relevant generated files.
- Tests: focused tests first, then broader tests when needed.
- Commands: exact command, exit status, and meaningful output summary.
- Install/runtime: plugin list, validator output, server status, or UI smoke
  result when relevant.
- Documentation: updated instructions for any new user-facing flow.

## Codex Constraints

- Do not claim hidden hook enforcement.
- Do not treat a passing narrow test as proof of a broad claim.
- Do not hide known unrelated failures; separate them from the target claim.


Do not claim hook-backed enforcement.
