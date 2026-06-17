# Current Agent Workflow, Loop, And Harness Deep Research

Date: 2026-06-17
Branch: `feat/p8-trust-installer-apply`
Status basis: P5, P6, and P7 are implemented and merged to `main`; P8 has
architecture and implementation-plan documents on this branch but is not yet
implemented.

## Executive Verdict

Athanor is now a strong Claude Code workflow plugin and a good local harness.
Its strongest advantages are evidence-backed hooks, deterministic fixture
gates, conservative default runtime cost, a trace/eval contract, and a durable
loop controller. Against current 2026 practice, the remaining gap is not more
commands. The gap is converting the existing workflow into a live, observable,
trusted, resumable, and self-cleaning system.

The phrase "loop engineering" now applies directly. Claude Code has `/goal`,
dynamic workflows, agent teams, worktrees, scheduled tasks, and hooks as
first-class orchestration surfaces. OpenAI, Anthropic, LangSmith, Braintrust,
Inspect, Temporal, and Fowler-style harness literature all converge on the
same operating model:

1. give agents executable context and constraints;
2. isolate workers and tool boundaries;
3. record typed traces of what happened;
4. score traces with deterministic and calibrated evaluators;
5. promote failures into regression datasets;
6. persist loop state across interruptions;
7. keep trust, install, and cleanup policy explicit.

Athanor has the right skeleton. It still needs P8-P12 to clear a broad 9.5/10
standard across all current dimensions.

## Sources Reviewed

Official and high-signal web sources:

- Claude Code dynamic workflows:
  https://code.claude.com/docs/en/workflows
- Claude Code `/goal`:
  https://code.claude.com/docs/en/goal
- Claude Code hooks guide:
  https://code.claude.com/docs/en/hooks-guide
- Claude Code agent teams:
  https://code.claude.com/docs/en/agent-teams
- Claude Code parallel agents and worktree guidance:
  https://code.claude.com/docs/en/agents
- Claude Code worktrees:
  https://code.claude.com/docs/en/worktrees
- Claude Code plugin discovery and marketplaces:
  https://code.claude.com/docs/en/discover-plugins
  https://code.claude.com/docs/en/plugin-marketplaces
- Claude Code plugin reference:
  https://code.claude.com/docs/en/plugins-reference
- Claude Code scheduled tasks:
  https://code.claude.com/docs/en/scheduled-tasks
- Claude Code monitoring:
  https://code.claude.com/docs/en/monitoring-usage
- OpenAI harness engineering:
  https://openai.com/index/harness-engineering/
- OpenAI agent workflow evals:
  https://developers.openai.com/api/docs/guides/agent-evals
- OpenAI Agents SDK tracing:
  https://openai.github.io/openai-agents-python/tracing/
- Martin Fowler harness engineering:
  https://martinfowler.com/articles/harness-engineering.html
- LangSmith evaluation and feedback/trace loop:
  https://www.langchain.com/langsmith-platform
  https://www.langchain.com/blog/agent-observability-needs-feedback-to-power-learning
- Braintrust agent evaluation and observability:
  https://www.braintrust.dev/articles/agent-evaluation
  https://www.braintrust.dev/articles/agent-observability-complete-guide-2026
- Inspect AI:
  https://inspect.aisi.org.uk/
- Temporal durable agent workflows:
  https://temporal.io/blog/building-ai-agents-that-overcome-the-complexity-cliff
  https://temporal.io/blog/build-resilient-agentic-ai-with-temporal

Local ignored `ref/` comparison set:

| Ref | Local HEAD | Role |
| --- | --- | --- |
| `ai-boost-awesome-harness-engineering` | `e11cb2b` | Harness/eval/orchestration index |
| `alexei-led-cc-thingz` | `2e590b6` | Generated multi-runtime hook pipeline |
| `anthropics-claude-code` | `843959f` | Official examples |
| `anthropics-claude-plugins-official` | `ccdc03c` | Official marketplace examples |
| `anthropics-knowledge-work-plugins` | `9903b20` | Skills/MCP/plugin packaging reference |
| `cobusgreyling-loop-engineering` | `0dde427` | Loop/harness terminology reference |
| `disler-claude-code-hooks-mastery` | `052ad1c` | Hook lifecycle reference |
| `ElliotJLT-hooksmith` | `836fb7d` | Hook registry/install UX reference |
| `fricklers-claude-code-config` | `c86b358` | Practical personal hook config |
| `jeremylongshore-claude-code-plugins-plus-skills` | `57b5254b` | Marketplace/catalog scale reference |
| `karanb192-claude-code-hooks` | `ebcc2a2` | Safety hook corpus reference |
| `launchdarkly-labs-claude-code-session-start-hook` | `3bf625e` | SessionStart context hook reference |
| `obra-superpowers` | `b62616f` | Skill discipline and SessionStart reference |
| `openai-codex` | `1315198` | Codex hook/trust/managed-hook reference |
| `RoggeOhta-awesome-codex-cli` | `d23a320` | Codex ecosystem index |
| `shakacode-claude-code-commands-skills-agents` | `2c375be` | Command/skill/agent packaging |
| `sjnims-plugin-dev` | `7b2a821` | Plugin authoring reference |
| `UKGovernmentBEIS-inspect_ai` | `00de5ba` | Eval framework reference |

