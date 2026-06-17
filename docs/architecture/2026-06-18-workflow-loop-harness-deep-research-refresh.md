# Workflow, Loop, And Harness Deep Research Refresh

Date: 2026-06-18
Local basis: `feat/p20-maintenance-profile` working tree.
Runtime evidence: Claude Code `2.1.179`, distribution smoke, maintenance
profile, harness decision ledger.

## Executive Verdict

Athanor is already doing real workflow engineering, loop engineering, and
harness engineering. The plugin is strongest as a local-first deterministic
harness: small runtime-visible agent surface, narrow default hooks, many
schema-backed gates, durable loop fixtures, workflow traces, eval episodes,
memory-quality checks, native runtime probes, and a read-only maintenance
profile.

The current frontier has shifted. The weak points are no longer "more agents"
or "more commands". They are:

1. ship-footprint control;
2. external eval/sandbox interoperability;
3. controlled native execution escalation beyond dry-run recommendations;
4. push-based reactive operations, such as CI or review events entering a
   running session;
5. keeping long-lived project knowledge short, indexed, and mechanically fresh.

Current top-line scores, including P20 working-tree evidence:

- Claude Code workflow plugin: 9.6/10
- Local deterministic harness: 9.7/10
- Loop-engineering platform: 9.55/10
- Harness-engineering platform: 9.6/10
- Distribution/ship discipline: 9.25/10
- External benchmark/sandbox readiness: 9.3/10
- Native execution escalation: 9.35/10

The practical answer: Athanor is optimized enough to be a high-quality local
harness, but not yet optimized enough to claim best-in-class distribution and
cross-harness interoperability.

## Sources Reviewed

Primary sources checked on 2026-06-17/18:

- Claude Code dynamic workflows:
  https://code.claude.com/docs/en/workflows
- Claude Code `/goal`:
  https://code.claude.com/docs/en/goal
- Claude Code `/loop` and scheduled tasks:
  https://code.claude.com/docs/en/scheduled-tasks
- Claude Code agent teams:
  https://code.claude.com/docs/en/agent-teams
- Claude Code worktrees:
  https://code.claude.com/docs/en/worktrees
- Claude Code hooks:
  https://code.claude.com/docs/en/hooks
- Claude Code skills:
  https://code.claude.com/docs/en/skills
- Claude Code headless/Agent SDK usage:
  https://code.claude.com/docs/en/headless
- Claude Code channels:
  https://code.claude.com/docs/en/channels
- Claude Code plugin marketplaces:
  https://code.claude.com/docs/en/plugin-marketplaces
- OpenAI harness engineering:
  https://openai.com/index/harness-engineering/
- OpenAI Agents SDK tracing:
  https://openai.github.io/openai-agents-python/tracing/
- OpenAI Agents guide:
  https://developers.openai.com/api/docs/guides/agents
- Martin Fowler / Thoughtworks harness engineering:
  https://martinfowler.com/articles/harness-engineering.html
- LangChain State of Agent Engineering:
  https://www.langchain.com/state-of-agent-engineering
- LangGraph overview:
  https://docs.langchain.com/oss/python/langgraph/overview
- Inspect AI:
  https://inspect.aisi.org.uk/
- HumanLayer 12-factor agents:
  https://github.com/humanlayer/12-factor-agents
- Addy Osmani, loop engineering:
  https://addyosmani.com/blog/loop-engineering/
- MindStudio, loop engineering:
  https://www.mindstudio.ai/blog/what-is-loop-engineering-ai-coding-agents
- Local refs under `ref/`, including official Claude repos, Inspect AI,
  awesome harness engineering, loop-engineering, hooks, plugins, skills, and
  worktree references.

## Current Evidence

Commands run during this refresh:

```text
python scripts/gates/maintenance_profile.py --skip-claude --ref-warn-days 99999 --samples 1 --json
python scripts/gates/distribution_smoke.py --json
python scripts/gates/harness_decision_ledger.py --json
```

