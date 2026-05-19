# Athanor — Implementation State

> 이 파일은 현재 구현 진행 상태를 추적합니다.
> 각 Phase / 릴리스 완료 시 업데이트합니다.
> 자세한 변경 내역은 `CHANGELOG.md` 를 정본(source of truth)으로 봅니다.

## Current Phase: SHIPPING — v0.11.1 (`using-superpowers` boundary clarification)

v0.10.0에서 흡수된 `superpowers:using-superpowers`가 SessionStart에 자동
로드되어 "ABSOLUTELY MUST invoke before response" 톤을 강제한다. v0.11.1은
그 톤이 athanor-native 9개 Thin Leader skill (analyze, debug, deep-plan,
discuss, lite-plan, plan, review, setup, work) 호출 context에서는
**advisory**라는 boundary를 문서화한다. runtime gate 추가 없음, vendored
content 편집 없음 (T2 lock). 산문 + lock-in test 중심의 작은 release.

- **U1**: brainstorm + plan 영구 트랙 (docs/brainstorms/ + docs/plans/).
- **U2**: `CLAUDE.md §Defense Mechanisms` 표에 row + 직후 상세 단락 추가.
  라벨: `advisory (preamble-declared)`. carve-out 명시 (scope-drift +
  verification-before-completion는 unprefixed slot이나 Thin Leader 패턴
  아닌 vendored-content이라 제외).
- **U3**: 9개 native Thin Leader SKILL.md 각각에
  `### v0.11.1 using-superpowers boundary` subsection (canonical 단락,
  모든 파일 동일) 추가.
- **U4**: 9개 신규 regression test (`tests/test_regression_v011_1_*`).
  - CLAUDE.md row presence + 4 signal phrase + advisory label
  - 9 skill preamble heading exactness + 7 canonical signal coverage
  - carve-out enforcement (excluded 2 skill must NOT carry preamble)
  - vendored sp-using-superpowers presence pin
  - CLAUDE.md + CHANGELOG forbidden-phrase guard (positive-commitment-only)
- **U5**: version bump 0.11.0 → 0.11.1; CHANGELOG; STATE.md.

honesty arc — runtime gate 추가가 없으므로 "enforced"로 격상하지 않는다.
boundary는 **advisory (preamble-declared)**로 라벨 고정. forbidden-phrase
test가 supersession/deprecate framing을 잠금.

### v0.11.1 ship surface

- 사용자-호출 skills: **62개** (변동 없음).
- Regression test suite: **396 passing** (387 baseline + 9 신규 v0.11.1).
- Active executable contracts (v0.11.1 신규):
  `v011-1-claude-md-boundary-row-and-signals`,
  `v011-1-native-thin-leader-skills-canonical-preamble`,
  `v011-1-carve-out-no-preamble-in-vendored-content-skills`,
  `v011-1-positive-commitment-only-voice`.

### v0.11.1 알려진 residual (v0.12.x+ 후보)

- A5 native-vs-vendored deprecation candidates (e.g.,
  `/athanor:discuss` synthesis vs `/athanor:ce-brainstorm`)
- LLM-class paraphrase / semantic similarity (sec-003 last carry)
- Transcript-event introspection (sec-001 잔류)
- Mid-session profile mutation guard
- CE 37 skill cross-cutting decisions (별도 brainstorm)

## Previous Phase: v0.11.0 (`/athanor:lfg` wrapper — standalone LFG closure)

v0.10.0 흡수 arc의 standalone narrative 마무리. `/athanor:lfg` wrapper
skill을 신설해서 LFG end-to-end 파이프라인이 athanor-native 명령으로
identity-bearing step에서 자동 dispatch. vendored `/athanor:ce-lfg` 는
T2 그대로 보존 — 두 skill 공존, 사용자가 namespace로 선택.

- **U1**: `skills/lfg/SKILL.md` 신설 (depth-1 auto-discovery).
  - Step 1 → `/athanor:plan` (cross-model adversarial)
  - Step 2 → `/athanor:work` (Spec-then-TDD)
  - Step 3 → `/athanor:review` (parallel 6-lens)
  - Steps 4-8 → vendored ce-lfg shape 그대로 (autofix persist /
    residual handoff / ce-test-browser / commit-push-PR / CI watch 3
    fix iterations) + Step 9 `<promise>DONE</promise>`.
- **U2** + **U3**: voice 회귀 + 10개 신규 regression tests.
  - frontmatter / 각 step의 athanor 명령 호출 / 모든 8개 step anchor /
    forbidden-phrase / difference-from-ce-lfg disclosure / T2 (ce-lfg
    body 무변경) / 공존 보장.
