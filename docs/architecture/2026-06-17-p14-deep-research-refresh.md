# P14 Deep Research Refresh: Workflow, Loop, Harness, And Athanor

Date: 2026-06-17
Local basis: `main` after P13 live command trace emitters.
Purpose: refresh the workflow/loop/harness comparison after P12 and P13, then
identify the remaining gaps before P14.

## Executive Verdict

Athanor is now past the "good Claude Code plugin" threshold and is closer to a
local software-agent harness. The strong areas are executable rather than
persuasive: hook replay, evidence gates, trust-aware install/remove, runtime
backend recommendation, workflow trace schemas, live trace emission anchors,
durable loop fixtures, cross-runtime conformance, and entropy checks.

The current external frontier is no longer prompt engineering. It is harness
engineering: repository knowledge, constraints, isolation, traces, evals,
feedback loops, cleanup, and controlled autonomy. Against that frontier,
Athanor is strong on local control and deterministic gates, but still below
9.5/10 in four places:

1. OpenTelemetry / GenAI vocabulary interoperability.
2. Portable eval episode packaging and evaluator isolation.
3. Trace-to-memory quality loops.
4. Harness decision observability for self-improvement.

Overall current scores:

- Claude Code workflow plugin: 9.55/10
- Local deterministic harness: 9.55/10
- Modern agent-runtime platform: 9.10/10

The next best move is P14: an opt-in, dependency-free OTel vocabulary/export
adapter over the P13 local traces.

## Sources Reviewed

Primary and high-signal references checked on 2026-06-17:

- OpenAI, "Harness engineering: leveraging Codex in an agent-first world"
  (2026-02-11): https://openai.com/index/harness-engineering/
- Anthropic, "Building effective agents" (2024-12-19):
  https://www.anthropic.com/engineering/building-effective-agents
- Claude Code hooks guide:
  https://code.claude.com/docs/en/hooks-guide
- Claude Code hooks reference:
  https://code.claude.com/docs/en/hooks
- Claude Agent SDK hooks:
  https://code.claude.com/docs/en/agent-sdk/hooks
- OpenAI Agents SDK guide:
  https://developers.openai.com/api/docs/guides/agents
- OpenAI Agents SDK tracing:
  https://openai.github.io/openai-agents-python/tracing/
- OpenTelemetry GenAI attribute registry:
  https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/registry/attributes/gen-ai.md
- OpenTelemetry GenAI agent spans:
  https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md
- OpenTelemetry GenAI spans and tool spans:
  https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-spans.md
- OpenTelemetry GenAI events:
  https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-events.md
- LangGraph persistence:
  https://docs.langchain.com/oss/python/langgraph/persistence
- LangGraph time travel:
  https://docs.langchain.com/oss/python/langgraph/use-time-travel
- Temporal for AI:
  https://temporal.io/solutions/ai
- OpenAI Evals guide:
  https://developers.openai.com/api/docs/guides/evals
- Inspect AI:
  https://inspect.aisi.org.uk/
- LangSmith trajectory evals:
  https://docs.langchain.com/langsmith/trajectory-evals
- LangChain Agent Evals:
  https://docs.langchain.com/oss/python/langchain/test/evals
- DSPy:
  https://dspy.ai/
- "The Last Harness You'll Ever Build" (arXiv, 2026):
  https://arxiv.org/html/2604.21003v1

## External Baseline

### Workflow Engineering

Anthropic's production pattern language remains the clean baseline: keep
systems simple, add autonomy only when it buys measurable performance, and
choose among prompt chaining, routing, parallelization, orchestrator-workers,
and evaluator-optimizer rather than treating every task as a fully autonomous
agent.

OpenAI's 2026 harness work adds a practical engineering lesson: agent velocity
depends on repository legibility, per-worktree app/runtime isolation,
queryable logs/metrics/traces, short top-level instructions that route to
deeper docs, and mechanical architecture constraints.

Athanor match:

- Strong command topology: discuss, analyze, debug, plan, work, review, lfg,
  lfg-goal.
- P12 now gives a deterministic runtime backend recommendation contract.
- Remaining gap: the adapter recommends dynamic-workflow, agent-team, and
  worktree paths, but does not yet launch or probe those native surfaces.

### Loop Engineering

Loop engineering is the action, observation, decision, retry, escalation, and
termination cycle. A good loop must prove progress, avoid unbounded retries,
preserve state, and convert failures into useful next actions.

Athanor match:

- Strong: durable loop state/evidence, lfg-goal semantics, stop/evidence gates,
  circuit breaker, no-progress decisions, and trace scenario evals.
- P13 improves the live side by adding command-skill trace anchors.
- Remaining gap: trace outcomes do not yet drive memory promotion or harness
  decision review.

