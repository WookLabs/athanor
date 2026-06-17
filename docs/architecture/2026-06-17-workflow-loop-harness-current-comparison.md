# Current Workflow, Loop, And Harness Engineering Comparison

Date: 2026-06-17
Branch basis: `main` at `e184e33`
Local basis: P8 trust installer, P9 cross-runtime conformance, and P10
observability trend snapshots are implemented, merged, and pushed.

## Executive Verdict

Athanor now sits in a strong position as a Claude Code workflow plugin and a
local agent harness. Its best properties are not "more prompts"; they are the
machine-checkable surfaces around the prompts: hook replay, performance
budgets, trust-aware hook installation, runtime conformance checks, workflow
trace fixtures, durable loop fixtures, and trend snapshots.

Against the 2026 external baseline, the next gap is narrower than before:
Athanor no longer lacks a local trace/eval/trend story, but it still lacks a
runtime adapter layer that makes those signals first-class during live
multi-agent execution. The modern frontier is:

1. isolate parallel runs with worktrees;
2. run larger fanout through dynamic workflows or agent teams;
3. emit structured traces during live `plan`, `work`, `review`, `lfg`, and
   `lfg-goal` runs;
4. promote failed real traces into regression fixtures;
5. keep repository knowledge, docs, candidates, and generated mirrors fresh
   through recurring cleanup;
6. optionally align trace vocabulary with OpenTelemetry-style agent semantics
   without making external telemetry a default dependency.

In short: Athanor is strong on local deterministic harness engineering, good on
loop engineering, and still behind the frontier on live orchestration adapters,
machine-readable observability interop, and continuous entropy cleanup.

## Sources Reviewed

Primary and high-signal sources:

- OpenAI, "Harness engineering: leveraging Codex in an agent-first world"
  (2026-02-11): https://openai.com/index/harness-engineering/
- Anthropic, "Building effective agents" (2024-12-19):
  https://www.anthropic.com/engineering/building-effective-agents
- Claude Code plugins:
  https://code.claude.com/docs/en/plugins
- Claude Code plugin marketplaces:
  https://code.claude.com/docs/en/plugin-marketplaces
- Claude Code hooks:
  https://code.claude.com/docs/en/hooks
- Claude Code goals:
  https://code.claude.com/docs/en/goal
- Claude Code dynamic workflows:
  https://code.claude.com/docs/en/workflows
- Claude Code agent teams:
  https://code.claude.com/docs/en/agent-teams
- Claude Code worktrees:
  https://code.claude.com/docs/en/worktrees
- Martin Fowler / Thoughtworks, "Harness engineering for coding agent users"
  (2026-04-02): https://martinfowler.com/articles/harness-engineering.html
- Datadog, "Closing the verification loop: Observability-driven harnesses for
  building with agents" (2026-03-09):
  https://www.datadoghq.com/blog/ai/harness-first-agents/
- Arize, "Self-Improving Agents: the Agent Harness for Reliable Code":
  https://arize.com/blog/closing-the-loop-coding-agents-telemetry-and-the-path-to-self-improving-software/
- LangGraph overview:
  https://docs.langchain.com/oss/python/langgraph/overview
- LangChain, "State of Agent Engineering":
  https://www.langchain.com/state-of-agent-engineering
- OpenAI Agents SDK guide:
  https://developers.openai.com/api/docs/guides/agents
- OpenAI Agents SDK tracing:
  https://openai.github.io/openai-agents-python/tracing/
- OpenTelemetry AI agent observability:
  https://opentelemetry.io/blog/2025/ai-agent-observability/
- Inspect AI sandboxing:
  https://inspect.aisi.org.uk/sandboxing.html
- Terminal-Bench:
  https://www.tbench.ai/
- MindStudio, "What Is Loop Engineering?":
  https://www.mindstudio.ai/blog/what-is-loop-engineering-ai-coding-agents

## External Baseline

### Workflow Engineering