- **U4**: version bump 0.10.3 → 0.11.0; CHANGELOG; STATE.md; CLAUDE.md
  Commands table에 `/athanor:lfg` 추가.

honesty arc — origin §R4 그대로 carry. v0.11.0는 vendored `/athanor:ce-lfg`
를 deprecate하거나 superseded라고 framing하지 않음. positive commitment
("athanor stands alone")만, negative commitment 안 함.

### v0.11.0 ship surface

- 사용자-호출 skills: **62개** (61 v0.10.x + 1 신규 `/athanor:lfg`).
- Regression test suite: ≥ **384 passing** (374 baseline post-v0.10.3 +
  10 new v0.11.0).
- Release gate (`scripts/check_release_ready.py --ci`) v0.11.0에서 green.
- Active executable contracts (v0.11.0 신규):
  `v011-athanor-lfg-skill-exists-depth-1`,
  `v011-step-1-2-3-invoke-athanor-native`,
  `v011-vendored-ce-lfg-body-unchanged`,
  `v011-positive-commitment-only-voice`.

### v0.11.0 알려진 residual (v0.11.1+ 후보)

- A4 `using-superpowers` cross-cutting integration
- A5 native-vs-vendored deprecation candidates (`/athanor:discuss`
  synthesis vs `/athanor:ce-brainstorm` 등)
- LLM-class paraphrase / semantic similarity (sec-003 last carry)
- Transcript-event introspection (sec-001 잔류)
- Mid-session profile mutation guard

## Previous-Previous Phase: v0.10.3 (Stop hook residual closure — R1+R2+R3)

v0.10.2가 정직하게 deferred로 표시한 세 잔류를 마무리.

- **R1 (Greek/Armenian homoglyph fold)** — `_CYRILLIC_TO_LATIN_TABLE` →
  `_CONFUSABLES_TO_LATIN_TABLE` 로 rename. Greek 13자 (α ε ι ν ο ρ υ
  + 7 uppercase) + Armenian ո 추가. "deployed tο production" (Greek ο)
  같은 attack vector 차단.
- **R2 (conditional/speculative tense suppression)** —
  `_is_conditional_or_speculative_context()` 도입. 매칭 위치 직전의
  clause-boundary로 거슬러 올라가서 그 clause의 first token이
  `{if, once, when, whenever, should, could, would, unless}` 또는 한국어
  prefix `만약/만일`이면 매칭 suppress. "If all tests are green, merge" →
  더 이상 트리거 안 됨.
- **R3 (attribution / quoted-context skip)** —
  `_is_attributed_quote_context()` 도입. 매칭이 paired quote (`"..."`/
  `'...'`/`` `...` ``) 안에 있거나, EN 40-char-before window 안에 said/
  claimed/wrote/etc.가 있거나, KO 40-char-after window 안에 라고-했/라고-적/
  라고-말이 있으면 suppress. `the v0.7.6 docs said "tests pass"` → 더
  이상 트리거 안 됨.
- **v0.10.2 known-residual tests inverted** per plan §D6 — current-
  behavior pins are intentional flippers; v0.10.3 closes them and
  assertions invert.

### v0.10.3 ship surface

- 사용자-호출 skills: 61개 (변동 없음).
- Regression test suite: ≥ 374 passing (352 baseline post-v0.10.2 + 22
  new v0.10.3 + 4 inverted pins).
- Release gate (`scripts/check_release_ready.py --ci`) v0.10.3에서 green.
- Active executable contracts (v0.10.3 신규):
  `v0103-greek-armenian-fold`,
  `v0103-conditional-clause-prefix-suppression`,
  `v0103-attribution-quote-context-suppression`,
  `v0103-known-residual-inversion`.

### v0.10.3 알려진 residual (v0.11.0+ 후보)

- LLM-class paraphrase (semantic similarity)
- Speculative tense without prefix marker ("Probably CI is green")
- Multi-paragraph quote span; code-block context
- Cherokee / full-width Latin / 기타 script confusables
- Sentinel forgery via filesystem nonce state (sec-001)
- Mid-session profile mutation
- A3 LFG pipeline reconciliation
- A4 superpowers cross-cutting integration
- A5 native-vs-vendored deprecation candidates

## Previous Phase: v0.10.2 (Stop hook paraphrase + NFKC + cyrillic + vendor-aware closure)

v0.7.9 docstring overclaim의 마지막 매듭. v0.7.9에서 "regex 패턴 + NFKC +
confusables fold ship됨" 이라고 claim했지만 실제로는 안 ship된 것을, v0.10.1
U6 audit가 잡아내고 정직하게 docstring 교정했다. v0.10.2가 *실제로* 그 약속을
수행한다.

