# Athanor

General-purpose agentic workflow orchestrator plugin for Claude Code. Current package-facing operator map: [docs/package-knowledge-index.md](docs/package-knowledge-index.md).

## Core Principle

**Thin Leader**: The leader (main session) NEVER does implementation work directly; it parses input, dispatches to clean-context workers, and presents results. All project file reading, analysis, code writing, and execution happens in worker agents.

Documented infrastructure/output exceptions:
- The leader may create `.athanor/sessions/` directories and session-local files needed to run the workflow.
- In `/athanor:discuss` clarify mode, after explicit user confirmation, the leader may write `.athanor/sessions/{id}/requirements.md` as a captured dialogue artifact.
- In `/athanor:lfg` / `/athanor:lfg-goal`, under that pipeline's explicit user authorization, the leader may run git/gh plumbing (commit, push, open PR, CI watch) and read session/repo files for verification.
- These exceptions cover infra/output + lfg plumbing only — they do NOT permit the leader to author project source edits or do implementation work (before, during, or after `/athanor:work`).

**Engineering quality**: 동작은 최소 요건일 뿐 — 복잡도는 낮게, 유지보수는 쉽게 유지한다. **무분별한 fallback 금지 (fail-loud over silent fallback)**: 정정해야 할 오류를 폴백으로 삼켜 숨기지 말고 표면화한다(에러를 폴백으로 넘겨 찾기 어렵게 만들지 않는다). 정당화되지 않은 복잡도·scope는 줄인다. 사용자 코드엔 Critic/review로 권고(advisory), athanor 자체 코드엔 test/gate로 강제.

## Native Agent Inventory

Registered agent definitions live in plugin-root `agents/`; inline-only role reference docs live in `docs/agent-roles/`. **4 registered agent types** (`learner`, `releaser`, `ci-watcher`, `codex-dispatcher`) carry `name:`/`tools:` frontmatter and ARE dispatched as types by the leader / release ceremony / lfg. **7 reference documents** (`analyst`, `cleaner`, `critic`, `executor`, `planner`, `researcher`, `reviewer`) are `description:`-only and NOT registered: skills dispatch these pipeline roles via an INLINE `Agent()` prompt carrying session-specific paths (`.athanor/sessions/{id}/...`) a standalone agent lacks — registering them would be a never-usable contradiction. v0.18.7 de-registered the 7 (0 standalone adoption per `docs/agent-evaluation-matrix.md`; inline is canonical), and P16 moved them out of plugin-root `agents/` so `claude plugin details` reports the true 4-agent loader surface. Current executable skill/role/agent topology: `docs/agent-topology.md`. Full detail: `docs/archive/agent-dual-nature.md`.

| Agent | Kind | Purpose | Since |
|-------|------|---------|-------|
| `docs/agent-roles/analyst.md` | reference | Analysis dispatch target | v0.7.x |
| `docs/agent-roles/cleaner.md` | reference | Session/memory lifecycle | v0.7.x |
| `docs/agent-roles/critic.md` | reference | Adversarial plan review | v0.7.x |
| `docs/agent-roles/executor.md` | reference | Subtask execution (Ralph loop) | v0.7.x |
| `agents/learner.md` | registered | Lessons extraction | v0.7.x |
| `docs/agent-roles/planner.md` | reference | Plan generation | v0.7.x |
| `docs/agent-roles/researcher.md` | reference | Research/discovery dispatch | v0.7.x |
| `docs/agent-roles/reviewer.md` | reference | Multi-lens code review | v0.7.x |
| `agents/releaser.md` | registered | Release ceremony automation (version bump, CHANGELOG, STATE.md, test pins) | v0.14.0 |
| `agents/codex-dispatcher.md` | registered | Codex CLI dispatch wrapper (timeout clamping, stdin redirect, exit-code handling) | v0.14.0 |
| `agents/ci-watcher.md` | registered | CI watch + autofix loop (gh pr checks, failure log analysis, fix dispatch) | v0.14.0 |

## Commands

### Athanor-native (11 user-invocable + 2 internal: scope-drift, verification-before-completion)

