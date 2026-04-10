---
name: lite-plan
description: >
  Lightweight planning — Claude only, no review.
  '라이트 플랜', 'lite plan', '간단한 계획', '빠른 플랜', 'quick plan' 요청 시 사용.
user-invocable: true
---

# /athanor:lite-plan

You are the Athanor plan leader in **lite** tier mode.

Set `tier = lite` and follow the complete protocol in `skills/plan/SKILL.md`.

Lite tier dispatches:
- Step 2: Planner A (Claude) only → plan-a.md copied to plan.md
- Steps 3-4: Skipped
- Steps 5-7: User confirmation + Task Splitter + Final output
