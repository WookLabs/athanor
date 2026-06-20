# STATE.md — Archived History

Older phase sections moved out of `docs/STATE.md` by the releaser bounded-history trim rule (CONVENTIONS §7 / releaser Step 3). Verbatim moves — no content loss.

## Archived from STATE.md (2026-06-06)

## Previous Phase: v0.15.0 — LFG Pipeline Contract Reconciliation (22-bug eradication)

**v0.15.0** (released 2026-05-28) — Full LFG pipeline contract
reconciliation eradicating 22 bugs (3 CRITICAL + 5 HIGH + 8 MEDIUM +
6 LOW) across `/athanor:lfg` and `/athanor:lfg-goal` skills, their
supporting schemas, agent definitions, and the Stop hook Korean path.

Key fixes:
- C1: No-progress circuit breaker moved inside `for cycle` loop (was dead
  code outside loop).
- C2: Aggregate status enum unified to 3-value across 4 files.
- C3: `cycle_phase` 7-value enum + resume semantics added to state-shape.
- H2/H3: Thin Leader violations in `/athanor:lfg` Steps 3 and 8 resolved
  via worker dispatch.
- M6: Korean position mapping bug in `stop_verify_claims.py` fixed
  (v0.14.2 EN fix extended to KO path).

Identity invariants intact (4): Thin Leader / cross-model adversarial /
Spec-then-TDD / Stop hook gate. Companion-fix arc 5 layer (v0.11.3 →
v0.11.8) untouched.

## Previous Phase: v0.14.3 — Documentation/Version Hygiene Patch

**v0.14.3** (released 2026-05-26) — Documentation and version hygiene
patch closing 3 findings from the v0.14.0 honesty-arc audit:

- G4: 5-file version manifest drift (stuck at 0.14.0 through v0.14.2)
  bumped atomically to 0.14.3.
- G5: CHANGELOG v0.14.0 test count overclaim corrected (20 -> 9, 7 -> 3).
- G6: Agent definition honesty framing clarified — codex-dispatcher has
  existing inline implementation; releaser + ci-watcher are reference-only.

Identity invariants intact (4): Thin Leader / cross-model adversarial /
Spec-then-TDD / Stop hook gate. Companion-fix arc 5 layer (v0.11.3 →
v0.11.8) untouched.

## Previous Phase: v0.14.2 — Infrastructure Bug Fix Patch

**v0.14.2** (released 2026-05-26) — Infrastructure bug fix patch:
`check_release_ready.py` version source fix (read from plugin.json not
athanor.json), CHANGELOG heading format fix (bracket vs bare), and
namespace layout test import fix. 4 identity invariants intact.

## Previous Phase: v0.14.0 — Native Agent Definitions

**v0.14.0 — Native Agent Definitions** (released 2026-05-24)

3 new native agent definition files added to `agents/`:
- `agents/releaser.md` — Release ceremony automation
- `agents/codex-dispatcher.md` — Codex CLI dispatch wrapper with timeout
  clamping and stdin redirect
- `agents/ci-watcher.md` — CI watch + autofix loop

Agent definitions are REFERENCE DOCUMENTS — they describe purpose, tools,
and dispatch contract but are NOT full implementations. The inline codex
invocation, CI loop, and release ceremony patterns remain in their
respective skills as canonical code.

Identity invariants intact (4): Thin Leader / cross-model adversarial /
Spec-then-TDD / Stop hook gate. Companion-fix arc 5 layer (v0.11.3 →
v0.11.8) untouched. `fallbackAfterMs` (soft deadline) deferred to v0.15+.
Codex dispatcher extraction (v0.13.2 Plan B) realized as agent reference
definition; full extraction deferred to v0.15+.

## Previous Phase: v0.13.2 — Bug Fix Patch (Phantom Variable + Korean Regex + Schema Max)

**v0.13.2** (released 2026-05-24) — Bug fix patch: `${CODEX_TIMEOUT_S}`
phantom variable fix (Worker clean-context Agent() dispatch has no access
to Leader shell variables; inline jq computation instead), Korean
paraphrase regex suffix mismatch fix, `codex.timeoutMs` schema maximum
(600000) addition. 4 identity invariants intact, companion-fix arc
untouched. "Worker prompts must not depend on Leader shell variables"
convention discovered.

## Previous Phase: v0.13.1 — Codex CLI Hang Prevention Patch

**v0.13.1 — Codex CLI Hang Prevention Patch** (released 2026-05-23)