### Harness Engineering

The modern harness is the environment around the model: task specs, repo maps,
skills, tool access, permissions, state, traces, tests, reviews, cleanup, and
release gates. The important distinction is that prompts advise while harnesses
enforce.

Athanor match:

- Very strong local harness discipline: scripts, schemas, fixtures, CI gates,
  hook replay, trust install/remove, runtime adapter, and live trace emitter.
- Strong conservative posture: no default external telemetry and no broad hook
  expansion just to collect more signals.
- Remaining gap: no machine-readable decision ledger that declares expected
  metric movement for harness edits and checks the outcome later.

### Observability And Interoperability

OpenAI Agents SDK tracing records end-to-end workflows, agent spans, generation
spans, tool calls, handoffs, guardrails, and custom events. OpenTelemetry's
GenAI conventions now include development-stage attributes and operations such
as `gen_ai.workflow.name`, `gen_ai.agent.name`, `gen_ai.conversation.id`,
`gen_ai.operation.name`, `invoke_workflow`, `invoke_agent`, `execute_tool`,
`plan`, and evaluation attributes. The same specs warn that message, tool
argument, tool result, memory, and instruction content can be sensitive and
should be opt-in.

Athanor match:

- P13 local JSONL traces are the right base.
- Missing: a local export envelope and mapping that lets Athanor traces be
  understood by OTel-style tools without changing the default runtime.
- P14 should not send data anywhere. It should emit a local JSON export and make
  raw message/evidence/reference content opt-in.

### Eval And Benchmark Engineering

Inspect, OpenAI Evals, LangSmith AgentEvals, and LangChain Agent Evals all
point in the same direction: evaluate trajectories, not only final answers.
Deterministic trajectory match is fast and cheap when expected tool paths are
known; LLM-as-judge is useful for fuzzy behavior but should not replace hard
gates. Inspect also raises the bar for sandboxed task packaging.

Athanor match:

- Good local scenario runner and deterministic trace graders.
- Missing: portable episode packages with setup, commands, expected checks,
  scorer metadata, sandbox hints, and evaluator-isolation rules.

### Harness Self-Evolution

The 2026 harness-evolution work frames the harness itself as the optimization
target. A worker executes, an evaluator diagnoses and scores, and an evolution
agent modifies prompts, tools, orchestration, observations, and model config
based on full history. This is more aggressive than Athanor should enable by
default, but the observability requirement is relevant now.

Athanor match:

- Component observability is good because most harness surfaces are files.
- Experience observability is improving through P13 traces.
- Decision observability is missing: harness edits do not declare a prediction,
  metric target, or later outcome check.

## Scorecard After P13

| Dimension | Score | Read |
| --- | ---: | --- |
| Command/workflow phase design | 9.6 | Clear command map with plan/execute separation. |
| Thin leader/context isolation | 9.55 | Strong core posture; top-level guidance remains focused. |
| Hook safety and evidence | 9.7 | Mature replay, evidence modes, budgets, and conservative defaults. |
| Hook performance discipline | 9.6 | Budget and trend gates are in place. |
| Trust/install engineering | 9.45 | Apply/remove/dry-run are reviewable; official distribution smoke can lift it. |
| Runtime backend selection | 9.15 | P12 made it executable; live launcher/probe remains deferred. |
| Worktree/runtime isolation | 8.6 | Recommended in P12 but not first-class live execution yet. |
| Agent-team/dynamic-workflow readiness | 8.7 | Decision contract exists; native backend use remains opt-in future work. |
| Cross-runtime conformance | 9.5 | CI-backed contract. |
| Local eval harness | 9.45 | Strong local trace graders; portable episodes still missing. |
| Durable loop engineering | 9.5 | Good state/evidence/decision model. |
| Live observability | 9.15 | P13 added emitters and anchors; nested span coverage is not exhaustive. |
| OTel/interoperability | 7.6 | Biggest current gap; P14 should address this. |
| Benchmark/sandbox export | 8.15 | Needs episode packaging and isolation metadata. |
| Harness self-evolution | 7.4 | Needs decision ledger and outcome checks. |
| Trace-to-memory quality loop | 8.2 | Lessons exist; measured promotion/decay is missing. |
| Marketplace/distribution UX | 8.85 | Needs official validate/zip/install/cost smoke where CLI supports it. |
| Security/permission posture | 9.3 | Conservative defaults remain the right tradeoff. |

## What Is Already Good

1. Repository-as-system-of-record posture is aligned with modern harness
   engineering.
2. The command surface is small and phase-oriented instead of feature-bloated.
3. P12 closes the old "team mode is generic" issue by making backend choice
   machine-checkable.
