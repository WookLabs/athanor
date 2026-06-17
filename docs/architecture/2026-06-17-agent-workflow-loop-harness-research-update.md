# Agent Workflow, Loop, And Harness Research Update

Date: 2026-06-17
Branch: `feat/p6-trace-eval-harness`
Purpose: compare Athanor against current workflow engineering, loop
engineering, harness engineering, Claude Code plugin, and eval/observability
practice.

## Scope

This report updates the earlier loop/harness audit with current public sources
and the local post-P5/P6 implementation state. Scores are for the current
working branch unless noted. P5 is merged to `main`; P6 is implemented on this
branch but still needs final full-suite verification and merge before it should
be treated as released.

## Source Set

Primary and high-signal references:

- Claude Code extension model: `CLAUDE.md`, skills, MCP, subagents, agent
  teams, hooks, plugins, and marketplaces:
  https://code.claude.com/docs/en/features-overview
- Claude Code hooks reference:
  https://code.claude.com/docs/en/hooks
- Claude Code skills reference:
  https://code.claude.com/docs/en/skills
- Claude Code MCP reference:
  https://code.claude.com/docs/en/mcp
- Claude Code agent teams:
  https://code.claude.com/docs/en/agent-teams
- Claude Code plugin marketplace distribution:
  https://code.claude.com/docs/en/plugin-marketplaces
- Anthropic harness design for long-running app development:
  https://www.anthropic.com/engineering/harness-design-long-running-apps
- Anthropic eval guidance for agents:
  https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- OpenAI harness engineering:
  https://openai.com/index/harness-engineering/
- OpenAI Agents SDK tracing:
  https://openai.github.io/openai-agents-python/tracing/
- OpenAI agent workflow evals:
  https://developers.openai.com/api/docs/guides/agent-evals
- Martin Fowler / Thoughtworks harness engineering:
  https://martinfowler.com/articles/harness-engineering.html
- Addy Osmani loop engineering:
  https://addyosmani.com/blog/loop-engineering/
- LangGraph durable orchestration:
  https://docs.langchain.com/oss/python/langgraph/overview
- Temporal durable agent workflows:
  https://temporal.io/blog/building-ai-agents-that-overcome-the-complexity-cliff
- LangSmith evaluation and observability:
  https://docs.langchain.com/langsmith/evaluation
  https://docs.langchain.com/langsmith/observability
- Inspect AI evaluation framework:
  https://inspect.aisi.org.uk/

Local refs were also refreshed earlier under ignored `ref/`, including
`ai-boost-awesome-harness-engineering`, `cobusgreyling-loop-engineering`,
`UKGovernmentBEIS-inspect_ai`, `anthropics-claude-plugins-official`,
`obra-superpowers`, `openai-codex`, and Claude Code hook/plugin examples.

## Current External Shape

### Workflow engineering

The modern workflow baseline is no longer "write a good prompt." Claude Code
documents the extension stack as layered surfaces: persistent context,
reusable skills, MCP tools, isolated subagents, agent teams, lifecycle hooks,
and distributable plugins. Anthropic's effective-agent material keeps the
pattern simple: prompt chaining, routing, parallelization,
orchestrator-worker, and evaluator-optimizer. The practical trend is to encode
those patterns as repo-local artifacts and explicit control paths rather than
conversation habit.

Athanor alignment: strong. `discuss`, `analyze`, `debug`, `plan`, `work`,
`review`, `lfg`, and `lfg-goal` already encode a workflow surface instead of a
bag of skills. The thin leader, clean-context workers, cross-model planning,
and 6-lens review match the orchestrator-worker and evaluator-optimizer
direction.

### Harness engineering

OpenAI, Anthropic, and Fowler converge on the same theme: the model is not the
unit of reliability; the surrounding environment is. Strong harnesses provide
structured context, task artifacts, tools, tests, review loops, feedback
sensors, and cleanup mechanisms. OpenAI's write-up treats docs, plans, tests,
review comments, eval harnesses, repository management scripts, and recurring
cleanup as agent-produced and versioned harness components. Anthropic's
long-running harness separates planner/generator/evaluator roles, negotiates
testable sprint contracts, and tunes evaluators from trace evidence.

