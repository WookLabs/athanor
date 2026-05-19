---
date: 2026-05-20
topic: athanor-using-superpowers-boundary
---

# v0.11.1 — `using-superpowers` boundary clarification

## Summary

v0.11.1은 항상 SessionStart에 로드되는 `superpowers:using-superpowers` skill과
athanor-native 9개 Thin Leader skill 사이의 운영 경계를 문서화한다. 산출은
세 가지 — (1) `CLAUDE.md §Defense Mechanisms` 항목 추가, (2) 11개 native
SKILL.md preamble line, (3) 2~3개 regression test. 코드 무거운 release가 아닌
산문 + lock-in 중심.

## Problem Frame

v0.10.0에서 superpowers v5.1.0을 흡수하면서 `superpowers:using-superpowers`
skill이 vendor 됐다. 이 skill은 SessionStart hook에서 자동으로 컨텍스트에
주입되며, "ABSOLUTELY MUST invoke" / "1% chance → must use it" /
EXTREMELY-IMPORTANT 톤으로 매 turn 전에 skill 적용 여부를 검사하라고 강제한다.

이 강제 톤은 athanor-native skill의 운영 원칙 — Thin Leader (leader는
dispatch만, worker가 실작업) + planner-classified discipline (Spec-then-TDD
advisory 분기) — 과 voice 측면에서 충돌한다. 실제 runtime 차단 사례는
관측되지 않았지만, 사용자가 v0.11.0에서 "나중에는 athanor만 쓸거야"라고
명시한 trajectory를 따라가면 다음 ambiguity가 표면화된다:

- `/athanor:plan` 호출 시 `using-superpowers`의 MUST-rule이 Thin Leader
  dispatch보다 우선하는가?
- skill 작성자가 새 native SKILL.md를 만들 때 `using-superpowers`
  pre-response check을 명시적으로 따라야 하는가?
- honesty arc 라벨 ("advisory" vs "enforced")이 이 경계에 어떻게
  매핑되는가?

v0.11.1은 이 세 질문을 documentation + skill preamble 수준에서 닫는다.
upstream `using-superpowers` 내용은 손대지 않는다 (T2 provenance lock).

## Actors

- **A1** — athanor end-user. `/athanor:<native-skill>` 명령을 호출하는
  주체. 어느 discipline이 적용되는지 예측 가능해야 함.
- **A2** — athanor skill author / maintainer. `skills/` 아래 파일을
  편집할 때 preamble convention을 따른다.
- **A3** — future contributor. `CLAUDE.md`를 읽고 voice/discipline 경계를
  60초 안에 파악할 수 있어야 함.

## Key Flows

- **F1** (A1) — user가 `/athanor:plan`을 호출한다. SessionStart에
  `using-superpowers`가 로드돼 있다. 기대 동작: native skill의 Thin
  Leader + planner-classified discipline이 운영 voice로 작동;
  `using-superpowers`의 MUST-rule은 acknowledged-but-advisory 위치.
- **F2** (A2) — skill author가 `skills/<native>/SKILL.md`를 새로 만들거나
  편집한다. 표준 preamble line이 SKILL.md 알려진 위치에 1줄로 들어간다.
  author는 발명하지 않고 convention만 따른다.
- **F3** (A3) — contributor가 `CLAUDE.md §Defense Mechanisms`를 펼친다.
  `using-superpowers` 행 또는 단락을 발견하고, "vendored under sp-
  namespace / SessionStart auto-load / MUST tone is advisory in
  athanor-native context"을 60초 안에 이해.

## Requirements

- **R1 (MUST)** — `CLAUDE.md §Defense Mechanisms`에 `using-superpowers`
  경계를 설명하는 새 row 또는 paragraph 추가. 다음 4요소 포함:
  (a) sp- namespace에 vendor 되어 있음,
  (b) SessionStart에 auto-load 됨,
  (c) "MUST invoke" 톤은 athanor-native discipline context에서는 advisory,
  (d) athanor-native 영역에서 discovery는 leader dispatch로 해소.
