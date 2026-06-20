# Athanor

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude_Code-plugin-blueviolet.svg)](https://claude.ai/code)

> The alchemist's self-sustaining furnace — a workflow orchestrator that grows smarter with use.

**v0.19.3** — 13 athanor-native commands (+ 2 internal skills: scope-drift, verification-before-completion) + 1 KEEP vendored skill (`/athanor:ce-test-browser`). Clean-context workers. Prompt generation. Goal-aligned assessment. Score-target goal loops. Agent topology gates. 3-tier adversarial planning. 6-lens parallel review. Sessions that compound. Thin Leader / cross-model adversarial planning / Spec-then-TDD discipline / Stop hook runtime gate are the athanor identity invariants — preserved intact through the v0.12.0 cutover. See [CLAUDE.md §"Concept Absorption Surface"](CLAUDE.md#concept-absorption-surface-post-v0120) for the post-cutover surface and [docs/v0.12.0-migration.md](docs/v0.12.0-migration.md) for the migration guide.

Current package-facing operator map: [docs/package-knowledge-index.md](docs/package-knowledge-index.md).

### What v0.10.0 absorbed (corrected by v0.12.0 atomic cut)

- **compound-engineering 3.8.3** — originally vendored 33 skills + 49 sub-agents at v0.10.0. v0.12.0 atomic cut reduced this to **1 KEEP skill** (`/athanor:ce-test-browser`, D8) + **2 KEEP sub-agents** (`ce-git-history-analyzer`, `ce-repo-research-analyst`, D12; both later removed in v0.15.x once no live dispatch reference remained). The remaining 32 skills + 47 sub-agents were removed in the v0.12.0 concept-kernel cutover. See [`docs/archive/v010-v011-vendoring-scope-correction.md`](docs/archive/v010-v011-vendoring-scope-correction.md) for the plan-of-record misread retrospective.
- **superpowers 5.1.0** — originally vendored 13 skills at v0.10.0. v0.12.0 atomic cut reduced this to **0 surviving skills**; 2 LIFT-source concepts (`sp-systematic-debugging`, `sp-using-superpowers`) absorbed into athanor-native skills as prose subsections, the rest dropped.
- **5 concepts absorbed as native prose** (NOT vendored directories): reviewer-persona vocabulary, doc-review mode, systematic-debugging Iron Law, requirements capture R/A/F/AE-IDs, skill-discovery preamble. Full MIT attribution in [NOTICE.md §"Concepts adopted from upstream"](NOTICE.md).

### What v0.12.0 deliberately does NOT do

- Does NOT silently downgrade `/athanor:plan` to a single-agent flow (cross-model adversarial dual-planner stays the default).
- Does NOT silently downgrade `/athanor:work` to a non-TDD execution flow (athanor-native Spec-then-TDD stays the default).
- Does NOT extend the Stop hook gate scope — per D10/D11 the runtime gate + companion-fix arc 5 layers + v0.10.2 normalization stack survive intact, with rationale re-framed to general defensive coverage.
- Does NOT re-license athanor (athanor stays MIT; CE and superpowers stay MIT under their copyright holders).
- Does NOT require CE or superpowers to be separately installed. Users who need a removed upstream skill install the upstream plugin directly — see the migration guide.

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

> Need deeper analysis? Try `/athanor:deep-plan` or `/athanor:plan --depth=deep` for full adversarial planning.
> In a hurry? `/athanor:lite-plan` or `/athanor:plan --depth=lite` skips the review step.

## Commands

| Command | Mode | What it does |
|---------|------|-------------|
| `/athanor:setup` | — | Health check and configuration |
| `/athanor:prompt-gen` | Plan | Clarify a vague request into a reusable prompt and recommend the next skill |
| `/athanor:discuss` | Plan | Decision brainstorming (researcher + devil's advocate + critic) |
| `/athanor:analyze` | Plan | Parallel fast analysis (multiple workers simultaneously) |
| `/athanor:assess` | Plan | Goal-aligned 100-point assessment with overbuilt/underbuilt findings |
| `/athanor:debug` | Plan | Triage-first parallel failure diagnosis |
| `/athanor:plan` | Plan | Tiered planning via `--depth=standard`(default)`/deep/lite` (+ `--no-review`) |
| `/athanor:deep-plan` | Plan | Thin wrapper for `/athanor:plan --depth=deep`; rejects contradictory `--depth=` flags |
| `/athanor:lite-plan` | Plan | Thin wrapper for `/athanor:plan --depth=lite`; rejects contradictory `--depth=` flags |
| `/athanor:work` | Execute | Grinding through every subtask until done |
| `/athanor:review` | Plan | Parallel 6-lens code review (architecture, quality, security, performance, testing, docs) |
| `/athanor:lfg` | Execute | Standalone end-to-end pipeline (plan → work → review → PR → CI) |
| `/athanor:lfg-goal` | Execute | Goal-driven macro Ralph loop over a durable goal ledger |

```
/athanor:prompt-gen → /athanor:discuss  →  /athanor:analyze  →  /athanor:assess  →  /athanor:debug (optional)
   "Ask better"          "What?"              "Where?"              "How good?"          "Why broken?"

                  →  /athanor:plan (--depth=standard/deep/lite)  →  /athanor:work
                        "How?"                                       "Do it."
```

Everything before `/athanor:work` is **Plan Mode** — no files are modified.

## Key Feature: 3-Tier Planning Pipeline

```
Deep (--depth=deep):
         ┌── Planner A ──→ Reviewer B ──┐
Input ───┤                               ├── Critic → Final Plan
         └── Planner B ──→ Reviewer A ──┘

Standard (/athanor:plan, default):
Input ── Planner ──→ Reviewer ──→ Refinement → Final Plan

Lite (--depth=lite):
Input ── Planner ──→ Final Plan
```

| Tier | When to use | Cost |
|------|------------|------|
| lite | Quick iteration, low-risk changes | 1 worker |
| standard | Default for most tasks | 2-3 workers |
| deep | High-stakes architecture, complex refactors | 5-6 workers |

## Design Philosophy

**13 commands, not 100 features.** A focused workflow instead of a feature collection. Each command maps to one phase: brainstorm, analyze, plan, execute.

**Thin leader.** The main session never reads files, analyzes code, or writes code. It dispatches and collects. Your context stays clean regardless of session length.

**3-tier adversarial planning.** Choose the review depth that fits the task: lite for speed, standard for balanced quality, deep for competing perspectives with cross-model review.

**Grow with use.** Lessons from every session are extracted to local `.athanor/lessons/` files, scored, and surfaced to future workers. The system gets better at your codebase over time.

**Plan before execute.** No files are modified until you confirm the plan. Explicit mode separation prevents accidental changes.

**Session isolation.** If a work-log exists in a session, a new session is automatically created. Every planning cycle starts clean.

## Architecture

**Thin leader** dispatches to **clean-context workers**:

**4 registered agent types** (dispatched as named types): `learner`, `releaser`, `ci-watcher`, `codex-dispatcher`.

**7 reference docs** (inline-dispatched via session-specific paths — not standalone registered types): `analyst`, `cleaner`, `critic`, `executor`, `planner`, `researcher`, `reviewer`.

When Codex is available, it serves as Planner B (deep tier) or Reviewer (standard tier). See [CLAUDE.md §Native Agent Inventory](CLAUDE.md#native-agent-inventory) and [agent topology](docs/agent-topology.md) for full detail.

**Session communication** via `.md` files — workers read and write to `.athanor/sessions/{id}/`. No shared state in the leader's context.

**Learning system** — after each `/athanor:work`, the Learner extracts structured lessons to `.athanor/lessons/`. Lessons carry memory-indexable fields for local recall, and [the read-only memory index](docs/memory-index.md) can search lessons, traces, goals, and completed goals without daemons, network calls, or automatic context injection. Goal/session resumes use the compact [handoff artifact](docs/handoff-artifact.md). Permanent persistence to mem-search remains separate and unimplemented; local lesson files stay the source of truth.

[Full architecture details](docs/DESIGN.md) | [Conventions](docs/CONVENTIONS.md)

Hook runtime policy is tracked separately from hook expansion candidates in
[docs/hook-catalog.md](docs/hook-catalog.md). Only entries marked `enabled`
there are registered by default.

Hook installer changes can be previewed without mutating user settings:

```bash
python scripts/gates/hook_install_dry_run.py --json
```

The dry-run planner reports `already-present`, `would-add`, `blocked`, and
`conflict` actions and always returns `writes: []`.

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
| `memory.promotionThreshold` | `5` | Access count for local working→permanent lesson promotion; local memory-index search is read-only |

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

## Companion Plugins

Athanor recommends (does not require) the following companion plugins:

**superpowers** — provides foundational skills like `verification-before-completion`. Athanor vendors a copy of this skill for guaranteed Stop hook behavior, but having superpowers installed adds the rest of its skill catalog (TDD, debugging, collaboration patterns).

```
# Official marketplace
/plugin install superpowers@claude-plugins-official

# Fallback marketplace
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
```

**athanor-codex** — a second-runtime mirror of the athanor native skill set for the [Codex CLI](https://github.com/openai/codex). Ships 17 skills (`athanor-analyze`, `athanor-assess`, `athanor-debug`, `athanor-deep-plan`, `athanor-discuss`, `athanor-lfg`, `athanor-lfg-goal`, `athanor-lite-plan`, `athanor-plan`, `athanor-prompt-gen`, `athanor-ci-watch`, `athanor-release`, `athanor-review`, `athanor-scope-drift`, `athanor-setup`, `athanor-verify`, `athanor-work`) with no Claude hooks. Install from the repo-local marketplace:

```
codex plugin marketplace add <path-to-athanor>/.agents/plugins/marketplace.json
codex plugin add athanor-codex@athanor
```

See [`plugins/athanor-codex/README.md`](plugins/athanor-codex/README.md) for the full install and refresh flow.

Run `/athanor:setup` to audit installed companions. If superpowers is absent, athanor remains fully functional — its vendored skill ensures the Stop hook works regardless. See [docs/DEPENDENCIES.md](docs/DEPENDENCIES.md) for the full policy.

## Roadmap

- [x] Core workflow (discuss, analyze, plan, work)
- [x] Cross-model adversarial planning
- [x] Solo and team execution modes
- [x] Local 2-tier lesson files with memory decay prompts and read-only memory-index search
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
- [DEPENDENCIES.md](docs/DEPENDENCIES.md) — Companion plugin policy and vendored-file inventory

## Acknowledgments

Athanor vendors the following open-source component:

- **`verification-before-completion` skill** from [superpowers](https://github.com/obra/superpowers) by Jesse Vincent (MIT).
  Triggered by the athanor Stop hook to enforce evidence-before-claims discipline
  at turn boundaries. Full attribution in [NOTICE.md](NOTICE.md).
- **`scope-drift` skill** from [claude-octopus](https://github.com/nyldn/claude-octopus) by nyldn (MIT).
  On-demand skill that detects scope drift between current branch changes and the canonical plan-of-record.
  Full attribution in [NOTICE.md](NOTICE.md).

## License

MIT
