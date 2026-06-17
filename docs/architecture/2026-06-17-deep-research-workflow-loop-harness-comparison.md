# Deep Research: Workflow, Loop, And Harness Engineering Comparison

Date: 2026-06-17
Local basis: `main` after P11 entropy cleanup (`5548748`).
Scope: Claude Code workflow/plugin surfaces, loop engineering, harness
engineering, eval/observability practices, and Athanor's current gaps.

## Executive Verdict

Athanor is now a strong local harness plugin, not just a prompt bundle. Its
strongest property is executable discipline: replay gates, hook budgets,
trust-aware install/apply/remove, workflow trace fixtures, durable loop
fixtures, cross-runtime conformance, observability trend snapshots, and the P11
entropy cleanup report.

The current frontier has moved from "good prompts" to "runtime selection,
isolation, trace-backed improvement, and harness self-evolution." Against that
frontier, Athanor is strong on deterministic local verification and loop
control, but still behind on live orchestration adapters, command-level traces,
OpenTelemetry-style interoperability, portable benchmark episode packaging, and
trace-to-memory/self-evolution loops.

Overall:

- Claude Code plugin quality: 9.35/10
- Local deterministic harness quality: 9.45/10
- Modern agent-runtime platform quality: 8.8/10

The main drag is not hook safety anymore. It is that Athanor still decides and
checks many things locally, but does not yet route live work across Claude's
newer execution surfaces or emit full live traces from the real command flows.

## Sources Reviewed

Primary and high-signal references:

- OpenAI, "Harness engineering: leveraging Codex in an agent-first world"
  (2026-02-11): https://openai.com/index/harness-engineering/
- OpenAI Agents SDK tracing:
  https://openai.github.io/openai-agents-python/tracing/
- Anthropic, "Building effective agents" (2024-12-19):
  https://www.anthropic.com/engineering/building-effective-agents
- Claude Code dynamic workflows:
  https://code.claude.com/docs/en/workflows
- Claude Code agent teams:
  https://code.claude.com/docs/en/agent-teams
- Claude Code worktrees:
  https://code.claude.com/docs/en/worktrees
- Claude Code goals:
  https://code.claude.com/docs/en/goal
- Claude Code hooks:
  https://code.claude.com/docs/en/hooks
- Claude Code plugins reference:
  https://code.claude.com/docs/en/plugins-reference
- Martin Fowler / Thoughtworks, "Harness engineering for coding agent users"
  (2026-04-02): https://martinfowler.com/articles/harness-engineering.html
- Datadog, "Closing the verification loop: Observability-driven harnesses for
  building with agents" (2026-03-09):
  https://www.datadoghq.com/blog/ai/harness-first-agents/
- Arize, "Self-Improving Agents: the Agent Harness for Reliable Code":
  https://arize.com/blog/closing-the-loop-coding-agents-telemetry-and-the-path-to-self-improving-software/
- arXiv, "Agentic Harness Engineering: Observability-Driven Automatic Evolution
  of Coding-Agent Harnesses" (v4, 2026-05-18):
  https://arxiv.org/abs/2604.25850
- OpenTelemetry AI agent observability:
  https://opentelemetry.io/blog/2025/ai-agent-observability/
- LangGraph overview:
  https://docs.langchain.com/oss/python/langgraph/overview
- Inspect AI:
  https://inspect.aisi.org.uk/
- Terminal-Bench:
  https://www.tbench.ai/
- Berkeley RDI, "How We Broke Top AI Agent Benchmarks":
  https://rdi.berkeley.edu/blog/trustworthy-benchmarks-cont/
- MindStudio, "What Is Loop Engineering?":
  https://www.mindstudio.ai/blog/what-is-loop-engineering-ai-coding-agents
- MindStudio, "Claude Code Dynamic Workflows vs /goal vs Agent Teams":
  https://www.mindstudio.ai/blog/claude-code-dynamic-workflows-vs-goal-vs-agent-teams-decision-framework

## External Baseline

### 1. Workflow Engineering

Modern workflow engineering is now about choosing the right execution surface:

- simple single-session work;
- subagents that report back to one lead context;
- dynamic workflows where a reusable script orchestrates many subagents;
- agent teams where independent Claude Code sessions coordinate through shared
  tasks and messages;
- worktrees where filesystem changes are isolated even if work happens in
  parallel.

