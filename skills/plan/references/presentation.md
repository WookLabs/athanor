# Step 5 Presentation Template

This reference holds the full presentation template + UNRESOLVED conflict
handler used by Step 5 of `skills/plan/SKILL.md`. The router carries the
brief invocation rule; the structured template lives here.

After the Critic returns, read `.athanor/sessions/{id}/plan.md` and present
the **complete plan** in a structured, scannable format. The user must see
everything before confirming.

## Plan presentation block

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Athanor Plan: {title}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Goal
{무엇을 왜 하는지 — 1-3문장}

## Approach
{전략 요약 — 어떤 방식으로 접근하는지}

## Phase Summary

| Phase | Name | Files | Verify | Note |
|-------|------|-------|--------|------|
| 1 | {name} | {N}개 | {MUST×N / prose} | {spec-then-tdd / test-aware / direct} |
| 2 | {name} | {N}개 | {MUST×N} | {classification} |

## Scope
  Files to modify: {N}개  |  New files: {N}개  |  Complexity: {low/medium/high}

## Phase Detail

Phase 1: {이름}
  ├── Step 1.1: {구체적 행동} → {대상 파일}
  ├── Step 1.2: {구체적 행동} → {대상 파일}
  └── Verify: {검증 방법}

Phase 2: {이름}
  ├── Step 2.1: {구체적 행동} → {대상 파일}
  └── Verify: {검증 방법}

## Key Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | {결정} | {이유} |
| 2 | {결정} | {이유} |

> Deep tier: Resolved Conflicts에서 추출 | Standard: Changes from Review에서 | Lite: plan-a.md Risks에서

## Risks
  ⚠ {리스크 1}: {대응}
  ⚠ {리스크 2}: {대응}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## UNRESOLVED conflict handler

If UNRESOLVED conflicts exist, show them AFTER the plan:

```
⚠ {N}개 미해결 충돌:

| # | Conflict | Option A | Option B | Lean |
|---|----------|----------|----------|------|
| 1 | {description} | {approach} | {approach} | {preference} |

각 충돌에 대해 AskUserQuestion으로 사용자 선택을 요청합니다.
preview 필드에 각 옵션의 영향을 ASCII 비교로 표시:

AskUserQuestion({
  questions: [{
    question: "Conflict 1: {description}",
    options: [
      { label: "Option A", description: "...", preview: "Option A impact:\n─────────\nPhase 2: unchanged\nRisk: low" },
      { label: "Option B", description: "...", preview: "Option B impact:\n─────────\nPhase 2: +1 file\nRisk: medium" }
    ]
  }]
})

선택해주세요 (예: "1A, 2B") 또는 직접 피드백을 주세요.
```

Wait for user to resolve, update plan.md, then re-display the full plan.

## No-conflicts confirmation

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ 모든 충돌이 해결되었습니다.
이 플랜을 확정할까요? 확정 후 /athanor:work 로 실행하세요.
  [Y] 확정  [N] 수정 필요
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**IMPORTANT**: 확정 후 plan.md는 as-authored 상태입니다.
/athanor:work 실행 전까지는 plan.md를 자유롭게 편집할 수 있으며,
/athanor:work는 항상 최신 plan.md를 기준으로 subtasks를 생성합니다.
(단, 이미 진행 중인 작업은 resume guard에 의해 보호됩니다.)

**If user says N (수정 필요):** Ask what to modify. Apply changes to
plan.md. Re-display the full plan. Repeat until user confirms.