Observed state:

- Maintenance profile: pass, 5/5 steps passed, 0 warnings, 0 failures,
  `irreversible_actions: 0`.
- Harness decision ledger: pass, 4 decisions recorded.
- Distribution smoke: pass, 12 checks, live Claude loader reports 4 agents.
- Always-on token estimate: 2,133 / 2,200 budget.
- Package footprint: 458 files, 3,986,822 bytes.
- Largest shipped files include `CHANGELOG.md`, archived state, historical
  plans, and regression tests.
- Native runtime probe: pass, but dynamic workflow, agent-team, and worktree
  plans are dry-run/manual rather than executable by default.

## External Baseline

### Workflow Engineering

Modern Claude Code now separates several surfaces:

- skills for progressive procedural context;
- subagents for bounded delegation inside one session;
- dynamic workflows for script-held fanout and rerunnable orchestration;
- agent teams for multiple Claude Code sessions with shared task state;
- worktrees for file isolation;
- `/goal` for completion-condition loops;
- `/loop` and scheduled tasks for interval-based recurrence;
- hooks and channels for lifecycle and event integration;
- plugin marketplaces for distribution and update channels.

The key pattern is surface selection. A mature plugin should not turn every
task into multi-agent orchestration. It should route by task shape, cost,
isolation needs, and verification requirements.

Athanor is strong at routing policy and deterministic checks. It is weaker at
actually invoking newer native surfaces because P19 intentionally stayed at
dry-run plans.

### Loop Engineering

The current loop-engineering definition is an action-observe-adapt cycle with
explicit exit conditions, failure exits, memory, and verification. `/goal`
handles turn-to-turn completion checks. `/loop` handles recurring prompts and
maintenance/polling. The broader ecosystem frames loop engineering as systems
that prompt and verify agents instead of humans manually prompting each turn.

Athanor clearly qualifies:

- `lfg-goal` is a goal-driven validated loop.
- Durable loop state/evidence schemas and fixtures prevent vague completion.
- Stop verification and evidence gates force claims back to proof.
- P20 packages a read-only recurring maintenance loop profile.
- P17 and P18 connect memory and harness changes to evidence.

Remaining issue: P20 provides a `/loop` prompt but does not register or manage
the scheduled task. That is the correct safety posture, but it keeps recurring
operations operator-driven.

### Harness Engineering

The best current harness framing is "model plus environment". The environment
includes repo-local knowledge, plans, tests, CI, traces, policies, permissions,
hooks, evals, memory, and cleanup. OpenAI emphasizes repo-local structured
knowledge and executable plans. Fowler emphasizes feedforward guides,
feedback sensors, maintainability harnesses, architecture fitness, behavior
checks, and human review where judgment matters.

Athanor is unusually close to that baseline:

- repo-local docs, schemas, plans, and decisions;
- deterministic CI gates;
- hook safety and replay fixtures;
- trace/eval/episode artifacts;
- runtime conformance and native probes;
- maintenance and entropy checks;
- harness decision ledger.

Weakness: too much historical knowledge still ships with the plugin. Good
harness knowledge should be discoverable from the repo, but not all historical
planning artifacts need to be part of the distributed runtime package.

### Observability And Evals

The external pattern is trace-first and eval-backed. OpenAI Agents SDK tracing,
LangChain/LangSmith, Arize Phoenix, and Inspect AI all point in the same
direction: final answers are not enough; agent behavior needs traces, spans,
tool-call records, guardrail events, scored episodes, and repeatable eval
datasets.

Athanor is strong locally:

- workflow trace schema;
- deterministic scenario runner;
- OTel-style export;
- portable eval episodes;
- trend snapshots;
- memory-quality gate.

Weakness: there is no first-class Inspect AI adapter or sandbox profile. The
episode format is portable, but external benchmark execution is still a manual
translation.

