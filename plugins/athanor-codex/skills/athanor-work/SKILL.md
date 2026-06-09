---
name: athanor-work
description: Execute an accepted Athanor plan in Codex with verification discipline, Spec-then-TDD where appropriate, work-log updates, and explicit status handling.
---

# Athanor Work

Use this after a plan is accepted and the user wants implementation. This is
Codex-native execution guidance, not Claude worker dispatch.

## Protocol

1. Load the active plan from the user's prompt or the latest
   `.athanor/sessions/<id>/plan.md`. If no plan exists, stop and ask for
   `athanor-plan`.
2. Split work into small subtasks with `files`, `verify`, dependencies, and one
   execution class:
   - `Spec-then-TDD`: new source behavior or bug fixes where a failing test can
     prove the expected behavior.
   - `test-aware`: refactors, config changes, or existing behavior changes that
     still need verification.
   - `direct`: prose-only or low-risk session artifact updates.
3. Execute in dependency order. Use parallel sub-agents only if the user
   explicitly requested parallel agent work and the write scopes are disjoint.
4. Track each subtask as one of: `done`, `failure`, `done_with_concerns`,
   `needs_context`, or `blocked`.
5. Append a concise `.athanor/sessions/<id>/work-log.md` entry when working from
   an Athanor session. Include files changed, verification, and unresolved
   concerns.
6. Finish with verification evidence before claiming completion.

## Execution Rules

- For `Spec-then-TDD`, write or update the failing test first, verify RED, make
  the smallest implementation change, then verify GREEN.
- For `test-aware`, identify the relevant existing tests or checks before
  editing and run them after the change.
- For `direct`, still inspect the rendered or parsed artifact when possible.
- If a subtask returns `needs_context`, gather the missing fact without reading
  unrelated source. If the fact is product intent, ask the user.
- If a subtask is `blocked`, preserve partial work, record the blocker, and move
  only to independent remaining work.

## Codex Constraints

- Do not claim Claude hook enforcement, Freeze enforcement, or Claude Task
  isolation.
- Do not claim Claude Stop hook verification. Use actual command output and
  inspected files as evidence.
- Do not broaden the plan just because nearby issues are visible. Use
  `athanor-scope-drift` when scope is uncertain.
