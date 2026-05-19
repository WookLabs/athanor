---
date: 2026-05-19
topic: discuss-clarify-mode
---

# /athanor:discuss — Add intent-clarification mode (v0.9.0)

## Summary

`/athanor:discuss` 스킬을 확장해서 두 모드를 갖는다 — **clarify** (intent 명확화) + **synthesis** (옵션 A/B 합성, 현재 동작). 새 명령어 신설 없이 discuss 안에서 흡수. Step 1에서 leader가 user에게 한 번 묻고 모드 분기. clarify 모드는 single-Claude dialog로 ce-brainstorm-style gap probe (evidence / specificity / counterfactual / attachment)를 돌고 `.athanor/sessions/{id}/requirements.md`를 산출. 끝나면 user가 다음 단계 메뉴에서 선택.

---

## Problem Frame

현재 `/athanor:discuss` (skills/discuss/SKILL.md)는 Step 1에서 사용자에게 "Option A vs Option B"가 이미 정의된 dilemma를 restate + confirm한 뒤 Researcher / Devil's Advocate / Critic으로 합성한다. 즉 **이미 정해진 옵션 사이에서 추천을 만드는 합성 단계**다. 그러나 athanor 사용자의 실제 흐름에서는 "옵션 자체가 명확하지 않은" 상태로 진입하는 경우가 잦다 — 무엇을 만들지가 아직 모호하거나, 이해관계자가 누구인지 / 무엇이 성공인지가 명확하지 않다. 이때 `/athanor:discuss`를 invoke하면 leader는 "A vs B로 정리해 주세요"라는 요구를 받게 되어 사용자가 옵션을 무리하게 만들어내거나, `/athanor:plan`으로 곧바로 가서 plan이 product behavior를 발명하게 된다. compound-engineering의 `ce-brainstorm`이 이미 검증된 패턴 (gap probe 4-lens — evidence / specificity / counterfactual / attachment)을 제공하므로, athanor도 그 등가물을 `/athanor:discuss` 안에서 제공하는 것이 자연스럽다.

---

## Actors