Anthropic's framing remains the cleanest baseline: use simple, composable
patterns first, distinguish predefined workflows from agents that dynamically
choose their own tool/process path, and only pay the cost of extra autonomy
when it buys measurable performance. Their named patterns map well to Athanor:
prompt chaining, routing, parallelization, orchestrator-workers, and
evaluator-optimizer.

Claude Code's 2026 surface has expanded beyond slash-command workflows:

- `/goal` keeps a session working until a measurable condition is met.
- Dynamic workflows let Claude write reusable JavaScript orchestration scripts
  that launch many subagents in the background.
- Agent teams coordinate multiple Claude Code instances with independent
  contexts and peer communication.
- Worktrees isolate parallel sessions so edits do not collide.
- Hooks provide deterministic lifecycle controls.
- Plugins package skills, agents, hooks, MCP servers, LSP servers, monitors,
  and default settings.

External lesson: workflow design is now a coordination problem, not just a
prompt/command problem.

### Loop Engineering

The useful definition is practical: a loop is an action-feedback-decision cycle
with explicit success, failure, and escalation exits. A well-engineered loop
must prevent unbounded retries, distinguish recoverable failures from blockers,
budget tool calls, and prove progress through evidence.

Claude `/goal` is a user-facing example: after every turn, a separate evaluator
checks the completion condition and either clears the goal or starts another
turn. Athanor's `lfg-goal` and durable loop controller are the local harness
version of the same idea, with stronger deterministic fixture coverage but less
integration into Claude's native session/runtime surfaces.

External lesson: Athanor's loop kernel is real, but the next step is live
dispatch/resume/instrumentation, not another abstract loop document.

### Harness Engineering

The modern harness is the agent's operating environment: instructions, repo
maps, skills, tools, permissions, tests, custom linters, structural rules,
trace access, evals, evidence ledgers, and cleanup. OpenAI's harness article is
especially relevant because it treats the repo as the system of record, makes
apps bootable per worktree, exposes logs/metrics/traces to agents, keeps plans
and docs versioned, and runs recurring cleanup tasks to fight drift.

Fowler's feedforward/feedback distinction is the clearest local design lens:

- feedforward controls: maps, skills, architecture docs, rules, constraints;
- feedback controls: tests, static analysis, hook gates, traces, evals,
  reviews, runtime telemetry.

External lesson: Athanor is strongest when it encodes judgment into executable
checks. It should keep default runtime controls narrow and make new controls
earn their place through failure evidence.

### Eval And Observability Engineering

The center of gravity is trace-first. OpenAI Agents SDK traces model
generations, tool calls, handoffs, guardrails, and custom events. Arize argues
that traces become documentation of what the system actually did; without
trace-backed evals, claimed improvement is guesswork. LangChain's 2026 survey
shows observability adoption is high while eval adoption still trails, which
matches the market gap: many systems can see traces, fewer convert them into
quality improvement loops.

OpenTelemetry's AI agent observability work matters because it is the emerging
interoperability layer. For Athanor, the right move is not to add a heavy OTel
dependency by default. The right move is to define an optional vocabulary/export
adapter so local traces can later flow into external tools without rewriting
the harness.

External lesson: P10's local snapshots are correct, but live trace capture and
OTel-compatible naming are the next maturity steps.

### Benchmark And Sandbox Engineering

Inspect and Terminal-Bench show the benchmark baseline:

- episode/task definitions must be runnable in isolated environments;
- files/setup/scripts belong to the task package;
- docker-style sandboxes are normal for higher-risk evals;
- terminal-agent tasks now measure long-horizon, end-to-end work rather than
  single-turn patch generation.

Athanor's current fixtures are intentionally local and cheap. That is good for
CI, but it should grow an "episode package" shape that can be exported to
heavier harnesses later.

External lesson: do not import a full benchmark stack yet; add an adapter shape
that preserves Athanor's local speed while making future benchmark export
straightforward.

## Current Athanor Strengths

1. Clear command topology. `discuss`, `analyze`, `debug`, `plan`, `work`,
   `review`, `lfg`, and `lfg-goal` map to recognizable engineering phases.