- **R2 (MUST)** — 9개 athanor-native **Thin Leader** SKILL.md (analyze,
  debug, deep-plan, discuss, lite-plan, plan, review, setup, work)에
  표준화된 preamble 한 단락을 §Identity 직후에 추가. **Carve-out:**
  `scope-drift`와 `verification-before-completion`는 unprefixed slot을
  차지하지만 Thin Leader 패턴이 아닌 vendored-content skill — 자체
  voice 유지로 제외. 내용: "Thin Leader +
  planner-classified discipline applies in this skill context;
  `using-superpowers`'s pre-response invocation pressure is advisory
  here — discovery resolves through leader dispatch."
- **R3 (MUST)** — 벤더 `skills/sp-using-superpowers/SKILL.md` body는
  편집 금지 (T2 provenance lock). 경계는 athanor wrapper layer에만 둔다.
- **R4 (MUST)** — 2~3개 regression test 추가 (신규 파일 또는 기존
  v011 test 확장 — 결정은 planner 몫):
  (i) `CLAUDE.md`에 boundary paragraph가 존재하고 4요소 signal phrase
       (sp- vendored / SessionStart / advisory / leader dispatch)를 포함,
  (ii) 9개 native Thin Leader SKILL.md 각각이 preamble signal phrase를 정확히
       1회 포함 — 누락도 중복도 fail,
  (iii) 벤더 `sp-using-superpowers/SKILL.md`가 drift script 기준
        upstream과 일치 (이미 v0.10.1 drift script로 enforced 됨 —
        본 test는 회귀 lock).
- **R5 (MUST)** — honesty arc 보존. boundary 문서는 "advisory" 또는
  "advisory in this context" 라벨을 사용. runtime gate 추가가 없으므로
  "enforced"로 격상하지 않는다 (v0.7.x~v0.10.x honesty arc 회귀 잠금).
- **R6 (SHOULD)** — `CHANGELOG.md` v0.11.1 entry는 honesty-arc voice
  유지. positive commitment만 ("athanor-native discipline applies here").
  forbidden: "superpowers deprecated", "athanor replaces superpowers",
  "supersedes using-superpowers" 등 사용 금지/대체 framing.
- **R7 (SHOULD)** — preamble line text는 짧게 (skill당 ≤2줄). 기존
  SKILL.md frontmatter나 첫 섹션을 방해하지 않는 위치 (frontmatter 직후
  또는 §Identity 단락 안쪽).

## Acceptance Examples

- **AE1 (R1 + R3)** — `grep -i "using-superpowers" CLAUDE.md` → 적어도
  1개 paragraph가 4 signal phrase를 포함하며 advisory 라벨을 둠.
  `scripts/check_vendor_drift.py` → `skills/sp-using-superpowers/SKILL.md`
  drift 0줄.
- **AE2 (R2)** — 11개 SKILL.md 각각에 대해 preamble signal phrase 검색
  → 정확히 1회 일치. 0회 (누락) 또는 ≥2회 (중복) 모두 회귀 test fail.
- **AE3 (R4)** — `pytest tests/test_regression_v011_1_*.py` (또는 확장된
  v010_honesty_arc.py) → 모두 green. 387 baseline test 그대로 green.
- **AE4 (R5 + R6)** — `CHANGELOG.md` v0.11.1 entry + `CLAUDE.md`
  boundary paragraph에 forbidden phrase ("superpowers deprecated",
  "athanor replaces superpowers", "supersedes using-superpowers",
  "do not use superpowers") 검색 → 0 hit.

## Success Criteria

- documentation gap closed — future contributor (A3)가 `CLAUDE.md`만
  읽고 "athanor-native skill 호출 시 using-superpowers MUST-rule이
  Thin Leader를 덮는가?"에 60초 안에 답할 수 있다.
- identity guard 4개 (Thin Leader / cross-model adversarial /
  Spec-then-TDD / Stop hook) 모두 그대로 작동 — boundary 추가가 dilute
  하지 않는다.
- honesty arc 회귀 잠금 — release prose는 "advisory" 라벨만 사용; 새
  runtime gate 없음.
- 387 baseline test + 2~3 신규 v0.11.1 test 전부 green.