Athanor alignment: strong on structure, still incomplete on production
feedback loops. Athanor has repo-local plans, skill contracts, stop/pre/post
hooks, replayable payload fixtures, hook budgets, and evidence-first policy.
It is still light on trace-derived quality dashboards, model-graded or human
spot-check evals, and recurring entropy cleanup tasks.

### Loop engineering

Loop engineering is emerging terminology rather than a fully standardized
discipline. The useful definition is: a system discovers work, dispatches
agents, checks evidence, writes durable state, decides the next action, and
stops or escalates without a human re-prompting every turn. Addy Osmani frames
the primitives as scheduled automation, worktree isolation, skills, plugins or
connectors, subagents, and external memory. Temporal and LangGraph frame the
same need from the durability side: above short workflows, restarts become
expensive or unsafe, so resumable state and failure recovery become core
infrastructure.

Athanor alignment: partial. `/athanor:lfg-goal` already has a durable ledger,
iteration caps, no-progress threshold, adversarial review, user ratification,
and scope-drift checks. What is missing is an outer controller that can resume
across sessions, maintain a queue, consume eval reports, coordinate review/fix
iterations, isolate concurrent attempts, and record why it stopped.

### Eval and observability engineering

Agent eval practice has shifted from output-only checks to trajectory-aware
measurement: traces, datasets, deterministic graders, LLM judges, human
calibration, online/offline eval loops, and production trace feedback.
OpenAI Agents SDK traces span LLM generations, tool calls, handoffs,
guardrails, and custom events. LangSmith combines traces with offline and
online evals. Inspect formalizes tasks, datasets, solvers, scorers, tools,
sandboxing, and agent evals, including external agents like Claude Code and
Codex CLI.

Athanor alignment: P6 finally puts Athanor on the right path. The local trace
schema and deterministic workflow scenario runner are correct as a foundation.
But P6 is still local and fixture-driven. It does not yet instrument live
skills, does not ingest production traces into datasets, and does not provide
LLM/human judge calibration.

### Claude Code plugin ecosystem

Claude Code now has an official extension taxonomy: skills for reusable
procedures, MCP for external tools, hooks for lifecycle automation, subagents
and agent teams for isolation/parallelism, plugins for packaging, and
marketplaces for distribution/update. Official marketplace docs also emphasize
trust and review: users should trust plugin source, manifests, MCP servers,
and bundled software before installation.

Athanor alignment: strong packaging and hooks; medium trust UX. Athanor has
local dry-run install planning and a conservative hook catalog, but it still
lacks a reversible apply/remove path, hash review, source trust state, and a
tracked marketplace release discipline comparable to official expectations.

## Athanor Current Scorecard

| Dimension | Score | Assessment |
| --- | ---: | --- |
| Workflow engineering | 9.2 | Strong command model, role separation, TDD/review discipline. Needs live trace wiring to prove decisions across real runs. |
| Harness engineering | 9.1 | Strong guides and sensors: docs, plans, hooks, replay corpus, budgets. Needs recurring cleanup and dashboard-style observability. |
| Loop engineering | 7.6 | `lfg-goal` is a useful ledger loop, but no general durable outer loop controller yet. |
| Eval/observability | 8.7 | P6 trace/eval harness is the right local foundation. Score remains below 9.5 until live workflows emit traces and CI/reporting graduate from fixtures. |
| Hook safety | 9.7 | Narrow default hooks, replay evidence, fail-open diagnostics, and performance budget gate are ahead of most plugin refs. |
| Hook lifecycle coverage | 8.4 | Good enabled core, many capture-only candidates. Correctly cautious; missing live evidence for newer events. |
| Performance discipline | 9.4 | P5 budget gate makes catalog budgets executable. Needs historical trend tracking to reach 9.5+. |
| Trust/install UX | 7.1 | Dry-run planner exists; reversible trusted apply path is still missing. |
| Cross-runtime portability | 8.2 | Codex mirror exists; single-source generation/conformance is still missing. |
| Plugin diet / surface restraint | 9.4 | Earlier over-vendoring has been corrected; only 4 registered agents remain. Watch for runtime mirror drift. |
| Context engineering | 8.8 | Thin leader and clean workers are strong. Missing progressive context index, trace-to-memory promotion, and external MCP/code intelligence integration. |
| Maintainability / entropy control | 8.1 | Tests and docs are strong. Missing scheduled garbage-collection loop over docs, plans, stale candidates, and generated mirrors. |

