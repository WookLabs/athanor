# Workflow, Loop, And Harness Research Refresh

Date: 2026-06-18
Local basis: `main` at `83ba888`.
Purpose: compare current Athanor against current workflow engineering, loop
engineering, and harness engineering patterns, then identify the next useful
changes.

## Executive Verdict

Athanor is no longer just a Claude Code plugin with useful commands. It is a
local-first agent harness:

- phase commands map intent to discuss, analyze, debug, plan, work, review,
  lfg, and lfg-goal;
- `lfg` ships a complete plan -> work -> review -> PR -> CI path;
- `lfg-goal` adds a durable validated receipt-ledger loop;
- hooks and gates enforce or check evidence before claims;
- traces, eval episodes, OTel export, trend snapshots, and reactive fixtures
  turn behavior into inspectable artifacts;
- the package knowledge index now gives workers a short current map instead
  of forcing them through all historical docs.

The current weak point is not "add many more agents". The weak point is that
the harness has become strong enough that the next lift is organizational:
turn incoming work into an explicit company-like operating flow with stage
ownership, decision handoffs, durable review records, and governance over what
becomes a rule, a gate, a lesson, or a deleted artifact.

## Sources Reviewed

External sources checked on 2026-06-18:

- Claude Code dynamic workflows:
  https://code.claude.com/docs/en/workflows
- Claude Code `/goal`:
  https://code.claude.com/docs/en/goal
- Claude Code `/loop` and scheduled tasks:
  https://code.claude.com/docs/en/scheduled-tasks
- Claude Code channels:
  https://code.claude.com/docs/en/channels
- Claude Code agent teams:
  https://code.claude.com/docs/en/agent-teams
- OpenAI harness engineering:
  https://openai.com/index/harness-engineering/
- OpenAI agent evals:
  https://developers.openai.com/api/docs/guides/agent-evals
- OpenAI Agents SDK tracing:
  https://openai.github.io/openai-agents-python/tracing/
- Anthropic long-running harnesses:
  https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- Anthropic harness design for long-running apps:
  https://www.anthropic.com/engineering/harness-design-long-running-apps
- Anthropic evals for AI agents:
  https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- LangGraph overview and persistence:
  https://docs.langchain.com/oss/python/langgraph/overview
  https://docs.langchain.com/oss/python/langgraph/persistence
- Inspect AI and sandboxing:
  https://inspect.aisi.org.uk/
  https://inspect.aisi.org.uk/sandboxing.html
- Addy Osmani loop engineering:
  https://addyosmani.com/blog/loop-engineering/

Local sources checked:

- `README.md`
- `CLAUDE.md`
- `skills/lfg/SKILL.md`
- `skills/lfg-goal/SKILL.md`
- `docs/package-knowledge-index.md`
- `docs/package-footprint-policy.md`
- `docs/native-runtime-probe.md`
- `docs/native-runtime-playbook.md`
- `docs/reactive-channel-fixtures.md`
- `docs/harness-decision-ledger.md`

## Local Evidence

Commands run:

```text
python scripts/gates/package_knowledge_index.py --json
python scripts/gates/package_footprint_policy.py --json
python scripts/gates/maintenance_profile.py --skip-claude --ref-warn-days 99999 --samples 1 --json
python scripts/gates/harness_decision_ledger.py --json
python scripts/gates/reactive_channel_fixture.py --fixture-root tests/fixtures/reactive_channels --json
```
Observed results:

- Package knowledge index: pass, 8 checks, 0 warnings.
- Harness decision ledger: pass, 9 decisions observed, 0 errors.
- Reactive channel fixtures: pass, 3 fixtures, 0 auto listeners, 0 auto
  execute actions.
- Maintenance profile: warn, 5 passed steps, 1 warning from the package
  footprint policy.
- Package footprint policy: warn, 499 files, 4,213,946 bytes, 20
  development-only candidates, 0 failures, 0 irreversible actions.
- Native runtime probe inside maintenance profile: pass, but dynamic workflow,
  agent-team, and worktree paths are still dry-run/manual, with 0 executable
  native plans.
