---
date: 2026-05-19
topic: tdd-sdd-integration
---

# TDD/SDD Integration into Athanor Workflow

## Summary

athanor의 `/athanor:plan`과 `/athanor:work`를 강화해서 unit 단위로 Spec-then-TDD 규율을 자동 적용한다. plan이 각 unit을 `spec-then-tdd | test-aware | direct` 중 하나로 분류하고 behavior-bearing unit에 MUST/SHOULD 형식 acceptance criteria를 박는다. work는 분류에 따라 red-first 실행 / 종료 게이트 / 그대로 분기.

---

## Problem Frame

athanor는 정체성으로 "self-sustaining agentic orchestrator"를 표방하지만, 현재 어떤 워크플로우 단계에서도 test-first 또는 spec-driven 규율을 강제하지 않는다. `/athanor:plan`이 "test scenarios" 필드를 산출하지만 강제력은 없고, `/athanor:work`는 fail-first 게이트 없이 바로 실행 루프로 들어간다. 결과적으로 unit별 동작 검증이 worker의 자율 판단에 맡겨지며, v0.7.7 release에서 발견된 M4 escapee (analyze:301 오타 잔존)나 v0.7.8 PR #16 review에서 발견된 3개 P0 findings 같이 "코드 변경 후 회고적으로 테스트 추가"가 사고 패턴으로 자리잡았다. 가시적인 큰 사고는 아직 없지만, 가드레일이 없는 상태에서 점점 더 자율적인 워크플로우를 가져가는 것은 부채를 누적시킨다.

---

## Actors

- A1. **planner agent (`/athanor:plan` 내부)**: unit 분해 후 각 unit에 `execution_note` 할당 및 behavior unit에 `acceptance_criteria` 작성
- A2. **executor agent (`/athanor:work` worker)**: 분류에 따라 red-first / test-aware / direct 분기 실행
- A3. **reviewer agent (`/athanor:plan` Codex critic)**: plan 산출물의 unit 분류 적절성 + AC coverage 평가
- A4. **verification skill (Stop hook)**: 완료 주장 차단 (현재 기능 유지, 본 작업에선 변경 없음)
- A5. **user (athanor operator)**: plan 산출물 검토 시 unit 분류 거부권 행사 가능 (plan.md 직접 수정)

---

## Key Flows

- F1. **Standard plan → work 사이클 (확장 후)**
  - **Trigger:** 사용자가 `/athanor:plan <topic>` 호출
  - **Actors:** A1, A3, A5
  - **Steps:**
    1. planner가 unit 분해 (현재와 동일)
    2. 각 unit에 `execution_note` 자동 할당 (spec-then-tdd / test-aware / direct)
    3. behavior-bearing unit에 `acceptance_criteria` MUST/SHOULD bullets 작성
    4. Codex critic이 분류 + AC coverage 평가 (기본 plan tier 이상)
    5. user가 plan.md 확인 → `/athanor:work` 진행
  - **Outcome:** plan.md 안에 모든 unit이 명시적 execution_note + (해당 시) AC 보유
  - **Covered by:** R1, R2, R3, R8

- F2. **work 실행 — spec-then-tdd unit**
  - **Trigger:** `/athanor:work`가 `execution_note: spec-then-tdd` unit 도달
  - **Actors:** A2
  - **Steps:**
    1. AC 항목 읽기
    2. AC 첫 항목에 대한 failing test 작성 (구현 코드 미수정)
    3. test 실행 → RED 확인
    4. 최소 구현
    5. test 실행 → GREEN 확인 + 기존 회귀 전부 green
    6. 다음 AC 항목 반복, 모두 끝나면 refactor 가능
  - **Outcome:** unit close 시점에 모든 AC가 verified 상태, test 커밋이 git log에 존재
  - **Covered by:** R4, R5, AE1

- F3. **work 실행 — RED 확인 실패 (test가 처음부터 PASS)**
  - **Trigger:** F2 Step 3에서 test가 RED가 아니라 GREEN
  - **Actors:** A2
  - **Steps:**
    1. work skill이 자동 감지
    2. unit을 `test-aware`로 강등, work-log에 사유 기록 ("AC #N: 이미 구현됨, red 불가")
    3. test-aware 종료 게이트로 unit 진행
  - **Outcome:** 사용자 개입 없이 자동 강등, 사후 audit 가능
  - **Covered by:** R6, AE2

---

## Requirements

**Plan strengthening (planner side)**