## External Baseline In 2026

### Workflow Engineering

The current baseline is multi-surface orchestration, not a single prompt or
one slash command. Claude Code now separates:

- `/goal` for repeated turns until a condition holds;
- dynamic workflows for rerunnable scripts that fan out subagents;
- agent teams for multiple independent Claude Code sessions;
- worktrees for edit isolation;
- hooks for deterministic lifecycle control;
- plugins and marketplaces for distribution;
- scheduled tasks for recurring automation.

Athanor already has strong command-level workflow design: `discuss`,
`analyze`, `debug`, `plan`, `work`, `review`, `lfg`, and `lfg-goal`. The gap is
that it still models parallelism and long-running execution mostly as
documents and local scripts rather than native adapters to dynamic workflows,
agent teams, and worktree-isolated runs.

### Harness Engineering

Modern harness work treats the agent environment as the product:
instructions, repo structure, tests, CI, plans, evidence ledgers, review
comments, dashboards, permissions, memory, and cleanup are all part of the
harness. Athanor is good here because it has repo-local plans, release gates,
hook replay, performance budgets, durable loop fixtures, and trace/eval
fixtures.

The remaining weakness is feedback depth. A production-grade harness should
preserve trend history, expose drift, and turn real failures into eval cases.
Athanor has point-in-time gates. It does not yet have a trendable local
observability layer.

### Loop Engineering

The useful definition is now concrete: a loop discovers work, executes through
isolated agents, checks evidence, persists state, decides the next action, and
stops or escalates on explicit conditions. Claude `/goal` is the user-facing
version. Temporal and similar durable execution runtimes are the production
version.

P7 gave Athanor a real local controller. That is a major improvement, but it is
not yet a live outer loop. It does not dispatch Claude Code sessions, create
worktrees, consume live traces, queue follow-up work, or resume dynamic
workflow runs. It is the decision kernel, not the full runtime.

### Eval And Observability Engineering

The direction is trace-first. OpenAI agent evals use traces, graders, datasets,
and eval runs. OpenAI Agents SDK tracing records LLM generations, tool calls,
handoffs, guardrails, and custom events. LangSmith and Braintrust both attach
feedback and scorers to traces, then use failures to improve datasets.

Athanor P6 is aligned but local. It defines a workflow trace schema and
deterministic scenario runner, and P7 emits a loop decision event. It still
does not instrument real `plan`, `work`, `review`, `lfg`, and `lfg-goal`
sessions end to end. It also lacks trace promotion and trend reports.

### Trust And Install Engineering

Claude plugins can include skills, agents, hooks, MCP servers, LSP servers, and
monitors. Marketplace docs and Codex managed-hook behavior both make trust a
first-order concern. A settings writer that installs hooks must be reversible,
reviewable, no-clobber, and hash-aware.

Athanor's P4 dry-run planner is the right safe starting point. P8 must now
complete the trust-aware apply/remove path before any higher-autonomy install
or deploy behavior is credible.

## Current Athanor Scorecard

Scores are current-state scores, not target scores.

