# P16 Deep Research Refresh: Workflow, Loop, Harness, And Distribution

Date: 2026-06-17
Local basis: `main` after P15 eval episode packaging (`de07c1d`).
Runtime checked: Claude Code `2.1.179` on Windows.
Purpose: compare Athanor against current workflow, loop, harness, eval, and
plugin-distribution practice, then identify what is still missing.

## Executive Verdict

Athanor is now a strong local harness plugin. P14 and P15 closed two important
frontier gaps: local OTel-style trace export and portable workflow eval episode
packaging. The strongest surfaces are executable: hook replay, hook
performance budgets, trust-aware hook install/remove, cross-runtime
conformance, runtime backend recommendation, live command trace anchors,
OTel-style export, deterministic workflow evals, portable eval episodes,
durable loop fixtures, and entropy cleanup.

The new research and local CLI smoke changed the next priority. The biggest
current gap is no longer eval packaging or OTel vocabulary. It is distribution
truth:

1. `claude --plugin-dir . plugin details athanor` reports **11 agents**, while
   Athanor docs and tests claim only 4 registered agents and 7 reference docs.
2. Static frontmatter tests are insufficient because Claude Code's plugin
   inventory still treats files under plugin-root `agents/` as agent components.
3. `claude plugin validate` passes, but with warnings:
   - root `CLAUDE.md` is not loaded as plugin context;
   - marketplace manifest has no marketplace description.
4. `claude plugin details` reports an always-on cost of about **2,512 tokens**
   and exposes `agent` inventory/cost as a distribution surface Athanor does not
   currently gate.

Overall current scores:

- Claude Code workflow plugin: 9.45/10
- Local deterministic harness: 9.60/10
- Modern loop/harness platform: 9.25/10

The local harness score is now above 9.5. The plugin score is pulled down by
runtime-visible distribution drift, not by workflow design.

## Sources Reviewed

Primary and high-signal references checked on 2026-06-17:

- OpenAI, "Harness engineering: leveraging Codex in an agent-first world"
  (2026-02-11): https://openai.com/index/harness-engineering/
- OpenAI Agents SDK guide:
  https://developers.openai.com/api/docs/guides/agents
- OpenAI Agents SDK tracing:
  https://openai.github.io/openai-agents-python/tracing/
- OpenAI agent workflow evals:
  https://developers.openai.com/api/docs/guides/agent-evals
- Claude Code changelog:
  https://code.claude.com/docs/en/changelog
- Claude Code plugins:
  https://code.claude.com/docs/en/plugins
- Claude Code discover/install plugins:
  https://code.claude.com/docs/en/discover-plugins
- Claude Code plugin reference:
  https://code.claude.com/docs/en/plugins-reference
- Claude Code hooks guide:
  https://code.claude.com/docs/en/hooks-guide
- Claude Code dynamic workflows:
  https://code.claude.com/docs/en/workflows
- Claude Code `/goal`:
  https://code.claude.com/docs/en/goal
- Claude Code agent teams:
  https://code.claude.com/docs/en/agent-teams
- Claude Code worktrees:
  https://code.claude.com/docs/en/worktrees
- Claude Code best practices:
  https://code.claude.com/docs/en/best-practices
- OpenTelemetry AI agent observability:
  https://opentelemetry.io/blog/2025/ai-agent-observability/
- Inspect AI:
  https://inspect.aisi.org.uk/

Local commands run:

```text
claude --version
claude plugin --help
claude plugin details athanor --help
claude plugin validate .claude-plugin/plugin.json
claude plugin validate .claude-plugin/marketplace.json
claude --plugin-dir . plugin details athanor
claude plugin list --json
claude plugin validate --help
claude plugin tag --dry-run .
```

## External Baseline

### Workflow Engineering

Claude Code's current execution model is multi-surface:

- subagents for focused delegated work;
- dynamic workflows for script-held orchestration and large fanout;
- agent teams for peer sessions with independent context, shared tasks, and
  direct teammate communication;