Claude's current docs make the tradeoff explicit: dynamic workflows are for
large fanout and reusable orchestration; agent teams are experimental, more
expensive, and best when peer communication matters; worktrees isolate file
edits rather than coordinating the work itself.

Anthropic's older but still useful pattern language remains the clean design
base: prompt chaining, routing, parallelization, orchestrator-workers, and
evaluator-optimizer. Complexity should be added only when it demonstrably
improves outcomes.

Implication for Athanor: the plugin should stop treating "team mode" as one
generic path. It needs an adapter that chooses between solo, subagent wave,
dynamic workflow, agent team, and worktree isolation based on task shape.

### 2. Loop Engineering

Loop engineering means designing the act-observe-decide-repeat cycle, including
clear goals, feedback, termination, escalation, and anti-infinite-loop controls.
Claude `/goal` is a native example: a completion condition is evaluated after
each turn and the session continues until the condition is met or cleared.

Athanor already has a credible local loop kernel:

- `lfg-goal` semantics;
- durable loop state and evidence schemas;
- fixture runner for loop decisions;
- no-progress and escalation decisions;
- Stop hook and verification gates.

What is missing is live dispatch/resume integration. The loop kernel is
well-tested locally, but it is not yet the runtime fabric that every live
`plan`, `work`, `review`, `lfg`, and `lfg-goal` command emits into.

### 3. Harness Engineering

OpenAI and Fowler converge on the same point: as agents write more code, human
work shifts toward designing environments, constraints, tests, feedback loops,
and control systems. Datadog's harness-first examples sharpen the bar: strong
simulation, formal/spec checks, shadow evaluation, production telemetry, and
fast automatic verification let agents iterate faster than human review can
scale.

Athanor is aligned here. It already treats the repository as the system of
record and encodes many decisions as scripts, schemas, fixtures, and CI gates.
The P11 entropy report further matches the "repo as harness" philosophy by
making stale plans, hook candidates, refs, and mirror drift visible.

The next maturity step is not another prose rule. It is more runtime feedback:
structured traces from live runs, trace promotion into eval fixtures, and
measurable before/after effects for harness edits.

### 4. Agentic Harness Engineering

The 2026 AHE paper raises the frontier: the harness itself becomes editable and
self-improving, with three observability pillars:

- component observability: every editable harness component is visible as a
  concrete, revertible file-level action space;
- experience observability: large trajectories are distilled into evidence a
  future agent can consume;
- decision observability: each harness edit declares a prediction, then later
  gets checked against task outcomes.

Athanor has partial component observability because most surfaces are files,
schemas, scripts, hooks, and docs. It has early experience observability via
workflow traces and trend snapshots. It does not yet have decision
observability for harness edits: commits do not carry machine-readable
predictions and later outcome checks.

Implication: after live traces, add a "harness decision ledger" that records
why a harness change is expected to improve a metric and later checks whether
that happened.

### 5. Observability And Interop

OpenAI Agents SDK tracing records end-to-end workflow traces, agent spans, model
generations, tool calls, handoffs, guardrails, and custom events. OpenTelemetry
is pushing standardized GenAI/agent semantic conventions to avoid vendor and
framework lock-in.

Athanor's P6/P10 trace/eval/trend layer is the right local-first base, but it
is not yet comparable to full live tracing. It also has no optional OTel
mapping/export adapter.

The correct move is still conservative: keep local JSONL as the default, and
add a no-runtime-dependency vocabulary/export adapter later. Do not make
external telemetry default.

### 6. Benchmark And Sandbox Engineering

Inspect and Terminal-Bench show the benchmark baseline: agent tasks should be
packaged as episodes with datasets, solvers/agents, tools, scorers, limits,
parallelism, traces, and sandbox isolation.

The Berkeley RDI benchmark exploit analysis is especially relevant: evals can
be reward-hacked when the agent and evaluator share mutable state, when answers
are visible to the agent, or when judge prompts ingest unsanitized agent output.

Athanor's current fixtures are fast and useful, but they are not yet portable
episode packages, and evaluator isolation is still mostly conventional rather
than explicitly modeled.

Implication: P15 should define portable eval episodes and evaluator isolation
rules before Athanor claims benchmark-grade harness maturity.

## Current Athanor Strengths

