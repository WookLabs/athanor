---
name: athanor-lite-plan
description: Thin wrapper for `athanor-plan --depth=lite`.
---

# Athanor Lite Plan

Use `athanor-plan` with forced `depth=lite`.

## Protocol

1. Read `plugins/athanor-codex/skills/athanor-plan/SKILL.md` and follow its
   planning protocol.
2. Bind `depth=lite` before tier classification.
3. Accept `--depth=lite` as redundant.
4. Reject `--depth=standard` or `--depth=deep` as contradictory and tell the
   user to remove the flag or use `athanor-plan --depth=<value>` directly.
5. Treat `--no-review` as redundant because lite planning already skips review
   and critic work.
6. Use the normal plan artifacts. Do not create `lite-plan.md`.
7. Do not claim hidden hook enforcement, Claude PreToolUse, or Claude Task dispatch
   enforcement in Codex.
