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
| Completion-Claim Verification (Stop hook) | **advisory (prompt-based)** — `hooks/hooks.json` Stop prompt fires on every Stop event; model self-classifies whether to invoke `verification-before-completion`. Plugin layer cannot force invocation. v0.7.8 upgrades to **enforced (command-based)** — see `docs/STATE.md` §"Command-hook Stop blocking spike (2026-05-18)". |
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

### Completion-Claim Verification (Stop hook — advisory, prompt-based)

On every `Stop` event, athanor injects a prompt asking the active model to
**self-classify** whether its preceding response contained a material claim
(edits/tests/releases/migrations/deployments/verification-output). If so,
the prompt asks the model to invoke the vendored
`verification-before-completion` skill to produce fresh evidence.

**Limitation:** This is a prompt nudge, not a runtime gate. The model decides
whether the classification applies. A determined model can rationalize past
the check ("my claim was just a tool-output summary, not material"). The
plugin layer cannot force skill invocation in v0.7.7 — Claude Code did not
expose a hook-can-block-Stop primitive at design time. The 2026-05-18 spike
confirmed `type: "command"` Stop hooks with exit 2 DO block Stop and feed
stderr back as continuation context (see `docs/STATE.md` §"Command-hook Stop
blocking spike (2026-05-18)"). v0.7.8 upgrades this gate to a real command
hook.

- **Skill source:** `skills/verification-before-completion/SKILL.md` (MIT, vendored)
- **Hook config:** `hooks/hooks.json` → Stop event, type `prompt`
- **Scope:** fires on every Stop event; the model self-identifies whether its preceding turn contained a **material claim** before invoking the skill. Explicitly skipped categories: analysis, planning, opinions, research Q&A, and tool-output summaries.

**What it catches:** Honest in-distribution turns where the model would benefit from being reminded to verify. The prompt is well-tuned (see `hooks/hooks.json` for the material-claim whitelist with Korean parity).

**What it does NOT catch:** Adversarial rationalization, novel claim phrasings outside the whitelist, or turns where the model decides the skill invocation is "obviously unnecessary." v0.7.8's command-hook upgrade addresses adversarial rationalization by gating at the runtime layer.

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