- **U1 (ADV-006 closure)**: `_normalize_for_match()` 도입. NFKC 정규화 +
  17자 Cyrillic→Latin 융합 + lowercase. "tеsts pass" (Cyrillic 'е') →
  "tests pass". Fullwidth 공격도 NFKC로 cover.
- **U2 (sec-003 closure)**: `MATERIAL_CLAIM_PATTERNS` regex 6개 (CI is
  green / all tests passing / the build is healthy / deploy paraphrase /
  KO 테스트 통과 / KO 빌드 성공). Verb-anchored — prose 거짓-양성 최소화.
  Module-load assert로 빈 리스트 silent disable 차단.
- **U3 (A2 closure)**: vendored CE/superpowers idiom 18개 추가 (review
  complete, `<promise>DONE</promise>`, all checks passing, branch merged,
  리뷰 완료 등).
- **U4**: docstring을 honesty arc 그대로 — "v0.7.9 overclaim →
  v0.10.1 audit → v0.10.2 ships" 명시. v0.10.0 "vendored-surface 거짓-부정"
  단락은 vendor-aware whitelist가 active해진 만큼 trimmed.

### v0.10.2 ship surface

- 사용자-호출 skills: 61개 (변동 없음 from v0.10.0+).
- Regression test suite: ≥ 352 passing (314 baseline post-v0.10.1 + 38
  new v0.10.2).
- Release gate (`scripts/check_release_ready.py --ci`) v0.10.2에서 green.
- Active executable contracts (v0.10.2 신규):
  `v0102-normalize-for-match-nfkc-cyrillic`,
  `v0102-material-claim-patterns-regex`,
  `v0102-vendor-aware-whitelist-extension`,
  `v0102-known-residual-current-behavior-pin`.

### v0.10.2 알려진 residual (v0.10.3+ 후보)

- LLM-class paraphrase (의미적 유사도 — clause embedding)
- Conditional / speculative tense ("If tests are green, merge")
- 인용된 역사적 참조 ("the v0.7.6 docs said 'tests pass'")
- Greek / Armenian 등 비-Cyrillic homoglyph
- Transcript-event introspection (sec-001 잔류)
- Mid-session profile mutation guard

## Previous Phase: v0.10.1 (Vendor hygiene + Splitter audit field + B2 honesty closure)

v0.10.0 후속 작은 릴리스. 정체성 결정 / architectural 변경 없음. 세 개의
deferred 항목 마무리 + v0.7.9 stop_verify_claims.py docstring overclaim
정직성 교정.

- **U1**: `scripts/check_vendor_drift.py` — vendor 트리 drift 단일 명령
  체크. CE upstream은 `ce-` 접두사 유지, superpowers는 `sp-` 추가 (rename
  매핑 포함, `ce-lfg`는 upstream `lfg`로 다시 매핑). exit 0 = no drift /
  1 = drift / 2 = upstream cache 부재. 머지된 v0.10.0 트리 대상 50/50
  unchanged 확인.
- **U2**: v0.9.0 시점 vendored references 2개 파일의 `source-commit`
  placeholder ("vendored at athanor v0.9.0 release time") → 정확한
  `compound-engineering@3.8.2 <upstream-path>` pin + v0.10.0 verification
  note. SHA pin은 plugin-cache distribution에서 도달 불가 — version-tag
  fallback per CLAUDE.md §Vendored Surface drift policy.
- **U3 + U4**: `/athanor:work` Splitter 출력 schema에
  `classification_reason: <one-line>` 필드 추가. 분류값과 무관하게 모든
  subtask가 갖는다 (acceptance_criteria는 spec-then-tdd-only인 것과 다름).
  3개 ambiguous-case fixture (case_01 spec-vs-direct, case_02 refactor
  test-aware, case_03 prose-contract direct). 길이 계약: ≤ 200 chars,
  no newline. Heuristic 자체는 v0.8.0 그대로 — 필드는 audit trail 용도.
- **U6**: B2 (v0.7.9.1 paraphrase bypass closure) 상태 재검증.
  `is_material_claim()` 함수가 literal substring matching만 하고 paraphrase
  regex / NFKC / confusables fold가 구현 안 됨에도, top-level docstring이
  v0.7.9에서 이미 ship한 것처럼 명시 — **honesty-arc 위반**. v0.10.1에서
  docstring 교정 (runtime 변경 없음). 실제 B2 작업은 v0.10.2로 carry.

### v0.10.1 ship surface

- 사용자-호출 skills: 61개 (10 native + 1 already-vendored verification +
  37 ce-* + 13 sp-*). v0.10.0 그대로.
