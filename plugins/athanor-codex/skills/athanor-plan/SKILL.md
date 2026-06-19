---
name: athanor-plan
description: Create or revise an implementation plan using Athanor's Codex-native planning workflow. Use when the user asks for an Athanor plan, implementation plan, deep plan, lite plan, or planning before execution.
---

# Athanor Plan

Create a decision-complete implementation plan for Codex. This skill adapts
Athanor's planning discipline without Claude `Task` dispatch or hook runtime.

## Protocol

1. Ground the plan in repo facts first: inspect relevant files, tests,
   manifests, docs, and prior `.athanor/sessions/*/plan.md` when present.
   If `.athanor/sessions/*/prompt-gen.md` exists, treat it as the refined
   user-intent prompt.
2. State the goal, current state, constraints, and non-goals before the plan.
   If target, desired outcome, success criteria, or depth are too vague, stop
   and recommend `athanor-prompt-gen` before planning instead of inventing
   product behavior.
3. Choose the smallest useful depth:
   - `lite`: straightforward, low-risk changes.
   - `standard`: default; include risks, tests, and verification.
   - `deep`: architecture, migrations, security, data loss, or broad refactors.
4. Produce a plan that leaves no implementation decisions open: files or
   subsystems, behavior changes, public interfaces, data flow, failure modes,
   tests, and verification.
5. If the user asks to write a session artifact, save it under
   `.athanor/sessions/<date-sequence>/plan.md`; otherwise present it in chat.

## Codex Constraints

- Do not claim Claude hook coverage, Freeze coverage, or Claude `Task` worker
  isolation in Codex.
- Use Codex sub-agents only if the user explicitly authorized delegation or
  parallel agent work.
- Do not implement while planning unless the user has left plan-only mode and
  explicitly asks for execution.