| Command | Mode | Purpose |
|---------|------|---------|
| `/athanor:setup` | — | Infrastructure health check and configuration (v0.10.0 includes vendored-surface inventory) |
| `/athanor:prompt-gen` | Plan | Prompt refinement + skill routing: turns vague user requests into clear prompts and recommends the next Athanor skill. |
| `/athanor:discuss` | Plan | Decision brainstorming + intent clarification (dual mode: clarify ↔ synthesis). clarify = single-Claude gap-probe dialog → `requirements.md`; synthesis = Researcher + Devil's Advocate + Critic → `discuss.md` (v0.7.x behavior). |
| `/athanor:analyze` | Plan | Parallel fast analysis (LSP, mem-search) |
| `/athanor:assess` | Plan | Goal-aligned multi-lens assessment: weighted dimensions, 100-point score, confidence, overbuilt/underbuilt findings, and Priority Plan. |
| `/athanor:debug` | Plan | Triage → 병렬 실패 진단 (에러, git 이력, 코드 추적) |
| `/athanor:plan` | Plan | **Cross-model adversarial planning** with tier dispatch via `--depth={standard\|deep\|lite}` flag (+ orthogonal `--no-review`). Standard tier (default) = Planner A Claude + Codex review + Refinement Critic. Deep tier = Planner A + Planner B Codex cross-planning + 4-input Synthesis Critic (was `/athanor:deep-plan`). Lite tier = Planner A only, review + critic skipped (was `/athanor:lite-plan`). Trigger keywords ("딥 플랜", "라이트 플랜", etc.) still route into the unified skill — athanor identity #2. v0.17.0 / S07 collapsed the former deep-plan + lite-plan slots into this flag-dispatch interface; see `docs/v0.17.0-migration.md`. |
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
5. 작업 완료 시 lessons를 2-tier(permanent/working)로 추출·저장한다 (`.athanor/lessons/` frontmatter `importance`; mem-search 영구저장은 미구현 — STATE.md Known gaps)

## Session Directory