## Scope Boundaries

**IN scope (v0.11.1):**
- `CLAUDE.md` §Defense Mechanisms 1단락 또는 1행 추가
- 9개 native Thin Leader SKILL.md preamble line 추가 (skill당 ≤2줄)
- 2~3 regression test
- `CHANGELOG.md` v0.11.1 entry
- version bump (plugin.json / marketplace.json / athanor.json /
  templates/athanor.json / schemas/athanor-config.schema.json)

**OUT of scope (deferred):**
- `sp-*` 13개 skill의 deprecation 결정 → carry to v0.12.x **A5**
- `using-superpowers` upstream 콘텐츠 편집 → T2 violation, 영구 OUT
- runtime hook으로 boundary 강제 → advisory positioning과 충돌, OUT
- mid-session `hooks.profile` mutation guard → carry to **sec-***
- LLM-class semantic similarity for `stop_verify_claims.py` →
  carry to **sec-003**
- transcript-event introspection → carry to **sec-001**
- CE 37개 skill cross-cutting 결정 → 별도 brainstorm

## Key Decisions

- **KD1** — Integration shape = **opt-out (advisory-coexist)**. native
  skill이 자신의 discipline을 명시적으로 선언; `using-superpowers`는
  로드 상태 유지하되 native context에서 advisory 위치. 다른 shape
  ((b) opt-in / (c) replace / (d) pure-doc) 평가했고 채택 안 함 —
  근거: opt-out이 v0.10.0 Thin Leader identity guard와 가장 적은
  dilute로 맞물림.
- **KD2** — Boundary 적용 대상 = **11 native skill만**. `sp-*` 13개는
  superpowers 출신이라 using-superpowers와 자연스러운 정합; carve-out
  불필요. `ce-*` 37개는 별도 voice라 boundary 무관.
- **KD3** — 강제 메커니즘 추가하지 않음. v0.7.9 enforced-vs-advisory
  honesty arc는 runtime gate (Stop hook 같은 exit-2)가 없으면
  "enforced" 라벨 금지를 요구. boundary는 "advisory (preamble-declared)"
  로 둔다.

## Dependencies / Assumptions

- **DA1** — v0.10.1 ship된 `scripts/check_vendor_drift.py`가 벤더 파일
  body의 우발적 편집을 잡는다. R3 (upstream lock)은 별도 enforcement
  없이 drift script 회귀 cover로 충분.
- **DA2** — 11 native skill enumeration은
  `tests/test_regression_v010_namespace_layout.py`의 `ATHANOR_NATIVE`
  set이 single source of truth. v0.11.1 test도 같은 set을 import 해
  drift 방지.
- **DA3** — `CLAUDE.md §Defense Mechanisms` 표 또는 그 직후 단락이
  canonical 위치. 기존 5개 메커니즘 (Stop-Phrase / Read-Before-Edit /
  Completion-Claim Verification / Scope Drift / Spec-then-TDD) 패턴과
  정합.

## Outstanding Questions

**Resolve before planning:**
- 없음. scoping synthesis에서 call-out #1 (integration shape)은
  opt-out으로, call-out #2 (boundary 적용 범위)는 11 native만으로 확정.

**Deferred to planning (planner가 정한다):**
- **OQ1** — preamble line의 정확한 wording. 후보: "Thin Leader +
  planner-classified discipline applies in this skill context;
  `using-superpowers`'s pre-response invocation pressure is advisory
  here — discovery resolves through leader dispatch." Planner가 길이
  / tone / bilingual 여부 (en만 vs en+ko) 결정.
- **OQ2** — `CLAUDE.md` 배치. (a) §Defense Mechanisms status table에
  새 행으로 추가 vs (b) table 직후 짧은 단락. Planner가 rendering과
  기존 패턴 fit으로 결정.
- **OQ3** — regression test 위치. (a) 신규
  `tests/test_regression_v011_1_using_superpowers_boundary.py` vs
  (b) 기존 `tests/test_regression_v010_honesty_arc.py` 확장. Planner가
  파일 응집성으로 결정.
