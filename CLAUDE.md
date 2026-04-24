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

## Defense Mechanisms

### Stop-Phrase Detection
Workers must NOT use these patterns. If detected in worker output, Leader flags it:
- "이 정도면 멈춰도 될 것 같습니다" / "I think we can stop here"
- "계속할까요?" / "Should I continue?"
- "기존 이슈입니다" / "This is a pre-existing issue"
- "새 세션에서 계속" / "Let's continue in a new session"
- "좋은 체크포인트" / "Good checkpoint"

If a worker uses stop-phrases, Leader should instruct: "Complete the task. Do not stop early."

### Read-Before-Edit Rule
Workers MUST read relevant files before editing. If a worker edits a file it hasn't read,
this indicates quality degradation. Leader should re-dispatch with explicit "read first" instruction.

### Completion-Claim Verification (Stop hook)

On every `Stop` event, athanor injects a prompt instructing the active model to
invoke the vendored `verification-before-completion` skill **if the turn contained a material claim (edits/tests/releases/migrations/deployments/verification-output)**; the prompt explicitly skips analysis, planning, opinions, research Q&A, and tool-output summaries. Enforced at plugin layer via `hooks/hooks.json`.

- Skill source: `skills/verification-before-completion/SKILL.md` (MIT, vendored)
- Hook config: `hooks/hooks.json` → Stop event, type `prompt`
- Scope: fires on every Stop event; the model self-identifies whether its preceding turn contained a **material claim** before invoking the skill. Explicitly skipped categories: analysis, planning, opinions, research Q&A, and tool-output summaries.

### Scope Drift Detection (on-demand skill)

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
