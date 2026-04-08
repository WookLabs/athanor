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
| `/athanor:plan` | Plan | Cross-model adversarial planning + task splitting |
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
    discuss.md
    analyze.md
    plan.md
    work-log.md
    discoveries/
  athanor.json
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