2. Thin leader and clean-context workers. This still matches current harness
   thinking: keep the primary context small and route work to specialized
   workers.
3. Strong maker/checker discipline. Cross-model planning, adversarial review,
   Stop verification, and fixture gates make quality checks explicit.
4. Evidence-backed hooks. Hook capture, replay, redaction, fixture tests, and
   performance budgets are mature for a plugin-scale system.
5. Trust-aware installation. P8 closed the major gap between "dry-run plan" and
   reviewable apply/remove behavior.
6. Cross-runtime conformance. P9 prevents Claude/Codex metadata drift from
   silently breaking packaging assumptions.
7. Local trace/eval/trend primitives. P6 and P10 give Athanor a structured
   trace contract, scenario runner, trace promotion CLI, and trend snapshots.
8. Durable loop decision kernel. P7 gives loop behavior explicit state,
   evidence, decision events, and fixtures instead of relying on prose.
9. Conservative default runtime cost. The enabled hook surface is intentionally
   narrow, and that restraint is a feature.

## Current Athanor Gaps

1. Live instrumentation is still partial. P10 gives local snapshots and trace
   promotion, but the real command flows do not yet emit end-to-end traces by
   default.
2. Dynamic workflow and agent-team integration is missing. Athanor can describe
   parallel workers, but it does not yet provide an adapter that chooses between
   subagents, dynamic workflows, agent teams, and worktrees based on task shape.
3. Worktree isolation is not first-class. OpenAI and Claude docs both point to
   per-worktree app/runtime isolation for serious parallel work.
4. OTel compatibility is absent. Athanor has local schemas, but no optional
   bridge to GenAI/agent span vocabulary.
5. Entropy cleanup is manual. OpenAI-style doc gardening, stale-plan cleanup,
   candidate pruning, ref freshness checks, and generated mirror audits are not
   yet one executable loop.
6. Benchmark export is thin. Fixtures are good, but not packaged as portable
   task episodes with sandbox/setup metadata.
7. Marketplace/distribution verification can go further. The repo has plugin
   metadata, but should regularly run official `claude plugin validate` where
   available and maintain a release-packaging smoke path.
8. Memory is local but not deeply evaluated. Lessons exist, but there is no
   trace-to-memory quality loop or stale-memory pressure test.
9. Domain-quality evals are underdeveloped. Deterministic evals are correct as
   the base, but there is no calibrated domain-review queue for the cases that
   cannot be decided by static checks.

## Scorecard

Scores reflect Athanor after P8-P10, not the older pre-P8 state.

| Dimension | Score | Read |
| --- | ---: | --- |
| Command/workflow phase design | 9.5 | Strong, coherent command surface with plan/execute separation. |
| Thin leader/context isolation | 9.4 | Strong conceptually; needs native worktree/team adapter for current Claude surfaces. |
| Hook safety and evidence | 9.7 | Best-in-class local rigor for a plugin-scale hook system. |
| Hook performance discipline | 9.6 | P5 plus P10 snapshots give both gate and trend primitive. |
| Trust/install engineering | 9.3 | P8 closes apply/remove safety; official CLI validation and release smoke can lift it. |
| Cross-runtime conformance | 9.5 | P9 gives a real gate; maintain as schemas evolve. |
| Local eval harness | 9.4 | Trace schemas and scenario runner are strong; episode export remains missing. |
| Live observability | 8.6 | Snapshot/trend exists; command-level live spans are the gap. |
| Loop engineering | 9.3 | Durable decision kernel is strong; live dispatch/resume queue is still missing. |
| Agent-team/dynamic-workflow readiness | 7.9 | Current largest workflow gap after P10. |
| Worktree/runtime isolation | 7.8 | Recognized but not implemented as an execution backend. |
| OTel/interoperability | 7.4 | Local-first is good, but no mapping/export exists. |
| Entropy cleanup | 8.1 | Tests/docs are strong; recurring garbage-collection loop missing. |
| Marketplace/distribution UX | 8.7 | Good packaging; more official validation and install smoke needed. |
| Security/permission posture | 9.1 | Conservative default hooks and trust install are good; external telemetry must stay opt-in. |