- worktrees for edit isolation;
- `/goal` for turn-to-turn recurrence until a completion condition is met;
- hooks for deterministic lifecycle control;
- plugins for versioned, shareable bundles of skills, agents, hooks, MCP, LSP,
  monitors, and settings.

Athanor matches the command-phase design well. P12 gave it a backend
recommendation contract. The remaining gap is that runtime selection is still
mostly advisory: Athanor does not launch dynamic workflows or agent teams and
does not make worktree isolation a first-class live execution backend.

### Loop Engineering

Claude `/goal` is the native loop reference: a completion condition is checked
after each turn by a separate fast model; if unmet, Claude continues. Good loop
engineering needs explicit progress evidence, stop conditions, no-progress
detection, attempt budgets, and escalation.

Athanor is strong here. `lfg-goal`, durable loop state/evidence schemas,
decision fixtures, Stop verification, and workflow eval scenarios are coherent.
The remaining gaps are:

- loop outcomes do not yet drive memory promotion or lesson decay;
- harness changes do not declare expected metric movement and later measured
  results.

### Harness Engineering

OpenAI's harness write-up and Claude's plugin/worktree/runtime docs point to
the same pattern: the repository and its executable checks become the agent's
operating environment. The engineer's role shifts toward task specs, repo
legibility, constraints, tests, traces, review loops, and cleanup.

Athanor is well aligned:

- local schemas and scripts are the source of truth;
- CI gates enforce hook replay, budgets, conformance, trend snapshots, entropy,
  runtime adapter fixtures, workflow evals, and episode packaging;
- trust install/remove keeps hook writes reviewable;
- external telemetry is not default.

The next harness maturity level is distribution measurement and
trace-to-memory/harness-decision feedback.

### Eval And Observability

OpenAI's current eval guidance starts with traces while debugging behavior,
then moves to repeatable datasets and eval runs. OpenAI Agents SDK tracing
captures workflow traces, agent spans, generation spans, tool calls, handoffs,
guardrails, and custom events. OpenTelemetry's GenAI work standardizes shapes
for AI-agent telemetry. Inspect AI adds a broader benchmark standard with
datasets, agents, tools, scorers, and sandboxing.

Athanor now has a strong local version of this:

- P6 workflow traces and deterministic scenario runner;
- P13 live command trace anchors;
- P14 local OTel-style export;
- P15 portable local eval episode packaging.

Remaining gap: the P15 episode package is intentionally conservative. It has
sandbox metadata and local runner commands, but does not execute arbitrary setup
commands, run Docker/Kubernetes sandboxes, or integrate with Inspect/OpenAI
Evals/LangSmith.

### Plugin Distribution Engineering

The Claude plugin reference makes distribution measurable:

- `claude plugin validate` validates manifests and supports `--strict`;
- `claude plugin details` reports component inventory and projected token cost;
- plugin root `CLAUDE.md` is explicitly not loaded as plugin context;
- plugin `agents/` contributes agent components;
- marketplace plugins are cached and cannot reference files outside the plugin
  directory.

This is where Athanor is currently weakest. It has static conformance checks,
but no gate that verifies the actual loader inventory and cost surface. The
current "4 registered agents" claim is static-test true but runtime-inventory
false.

## Local Runtime Findings

### Finding 1: Agent Inventory Drift

Command:

```text
claude --plugin-dir . plugin details athanor
```

Observed:

```text
Component inventory
  Skills (12)
  Agents (11)  analyst, ci-watcher, cleaner, codex-dispatcher, critic,
               executor, learner, planner, releaser, researcher, reviewer
  Hooks (3)  Stop, PreToolUse, PostToolUse
```

Expected from Athanor docs/tests:

```text
4 registered agents:
  learner, releaser, ci-watcher, codex-dispatcher
7 reference docs:
  analyst, cleaner, critic, executor, planner, researcher, reviewer
```

Impact:

- User-visible plugin inventory is larger than intended.
- Always-on token cost includes descriptions for reference-only roles.
- The old collision risk is not fully gone because the loader still sees the
  pipeline role files as agent components.
