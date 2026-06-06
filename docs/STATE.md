# Athanor — Implementation State

> 이 파일은 현재 구현 진행 상태를 추적합니다.
> 각 Phase / 릴리스 완료 시 업데이트합니다.
> 자세한 변경 내역은 `CHANGELOG.md` 를 정본(source of truth)으로 봅니다.

## Current Phase: v0.18.4 — Engineering-Quality Principle (complexity + fail-loud)

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
| `learner-on-release` | ✅ ceremony 단계 (advisory) | `agents/releaser.md` Step 6 — release tag 후 leader가 Learner dispatch (`learner_on_release: pending-leader-dispatch` 신호). `agents/learner.md` §On Release |
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