Operational hardening patch closing user-reported `/athanor:deep-plan`
hangs. Root cause (GitHub codex#20919): `codex exec` `readFileSync(0)`
blocking stdin read in non-TTY Bash dispatch environments.

Fixes (5):
1. `< /dev/null` redirect on all codex invocations + probes
2. `--full-auto` → top-level `-a never -s workspace-write` migration
   (deprecated/removed in CLI 0.133.0)
3. Shell-level `timeout 300s` prefix as primary wall-clock fence
4. `codex.timeoutMs` config key + Step 0 probe wiring
5. 11-test regression file + 2 lock-step existing-test updates +
   3-doc stale reference migration

Identity invariants intact (4): Thin Leader / cross-model adversarial /
Spec-then-TDD / Stop hook gate. Companion-fix arc 5 layer (v0.11.3 →
v0.11.8) untouched. `fallbackAfterMs` (soft deadline) deferred to v0.15+.

## Previous Phase: v0.13.0 — /athanor:lfg-goal (Goal-Driven Validated Ralph Loop)

v0.13.0은 goal-driven Ralph loop orchestrator `/athanor:lfg-goal`을 도입한다.
사용자 의도를 durable goal ledger로 고정하고, 매 cycle마다 별도 worker가
"실제로 receipt가 떨어졌는지"를 검증한 뒤, goal-completion 판정을 세 단계
adversarial check로 통과시키는 흐름이다. v0.11.0 `/athanor:lfg` wrapper와는
다른 축 — lfg는 plan→work→review 파이프라인 엮기, lfg-goal은 goal-state
컨버전스 루프.

### Three-layer architecture (three-layer goal-driven loop)

1. **Durable goal ledger** at `.athanor/goals/<id>/goal.md` — 사용자 의도가
   세션 휘발성에 빠지지 않도록 별도 디렉토리에 기록한다.
   `.athanor/sessions/<id>/`(per-session) 과 분리된 cross-session 영속
   레이어. 각 ledger entry는 goal text + acceptance criteria + cycle ledger
   (receipt-validator 결과 timeline) 를 포함한다.
2. **Dispatched receipt-validator worker** — 매 cycle 종료 시 clean-context
   worker가 dispatch 되어 cycle artifact (work-log.md, git diff, test
   evidence)를 읽고 "이 cycle이 실제로 약속한 것을 만들었는가" 를 판정한다.
   Leader 자신이 검증하지 않는다 (Thin Leader 유지) — 별도 worker가 evidence
   shape + 실재성을 본다.
3. **Adversarial 3-tier goal-completion check** — goal 전체가 닫혔는지 판정
   할 때 세 단계 게이트: (a) mechanical (acceptance criteria의 grep-able /
   command-runnable 조건이 통과), (b) cross-model judge (Codex가 goal text +
   final state를 보고 closure 판정 — `/athanor:plan` 의 cross-model 패턴
   재사용), (c) user ratification (최종 사용자 confirm). 셋 중 하나라도
   fail이면 다음 cycle로 ralph-loop 계속.

### 4 athanor identity invariants preserved

D11에 따라 lfg-goal은 새 identity invariant를 추가하지 않는다. 기존 네 축
위에 놓이는 orchestration layer:

- **Thin Leader**: lfg-goal leader는 goal ledger 관리 + cycle dispatch만
  한다. 실제 plan / work / receipt 검증은 모두 clean-context worker에서.
- **Cross-model adversarial planning**: 각 cycle의 plan 단계는 기존
  `/athanor:plan` (Planner A Claude + Planner B Codex + Critic) 을 그대로
  호출한다. Layer 3-(b) goal-closure judge 역시 동일 cross-model 패턴.
- **Spec-then-TDD discipline**: 각 cycle의 work 단계는 `/athanor:work` 의
  Splitter execution_note + conjunction-of-three Phase 3 gate를 그대로
  거친다. lfg-goal은 그 위에서 cycle을 묶을 뿐.
- **Stop hook runtime gate**: 매 cycle의 worker turn은 기존 Stop hook
  (`scripts/hooks/stop_verify_claims.py`) 의 material-claim verification을
  통과해야 한다. v0.11.3 input-layer + v0.11.4 plugin-root + v0.11.6 sentinel
  body-hash binding + v0.11.7 scanner extension 5-layer companion-fix arc
  그대로.

### User decisions (session `.athanor/sessions/2026-05-22-002/`)

- **D8 — maxIterations=5 default.** Ralph loop는 무한이 아니다. 기본 5
  cycle에서 goal-closure가 안 닫히면 leader가 사용자에게 escalate
  ("5 cycle 돌렸는데 closure 못 받았습니다 — 계속/중단/goal 수정 중 선택").
  config override 가능 (`athanor.json` `lfgGoal.maxIterations`).
- **D9 — consolidateCycles=false (per-cycle release default).** 매 cycle이
  독립적인 commit/release 단위로 닫힌다. 여러 cycle을 한 changeset으로
  묶지 않는다 — Stop hook 게이트와 Spec-then-TDD evidence가 cycle 단위로
  떨어지도록 강제. opt-in으로 cycle 묶기는 가능하나 기본 off.
- **D10 — dual invocation surface.** 두 방식으로 호출:
  (1) inline goal text → leader가 auto-id (`YYYY-MM-DD-NNN` 패턴) 부여 후
  `.athanor/goals/<id>/goal.md` 생성;
  (2) `--goal-file <path>` → 사전 작성된 goal ledger 재사용 (이전 lfg-goal
  세션 이어가기 또는 외부에서 작성한 goal 가져오기).

### Honesty boundary

본 메커니즘은 advisory + orchestration. runtime 강제는 기존 Stop hook
(material-claim verification) + Spec-then-TDD Phase 3 gate가 그대로 담당
하며, lfg-goal 레이어 자체는 새 runtime guard를 추가하지 않는다. Layer 2
receipt-validator의 "실재성" 검증은 evidence shape 검증 (command /
test_node_id / exit_code / output_tail) 까지만 — adversarial forgery
(worker가 evidence를 fabricate) 차단은 본 릴리스 범위 밖. Layer 3-(b)
cross-model judge는 Codex 호출이 unavailable / disabled 일 때 fail-open
(closure를 자동 grant하지 않고 사용자에게 fallback escalate) 로 운용한다.

세션 참조: `.athanor/sessions/2026-05-22-002/` (계획 + decisions D1~D14 기록;
deep-tier: Claude Planner A + Codex Planner B + cross-review + Critic
synthesis).

### v0.13.0 ship surface

- 15 subtasks shipped via `/athanor:work` Splitter (Plan B Phase 4 dropped
  per D2; Subtasks 1-15 covering goal ledger spec + receipt-validator
  worker template + Tier 1/2/3 check + config block + schema + skill body
  + CHANGELOG/STATE.md release entries + version bump).
- Tests: **501 passed + 3 skipped + 1 xpassed** (479 v0.12.0 baseline + 22
  신규 v0.13.0 regression tests across 3 files —
  `tests/test_regression_v013_lfg_goal_*.py`).
- Active executable contracts (v0.13.0 신규):
  `v013-lfg-goal-skill-surface`,
  `v013-lfg-goal-receipt-contract`,
  `v013-lfg-goal-config-validation`.
- 4 athanor identity invariants 무손상 보존 — lfg-goal은 orchestration
  layer, 새 identity invariant 추가 안 함 (D11).
- Companion-fix arc 5-layer closure (v0.11.3 ~ v0.11.7) 그대로 통과 —
  Stop hook script + sentinel body-hash binding + scanner extension +
  B1 minimal detection 모두 v0.13.0 ship에서 unchanged.

## Previous Phase: v0.12.0 — Concept Absorption Pivot

v0.12.0 atomically removes 45 vendored skills (5 LIFT-source + 40 DROP) and 47
vendored CE sub-agents under the `/athanor:ce-*` and `/athanor:sp-*` namespaces.
Direct attribution per D7: **v0.10.0 plan-of-record misread the user's
concept-absorption intent as wholesale plugin vendoring.** The cutover lands
the scope correction in one atomic release after the v0.11.8 deprecation
warning cycle.

Per the v0.12.0 plan (`docs/plans/2026-05-22-001-feat-v0.12.0-concept-kernel-cutover-plan-b.md`)
and decisions D1, D7, D8, D9, D10, D11, D12 (`.athanor/sessions/2026-05-22-001/decisions.md`),
the cutover does the following:

- **5 LIFT** — concepts absorbed into athanor-native skills as prose subsections
  (NOT vendored directories): review personas (`ce-code-review` → `skills/review/SKILL.md`),
  doc-review mode (`ce-doc-review` → `skills/review/SKILL.md` §"Doc review mode"),
  systematic debugging Iron Law + Four Phases (`sp-systematic-debugging` →
  `skills/debug/SKILL.md` §"Systematic Debugging Discipline"), requirements
  capture R/A/F/AE-IDs (`ce-brainstorm` → `skills/discuss/references/requirements-capture.md`),
  skill-discovery preamble (`sp-using-superpowers` → CLAUDE.md §"using-superpowers
  boundary (v0.11.1)"). Each concept enumerated in NOTICE.md §"Concepts adopted
  from upstream" with MIT attribution preserved.
- **1 KEEP** (D8) — `/athanor:ce-test-browser` retained as user opt-in browser
  automation (non-identity but real utility); T2 provenance block preserved.
- **2 KEEP sub-agents** (D12) — `ce-git-history-analyzer` + `ce-repo-research-analyst`
  retained as generic discovery dispatch targets at `agents/vendored/ce/`.
- **Surface reduction: 95 → 3 (97%)** — from 33 ce-* + 13 sp-* + 49 sub-agents
  (95 items) down to 1 KEEP skill + 2 KEEP sub-agents (3 items).
- **45 removed skill directories** + **47 removed sub-agents** + 1 ledger archive
  + 1 architecture doc + 1 user-facing migration guide
  (`docs/v0.12.0-migration.md`) shipped together as the atomic cut.

### Companion-fix arc 5-layer closure intact across the pivot

v0.11.3 (script wrong) → v0.11.4 (path wrong) → v0.11.5 (CLAUDE.md doc drift) →
v0.11.6 (sentinel body-hash binding) → v0.11.7 (scanner extension + Residual
reclassification + B1 minimal) is preserved by v0.12.0. Stop hook script
(`scripts/hooks/stop_verify_claims.py`) + all v0.11.3 ~ v0.11.7 regression
tests + Spec-then-TDD discipline + cross-model `/athanor:plan` + Stop hook
runtime gate (D10) — every athanor identity invariant survives the cutover.

### v0.12.0 ship surface

- Skills: 10 athanor-native + 1 KEEP vendored (`ce-test-browser`) + 2 internal
  vendored (`scope-drift`, `verification-before-completion`) = **13 surviving**
  skills total (down from 58 at v0.11.7).
- Sub-agents: 2 retained at `agents/vendored/ce/` (down from 49).
- pytest test count: **473 passed + 3 skipped + 2 xfailed + 5 xpassed** at
  v0.12.0 baseline (with Phase 6 prose updates landed). All companion-fix arc
  regression tests + v0.12.0 invariant tests green.
- Honesty arc — D7 voice discipline: "plan-of-record misread" verbatim;
  the four forbidden softening phrases enumerated in D7 are absent from
  the new v0.12.0 content (voice-safety greps land green in CI).

Full retrospective: `docs/archive/v010-v011-vendoring-scope-correction.md`.

## Previous Phase: v0.11.8 — Deprecation Warning Cycle (Scope-Correction Prep)

v0.11.8은 v0.12.0 atomic scope-correction cut에 앞서 deprecation preamble을
45개 vendored SKILL.md (5 LIFT + 40 DROP)에 ship한다. 기능 변경 없음 —
사용자가 `/athanor:ce-*` 또는 `/athanor:sp-*` skill을 호출하면 in-skill
⚠ DEPRECATION 안내 (migration target 또는 "no athanor-native migration"
라벨)를 본다. D8 결정에 따라 `ce-test-browser`는 KEEP carve-out으로
preamble 미적용.

`docs/plans/2026-05-22-001-feat-v0.12.0-concept-kernel-cutover-plan-b.md`
의 18개 subtask 중 본 release (Subtasks 1-7)는 deprecation 인프라 + 회귀
잠금 + Stop hook + drift carve-out + version bump을 ship; Subtasks 8-20은
v0.12.0 atomic cut으로 이월 (concept LIFT + 45 directory 제거 + NOTICE
재구성 + marketplace.json 재설명).

### Companion-fix arc 5-layer closure intact

v0.11.3 (script wrong) → v0.11.4 (path wrong) → v0.11.5 (CLAUDE.md doc drift)
→ v0.11.6 (sentinel body-hash binding) → v0.11.7 (scanner extension +
Residual reclassification + B1 minimal) 의 5-layer 회로는 v0.11.8 pivot이
건드리지 않는다. Stop hook script (`scripts/hooks/stop_verify_claims.py`) +
regression suite 46개 + Spec-then-TDD discipline + cross-model
`/athanor:plan` 모두 보존; scope-correction은 vendored surface에만 적용.

### Stop hook + drift carve-outs

- `scripts/hooks/stop_verify_claims.py` — deprecation sentinel
  (`<!-- athanor:deprecated v=1 since=0.11.8 removal=0.12.0 -->`) early-return
  carve-out 추가. v=2 sentinel check 뒤, material-claim detection 앞에 위치;
  hit 시 counter reset. v=2 sentinel handling, v0.11.3 transcript_path parser,
  v0.11.6 body-hash normalization, v0.11.7 B1 mutation detection 모두
  무손상 보존.
- `scripts/check_vendor_drift.py` — `_strip_deprecation_block`
  (`_strip_provenance_block` mirror) 추가; `_diff_skill`에 wired. 4-line
  preamble이 upstream drift로 잡히지 않도록 잠금.

### v0.11.8 ship surface

- 45 preamble injected (5 LIFT class + 40 DROP class; 1 KEEP carve-out =
  `ce-test-browser` per D8).
- Tests: **465 passed + 1 skipped + 1 xpassed** (453 v0.11.7 baseline + 12
  신규 v0.11.8 deprecation preamble regression tests).
- Active executable contracts (v0.11.8 신규):
  `v011-8-deprecation-preamble-shape`,
  `v011-8-deprecation-preamble-idempotency`,
  `v011-8-stop-hook-deprecation-carve-out`,
  `v011-8-vendor-drift-deprecation-carve-out`.

### Forward — v0.12.0 atomic cut

v0.12.0 ships the cut from session `2026-05-22-001` Subtasks 8-20:

- Concept LIFT (review personas, debug discipline, requirements-capture,
  skill-discovery preamble) into athanor-native skills
- 40 DROP-class directory removal + 5 LIFT-class source removal post-merge
- 49 sub-agents at `agents/vendored/ce/` 및 superpowers 잔여 정리
- NOTICE.md attribution 재구성 (interpretive citation 모드로 전환)
- `marketplace.json` description 재작성 (concept-absorption shape)
- 5-file version bump 0.11.8 → 0.12.0

## Previous Phase: v0.11.7 (Doc-drift scanner extension + Residual reclassification + minimal B1 — companion-fix arc 5th layer)

v0.11.5는 CLAUDE.md drift-class 회귀 infrastructure를 ship했지만 scanner
가 Markdown narrative에만 적용. Python docstring (특히
`scripts/hooks/stop_verify_claims.py`) + `docs/STATE.md`은 같은 prose-vs-
code drift pattern을 들고 있었지만 v0.11.5 그물 밖. v0.11.7은 scanner를
`ast.get_docstring` + per-file extractor로 확장, hook docstring과
STATE.md의 stale version pin을 audit, B2/B5 stale pin closure + B6
broken-promise reclassification 적용 + Codex Reviewer push에 따라 minimal
B1 (profile mutation) 탐지 layer까지 같은 릴리스에 포함. 결과: 8+ release
cycle 동안 "documented but not guarded" 상태였던 honesty residual에
최초의 closure layer가 들어감.

6 ~ 11+ release cycle 동안 `scripts/hooks/stop_verify_claims.py` Residual
block + CLAUDE.md §Known residuals에 익명 "candidate"로 carry되던 4건
(B1 profile mutation, B2 stale pin, B5 stale label, B6 broken-promise
phrasing)이 v0.11.6 reclassification 패턴을 적용받아 명시 Severity /
Target / Acceptance 라벨로 정직성 회복. B1은 특히 "not guarded" 라벨로만
이어지던 것에 minimal detection을 ship해서 자기-위반 한 겹 closure.

### Companion-fix arc 5 layers

| Layer | Release | Bug |
|---|---|---|
| 1. Runtime stdin parser shape | v0.11.3 | script wrong (last_assistant_message vs transcript_path) |
| 2. Hook command path resolution | v0.11.4 | path wrong (relative vs ${CLAUDE_PLUGIN_ROOT}) |
| 3. CLAUDE.md doc drift class | v0.11.5 | Markdown untestable claims |
| 4. Sentinel body-hash binding | v0.11.6 | trailing-whitespace round-trip mismatch |
| **5. Scanner extension + Residual reclassification + B1 minimal** | **v0.11.7** | **Python docstrings + STATE.md outside scanner; documented bugs carried as anonymous "candidates"; profile mutation undetected** |

Shared meta-cause 지속: documentation surface가 test coverage보다 빠르게
drift; "Residual known limitations" block은 hold-everything bin이 되어
v0.11.6 reclassification 패턴을 더 광범위하게 적용해야 했음. v0.11.7은
각 entry를 ship 가능한 intent로 라벨링해서 bin을 정리.

### v0.11.7 ship surface

- 7 subtask shipped, 6 honesty-arc closure (B2/B5/B6 stale-or-broken
  phrasing + Residual reclassification with explicit Severity / Target
  / Acceptance + B1 minimal detection ship + xfail marker cleanup).
- Tests: **453 passed + 1 skipped + 1 xpassed** (Case #19은 v0.11.3
  pre-existing xfail-tolerant; 산문 voice safety 28 forbidden-phrase
  패턴 → 0 hit).
- Active executable contracts (v0.11.7 신규):
  `v011-7-doc-drift-scanner-python-docstrings`,
  `v011-7-import-path-invariants`,
  `v011-7-profile-mutation-detection`,
  `v011-7-residual-reclassification`.

### v0.11.8+ deferred

- **B1 full architectural treatment** — snapshot / cache / lock +
  legitimate cross-session edit handling. v0.11.7는 detection-only.
- **B3 full T2 navigation pattern** — clickable reference repair across
  the vendored corpus. v0.11.7은 minimal honest message만 ship.
- **B4 `_content_to_text` no-separator 실증 조사** — v0.11.3 helper의
  separator-less join 동작은 문서화되었지만 fuzz / adversarial 테스트
  부재.
- LOW-7 tag gap v0.7.7 → v0.11.1 backfill (release archaeology)
- LOW-8 detection coverage via transcript_path (35+ legacy tests
  parameterization)
- Bolder: CLAUDE.md generate-from-manifests architecture (Codex
  Reviewer 제안, v0.11.5 / v0.11.6 / v0.11.7 carry)

## Previous Phase: v0.11.6 (Sentinel body-hash binding fix — companion-fix arc 4th layer)

v=2 sentinel protocol (도입 v0.7.9)의 hash-binding round-trip이 처음부터
broken이었음. `sentinel_helper.py emit`은 stdin 받은 body를 그대로 hash
하지만 (typically heredoc trailing `\n` 포함, e.g. 1744 bytes), Claude
Code transcript는 모델 응답에서 trailing whitespace를 strip해서 저장
(1743 bytes). `stop_verify_claims.py validate_emission_sentinel()`이
transcript에서 추출한 body를 hash → exact 1-byte 차이로 mismatch →
sentinel always rejected → verification skill 호출이 production에서
실제로 작동한 적 없음.

11+ release cycle (v0.7.9 → v0.11.5) 동안 `Residual known limitations`
docstring에 originally "v0.11.0+ candidate"로 carry — 그 분류 자체가
honesty-arc 위반이었음 (documented bug를 "enhancement candidate"로 mask).
reclassified v0.11.7 as documented bug — closure 추적은 stop_verify_claims.py
Residual table 참고. v0.11.6은 기술 버그 + 분류 drift 둘 다 closure.

### Companion-fix arc 4 layers

| Layer | Release | Bug |
|---|---|---|
| 1. Runtime stdin parser shape | v0.11.3 | script wrong (last_assistant_message vs transcript_path) |
| 2. Hook command path resolution | v0.11.4 | path wrong (relative vs ${CLAUDE_PLUGIN_ROOT}) |
| 3. CLAUDE.md doc drift class | v0.11.5 | doc untestable claims |
| **4. Sentinel body-hash binding** | **v0.11.6** | **trailing-whitespace round-trip mismatch** |

Shared meta-cause: source-repo-only manual testing이 각 layer를 동시에
가려둠. v0.11.6은 추가로 meta-bug도 노출 — "documented known limitation"
이라는 분류가 honest bug를 책임에서 가릴 수 있다는 점.

### v0.11.6 fix

- `scripts/hooks/sentinel_helper.py emit()` (line 64): `body.encode(...)`
  → `body.strip().encode(...)`. 1-line.
- `scripts/hooks/stop_verify_claims.py validate_emission_sentinel()`
  (line 861): `body_canonical = body_after.lstrip("\n")` →
  `body_canonical = body_after.strip()`. Symmetric normalization.
- 5 신규 regression test in
  `tests/test_regression_v011_6_sentinel_body_normalization.py`:
  RED-first repro (trailing + leading newline mismatch) +
  byte-identical baseline + content-forgery rejection (security boundary
  preserved) + helper-script normalization consistency unit test.
  All 5 PASS after fix.

### v0.11.6 ship surface

- Tests: **428 passed + 4 xpassed** (423 v0.11.5 baseline + 5 new
  v0.11.6 sentinel normalization tests).
- Voice safety: 28 forbidden-phrase patterns → 0 hits.
- Active executable contracts (v0.11.6 new):
  `v011-6-sentinel-body-normalization-round-trip`,
  `v011-6-content-forgery-still-rejected`.

### v0.11.7+ deferred

- LOW-7 tag gap v0.7.7 → v0.11.1 backfill (release archaeology)
- LOW-8 detection coverage via transcript_path (35+ legacy tests
  parameterization)
- MEDIUM-4 dangling `/ce-setup` references (T2 navigation)
- Bolder: CLAUDE.md generate-from-manifests architecture
- Audit `Residual known limitations` block for other documented-but-
  unfixed entries (apply v0.11.6 reclassification pattern)

## Previous Phase: v0.11.5 (Documentation honesty hardening — CLAUDE.md drift closure)

v0.11.3 + v0.11.4 runtime closure에 이어진 documentation-layer companion.
v0.11.3은 Stop hook script 입력 파싱 (input-layer)을 정상화했고, v0.11.4는
배포 경로 (`${CLAUDE_PLUGIN_ROOT}` expansion)를 정상화했다. v0.11.5은 5
release cycle 동안 runtime bug를 가려둔 *documentation drift class*를 산문
레벨에서 닫는다. CLAUDE.md가 test로 enforce되지 않는 truth claim을 누적
하고 있었음 — "37 CE skills" (v0.11.2 scope-clarification cut 이후 실제 33),
"SessionStart 자동 로드" (athanor `hooks/hooks.json`은 Stop event만 등록;
SessionStart skill loading은 Claude Code platform 메커니즘), "v=1 sentinel"
(production은 v0.7.9부터 v=2 nonce-bound 사용). v0.11.5은 2-layer scanner
+ historical-context exemption 기반 drift-class regression test
infrastructure를 ship — 다음 8 release cycle 동안 같은 prose-vs-code gap
이 누적되지 않도록 잠근다.

Source: cross-model cutting-prep deep analysis 2026-05-20-002 (Researcher A
Claude + Devil's Advocate Codex + Critic synthesis)가 origin이었고, v0.11.5
이행은 2026-05-21 analyze 세션이 docs/STATE.md §"May 21, 2026" 항목에
연결됨.

- **U1**: CLAUDE.md CE-count drift 3건 (lines 35, 113, 319) "37" → "33".
  Historical / attributed references (예: "absorbed compound-engineering
  v3.8.3 (37 skills)" chronological artifact) 보존.
- **U2**: README.md CE-count drift 2건 (lines 8, 12) + dependent
  arithmetic "50 vendored skills" → "46" (33 ce-* + 13 sp-*).
- **U3**: CLAUDE.md SessionStart fiction (line 113) — 실제 hook 등록
  현황과 일치하도록 산문 교정. v=1 sentinel doc lag (lines 144, 161) 도
  v=2 nonce-bound로 교정 (`SENTINEL_PATTERN` 일치).
- **U4**: `tests/test_regression_v011_5_claude_md_invariants.py` 신설 —
  4 invariant test (Layer A narrow current-state matcher + Layer B
  claim-verb broad scan + `HISTORICAL_MARKERS` left-context filter).
  drift class going forward 잠금. `scripts/hooks/__init__.py` 빈 패키지
  marker도 함께 ship (LOW-6 latent import-path trap closure).
- **U5**: lfg ghost MEDIUM-5 closure — `NATIVE_THIN_LEADER_SKILLS` tuple
  9 → 10 (lfg 알파벳 위치). `skills/lfg/SKILL.md`에 v0.11.1 boundary
  preamble subsection 추가. CLAUDE.md boundary row enumeration 동기화.
- **U6**: version bump 0.11.4 → 0.11.5; CHANGELOG; STATE.md.

honesty arc — v0.11.5은 v0.11.3 / v0.11.4를 supersede / retract하지 않음.
companion-fix arc 계속: runtime gate restored (v0.11.3 input + v0.11.4
path) + drift class closed (v0.11.5 prose level).

### v0.11.5 ship surface

- 사용자-호출 skills: **62개** (변동 없음).
- Regression test suite: **423 passed + 4 xpassed** (v0.11.5 신규
  invariants + 기존 xfail-tolerant 4건).
- Drift-class regression test infrastructure ship — v0.11.7 scanner
  extension의 precursor.
- Active executable contracts (v0.11.5 신규):
  `v011-5-claude-md-ce-count-invariant`,
  `v011-5-claude-md-hook-event-invariant`,
  `v011-5-claude-md-sentinel-version-invariant`,
  `v011-5-historical-marker-exemption-filter`.

### v0.11.5 알려진 residual (v0.11.6+ 후보 → v0.11.6 / v0.11.7에서 일부 closure)

- MEDIUM-4: dangling `/ce-setup` references in 3 vendored skills
  (v0.11.7 B3 minimal closure 적용)
- LOW-7 tag gap v0.7.7 → v0.11.1 backfill (release archaeology — 잔류)
- LOW-8 detection coverage via transcript_path (잔류)
- xfail marker cleanup (v0.11.7 closure 적용)

## Previous Phase: v0.11.4 (Stop hook plugin-root path fix — deployment-path closure)

v0.11.3 input-layer fix delivered the correct script behavior but the
script was only REACHABLE inside athanor's own source repo. `hooks/
hooks.json` registered the Stop hook command with a bare relative path
(`python3 scripts/hooks/stop_verify_claims.py`) which Claude Code
resolves relative to the user's PROJECT cwd — not the plugin install
dir. From v0.7.8 (script introduction) through v0.11.3 (input-layer
fix), every project EXCEPT athanor's source repo silently lost the
gate (CC treats the "file not found" exit as "hook missing" /
non-blocking). v0.11.4 closes the deployment-path arc by switching to
`${CLAUDE_PLUGIN_ROOT}` env var expansion — the industry pattern used
by superpowers, claude-mem, openai-codex plugin hooks.

- **U1**: `hooks/hooks.json` command updated from bare relative path
  to `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/hooks/stop_verify_claims.py"`.
  `tests/test_regression_stop_command_hook.py` extended with new test
  `test_stop_hook_command_uses_plugin_root_or_absolute_path` locking
  the invariant (Reviewer revision 1: strip leading quote before
  absolute-path heuristic via `cmd.lstrip("\"'")`).
- **U2**: CLAUDE.md status-table cell pointer + new §"Stop hook v0.11.4
  plugin-root deployment fix (post-mortem)" subsection chronologically
  after v0.11.3 post-mortem; retroactively annotated v0.11.3 post-mortem
  block with "scope: source-repo only until v0.11.4 plugin-root fix"
  footnote in both CLAUDE.md and `scripts/hooks/stop_verify_claims.py`
  docstring; CLAUDE.md line ~206 Hook config reference updated to
  mention `${CLAUDE_PLUGIN_ROOT}`.
- **U3**: docs/STATE.md Current Phase shift.
- **U4**: CHANGELOG v0.11.4 entry + 5-file version bump 0.11.3 → 0.11.4
  (2 plugin/marketplace version fields + 3 URL pins v0.11.3 → v0.11.4).

honesty arc — v0.11.3 + v0.11.4 are **companion-fixes of one latent
bug arc**: script wrong (closed v0.11.3) + path wrong (closed v0.11.4).
Shared meta-cause — manual testing only inside athanor's source repo
hid both bugs simultaneously. No supersession framing; the v0.11.3
post-mortem is retroactively annotated, not retracted.

### v0.11.4 ship surface

- Tests: **422 passed + 1 xpassed** (421 v0.11.3 baseline + 1 new
  Subtask 1 regression test).
- Active executable contracts (v0.11.4 new):
  `v011-4-stop-hook-command-uses-plugin-root-or-absolute-path`.

### v0.11.4 deferred (carry forward — v0.11.5+)

- 8 analyze.md bugs from session 2026-05-21-001 (CLAUDE.md "37" stale,
  SessionStart fiction, v=1 doc lag, dangling /ce-setup, lfg ghost,
  scripts/hooks/__init__.py, tag gap, detection coverage). Plan
  preserved at `.athanor/sessions/2026-05-21-002/plan-a-v011_5-carry.md`.
- A5 / sec-001 / sec-003 / profile-mutation guard — carry from earlier.

## Previous Phase: v0.11.3 (Stop hook input-layer fix — honesty arc restoration)

5 release cycles (v0.7.8 → v0.11.2) 동안 Stop hook의 `**enforced (command-based)**`
라벨이 산문상 정직했지만 production 입력 파싱 경로가 실제 Claude Code 페이로드
모양을 처리하지 못해 매 Stop 이벤트가 silently fail-open 상태였다. v0.11.3은
입력 계층 격차를 닫아 v0.7.9 / v0.10.2 / v0.10.3에서 출하된 탐지 코드가 비로소
production에서 실제로 실행되도록 한다. 정체성 약속 (Thin Leader / cross-model
plan / Spec-then-TDD / Stop hook scope) 변경 없음. self-violation acknowledged
and corrected.

- **U1**: `scripts/hooks/stop_verify_claims.py`에 `_content_to_text()` +
  `_read_last_assistant_message()` 헬퍼 추가. legacy-first early return
  (`payload["last_assistant_message"]` 즉시 반환 — 기존 35+ 테스트 backwards-
  compat lock 보존) + `transcript_path` JSONL reverse-scan + `isSidechain
  != true` 필터 (sub-agent turn skip) + `stop_hook_active` pass-through.
  v0.7.9 hook_state circuit breaker 재진입 의미 변경 없음.
- **U2**: `tests/test_regression_v011_3_stop_hook_input_layer.py` 신설.
  실제 Claude Code 페이로드 모양 (transcript_path → JSONL → main-session
  assistant entry) 기준 25 mandatory + 1 xfail-tolerant test. 기존
  `test_regression_stop_hook_script.py` 35+ 테스트는 그대로 통과 (legacy
  shape 처리가 보존되므로).
- **U3**: honesty arc 산문 3건 — CLAUDE.md status 행에 v0.11.3 input-layer
  audit 포인터 1문장 append + `### Completion-Claim Verification` 상세
  단락에 §"Stop hook v0.11.3 input-layer fix (post-mortem)" 삽입;
  `scripts/hooks/stop_verify_claims.py` docstring에 chronological order
  로 v0.11.3 post-mortem 블록 삽입 (v0.10.3 다음, Residual 블록 앞);
  STATE.md Current Phase v0.11.2 → v0.11.3 promotion.
- **U4**: CHANGELOG v0.11.3 entry + 5-file version bump (2 plugin-version
  manifest 파일 + 3 URL pin 파일 v0.11.2 → v0.11.3).

honesty arc summary: "For 5 release cycles (v0.7.8 → v0.11.2) the Stop hook
was labeled enforced while silently fail-opening in production. v0.11.3
closes the input-layer gap; the detection logic shipped over v0.7.9 /
v0.10.2 / v0.10.3 is unchanged and now actually runs. Self-violation
acknowledged and corrected." — positive-commitment 언어 유지, supersession
framing 없음 (forbidden phrase list 통과).

### v0.11.3 ship surface

- 사용자-호출 skills: **58개** (변동 없음).
- Regression test suite: **421+ passing** (396 baseline + 25 신규
  v0.11.3 input-layer; 기존 35+ legacy-shape 테스트는 그대로 통과).
- Active executable contracts (v0.11.3 신규):
  `v011-3-stop-hook-input-layer-real-claude-code-shape`,
  `v011-3-legacy-shape-backwards-compat-lock`,
  `v011-3-sub-agent-isSidechain-filter`,
  `v011-3-honesty-arc-prose-emission`.

### v0.11.3 알려진 residual (v0.12.x+ 후보)

- 입력 계층은 닫혔지만 탐지 계층의 v0.10.3 residual (LLM-class semantic
  similarity / 접두어 없는 speculative tense / multi-paragraph 인용 /
  Cherokee · full-width Latin homoglyph)은 carry-forward.
- adversarial sentinel forgery는 file-system 접근 가능한 모델에 한해
  여전히 잔류 (v0.7.9 raised cost, not eliminated).
- Mid-session profile mutation guard 미구현.

## Previous Phase: v0.11.2 (hygiene cut — scope clarification)

Cross-model cutting-preparation deep analysis (session `2026-05-20-002`
— Researcher A Claude + Devil's Advocate Codex + Critic synthesis)에서
도출된 **high-agreement 교집합**만 즉시 cut. 큰 prune은 v0.12.0+ deferred.

- **U1**: `models` config block 제거 (`athanor.json`,
  `templates/athanor.json`, `schemas/athanor-config.schema.json`).
  v0.7.7에서 자기 deprecation 선언 → 4 minor 늦게 v0.11.2에서 closure.
- **U2**: CE-plugin lifecycle 4종 skill 제거 (`ce-update`,
  `ce-report-bug`, `ce-release-notes`, `ce-setup`). compound-engineering
  플러그인 자체 라이프사이클 도구 — athanor (orchestrator) 정체성 무관.
- **U3**: `NOTICE.md` vendored CE list 4건 제거 + v0.11.2 explanatory note.
- **U4**: test 회귀 처리 — `test_regression_v010_namespace_layout.py`의
  ce-* count assertion 37 → 33; `test_regression_doc_string_honesty.py`의
  models._doc pin을 inversion 패턴 (v0.10.3 §D6 답습) — "doc must lead
  DEPRECATED" → "block must NOT exist". v0.7.7~v0.11.2 honesty arc 종결.
- **U5**: plan + CHANGELOG + STATE + version bump (0.11.1 → 0.11.2).

honesty arc — supersession framing 없음. 정체성 cut framing =
"scope-clarification" (athanor stands alone, so CE-plugin lifecycle
belongs to CE). Devil's Advocate가 명시적으로 defend한 항목 (ce-lfg,
sp-using-superpowers, deep-plan/lite-plan, honesty-arc tests,
docs/plans, drift script) 모두 손대지 않음. drift script 변경 없음
(walk 동적 — 자연스럽게 33개만 iterate).

### v0.11.2 ship surface

- 사용자-호출 skills: **58개** (v0.11.1의 62에서 −4).
- Regression test suite: **396 passing** (변동 없음; v0.11.2는 신규
  test 없이 inversion 패턴으로 closure lock).
- Active cuts:
  - `models` config block: 3 manifest/schema files.
  - 4 ce-* skill directories.

### v0.12.0 mid-cut (deferred from v0.11.2)

- 도메인 특화 CE 7종 (`ce-dhh-rails-style`, `ce-gemini-imagegen`,
  `ce-test-xcode`, `ce-riffrec-feedback-analysis`, `ce-product-pulse`,
  `ce-slack-research`, `ce-frontend-design`)
- Beta variant 2종 (`ce-work-beta`, `ce-polish-beta`)
- Orphan sub-agent sweep (호스트 skill cut 이후)
- 호네스티 테스트 helper 추출 (~150줄 dedup)
- `docs/plans/` archive 이동

### v0.13.0 big cut (architectural, deferred)

- Drift script invariant 재정의 (`"approved subset, athanor-relevance
  justified"`)
- CE narrow to ~13-15 identity-leaning skills
- sp-* narrow to 4
- CLAUDE.md advisory-only section consolidation

요구: CHANGELOG voice-framing 사전 결정 — v0.11.0 / v0.11.1
positive-commitment gate 안에서 architectural cut을 표현 가능한지.

## Previous Phase: v0.11.1 (`using-superpowers` boundary clarification)

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
   prose 에서 false-negative 가능했으나 — vendor-aware whitelist 는
   originally scoped as v0.10.1+ work, shipped in v0.10.2 (A2 closure:
   18 CE/superpowers idioms + paraphrase regex + Cyrillic homoglyph fold).

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

## Archived from STATE.md (2026-06-06, v0.18.3 rotation)

## Previous Phase: v0.15.1 — LFG Team Default + Stale Reference Sweep

**v0.15.1** (released 2026-05-28) — `/athanor:lfg` Step 2 now invokes
`/athanor:work --team` by default (wave-parallel execution). Users may
override with `--solo`. Global `work.defaultMode` remains `"solo"` —
only the LFG pipeline defaults to team mode.

Stale reference sweep: 5 cross-references to the removed
`§"Vendored Surface — Identity Guard Layer"` updated to
`§"Concept Absorption Surface"`; plugin.json keywords cleaned;
`codex._doc` deferral text bumped to v0.16+.

Planning: standard tier (Planner A Claude + Codex review + Critic
refinement). Codex review scoped down Phase 1 from global default
change to LFG-only flag.

Identity invariants intact (4): Thin Leader / cross-model adversarial /
Spec-then-TDD / Stop hook gate. Companion-fix arc 5 layer (v0.11.3 →
v0.11.8) untouched.


## Archived from STATE.md (2026-06-06, v0.18.4 rotation)

## Previous Phase: v0.16.0 — Multi-Status Executor + PreToolUse Kernel Guard + CLAUDE.md Token Diet

**v0.16.0** (released 2026-05-28) — Three coordinated changes that
strengthen the Thin Leader contract surface:

1. **Multi-status executor.** `/athanor:work` now emits four worker
   completion statuses — `done`, `done_with_concerns`, `needs_context`,
   `blocked` — plus a `blocked_queue` so the leader can route partial
   completions without flattening them to binary success/failure.
2. **PreToolUse Kernel Guard.** A new PreToolUse hook enforces 3-class
   safety (destructive shell / force-push / credentials) before any
   tool invocation reaches the runtime. Sits alongside the existing
   Stop hook gate; both are command-based and honour
   `hooks.profile: "off"` per-project opt-out.
3. **CLAUDE.md token diet.** The contract index slimmed from ~534
   lines down to ~175 (navigation + 4 identity invariants + Status
   table). Heavyweight prose moved to `docs/archive/`:
   `stop-hook-postmortem.md`, `concept-absorption-surface.md`,
   `defense-mechanisms-detail.md`. Pinned by
   `tests/test_regression_v016_claude_md_contract.py` (line count
   band 145-175 + 4 contract anchors + 3 archive files).

Test surface grows from 639 → 644 (+5 ST16) plus additional coverage
shipped alongside the executor and kernel-guard work landed earlier in
the cycle.

Identity invariants intact (4): Thin Leader / cross-model adversarial /
Spec-then-TDD / Stop hook gate. Companion-fix arc 5 layer (v0.11.3 →
v0.11.8) untouched.


## Archived from STATE.md (2026-06-06, v0.18.5 bounded-history trim — cap 5 Previous)

## Previous Phase: v0.17.0 — Surface Cut + Capability Spikes

**v0.17.0** (released 2026-05-28) — A coordinated surface cut + two
infrastructure spikes landing as a single release:

1. **Big skill splits.** `skills/work/SKILL.md` (1153 → 250 lines
   router + 5 references files: multi-status, spec-then-tdd-handler,
   splitter, team-mode, learner-cleaner) and `skills/plan/SKILL.md`
   (1255 → 300 lines router + 7 references files: planner-dispatch,
   reviewer-dispatch, critic-variants, codex-availability,
   critic-rubric, presentation, depth-flag-dispatch). Two of athanor's
   heaviest skills become navigable routers with companion references.
2. **Command surface simplification.** `/athanor:deep-plan` and
   `/athanor:lite-plan` collapse into `/athanor:plan --depth={standard|
   deep|lite}` plus `/athanor:plan --no-review`. Trigger keywords stay
   on `/athanor:plan` for muscle memory; migration guide ships at
   `docs/v0.17.0-migration.md`.
3. **Documentation hoisting.** using-superpowers boundary moves from
   11× verbatim copies into CLAUDE.md canonical + 9 pointer refs.
   Spec-then-TDD discipline canonicalised in CLAUDE.md with brief
   pointers in plan/work/executor. NOTICE.md LIFT entries compressed
   to 1-line attributions.
4. **Vendoring cleanup.** `agents/vendored/ce/*.agent.md` removed —
   dead vendoring with zero live dispatch.
5. **Shared hook runtime + capability probe.** New
   `scripts/hooks/_athanor_hook_runtime.py` shared helpers
   (read_stdin_payload / read_athanor_config / is_hook_profile_off /
   resolve_project_root) consumed by `stop_verify_claims.py` and
   `pretool_kernel_guard.py` (behaviour preserved). New
   `scripts/hooks/capability_probe.py` passive probe emits
   `.athanor/hook-capability.json`.
6. **Config diet.** All `_doc` inline documentation fields hard-removed
   from `athanor.json` and `templates/athanor.json` (athanor.json
   4897 → 1153 bytes). Schema `description` fields remain the
   canonical inline docs.

Test surface grows 644 → 692+ across the cycle (S04 689, S08 692, S09
682 after the v0.17.0 doc-string honesty test deletion). New regression
files: `test_regression_v017_work_skill_split`,
`test_regression_s02_plan_skill_split`,
`test_regression_v017_hook_runtime`,
`test_regression_v017_capability_probe`,
`test_regression_s07_depth_flag_collapse`. Removed:
`tests/test_regression_doc_string_honesty.py`.

Planning: deep-tier adversarial plan (Planner A Claude + Planner B
Codex + cross-review + Critic synthesis). REMOVE-first ordering per
Plan B + Plan A's test-cascade rigor. 3-release roadmap: v0.17.0
(this) → v0.18.0 (hook additions) → v0.19.0 (evidence-bound
discipline).

Identity invariants intact (4): Thin Leader / cross-model adversarial /
Spec-then-TDD / Stop hook gate. Companion-fix arc 5 layer (v0.11.3 →
v0.11.8) untouched.

## Archived from STATE.md (2026-06-07, v0.18.6 bounded-history trim — cap 5 Previous)

## Previous Phase: v0.18.0 — Freeze-First (Plan B base)

**v0.18.0** (released 2026-05-29) — Introduces the **Freeze
infrastructure** stage shipping the first scope-locked editing envelope
for Claude file tools:

1. **Builder: `scripts/work/build_freeze_allowlist.py`** — per-session
   allowlist builder. Parses the `## Subtasks` block of `plan.md`,
   unions each subtask's `files:` declaration with session-local
   defaults + `athanor.json` `hooks.freeze.extraAllowedPaths`, writes
   `.athanor/sessions/<id>/freeze-allowlist.json`. Stdlib-only (same
   constraint as `scripts/hooks/*.py`).
2. **PreToolUse dispatcher: `scripts/hooks/pretool_dispatcher.py`** —
   single outer entry for PreToolUse events. Runs the v0.16.0 Kernel
   Guard FIRST (catastrophic class — destructive shell / force-push /
   credentials — is never over-ruled), then evaluates the freeze guard
   if `hooks.freeze.mode != "off"`. Kernel guard fail-CLOSED on missing
   config preserved (v0.16.0 default unchanged); freeze guard fail-open
   on missing allowlist (opt-in semantics).
3. **Freeze guard: `scripts/hooks/freeze_guard.py`** — Claude file-tool
   allowlist. Edit / Write / MultiEdit destination paths plus
   conservative Bash write patterns (`>`, `>>`, `tee`, `cp`, `mv`,
   `mkdir`, `touch`) are gated against
   `.athanor/sessions/<id>/freeze-allowlist.json`. Exit 2 on rejection.
4. **Config block: `hooks.freeze`** — new athanor.json key under
   `hooks.freeze` with `mode` ("off" default, "session" opt-in) and
   `extraAllowedPaths`. Schema entry shipped at the same time.

**Honesty residuals** (intentional scope limits):

- **D2 — Codex stage uneven enforcement.** `/athanor:lfg` Codex subprocess
  writes are NOT gated by Freeze. Freeze is documented as "Claude
  file-tool allowlist", not a comprehensive editing envelope.
- **Bash subprocess writes ungated.** `python -c "open('foo', 'w')..."`,
  `make build`, `codex exec`, etc. NOT detected. The conservative Bash
  pattern set covers visible-destination writes only.

**Deferred** (per Critic synthesis, both reviewers converged):

- **v0.18.1 — git-worktree isolation.** Admission criteria documented
  in `docs/ROADMAP.md`: freeze-violations.jsonl >= 10 across >= 5
  sessions, OR 1 user-reported issue with repro, OR `/athanor:work
  --team` same-file collision.
- **v0.18.2 — UserPromptSubmit injection.** Design precondition: live
  spike capturing real payload shape (v0.17.0 capability_probe shows
  UPS supported=false passively).

Test surface grows 692 -> 872+ across the cycle (+180 new). 11 new
regression files: `test_regression_v018_build_freeze_allowlist`,
`test_regression_v018_hooks_freeze_schema`,
`test_regression_v018_splitter_files_contract`,
`test_regression_v018_kernel_evaluate_payload`,
`test_regression_v018_pretool_dispatcher`,
`test_regression_v018_freeze_guard`,
`test_regression_v018_phase2_integration`,
`test_regression_v018_static_dedup_preservation`,
`test_regression_v018_freeze_step_06`,
`test_regression_v018_release_evidence` (4.2),
schema-coverage extensions across existing release-smoke tests.

Planning: deep-tier adversarial plan (Planner A Claude + Planner B
Codex + cross-review + Critic synthesis). Plan B base (Freeze-First) +
Plan A Phase 2 architecture (corrected per Codex review) + reviewer
convergence on stage shipping. Architectural choices: kernel-FIRST
dispatch ordering, kernel fail-CLOSED, freeze fail-open on missing
allowlist.

Identity invariants intact (4): Thin Leader / cross-model adversarial /
Spec-then-TDD / Stop hook gate. Companion-fix arc 5 layer (v0.11.3 ->
v0.11.8) untouched. PreToolUse Kernel Guard (v0.16.0) untouched —
dispatcher runs kernel FIRST.

## Archived from STATE.md (2026-06-07, v0.18.7 bounded-history trim — cap 5 Previous)

## Previous Phase: v0.18.1 — Agent Inventory Audit + Concept Absorption

**v0.18.1** (released 2026-05-31) — Cleanup + concept-absorption patch
(Goal 36470e54). No new feature, no new agent.

1. **Reference-agent evaluation.** Systematic audit of external agent
   inventories (ECC 259/68, CE 43, autoresearch 1, gstack/superpowers 0)
   → **0 wholesale adoptions**. Every candidate was subsumed by the
   existing reviewer 6-lens / critic / researcher / learner surface, out
   of scope, or Thin-Leader-incompatible. Consistent with the v0.12.0
   concept-absorption policy. Matrix: `docs/agent-evaluation-matrix.md`.
2. **Concept absorption (prose, not new agents).** Reviewer quality lens
   gains two heuristics: silent-failure (swallowed-error / empty-catch,
   ex-ECC) + project-standards (repo CLAUDE.md audit, ex-CE).
   `agents/reviewer.md` + `skills/review/SKILL.md`. NOTICE.md ledger +2.
3. **Agent inventory clarified.** Dual-nature framing (inline-dispatch
   reference docs + @-mention registered types) + COLLISION GUARD
   rationale documented (CLAUDE.md + `docs/archive/agent-dual-nature.md`).
   All 11 agents KEPT, 0 removed.

Identity invariants intact (4): Thin Leader / cross-model adversarial /
Spec-then-TDD / Stop hook gate.

## Archived from STATE.md (2026-06-20, v0.19.3 bounded-history trim — cap 5 Previous)

## Previous Phase: v0.18.4 — Engineering-Quality Principle (complexity + fail-loud)

**v0.18.4** (released 2026-06-06) — Codifies the "Engineering quality"
principle (low complexity + fail-loud over silent fallback) across athanor's
advisory + gate surfaces. No identity-invariant change.

1. **Principle (CLAUDE.md §Core Principle)**: works is the floor; minimize
   complexity; **no indiscriminate fallback** — surface errors, don't swallow
   them into a fallback. band 175→178.
2. **Advisory wiring (user code)**: plan Critic axis (D) simplicity & fail-loud
   (synced across rubric + all variants + SKILL.md four-axis); review
   maintainability silent-failure lens strengthened (fail-loud explicit).
3. **Gate (athanor's own code)**: pretool_dispatcher fail-loud breadcrumb on
   unparseable stdin (was silent).

4 new regression tests; full suite 939 passed, 0 failed. An adversarial
Workflow review (4 lenses) caught + fixed a SKILL.md three→four-axis sync miss
pre-release.

Identity invariants intact (4): Thin Leader / cross-model adversarial /
Spec-then-TDD / Stop hook gate.

## Archived from STATE.md (2026-06-18, v0.19.0 bounded-history trim — cap 5 Previous)

## Previous Phase: v0.18.3 — Cleanup Audit + ref Adoption

**v0.18.3** (released 2026-06-06) — Plugin-hygiene cleanup + 2 ref-pattern
adoptions, from the ref-update audit. No identity-invariant change.

1. **Cleanup.** README deep/lite-plan→`--depth=`; discuss `--new-session`
   broken-promise dropped; agent model drift fixed (CLAUDE.md §Effort maps
   all 11 agents to actual tier); STATE.md trimmed 28→5 Previous (v0.15.0…
   v0.7.9 → `docs/archive/STATE-history.md`); Memory 2-tier honesty label.
2. **ref adoption.** Approach-altitude gate in `/athanor:plan` (CE v3.11.1);
   review lens-persona section carving (STOP-Read) in `/athanor:review`
   (gstack v1.56) — 418→311 lines, behavior preserved.
3. **Verified false-positives.** B-6 concepts orphan + B-8 defense label
   were oversights (no change); autoresearch dangerous-cmd/privacy-block
   already covered by the PreToolUse kernel guard.

16 new regression tests, all RED→GREEN. Full suite 932 passed, 0 failed.

Identity invariants intact (4): Thin Leader / cross-model adversarial /
Spec-then-TDD / Stop hook gate.

## Archived from STATE.md (2026-06-12, v0.18.8 bounded-history trim — cap 5 Previous)

## Previous Phase: v0.18.2 — lfg/lfg-goal Doc-Lifecycle Audit + Cleanup

**v0.18.2** (released 2026-06-04) — Patch closing the lfg/lfg-goal
documentation-lifecycle audit (3 concerns: read→execute, execute→document,
cleanup of stale docs). No identity-invariant change.

1. **Cleanup layer (concern ③, the weakest).** `agents/cleaner.md` gains a
   "Clean Old Goals" step that ages out non-completing (`aborted`/
   `abandoned`) goals past `goalRetentionDays` — closing the **D13 broken
   cross-reference** (lfg-goal claimed the cleaner does this; no step
   existed). `complete` goals excluded (user action). Dispatch synced.
2. **Drift + dormancy fixes.** Cleaner dispatch tier `sonnet`→`haiku`
   (matches frontmatter + CLAUDE.md "minimal effort"); `learner-on-release`
   wired into the release ceremony (`agents/releaser.md` Step 6).
3. **Documentation lifecycle (new).** Migration-guide staleness frontmatter
   (`status`/`superseded-by`) + `CONVENTIONS.md §7` + regression-test ager;
   STATE.md bounded-history trim rule (progressive); completed-goal
   `receipts/` archival; lfg PR-body work-log/review persistence slots.

16 new regression tests (7 files), all RED→GREEN. Cleanup/trigger layers
are advisory (prose-driven), consistent with athanor defense-mechanism
honesty labels.

Identity invariants intact (4): Thin Leader / cross-model adversarial /
Spec-then-TDD / Stop hook gate.
