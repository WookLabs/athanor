# Current Workflow, Loop, And Harness Research Comparison

Date: 2026-06-18
Local branch: `feat/p21-package-footprint-policy`
Local baseline commit: `2aa88e6`

## Executive Verdict

Athanor is already a strong local-first Claude Code harness. Its strongest
properties are deterministic gates, evidence-bound hooks, bounded runtime
surface, portable local workflow traces, and a read-only maintenance profile.

The external frontier in June 2026 is not "more prompts" or "more agents". It
is the disciplined environment around the model: sandboxed execution,
trace-backed improvement loops, evals that can be rerun, short entrypoint
knowledge with indexed deeper docs, native context isolation, and package
surfaces that stay lean enough to ship.

Against that frontier, Athanor's remaining gaps are now concentrated in two
places:

1. operator-approved native runtime escalation;
2. reactive event/channel compatibility.

P21, the package footprint policy gate, has now closed the lowest-risk
sub-9.5 gap. The gate keeps packaging read-only, reports ship-profile budgets,
classifies development-only candidates, and makes exclusion work explicit
without silently deleting files.

P22, the external eval/sandbox adapter, has now closed the external interop
gap enough for the current 9.5 target. It exports packaged workflow episodes
into inspect-like and harbor-like task, scorer, and sandbox metadata without
installing external harnesses or enabling networked execution by default.

## External Sources Checked

- OpenAI, "Harness engineering: leveraging Codex in an agent-first world",
  2026-02-11:
  https://openai.com/index/harness-engineering/
- OpenAI, "Unrolling the Codex agent loop", 2026:
  https://openai.com/index/unrolling-the-codex-agent-loop/
- OpenAI Cookbook, "Build an Agent Improvement Loop with Traces, Evals, and
  Codex", 2026:
  https://developers.openai.com/cookbook/examples/agents_sdk/agent_improvement_loop
- OpenAI, "The next evolution of the Agents SDK", 2026-04-15:
  https://openai.com/index/the-next-evolution-of-the-agents-sdk/
- Anthropic, "Demystifying evals for AI agents", 2026-01-09:
  https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- Anthropic, "Measuring AI agent autonomy in practice", 2026-02-18:
  https://www.anthropic.com/research/measuring-agent-autonomy
- Anthropic, "Agentic coding and persistent returns to expertise",
  2026-06-16:
  https://www.anthropic.com/research/claude-code-expertise
- Claude Code docs, hooks:
  https://code.claude.com/docs/en/hooks-guide
- Claude Code docs, plugins reference:
  https://code.claude.com/docs/en/plugins-reference
- Claude Code docs, subagents:
  https://code.claude.com/docs/en/sub-agents
- Claude Code docs, extension overview:
  https://code.claude.com/docs/en/features-overview
- LangChain, "Improving Deep Agents with harness engineering", 2026-02-17:
  https://www.langchain.com/blog/improving-deep-agents-with-harness-engineering
- LangGraph overview:
  https://docs.langchain.com/oss/python/langgraph/overview
- Terminal-Bench, "Introducing Terminal-Bench 2.0 and Harbor", 2025-11-07:
  https://www.tbench.ai/news/announcement-2-0
- Harbor docs, "Running Terminal-Bench":
  https://www.harborframework.com/docs/tutorials/running-terminal-bench
- Microsoft AutoGen research page:
  https://www.microsoft.com/en-us/research/project/autogen/

## Research Synthesis

### 1. Workflow Engineering

The modern workflow layer is a surface-selection problem. Claude Code now
separates persistent context, skills, MCP, subagents, agent teams, hooks,
channels, goals, scheduled tasks, and plugins. The best pattern is not to use
every surface by default, but to route work according to cost, isolation,
repeatability, and risk.

Athanor does this well. It keeps the user-facing command set focused, keeps
only four loader-visible agents, and moves heavier process into skills,
reference docs, and deterministic scripts. This is stronger than most plugin
collections that accumulate commands without a routing policy.

Remaining gap: native dynamic-workflow, agent-team, and worktree surfaces are
detected and documented, but still dry-run/manual by design. That is safe, but
it means Athanor is not yet a first-class native runtime orchestrator.

### 2. Loop Engineering

The current loop model is action, observation, feedback, and adaptation with
clear exit conditions. OpenAI's agent-improvement-loop framing is especially
relevant: traces preserve what happened, feedback explains what mattered, evals
make the expectation reusable, and Codex can implement the next harness
change.

Athanor qualifies as loop engineering:

- `lfg-goal` has durable state, evidence, and no-progress exits.
- workflow evals produce deterministic trace scores;
- P17 trace-memory quality turns lessons into checked artifacts;
- P18 harness decision ledger makes self-improvement accountable;
- P20 maintenance profile provides a read-only recurring loop profile.

Remaining gap: the profile is not a registered scheduler and should not become
one without explicit operator control. The gap is acceptable, but it caps the
reactive/recurring operations score.

### 3. Harness Engineering

OpenAI's Codex harness writeup emphasizes that engineering moves from direct
coding into environment design, repository knowledge, architecture constraints,
feedback loops, worktree-local execution, UI/app legibility, observability, and
garbage collection. LangChain's Terminal-Bench result shows the same theme:
performance changed materially through self-verification, tracing, and harness
changes rather than model changes.

Athanor is aligned here:

- hooks are evidence-bound and replayed;
- Stop, PreToolUse, and PostToolUse paths have fixtures and health checks;
- runtime conformance, distribution smoke, and maintenance profile are CI
  gates;
- traces, OTel-style export, episodes, and trend snapshots exist;
- entropy cleanup and decision-ledger gates are already in place.

P21 result: package footprint is now budgeted and classified. The current
package passes hard file and byte budgets and warns on development-only
candidates that should be excluded from the ship profile over time.

### 4. Evals And Sandboxes

Anthropic's eval guidance and Harbor/Terminal-Bench converge on repeatable
agent trials, verified tasks, graders, containerized execution, and frameworks
that can run at scale. OpenAI's 2026 Agents SDK direction adds native sandbox
execution and portable manifests for files and outputs.

Athanor is strong locally but incomplete externally:

- local deterministic workflow scenarios pass;
- portable episode packaging exists;
- OTel-style export exists;
- an Inspect/Harbor-like adapter now exports task, scorer, and sandbox
  metadata;
- no Docker/sandbox runtime is installed by default;
- no external benchmark runner is auto-launched in CI.

This should remain optional. External sandbox dependencies should not become a
default install or CI burden.

### 5. Human Steering And Expertise

Anthropic's June 2026 Claude Code expertise report reinforces the division of
labor: humans decide what to build and agents decide how to execute. The more
domain expertise the user brings, the more useful work the agent can do per
instruction.

Athanor is built around that same premise. Its best feature is not autonomous
launching; it is forcing the human to preserve intent and evidence through
plans, reviews, receipts, and verifiable gates.

The risk is over-automation: enabling default agent teams, channel listeners,
or auto worktrees would reduce human steering unless guarded by approval and
cleanup policies.

## Local Evidence Snapshot

Commands run on 2026-06-18:

```text
python scripts/gates/maintenance_profile.py --skip-claude --ref-warn-days 99999 --samples 1 --json
python scripts/gates/distribution_smoke.py --skip-claude --json
python scripts/gates/package_footprint_policy.py --json
python scripts/evals/package_workflow_episode.py --scenario-root tests/fixtures/workflow_evals --output-dir .athanor/episodes/workflow-evals --json
python scripts/evals/export_external_eval_adapter.py --episode-root .athanor/episodes/workflow-evals --output-dir .athanor/external-evals/workflow-evals --json
python scripts/gates/harness_decision_ledger.py --json
python scripts/gates/native_runtime_probe.py --fixture-root tests/fixtures/native_runtime_probe --json
```

Observed:

- Maintenance profile: warn, 6/6 steps, 1 warning, 0 failures,
  `irreversible_actions: 0`.
- Distribution smoke: pass, 7 checks in skip-Claude mode.
- Package footprint policy: warn, 475 files, about 4.1 MB, 0 hard budget
  failures, 20 development-only candidates, `irreversible_actions: 0`.
- External eval adapter: pass, 2 compatibility profiles, network disabled,
  external telemetry disabled, setup commands 0.
- Agent surface: exactly `ci-watcher`, `codex-dispatcher`, `learner`,
  `releaser`.
- Harness decision ledger: pass, 6 decisions after P22.
- Native runtime probe fixtures: pass; dynamic workflow, agent team, and
  worktree are intentionally dry-run/operator-approved rather than
  auto-launched.

## Scorecard