Overall current branch score: 8.9/10.

Interpreted narrowly as a Claude Code plugin rather than a production agent
platform, Athanor is already high-end. Interpreted against 2026 loop/harness
engineering expectations, the remaining gap is not more commands; it is
durable orchestration, live traces, trust-state installs, and entropy control.

## What Athanor Does Well

1. It is evidence-first. Hook payloads, replay fixtures, live-redacted
   provenance, test evidence, and performance budgets are stronger than most
   Claude Code plugin examples.
2. It resists surface bloat. Earlier vendored CE/superpowers content was cut
   down to concepts and a small native command set.
3. It separates producer and checker roles. Plan/review/work, Codex review,
   critic passes, Stop verification, and P6 graders all follow the modern
   evaluator-optimizer direction.
4. It has a real workflow product shape. The command set maps to developer
   phases, not random utility snippets.
5. It keeps honest boundaries. Capture-only hook candidates are not silently
   treated as supported enforcement; P6 does not claim live instrumentation.
6. It is CI-friendly. Most gates are local, deterministic, and cheap enough to
   run repeatedly.

## What Is Missing

1. Durable outer loop controller. Athanor needs a state machine that can queue,
   resume, dispatch, evaluate, retry, stop, and escalate across sessions.
2. Live workflow traces. The P6 trace schema should be wired into real
   `plan`, `work`, `review`, `lfg`, and `lfg-goal` paths.
3. Trace-to-eval feedback loop. Failed real traces should become regression
   scenarios. Passing capability scenarios should graduate to regression gates.
4. Trust-aware installer apply. Dry-run is not enough for users who want a
   managed apply/remove path.
5. Cross-runtime conformance generation. Claude and Codex plugin surfaces
   should be verified from one source of truth.
6. Agent-team/worktree integration. Claude Code has experimental agent teams
   and worktree hooks; Athanor has team mode conceptually but not native
   worktree-backed isolation and cleanup as a first-class path.
7. Entropy cleanup. Athanor needs a scheduled or command-driven cleanup loop
   for stale docs, stale capture-only candidates, unused mirrors, and drifted
   references.
8. Observability trend history. P5/P6 produce point-in-time gates; they do not
   yet preserve historical latency, scenario score, failure reason, and drift
   trends.
9. MCP/code intelligence bridge. Athanor can recommend companion plugins, but
   does not yet encode a stable MCP/code-search strategy for large repos.

## Overbuilt Or Risky Parts

1. More default hooks would be risky. The official Claude Code hook surface is
   broad, but every default hook increases latency and failure modes. Athanor
   should keep capture-only promotion evidence-gated.
2. More registered agents are unnecessary. The current 4 registered agents are
   reasonable; re-registering pipeline reference roles would reintroduce the
   old collision problem.
3. A model-judge eval layer would be premature as a default. Deterministic P6
   graders should stay primary until live traces show where model graders add
   value.
4. Full external eval framework adoption is unnecessary now. Inspect or
   LangSmith integration can be optional after the local trace contract
   stabilizes.
5. Marketplace breadth is not a moat. Athanor's advantage is disciplined
   workflow, not a large catalog of generic skills.
6. Autonomous merge/deploy loops should wait. OpenAI-style end-to-end merging
   requires stronger trust/install and live eval evidence than Athanor has
   today.

## Add / Keep / Remove

### Add

1. P7 durable loop controller:
   - state file under `.athanor/goals` or `.athanor/loops`
   - queue, attempt budget, no-progress detector, eval report input
   - stop reasons and human escalation records
   - worktree isolation hooks where available
2. Live trace instrumentation:
   - trace writer adapters for plan/work/review/lfg/lfg-goal
   - correlation IDs across hooks, worker artifacts, and eval reports
3. Eval dataset graduation:
   - convert failed real traces into committed scenarios
   - keep deterministic graders first
   - add optional LLM/human judge slots later
4. Trust installer:
   - apply/remove operations
   - hash/source review
   - no-clobber conflict policy
   - rollback plan
