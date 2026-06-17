# Post-P16 Workflow, Loop, Harness, And Memory Deep Research

Date: 2026-06-17
Local basis: `feat/p17-trace-to-memory`, after P16 distribution smoke landed on
`main`.
Runtime checked: Claude Code `2.1.179` on Windows.
Purpose: refresh the external workflow/loop/harness baseline after P16, compare
Athanor's actual runtime-visible plugin surface, and pick the next
quality-lifting work.

## Executive Verdict

Athanor is now a strong Claude Code workflow plugin and a strong local
deterministic harness. P16 fixed the previous distribution-truth gap: the live
Claude plugin loader now reports 4 registered agents and an always-on cost under
the local budget. That moves Athanor's plugin/distribution score above the 9.5
threshold.

The remaining gap is no longer "more commands", "more agents", or "more hooks".
The current frontier is a closed quality loop:

1. real runs emit traces;
2. traces are scored or reviewed;
3. scored evidence promotes, decays, or quarantines memory;
4. harness changes record expected metric movement;
5. later runs prove whether the harness change helped;
6. native Claude surfaces such as `/goal`, `/loop`, dynamic workflows, agent
   teams, and worktrees are used only when the task shape justifies the cost.

Bottom line: Athanor is already doing workflow engineering, loop engineering,
and harness engineering. It is not fully optimized yet because memory quality
and harness self-evolution are still mostly documented intent rather than
machine-checked feedback loops.

Current top-line scores:

- Claude Code workflow plugin: 9.55/10
- Local deterministic harness: 9.65/10
- Modern loop/harness platform: 9.35/10

The third score is pulled down by P17/P18-class gaps: trace-to-memory quality
and harness decision accounting.

## Fresh Sources Reviewed

Primary/high-signal sources checked on 2026-06-17:

- Claude Code dynamic workflows:
  https://code.claude.com/docs/en/workflows
- Claude Code agent teams:
  https://code.claude.com/docs/en/agent-teams
- Claude Code worktrees:
  https://code.claude.com/docs/en/worktrees
- Claude Code `/goal`:
  https://code.claude.com/docs/en/goal
- Claude Code scheduled tasks and `/loop`:
  https://code.claude.com/docs/en/scheduled-tasks
- Claude Code hooks reference and guide:
  https://code.claude.com/docs/en/hooks
  https://code.claude.com/docs/en/hooks-guide
- Claude Code memory:
  https://code.claude.com/docs/en/memory
- Claude Code skills:
  https://code.claude.com/docs/en/skills
- Claude Code plugin marketplaces:
  https://code.claude.com/docs/en/plugin-marketplaces
- OpenAI, "Harness engineering: leveraging Codex in an agent-first world":
  https://openai.com/index/harness-engineering/
- OpenAI Agents SDK guide and tracing:
  https://developers.openai.com/api/docs/guides/agents
  https://openai.github.io/openai-agents-python/tracing/
- Martin Fowler / Thoughtworks harness engineering:
  https://martinfowler.com/articles/harness-engineering.html
- LangGraph overview:
  https://docs.langchain.com/oss/python/langgraph/overview
- LangChain, "Agent observability powers agent evaluation":
  https://www.langchain.com/blog/agent-observability-powers-agent-evaluation
- LangChain, "Improving Deep Agents with harness engineering":
  https://www.langchain.com/blog/improving-deep-agents-with-harness-engineering
- Arize, "How to build a better agent harness with traces and evals":
  https://arize.com/blog/improve-ai-agents-traces-evals-harness/
- Inspect AI:
  https://inspect.aisi.org.uk/
- HumanLayer 12-factor agents:
  https://github.com/humanlayer/12-factor-agents

Local commands run:

```text
claude --plugin-dir . plugin details athanor
python scripts/gates/distribution_smoke.py --json
```

Observed local state:

- Claude CLI: `2.1.179 (Claude Code)`
- Skills: 12
- Agents: 4 (`ci-watcher`, `codex-dispatcher`, `learner`, `releaser`)
- Hooks: 3 (`Stop`, `PreToolUse`, `PostToolUse`)
- Always-on token estimate: 2,133
- Distribution smoke status: pass
- Package footprint: 421 files, 3,793,310 bytes

## External Baseline After P16

### Workflow Engineering

Claude Code now separates several execution surfaces:

- skills: on-demand procedural context;
- subagents: a few delegated workers inside a session;
- agent teams: peer Claude Code sessions with shared tasks and direct
  communication;
- dynamic workflows: script-held fanout across many subagents;
- worktrees: file-system isolation for parallel sessions;
- `/goal`: a session-scoped completion-condition loop;
- `/loop` and scheduled tasks: interval-driven maintenance or polling;
- hooks: deterministic lifecycle controls;
- plugins: distribution and packaging.

