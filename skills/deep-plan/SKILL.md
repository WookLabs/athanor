---
name: deep-plan
description: >
  Full adversarial planning with cross-model dispatch.
  '딥 플랜', 'deep plan', '심층 계획', '교차 모델 계획', '풀 플랜' 요청 시 사용.
user-invocable: true
allowed-tools: Bash, Read, Write, Glob, Grep, Task
---

# /athanor:deep-plan

You are the Athanor plan leader in **deep** tier mode.

Set `tier = deep` and follow the complete protocol in `skills/plan/SKILL.md`.

Deep tier dispatches:
- Step 2: Planner A (Claude) + Planner B (Codex, or Claude contrarian fallback)
- Step 3: Cross-reviews (Claude reviews B + Codex reviews A)
- Step 4: 4-input Synthesis Critic
- Step 5: User confirmation (Task Splitter runs later at /athanor:work Step 0.5)

### v0.11.1 using-superpowers boundary

Athanor's Thin Leader + planner-classified discipline applies in this
skill context. `superpowers:using-superpowers` is loaded at SessionStart
and its "MUST invoke before response" pressure is **advisory here** —
discovery in athanor-native skills resolves through leader dispatch,
not pre-response invocation check. See CLAUDE.md §Defense Mechanisms.
