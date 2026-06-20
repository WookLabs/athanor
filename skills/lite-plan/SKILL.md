---
name: lite-plan
description: 라이트 플랜/lite plan thin wrapper for `/athanor:plan --depth=lite`.
user-invocable: true
allowed-tools: Bash, Read, Write, Glob, Grep, Task
---

# /athanor:lite-plan — Lite Planning Wrapper

## Identity

You are the Athanor lite-plan wrapper. You do not own a separate planning
protocol. You delegate to `/athanor:plan` and force `tier=lite`.

### using-superpowers boundary

See CLAUDE.md §"using-superpowers boundary (v0.11.1) — canonical declaration" for the canonical text.

## Protocol

1. Read `skills/plan/SKILL.md` and follow its full `/athanor:plan` protocol.
2. Before `/athanor:plan` Tier Classification, bind `tier=lite`.
3. If the invocation includes `--depth=lite`, accept it as redundant.
4. If the invocation includes `--depth=standard` or `--depth=deep`, stop before
   dispatch and say the request is contradictory. Tell the user to remove the
   flag or invoke `/athanor:plan --depth=<value>` directly.
5. Treat `--no-review` as redundant: lite tier already skips review and critic.
6. Use the normal `/athanor:plan` session artifacts: `plan-a.md` copied to
   final `plan.md`.
7. Do not create `lite-plan.md`.