- Observability snapshot inside maintenance profile: pass, workflow eval mean
  score 1.0, durable loop pass, hook max budget ratio 0.145.

## External Baseline

### Workflow Engineering

Modern Claude Code now distinguishes several execution surfaces:

- skills for reusable procedural context;
- subagents for bounded delegation inside a session;
- dynamic workflows for script-held fanout and rerunnable orchestration;
- agent teams for independent peer sessions with shared task state;
- worktrees for file isolation;
- `/goal` for condition-bound continuation;
- `/loop` for scheduled recurrence;
- channels for event-driven sessions;
- hooks for deterministic lifecycle enforcement.

The important lesson is routing. A mature harness should not send every task
through the biggest orchestration surface. It should choose the smallest
surface that gives enough isolation, verification, and memory.

Athanor does this well at the command layer. It is conservative at the native
runtime layer: dynamic workflows, worktrees, and agent teams are documented and
probed, but not yet elevated into controlled executable recipes.

### Loop Engineering

Current loop engineering is the shift from manually prompting an agent to
designing the loop that prompts, observes, validates, and resumes the agent.

Athanor already qualifies:

- `/athanor:lfg-goal` is a bounded goal loop with a durable ledger.
- The receipt validator checks artifacts instead of trusting a DONE sentinel.
- Stop verification and evidence gates force proof before completion claims.
- Maintenance profile supplies a safe `/loop` prompt.
- Durable loop fixtures and trend snapshots make regressions measurable.

Remaining issue: the loop is excellent at work execution, but weak at
organizational lifecycle management. It can answer "did the work finish?" much
better than "which office owns this issue, what decision stage is it in, and
what institutional rule did we learn?"

### Harness Engineering

The strongest harness references converge on the same pattern:

- repository-local knowledge is the source of truth;
- short entrypoints point to deeper indexed docs;
- tests, linters, traces, and review artifacts are feedback sensors;
- repeated failures become tools, docs, or gates;
- stale guidance is garbage-collected;
- humans steer at the level of intent and policy, while agents execute.

Athanor is close:

- the package knowledge index is a short worker-facing map;
- many harness rules are schema-backed and CI-backed;
- package footprint now separates repo memory from ship-profile concern;
- harness decisions are recorded in a ledger;
- reactive events are modeled as safe fixtures.

The gap is governance: there is no explicit "organization operating model" that
decides when a repeated issue becomes a lesson, when a lesson becomes a rule,
when a rule becomes a gate, and when old material is removed from the shipped
surface.

### Evals And Observability

OpenAI and Inspect emphasize traces, graders, datasets, eval runs, tool-call
records, and sandboxed execution. Anthropic emphasizes end-state checks and
multi-dimensional graders. LangGraph emphasizes durable state, human-in-the
loop interrupts, and persistence.

Athanor is strong locally:

- workflow trace schema;
- deterministic workflow scenario runner;
- portable eval episodes;
- external eval adapter;
- OTel-style export;
- observability trend snapshots;
- reactive fixtures.

The remaining gap is interoperability depth. Athanor can export and shape data,
but it does not yet run a first-class external sandboxed benchmark profile as a
normal gate.

## Current Scorecard

| Dimension | Score | Read |
| --- | ---: | --- |
| Command phase design | 9.7 | Focused command surface, no feature sprawl. |
| Thin leader discipline | 9.6 | Clear leader/worker split; 4 registered agents only. |
| End-to-end shipping loop | 9.55 | LFG covers plan, work, review, PR, CI. Counters are prose in places. |
| Goal loop engineering | 9.65 | Durable ledger plus receipts and 3-tier check. |
| Evidence and hook harness | 9.75 | Stop, PreToolUse, PostToolUse, freeze, replay, and performance gates. |
| Trace/eval harness | 9.7 | Strong local traces, evals, episodes, trends, and export. |
| Reactive operations | 9.35 | Safe fixture coverage exists; no default listener or live bridge. |
| Native runtime integration | 9.35 | Probe/playbook exist; executable escalation is still manual/dry-run. |
| Package/ship discipline | 9.45 | Gate exists and passes budgets, but still warns on dev-only candidates. |
| Knowledge surface freshness | 9.65 | Package index is short and gated. Needs lifecycle governance. |
| Organizational operating model | 8.45 | Roles exist, but no stage graph, RACI, decision office, or policy promotion loop. |
| External benchmark/sandbox interop | 9.4 | Adapter exists, but no first-class sandboxed benchmark run gate. |

