# Athanor

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude_Code-plugin-blueviolet.svg)](https://claude.ai/code)

> The alchemist's self-sustaining furnace — a workflow orchestrator that grows smarter with use.

**8 commands. Clean-context workers. 3-tier adversarial planning. Sessions that compound.**

## Why Athanor Exists

**Without Athanor**, your Claude Code session is a single brain trying to hold everything at once — the analysis, the plan, the implementation, and quality checks. Context fills up. Quality degrades. When you ask for a plan, the same model that writes code also evaluates it — no second opinion.

**With Athanor**, the main session never touches a file. It dispatches work to clean-context specialists — a researcher who brainstorms, a planner who architects, a critic who cross-reviews, an executor who implements with verification loops. By default, a single planner gets cross-model review from Codex. In deep mode, two independent planners compete and cross-review each other. Lessons from every session compound — future workers start smarter than the last.

Other tools give Claude more skills. Athanor gives Claude a **team**.

## Quick Start

**Prerequisites:** [Claude Code](https://claude.ai/code)

In Claude Code:

```
/plugin marketplace add WookLabs/athanor
/plugin install athanor@athanor
/athanor:setup
```

Then try it:
```
/athanor:discuss "Add user authentication — OAuth vs session-based?"
```

<details>
<summary><b>For local development</b></summary>

```bash
git clone https://github.com/WookLabs/athanor.git
claude --plugin-dir /path/to/athanor
```

</details>

## See It Work

```
You:     /athanor:discuss "Add a caching layer for the API"

         [dispatches researcher + devil's advocate in parallel]

         Researcher: 3 strategies — Redis, in-memory LRU, CDN edge cache
         Devil's Advocate: Redis adds ops complexity for a team of 1.
                          In-memory LRU handles current traffic fine.
         Critic: Start with in-memory LRU. Add Redis at 10K RPM.

You:     /athanor:plan

         [dispatches Planner (Claude)]
         Plan: Cache middleware, 4 phases
         [Codex reviews the plan]
         [Critic refines with review feedback]
         Final plan: 6 subtasks, dependency-ordered.

You:     /athanor:work --team

         Wave 1: [subtask 1, 2] parallel
           ↓ discovery relay
         Wave 2: [subtask 3, 4] depends on wave 1
           ↓
         Wave 3: [subtask 5, 6]
         All 6 subtasks complete. 2 lessons saved for next time.
```

> Need deeper analysis? Try `/athanor:deep-plan` for full adversarial planning.
> In a hurry? `/athanor:lite-plan` skips the review step.

## Commands

| Command | Mode | What it does |
|---------|------|-------------|
| `/athanor:setup` | — | Health check and configuration |
| `/athanor:discuss` | Plan | Decision brainstorming (researcher + devil's advocate + critic) |
| `/athanor:analyze` | Plan | Parallel fast analysis (multiple workers simultaneously) |
| `/athanor:debug` | Plan | Triage-first parallel failure diagnosis |
| `/athanor:deep-plan` | Plan | Full adversarial planning (Claude + Codex cross-review) |
| `/athanor:plan` | Plan | Standard planning + review + task splitting (default) |
| `/athanor:lite-plan` | Plan | Lightweight planning (Claude only, no review) |
| `/athanor:work` | Execute | Grinding through every subtask until done |

```
/athanor:discuss  →  /athanor:analyze  →  /athanor:debug (optional)
   "What?"              "Where?"              "Why broken?"

                  →  /athanor:plan (or deep-plan / lite-plan)  →  /athanor:work
                        "How?"                                       "Do it."
```

Everything before `/athanor:work` is **Plan Mode** — no files are modified.

## Key Feature: 3-Tier Planning Pipeline

```
Deep (/athanor:deep-plan):
         ┌── Planner A ──→ Reviewer B ──┐
Input ───┤                               ├── Critic → Final Plan
         └── Planner B ──→ Reviewer A ──┘

Standard (/athanor:plan, default):
Input ── Planner ──→ Reviewer ──→ Refinement → Final Plan

Lite (/athanor:lite-plan):
Input ── Planner ──→ Final Plan
```

| Tier | When to use | Cost |
|------|------------|------|
| lite | Quick iteration, low-risk changes | 1 worker |
| standard | Default for most tasks | 2-3 workers |
| deep | High-stakes architecture, complex refactors | 5-6 workers |

## Design Philosophy

**8 commands, not 100 features.** A focused workflow instead of a feature collection. Each command maps to one phase: brainstorm, analyze, plan, execute.

**Thin leader.** The main session never reads files, analyzes code, or writes code. It dispatches and collects. Your context stays clean regardless of session length.

**3-tier adversarial planning.** Choose the review depth that fits the task: lite for speed, standard for balanced quality, deep for competing perspectives with cross-model review.

**Grow with use.** Lessons from every session are extracted, scored, and surfaced to future workers. The system gets better at your codebase over time.

**Plan before execute.** No files are modified until you confirm the plan. Explicit mode separation prevents accidental changes.

**Session isolation.** If a work-log exists in a session, a new session is automatically created. Every planning cycle starts clean.

## Architecture

**Thin leader** dispatches to **clean-context workers**:

| Agent | Model | Role |
|-------|-------|------|
| researcher | sonnet | Objective research + Devil's Advocate |
| analyst | sonnet | Fast parallel analysis |
| planner | opus | Implementation planning |
| critic | opus | Plan synthesis and review |
| executor | sonnet | Code execution with verification loop |
| learner | sonnet | Session learning extraction |
| task splitter | sonnet | Plan → subtask decomposition |
| cleaner | haiku | Memory decay and cleanup |

When Codex is available, it serves as Planner B (deep tier) or Reviewer (standard tier).

**Session communication** via `.md` files — workers read and write to `.athanor/sessions/{id}/`. No shared state in the leader's context.

**Learning system** — after each `/athanor:work`, the Learner extracts structured lessons to `.athanor/lessons/`. Workers read relevant lessons before starting. Frequently-accessed lessons auto-promote to permanent. Stale ones decay and get cleaned.

[Full architecture details](docs/DESIGN.md) | [Conventions](docs/CONVENTIONS.md)

## Execution Modes

**Solo (`--solo`)** — One subtask at a time, each in a clean context. Simple and reliable.

**Team (`--team`)** — Wave-based parallel execution. Subtasks grouped by dependency, each wave runs simultaneously with discovery relay between waves.

```
Wave 1: [task 1, task 2]  ← parallel
  ↓ discovery relay
Wave 2: [task 3]          ← depends on wave 1
```

## Configuration

`athanor.json` at project root (auto-created by `/athanor:setup`):

| Key | Default | Description |
|-----|---------|-------------|
| `codex.enabled` | `true` | Cross-model planning with Codex (falls back to contrarian Claude) |
| `work.defaultMode` | `"solo"` | Default execution mode |
| `work.ralphLoop.maxRetries` | `5` | Max verification retries per subtask |
| `work.circuitBreaker.consecutiveFailures` | `3` | Failures before circuit breaker trips |
| `team.waveSize` | `3` | Max parallel workers per wave |
| `memory.decayDays` | `7` | Working memory retention period |
| `memory.promotionThreshold` | `5` | Access count for auto-promotion to permanent |

## FAQ

**How is this different from just using Claude Code?**
Claude Code is one brain doing everything. Athanor gives it a team — separate workers for research, planning, execution, and review, each with clean context. The main session stays lightweight no matter how long you work.

**Why cross-model adversarial planning?**

Different models have different blind spots. In deep mode, Claude and Codex create competing plans and review each other's work. Standard mode gets Codex review on a single plan. Lite mode skips review entirely. Each tier degrades gracefully:
- **Deep**: Planner B falls back to Claude contrarian; Reviewer B falls back to Claude.
- **Standard**: Codex review falls back to Claude self-review.
- **Lite**: Unaffected (Claude only by design).

**What does /athanor:debug do?**

Triage-first failure diagnosis. It analyzes errors, git history, and code traces in parallel to pinpoint root causes before you plan a fix.

**Does this work without Codex?**
Yes. All tiers degrade gracefully — deep mode uses Claude contrarian instead of Codex as Planner B, standard mode falls back to Claude self-review. Set `codex.enabled: true` to use Codex when available.

**How much token overhead does this add?**
The leader session stays minimal — it only dispatches and collects. Workers use tokens in clean contexts that are discarded after each task. Net cost is comparable to doing the same work manually, but with better plan quality.

**Who is this for?**
Solo developers who want structured planning. Tech leads who want reproducible quality. Teams who want their Claude Code sessions to share learned lessons.

## Roadmap

- [x] Core workflow (discuss, analyze, plan, work)
- [x] Cross-model adversarial planning
- [x] Solo and team execution modes
- [x] 2-tier learning system with memory decay
- [x] Codex native integration (codex exec CLI)
- [ ] Multi-project lesson sharing
- [ ] Custom worker agent definitions
- [ ] CI/CD integration hooks

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Docs

- [DESIGN.md](docs/DESIGN.md) — Architecture and design decisions
- [CONVENTIONS.md](docs/CONVENTIONS.md) — Dispatch, session, and lesson conventions
- [ROADMAP.md](docs/ROADMAP.md) — Implementation roadmap

## Acknowledgments

Athanor vendors the following open-source component:

- **`verification-before-completion` skill** from [superpowers](https://github.com/obra/superpowers) by Jesse Vincent (MIT).
  Triggered by the athanor Stop hook to enforce evidence-before-claims discipline
  at turn boundaries. Full attribution in [NOTICE.md](NOTICE.md).

## License

MIT