4. P13 closes the old "trace layer is fixture-only" issue by giving command
   skills a local emitter and lifecycle anchors.
5. Hook safety is unusually strong for a plugin: payload replay, redaction,
   evidence stages, performance budgets, and trust-aware install/remove.
6. The deterministic-first eval posture is correct. LLM judges should be
   additive and scoped, not primary release gates.
7. External telemetry is not default. This is a strength, not a missing feature.

## What Is Still Missing

1. OTel vocabulary/export mapping over local traces.
2. Privacy-safe export defaults for messages, evidence, references, tool
   arguments, tool results, and memory records.
3. Portable eval episode packaging with setup, scorer, sandbox, limits, and
   evaluator-isolation metadata.
4. Trace-to-memory quality loop that promotes lessons only when traces show
   positive or at least non-regressive impact.
5. Harness decision ledger that ties harness edits to expected metric movement
   and later observed outcome.
6. Native runtime launcher/probe for dynamic workflows, agent teams, and
   worktrees. P12 decides; it does not execute.
7. Distribution/cost smoke using official Claude plugin commands when present.
8. Staleness cleanup for old scorecards and old phase-number references.

## Overbuilt Or Risky

1. More default hooks. Add only when replay evidence and latency budgets justify
   it.
2. Default external telemetry. Keep OTel/export local and opt-in.
3. Agent teams as default. They are coordination-heavy and should remain
   explicit.
4. LLM-as-judge as a release gate. Use deterministic gates first.
5. Monolithic instruction growth. Keep top-level guidance as a map.
6. Strict evidence defaults for existing installs. Stage strictness by new
   install or explicit user opt-in.
7. Self-evolving harness edits without decision ledger and rollback evidence.

## Remove Or De-Emphasize

1. Stale pre-P12/P13 scorecards that still list runtime adapter and live trace
   emitters as fully open gaps without status notes.
2. Old phase-number labels in `docs/STATE.md` that collide with the current
   P14/P15/P16/P17/P18 research roadmap.
3. Capture-only hook candidates with no replay evidence, review date, or clear
   decision path.
4. Stale refs without freshness metadata.
5. Any doc language implying P13 is exhaustive automatic tracing. It is command
   anchor tracing, not full nested span instrumentation.

## Add Next

### P14: OTel Vocabulary And Local Export Adapter

Implement a stdlib-only exporter from Athanor workflow traces to a local
OTel-style JSON envelope.

Required properties:

- no network export;
- no required OpenTelemetry dependency;
- `gen_ai.operation.name` mapping using known values where applicable:
  `invoke_workflow`, `invoke_agent`, `execute_tool`, `plan`;
- `gen_ai.workflow.name`, `gen_ai.agent.name`, `gen_ai.conversation.id`, and
  `gen_ai.evaluation.*` where source data supports them;
- Athanor namespaced attributes for fields not covered by current GenAI
  conventions;
- raw `message`, `evidence`, and `references` omitted by default;
- explicit flags for including sensitive content.

### P15: Eval Episode Packaging

Export trace scenarios as portable local episodes:

- task id and intent;
- setup files and commands;
- allowed files or sandbox hints;
- expected trajectory or score rules;
- scorer metadata;
- evaluator isolation notes;
- limits for time, retries, and parallelism.

### P16: Distribution And Cost Smoke

Add release-time checks for:

- plugin manifest validation where Claude CLI supports it;
- zip or plugin-dir smoke;
- marketplace version pins;
- projected token/cost surface where `claude plugin details` supports it.

### P17: Trace-To-Memory Quality Loop

Use trace/eval evidence to decide lesson promotion, decay, and quarantine. A
lesson should not become durable just because it was written; it should earn
promotion through scenario outcomes.

### P18: Harness Decision Ledger

For each harness change, record:

- changed harness component;
- expected metric direction;
- target signal;
- verification command;
- later observed result;
- rollback or follow-up decision.

This is the practical first step toward harness self-evolution without handing
over unsafe autonomy.

## Bottom Line

Yes, Athanor is already doing loop engineering. It is also doing meaningful
harness engineering. What it is not yet doing is full harness self-evolution.
The difference is evidence closure: traces must feed eval episodes, memory
promotion, and decision ledgers before the system can safely claim it improves
its own harness.

The current highest-leverage sequence remains:

1. P14 OTel vocabulary/local export.
2. P15 eval episode packaging.
3. P16 distribution/cost smoke.
4. P17 trace-to-memory quality loop.
5. P18 harness decision ledger.

P14 is first because P13 has created the trace substrate and the next gap is
interoperable vocabulary with strict privacy defaults.