- A1. **user (athanor operator)**: `/athanor:discuss` 호출 시 Step 1에서 모드 선택. clarify dialog에 답함. Phase 4 메뉴에서 다음 단계 선택.
- A2. **discuss leader (skills/discuss/SKILL.md, Thin Leader)**: Step 1에서 모드 질문 → 분기. clarify 모드에서는 single-Claude dialog로 gap probe 진행. synthesis 모드에서는 기존 worker dispatch 그대로.
- A3. **clarify dialog agent (`/athanor:discuss` clarify 모드 내부, NEW)**: single-Claude (no parallel workers, no Codex). gap probe 시리즈를 ce-brainstorm Phase 1.2-1.3 패턴으로 진행하고 requirements.md 산출.
- A4. **synthesis workers (Researcher + Devil's Advocate + Critic, EXISTING)**: synthesis 모드에서만 dispatch. 현재 동작 보존.
- A5. **/athanor:plan leader (downstream)**: Step 1에서 discuss.md / analyze.md에 더해 requirements.md도 input으로 자동 로드. Planner A는 원본 R-IDs를 plan의 Verify field로 trace.

---

## Key Flows

- F1. **`/athanor:discuss` Step 1 mode dispatch**
  - **Trigger:** user가 `/athanor:discuss` 호출 + 자연어 입력 제공
  - **Actors:** A1, A2
  - **Steps:**
    1. Leader가 user 입력을 restate
    2. Leader가 단일 질문: "이미 옵션 A/B가 명확하신가요, 아니면 의도부터 명확히 하고 싶으신가요?"
    3. user 응답 분기:
       - "옵션 A/B 명확" → synthesis 모드 (기존 Step 2 워커 dispatch로 진행)
       - "의도 명확화" → clarify 모드 (F2)
       - "잘 모르겠다" → clarify 모드 default (clarify 끝나면 옵션이 보이면 user가 F4 메뉴에서 synthesis 선택)
  - **Outcome:** 모드 확정, 분기된 path로 진행
  - **Covered by:** R1, R2

- F2. **clarify 모드 dialog**
  - **Trigger:** F1 분기에서 clarify 모드 선택됨
  - **Actors:** A2, A3, A1
  - **Steps:**
    1. clarify dialog agent가 user의 opening prompt를 받아 Phase 1.2-style internal scan (evidence / specificity / counterfactual / attachment 각 gap이 존재하는지 판단)
    2. 존재하는 각 gap마다 open-ended probe 질문 1개 발화 (one question per turn)
    3. user 답변 → 다음 gap probe 또는 narrowing 질문
    4. 모든 active gap 처리 + integration check 완료 시 dialog 종료
    5. Phase 2.5-style scoping synthesis 발화 + 사용자 확정 요청
    6. 확정되면 requirements.md 작성
  - **Outcome:** `.athanor/sessions/{id}/requirements.md` 산출. ce-brainstorm requirements-capture.md 템플릿 (Summary / Problem Frame / Actors / Key Flows / Requirements R-IDs / Acceptance Examples AE-IDs / Success Criteria / Scope Boundaries / Key Decisions / Dependencies / Outstanding Questions) 채택
  - **Covered by:** R3, R4, R5, R6, AE1, AE2

- F3. **synthesis 모드 (기존 동작 보존)**
  - **Trigger:** F1 분기에서 synthesis 모드 선택됨
  - **Actors:** A2, A4, A1
  - **Steps:** 현재 skills/discuss/SKILL.md Step 2 (Researcher + Devil's Advocate 병렬 dispatch) → Step 2.5 (Worker Output Defense) → Step 3 (Critic) → Step 4 (Present Results) 그대로
  - **Outcome:** `.athanor/sessions/{id}/discuss.md` 산출 (기존 동작)
  - **Covered by:** R7

- F4. **Phase 4 handoff 메뉴 (clarify 모드 종료 후)**
  - **Trigger:** F2 종료 (requirements.md 작성 완료)
  - **Actors:** A2, A1
  - **Steps:**
    1. Leader가 user에게 다음 단계 메뉴 제시 (numbered list 또는 AskUserQuestion 형식):
       - [1] `/athanor:plan`으로 진행 — requirements.md를 input으로
       - [2] `/athanor:discuss synthesis` — 옵션 A/B가 dialog 중 떠올랐다면 이어서 합성
       - [3] `/athanor:analyze` — 코드/시스템 분석
       - [4] 일단 멈춤 — requirements.md 저장하고 종료
    2. user 선택에 따라 다음 skill 자동 dispatch 또는 종료
  - **Outcome:** 명시적 다음 단계 진입 또는 명확한 pause
  - **Covered by:** R8

- F5. **/athanor:plan input integration (downstream effect)**
  - **Trigger:** user가 `/athanor:plan` 호출 + 같은 session에 requirements.md 존재
  - **Actors:** A5
  - **Steps:** plan Step 1 ("Gather Context & Parse Request")에서 기존 discuss.md / analyze.md 로딩 로직에 requirements.md 추가. Planner A 프롬프트에 requirements.md 내용 inject. Planner A가 phase Verify에 R-ID trace 포함 가능 (v0.8.0 MUST/SHOULD bullets와 결합)
  - **Outcome:** plan-a.md의 phase Verify가 R-IDs를 cite-back. v0.8.0 Spec-then-TDD discipline과 compound 효과
  - **Covered by:** R9, AE3

---

## Requirements

**Mode dispatch (Step 1)**

- R1. `/athanor:discuss` Step 1은 user에게 모드 선택 질문 1회를 발화한다. 옵션은 (a) 옵션 A/B 명확 → synthesis 모드, (b) 의도 명확화 필요 → clarify 모드, (c) 잘 모르겠다 → clarify 모드로 시작.
- R2. user 응답에 따라 leader는 즉시 분기. 자동 모드 감지는 하지 않는다 (false-positive 위험 회피).

**Clarify mode dialog (F2)**

- R3. clarify dialog는 single-Claude로 진행 (parallel workers 없음, Codex 없음). leader가 직접 dialog agent로 동작.
- R4. ce-brainstorm Standard tier 4 gap lenses 채택 — evidence / specificity / counterfactual / attachment. 각 lens는 user opening에 해당 gap이 있을 때만 fire (Phase 1.2 internal scan).
- R5. dialog 진행은 ce-brainstorm Interaction Rules 따름 — 한 번에 한 질문, 가능하면 AskUserQuestion 메뉴, 일부 introspective probe는 open-ended.
- R6. dialog 종료 시 ce-brainstorm requirements-capture.md 템플릿을 채택한 `.athanor/sessions/{id}/requirements.md` 산출 — Summary / Problem Frame / Actors (A-IDs) / Key Flows (F-IDs) / Requirements (R-IDs) / Acceptance Examples (AE-IDs) / Success Criteria / Scope Boundaries / Key Decisions / Dependencies / Outstanding Questions 섹션.

**Synthesis mode (F3, backwards compat)**

- R7. synthesis 모드의 모든 동작 (Step 2 Researcher / Devil's Advocate / Step 2.5 Worker Output Defense / Step 3 Critic / Step 4 Present Results)은 v0.9.0에서 변경되지 않는다. discuss.md 산출 경로 그대로.

**Phase 4 handoff (F4)**

- R8. clarify 모드 종료 후 leader는 user에게 4-option 메뉴를 제시 ((1) plan / (2) synthesis chain / (3) analyze / (4) 멈춤). 자동 chain하지 않는다. AskUserQuestion 또는 numbered chat list로 발화.

**Downstream plan integration (F5)**

- R9. `/athanor:plan` Step 1은 session 디렉토리에 requirements.md가 있으면 기존 discuss.md / analyze.md 로딩 로직에 requirements.md를 추가한다. Planner A 프롬프트에 그 내용을 context로 inject. requirements.md 부재 시 현재 동작과 동일.

**Discoverability**

- R10. `/athanor:discuss` skill description의 trigger keyword 그룹에 clarify-방향 자연어를 추가 — "의도 명확화" / "헷갈려" / "뭘 해야할지" / "명확히". 기존 synthesis-방향 trigger ("논의", "이런게 좋을까", "A vs B", "브레인스토밍")는 그대로 유지. trigger 통합 → discuss 안에서 분기.

**Honesty arc**

- R11. CLAUDE.md Commands 표의 `/athanor:discuss` Purpose 칸을 갱신 — "Decision brainstorming + intent clarification (dual mode)" 또는 동등 표현. CHANGELOG에서 "advisory dialog, planner-classified gap probes" 같은 표현 채택. "ce-brainstorm equivalent" / "intent-clarification enforced" 같은 과장 표현 회피.

---

## Acceptance Examples

- AE1. **Covers R1, R3, R4, F1, F2.** Given: user가 `/athanor:discuss '로그인 개선하고 싶은데'`라고 호출. When: Step 1에서 모드 질문 발화. user가 "잘 모르겠다, 의도부터" 선택. Then: leader가 clarify 모드 진입. internal scan에서 specificity gap + attachment gap 감지. open-ended probe 발화: "구체적으로 누가 로그인을 못 해서 불만이었나, 1-2명 떠올릴 수 있나?" → user 답변 → 다음 probe → integration check → scoping synthesis 발화 → user 확정 → requirements.md 작성.

- AE2. **Covers R6.** Given: clarify dialog 종료 후 requirements.md 작성 시점. When: leader가 ce-brainstorm requirements-capture.md 템플릿 적용. Then: 산출된 requirements.md는 frontmatter (`date`, `topic`) + Summary + Problem Frame + Actors (A-IDs assigned) + Key Flows (F-IDs assigned) + Requirements (R-IDs assigned, 필요시 그룹 헤더) + Acceptance Examples (AE-IDs assigned, behavioral-conditional requirements 커버) + Success Criteria + Scope Boundaries + Key Decisions + Dependencies / Assumptions + Outstanding Questions 섹션을 포함.

- AE3. **Covers R9, F5.** Given: 같은 session에 `requirements.md`와 user가 호출한 `/athanor:plan`이 있다. When: plan Step 1 Gather Context. Then: Planner A 프롬프트가 discuss.md / analyze.md (있으면)에 더해 requirements.md 내용을 context block에 inject. Planner A 산출 plan-a.md의 phase Verify field가 가능한 한 origin R-IDs를 cite-back ("R3, R5 충족 확인" 같이 명시).

- AE4. **Covers R7.** Given: user가 `/athanor:discuss '세션 ID를 UUID vs sequential 중 뭘 쓸까'` 호출. When: Step 1 모드 질문에서 user가 "A vs B 명확" 선택. Then: leader가 synthesis 모드로 진입. Step 2 Researcher + Devil's Advocate 병렬 dispatch (현재 동작 그대로). Step 3 Critic. discuss.md 산출. requirements.md는 작성하지 않음.

- AE5. **Covers R8, F4.** Given: clarify 모드가 종료되어 requirements.md가 작성됨. When: Phase 4 handoff. Then: leader가 user에게 메뉴 발화 — [1] plan / [2] synthesis chain / [3] analyze / [4] 멈춤. user가 [1] 선택 시 leader가 `/athanor:plan` 자동 dispatch. [2] 선택 시 leader가 같은 skill의 synthesis 모드 재진입. [4] 선택 시 종료.

- AE6. **Covers R11.** Given: v0.9.0 CHANGELOG draft. When: 검토. Then: "ce-brainstorm equivalent" / "intent-clarification enforced" 같은 과장 표현 없음. "advisory dialog mode" / "planner-classified gap probes" / "single-Claude clarify dialog" 같은 정직한 framing 채택. v0.7.7~v0.8.0 honesty arc 일관 유지.

---

## Success Criteria

- 사용자 outcome: 모호한 의도로 athanor에 들어와도 `/athanor:discuss`가 의미 있게 사용자 의도를 명확화한다. 동일 세션에서 `/athanor:plan`을 호출하면 plan-a.md가 requirements.md의 R-IDs를 trace하며 product behavior를 발명하지 않는다.
- 기존 사용자 outcome: `/athanor:discuss`의 synthesis 모드 호출은 v0.9.0에서 변경 없음 (backwards compat). 기존 동작 그대로 진입.
- 다운스트림 agent 핸드오프: `/ce-plan` 또는 후속 athanor 사용자가 본 문서만 보고 v0.9.0 PR을 구성할 수 있다 (skills/discuss/SKILL.md 변경 영역, plan/SKILL.md Step 1 input 추가, CLAUDE.md Commands 표 + 트리거 키워드, CHANGELOG voice, 테스트 위치까지 추론 가능).
- Carrying cost 정당화: synthesis 모드만 호출하는 사용자는 추가 마찰 zero (Step 1 질문 1회만). clarify 모드만 호출하는 사용자도 정확히 ce-brainstorm 등가 경험.

---

## Scope Boundaries

- 새 `/athanor:clarify` 명령어 신설 — 기각. `/athanor:discuss` 안에 흡수.
- 입력 shape 자동 감지 (`A vs B` 키워드 패턴, 자연어 분류) — 기각. Step 1 explicit 질문 채택.
- clarify → synthesis 자동 chain — 기각. Phase 4 메뉴로 user 선택.
- clarify → plan 자동 chain — 기각. Phase 4 메뉴로 user 선택.
- `/athanor:discuss` synthesis 모드 deprecation — 기각. 현재 동작 보존.
- ce-brainstorm의 Lightweight tier / Deep-product tier 추가 — 기각. v0.9.0은 Standard tier 등가만 (4 lenses). Deep-product의 durability gap probe는 v0.9.1+ 후보.
- Codex를 clarify dialog에 도입 — 기각. clarify는 single-Claude (dialog는 단일 모델이 자연). Codex는 synthesis 모드의 Worker B에서만 (현재 동작 보존).
- 기존 sessions의 backwards compat 마이그레이션 (이전 discuss.md를 requirements.md로 변환) — 기각. 자연 grandfathered.

### Deferred to Follow-Up Work

- **v0.9.1**: Deep-product tier durability gap probe + 추가 시나리오 (옵션 명확화 후 자동 synthesis chain은 user opt-in flag로).
- **v0.9.x**: clarify dialog의 codex cross-model 옵션 (현재는 single-Claude만).
- **v0.9.x**: clarify 산출 requirements.md를 `/athanor:plan` 외에 `/athanor:work` Splitter도 직접 읽도록 (현재는 plan 경유).

---

## Key Decisions

- **새 명령어 vs 기존 흡수**: 기존 `/athanor:discuss` 흡수 채택. 새 명령어 surface 증가 회피, athanor의 10개 user-invocable skill 표면 유지.
- **모드 분기 방식**: Step 1 explicit 질문. 자동 감지 (heuristic)는 false-positive 위험으로 기각. user 의사결정 가시화 우선.
- **clarify dialog 구조**: single-Claude (no parallel workers). ce-brainstorm 자체가 single-agent dialog 패턴이므로 일관성.
- **Gap probe 채택 범위**: Standard tier 4 lenses (evidence / specificity / counterfactual / attachment). Deep-product durability는 v0.9.1+ 후보.
- **출력 파일명**: `requirements.md` (clarify 모드 전용) + `discuss.md` (synthesis 모드 전용). frontmatter mode 필드로 합치는 대안은 plan-side parsing 복잡성으로 기각.
- **Phase 4 handoff**: stop-after-requirements + user 선택 메뉴. 자동 chain은 user 의도 무시 위험으로 기각.
- **`/athanor:plan` integration**: plan Step 1이 자동으로 requirements.md 로드 (있으면). 부재 시 현재 동작과 동일 (backwards compat).
- **Trigger keyword 확장**: 기존 trigger + clarify-방향 자연어 추가. 트리거 통합으로 discoverability 확보.
- **Honesty framing**: "advisory dialog mode" / "planner-classified gap probes". 과장 표현 회피 (v0.7.7~v0.8.0 arc 일관).

---

## Dependencies / Assumptions

- ce-brainstorm 스킬 (compound-engineering plugin)이 안정적으로 동작 중인 것으로 가정. 본 작업은 athanor 안에 등가 패턴을 이식.
- v0.8.0의 Spec-then-TDD discipline (Planner A의 MUST/SHOULD Verify 필드)이 출하된 상태에서 v0.9.0 진행. R9 (plan input integration)의 compound 효과는 v0.8.0 베이스 위에서만 발현.
- ce-brainstorm requirements-capture.md 템플릿을 그대로 채택할 수 있다는 가정 — license 호환 (MIT vendored 패턴).
- `/athanor:discuss` 호출자의 평균 입력 mode 분포에 대한 가설: clarify 모드 호출 비율이 의미 있게 존재 (현재 데이터 없음). 첫 운용에서 데이터 수집 후 분기 휴리스틱 보강 후보 (v0.9.1+).
- single-Claude dialog가 ce-brainstorm-equivalent 품질로 작동한다는 가정 — ce-brainstorm 자체가 단일 agent dialog이므로 reasonable.

---

## Outstanding Questions

### Resolve Before Planning

(없음 — 모든 product 결정은 본 문서에서 확정)

### Deferred to Planning

- [Affects R3, F2][Technical] clarify dialog의 internal Phase 1.2 gap scan 로직을 어디에 표현할지 — skills/discuss/SKILL.md inline prose vs 별도 reference markdown (`skills/discuss/references/clarify-gap-probes.md`).
- [Affects R6][Technical] requirements.md 템플릿 자체를 athanor 안에 어떻게 vendor할지 — ce-brainstorm references 파일을 직접 vendor (T2 패턴) vs SKILL.md prose에 inline embed.
- [Affects R9, F5][Technical] plan Step 1의 input 로딩 로직 변경 — discuss.md / analyze.md / requirements.md 셋 다 있을 때 ordering / merging 규칙.
- [Affects R8, F4][Technical] Phase 4 메뉴 발화 방식 — AskUserQuestion vs numbered chat list (블로킹 도구 가용성에 따라 fallback).
- [Affects R2][Needs research] 자연어 trigger keyword가 실제로 clarify-vs-synthesis 분기를 user 의도와 일치시키는지 검증 — 첫 운용 후 데이터 기반 보강.
- [Affects R11][Technical] CLAUDE.md Commands 표의 Purpose 칸 정확 문구 — "Decision brainstorming + intent clarification (dual mode)" vs 다른 표현.
