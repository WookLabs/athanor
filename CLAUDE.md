# Athanor

General-purpose agentic workflow orchestrator plugin for Claude Code.

## Core Principle

**Thin Leader**: The leader (main session) NEVER does work directly.
It only parses input, dispatches to clean-context workers, and presents results.
All file reading, analysis, code writing, and execution happens in worker agents.

## Commands

| Command | Mode | Purpose |
|---------|------|---------|
| `/athanor:setup` | — | Infrastructure health check and configuration |
| `/athanor:discuss` | Plan | Decision brainstorming + intent clarification (dual mode: clarify ↔ synthesis). Step 1 asks the user to pick mode. clarify = single-Claude gap-probe dialog → `requirements.md`. synthesis = Researcher + Devil's Advocate + Critic → `discuss.md` (existing v0.7.x behavior). |
| `/athanor:analyze` | Plan | Parallel fast analysis (LSP, mem-search) |
| `/athanor:debug` | Plan | Triage → 병렬 실패 진단 (에러, git 이력, 코드 추적) |
| `/athanor:deep-plan` | Plan | Full adversarial planning (Claude + Codex 교차 검증) |
| `/athanor:plan` | Plan | Standard planning + Codex review (default) |
| `/athanor:lite-plan` | Plan | Lightweight planning (Claude only, 리뷰 없음) |
| `/athanor:work` | Execute | TodoList grinding with ralph-loop |
| `/athanor:review` | Plan | Parallel multi-lens code review (architecture, quality, security, performance, testing, documentation) |

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
   > create a new session manually or wait for the --new-session flag (v0.8.0).`
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
| Completion-Claim Verification (Stop hook) | **enforced (command-based)** — `hooks/hooks.json` registers a `type: command` Stop hook invoking `scripts/hooks/stop_verify_claims.py`. The script reads the Stop event payload, detects material claims via the v0.7.7-derived English + Korean phrase whitelist, and exits 2 to block Stop with stderr fed back to the model as continuation context. The verification skill prefixes its output with `<!-- athanor:verification-emission v=1 -->` so the hook detects its own evidence emission and exits 0 silently (no re-entry loop). `athanor.json` `hooks.profile: "off"` disables the gate per-project. Spike evidence: `docs/STATE.md` §"Command-hook Stop blocking spike (2026-05-18)". |
| Stop-Phrase Detection | **advisory** — Leader-side prose guidance; spread across `skills/{work,discuss,analyze,debug,plan}/SKILL.md` Step 2.5 "Worker Output Defense"; not enforced by a code-level grep gate |
| Read-Before-Edit Rule | **advisory** — prose guidance; Claude Code runtime is the practical enforcer for Claude-based workers, but no plugin-layer guard for Codex/non-Claude workers |
| Scope Drift Detection | **on-demand** — `skills/scope-drift/SKILL.md` user-invoked only; no auto-fire on Stop or completion claims |
| Spec-then-TDD Discipline | **advisory (planner-classified)** — `/athanor:plan` Planner A 출력의 Verify 필드를 MUST/SHOULD bullets로 받고, `/athanor:work` Task Splitter가 각 subtask에 `execution_note` (spec-then-tdd / test-aware / direct) + `acceptance_criteria` 자동 할당. Executor가 분류에 따라 red-first 5단계 / 종료 게이트 (`tests/**` 수정 + `full_suite_passed: true` 자가보고 + verification line 일관성, 세 조건 conjunction) / 그대로 분기. RED 안 가는 경우 즉시 완료 아닌 **pending-then-gated** 처리 — Phase 3 게이트를 다시 통과해야 success로 마감. 메커니즘은 advisory — Stop hook 같은 runtime 강제는 없고 worker prompt + result 검증으로 운용. evidence shape 검증 (command/test_node_id/exit_code/output_tail) + 게이트 conjunction으로 가장 흔한 실수(RED 건너뛰기, full suite 미실행)는 잡지만 adversarial forgery (worker가 fields를 fabricate)는 못 잡음. 운용 근거: `docs/STATE.md` §Current Phase. |

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
   `<!-- athanor:verification-emission v=1 -->` (anchored at the first
   non-whitespace line). If yes, exits 0 silently to prevent re-entry on
   the verification skill's own output.
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
contractually required to prefix every response with the v=1 sentinel
(see `skills/verification-before-completion/SKILL.md` §"Emission Sentinel").
The hook script matches the sentinel anchored at response-start (line 1,
optional leading whitespace). Sentinels on line 2 or later do NOT count —
that's the brittleness trade-off documented in the skill.

**Per-project opt-out:** set `"hooks": {"profile": "off"}` in `athanor.json`
to disable the gate. The script exits 0 unconditionally; no claim detection
runs. `"standard"` (default) is the only other supported value;
`lenient` / `strict` are deferred to a future release.

- **Skill source:** `skills/verification-before-completion/SKILL.md` (MIT, vendored)
- **Hook config:** `hooks/hooks.json` → Stop event, type `command` → `scripts/hooks/stop_verify_claims.py`
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
level attributed-history detection is v0.8.0+ work. Users encountering
false positives can set `profile: "off"` as the escape hatch.

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