| Dimension | Score | Judgment |
| --- | ---: | --- |
| Claude Code workflow plugin | 9.6 | Strong phase design, restrained visible surface, good extension fit. |
| Local deterministic harness | 9.75 | CI gates, hook replay, schemas, and evidence checks are unusually strong. |
| Loop-engineering platform | 9.6 | Durable goal loops, maintenance profile, trend snapshots, and no-progress exits exist. |
| Harness-engineering platform | 9.65 | Strong feedback/control system; package policy and external adapter are CI-visible. |
| Hook/evidence discipline | 9.8 | Stop/PreToolUse/PostToolUse paths are the strongest area. |
| Trace/eval discipline | 9.7 | Local traces, scenarios, OTel-style export, and episodes are solid. |
| Memory quality | 9.55 | Structurally good; needs more real-run history over time. |
| Distribution smoke | 9.65 | Manifest, loader-visible agents, package existence, and footprint policy are checked. |
| Package footprint policy | 9.55 | Read-only budgets and dev-only classification now exist; actual exclusions remain future packaging work. |
| External benchmark/sandbox interop | 9.6 | Portable episodes now export inspect-like/harbor-like task, scorer, and local-only sandbox metadata. |
| Native execution escalation | 9.35 | Safe dry-run posture; no operator-approved executable recipes yet. |
| Reactive channels/events | 8.9 | Polling and CI gates exist; pushed event compatibility is absent. |
| Knowledge surface freshness | 9.25 | Rich docs and cleanup gates exist; runtime/ship surface is too broad. |

## What Is Good

1. Evidence-before-claims is real, not rhetorical.
2. Default runtime surface is restrained.
3. Most important behavior is schema-backed and tested.
4. Claude hooks are used for deterministic control, matching the official
   hooks model.
5. Local observability exists without default external telemetry.
6. Maintenance is read-only by default.
7. Harness self-improvement is logged in a decision ledger.
8. P19 correctly refuses default native auto-launch.

## What Is Missing

1. Operator-approved worktree/dynamic-workflow/agent-team recipes.
2. Local-only fake channel fixture for pushed CI/review events.
3. Long-run history proving P17/P18/P20/P21/P22 improve outcomes across many
   cycles.
4. A short package-facing knowledge index distinct from full development
   history.

## What Is Overbuilt

1. Historical plans and archives are too prominent in the package footprint.
2. The changelog is valuable but dominates shipped bytes.
3. Regression test files ship as part of the default footprint scan.
4. More registered agents would now be harmful.
5. More default hooks would add startup and failure surface without enough
   benefit.
6. Default dynamic workflow, channel listener, or agent-team launch would be
   premature.

## Add

### P21: Package Footprint Policy Gate

Status: implemented on branch `feat/p21-package-footprint-policy`.

Added a read-only gate that classifies package files by ship profile:
runtime-critical, distribution metadata, docs, development history, tests,
archives, refs, and CI. It reports budgets, largest files, dev-only
candidates, and recommended exclusions. CI runs the gate in warn mode first.

Target movement:

- Package footprint policy: 8.7 -> 9.55.
- Distribution/ship discipline: 9.55 -> 9.65.

### P22: External Eval/Sandbox Adapter

Status: implemented on branch `feat/p22-external-eval-sandbox-adapter`.

Exports existing workflow episodes to an Inspect/Harbor-like layout with a
manifest, task metadata, scorer metadata, and local-only sandbox profile. It
does not install Docker, install Inspect or Harbor, or run networked jobs by
default.

Target movement:

- External benchmark/sandbox interop: 9.3 -> 9.6.

### P23: Native Runtime Playbook

Add operator-approved recipes for worktree creation/cleanup, dynamic workflow
fanout, and agent-team lifecycle fixtures. Keep auto-launch blocked by
default.

Target movement:

- Native execution escalation: 9.35 -> 9.6.

### P24: Reactive Channel Spike

Add a local-only fake channel/event fixture for CI or review event payloads.
Map the payload to existing maintenance/CI-watch actions. No default listener.

Target movement:

- Reactive channels/events: 8.9 -> 9.45-9.55.

## Remove Or Exclude

1. Exclude old plans, archive-heavy docs, and tests from the default ship
   profile where Claude plugin packaging allows it.
2. Quarantine capture-only hooks that are not promoted by evidence.
3. Remove stale score language that predates P17-P20.
4. Avoid adding generic all-purpose skills.
5. Do not ship default external telemetry, channel listeners, dynamic workflow
   launches, or agent-team launches.

## Decision

Continue with P23 after P22 is merged.

Reason: P21 and P22 made the distinction between development repository,
runtime plugin, and external eval package explicit. P23 should now convert the
safe native-runtime probe posture into operator-approved playbooks for
worktree, dynamic workflow, and agent-team lifecycle without default
auto-launch.