Overall:

- Claude Code workflow plugin: 9.3/10
- Local harness engineering system: 9.4/10
- Modern loop/agent-runtime platform: 8.7/10

The rating is now pulled down less by local verification and more by live
runtime integration.

## Overbuilt Or Risky Areas

1. More default hooks. The catalog can remain broad, but enabling more hooks by
   default would increase latency and user surprise.
2. Heavy LLM-judge gates. Deterministic checks should stay primary. Add
   inferential checks only where real trace failures show deterministic checks
   are insufficient.
3. External telemetry by default. Observability should be local-first and
   privacy-preserving. OTel/export should be explicit opt-in.
4. A giant monolithic instruction file. OpenAI's repo-map lesson applies
   directly: keep the top-level file short and point to indexed docs.
5. Autonomous merge/deploy as a default behavior. Athanor can support stronger
   autonomy, but it should remain gated by trust state, tests, and explicit user
   intent.
6. More registered agents for their own sake. The current smaller agent surface
   is healthier than the old vendored bloat.

## Add

1. P11 entropy cleanup loop:
   - stale docs/plans/reference checks;
   - generated mirror drift check;
   - hook catalog candidate aging;
   - ref repository freshness report;
   - quality-grade snapshot;
   - one CLI gate that emits JSON and can run in CI.
2. P12 live runtime adapter:
   - classify task shape as solo, subagent, dynamic workflow, agent team, or
     worktree run;
   - define isolation policy and collision rules;
   - preserve existing command UX while delegating wider fanout to native
     Claude surfaces when available.
3. P13 command-level trace emitters:
   - emit workflow trace events from `plan`, `work`, `review`, `lfg`, and
     `lfg-goal`;
   - attach evidence paths, test commands, loop decisions, worker roles, and
     stop/escalation reasons;
   - keep local JSONL as the default store.
4. P14 optional OTel vocabulary/export adapter:
   - map local events to agent/workflow/tool/eval span concepts;
   - do not add a required runtime dependency;
   - document privacy, redaction, and opt-in export.
5. P15 eval episode packaging:
   - export trace/eval scenarios as portable episode packages;
   - include setup files, commands, expected checks, and sandbox hints;
   - keep the default CI runner local and fast.
6. P16 distribution smoke:
   - run official `claude plugin validate` when present;
   - package zip smoke with `--plugin-dir` where CLI support exists;
   - validate marketplace version pins and stale manifest versions.
7. P17 trace-to-memory quality loop:
   - only promote lessons when backed by trace/eval evidence;
   - decay stale lessons;
   - test that injected memory improves or at least does not degrade scenario
     outcomes.

## Remove Or De-Emphasize

1. Stale pre-P8 audit scores that still list trust install as the primary open
   gap without noting P8 is complete.
2. Any docs that imply P6/P10 are live instrumentation rather than local
   trace/eval/trend primitives.
3. Capture-only hook candidates that have not earned replay evidence or a clear
   user-facing decision role.
4. Generated mirrors or copied reference notes with no source/date/freshness
   marker.
5. Commands or agents that duplicate the same phase without a distinct decision
   point.

## Next Work Recommendation

Proceed with P11 before P12.

Reason: P12 will add more execution surfaces and therefore more entropy. The
OpenAI and Fowler lessons both point to the same order: build the cleanup and
freshness controls before increasing autonomy. P11 should give Athanor an
executable "garbage collection" loop for docs, refs, hook candidates, generated
artifacts, and quality snapshots. After that, P12 can safely add dynamic
workflow, agent-team, and worktree adapters without making the repo harder for
future agents to reason about.

Proposed sequence:

1. P11: Entropy cleanup loop.
2. P12: Dynamic workflow / agent-team / worktree adapter.
3. P13: Live command trace emitters.
4. P14: Optional OTel vocabulary/export adapter.
5. P15: Eval episode packaging and benchmark export shape.
6. P16: Distribution validation smoke.
7. P17: Trace-to-memory quality loop.

