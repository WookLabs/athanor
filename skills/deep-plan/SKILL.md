---
name: deep-plan
description: 딥 플랜/deep plan thin wrapper for `/athanor:plan --depth=deep`.
user-invocable: true
allowed-tools: Bash, Read, Write, Glob, Grep, Task
---

# /athanor:deep-plan — Deep Planning Wrapper

## Identity

You are the Athanor deep-plan wrapper. You do not own a separate planning
protocol. You delegate to `/athanor:plan` and force `tier=deep`.

### using-superpowers boundary

See CLAUDE.md §"using-superpowers boundary (v0.11.1) — canonical declaration" for the canonical text.

## Protocol

1. Read `skills/plan/SKILL.md` and follow its full `/athanor:plan` protocol.
2. Before `/athanor:plan` Tier Classification, bind `tier=deep`.
3. If the invocation includes `--depth=deep`, accept it as redundant.
4. If the invocation includes `--depth=standard` or `--depth=lite`, stop before
   dispatch and say the request is contradictory. Tell the user to remove the
   flag or invoke `/athanor:plan --depth=<value>` directly.
5. Preserve `--no-review` as an orthogonal flag. Deep + `--no-review` still
   uses the deep two-planner path, skips Step 3, and runs the review-skipped
   Critic variant from `skills/plan/SKILL.md`.
6. Use the normal `/athanor:plan` session artifacts: `plan-a.md`, `plan-b.md`,
   reviews when enabled, and final `plan.md`.
7. Do not create `deep-plan.md`.
