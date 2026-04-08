# Athanor

> The alchemist's self-sustaining furnace — a workflow orchestrator that grows smarter with use.

Athanor is a Claude Code plugin that provides **5 workflow commands** instead of 100 features. It uses a **thin-leader architecture** where the main session never does work directly — all tasks are dispatched to clean-context worker agents.

## Key Feature: Cross-Model Adversarial Planning

Two independent planners create competing plans, cross-review each other's work, and a critic synthesizes the best elements. This produces higher-quality plans than any single model can achieve alone.

```
         ┌── Planner A (standard) ──→ Reviewer B ──┐
Input ───┤                                          ├── Critic → Final Plan
         └── Planner B (contrarian) ──→ Reviewer A ──┘
```

## Install

```bash
git clone https://github.com/WookLabs/athanor.git
claude --plugin-dir /path/to/athanor          # macOS/Linux
claude --plugin-dir C:\path\to\athanor        # Windows
```

Then run `/athanor:setup` to verify your environment.

## Commands

| Command | Mode | What it does |
|---------|------|-------------|
| `/athanor:setup` | — | Health check and configuration |
| `/athanor:discuss` | Plan | Decision brainstorming with multiple perspectives |
| `/athanor:analyze` | Plan | Parallel fast analysis (multiple workers) |
| `/athanor:plan` | Plan | Cross-model adversarial planning + task splitting |
| `/athanor:work` | Execute | TodoList grinding until all tasks complete |

### Workflow

```
/athanor:discuss  →  /athanor:analyze  →  /athanor:plan  →  /athanor:work
   "What?"              "Where?"             "How?"            "Do it."
   (brainstorm)         (analyze)            (plan)            (execute)
```

Everything before `/athanor:work` is **Plan Mode** — no files are modified. Execution mode begins only after you confirm the plan.

## Architecture

### Thin Leader Pattern

The leader (main session) **never** reads files, analyzes code, or writes code. It only:

1. Parses user input
2. Dispatches worker agents
3. Collects result briefs
4. Presents output to user

This keeps the leader's context clean regardless of session length.

### Worker Agents

| Agent | Model | Role |
|-------|-------|------|
| researcher | sonnet | Brainstorming research |
| analyst | sonnet | Fast parallel analysis |
| planner | opus | Implementation planning |
| critic | opus | Plan synthesis and review |
| executor | sonnet | Code execution with verification loop |
| learner | sonnet | Session learning extraction |
| cleaner | haiku | Memory decay and cleanup |

### Session Communication

All inter-stage communication uses `.md` files in `.athanor/sessions/{id}/`:

```
.athanor/
├── sessions/
│   └── 2026-04-08-001/
│       ├── discuss.md          ← brainstorming results
│       ├── analyze.md          ← analysis report
│       ├── plan-claude.md      ← Plan A
│       ├── plan-codex.md       ← Plan B (contrarian)
│       ├── review-of-claude.md ← Review of Plan A
│       ├── review-of-codex.md  ← Review of Plan B
│       ├── plan.md             ← Final merged plan + subtasks
│       ├── decisions.md        ← Decision log
│       ├── work-log.md         ← Execution progress
│       └── discoveries/        ← Worker findings
└── lessons/                    ← learned lessons (auto-managed)
    └── work-2026-04-08-001.md
```

### Learning System

After each `/athanor:work` session:

1. **Learner** analyzes results and extracts structured lessons
2. **Cleaner** applies memory decay (age + access count)
3. Future workers automatically read relevant lessons

Lessons use a 2-tier model:
- **Permanent**: Architecture decisions, critical patterns — never deleted
- **Working**: Task-specific details — auto-cleaned after decay period

## Configuration

`athanor.json` at project root:

| Key | Default | Description |
|-----|---------|-------------|
| `codex.enabled` | `true` | Enable cross-model planning with Codex |
| `work.defaultMode` | `"solo"` | Default execution mode (`solo` or `team`) |
| `work.ralphLoop.maxRetries` | `5` | Max verification retries per subtask |
| `work.circuitBreaker.consecutiveFailures` | `3` | Failures before circuit breaker trips |
| `team.waveSize` | `3` | Max parallel workers per wave |
| `memory.decayDays` | `7` | Working memory retention period |
| `memory.promotionThreshold` | `5` | Access count for auto-promotion to permanent |
| `triggers.language` | `"both"` | Trigger language (`ko`, `en`, or `both`) |

## Execution Modes

### Solo (`--solo`)
Sequential execution. One subtask at a time, each in a clean context.

### Team (`--team`)
Wave-based parallel execution. Subtasks grouped by dependency, each wave runs in parallel with discovery relay between waves.

```
Wave 1: [task 1, task 2]  ← parallel, no dependencies
  ↓ discovery relay
Wave 2: [task 3]          ← depends on wave 1
  ↓ discovery relay
Wave 3: [task 4]          ← depends on wave 2
```

## Design Philosophy

- **5 commands, not 100 features** — focused workflow, not feature collection
- **Thin leader** — leader context never grows, workers get clean starts
- **Cross-model adversarial** — competing perspectives produce better plans
- **Grow with use** — lessons accumulate, future sessions benefit
- **Plan before execute** — explicit mode separation prevents accidental changes

## Docs

- [DESIGN.md](docs/DESIGN.md) — Architecture and design decisions
- [CONVENTIONS.md](docs/CONVENTIONS.md) — Dispatch, session, and lesson conventions
- [ROADMAP.md](docs/ROADMAP.md) — Implementation roadmap
- [STATE.md](docs/STATE.md) — Current implementation state

## License

MIT