| Dimension | Current | Target | Read |
| --- | ---: | ---: | --- |
| Evidence/replay rigor | 9.8 | 9.8 | Strong live-redacted/replay-gated hook evidence. This remains the best area. |
| Hook safety/default restraint | 9.7 | 9.7 | Narrow default hooks are correct. Do not broaden defaults without evidence. |
| Performance discipline | 9.5 | 9.6 | P5 budget gate makes hook cost executable. Trend history would improve it. |
| Workflow engineering | 9.3 | 9.6 | Strong commands and review loops. Needs live trace wiring and dynamic workflow/team adapters. |
| Harness engineering | 9.2 | 9.6 | Strong local gates and docs. Missing trendable observability and cleanup flywheel. |
| Loop engineering | 9.1 | 9.6 | P7 decision kernel is solid. Missing live queue/dispatch/resume/worktree integration. |
| Eval/observability | 8.9 | 9.6 | P6 local trace/eval is correct. Live instrumentation and trace promotion are missing. |
| Trust/install UX | 7.4 | 9.5 | P8 is only designed, not implemented. This is the largest current gap. |
| Cross-runtime portability | 8.2 | 9.5 | Matrix exists. Generator/conformance gate still missing. |
| Agent-team/worktree integration | 7.7 | 9.5 | Claude has moved here; Athanor still treats it as mostly deferred or conceptual. |
| Plugin distribution/onboarding | 8.4 | 9.5 | Plugin packaging exists. Marketplace/readme/test-with-others discipline is thin. |
| Context and memory engineering | 8.8 | 9.5 | Thin leader and clean workers are good. Trace-to-memory promotion and context index are missing. |
| Entropy control | 8.2 | 9.5 | Tests are strong, but stale docs, candidates, refs, and mirrors need an executable cleanup loop. |

Overall: 9.0/10 as a Claude Code workflow plugin, 8.8/10 as a modern
loop/harness platform. The difference is live orchestration and observability.

## What Athanor Does Well

1. Evidence-first policy. Hook claims are backed by fixtures, replay gates,
   provenance, and performance checks.
2. Conservative runtime cost. The default hook surface is intentionally small.
3. Strong maker/checker separation. Planning, work, review, LFG, Stop
   verification, and eval scenarios reinforce each other.
4. Good local determinism. The key gates can run in CI without external
   services.
5. Honest capability boundaries. Capture-only events are not mislabeled as
   supported enforcement.
6. Good command identity. The command surface maps to real developer phases
   instead of becoming a generic utility bucket.

## What Is Still Missing

1. P8 trust-aware installer apply/remove. This is the largest practical gap.
2. P9 cross-runtime conformance. Claude/Codex surfaces need one source of
   truth or a strict verifier.
3. P10 live trace adoption. P6 must move from fixture contract to actual
   workflow instrumentation.
4. P10 trend reports. Scenario scores, hook latency, stop reasons, and loop
   outcomes need local history.
5. P11 entropy loop. Stale docs, stale capture-only candidates, and generated
   mirrors need a cleanup gate.
6. P12 dynamic workflow/team/worktree adapter. Current Claude Code practice now
   includes dynamic workflows and agent teams; Athanor needs an explicit
   compatibility layer and isolation policy.
7. Trace-to-dataset promotion. Real failed traces should become regression
   scenarios.
8. Trust/distribution UX. Marketplace instructions, plugin test protocol, and
   trust-state review flow need to be first-class.

## Overbuilt Or Risky Areas

1. More default hooks would be counterproductive. The catalog can stay broad,
   but enabled hooks should stay narrow.
2. More registered agents are unnecessary. The current four registered agents
   avoid the previous collision problem.
3. A default LLM-judge eval layer is premature. Deterministic graders should
   stay primary until live traces show where subjective scoring adds value.
4. A full marketplace clone is not needed. Athanor needs trustworthy
   distribution, not a huge catalog.
5. Autonomous merge/deploy loops should remain gated. Trust install and live
   eval evidence must land first.
6. Dynamic workflows should not replace the existing command surface. They
   should become an execution backend for wide fanout and audits.

## Add, Keep, Remove

### Add

1. Trust-aware installer implementation:
   - hash/source trust state;
   - apply/remove;
   - backups and rollback;
   - no-clobber settings changes;
   - schema v2 reports.
2. Cross-runtime conformance:
   - one catalog-derived metadata source;
   - Claude/Codex manifest verification;
   - CI failure on drift.
3. Live trace emitters:
   - `plan`, `work`, `review`, `lfg`, `lfg-goal`;
   - correlation IDs across hooks and loop state;
   - trace promotion command.
4. Observability trends:
   - JSONL or SQLite local history;
   - hook latency over time;
   - scenario score changes;
   - loop stop reasons and escalation counts.
5. Entropy cleanup loop:
   - stale docs/plans scan;
   - stale capture-only candidate age report;
   - generated mirror drift report;
   - ref freshness report.
6. Dynamic workflow/team/worktree adapter:
   - decision rules for subagent vs dynamic workflow vs agent team;
   - worktree isolation requirements for same-file edits;
   - cleanup and merge discipline;
   - trace coverage for each worker/session.

