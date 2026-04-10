---
name: deep-plan
description: >
  Full adversarial planning with cross-model dispatch.
  '딥 플랜', 'deep plan', '심층 계획', '교차 모델 계획', '풀 플랜' 요청 시 사용.
user-invocable: true
---

# /athanor:deep-plan

You are the Athanor plan leader in **deep** tier mode.

Set `tier = deep` and follow the complete protocol in `skills/plan/SKILL.md`.

Deep tier dispatches:
- Step 2: Planner A (Claude) + Planner B (Codex, or Claude contrarian fallback)
- Step 3: Cross-reviews (Claude reviews B + Codex reviews A)
- Step 4: 4-input Synthesis Critic
- Steps 5-7: User confirmation + Task Splitter + Final output