5. Drift/entropy command:
   - stale docs and plan scanner
   - capture-only candidate age report
   - generated mirror consistency check
   - hook latency trend summary
6. Cross-runtime conformance:
   - generate/verify Claude and Codex manifests from one catalog
   - ensure runtime defaults do not diverge silently

### Keep

1. 9-command surface.
2. Thin leader and clean-context worker identity.
3. Conservative default hook policy.
4. Capture-only event promotion process.
5. Deterministic local gates before external services.
6. P6 local trace/eval harness as the base contract.
7. Concept absorption policy instead of wholesale vendoring.

### Remove Or Avoid

1. Do not enable `SessionStart`, `PreCompact`, `PermissionRequest`,
   `PostToolUseFailure`, or `SubagentStop` enforcement by default without live
   payload evidence and budget data.
2. Do not add language-specific or domain-specific reviewer agents as native
   registered agents; the existing reviewer lenses cover that better.
3. Do not keep generated Codex mirror files if they become unverifiable by CI.
   Either conformance-test them or regenerate them.
4. Do not add always-on MCP connections as plugin defaults. Treat MCP as
   opt-in connector policy because tool output and prompt injection risk vary
   by user environment.
5. Do not build a high-autonomy merge loop before trust installer and live eval
   gates exist.

## Revised Priority Program

### P6 Finish: Merge Trace/Eval Harness

Status: implemented on `feat/p6-trace-eval-harness`; not yet merged.

Required next steps:

1. Run full verification:
   - `python -m pytest tests/ -q`
   - `git diff --check`
   - `python scripts/evals/run_workflow_scenarios.py --scenario-root tests/fixtures/workflow_evals --json`
   - `python scripts/check_release_ready.py --ci`
2. Merge to `main` and push if clean.

### P7: Durable Loop Controller

Goal: convert `lfg-goal` from a command-local macro loop into a resumable
controller that consumes trace/eval evidence.

Minimum acceptance:

- loop state schema and migration-safe loader
- resume command path
- attempt budget and no-progress stop
- eval report input
- explicit stop/escalation reasons
- tests for resume, no-progress, pass, fail, and user escalation

Expected score movement:

- Loop engineering: 7.6 -> 9.5
- Workflow engineering: 9.2 -> 9.6

### P8: Trust-Aware Installer Apply Path

Goal: make hook/plugin installation safe enough for real users.

Minimum acceptance:

- reversible apply/remove
- hook hash/source trust status
- capture-only hooks cannot be enabled by default
- no-clobber conflict handling
- dry-run and apply reports share schema

Expected score movement:

- Trust/install UX: 7.1 -> 9.5

### P9: Cross-Runtime Conformance Generator

Goal: ensure Claude and Codex plugin surfaces cannot drift.

Minimum acceptance:

- one source of truth for command/skill metadata
- generated or verified Codex mirror
- CI conformance test
- no expansion of default runtime hooks

Expected score movement:

- Cross-runtime portability: 8.2 -> 9.5

### P10: Live Trace Adoption And Observability Trends

Goal: move P6 from local fixture harness to real workflow observability.

Minimum acceptance:

- real `plan`, `work`, `review`, `lfg`, `lfg-goal` traces
- trace IDs connected to session files and hook evidence
- trendable local reports for scenario scores and hook latency
- failing traces can be promoted to scenario fixtures

Expected score movement:

- Eval/observability: 8.7 -> 9.6
- Harness engineering: 9.1 -> 9.6

### P11: Entropy Cleanup Loop

Goal: encode recurring cleanup so Athanor does not accumulate stale harness
surface.

Minimum acceptance:

- command or scheduled-compatible script for stale docs/plans/candidates
- generated mirror drift report
- hook catalog freshness report
- CI or manual gate that produces actionable cleanup tasks

Expected score movement:

- Maintainability/entropy: 8.1 -> 9.4

## Bottom Line

The current Athanor direction is correct. It should not add many more visible
features. The next level is to make the existing workflow measurable,
resumable, trusted, and self-cleaning.

The highest-value next action is not a new skill or hook. It is finishing P6
merge, then implementing P7 as a durable loop controller that consumes P6 eval
reports rather than raw optimism.
