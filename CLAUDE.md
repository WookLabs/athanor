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
| `/athanor:discuss` | Plan | Decision brainstorming (Claude × Codex) |
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
