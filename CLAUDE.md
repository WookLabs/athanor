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
| `/athanor:discuss` | Plan | Decision brainstorming + intent clarification (dual mode: clarify ↔ synthesis). Step 1 asks the user to pick mode. clarify = single-Claude gap-probe dialog → `requirements.md`. synthesis = Researcher + Devil's Advocate + Critic → `discuss.md` (existing v0.7.x behavior). |
| `/athanor:analyze` | Plan | Parallel fast analysis (LSP, mem-search) |
| `/athanor:debug` | Plan | Triage → 병렬 실패 진단 (에러, git 이력, 코드 추적) |
| `/athanor:deep-plan` | Plan | Full adversarial planning (Claude + Codex 교차 검증) |
| `/athanor:plan` | Plan | **Cross-model adversarial planning** (Planner A Claude + Planner B Codex + Critic) — athanor identity #2. Post-v0.12.0: sole native planner. Install upstream compound-engineering for CE variant. |
| `/athanor:lite-plan` | Plan | Lightweight planning (Claude only, 리뷰 없음) |
| `/athanor:work` | Execute | **Spec-then-TDD discipline** (Splitter execution_note + conjunction-of-three Phase 3 gate) — athanor identity #3. Post-v0.12.0: sole native executor. Install upstream compound-engineering for CE variant. |
| `/athanor:review` | Plan | Parallel multi-lens code review (architecture, quality, security, performance, testing, documentation) |
| `/athanor:lfg` | Execute | **Standalone end-to-end pipeline** (v0.11.0) — wraps the LFG flow through athanor-native commands at identity-bearing steps (Step 1 `/athanor:plan` cross-model + Step 2 `/athanor:work` Spec-then-TDD + Step 3 `/athanor:review` 6-lens). Post-v0.12.0: sole pipeline (`/athanor:ce-lfg` removed). (v0.15.1: `--team` mode default) |
| `/athanor:lfg-goal` | Execute | **Goal-driven macro Ralph loop** (v0.13.0) — orchestration layer over existing 4 identity invariants (no new invariant per D11). Combines durable goal ledger + dispatched receipt-validator + adversarial 3-tier goal-completion check. |

### Vendored (post-v0.12.0 atomic cut — see §Concept Absorption Surface below)

- `/athanor:ce-test-browser` — sole CE skill retained (browser automation, no athanor-native equivalent, D8 KEEP). Originally v0.10.0 vendored 33 ce-* skills from compound-engineering v3.8.3; the v0.12.0 atomic cut removed 32 of them (3 LIFT-source concepts merged into native skills + 29 DROP). See `docs/archive/v010-v011-vendoring-scope-correction.md` for the plan-of-record misread retrospective.
- No `/athanor:sp-*` skills remain. Originally v0.10.0 vendored 13 sp-* skills from superpowers v5.1.0; the v0.12.0 atomic cut removed all 13 (2 LIFT-source concepts + 11 DROP).
- Naming policy (D2): athanor-native skills keep the unprefixed `/athanor:<name>` slot; the surviving `ce-test-browser` retains the `ce-` prefix.

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
    discuss.md               ← /athanor:discuss 결과
    research-a.md            ← intermediate (discuss)
    research-b.md            ← intermediate (discuss)
    analyze.md               ← /athanor:analyze 결과
    debug.md                 ← /athanor:debug 결과
    plan-a.md                ← plan A (standard approach)
    plan-b.md                ← plan B (alternative, deep tier only)
    review-of-a.md           ← review of plan A
    review-of-b.md           ← review of plan B (deep tier only)
    plan.md                  ← /athanor:plan 확정안 (Subtasks는 /athanor:work Step 0.5에서 생성)
    decisions.md             ← 확정 결정 로그 (/athanor:work Task Splitter가 기록)
    work-log.md              ← /athanor:work 진행 기록
    discoveries/             ← worker discovery briefs
  lessons/                   ← learned lessons (auto-managed)