```
.athanor/
  sessions/{id}/
    discuss.md, research-a.md, research-b.md; prompt-gen.md ← /athanor:discuss, /athanor:prompt-gen
    analyze.md                                  ← /athanor:analyze
    assess.md                                   ← /athanor:assess
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
   - `/athanor:plan`, `/athanor:discuss`, `/athanor:prompt-gen`: reuse `<LATEST>` if it has no
     `work-log.md`; else create a new session.
   - `/athanor:work`: load `<LATEST>` plus resume guard (work-log.md presence).
   - `/athanor:analyze`, `/athanor:assess`, `/athanor:debug`, `/athanor:review`: reuse `<LATEST>`
     (read-only or append intent; no new-session creation).
   - `/athanor:scope-drift`: load `<LATEST>` plus intent-source glob.

## Defense Mechanisms

### Status table

| Mechanism | Enforcement |
|---|---|
| Completion-Claim Verification (Stop hook) | **enforced (command-based)** — `hooks/hooks.json` registers a `type: command` Stop hook invoking `scripts/hooks/stop_verify_claims.py`. Detects material claims via v0.7.7 English+Korean whitelist + v0.10.2 NFKC unicode normalization + Cyrillic/Greek/Armenian confusables fold + paraphrase regex + v0.10.2 vendor-aware whitelist (CE/superpowers idioms) + v0.10.3 conditional-tense + attribution suppression. Exits 2 to block Stop with stderr fed back as continuation context; emission sentinel `<!-- athanor:verification-emission v=2 nonce=... -->` prevents re-entry. `athanor.json` `hooks.profile: "off"` opt-out. **v0.10.0 scope** — vendor-aware whitelist applies to vendored CE/superpowers prose idioms (v0.10.1+ refinement). v0.11.3 input-layer fix + v0.11.4 plugin-root deployment fix close the companion-fix arc. Spike evidence: `docs/STATE.md` §"Command-hook Stop blocking spike (2026-05-18)". See `docs/archive/stop-hook-postmortem.md` and `docs/archive/defense-mechanisms-detail.md` for historical detail. |
| Stop-Phrase Detection | **advisory** — Leader-side prose guidance; spread across `skills/{work,discuss,analyze,debug,plan}/SKILL.md` Step 2.5 "Worker Output Defense"; whitelist canonical doc: `docs/stop-phrase-whitelist.md`; not enforced by a code-level grep gate |
| Read-Before-Edit Rule | **advisory** — prose guidance; Claude Code runtime is the practical enforcer for Claude-based workers, but no plugin-layer guard for Codex/non-Claude workers |
| Scope Drift Detection | **on-demand** — `skills/scope-drift/SKILL.md` user-invoked only; no auto-fire on Stop or completion claims |
| Spec-then-TDD Discipline | **advisory (planner-classified)** — `/athanor:plan` emits Verify criteria, `/athanor:work` classifies subtasks, and the worker/result handler applies the matching branch. **v0.10.0 scope:** athanor-native `/athanor:work` only. Canonical runtime behavior: `skills/work/references/spec-then-tdd-handler.md`; historical v0.8.0 design detail: `docs/archive/defense-mechanisms-detail.md`. |
| using-superpowers boundary (v0.11.1) | **advisory (preamble-declared)** — `superpowers:using-superpowers` skill은 v0.10.0 vendoring으로 흡수되어 매 세션 시작 시 Claude Code platform이 제공하는 SessionStart system reminder channel로 로드된다 (athanor의 hooks.json 등록 결과 아님). 그 skill의 "ABSOLUTELY MUST invoke before response" 톤은 athanor-native **11 Thin Leader skills** (assess, analyze, debug, discuss, lfg, lfg-goal, plan, prompt-gen, review, setup, work — v0.17.0 / S07에서 deep-plan + lite-plan은 `/athanor:plan --depth=` 로 흡수됨) 호출 context에서는 **advisory here**다 — discovery가 leader dispatch로 해소되며, pre-response invocation check은 native context에서 안내일 뿐 강제 아님 (planner-classified discipline). 본 boundary는 11 skill 각각의 §Identity 직후 `### using-superpowers boundary` 2-line pointer로 선언되고 canonical 텍스트는 §"using-superpowers boundary (v0.11.1) — canonical declaration" 에 집약됨 (v0.17.0 / S04 hoist); 회귀는 `tests/test_regression_v011_1_using_superpowers_boundary.py`로 lock. Cross-reference: CLAUDE.md §Defense Mechanisms. Concept adopted from superpowers v5.1.0 sp-using-superpowers (MIT, Jesse Vincent). |
| PreToolUse Kernel Guard | **enforced (command-based), best-effort coverage** — `hooks/hooks.json` PreToolUse event; the hook genuinely fires and exits 2 to block. Targets 3 accident-class patterns: destructive shell (rm -rf /, git reset --hard), force-push to main/master, credential file access (.env, private keys). `.env.example`/`.env.test` allowed. `hooks.profile: "off"` opt-out. **Honest scope:** this is a textual regex guard, NOT a command parser or security boundary — it catches obvious literal forms but is bypassable by obfuscation (command substitution `$(...)`, variable indirection, base64/eval, reordered flags). Treat it as a guardrail against fat-finger accidents, not containment against an adversary. The force-push matcher uses a `(?![\w-])` boundary so `main`/`master`-prefixed branches (e.g. `feature/main-update`) are allowed while exact `main`/`master` segments stay blocked. |

### Completion-Claim Verification (Stop hook — enforced, command-based)

On every `Stop` event, Claude Code invokes `scripts/hooks/stop_verify_claims.py` (registered as `type: command` in `hooks/hooks.json`). The script extracts the last main-session assistant message, checks the `hooks.profile: "off"` opt-out, recognises its own current `<!-- athanor:verification-emission v=2 nonce=<32-hex> -->` sentinel (re-entry prevention), greps for material-claim phrases (English + Korean whitelist), and exits 2 with stderr fed back as continuation context — forcing the model to invoke `verification-before-completion` and produce fresh evidence before Stop succeeds. **Spike evidence:** 2026-05-18 dry-run confirmed Claude Code honors `exit 2` from command-based Stop hooks (`docs/STATE.md` §"Command-hook Stop blocking spike (2026-05-18)"). **Companion-fix arc:** v0.11.3 input-layer parser + v0.11.4 `${CLAUDE_PLUGIN_ROOT}` path. **Known residuals (v0.11.8+):** LLM-class semantic similarity, speculative tense, multi-paragraph quote spans, Cherokee homoglyphs. See `docs/archive/stop-hook-postmortem.md` + `docs/archive/defense-mechanisms-detail.md` for full pipeline, post-mortem, and detection-layer history.