- Regression test suite: ≥ 314 passing (296 baseline post-v0.10.0 + 18
  new across U1/U2/U3/U4).
- Release gate (`scripts/check_release_ready.py --ci`) v0.10.1에서 green.
- Active executable contracts (v0.10.1 신규):
  `v0101-vendor-drift-script-exit-codes`,
  `v0101-vendor-provenance-sha-pin`,
  `v0101-splitter-classification-reason-field`,
  `v0101-stop-hook-docstring-honesty`.

## Previous Phase: v0.10.0 (Absorb CE 3.8.3 + superpowers 5.1.0 — vendored superset, identity-preserving)

athanor가 compound-engineering 3.8.3 (37 skills + 49 sub-agents) +
superpowers 5.1.0 (13 skills) 을 vendor superset 으로 흡수. 사용자가
"full merge with athanor identity preserved" 로 scope 확정 (2026-05-19
대화). 네 가지 정체성 commitment 가 흡수물 위에 보존됨 — guard prose +
namespace policy + regression locks 로 보장:

1. **Thin Leader contract** — 흡수된 SKILL.md 가 "the agent does X" 라고
   해도 athanor leader 는 worker 에 dispatch 만 함. CLAUDE.md §Vendored
   Surface 명시.
2. **Cross-model adversarial planning** — `/athanor:plan` 은 Planner A
   (Claude) + Planner B (Codex) + Critic 디스패치 유지. CE 단일-agent flow
   는 `/athanor:ce-plan` 으로만 도달.
3. **Spec-then-TDD discipline** — `/athanor:work` 가 Splitter execution_note +
   conjunction-of-three Phase 3 gate 유지. `/athanor:ce-work` 와
   `/athanor:sp-test-driven-development` 는 outside.
4. **Stop hook runtime gate** — `scripts/hooks/stop_verify_claims.py` 가
   모든 Stop 에 동일하게 발화. v0.7.7 voice-tuned whitelist 는 vendored
   prose 에서 false-negative 가능 — vendor-aware whitelist 는 v0.10.1+
   work.

### v0.10.0 ship surface

- **사용자-호출 skills**: 10 native + 1 already-vendored (`verification-
  before-completion`) + 37 CE-vendored + 13 superpowers-vendored = **61 total**.
- **Sub-agents**: 기존 athanor agents + 49 CE-vendored at `agents/vendored/ce/`.
- **267 files** vendored (skills + references + sub-agent definitions
  + assets). 모두 T2 provenance block (`upstream / source-commit /
  upstream-url / license / modifications / t0-t1-disproof`) 포함.
- 1 hook (Stop, command-mode + v=2 nonce-bound + circuit breaker per
  v0.7.9; v0.10.0 에서 docstring 만 vendored-surface 스코프 명시 업데이트).
- Regression test suite: ~255 baseline (post-v0.9.0) + ~25 new (M6)
  ≥ 280 passing on Python 3.x.
- Release gate (`scripts/check_release_ready.py --ci`) 통과.
- Active executable contracts (v0.10.0 신규):
  `v010-thin-leader-guard`, `v010-cross-model-default`,
  `v010-tdd-native-default`, `v010-stop-hook-scope`,
  `v010-vendor-provenance`, `v010-namespace-collisions`,
  `v010-honesty-arc`, `v010-changelog-voice`.

### Vendor Manifest (v0.10.0)

| Source | Plugin@version | Skills | Sub-agents | Vendored on | License |
|---|---|---|---|---|---|
| compound-engineering | 3.8.3 | 37 (at `skills/ce-*/`) | 49 (at `agents/vendored/ce/`) | 2026-05-19 | MIT (Every Inc / Kieran Klaassen) |
| superpowers | 5.1.0 | 13 (at `skills/sp-*/`) | — | 2026-05-19 | MIT (Jesse Vincent) |
| superpowers | 5.0.7 → 5.1.0 | `verification-before-completion` (kept at original path from v0.7.8; NOT re-vendored at v0.10.0) | — | 2026-04-24 (original) | MIT |
| claude-octopus | (SHA-pinned) | `scope-drift` (kept at original path from earlier vendor) | — | (pre-v0.10.0) | MIT (nyldn) |

**Full inventory**: `docs/plans/2026-05-19-003-feat-v0.10.0-absorb-ce-superpowers-plan-INVENTORY.md`

### Drift check process (v0.10.0 — manual; scripted in v0.10.1)

When CE or superpowers releases a new version, manually diff each
`skills/ce-<name>/` against `~/.claude/plugins/cache/.../skills/<name>/`
(or `<no-ce-prefix>/`) and record drift findings in the next minor
release CHANGELOG entry. Automated drift detection (`scripts/check_vendor_drift.py`)
is v0.10.1 work.

