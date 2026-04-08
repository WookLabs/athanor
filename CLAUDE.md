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

## Configuration

See `athanor.json` in project root. Key settings:
- `codex.enabled`: Codex cross-model planning (default: true)
- `work.defaultMode`: "solo" or "team"
- `cleaner.maxAgeDays`: Working memory retention (default: 7)
- `triggers.language`: "ko", "en", or "both"