- Static tests that only inspect `name:` frontmatter do not model Claude's
  actual component discovery behavior.

Likely fix options:

1. Add an explicit manifest `agents` list containing only the 4 intended files,
   if Claude's manifest field overrides default `agents/` autodiscovery.
2. Move the 7 reference docs out of plugin-root `agents/` to a non-component
   docs path such as `docs/agent-roles/` or `concepts/agent-roles/`.
3. Keep the current layout but stop claiming 4 runtime agents. This is not
   recommended because it preserves avoidable surface area.

Recommended: test option 1 first. If `plugin details` still reports 11, move
the 7 reference docs out of `agents/`.

### Finding 2: Validation Warnings Are Real Distribution Signals

`claude plugin validate .claude-plugin/plugin.json` passes with a warning:

```text
CLAUDE.md at the plugin root is not loaded as project context.
```

`claude plugin validate .claude-plugin/marketplace.json` passes with a warning:

```text
No marketplace description provided.
```

Impact:

- The root `CLAUDE.md` warning is acceptable only if Athanor documents it as
  repo-developer guidance, not shipped plugin context.
- The marketplace warning is easy to fix by adding a marketplace description.
- P16 should capture warnings and decide which are allowed vs. which fail.

### Finding 3: Token Cost Surface Is Now First-Class

`plugin details` reports:

```text
Always-on: ~2,512 tok added to every session
```

This is not catastrophic for a workflow plugin, but it is high enough to gate.
The largest on-invoke components are expected (`lfg-goal`, `setup`,
`discuss`, `debug`), but the always-on cost should shrink if the unintended
agent inventory is corrected.

## Updated Scorecard After P15

| Dimension | Score | Read |
| --- | ---: | --- |
| Command/workflow phase design | 9.6 | Strong, small command topology with plan/execute separation. |
| Thin leader/context isolation | 9.5 | Strong design; loader-visible 11-agent drift weakens the surface. |
| Hook safety and evidence | 9.7 | Mature replay, redaction, evidence modes, and budgets. |
| Hook performance discipline | 9.6 | Gate and trend snapshot exist. |
| Trust/install engineering | 9.45 | Apply/remove/dry-run are reviewable. |
| Runtime backend selection | 9.15 | P12 decision contract exists; native launch remains future work. |
| Worktree/runtime isolation | 8.6 | Recommended but not first-class live execution. |
| Agent-team/dynamic-workflow readiness | 8.7 | Decision contract exists; native backend use remains opt-in/future. |
| Cross-runtime conformance | 9.5 | CI-backed contract. |
| Local eval harness | 9.6 | P15 raises local eval packaging above 9.5. |
| Durable loop engineering | 9.5 | Good state/evidence/decision model. |
| Live observability | 9.2 | P13 anchors exist; nested span coverage is not exhaustive. |
| OTel/interoperability | 9.5 | P14 local export closes the previous major gap. |
| Benchmark/sandbox export | 9.3 | P15 packages episodes; heavier sandbox integration remains absent. |
| Marketplace/distribution UX | 8.35 | Actual loader/cost smoke exposes drift and warnings. |
| Registered-agent surface discipline | 7.6 | Static tests say 4; runtime inventory says 11. |
| Trace-to-memory quality loop | 8.2 | Lessons exist; impact is not eval-driven. |
| Harness self-evolution | 7.4 | Needs decision ledger and outcome checks. |
| Security/permission posture | 9.3 | Conservative defaults remain correct. |

## What Athanor Does Well

1. It has a coherent workflow identity instead of a giant feature pile.
2. It is unusually executable: many policies are schemas, gates, fixtures, and
   CI jobs.
3. Hook safety is mature and conservative.
4. Trace/eval infrastructure is local-first and privacy-preserving.
5. P14/P15 make the eval/trace layer portable enough for future external
   harnesses.
6. Trust install/remove avoids silent settings mutation.
7. Entropy cleanup exists before higher-autonomy surfaces are expanded.

