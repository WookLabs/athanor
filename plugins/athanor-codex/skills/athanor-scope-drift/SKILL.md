---
name: athanor-scope-drift
description: Compare current branch changes against Athanor session plans, PR intent, or user-stated requirements to identify scope drift and missing work.
---

# Athanor Scope Drift

Check whether the current diff still matches the intended scope. This skill is
informational; it does not block work by itself.

## Protocol

1. Identify intent sources in this order:
   - user-provided plan or requirement in the current conversation;
   - latest `.athanor/sessions/*/plan.md`;
   - PR body, commit messages, or issue text if available;
   - explicit fallback to "no written plan found".
2. Inspect actual change scope with `git status --short`, `git diff --stat`,
   `git diff --name-only`, and targeted diffs for suspicious paths.
3. Classify findings:
   - `Aligned`: change supports the stated intent.
   - `Possible drift`: change may be valid but lacks stated justification.
   - `Missing`: planned work not reflected in the diff.
   - `Unknown`: insufficient source intent.
4. Report concise evidence and recommended next action for each drift or
   missing item.

## Codex Constraints

- Do not modify files during a scope-drift check.
- Exclude generated caches and Athanor session artifacts unless they are the
  subject of the change.
- Do not infer product intent beyond the available plan or user statement.
