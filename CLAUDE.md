# Athanor

General-purpose agentic workflow orchestrator plugin for Claude Code.

## Core Principle

**Thin Leader**: The leader (main session) NEVER does implementation work directly.
It normally parses input, dispatches to clean-context workers, and presents results.
All project file reading, analysis, code writing, and execution happens in worker agents.

Documented infrastructure/output exceptions:
- The leader may create `.athanor/sessions/` directories and session-local files needed to run the workflow.
- In `/athanor:discuss` clarify mode, after explicit user confirmation, the leader may write `.athanor/sessions/{id}/requirements.md` as a captured dialogue artifact.
- These exceptions do not permit editing project source files or performing implementation work before `/athanor:work`.

## Native Agent Inventory

Agent definitions live in `agents/` as `.md` reference documents. The Leader reads these when dispatching via `Agent()`. They describe purpose, tools, and dispatch contract but are NOT full implementations — canonical code remains in the respective skills.

| Agent | Purpose | Since |
|-------|---------|-------|
| `analyst.md` | Analysis dispatch target | v0.7.x |
| `cleaner.md` | Session/memory lifecycle | v0.7.x |
| `critic.md` | Adversarial plan review | v0.7.x |
| `executor.md` | Subtask execution (Ralph loop) | v0.7.x |
| `learner.md` | Lessons extraction | v0.7.x |
| `planner.md` | Plan generation | v0.7.x |
| `researcher.md` | Research/discovery dispatch | v0.7.x |
| `reviewer.md` | Multi-lens code review | v0.7.x |
| `releaser.md` | Release ceremony automation (version bump, CHANGELOG, STATE.md, test pins) | v0.14.0 |
| `codex-dispatcher.md` | Codex CLI dispatch wrapper (timeout clamping, stdin redirect, exit-code handling) | v0.14.0 |
| `ci-watcher.md` | CI watch + autofix loop (gh pr checks, failure log analysis, fix dispatch) | v0.14.0 |

Additionally, 2 vendored sub-agents at `agents/vendored/ce/`: `ce-git-history-analyzer.agent.md` and `ce-repo-research-analyst.agent.md` (retained per D12).

## Commands

### Athanor-native (11 user-invocable + 2 internal)

| Command | Mode | Purpose |
|---------|------|---------|
| `/athanor:setup` | — | Infrastructure health check and configuration (v0.10.0 includes vendored-surface inventory) |
| `/athanor:discuss` | Plan | Decision brainstorming + intent clarification (dual mode: clarify ↔ synthesis). clarify = single-Claude gap-probe dialog → `requirements.md`; synthesis = Researcher + Devil's Advocate + Critic → `discuss.md` (v0.7.x behavior). |
| `/athanor:analyze` | Plan | Parallel fast analysis (LSP, mem-search) |
| `/athanor:debug` | Plan | Triage → 병렬 실패 진단 (에러, git 이력, 코드 추적) |
| `/athanor:deep-plan` | Plan | Full adversarial planning (Claude + Codex 교차 검증) |
| `/athanor:plan` | Plan | **Cross-model adversarial planning** (Planner A Claude + Planner B Codex + Critic) — athanor identity #2. Post-v0.12.0: sole native planner. Install upstream compound-engineering for CE variant. |
| `/athanor:lite-plan` | Plan | Lightweight planning (Claude only, 리뷰 없음) |
| `/athanor:work` | Execute | **Spec-then-TDD discipline** (Splitter execution_note + conjunction-of-three Phase 3 gate) — athanor identity #3. Post-v0.12.0: sole native executor. Install upstream compound-engineering for CE variant. |
| `/athanor:review` | Plan | Parallel multi-lens code review (architecture, quality, security, performance, testing, documentation) |
| `/athanor:lfg` | Execute | **Standalone end-to-end pipeline** (v0.11.0) — wraps the LFG flow through athanor-native commands at identity-bearing steps (Step 1 `/athanor:plan` cross-model + Step 2 `/athanor:work` Spec-then-TDD + Step 3 `/athanor:review` 6-lens). Post-v0.12.0: sole pipeline. (v0.15.1: `--team` mode default) |
| `/athanor:lfg-goal` | Execute | **Goal-driven macro Ralph loop** (v0.13.0) — orchestration layer over existing 4 identity invariants (no new invariant per D11). Combines durable goal ledger + dispatched receipt-validator + adversarial 3-tier goal-completion check. |