1. Clear workflow phase model: `discuss`, `analyze`, `plan`, `work`, `review`,
   `lfg`, and `lfg-goal` are coherent engineering phases.
2. Good thin-leader posture: the design favors focused workers and synthesis
   rather than one giant context.
3. Strong hook evidence surface: capture, replay, redaction, replay fixtures,
   performance budgets, evidence modes, and PostToolUse evidence behavior are
   unusually rigorous for a Claude Code plugin.
4. Trust-aware installation: dry-run/apply/remove paths and trust metadata make
   hook installation reviewable instead of magical.
5. Cross-runtime conformance: Claude and Codex surfaces are checked against a
   runtime contract.
6. Local trace/eval/trend base: workflow trace schemas, scenario fixtures,
   trend snapshots, and trace-to-scenario promotion form a usable local
   observability loop.
7. Durable loop kernel: state, evidence, decisions, actions, and fixtures give
   loop behavior an executable contract.
8. Entropy cleanup: P11 turns stale plans, capture-only candidates, refs, and
   mirror drift into structured cleanup actions.
9. Conservative security posture: default hooks stay narrow, external telemetry
   is not default, and strict modes are staged.

## Current Athanor Gaps

1. No runtime execution adapter. Athanor does not yet classify live work into
   solo, subagent wave, dynamic workflow, agent team, or worktree backend.
2. Worktree isolation is not first-class in the live command flow. It is
   documented/deferred, but not a selected backend.
3. Dynamic workflows are not used as a native fanout target.
4. Agent teams are not modeled as an optional, experimental backend with cost
   and coordination constraints.
5. Live trace emitters are missing from the real commands. P10 is plumbing, not
   full instrumentation.
6. No OTel vocabulary/export mapping.
7. Eval fixtures are not portable episodes with setup, sandbox, scorer, and
   evaluator isolation metadata.
8. No machine-readable harness decision ledger tying harness edits to expected
   metric changes and later outcomes.
9. Memory/lesson quality is not trace-evaluated. Lessons exist, but promotion
   and decay are not driven by measured scenario impact.
10. Plugin token/cost budget is not yet a release gate, even though Claude now
    exposes projected plugin token costs.

## Scorecard After P11

| Dimension | Score | Read |
| --- | ---: | --- |
| Command/workflow phase design | 9.5 | Coherent, practical command topology. |
| Thin leader/context isolation | 9.4 | Strong design; needs native backend selection. |
| Hook safety and evidence | 9.7 | Best current area. |
| Hook performance discipline | 9.6 | Gate and trend snapshot both exist. |
| Trust/install engineering | 9.4 | Strong; official distribution smoke can lift it. |
| Cross-runtime conformance | 9.5 | Real gate, CI-backed. |
| Local eval harness | 9.45 | Strong fixtures; portable episodes still missing. |
| Durable loop engineering | 9.45 | Good local loop kernel; live integration remains. |
| Entropy cleanup | 9.2 | P11 closes the biggest drift gap; still non-strict and read-only. |
| Live observability | 8.6 | Trace/trend base exists; command-level emitters missing. |
| Runtime backend selection | 7.8 | Largest gap after P11. |
| Agent-team/dynamic-workflow readiness | 7.8 | Concepts exist; no adapter or live backend contract. |
| Worktree isolation | 7.8 | Recognized but not selected/enforced by workflow. |
| OTel/interoperability | 7.4 | Local-first is good; export/mapping absent. |
| Benchmark/sandbox export | 8.0 | Fixtures are useful; benchmark-grade isolation/export missing. |
| Harness self-evolution | 7.1 | No decision observability ledger yet. |
| Memory quality loop | 8.2 | Local lessons exist; impact is not eval-driven. |
| Marketplace/distribution UX | 8.8 | Packaging is decent; token/cost and zip/install smoke should improve. |
| Security/permission posture | 9.2 | Conservative defaults; keep experimental surfaces opt-in. |

## Overbuilt Or Risky Areas

1. More default hooks. The catalog can contain candidates, but defaults should
   remain narrow until replay evidence and performance budgets justify them.
2. Default external telemetry. OTel/export must stay opt-in.
3. Agent teams as a default path. Claude docs mark them experimental and
   costly; use only when peer coordination matters.
4. Heavy LLM-judge release gates. Deterministic gates should remain primary.
5. Monolithic instruction growth. Keep top-level guidance short and route to
   focused docs.