- R1. `/athanor:plan` 산출 plan.md의 각 unit은 `execution_note` 필드를 갖는다. 값은 `spec-then-tdd | test-aware | direct` 중 하나.
- R2. planner는 unit 분류를 자동 결정한다 (user opt-in 아님). 분류 규칙은 SKILL prompt에 명시되며 다음 휴리스틱을 따른다: 소스 코드(.py/.js 등) 수정이 있고 새 동작/계약 도입 → `spec-then-tdd`; 기존 동작 보존하며 코드 수정 (refactor, 작은 bug fix) → `test-aware`; doc/config/CHANGELOG/`_doc` 등 prose-only → `direct`.
- R3. `execution_note: spec-then-tdd` unit은 `acceptance_criteria` 필드를 갖는다. 값은 MUST/SHOULD로 시작하는 observable assertion 1행 bullets. exit code, file state, schema validation, error reference 등 관찰 가능한 기준이어야 함.
- R8. Codex critic (plan tier 이상)은 unit 분류 적절성과 AC coverage 완성도를 평가 기준에 포함한다. Codex 미사용 시 best-effort.

**Work execution (executor side)**

- R4. `/athanor:work`는 unit의 `execution_note`에 따라 분기한다 — `spec-then-tdd` → F2 5단계 루프; `test-aware` → unit 종료 게이트 ("test 작성/업데이트되어 git diff에 포함 + 통과"); `direct` → 현재 그대로.
- R5. spec-then-tdd unit에서 worker는 test와 implementation을 같은 step에서 작성하지 않는다 (ce-work 가이드와 동일 원칙).
- R6. F2 Step 3에서 test가 RED가 아닐 경우, work skill은 unit을 `test-aware`로 자동 강등하고 work-log에 사유 기록한다. 사용자 에스컬레이션 없음.
- R7. `execution_note`가 없는 plan (기존 `docs/plans/2026-05-18-*` 4개 plan-docs 포함)을 만나면 work skill은 `direct`로 fallback. work-log에 grandfathered 사유 기록.

**Documentation contract**

- R9. CLAUDE.md `Defense Mechanisms` 표에 본 메커니즘을 advisory로 등재. verification-before-completion (enforced) 항목과 별개 행으로. 본 작업이 verification 스킬을 확장하지 않음을 명시.
- R10. CHANGELOG에 본 변경을 정직하게 기술 — "advisory, planner-classified" 임을 명시. "TDD enforced", "Spec-driven required" 같은 과장 표현 금지. v0.7.7~v0.7.9 사이의 honesty 약정과 일관.

---

## Acceptance Examples

- AE1. **Covers R3, R4, F2.** Given: plan.md에 `execution_note: spec-then-tdd` + `acceptance_criteria: [MUST exit 2 when material claim detected]` unit이 있다. When: `/athanor:work`가 해당 unit에 도달. Then: worker가 (1) test 함수 작성 (impl 미수정), (2) pytest 실행 → RED 확인, (3) 구현 추가, (4) pytest 재실행 → GREEN, (5) 다음 AC 항목 반복. work-log에 5단계 진행 기록.

- AE2. **Covers R6.** Given: plan.md에 `execution_note: spec-then-tdd` unit, AC #1이 `MUST validate v=2 sentinel format`인데 코드가 이미 그 검증을 구현 중. When: worker가 test 작성 후 pytest 실행. Then: test PASS (RED 아님). work skill이 자동 감지 → unit을 `test-aware`로 강등, work-log에 "AC #1: RED 불가, 이미 구현됨" 기록. unit은 test-aware 종료 게이트로 진행.

- AE3. **Covers R7.** Given: `docs/plans/2026-05-18-001-feat-v0.7.8-stop-hook-command-mode-plan.md` 같이 `execution_note` 필드가 없는 grandfathered plan. When: `/athanor:work`가 unit에 도달. Then: worker가 unit을 `direct`로 처리, work-log에 grandfathered 사유 기록. RED check와 종료 게이트 모두 적용 안 함.

- AE4. **Covers R2.** Given: plan.md unit이 `_doc` 필드 한 줄 수정만 포함. When: planner 분류. Then: `execution_note: direct` 할당. behavior-bearing 아님이라는 짧은 사유가 unit 설명에 적힘. work에서 RED check, 종료 게이트 모두 발동 안 함.

- AE5. **Covers R10.** Given: v0.8.0 CHANGELOG draft. When: 검토. Then: 본 메커니즘이 "advisory" 또는 "planner-classified discipline"으로 기술됨. "TDD enforced" / "Spec-driven required" 같은 과장 없음.

---

## Success Criteria

- 사용자 outcome: athanor v0.8.0 이후 출하되는 plan.md에서 spec-then-tdd로 분류된 unit이 work 종료 시점에 test 커밋과 함께 닫힌다. work-log + `git log` 추적 가능.
- 다운스트림 agent 핸드오프: `/ce-plan` 또는 후속 worker가 본 문서만 보고 다음 PR을 구성할 수 있다 (`skills/plan/SKILL.md`, `skills/work/SKILL.md`, `skills/verification-before-completion/SKILL.md`, `schemas/athanor-config.schema.json`, `CLAUDE.md`, `CHANGELOG.md`, 테스트 위치까지 추론 가능).
- carrying cost 정당화: doc/config-only PR (예: `_doc` 수정, CHANGELOG bump)에서는 본 메커니즘이 발동되지 않는다 — false-positive zero. work-log에 "execution_note: direct"가 명시적으로 기록됨.