### Event-Driven Operations

Claude Code channels can push external events such as CI failures or webhooks
into a running local session. Athanor currently relies on polling-style
maintenance, CI gates, and explicit commands. That is simpler and safer, but it
misses a modern workflow surface: reactive "event arrives, session responds"
ops.

This should stay opt-in. A channel bridge has real security and notification
risk, but a fake/local channel fixture or documented plugin compatibility test
would raise readiness.

## Comparative Scorecard

| Dimension | Score | Read |
| --- | ---: | --- |
| Command/workflow phase design | 9.6 | Focused phase commands and clear plan/work/review/verify separation. |
| Thin leader and context isolation | 9.6 | Runtime-visible agents are restrained at 4; reference roles are not registered. |
| Hook safety and evidence | 9.75 | Replay, redaction, kernel guard, freeze, evidence sniffer, and performance budgets are strong. |
| Deterministic harness gates | 9.75 | Policies are mostly executable and CI-backed. |
| Trace/eval harness | 9.7 | Traces, scenarios, OTel export, packages, and trends exist. |
| Memory quality | 9.55 | P17 closes the original evidence gap, but live long-horizon impact still needs more real-run history. |
| Harness self-evolution | 9.55 | P18 ledger makes harness changes accountable. |
| Recurring maintenance loop | 9.55 | P20 read-only profile is the right baseline; no auto-scheduler by design. |
| Distribution truth | 9.55 | Live Claude loader smoke passes and token budget is observed. |
| Package footprint | 8.7 | 458 files / 3.99 MB, with historical docs and tests in the ship surface. |
| Native runtime bridge | 9.35 | Availability and dry-run plans are checked; actual worktree/workflow/team execution is still manual. |
| Dynamic workflow readiness | 9.35 | Good policy, no saved Athanor-native workflow commands yet. |
| Agent-team readiness | 9.3 | Treated correctly as experimental; no fixture for teammate task lifecycle. |
| Worktree isolation | 9.35 | Detected and recommended, but no controlled create/cleanup recipe owned by Athanor. |
| External eval/sandbox interop | 9.3 | Portable episodes exist; no Inspect/Docker sandbox adapter. |
| Push/reactive ops | 8.9 | Channels are not integrated; CI/review events are polled or handled manually. |
| Knowledge-map freshness | 9.25 | Docs are rich and gated, but CLAUDE/runtime knowledge can still grow into token pressure. |

## What Athanor Does Better Than Many References

1. It turns workflow advice into gates, schemas, fixtures, and CI.
2. It keeps default agent count and hook count restrained.
3. It separates maker, reviewer, verifier, releaser, and learner roles without
   registering every reference role as a live agent.
4. It has a strong local privacy posture: JSON artifacts and opt-in export
   rather than default external telemetry.
5. It uses evidence before claims: hook replay, Stop verification, freeze
   evidence, post-tool sniffing, and release-story tests.
6. It has a self-improvement ledger, which many plugin collections do not.
7. It keeps native Claude experimental surfaces conservative instead of
   auto-launching costly or hard-to-clean orchestration.

## What Is Missing

1. **Ship profile / package footprint gate.**
   Distribution smoke proves the package is valid, but not that it is lean.
   Historical plans, archived state, and tests are useful for development but
   should not all be in the default marketplace ship surface forever.

2. **Inspect AI / sandbox adapter.**
   Athanor's eval episodes are portable locally, but they do not map directly
   to Inspect datasets, solvers, scorers, or sandbox configs.

3. **Native execution escalation.**
   P19 intentionally stops at dry-run. To reach best-in-class, Athanor needs
   explicit operator-approved recipes for worktree creation/cleanup, saved
   dynamic workflow commands, and maybe an agent-team research/review fixture.

4. **Reactive channel integration.**
   The current profile polls. Modern Claude Code can receive pushed channel
   events. Athanor should at least test or document a safe local/fake channel
   bridge for CI failure events.