## What Is Missing

1. Loader-level distribution smoke that checks actual `plugin details` output.
2. Correction of the 11-agent inventory drift.
3. A token/cost budget policy for always-on plugin load.
4. A marketplace description and strict-validation policy.
5. A documented root `CLAUDE.md` stance: repo-dev instruction, not plugin
   context.
6. Trace-to-memory promotion/decay driven by eval outcomes.
7. Harness decision ledger tying harness changes to expected metric movement.
8. Native launch/probe for dynamic workflows, agent teams, and worktrees.

## Overbuilt Or Risky

1. More default hooks. The current conservative hook surface is still right.
2. More registered agents. The runtime already exposes too many agents.
3. Default external telemetry. Keep exports local and opt-in.
4. Agent teams as a default execution path. Claude docs describe higher cost
   and experimental setup, so this should stay explicit.
5. LLM-as-judge release gates. Deterministic gates should remain primary.
6. Strict validation without warning policy. Root `CLAUDE.md` may remain
   intentionally present for repository development, so P16 must distinguish
   allowed from actionable warnings.

## Add

1. P16 distribution/cost smoke gate:
   - run `claude plugin validate` when available;
   - record warnings;
   - optionally run `--strict` in informational mode first;
   - run `claude --plugin-dir . plugin details athanor`;
   - parse Skills/Agents/Hooks/MCP/LSP counts;
   - parse always-on token cost;
   - fail on manifest/marketplace version drift;
   - report package file count and byte size.

2. P16a loader-inventory fix:
   - either constrain plugin manifest `agents` to the 4 intended files or move
     7 reference docs out of the plugin-root `agents/` component directory;
   - add a regression test that shells out to `claude --plugin-dir . plugin
     details athanor` when `claude` exists and skips otherwise;
   - keep a pure-Python fallback that checks static manifest/path invariants.

3. P17 trace-to-memory quality loop:
   - lesson promotion requires trace/eval evidence;
   - stale or unhelpful lessons decay/quarantine;
   - scenario runs compare with/without selected lesson injection where local
     deterministic evidence is available.

4. P18 harness decision ledger:
   - every harness change records expected metric direction, verification
     command, observed result, and rollback/follow-up decision.

## Remove Or De-Emphasize

1. The claim that 7 pipeline files under `agents/` are not runtime-visible
   agents, unless the loader inventory is fixed.
2. Stale scorecards that predate P14/P15 or miss the new loader-level finding.
3. Pipeline reference docs living in plugin component directories if manifest
   allowlisting cannot hide them.
4. Marketplace distribution without description metadata.
5. Any assumption that frontmatter-only tests are enough for plugin surface
   truth.

## Recommended Next Plan

Proceed with P16 before P17.

P16 should be slightly expanded from "distribution smoke" to
"distribution smoke plus loader-surface correction" because the smoke already
found a real gap. The order should be:

1. Write a P16 plan and failing tests for loader inventory/cost reporting.
2. Implement a read-only `distribution_smoke.py` gate that emits JSON and
   records `claude` CLI availability, validation warnings, component inventory,
   always-on token estimate, manifest/marketplace pins, and package footprint.
3. Fix marketplace metadata warning.
4. Fix the 11-agent inventory drift using manifest allowlisting first; if that
   does not work, move the 7 reference docs outside `agents/`.
5. Add CI gate. It must be skip-safe when `claude` is unavailable, but strict
   when the CLI is installed.
6. Re-run `claude --plugin-dir . plugin details athanor` and require 4 agents
   before claiming the 4-agent diet is truly enforced.

P17 and P18 remain valid, but they should wait until the published plugin
surface is truthful and measured.

## Bottom Line

Yes, Athanor is doing workflow engineering, loop engineering, and harness
engineering. After P14/P15 it is strong on local eval/trace harnesses. The next
quality jump is distribution truth: the actual Claude plugin loader must agree
with Athanor's documented surface, and token/cost inventory must become a
release signal.