The important distinction is who owns the plan. Skills and subagents keep the
plan mostly in Claude's context. Dynamic workflows move the plan into code.
Agent teams move coordination into peer sessions. Worktrees isolate edits. A
modern workflow plugin should therefore decide which surface fits a task rather
than treating all parallelism as the same thing.

Athanor's current status: strong command topology and runtime recommendation
contracts, but native launching of dynamic workflows, agent teams, and
worktrees remains intentionally conservative/future-facing.

### Loop Engineering

The current loop baseline is an action-feedback-decision cycle with explicit
exit conditions. Claude `/goal` checks a completion condition after each turn
with a separate fast model. `/loop` schedules recurring prompts and includes a
built-in maintenance prompt for unfinished work, PR care, and cleanup.

Athanor's `lfg-goal`, durable loop state/evidence schemas, loop fixtures, Stop
verification, and workflow eval scenarios are already aligned with this model.
The missing piece is not another loop prompt. The missing piece is that loop
outcomes do not yet automatically affect memory quality or harness-change
decisions.

### Harness Engineering

OpenAI's harness framing and Fowler's feedforward/feedback framing converge:
the repository is the operating environment for agents. The harness includes
instructions, repo maps, tests, CI, permission boundaries, hooks, traces, evals,
review gates, docs, and cleanup. Engineers increasingly design the environment
and feedback loops while agents execute.

Athanor is strong here because many policies are executable:

- hook replay and evidence gates;
- hook performance budgets;
- trust-aware hook install/remove;
- cross-runtime conformance;
- runtime adapter fixtures;
- workflow traces, scenario evals, OTel-style export, and eval episodes;
- entropy cleanup;
- distribution smoke with live Claude loader inventory and cost checks.

The next maturity level is trace-backed self-evolution: memory and harness
changes should have evidence, expected movement, observed movement, and a
rollback/follow-up decision.

### Eval And Observability

The external pattern is trace-first. OpenAI Agents SDK traces full workflow
runs with spans for agents, generations, tools, handoffs, guardrails, and custom
events. LangChain and Arize both make the same point: agent behavior cannot be
understood from final output alone; traces are the source of truth, and
production or real-run traces should become offline eval cases. Inspect AI
adds a broader standard for datasets, agents, tools, scorers, and sandboxes.

Athanor has a strong local version:

- workflow trace schema;
- deterministic scenario runner;
- live command trace anchors;
- OTel-style local export;
- portable local eval episode packaging;
- trend snapshots.

The weakest link is memory. Lessons exist, but there is no gate that proves a
lesson was promoted because trace/eval evidence says it improves behavior, or
quarantined because it degraded behavior.

### Memory Engineering

Claude Code now has explicit memory surfaces: `CLAUDE.md`/rules for
instructions, auto memory for learned patterns, and plain markdown files that
can be audited. The memory docs emphasize that memory can be edited/deleted and
that oversized instruction files reduce adherence.

Athanor has a local `.athanor/lessons/` concept with decay and promotion config:

```json
"memory": {
  "decayDays": 7,
  "promotionThreshold": 5,
  "maxAgeDays": 30
}
```

That is the right shape, but incomplete. A trace-to-memory loop should require
evidence before promotion and should pressure-test stale or harmful lessons.
Otherwise memory becomes a silent regression channel.

## Current Athanor Scorecard

Scores reflect current post-P16 state, not older pre-P16 reports.

| Dimension | Score | Read |
| --- | ---: | --- |
| Command/workflow phase design | 9.6 | Focused phase commands; no giant utility pile. |
| Thin leader/context isolation | 9.6 | Four runtime-visible agents, reference roles moved out of plugin `agents/`. |
| Hook safety and evidence | 9.7 | Replay, redaction, safety corpus, freeze, and evidence mode are strong. |
| Hook performance discipline | 9.6 | Performance budgets and trend snapshots exist. |
| Trust/install engineering | 9.55 | Apply/remove and no-clobber behavior are reviewable. |
| Cross-runtime conformance | 9.5 | Claude/Codex metadata drift has a gate. |
| Local trace/eval harness | 9.65 | Trace schema, scenarios, OTel export, and eval episodes are strong. |
| Distribution truth | 9.55 | P16 live loader smoke checks agents and always-on tokens. |
| Durable loop engineering | 9.5 | State/evidence/decision fixtures are coherent. |
| Runtime backend recommendation | 9.2 | Adapter exists; native execution remains advisory. |
| Worktree isolation | 8.8 | Recognized and classified; not first-class live execution. |
| Dynamic workflow / agent-team readiness | 8.9 | Good policy; no native launch/probe path yet. |
| Live observability | 9.25 | Anchors and export exist; not all real command flows emit exhaustive spans. |
| Recurring maintenance loop | 8.7 | Entropy gate exists; no scheduled `/loop`/CI maintenance package yet. |
| Trace-to-memory quality | 8.2 | Biggest near-term gap; lessons are not eval-driven. |
| Harness self-evolution ledger | 7.7 | Harness changes lack expected-vs-observed metric accounting. |
| External benchmark/sandbox interop | 9.3 | Episode shape exists; no Inspect/Docker-heavy runner integration by default. |
| Package size/ship footprint | 8.8 | 421 files and 3.8 MB is acceptable but growing. |