### Keep

1. Nine-command identity surface.
2. Thin leader and clean worker contexts.
3. Conservative default hook policy.
4. Capture-only promotion rules.
5. Deterministic local gates.
6. P6 trace/eval contract.
7. P7 durable loop decision kernel.
8. Concept absorption instead of wholesale vendoring.

### Remove Or Avoid

1. Do not enable `SessionStart`, `PreCompact`, `PermissionRequest`,
   `PostToolUseFailure`, or `SubagentStop` enforcement by default without live
   payload and budget evidence.
2. Do not re-register pipeline reference roles as live agents.
3. Do not keep generated Codex mirrors unless CI verifies them or regenerates
   them.
4. Do not add always-on MCP servers as plugin defaults.
5. Do not make the installer infer trust from repository presence.
6. Do not let old research docs stay authoritative after score-moving work
   lands. Supersede or archive them through P11.

## Updated 9.5 Program

### P8: Trust-Aware Installer Apply/Remove

Current status: design and plan exist on this branch. Implementation is next.

Acceptance:

- trust schema and fingerprint helpers;
- shared schema v2 reports for dry-run/apply/remove;
- apply only for trusted installable hooks;
- capture-only and disabled hooks blocked;
- atomic settings writes with backups;
- exact-entry remove with unrelated hooks preserved;
- docs, tests, and release story.

Expected score movement:

- Trust/install UX: 7.4 -> 9.5
- Plugin distribution/onboarding: 8.4 -> 8.9

### P9: Cross-Runtime Conformance Generator

Acceptance:

- catalog-derived source of truth for hook/command metadata;
- verifier or generator for Claude and Codex surfaces;
- CI conformance gate;
- no expansion of default runtime hooks.

Expected score movement:

- Cross-runtime portability: 8.2 -> 9.5
- Entropy control: 8.2 -> 8.7

### P10: Live Trace Adoption And Observability Trends

Acceptance:

- real workflows emit P6 trace records;
- hook evidence, loop decisions, and worker artifacts share correlation IDs;
- trend report for scenario score, hook latency, stop reasons, and escalations;
- trace-to-scenario promotion path.

Expected score movement:

- Eval/observability: 8.9 -> 9.6
- Harness engineering: 9.2 -> 9.6
- Workflow engineering: 9.3 -> 9.6

### P11: Entropy Cleanup Loop

Acceptance:

- stale docs/plans scanner;
- capture-only candidate age/freshness report;
- generated mirror drift report;
- ref freshness ledger;
- actionable cleanup task output.

Expected score movement:

- Entropy control: 8.2 -> 9.5
- Plugin distribution/onboarding: 8.9 -> 9.3

### P12: Dynamic Workflow, Agent-Team, And Worktree Adapter

This is new from the current research refresh. P8-P11 are still necessary, but
they do not fully cover Claude Code's newer orchestration surfaces.

Acceptance:

- decision matrix for subagent vs dynamic workflow vs agent team vs manual
  worktree session;
- worktree isolation policy for same-file or high-risk concurrent edits;
- trace schema extensions for worker/session IDs;
- fixture scenarios for fanout, contradiction synthesis, and cleanup;
- docs that state when Athanor should use dynamic workflows and when it should
  stay with the existing command path.

Expected score movement:

- Agent-team/worktree integration: 7.7 -> 9.5
- Loop engineering: 9.1 -> 9.6
- Workflow engineering: 9.6 -> 9.7

## Architecture Review

The current architecture is directionally correct. The highest-risk mistake
would be to add visible surface area instead of finishing the invisible control
layer. P8-P12 should keep these invariants:

1. state before autonomy;
2. trace before trend;
3. trend before promotion;
4. trust before install;
5. conformance before generation;
6. worktree isolation before parallel writes;
7. cleanup before catalog expansion.

## Immediate Next Action

Continue P8 on `feat/p8-trust-installer-apply`. The branch already contains
the architecture and implementation plan. The first implementation slice should
be the trust hash model:

1. add `schemas/hook-installer-trust.schema.json`;
2. add `scripts/gates/hook_installer.py`;
3. add `tests/test_regression_hook_installer_trust.py`;
4. prove command hash, source hash, missing-source, trusted, untrusted, and
   mismatch behavior.

P8 must merge before P9-P12 because installer trust is the prerequisite for
credible higher-autonomy workflow and distribution behavior.