Top-line:

- Workflow plugin: 9.65/10
- Loop-engineering platform: 9.6/10
- Harness-engineering platform: 9.65/10
- Company-like AI organization: 8.45/10

## What Athanor Does Well

1. It keeps the default live surface narrow: 9 user commands, 4 registered
   agents, and current-package knowledge index.
2. It turns many claims into executable gates rather than relying on prose.
3. It has good evidence discipline: Stop verification, evidence sniffer,
   workflow traces, eval episodes, and CI-backed schema checks.
4. It has a better-than-average loop boundary: DONE alone is not enough for
   lfg-goal; receipts and goal checks matter.
5. It is conservative about native surfaces that can be expensive or messy.
6. It has begun treating its own harness changes as decisions that need
   ledger entries.
7. It already has the raw ingredients for an internal operating system:
   planner, critic, executor, reviewer, cleaner, learner, releaser,
   ci-watcher, and decision logs.

## What Is Missing

### 1. Organization Stage Graph

Incoming work should enter a durable stage machine, for example:

```text
intake -> triage -> requirements -> research -> plan -> design review
       -> execution -> verification -> release -> postmortem -> memory update
```

Each stage should name:

- owner role;
- required artifact;
- entry criteria;
- exit criteria;
- escalation condition;
- whether the leader may write infra files;
- which worker or command owns the work.

This would convert Athanor from a command collection into an operating model.

### 2. RACI / Office Model

Current roles exist, but ownership is mostly implicit. Add a small office map:

- Product/Intake office: clarifies requested outcome.
- Research office: gathers external and repo evidence.
- Architecture office: shapes design and boundaries.
- Execution office: implements via work.
- QA/Verification office: runs gates and evidence checks.
- Release office: PR, CI, changelog, version, residuals.
- Learning/Governance office: decides what becomes memory, policy, gate, or
  deletion candidate.

This should not add registered agents by default. Start as a stage policy and
fixture-backed report.

### 3. Policy Promotion Loop

Athanor has lessons and gates, but no canonical promotion path:

```text
incident -> lesson -> repeated lesson -> policy -> gate -> package index
         -> stale check -> deletion/exclusion candidate
```

This is the missing self-improvement loop. Without it, learning accumulates but
does not reliably become organizational policy.

### 4. Stage-Level Receipts

LFG-goal has cycle receipts. The broader organization flow needs stage receipts
that answer:

- what artifact changed;
- who reviewed it;
- which evidence closed the stage;
- what decision was made;
- what should be remembered or pruned.

This can start as a read-only report over existing docs and sessions.

### 5. Native Runtime Escalation Decision

The current posture is right: no default auto-launch. But if we want the plugin
to match Claude Code's current native surfaces, Athanor needs a controlled
"operator approved execution" path for:

- worktree recipes;
- saved dynamic workflow commands;
- agent-team review/research fixtures;
- channel-backed PR/CI event handling.

Do not make these default. Make them opt-in and evidence-logged.

### 6. External Sandbox Benchmark Gate

The external eval adapter is useful, but the next maturity step is a sandbox
profile that can run at least one toy benchmark through Inspect-compatible
shape without mutating real files or requiring network by default.

## Overbuilt Or Risky Areas

1. More registered agents would likely hurt the P16 surface diet.
2. More default hooks would increase startup and failure risk.
3. Default live channel listeners would add security and notification risk.
4. Default dynamic workflows or agent teams would be premature.
5. More historical docs in the ship profile would fight the package index
   direction.