## Previous Phase: v0.9.0 (`/athanor:discuss` dual-mode — clarify + synthesis)

`/athanor:discuss` 스킬에 clarify (intent 명확화) 모드 흡수 — synthesis
모드 (현재 동작)는 backwards compat 그대로. Step 1에서 user에게 모드 묻고
분기. clarify 모드는 single-Claude gap-probe dialog (4 lens: evidence /
specificity / counterfactual / attachment) + requirements.md 산출.
`/athanor:plan` Step 1이 requirements.md 자동 inject + Critic Rubric에
axis (C) R-ID traceback coverage 추가. 메커니즘은 advisory dialog mode /
planner-classified gap probes — runtime 강제 없음 (Stop hook 같은 enforce
는 v0.9.x+ 후보 — `/athanor:plan` Critic이 cite-back 미흡 시 flag만 함).

- 10 user-invocable skills + 2 internal vendored skills (`scope-drift`,
  `verification-before-completion`).
- 2 vendored references under `skills/discuss/references/` (NEW v0.9.0):
  `clarify-gap-probes.md` + `requirements-capture.md`.
- 7 worker agents (unchanged).
- 1 hook (Stop, command-mode + v=2 nonce + circuit breaker per v0.7.9).
- v0.9.0 추가: `/athanor:discuss` dual-mode + clarify single-Claude dialog
  + `requirements.md` artifact + `/athanor:plan` Step 1 auto-load + Critic
  Rubric axis (C) R-ID traceback.
- Regression test suite: ≥255 tests passing (203 baseline post-v0.8.0 +
  ≥48 new across U1-U6).
- Release gate (`scripts/check_release_ready.py --ci`) green.
- Active executable contracts (v0.9.0 신규):
  `discuss-mode-question-contract`, `discuss-synthesis-preservation`,
  `clarify-dialog-protocol`, `clarify-requirements-template`,
  `clarify-handoff-menu`, `plan-reads-requirements-md`,
  `critic-axis-c-r-id-traceback`, `discuss-trigger-keywords-qualified`.

## Previous Phase: v0.8.0 (Spec-then-TDD discipline — advisory, planner-classified)

Planner-classified Spec-then-TDD가 `/athanor:plan` + `/athanor:work`에 통합됨.
Splitter가 분류 책임 짐. Executor가 분류에 따라 분기 실행. RED 안 가면 자동
`test-aware` 강등. 메커니즘은 advisory — runtime 강제 없음 (verification 스킬
확장은 v0.8.1+ 후보).

- 10 user-invocable skills + 2 internal vendored skills (`scope-drift`, `verification-before-completion` — v0.7.9 migrated §Emission Sentinel to v=2 nonce-bound).
- 7 worker agents.
- 1 hook (Stop, **`type: command` as of v0.7.8, v=2 nonce-bound sentinel + config-resolution priority chain + circuit breaker as of v0.7.9**).
- v0.8.0 추가: subtask-level `execution_note` (`spec-then-tdd | test-aware | direct`) +
  `acceptance_criteria` propagation + `red_evidence` shape validation +
  `tests/**` broader gate + auto-downgrade on `never_red` + Critic axis-B
  classification rubric.
- Regression test suite passing on Python 3.x with `jsonschema` dependency. v0.7.7→v0.7.8→v0.7.9→v0.8.0 누적: ≥187 tests (154 baseline + 13 Phase A + 20 Phase B + 5 Phase C).
- Release gate (`scripts/check_release_ready.py --ci`) green.
- Active executable contracts: `stop-hook-command-contract`, `hook-uniqueness`, `manifest-no-hooks-field`, `schema-validates-config`, `schema-url-version-pin`, `session-lookup-convention`, `_doc-honesty`, **v0.8.0 신규 contracts**: `planner-a-verify-must-should-format`, `critic-ac-coverage-and-classification`, `splitter-execution-note-classification`, `work-dispatch-3-branch-on-execution-note`.

## Previous Phase: v0.7.9 (Stop hook hardening — nonce binding + config scoping + circuit breaker)