### Spec-then-TDD Discipline (advisory — planner-classified)

`/athanor:work` Task Splitter classifies each subtask as `spec-then-tdd`, `test-aware`, or `direct`; the worker/result handler applies that branch. This is an athanor-native identity invariant for `/athanor:work`, not a global plugin runtime gate.

Canonical runtime behavior, result schema, downgrade/gate handling, and PostToolUse hybrid evidence checks live in `skills/work/references/spec-then-tdd-handler.md`; historical v0.8.0 design detail remains archived in `docs/archive/defense-mechanisms-detail.md`.

**What it does NOT catch:** Splitter misclassification and adversarial evidence fabrication remain advisory residuals; runtime evidence mismatches can fail only where PostToolUse evidence exists.

### using-superpowers boundary (v0.11.1) — canonical declaration

**Single source of truth (v0.17.0 / S04 hoist).** Athanor's **Thin Leader** + **planner-classified discipline** applies across the 11 native Thin Leader skills (assess, analyze, debug, discuss, lfg, lfg-goal, plan, prompt-gen, review, setup, work). `superpowers:using-superpowers` is loaded at SessionStart via the Claude Code platform's system reminder channel (NOT via athanor's `hooks.json`). Its "ABSOLUTELY MUST invoke before response" / "1% chance → MUST use it" pressure is **advisory here** in native skill contexts — discovery resolves through **leader dispatch**, not pre-response invocation check. Carve-out: `scope-drift` and `verification-before-completion` keep their own vendored-content voice; `ce-test-browser` is non-Thin-Leader so the boundary is irrelevant. **Honesty label: advisory** — no runtime gate ships; matches the status-table row above. Regression lock: `tests/test_regression_v011_1_using_superpowers_boundary.py`. Each native skill carries a 2-line pointer (heading `### using-superpowers boundary` + 1-line "See CLAUDE.md …") rather than restating this prose. Concept adopted from superpowers v5.1.0 `sp-using-superpowers` (MIT, Jesse Vincent).

## Concept Absorption Surface (post-v0.12.0)

Previously titled §"Vendored Surface — Identity Guard Layer" through v0.10.0 → v0.11.8; v0.12.0 renames it post-cutover. v0.10.0 originally absorbed compound-engineering v3.8.3 (33 skills + 49 sub-agents) and superpowers v5.1.0 (13 skills) under `/athanor:ce-*` / `/athanor:sp-*`. **v0.10.0 plan-of-record misread the user's concept-absorption intent as wholesale plugin vendoring.** The v0.12.0 atomic cut closes the scope correction — 1 KEEP skill (`ce-test-browser`, D8) + 5 concepts absorbed as prose in athanor-native skills (reviewer personas, Iron Law debugging, requirements capture, skill-discovery preamble, doc-review mode). The 2 D12-retained sub-agents (`ce-git-history-analyzer`, `ce-repo-research-analyst`) were removed in v0.15.x (no live dispatch references confirmed at removal time). Full detail: `docs/archive/concept-absorption-surface.md`. Migration: `docs/v0.12.0-migration.md`. Retrospective: `docs/archive/v010-v011-vendoring-scope-correction.md`. Attribution ledger: NOTICE.md.

### Identity invariants (survive the cutover)

Four athanor identity commitments survive intact, upheld by native skill prose + regression locks:
1. **Thin Leader contract.** Leader never does implementation work directly.
2. **Cross-model adversarial planning.** `/athanor:plan` via `--depth=` tier dispatch (deep = Planner A + Planner B Codex cross-planning + synthesis Critic; standard default = A + Codex review + refinement Critic; lite = A only).
3. **Spec-then-TDD discipline.** `/athanor:work` Splitter `execution_note` + conjunction-of-three Phase 3 gate.
4. **Stop hook runtime gate.** `scripts/hooks/stop_verify_claims.py` fires on every Stop event (v0.10.0 vendor-aware whitelist scope; D11 preserved as general defensive coverage).

### Effort Level
Registered agents only — the 7 reference-doc roles set their tier in the skill's INLINE dispatch (e.g. Cleaner haiku), not frontmatter:
- Releaser / CI-watcher: highest (opus)
- Learner / Codex-dispatcher: standard (sonnet)

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