6. LLM judges should remain secondary to deterministic gates where direct
   evidence is available.
7. The current LFG prose counters should not become broader prose-only
   governance. If a loop limit matters, a machine-readable state should carry
   it.

## Add

### P26: Organization Operating Model Gate

Add a read-only organization model document, schema, and gate.

Minimum scope:

- `docs/organization-operating-model.md`;
- `schemas/organization-operating-model-report.schema.json`;
- `scripts/gates/organization_operating_model.py`;
- stage graph with required roles, artifacts, entry/exit criteria, and
  escalation conditions;
- map existing commands and agents into the stage graph;
- report missing coverage and overreach risk;
- CI gate in read-only mode.

Expected score movement:

- Company-like AI organization: 8.45 -> 9.25.
- Workflow plugin: 9.65 -> 9.7.

### P27: Policy Promotion Ledger

Add a canonical lifecycle for lessons becoming policies and policies becoming
gates.

Minimum scope:

- `docs/policy-promotion-ledger.md`;
- schema-backed ledger entries;
- rule states: observed, lesson, candidate_policy, policy, gate_candidate,
  gate, retired;
- backlinks to source incident, tests, docs, and package index updates;
- gate that fails malformed or stale entries.

Expected score movement:

- Knowledge freshness: 9.65 -> 9.75.
- Harness self-evolution: 9.65 -> 9.8.

### P28: Stage Receipt Fixtures

Add fixture-backed stage receipts for non-lfg work.

Minimum scope:

- stage receipt schema;
- examples for research, plan, design review, execution, verification, release,
  and postmortem;
- read-only validator that checks artifact path, owner role, evidence refs,
  and decision outcome;
- no runtime enforcement yet.

Expected score movement:

- Organizational operating model: 9.25 -> 9.45.
- Evidence harness: 9.75 -> 9.8.

### P29: Operator-Approved Native Execution Fixture

Promote native runtime playbook from recipe-only to an approval-gated dry-run
plus one safe executable fixture.

Minimum scope:

- fake/dummy worktree fixture that creates and removes a temporary worktree
  only under a test temp directory;
- saved dynamic workflow command template fixture;
- agent-team task lifecycle fixture;
- no real live agent launch by default.

Expected score movement:

- Native runtime integration: 9.35 -> 9.55.

### P30: Inspect Sandbox Smoke

Add one dependency-light Inspect-compatible sandbox smoke fixture.

Minimum scope:

- export an existing workflow episode to an Inspect task skeleton;
- include sandbox metadata;
- validate shape locally without pulling Docker or hitting network;
- document how to run full Inspect externally.

Expected score movement:

- External benchmark/sandbox interop: 9.4 -> 9.6.

## Remove Or Exclude

1. Keep excluding `ref/`, `.athanor/`, `.git/`, `.pytest_cache/`, and
   `__pycache__` from package accounting.
2. Move toward excluding `tests/`, old `docs/plans/`, old `docs/archive/`,
   and old `docs/architecture/` from the default marketplace ship profile
   if Claude Code packaging supports a narrower ship profile.
3. Retire stale capture-only hook candidates unless they earn promotion.
4. Do not add a new registered "organization manager" agent yet. Model the
   organization first as a stage graph and gate.
5. Do not add live external telemetry or live channels by default.

## Recommended Next Step

Do P26 first: Organization Operating Model Gate.

Reason:

- It directly addresses the user's desired "company-like organization" model.
- It uses current strengths instead of adding risky runtime surfaces.
- It is read-only and therefore safe.
- It gives future work a durable place to attach decisions, receipts, and
  policy promotion.
- It should precede P27/P28 because promotion ledgers and stage receipts need a
  stable stage vocabulary.

Draft P26 outcome:

```text
incoming issue
  -> classify task shape and risk
  -> assign stage owners
  -> require artifacts per stage
  -> run existing Athanor commands as stage executors
  -> produce stage/goal receipts
  -> promote repeated learning to policy/gate candidates
  -> prune stale or non-load-bearing harness material
```