---

## Scope Boundaries

- 새 `/athanor:spec` 명령어 신설 — 기각. workflow 표면 확장 없이 기존 `/athanor:plan` + `/athanor:work` 강화로 처리.
- 기존 4개 plan docs (`docs/plans/2026-05-18-*`) backfill — 기각. grandfathered (R7).
- `verification-before-completion` 스킬 확장 (test-commit 존재 확인 Stop hook gate) — 본 작업 범위에서 제외. baseline 효과 측정 가능한 상태로 출하된 후 데이터 보고 후속 릴리즈에서 검토.
- BDD Given/When/Then 형식 acceptance criteria — 기각. observable assertions (MUST/SHOULD) 단일 형식만 채택 (R3).
- `execution_note: spec-then-tdd` 적용에서 user opt-in 플래그 — 기각. planner 자율 결정 (R2).
- old + new plan 형식 영구 공존에 대한 sunset/migration 정책 — 본 작업 범위 제외. 자연 도태로 두며, 데이터 보고 후속 결정.
- universal (모든 unit 균일) 적용 — 기각. doc/config unit은 `direct`로 면제 (R2).

---

## Key Decisions

- **Both (Spec-then-TDD) 채택**, TDD만 또는 SDD만 단독 채택 거부: 두 메커니즘이 통합되어야 athanor 정체성이 가드레일로 단단해진다. carrying cost는 planner-classified 범위 좁힘 + baseline 단독 출하로 완화.
- **Planner-classified per unit**, universal 적용 거부: doc/config unit에 red-first는 TDD theater. planner가 분류 책임지고 user는 plan.md 검토 시 거부권만 행사.
- **Observable assertions (MUST/SHOULD)** 단일 형식, G/W/T 거부: athanor 작업은 infra/script/config가 다수라 BDD 어색. 단일 형식이 plan.md 일관성에 유리.
- **기존 skill 강화, 새 명령어 신설 거부**: workflow 표면 변화 없음 → 기존 사용자 친화. "spec 기능 발견 어려움" 단점은 CHANGELOG + skill description으로 보완.
- **baseline 단독 출하, verification 확장 후속**: 메커니즘 동시 투입은 효과 측정 어려움.
- **RED 안 가는 case는 auto-downgrade**: 사용자 에스컬레이션은 마찰 비용 큼. work-log 기록으로 audit 보장.

---

## Dependencies / Assumptions

- ce-work의 Execution note 패턴 (test-first, characterization-first)이 안정적으로 작동 중인 것으로 가정. 본 작업은 athanor에 동등 패턴을 이식하는 것이므로 참조 구현으로 활용.
- athanor의 154개 기존 테스트는 본 작업으로 깨지지 않는다 (회귀 보장 요구).
- 기존 `verification-before-completion` 스킬과 Stop hook command-mode (v0.7.9 출하분)는 변경 없이 유지.
- Codex CLI가 활성화된 환경에서 R8 (critic이 unit 분류 평가)이 작동. Codex 미사용 환경에서는 critic 단계가 skip되므로 R8은 best-effort.

---

## Outstanding Questions

### Resolve Before Planning

(없음 — 모든 product 결정은 본 문서에서 확정)

### Deferred to Planning

- [Affects R1, R2][Technical] planner의 unit 분류 휴리스틱을 어디에 작성? `skills/plan/SKILL.md` 안의 inline prose vs 별도 reference markdown (`skills/plan/references/unit-classification.md` 같은).
- [Affects R3][Technical] `acceptance_criteria` 필드를 plan.md unit block 안에 inline bullet으로 vs YAML frontmatter style로. 가독성 vs LLM 파싱 용이성 트레이드.
- [Affects R4, R5, F2][Technical] red-first 5단계를 work skill prompt에서 어떻게 enforce할지 — single super-prompt vs sub-step dispatch. ce-work 참조.
- [Affects R6][Technical] "test가 RED 아님" 감지 메커니즘 — pytest exit code 직접 확인 vs work skill 자체 로직. ralph-loop 통합 방식.
- [Affects R7][Needs research] backwards compat 회귀 — 4개 기존 plan docs에 대해 work skill이 `direct`로 fallback 잘 하는지 자동 검증할 방법 (regression test).
- [Affects R9][Technical] CLAUDE.md `Defense Mechanisms` 표의 기존 4개 mechanism과 명명/granularity 조화. advisory label 위치.