5. **Knowledge surface pruning.**
   OpenAI's harness article favors short entrypoints plus indexed repo-local
   knowledge. Athanor has the repo-local knowledge, but the package surface is
   too close to "everything ships".

6. **A real-run quality history.**
   P17/P18/P20 are structurally correct. They need time-series proof from
   multiple real maintenance cycles to show sustained improvement.

## Overbuilt Or Risky Areas

1. More default hooks would likely hurt reliability and startup cost.
2. More registered agents would reverse the P16 diet.
3. Default dynamic workflow or agent-team launch would be premature.
4. External telemetry should remain opt-in.
5. LLM-judge release gates should stay secondary to deterministic checks.
6. Historical docs should stay in the repo, but not necessarily in the shipped
   plugin package.
7. Capture-only hook candidates should expire unless promoted by evidence.

## Add

### P21: Ship Footprint Policy Gate

Add a gate that distinguishes development assets from runtime/distribution
assets. It should report package bytes, largest files, dev-only candidates,
marketplace-included paths, and budget drift.

Minimum scope:

- `scripts/gates/package_footprint_policy.py`;
- schema-backed report;
- budgets for file count, total bytes, always-on tokens, and top-file classes;
- allowlist/denylist for docs, tests, ref, archive, and plans;
- no deletion by default;
- CI gate in warn mode first;
- docs explaining what stays repo-local but out of the ship profile.

Expected movement:

- Package footprint: 8.7 -> 9.55.
- Distribution/ship discipline: 9.25 -> 9.6.

### P22: Inspect/Sandbox Eval Adapter

Add a local adapter that can export Athanor workflow eval episodes into an
Inspect-compatible layout and a sandbox manifest. Keep it optional and
dependency-light.

Minimum scope:

- export command for existing `.athanor/episodes/workflow-evals`;
- Inspect task skeleton or manifest;
- sandbox profile metadata;
- no network and no Docker launch by default;
- committed fixture proving round-trip shape.

Expected movement:

- External benchmark/sandbox interop: 9.3 -> 9.6.

### P23: Native Execution Playbook

Promote P19 from "dry-run only" to "operator-approved recipes" without
auto-launching by default.

Minimum scope:

- worktree create/cleanup recipe with dirty-state refusal;
- saved dynamic workflow command template for research/review fanout;
- agent-team readiness fixture for task assignment and shutdown constraints;
- explicit cost/cleanup/permission warnings;
- no default auto-launch.

Expected movement:

- Native runtime bridge: 9.35 -> 9.6.
- Worktree isolation: 9.35 -> 9.6.
- Dynamic workflow / agent-team readiness: 9.3-9.35 -> 9.55.

### P24: Reactive Channel Spike

Add a safe, local-only compatibility spike for pushed events.

Minimum scope:

- document fake/local channel flow;
- fixture a CI-failure event payload;
- map payload to maintenance-profile or CI-watch actions;
- require explicit user enablement and sender allowlist;
- no default channel install.

Expected movement:

- Push/reactive ops: 8.9 -> 9.45 or 9.55 depending on fixture depth.

## Remove Or Exclude

1. Exclude old plans, archive-heavy docs, and regression tests from the default
   shipped plugin package if Claude Code marketplace packaging allows a
   narrower source profile.
2. Remove stale score language that predates P17-P20.
3. Remove or quarantine capture-only hooks that do not earn promotion.
4. Do not add broad "all purpose" skills; keep one skill to one job.
5. Do not ship default external telemetry, dynamic workflow launch, agent-team
   launch, or channel listeners without explicit operator intent.

## Recommended Next Step

Finish and merge P20 first because the working tree already contains it and the
gate is passing.

Then do P21: ship footprint policy gate. It is now the most concrete
sub-9.5 gap, and it is safe: it can start as read-only reporting before any
package exclusion or file movement.