### Vendored (post-v0.12.0 atomic cut)

- `/athanor:ce-test-browser` — sole CE skill retained (D8 KEEP; browser automation). Originally v0.10.0 vendored 33 ce-* + 13 sp-* skills; v0.12.0 atomic cut removed all but this one. No `/athanor:sp-*` skills remain.
- Naming policy (D2): athanor-native skills keep unprefixed `/athanor:<name>`; `ce-test-browser` keeps the `ce-` prefix. See §Concept Absorption Surface and `docs/archive/concept-absorption-surface.md`.

## Rules

1. `/athanor:work` 전에는 절대 파일을 수정하지 않는다 (Plan Mode)
2. Leader는 dispatch + 결과 수집만 한다
3. Worker는 항상 깨끗한 컨텍스트에서 시작한다
4. 세션 간 통신은 `.athanor/sessions/{id}/` 의 .md 파일을 통한다
5. 작업 완료 시 자동으로 메모리를 저장한다 (2-tier: permanent + working)

## Session Directory

```
.athanor/
  sessions/{id}/
    discuss.md, research-a.md, research-b.md   ← /athanor:discuss
    analyze.md                                  ← /athanor:analyze
    debug.md                                    ← /athanor:debug
    plan-a.md, plan-b.md                        ← plan A / B (deep tier)
    review-of-a.md, review-of-b.md              ← reviews (deep tier)
    plan.md                                     ← /athanor:plan 확정안 (Subtasks는 /athanor:work Step 0.5)
    decisions.md                                ← 확정 결정 로그
    work-log.md                                 ← /athanor:work 진행 기록
    discoveries/                                ← worker discovery briefs
  lessons/                                      ← learned lessons (auto-managed)
athanor.json                                    ← project root, NOT inside .athanor/
```

## Session Lookup Convention

Canonical rule for finding "the active session"; per-skill prose should reference this section rather than restate (drift between skills caused the v0.7.7 M4 finding).

1. **Pattern:** Only `.athanor/sessions/<dir>` where `<dir>` matches
   `^\d{4}-\d{2}-\d{2}-\d{3}$`. Non-matching names (e.g., `lessons/`,
   `discoveries/`, manually-renamed directories) are ignored.
2. **Selection:** Sort matching directories lexicographically descending.
   The first element is `<LATEST>`. This is the active session.
3. **No "today" semantics.** Day boundaries do NOT affect selection.
   A session created at 23:45 yesterday remains LATEST at 09:00 today,
   until a new session is explicitly created.
4. **Stale-session announcement:** If `<LATEST>` date != today's date,
   the skill announces:
   > `Reusing session <LATEST> (created on <YYYY-MM-DD>). To start fresh,
   > create a new session manually` (the `--new-session` flag was originally
   promised in v0.8.0 release notes but never implemented; reclassified
   v0.11.7 as broken-promise — no current implementation target).
5. **Bash reference implementation** (skills MAY embed inline):
   ```bash
   LATEST=$(ls -1 .athanor/sessions 2>/dev/null \
     | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{3}$' \
     | sort | tail -1)
   ```
6. **Skill responsibilities:**
   - `/athanor:plan`, `/athanor:discuss`: reuse `<LATEST>` if it has no
     `work-log.md`; else create a new session.
   - `/athanor:work`: load `<LATEST>` plus resume guard (work-log.md presence).
   - `/athanor:analyze`, `/athanor:debug`, `/athanor:review`: reuse `<LATEST>`
     (read-only or append intent; no new-session creation).
   - `/athanor:scope-drift`: load `<LATEST>` plus intent-source glob.

## Defense Mechanisms

### Status table