athanor.json  ← project root, NOT inside .athanor/
```

## Session Lookup Convention

Skills that need to find "the active session" use these semantics. This is
the canonical rule; per-skill prose should reference this section rather than
restating semantics (drift between skills caused the v0.7.7 M4 finding).

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
| Completion-Claim Verification (Stop hook) | **enforced (command-based)** — `hooks/hooks.json` registers a `type: command` Stop hook invoking `scripts/hooks/stop_verify_claims.py`. The script reads the Stop event payload, detects material claims via: v0.7.7 English + Korean phrase whitelist; v0.10.2 NFKC unicode normalization + Cyrillic confusables fold + 6 verb-anchored paraphrase regex patterns; v0.10.2 vendor-aware whitelist extension (CE/superpowers idioms); v0.10.3 Greek+Armenian confusables fold extension; v0.10.3 conditional/speculative clause-prefix suppression; v0.10.3 attribution / paired-quote / attributed-verb suppression. Exits 2 to block Stop with stderr fed back as continuation context. The verification skill prefixes its output with `<!-- athanor:verification-emission v=2 nonce=... -->` so the hook detects its own evidence emission and exits 0 silently. `athanor.json` `hooks.profile: "off"` disables the gate per-project. **v0.10.3 coverage:** paraphrase ("CI is green"), Cyrillic/Greek/Armenian homoglyph, fullwidth, vendored CE/superpowers idioms — all detected. Conditional/speculative tense ("If all tests are green, merge") and attributed historical quotes (`the v0.7.6 docs said "tests pass"`) — both suppressed. Known residual (v0.11.0+): LLM-class semantic similarity; speculative tense without prefix marker; multi-paragraph quote spans; Cherokee/full-width-Latin confusables. v0.11.3 audit: see §"Completion-Claim Verification" detail section below for the v0.7.8 → v0.11.2 input-layer fail-open history. v0.11.4 plugin-root deployment fix: command now uses `${CLAUDE_PLUGIN_ROOT}` so the script reaches users in every project, not just athanor's source repo — see §"Completion-Claim Verification" detail section below for the v0.7.8 → v0.11.3 source-repo-only history. Spike evidence: `docs/STATE.md` §"Command-hook Stop blocking spike (2026-05-18)". |
| Stop-Phrase Detection | **advisory** — Leader-side prose guidance; spread across `skills/{work,discuss,analyze,debug,plan}/SKILL.md` Step 2.5 "Worker Output Defense"; not enforced by a code-level grep gate |
| Read-Before-Edit Rule | **advisory** — prose guidance; Claude Code runtime is the practical enforcer for Claude-based workers, but no plugin-layer guard for Codex/non-Claude workers |
| Scope Drift Detection | **on-demand** — `skills/scope-drift/SKILL.md` user-invoked only; no auto-fire on Stop or completion claims |
| Spec-then-TDD Discipline | **advisory (planner-classified)** — `/athanor:plan` Planner A 출력의 Verify 필드를 MUST/SHOULD bullets로 받고, `/athanor:work` Task Splitter가 각 subtask에 `execution_note` (spec-then-tdd / test-aware / direct) + `acceptance_criteria` 자동 할당. Executor가 분류에 따라 red-first 5단계 / 종료 게이트 (`tests/**` 수정 + `full_suite_passed: true` 자가보고 + verification line 일관성, 세 조건 conjunction) / 그대로 분기. RED 안 가는 경우 즉시 완료 아닌 **pending-then-gated** 처리 — Phase 3 게이트를 다시 통과해야 success로 마감. 메커니즘은 advisory — Stop hook 같은 runtime 강제는 없고 worker prompt + result 검증으로 운용. evidence shape 검증 (command/test_node_id/exit_code/output_tail) + 게이트 conjunction으로 가장 흔한 실수(RED 건너뛰기, full suite 미실행)는 잡지만 adversarial forgery (worker가 fields를 fabricate)는 못 잡음. **v0.10.0 scope:** discipline applies to athanor-native `/athanor:work` only. Vendored `/athanor:ce-work` and `/athanor:sp-test-driven-development` are OUTSIDE — users opt in by explicit invocation; CE/superpowers carry their own execution semantics. 운용 근거: `docs/STATE.md` §Current Phase. |
| using-superpowers boundary (v0.11.1) | **advisory (preamble-declared)** — `superpowers:using-superpowers` skill은 v0.10.0 vendoring으로 흡수되어 매 세션 시작 시 Claude Code platform이 제공하는 SessionStart system reminder channel (additional-context)로 로드된다 — 이것은 athanor의 hooks.json 등록 결과가 아니다 (athanor `hooks/hooks.json`은 Stop event만 등록; SessionStart는 platform mechanism이 skill body를 system reminder channel을 통해 자동 포함시키는 Claude Code platform 동작이며, athanor가 register하는 hook event가 아님). 그 skill의 "ABSOLUTELY MUST invoke before response" / "1% chance → MUST use it" 톤은 athanor-native **11 Thin Leader skill** (analyze, debug, deep-plan, discuss, lfg, lfg-goal, lite-plan, plan, review, setup, work) 호출 context에서는 **advisory**다 (v0.13.0 추가: lfg-goal). 이 영역에서는 discovery가 leader dispatch로 해소된다 (Thin Leader pattern + planner-classified discipline) — pre-response invocation check은 native context에서 advisory 안내일 뿐 강제 아님. 본 boundary는 11 skill 각각의 §Identity 직후 `### v0.11.1 using-superpowers boundary` subsection에 동일 문구로 인라인 선언됨; 회귀는 `tests/test_regression_v011_1_using_superpowers_boundary.py`로 lock. **scope (intentional carve-outs):** (a) `scope-drift` 와 `verification-before-completion`는 unprefixed slot을 차지하나 Thin Leader 패턴이 아닌 vendored-content skill — 자체 body voice 유지 (T2 modification 최소화); (b) sp-* 13 skill은 superpowers 출신이라 자연 정합 (carve-out 불필요); (c) ce-* 33 skill은 별도 voice (boundary 무관). vendored `skills/sp-using-superpowers/SKILL.md` body는 T2 lock — 편집 금지 (drift script로 enforced). runtime gate 추가 없음 — "advisory" 라벨 honesty 회귀 잠금. Concept adopted from superpowers v5.1.0 sp-using-superpowers (MIT, Jesse Vincent). Source: https://github.com/obra/superpowers |

Detail follows.

### Stop-Phrase Detection (advisory)
Workers must NOT use these patterns. If detected in worker output, Leader flags it:
- "이 정도면 멈춰도 될 것 같습니다" / "I think we can stop here"
- "계속할까요?" / "Should I continue?"
- "기존 이슈입니다" / "This is a pre-existing issue"
- "새 세션에서 계속" / "Let's continue in a new session"
- "좋은 체크포인트" / "Good checkpoint"

If a worker uses stop-phrases, Leader should instruct: "Complete the task. Do not stop early."

### Read-Before-Edit Rule (advisory)
Workers MUST read relevant files before editing. If a worker edits a file it hasn't read,
this indicates quality degradation. Leader should re-dispatch with explicit "read first" instruction.
Note: Claude Code runtime enforces read-before-edit on Claude-based workers automatically;
this rule still matters for Codex-based dispatches and other non-Claude runtimes.

### Completion-Claim Verification (Stop hook — enforced, command-based)

On every `Stop` event, Claude Code invokes `scripts/hooks/stop_verify_claims.py`
(registered as `type: command` in `hooks/hooks.json`) with the Stop event
JSON on stdin. The script:

1. Reads the payload; extracts `last_assistant_message`. Fail-open on
   missing/unparseable stdin.
2. Reads `hooks.profile` from `athanor.json`. If `"off"`, exits 0 silently
   — the user has opted out of the runtime gate.
3. Checks whether the response begins with the emission sentinel
   `<!-- athanor:verification-emission v=2 nonce=<32-hex> -->` (anchored at
   the first non-whitespace line). If yes, exits 0 silently to prevent
   re-entry on the verification skill's own output.
4. Greps the response body for material-claim phrases (English + Korean,
   whitelist ported verbatim from the v0.7.7 prompt). On no match, exits 0.
5. On match, exits 2 with stderr directing the model to invoke the
   `verification-before-completion` skill. Claude Code feeds the stderr
   back to the model as continuation context; the model must produce
   fresh evidence before Stop succeeds.

**Spike evidence:** the 2026-05-18 dry-run confirmed Claude Code honors
`exit 2` from `type: command` Stop hooks (the user's intended next message
never reached the model; instead the model received the stderr as system
feedback). Full result in `docs/STATE.md` §"Command-hook Stop blocking
spike (2026-05-18)".

**Re-entry prevention:** the `verification-before-completion` skill is now
contractually required to prefix every response with the v=2 nonce-bound
sentinel (`<!-- athanor:verification-emission v=2 nonce=<32-hex> -->`; see
`skills/verification-before-completion/SKILL.md` §"Emission Sentinel"). The
hook script matches the sentinel anchored at response-start (line 1,
optional leading whitespace). Sentinels on line 2 or later do NOT count —
that's the brittleness trade-off documented in the skill.

**Per-project opt-out:** set `"hooks": {"profile": "off"}` in `athanor.json`
to disable the gate. The script exits 0 unconditionally; no claim detection
runs. `"standard"` (default) is the only other supported value;
`lenient` / `strict` are deferred to a future release.

#### Stop hook v0.11.3 input-layer fix (post-mortem)

For 5 release cycles (v0.7.8 → v0.11.2), the script's stdin parser assumed
the Stop event payload contained `last_assistant_message: <string>`. Claude
Code actually sends `transcript_path: <jsonl-path>` and the message lives
inside that file. Every Stop event silently fail-opened (`exit 0` with stderr
`"last_assistant_message missing or non-string"`). The 35+ existing tests in
`tests/test_regression_stop_hook_script.py` used the same incorrect assumed
payload shape, so they passed while production fail-opened.

v0.11.3 introduces `_read_last_assistant_message()` and `_content_to_text()`
in `scripts/hooks/stop_verify_claims.py`. The new parser accepts BOTH the
legacy shape (preserves the 35+ existing tests as a backwards-compat lock)
AND the real Claude Code shape (`transcript_path` → JSONL → reverse-scan
to the first main-session `entry.type == "assistant"` with `isSidechain
!= true` → join `text` blocks from `message.content`). Sub-agent assistant
turns are skipped so only the main-session model response gates. The
`stop_hook_active` flag is pass-through; re-entry semantics remain governed
by the existing `hook_state` circuit breaker per v0.7.9 design.

The detection logic shipped in v0.7.9 (nonce sentinel), v0.10.2 (paraphrase
regex + NFKC + Cyrillic fold + vendor-aware whitelist), and v0.10.3 (Greek/
Armenian fold + conditional-tense suppression + attribution skip) is
code-correct and unchanged; it was simply unreachable in production until
v0.11.3 fixed the input layer. The `**enforced (command-based)**` label
in the status table above is now honest.

`tests/test_regression_v011_3_stop_hook_input_layer.py` adds 25 mandatory +
1 xfail-tolerant tests against the real Claude Code payload shape. The
2026-05-18 dry-run spike documented in `docs/STATE.md` confirmed `exit 2`
behavior but did not validate the stdin parsing path (it tested the gate
by manually piping JSON, which masked the production gap).

Scope note (added v0.11.4): the v0.11.3 fix above was reachable only in
athanor's source repo until v0.11.4's `${CLAUDE_PLUGIN_ROOT}` path fix —
see §"Stop hook v0.11.4 plugin-root deployment fix (post-mortem)" below.

- **Skill source:** `skills/verification-before-completion/SKILL.md` (MIT, vendored)
- **Hook config:** `hooks/hooks.json` → Stop event, type `command` → `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/hooks/stop_verify_claims.py"` (plugin-root expansion since v0.11.4; bare relative path in v0.7.8 → v0.11.3 was the deployment-path bug)
- **Detection scope:** material claims (edits applied / files
  created-removed-renamed / tests passing-failing / lint-typecheck clean /
  builds succeeding / bug fixed / requirements met / releases shipped /
  migrations completed / deployments succeeded / agent task completed /
  verification output) — English + Korean phrase whitelist. Explicitly
  skipped (no exit 2): pure analysis, planning, design, opinions, research
  Q&A, tool-output summaries that don't assert work status.

**What it catches:** material-claim turns without fresh evidence — the
model must invoke the verification skill before Stop succeeds. Adversarial
rationalization that previously bypassed the v0.7.7 prompt nudge now hits
a runtime exit-2 gate.

**What it does NOT catch:** material claims phrased outside the whitelist
(false negative — the whitelist mirrors v0.7.7's well-tuned set; expand
deliberately, not greedily), or quoted historical references that contain
trigger phrases (e.g., "the v0.7.6 docs claimed 'tests pass'"). Sentence-
level attributed-history detection was originally promised as v0.8.0+ work
but shipped in v0.10.3 R3 (attribution / paired-quote / attributed-verb
suppression in `stop_verify_claims.py`); residual semantic-similarity and
multi-paragraph quote-span detection is deferred to v0.11.8+. Users
encountering false positives can set `profile: "off"` as the escape hatch.

#### Stop hook v0.11.4 plugin-root deployment fix (post-mortem)

The v0.11.3 input-layer fix was correct in code but only reachable when
Claude Code resolved the hook command relative to athanor's own source
repo. The hook command in `hooks/hooks.json` was registered with a
bare relative path (`python3 scripts/hooks/stop_verify_claims.py`)
which CC resolves relative to the user's PROJECT cwd, not the plugin
install dir. For any user with athanor installed user-scope but
working in another project, CC would fail to find the script and exit
2 with stderr `python3: can't open file '<project>/scripts/hooks/
stop_verify_claims.py'`. CC treats that stderr pattern as
"hook script missing" — non-blocking — so the gate was silently
absent in every project except athanor's source repo from v0.7.8
through v0.11.3 inclusive.

v0.11.4 closes the deployment-path arc. `hooks/hooks.json` now uses
`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/hooks/stop_verify_claims.py"`
— the env var `${CLAUDE_PLUGIN_ROOT}` is set by Claude Code for plugin
hooks and expands to the plugin install path. This matches the
industry pattern used by `superpowers`, `claude-mem`, and `openai-codex`
plugin hook registrations. The v0.11.3 input-layer fix and the v0.11.4
deployment-path fix are companion-fixes of the same latent bug arc —
script wrong (closed v0.11.3) + path wrong (closed v0.11.4). The
shared meta-cause: manual testing only inside athanor's source repo
hid both bugs simultaneously.

`tests/test_regression_stop_command_hook.py::test_stop_hook_command_uses_plugin_root_or_absolute_path`
locks the invariant — bare relative paths in the Stop hook command
string will fail this test post-v0.11.4.

The detection layers shipped in v0.7.9 / v0.10.2 / v0.10.3 + v0.11.3
input-layer fix are unchanged and now actually reach every project
where athanor is installed.

### Scope Drift Detection (on-demand skill — advisory)

Use the `scope-drift` skill on demand to compare current changes against the canonical plan-of-record (glob: `[plan.md > deep-plan.md > lite-plan.md]` in latest `.athanor/sessions/<id>/`). Pilot wiring = on-demand only; no automatic invocation.

- Skill source: `skills/scope-drift/SKILL.md` (MIT, vendored from claude-octopus)
- Trigger: user-invoked ("check scope drift", "scope check", "did I drift", "drifted from plan", "still on track", "off-track", "스코프 드리프트 체크", "스코프 체크", "드리프트 확인", "계획 벗어났나")
- Self-reference exclusion: `.athanor/sessions/**/*`, `.athanor/lessons/**/*`, `.athanor/discoveries/**/*`

### Spec-then-TDD Discipline (advisory — planner-classified)

Subtask 단위로 Spec-then-TDD를 자동 적용. 메커니즘 분기:
- **분류** (`execution_note`): `/athanor:work` Task Splitter가 각 subtask를
  `spec-then-tdd | test-aware | direct` 중 하나로 분류 (heuristic in
  `skills/work/SKILL.md` Step 0.5 Rules block):
  - source code modification + 새 동작/계약 → `spec-then-tdd`
  - source code modification + 기존 동작 보존 (refactor) → `test-aware`
  - prose-only (`.md`, `_doc`, CHANGELOG) → `direct`
- **spec-then-tdd**: red-first 5단계 (test write → run RED → implement → run
  GREEN → next criterion). Worker가 per-criterion `red_evidence` (command,
  test_node_id, exit_code, output_tail) 보고 + `tests_modified` /
  `test_paths_touched` / `full_suite_passed` 자가보고. Leader가 evidence
  shape 검증 후 RED 안 갔으면 `test-aware`로 **pending-downgrade** —
  Phase 3 게이트 (conjunction of three signals)를 다시 통과해야 success.
- **test-aware**: 종료 게이트 — 세 조건의 conjunction: (1) `git diff --name-only`
  결과에 `tests/**` path가 1개 이상 포함 (test_*.py, conftest.py, fixtures/,
  snapshot 모두 허용), (2) worker가 `full_suite_passed: true`로 자가보고
  (즉 `pytest tests/`를 실행해 exit 0을 봤다고 주장), (3) `verification:`
  자유형 prose가 (2)와 일관. 셋 중 하나라도 빠지면 게이트 fail.
- **direct**: 현재 athanor 동작 그대로 (doc/config-only edits).

**What it catches:** 새 동작 도입하는 subtask에서 "tests are afterthought" 패턴.
RED 단계 자체를 건너뛰는 worker는 evidence shape 누락으로 잡힘 (다음 단락 참고).

**What it does NOT catch:** Splitter의 오분류 (false-positive: prose-only를
spec-then-tdd로; false-negative: behavior를 direct로). Worker가 evidence를
fabricate (실제 RED를 본 적 없으면서 만들어낸 command/exit_code 보고)하면
잡히지 않음 — leader는 evidence의 *shape*만 검증하며 *진실성*은 검증 불가.
adversarial forgery 차단 (runtime 강제, transcript-event introspection)은
v0.8.1+ 후보 (verification-before-completion skill 확장).

**Per-project opt-out:** 본 메커니즘은 advisory이므로 별도 `athanor.json`
플래그 없음. plan.md를 수동 편집해 `execution_note: direct`로 강제하거나
`<!-- athanor:subtasks:manual -->` 마커로 Splitter를 우회 가능.

- **Splitter prompt:** `skills/work/SKILL.md` Step 0.5 (Rules per subtask + Output Format)
- **Dispatch packet:** `skills/work/SKILL.md` Step 2a §"Execution Instructions"
  (3-branch conditional on execution_note)
- **Result handler:** `skills/work/SKILL.md` Step 2b §"v0.8.0 Spec-then-TDD result handler"
- **Critic rubric:** `skills/plan/SKILL.md` Step 4 §"v0.8.0 Critic Rubric"
- **Honesty arc:** v0.7.7~v0.7.9의 advisory/enforced 라벨 정직성 약속 유지.
  본 작업은 "advisory (planner-classified)" — runtime 강제 없음 명시.

## Concept Absorption Surface (post-v0.12.0)

This section was previously titled §"Vendored Surface — Identity Guard
Layer" through v0.10.0 → v0.11.8. v0.12.0 renames it to reflect the
post-cutover reality: the wholesale vendored surface is gone; what
remains is a 5-concept absorption inventory + 1 KEEP skill + 2 KEEP
sub-agents.

athanor v0.10.0 originally absorbed **compound-engineering v3.8.3**
(33 skills + 49 sub-agents) and **superpowers v5.1.0** (13 skills) under
the `/athanor:ce-*` and `/athanor:sp-*` namespaces. **v0.10.0
plan-of-record misread the user's concept-absorption intent as wholesale
plugin vendoring.** v0.12.0 atomic cut closes the scope correction —
surface reduced from 95 items down to 3 (97%): 1 KEEP skill +
2 KEEP sub-agents, plus 5 concepts absorbed as prose subsections in
athanor-native skills. See
`docs/archive/v010-v011-vendoring-scope-correction.md` for the full
retrospective and `docs/v0.12.0-migration.md` for the user-facing
migration guide.

### Retained vendored items

**1 retained skill** (D8):

- `/athanor:ce-test-browser` — user opt-in UI browser automation
  (compound-engineering v3.8.3). Non-identity but real utility; T2
  provenance block preserved.

**2 retained sub-agents** (D12) under `agents/vendored/ce/`:

- `ce-git-history-analyzer.agent.md` — generic git-history discovery
  dispatch target.
- `ce-repo-research-analyst.agent.md` — generic repo-research discovery
  dispatch target.

### 5 concepts absorbed as native prose (NOT vendored directories)

The following upstream concepts have been lifted into athanor-native
skills with full MIT attribution preserved. Each entry cross-links to
NOTICE.md §"Concepts adopted from upstream" for the canonical attribution
ledger.

1. **Reviewer-persona vocabulary** — from `ce-code-review@3.8.3` (MIT,
   Kieran Klaassen / Every Inc) into `skills/review/SKILL.md` §"Personas".
   See NOTICE.md §"Concepts adopted from upstream" entry #1.
2. **Iron Law + Four Phases (debugging discipline)** — from
   `sp-systematic-debugging@5.1.0` (MIT, Jesse Vincent) into
   `skills/debug/SKILL.md` §"Systematic Debugging Discipline". See NOTICE.md
   §"Concepts adopted from upstream" entry #2.
3. **Requirements capture (R-ID / A-ID / F-ID / AE-ID)** — from
   `ce-brainstorm@3.8.3` (MIT, Kieran Klaassen / Every Inc) into
   `skills/discuss/references/requirements-capture.md` (v0.9.0
   absorption; v0.12.0 attribution formalized). See NOTICE.md §"Concepts
   adopted from upstream" entry #3.
4. **Skill-discovery preamble** — from `sp-using-superpowers@5.1.0` (MIT,
   Jesse Vincent) into CLAUDE.md §"using-superpowers boundary (v0.11.1)".
   See NOTICE.md §"Concepts adopted from upstream" entry #4.
5. **Doc-review persona mode** — from `ce-doc-review@3.8.3` (MIT, Kieran
   Klaassen / Every Inc) into `skills/review/SKILL.md` §"Doc review mode".
   See NOTICE.md §"Concepts adopted from upstream" entry #5.

### Removed in v0.12.0

The atomic cut removed **45 skill directories** + **47 sub-agents** under
the vendored namespaces. Full enumeration lives in NOTICE.md §"Removed in
v0.12.0" + `docs/v0.12.0-migration.md` (user-facing migration table).
Summary grouped by source plugin:

**compound-engineering v3.8.3 — originally 33 ce-* skill directories, 32 removed at v0.12.0** (3
LIFT-source + 29 DROP; `ce-test-browser` carved out per D8):

- LIFT-source (concept absorbed into native skills): `ce-code-review`,
  `ce-doc-review`, `ce-brainstorm`.
- DROP (no athanor-native migration target — install upstream
  compound-engineering if needed): `ce-agent-native-architecture`,
  `ce-agent-native-audit`, `ce-clean-gone-branches`, `ce-commit`,
  `ce-commit-push-pr`, `ce-compound`, `ce-compound-refresh`, `ce-debug`,
  `ce-demo-reel`, `ce-dhh-rails-style`, `ce-frontend-design`,
  `ce-gemini-imagegen`, `ce-ideate`, `ce-lfg` (D9 full DROP),
  `ce-optimize`, `ce-plan` (D9 full DROP), `ce-polish-beta`,
  `ce-product-pulse`, `ce-proof`, `ce-resolve-pr-feedback`,
  `ce-riffrec-feedback-analysis`, `ce-sessions`, `ce-simplify-code`,
  `ce-slack-research`, `ce-strategy`, `ce-test-xcode`, `ce-work` (D9
  full DROP), `ce-work-beta`, `ce-worktree`.

**superpowers v5.1.0 — originally 13 sp-* skill directories, all removed at v0.12.0** (2
LIFT-source + 11 DROP):

- LIFT-source (concept absorbed into native skills): `sp-systematic-debugging`,
  `sp-using-superpowers`.
- DROP (install upstream superpowers if needed):
  `sp-brainstorming`, `sp-dispatching-parallel-agents`,
  `sp-executing-plans`, `sp-finishing-a-development-branch`,
  `sp-receiving-code-review`, `sp-requesting-code-review`,
  `sp-subagent-driven-development`, `sp-test-driven-development`,
  `sp-using-git-worktrees`, `sp-writing-plans`, `sp-writing-skills`.

**compound-engineering sub-agents — originally 49, with 47 removed at v0.12.0** under
`agents/vendored/ce/`. 2 retained per D12 above (`ce-git-history-analyzer`,
`ce-repo-research-analyst`); the remaining 47 `*.agent.md` files removed
together (no athanor-native dispatch target relies on them post-cutover).

### Identity guard layer (what survives the cutover)

The four athanor identity commitments survive the v0.12.0 cutover intact.
Post-cutover the surface is much smaller (1 KEEP skill + 2 KEEP sub-agents
+ 5 absorbed concept prose subsections); the identity commitments are
upheld by *native skill prose + regression locks* — namespace defense is
no longer needed because the inflated vendored namespace was removed:

1. **Thin Leader contract.** The athanor leader (main session) NEVER does
   implementation work directly. It dispatches clean-context workers and
   presents results. The post-v0.12.0 surface is athanor-native + 1 KEEP
   skill + 2 KEEP sub-agents — the wholesale vendored namespace that
   previously required guard prose against agent-direct voice is gone.
2. **Cross-model adversarial planning stays athanor-native.** `/athanor:plan`
   dispatches Planner A (Claude) + Planner B (Codex) + Critic per
   v0.7.x~v0.9.0. CE's single-agent planning skill (`ce-plan`) was DROPped
   per D9; users wanting CE's flow install the upstream compound-engineering
   plugin.
3. **Spec-then-TDD discipline stays athanor-native.** `/athanor:work`
   applies Splitter `execution_note` classification + conjunction-of-three
   Phase 3 gate. CE's execution skill (`ce-work`) and superpowers'
   test-driven-development skill (`sp-test-driven-development`) were
   DROPped at v0.12.0 (D9 + DROP-class respectively); users wanting those
   flows install the upstream plugins directly.
4. **Stop hook runtime gate scope.** The Stop hook
   (`scripts/hooks/stop_verify_claims.py`) triggers on every `Stop` event
   regardless of which skill produced the turn output. Per D11 the
   v0.10.2 vendor-aware whitelist extension (18 idioms + paraphrase regex
   layer + Cyrillic / Greek / Armenian homoglyph fold) is preserved with
   rationale re-framed to **general defensive coverage**: those idioms +
   normalizations apply broadly to English / Korean material-claim
   phrasing and are not vendored-prose-specific. The companion-fix arc
   5 layers (v0.11.3 input parser → v0.11.4 plugin-root path → v0.11.5
   doc drift → v0.11.6 sentinel body hash → v0.11.7 scanner extension +
   B1 minimal) survive the cutover intact (D10). Honesty residuals
   (v0.11.8+): LLM-class semantic similarity, conditional / speculative
   tense without prefix marker, multi-paragraph quote spans,
   Cherokee / full-width-Latin homoglyphs.

### Vendor manifest (post-v0.12.0)

- Source plugins (origin attribution preserved):
  `compound-engineering@3.8.3`
  (https://github.com/EveryInc/compound-engineering-plugin),
  `superpowers@5.1.0` (https://github.com/obra/superpowers).
- Vendor pattern: T2 (per `docs/DEPENDENCIES.md` §Tier ordering).
- Layout (post-v0.12.0): `skills/ce-test-browser/` (1 KEEP) at depth 1
  under `skills/`; 2 sub-agents at `agents/vendored/ce/*.agent.md`.
  No `skills/ce-*` or `skills/sp-*` directories beyond `ce-test-browser`
  exist.
- Concept-absorption inventory (5 LIFT entries): NOTICE.md §"Concepts
  adopted from upstream"; per-concept inventory under `concepts/*.md`.
- Drift check process: `scripts/check_vendor_drift.py` (since v0.10.1)
  walks the present skill tree, so it naturally iterates the post-cutover
  surface.

### What the post-v0.12.0 surface does NOT do

- Does NOT carry a wholesale vendored namespace. Users who need
  upstream CE or superpowers skills install those plugins directly
  (`docs/v0.12.0-migration.md` documents the path).
- Does NOT re-license athanor (athanor stays MIT; CE and superpowers
  stay MIT under their copyright holders).
- Does NOT deprecate any athanor-native skill in favour of a vendored
  variant.
- Does NOT auto-install upstream plugins as dependencies. athanor
  stands alone.

### Effort Level
- Planner and Critic agents: always use highest reasoning effort
- Executor and Analyst: standard effort is sufficient
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
