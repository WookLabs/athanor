---
name: athanor-deep-plan
description: Thin wrapper for `athanor-plan --depth=deep`.
---

# Athanor Deep Plan

Use `athanor-plan` with forced `depth=deep`.

## Protocol

1. Read `plugins/athanor-codex/skills/athanor-plan/SKILL.md` and follow its
   planning protocol.
2. Bind `depth=deep` before tier classification.
3. Accept `--depth=deep` as redundant.
4. Reject `--depth=standard` or `--depth=lite` as contradictory and tell the
   user to remove the flag or use `athanor-plan --depth=<value>` directly.
5. Preserve `--no-review` as an orthogonal request: deep planning still creates
   competing plans, then skips the review round where the parent protocol says
   to.
6. Use the normal plan artifacts. Do not create `deep-plan.md`.
7. Do not claim hidden hook enforcement, Claude PreToolUse, or Claude Task dispatch
   enforcement in Codex.