| Mechanism | Enforcement |
|---|---|
| Completion-Claim Verification (Stop hook) | **enforced (command-based)** — `hooks/hooks.json` registers a `type: command` Stop hook invoking `scripts/hooks/stop_verify_claims.py`. Detects material claims via v0.7.7 English+Korean whitelist + v0.10.2 NFKC unicode normalization + Cyrillic/Greek/Armenian confusables fold + paraphrase regex + v0.10.2 vendor-aware whitelist (CE/superpowers idioms) + v0.10.3 conditional-tense + attribution suppression. Exits 2 to block Stop with stderr fed back as continuation context; emission sentinel `<!-- athanor:verification-emission v=2 nonce=... -->` prevents re-entry. `athanor.json` `hooks.profile: "off"` opt-out. **v0.10.0 scope** — vendor-aware whitelist applies to vendored CE/superpowers prose idioms (v0.10.1+ refinement). v0.11.3 input-layer fix + v0.11.4 plugin-root deployment fix close the companion-fix arc. Spike evidence: `docs/STATE.md` §"Command-hook Stop blocking spike (2026-05-18)". See `docs/archive/stop-hook-postmortem.md` and `docs/archive/defense-mechanisms-detail.md` for historical detail. |
| Stop-Phrase Detection | **advisory** — Leader-side prose guidance; spread across `skills/{work,discuss,analyze,debug,plan}/SKILL.md` Step 2.5 "Worker Output Defense"; not enforced by a code-level grep gate |
| Read-Before-Edit Rule | **advisory** — prose guidance; Claude Code runtime is the practical enforcer for Claude-based workers, but no plugin-layer guard for Codex/non-Claude workers |
| Scope Drift Detection | **on-demand** — `skills/scope-drift/SKILL.md` user-invoked only; no auto-fire on Stop or completion claims |
| Spec-then-TDD Discipline | **advisory (planner-classified)** — `/athanor:plan` Planner A 출력의 Verify 필드를 MUST/SHOULD bullets로 받고, `/athanor:work` Task Splitter가 각 subtask에 `execution_note` (spec-then-tdd / test-aware / direct) + `acceptance_criteria` 자동 할당. Executor가 분류에 따라 red-first 5단계 / 종료 게이트 (`tests/**` 수정 + `full_suite_passed: true` 자가보고 + verification line 일관성, 세 조건 conjunction) / 그대로 분기. **v0.10.0 scope:** discipline applies to athanor-native `/athanor:work` only. See `docs/archive/defense-mechanisms-detail.md` for full pipeline. |
| using-superpowers boundary (v0.11.1) | **advisory (preamble-declared)** — `superpowers:using-superpowers` skill은 v0.10.0 vendoring으로 흡수되어 매 세션 시작 시 Claude Code platform이 제공하는 SessionStart system reminder channel로 로드된다 (athanor의 hooks.json 등록 결과 아님). 그 skill의 "ABSOLUTELY MUST invoke before response" 톤은 athanor-native **11 Thin Leader skill** (analyze, debug, deep-plan, discuss, lfg, lfg-goal, lite-plan, plan, review, setup, work) 호출 context에서는 **advisory here**다 — discovery가 leader dispatch로 해소되며, pre-response invocation check은 native context에서 안내일 뿐 강제 아님 (planner-classified discipline). 본 boundary는 11 skill 각각의 §Identity 직후 `### v0.11.1 using-superpowers boundary` subsection에 동일 문구로 인라인 선언됨; 회귀는 `tests/test_regression_v011_1_using_superpowers_boundary.py`로 lock. Cross-reference: CLAUDE.md §Defense Mechanisms. Concept adopted from superpowers v5.1.0 sp-using-superpowers (MIT, Jesse Vincent). |
| PreToolUse Kernel Guard | **enforced (command-based)** — `hooks/hooks.json` PreToolUse event. Blocks 3 catastrophic classes: destructive shell (rm -rf /, git reset --hard), force-push to main/master, credential file access (.env, private keys). `.env.example`/`.env.test` allowed. `hooks.profile: "off"` opt-out. |

### Completion-Claim Verification (Stop hook — enforced, command-based)