- v=2 nonce-bound sentinel closed P0 forgery path (v=1 bare-string)
- Config resolution priority chain (`$CLAUDE_PROJECT_DIR` → git-root → walk-up-stops-at-`.git`) closed P0 parent-directory hijack
- Circuit breaker (`hooks.stopLoopThreshold`, default 3) prevents Stop-loop runaway
- 33 new tests added (154 total post-merge of #18)

## History (시계열 요약 — 자세한 항목은 CHANGELOG.md 참조)

### Foundation — v0.1.0 ~ v0.5.x (2026-04-08 ~ 2026-04-14)

- **Phase 0–9 (v0.1.0)**: 초기 scaffold → /athanor:setup → CONVENTIONS.md → /athanor:discuss → /athanor:analyze → /athanor:plan (cross-model adversarial pipeline) → /athanor:work solo → /athanor:work --team (wave grouping, discovery relay) → Lessons system (learner + cleaner) → README & defense mechanisms 문서화.
- **v0.2.x ~ v0.5.x**: tier 분리 (lite/standard/deep plan), `/athanor:debug` triage, 파일명 중립화 (plan-claude/plan-codex → plan-a/plan-b), Codex CLI fallback 정비.

### Hook hardening cycle — v0.6.x (2026-04-15 ~ 2026-04-17)

- **v0.6.0**: `scope-drift` skill 추가.
- **v0.6.1**: `hooks.json` prompt-type 필드 수정, marketplace manifest 정리.
- **v0.6.2**: agent description 충돌 해소 (Codex dispatch collision in `/athanor:deep-plan`).
- **v0.6.3**: plugin.json `hooks` 필드 잔존 → `Duplicate hooks file detected` 회귀 fix.
- **v0.6.4**: validate-plugin gate 강화, duplicate-hooks path check 추가, live-load evidence enforce.

### Contract-first defense — v0.7.x (2026-04-17 ~ 2026-04-24)

- **v0.7.0**: 28-subtask `/athanor:work --team` 세션 (`2026-04-17-001`)으로 11개 contract 종결. CHANGELOG.md bootstrap (15개 historical tag), `scripts/check_release_ready.py`, 3개 regression fixture + pytest 도입, `/athanor:setup` self-audit Check #7–11 (vendoring-gate + regression invariants), `agents/cleaner.md` §Schema-Validation, `agents/learner.md` §On Release, `docs/DESIGN.md` §Agent Registration.
- **v0.7.1**: PR #3 adversarial-review follow-up. `check_a_evidence`를 `## v<version>` anchor 기반 word-boundary regex로 강화, `scripts/gates/manifest_checks.py` 모듈로 hook 게이트 일원화 (3-way duplicate path 통합), `Path.resolve()`로 cross-platform 통일.
- **v0.7.2**: Stop hook을 material-claim 트리거로 narrow. analysis/planning/research Q&A turn에서의 user-fatigue 제거. `fixture_narrowed_stop_prompt.json` + `test_current_hooks_contains_narrowed_gating_markers` 회귀 추가.
- **v0.7.6 (2026-05-02)**: 5-agent ref deep-dive + Codex cross-validation. 최우선 contract-default `athanor.json` 파일 신설. `agents/reviewer.md` confidence-anchored review findings (CE persona reviewer pattern).
- **v0.7.7 (2026-05-18)**: Truth-in-documentation release. Stop hook 라벨을 `enforced` → `advisory (prompt-based)`로 정직하게 demote, schema/template/config `_doc` 거짓 claim 시정, `schemas/athanor-config.schema.json` (draft-07) 신설 + `$schema` URL을 release tag pin, `templates/athanor.json` 추출 + setup이 읽도록 변경, 6개 session-touching skill을 CLAUDE.md §Session Lookup Convention canonical rule로 정렬, `plan/SKILL.md` Step 3/4 intro tier-aware 재작성, `plan/discuss` skill에 `codex.enabled` + `codex.fallback` matrix 도입. 41 regression test 추가. PR #10 dual review (Opus + Codex)로 `_doc` 거짓 claim 잔존 catch + commit 6fdbd05로 시정.
- **v0.7.8 (2026-05-18)**: 스파이크-약속 enforcement upgrade. Stop hook이 `type: prompt` → `type: command`로 전환, `scripts/hooks/stop_verify_claims.py`가 stdin payload를 읽어 material-claim detection 수행 (English + Korean whitelist v0.7.7 prompt에서 verbatim 포팅) + exit 2로 Stop 차단, stderr가 모델 컨텍스트로 피드백. `verification-before-completion` skill에 §Emission Sentinel 추가 (`<!-- athanor:verification-emission v=1 -->` 응답 prefix로 hook이 re-entry 방지). `hooks.profile`의 `off`/`standard` 값만 honoured (`lenient`/`strict`는 deferred), `hooks.disabled[]` orphan 키 삭제. CLAUDE.md 라벨 `advisory (prompt-based)` → `enforced (command-based)`로 재승급. PR #10 dual-review에서 catch한 Major 4건 (Step 2 tier prose, Deep-tier 2-input Critic, /work review-skipped marker, analyze:301 today residual) 함께 처리.

## Live invariants (현 시점 contract status)

| Contract | 상태 | 보호 위치 |
|---|---|---|
| `stop-hook-command-contract` | ✅ enforced (v0.7.8 — runtime gate via `type: command` + exit 2) | `tests/test_regression_stop_command_hook.py` (registration) + `tests/test_regression_stop_hook_script.py` (decision flow) |
| `hook-uniqueness` | ✅ enforced | `tests/test_regression_hook_uniqueness.py`, `scripts/gates/manifest_checks.py::hook_uniqueness_check` |
| `manifest-no-hooks-field` | ✅ enforced | `tests/test_regression_manifest_hooks.py`, `scripts/gates/manifest_checks.py::duplicate_hooks_path_check` |
| `check_a_evidence` (release-time) | ✅ enforced | `scripts/check_release_ready.py::check_a_evidence` (word-boundary regex) |
| `schema-validates-config` (v0.7.7) | ✅ enforced | `tests/test_regression_schema_validates_config.py` |
| `schema-url-version-pin` (v0.7.7) | ✅ enforced | `tests/test_regression_schema_url_version_pin.py` |
| `session-lookup-convention` (v0.7.7) | ✅ enforced | `tests/test_regression_session_lookup_convention.py` |
| `_doc-honesty` (v0.7.7+v0.7.8) | ✅ enforced | `tests/test_regression_doc_string_honesty.py` (models deprecated; hooks working contract) |
| `vendoring-gate` (T0+T1 disproof) | ⚠️ LLM-driven only | `/athanor:setup` Check #7. CI 자동 실행 안 됨 (개선 후보) |
| `contract-ledger` presence | ⚠️ user-install 환경에서 항상 fail | `/athanor:setup` Check #11. fresh-checkout 분기 필요 (개선 후보) |
| `learner-on-release` | ⚠️ contract만 있음 | `agents/learner.md` §On Release. 자동 트리거 없음 |
| `agent-frontmatter-consistency` | ❌ 회귀 0건 | v0.6.2 클래스 재발 시 잡지 못함 (개선 후보) |
| `stop-phrase-detection` | ❌ prose-only, enforce 없음 | CLAUDE.md §Defense Mechanisms (개선 후보) |
| `read-before-edit` | ❌ prose-only, enforce 없음 | CLAUDE.md §Defense Mechanisms (개선 후보) |

## Known gaps (다음 작업 후보)

- 신규 user 환경에서 `/athanor:setup` Check #11이 항상 빨간 X (`.athanor/sessions/`이 gitignored이므로 fresh checkout에 ledger 없음). `--ci` 모드처럼 user-install fresh 환경 분기 필요.
- Memory 2-tier (`permanent → mem-search`)이 디자인 문서에는 있으나 실제 구현은 frontmatter `importance` 마킹뿐 — mem-search MCP에 영구 저장하는 코드 부재.
- agent / skill frontmatter 회귀 테스트 부재 (v0.6.2 클래스 재발 시 잡지 못함).
- CI matrix는 ubuntu-latest 단일 — Windows-specific 회귀(case-insensitive FS 등) 자동 검증 부재.
- Stop hook이 모델 자기-식별에 100% 의존 (false-negative 위험). 외부 transcript-parser 마이그레이션 후보. **(2026-05-18 spike: PASS — 아래 §Command-hook Stop blocking spike 참조)**

## Command-hook Stop blocking spike (2026-05-18)

**Goal:** v0.7.8 plan(`.athanor/sessions/2026-05-18-001/plan.md` §SPIKE) prerequisite — empirically verify whether Claude Code runtime honors `type: "command"` Stop hooks with `exit 2` to block stop and feed stderr back to the model.

**Method:**
- Script: `scripts/hooks/stop_verify_claims.py` — no-op stub with one-shot exit 2 via `/tmp/athanor-spike-block.flag` + `/tmp/athanor-spike-done.flag` safety guard.
- Registered as parallel Stop hook in `~/.claude/settings.json` (NOT athanor plugin's hooks.json — current Claude Code session does not have athanor installed; user-global settings exercises the same runtime path).
- Logged every invocation to `/tmp/athanor-spike.log`.

**Result: PASS** — all four spike questions answered empirically:

| Q | Result | Evidence |
|---|---|---|
| Q1: Does `type: command` Stop hook execute? | ✅ YES | Log: `invoked event=Stop payload_bytes=554 argv=[...]` |
| Q2: Does exit 0 produce normal Stop? | ✅ YES | Phase A turn ended cleanly after PASSING entry |
| Q3: Does exit 2 block Stop? | ✅ YES | Phase B: user's intended message never reached model; instead Claude received system-formatted "Stop hook feedback" |
| Q4: Is stderr fed back as continuation context? | ✅ YES | Stderr appeared verbatim as `Stop hook feedback: [<command>]: <stderr text>` in model input |

**Empirical raw observation (Phase B):**

The next message after `exit 2` arrived at the model as:
```
Stop hook feedback:
[python3 /home/wook/work/06_athanor/scripts/hooks/stop_verify_claims.py]: athanor spike: blocking Stop to test command-hook gating semantics. This stderr message demonstrates whether type=command Stop hooks feed exit-2 stderr back to the model as continuation context.
```

The model recognized this as system feedback (not a user message) and continued processing in the same turn context. The user-facing UI showed no error.

**Timing observation (worth designing around):**

The log shows TWO Stop events that should have triggered exit 2 — first `14:26:31 PASSING` and then `14:27:04 BLOCKING`. The block flag was created via `touch` before the 14:26:31 Stop, yet only the 14:27:04 event detected it. Possible explanations:
1. The 14:26:31 event was M3's natural turn-end Stop fired before the next user message; the 14:27:04 event fired as a separate hook invocation (possibly pre-next-turn evaluation).
2. Filesystem sync race between `touch` from Bash tool's environment and the hook's `os.path.exists` from a possibly different working directory.

**Implication for v0.7.8 design:**
- Do NOT rely on `os.path.exists`-style transient state for gating decisions. Use the script's own evaluation of stdin payload (the hook event JSON), which is guaranteed-present.
- The v0.7.8 production script (`scripts/hooks/stop_verify_claims.py` v1) should parse `last_assistant_message` from stdin and decide entirely from message content + the M2 sentinel marker — NO filesystem flags.

**Cross-platform note:** Hook command was `python3 /home/wook/work/06_athanor/scripts/hooks/stop_verify_claims.py`. On Windows, `python3` may not be on PATH (`py -3` or `python` instead). v0.7.8 must use a portable invocation — proposal: shebang-less script + explicit `python` resolver in `hooks/hooks.json` per-platform OR a launcher shim.

**Decision:** v0.7.8 plan §SPIKE branch = **PASS path** (command hook with exit 2 enforcement, single-marker sentinel for re-entry, off/standard profiles only). M1 relabel in v0.7.7 references this spike with forward note: "v0.7.8 upgrades to enforced (command-based)."

**Cleanup performed:** hook removed from `~/.claude/settings.json`; `/tmp/athanor-spike*` files deleted. `scripts/hooks/stop_verify_claims.py` remains in repo as the v0.7.8 starting point (current state = no-op stub; will be extended in v0.7.8 PR with claim-classification + sentinel-detection logic).

## Phase 1 Checklist (historical, archived)

### 1.1 플러그인 로딩 검증 ✅
- [x] Claude Code에서 `--plugin-dir` 로 로딩 테스트
- [x] 5개 스킬이 `/athanor:` prefix로 표시 확인 (setup, discuss, analyze, plan, work)
- [x] plugin.json → .claude-plugin/plugin.json 이동 (Claude Code 규약)

### 1.2 Session 디렉토리 관리 ✅
- [x] `.athanor/sessions/` 자동 생성 로직 (setup SKILL.md에 구현)
- [x] 세션 ID 규칙: `YYYY-MM-DD-NNN`
- [x] 세션 디렉토리 템플릿 (discuss.md, analyze.md, plan.md, decisions.md, work-log.md, discoveries/)

### 1.3 Config 관리 ✅
- [x] athanor.json 로딩 로직 (setup worker가 처리)
- [x] 기본값 fallback (template에서 복사)

### 1.4 /athanor:setup 구현 ✅
- [x] Health check worker dispatch (thin leader 패턴)
- [x] 상태 테이블 출력 (6개 항목)
- [x] 트리거 언어 설정 (ko/en/both)

### 1.5 테스트 ✅
- [x] `/athanor:setup` 실행 → 동작 확인
- [x] Status table 정상 출력 확인
- [x] Agent Teams: ✓ enabled
- [x] LSP: ✓ available (built-in)
- [x] mem-search: 사용자 세션에서 검증 (MCP가 로드되어 있을 때)

### MCP 접근성 결론
- `-p` (non-interactive) 모드에서는 MCP 서버가 로드되지 않아 mem-search 미감지 가능
- 이는 테스트 환경 한계. 실제 사용자 세션에서는 MCP가 로드되어 있을 것
- fallback (.md 파일 통신)은 이미 설계에 포함되어 있음
