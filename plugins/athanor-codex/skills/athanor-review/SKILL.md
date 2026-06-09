---
name: athanor-review
description: Run an Athanor-style structured code review in Codex across architecture, quality, security, performance, testing, and documentation lenses.
---

# Athanor Review

Review code changes with Athanor's multi-lens discipline, adapted for Codex.
Findings lead; summaries are secondary.

## Protocol

1. Establish review scope with `git status`, `git diff`, and any user-specified
   branch, PR, or file set.
2. Select relevant lenses from: architecture, quality, security, performance,
   testing, documentation. Skip irrelevant lenses explicitly and briefly.
3. Inspect the changed code and nearby tests before forming findings.
4. Report only actionable issues. Each finding must include severity, file and
   line reference, impact, and a concrete fix direction.
5. Include test gaps and residual risk even when no blocking issues are found.

## Codex Constraints

- Do not fabricate parallel worker output. If sub-agents are unavailable or not
  explicitly authorized, run the review locally.
- Use the host's code-review stance: bugs, regressions, risks, and missing
  tests first; summary after findings.
- Do not modify files during review unless the user explicitly asks to fix the
  findings.