On every `Stop` event, Claude Code invokes `scripts/hooks/stop_verify_claims.py` (registered as `type: command` in `hooks/hooks.json`). The script extracts the last main-session assistant message, checks the `hooks.profile: "off"` opt-out, recognises its own current `<!-- athanor:verification-emission v=2 nonce=<32-hex> -->` sentinel (re-entry prevention), greps for material-claim phrases (English + Korean whitelist), and exits 2 with stderr fed back as continuation context — forcing the model to invoke `verification-before-completion` and produce fresh evidence before Stop succeeds. **Spike evidence:** 2026-05-18 dry-run confirmed Claude Code honors `exit 2` from command-based Stop hooks (`docs/STATE.md` §"Command-hook Stop blocking spike (2026-05-18)"). **Companion-fix arc:** v0.11.3 input-layer parser + v0.11.4 `${CLAUDE_PLUGIN_ROOT}` path. **Known residuals (v0.11.8+):** LLM-class semantic similarity, speculative tense, multi-paragraph quote spans, Cherokee homoglyphs. See `docs/archive/stop-hook-postmortem.md` + `docs/archive/defense-mechanisms-detail.md` for full pipeline, post-mortem, and detection-layer history.

### Spec-then-TDD Discipline (advisory — planner-classified)

`/athanor:work` Task Splitter가 각 subtask를 세 분류 중 하나로 자동 할당:
- **`spec-then-tdd`**: source code + 새 동작/계약 → red-first 5단계 (test → run RED → implement → run GREEN → next). Worker가 per-criterion `red_evidence` 보고. RED 안 가면 **pending-then-gated** — Phase 3 게이트 재통과 필요.
- **`test-aware`**: source code + refactor → 종료 게이트 (세 조건 conjunction): (1) `tests/**` path 수정 1개 이상, (2) `full_suite_passed: true` 자가보고, (3) `verification:` prose 일관성.
- **`direct`**: prose-only (`.md`, CHANGELOG) → doc/config-only edits.

**What it does NOT catch:** Splitter의 오분류, worker가 evidence를 fabricate하는 adversarial forgery (leader는 evidence *shape*만 검증). 메커니즘은 advisory — runtime 강제 없음. **v0.10.0 scope:** athanor-native `/athanor:work` only. See `docs/archive/defense-mechanisms-detail.md` for full pipeline, stop-phrase list, scope-drift trigger glob, and Critic rubric.

## Concept Absorption Surface (post-v0.12.0)

Previously titled §"Vendored Surface — Identity Guard Layer" through v0.10.0 → v0.11.8; v0.12.0 renames it post-cutover. v0.10.0 originally absorbed compound-engineering v3.8.3 (33 skills + 49 sub-agents) and superpowers v5.1.0 (13 skills) under `/athanor:ce-*` / `/athanor:sp-*`. **v0.10.0 plan-of-record misread the user's concept-absorption intent as wholesale plugin vendoring.** The v0.12.0 atomic cut closes the scope correction — 1 KEEP skill (`ce-test-browser`, D8) + 2 KEEP sub-agents (D12) + 5 concepts absorbed as prose in athanor-native skills (reviewer personas, Iron Law debugging, requirements capture, skill-discovery preamble, doc-review mode). Full detail: `docs/archive/concept-absorption-surface.md`. Migration: `docs/v0.12.0-migration.md`. Retrospective: `docs/archive/v010-v011-vendoring-scope-correction.md`. Attribution ledger: NOTICE.md.

### Identity invariants (survive the cutover)

Four athanor identity commitments survive intact, upheld by native skill prose + regression locks:
1. **Thin Leader contract.** Leader never does implementation work directly.
2. **Cross-model adversarial planning.** `/athanor:plan` = Planner A (Claude) + Planner B (Codex) + Critic.
3. **Spec-then-TDD discipline.** `/athanor:work` Splitter `execution_note` + conjunction-of-three Phase 3 gate.
4. **Stop hook runtime gate.** `scripts/hooks/stop_verify_claims.py` fires on every Stop event (v0.10.0 vendor-aware whitelist scope; D11 preserved as general defensive coverage).

### Effort Level
- Planner / Critic: highest reasoning effort
- Executor / Analyst: standard effort
- Cleaner: minimal effort

## Lessons System

Workers should check `.athanor/lessons/` for relevant lessons before starting:
- Filter by `skill:` tag matching their role
- Apply relevant lessons to their approach
- This enables Athanor to grow smarter with use

## Configuration

See `athanor.json` in project root. Key settings:
- `codex.enabled`: Codex cross-model planning (default: true)
- `work.defaultMode`: "solo" or "team"
- `memory.decayDays`: Working memory retention (default: 7)
- `memory.promotionThreshold`: Access count for auto-promotion (default: 5)
- `triggers.language`: "ko", "en", or "both"