6. Stale reference clones as hidden truth. P11 surfaces staleness; future
   research must refresh or annotate refs before relying on them.
7. Automated deletion. P11 should remain a sensor until cleanup policies are
   proven.

## Underbuilt Areas

1. Runtime adapter: a decision layer that selects execution backend and
   isolation policy.
2. Live trace emission from actual commands.
3. Optional OpenTelemetry vocabulary/export.
4. Eval episode packaging and evaluator isolation.
5. Harness decision ledger for self-evolution.
6. Trace-to-memory quality loop.
7. Plugin cost/token budget checks using `claude plugin details` when
   available.
8. Distribution smoke: validate manifest, load plugin zip, and verify
   marketplace pins.

## Add

1. P12 runtime execution adapter.
   - Read-only first: classify task shape and recommend backend.
   - Inputs: task risk, estimated file count, parallelism, same-file conflict
     risk, long-running flag, isolation requirement, required capabilities.
   - Outputs: backend, isolation policy, warnings, fallback backend, and
     reasons.

2. P13 live command trace emitters.
   - Emit `workflow.started`, `worker.started`, `loop.decision`,
     `verification.result`, `workflow.finished`, and escalation events from
     real command flows.
   - Store local JSONL by default.
   - Promote reviewed traces into deterministic fixtures.

3. P14 optional OTel vocabulary/export adapter.
   - Map local workflow/tool/agent/eval events into GenAI/agent-style span
     concepts.
   - Keep dependency-free local mode as default.
   - Redaction and privacy rules must be explicit.

4. P15 eval episode packaging.
   - Add episode metadata: setup, command, files, scorer, sandbox hints,
     hidden evaluator boundary.
   - Preserve fast local CI fixtures.
   - Add benchmark-hardening checks inspired by evaluator-isolation failures.

5. P16 distribution and plugin cost smoke.
   - Run official `claude plugin validate` where available.
   - Smoke `--plugin-dir` with directory and zip.
   - Capture `claude plugin details` cost output when available and enforce a
     soft always-on budget.

6. P17 trace-to-memory quality loop.
   - Promote lessons only when backed by trace/eval evidence.
   - Decay stale lessons.
   - Test whether lesson injection improves or at least does not degrade
     scenario outcomes.

7. P18 harness decision ledger.
   - Each harness change declares expected metric movement.
   - Later trend snapshots check the prediction.
   - This is the practical first step toward AHE-style decision observability.

## Remove Or De-Emphasize

1. Old scorecards that still describe pre-P8/P9/P10/P11 gaps as current.
2. Any doc language that implies P10 is complete live tracing.
3. Capture-only hook candidates without source refs, review dates, or a clear
   decision path.
4. Stale refs without freshness notes.
5. Duplicate command/agent surfaces that do not change a routing decision.
6. Claims that agent teams are stable/default; keep the experimental caveat.
7. Any "strict by default" migration that would surprise existing installs.

## Updated Priority

1. P12 runtime execution adapter.
2. P13 live command trace emitters.
3. P14 OTel vocabulary/export adapter.
4. P15 eval episode packaging and evaluator isolation.
5. P16 distribution/plugin cost smoke.
6. P17 trace-to-memory quality loop.
7. P18 harness decision ledger.

P12 remains the best next move because it closes the largest remaining
workflow gap without needing to launch experimental backends by default. It can
be implemented as a decision contract first, then later connected to native
Claude dynamic workflows, agent teams, and worktrees when the environment
supports them.

## Architecture Review

The safest architecture is layered:

1. Keep Athanor's local gates as the deterministic base.
2. Add a runtime adapter that selects a backend but does not initially launch
   experimental surfaces.
3. Make every live backend write the same local trace contract.
4. Use traces to promote eval fixtures and trend snapshots.
5. Only after trace coverage exists, add interop/export and memory promotion.
6. Only after measurable trends exist, add harness self-evolution ledgers.

This sequencing avoids the common failure mode: adding autonomy before adding
observability and cleanup.

## Bottom Line

Athanor is already above-average as a Claude Code plugin and strong as a local
harness. It is not yet a full modern agent-runtime platform. To get every
dimension above 9.5, the next work must shift from more static checks to
runtime selection, live traces, portable eval packaging, and measurable harness
evolution.