## What Athanor Does Well

1. It has a small, meaningful workflow command surface.
2. It keeps default runtime cost restrained after P16.
3. It is unusually executable: policies become schemas, gates, fixtures, and
   CI checks.
4. It uses maker/checker separation: plan, work, review, Stop verification,
   LFG receipts, and eval runners reinforce each other.
5. It keeps external telemetry opt-in and local-first.
6. It treats hook installation and distribution as trust surfaces.
7. It has enough trace/eval infrastructure to support real feedback loops.

## What Is Still Missing

1. **Trace-to-memory quality loop.** Promotion/decay/quarantine needs evidence
   refs, stale-memory checks, and with/without lesson outcome comparison.
2. **Harness decision ledger.** Every harness change should record expected
   metric direction, verification command, observed result, and rollback or
   follow-up decision.
3. **Native runtime execution bridge.** The P12 adapter recommends solo,
   subagent, dynamic workflow, agent team, or worktree modes, but Athanor does
   not yet launch/probe those native surfaces.
4. **Scheduled maintenance packaging.** Entropy cleanup is executable but not
   packaged as a recurring `/loop`, scheduled task, or CI maintenance mode.
5. **Memory pressure tests.** There is no committed fixture showing stale or
   harmful memory causing degradation and being quarantined.
6. **External eval export target.** Eval episodes are portable locally but not
   mapped to Inspect or another benchmark harness.
7. **Package footprint control.** Large historical docs and changelog entries
   are useful for development but may eventually need a ship-profile exclusion
   policy.

## Overbuilt Or Risky Areas

1. More default hooks would be counterproductive. Keep enabled hooks narrow.
2. More registered agents would weaken the P16 correction.
3. Default dynamic workflow or agent-team execution would add cost and
   coordination risk. Keep it task-shape driven.
4. LLM-judge release gates should stay secondary. Deterministic gates remain
   the right default.
5. External telemetry should not become default. Local JSONL and opt-in exports
   are the right privacy posture.
6. Large historical docs should not remain in the distribution forever without
   a footprint policy.

## Add Next

### P17: Trace-To-Memory Quality Gate

Goal: make memory promotion, decay, and quarantine evidence-backed.

Minimum viable scope:

- parse lesson frontmatter from `.athanor/lessons/` or fixture roots;
- fail promotion candidates that lack trace/eval evidence;
- report stale working lessons using `memory.decayDays`;
- quarantine explicitly degraded or harmful lessons;
- accept optional with/without lesson comparison fixtures;
- emit a JSON report validated by schema;
- add CI coverage against committed fixtures.

Why first: it closes the largest remaining quality gap and directly matches the
trace/eval/memory direction in current agent-engineering practice.

### P18: Harness Decision Ledger

Goal: prevent harness changes from becoming unmeasured prompt churn.

Minimum viable scope:

- require each harness change to record expected metric movement;
- record verification commands and observed results;
- tie decisions to follow-up or rollback;
- emit a ledger report and CI gate for recent harness changes.

Why second: it turns Athanor into a self-improving harness instead of a growing
collection of good local tools.

### P19: Native Runtime Bridge Spike

Goal: prove whether Athanor can safely launch or probe native Claude runtime
surfaces.

Minimum viable scope:

- readonly probe for `/goal`, `/loop`, worktree, dynamic workflow, and agent-team
  availability;
- dry-run launch plans only;
- no default auto-launch;
- record permission, cost, and cleanup constraints.

Why third: P12 already recommends modes. P19 should establish whether those
recommendations can become executable safely.

### P20: Scheduled Maintenance Profile

Goal: package entropy cleanup as recurring maintenance.

Minimum viable scope:

- a documented `/loop` prompt or CI job profile;
- no irreversible actions by default;
- runs entropy cleanup, distribution smoke, trend report, and stale-ref checks;
- emits a concise operator report.

## Remove Or De-Emphasize

1. Stale scorecards that predate P16's loader-surface correction.
2. Any claim that lesson memory is self-improving until P17 lands.
3. Capture-only hook candidates that age without evidence.
4. Shipping large historical planning files forever without a package-footprint
   policy.
5. Any default path that starts agent teams, dynamic workflows, or external
   telemetry without explicit user intent.

## Recommended Next Step

Proceed with P17 now.

P17 is the best next move because it connects the strongest existing assets
into a real improvement loop: traces, evals, durable loop outcomes, and local
lessons. After P17, P18 should add harness decision accounting so future
changes can prove whether they helped.

