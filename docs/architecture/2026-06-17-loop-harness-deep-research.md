# Athanor Loop/Harness Deep Research Refresh

Date: 2026-06-17
Purpose: update the post-P4 architecture score against current workflow,
harness, loop, hook, and eval references, then define the next work needed for
all major dimensions to clear a 9.5/10 standard.

## Reference Refresh

The ignored local `ref/` directory was refreshed with shallow clones for the
existing hook/plugin comparison set plus three new loop/harness/eval references:

- `ai-boost-awesome-harness-engineering` at `e11cb2b`
- `cobusgreyling-loop-engineering` at `0dde427`
- `UKGovernmentBEIS-inspect_ai` at `00de5ba`
- `openai-codex` at `1315198`
- `alexei-led-cc-thingz` at `2e590b6`
- `obra-superpowers` at `b62616f`
- official and ecosystem Claude Code plugin/hook repos already listed in
  `docs/architecture/2026-06-16-ref-deep-research.md`

Web sources reviewed:

- Anthropic, "Building effective agents":
  https://www.anthropic.com/engineering/building-effective-agents
- Anthropic, "Harness design for long-running application development":
  https://www.anthropic.com/engineering/harness-design-long-running-apps
- OpenAI, "Harness engineering: leveraging Codex in an agent-first world":
  https://openai.com/index/harness-engineering/
- OpenAI Codex hooks docs:
  https://developers.openai.com/codex/hooks
- OpenAI agent workflow evals docs:
  https://developers.openai.com/api/docs/guides/agent-evals
- Claude Code hooks reference:
  https://code.claude.com/docs/en/hooks
- Claude Code hooks guide:
  https://code.claude.com/docs/en/hooks-guide
- Martin Fowler / Thoughtworks harness engineering article:
  https://martinfowler.com/articles/harness-engineering.html
- Inspect AI docs:
  https://inspect.aisi.org.uk/
- Addy Osmani, "Loop Engineering":
  https://addyosmani.com/blog/loop-engineering/
- MindStudio loop engineering overview:
  https://www.mindstudio.ai/blog/what-is-loop-engineering-ai-coding-agents
- LangChain deep-agent harness engineering article:
  https://www.langchain.com/blog/improving-deep-agents-with-harness-engineering

## Definitions For Scoring

- Workflow engineering: deterministic orchestration of LLMs, tools, skills,
  agents, and verification through known code paths.
- Harness engineering: the environment around agents: repo hygiene, tools,
  context, guardrails, isolation, feedback sensors, observability, and review.
- Loop engineering: autonomous or semi-autonomous recurrence: discover work,
  dispatch, isolate, verify, persist state, decide the next action, and stop or
  escalate on explicit conditions.
- Eval engineering: traces, datasets, graders, and repeatable evaluation runs
  that measure whether workflow or harness changes improve behavior.

## Updated Scorecard

Scores are current-state Athanor scores after P4. They are not target scores.

| Dimension | Score | Read |
| --- | ---: | --- |
| Evidence/replay rigor | 9.7 | Strongest current area. Live-redacted fixtures, replay gate, catalog provenance, and PostToolUse evidence are ahead of most refs. |
| Hook safety and default restraint | 9.6 | Stop/PreToolUse block and PostToolUse warn are narrow enough for performance and false-positive control. |
| Workflow engineering | 8.8 | Spec/TDD, analyze/plan/work, cross-review, and Ralph-style verification loops are strong, but trace-level workflow metrics are missing. |
| Harness engineering | 8.6 | Good guards, work discipline, and repo-embedded scripts; lacks first-class trace/eval artifacts and executable performance budgets. |
| Loop engineering | 7.0 | `/athanor:lfg-goal` has a ledger loop, but there is no modern outer loop controller that discovers work, queues next actions, evaluates progress, and resumes across runs. |
| Eval/observability | 6.5 | Tests are extensive, but agent-run traces, scenario datasets, graders, and regression dashboards are not yet productized. |
| Trust/install UX | 6.8 | P4 dry-run planner is correct, but there is no trust-state model, no reversible apply path, and no hook hash/review workflow. |
| Cross-runtime portability | 8.1 | Matrix exists and refs are cloned; no generator or conformance suite yet. |
| Performance discipline | 7.3 | Catalog has budgets, but they are documentation fields until a benchmark gate enforces them. |
| Plugin-dev onboarding | 7.6 | Internal docs are strong; contributor-facing plugin authoring and validation flow remain thinner than official/plugin-dev refs. |

## What Athanor Does Better Than The Refs

- It treats hook evidence as replayable corpus data rather than README claims.
- It keeps the default hook surface narrow and avoids broad lifecycle hooks
  before live payload evidence exists.
- It has explicit capture-only states, promotion rules, and dry-run install
  planning.
- It already separates maker/checker concerns through planning, review, and
  verification skills.
- It preserves an honesty boundary: unsupported runtime/event claims are marked
  as candidate or synthetic instead of shipped as enforcement.

## What Athanor Is Missing

- Trace artifacts for complete workflow runs: model calls, tool calls,
  guardrail outcomes, handoffs, verifier decisions, and final result.
- Scenario evals: small repeatable tasks that exercise Athanor flows and score
  whether the workflow selected the right path, produced evidence, and stopped
  for the right reason.
- A loop controller outside single-turn commands: durable queue, state machine,
  progress ledger, attempt budget, reviewer split, and human escalation.
- Executable hook performance budgets that measure enabled hooks against
  `hooks/catalog.json`.
- Trust-aware installer state: hook hash, source, review status, reversible
  apply plan, conflict policy, and no-clobber tests.
- Ref freshness governance: `ref/` is intentionally ignored, so tracked docs
  must record HEADs and update cadence.

## Overbuilt Or Risky Areas

- More default hooks would be counterproductive before performance and live
  payload evidence are executable.
- A focused test-runner hook should not become default; it is useful only after
  trace/eval can prove benefit and false-positive rate.
- Strict evidence mode should not become the default until migration and
  false-positive evidence are gathered.
- Large marketplace/catalog surfaces should not be imported wholesale; Athanor's
  advantage is narrow, evidence-first policy.
- Autonomous loop execution should not precede trace/eval; otherwise the loop
  can create high-volume unverified churn.

## 9.5+ Completion Criteria

All major dimensions clear 9.5 only when these objective gates exist:

1. Performance gate: enabled hooks are measured against catalog budgets in CI.
2. Trace gate: every Athanor workflow scenario can emit a normalized trace.
3. Eval gate: a deterministic local scenario suite scores workflow decisions,
   evidence production, stopping conditions, and escalation behavior.
4. Loop gate: the durable loop controller can resume, stop on proof, detect no
   progress, and route review/fix iterations through separate roles.
5. Trust gate: installer apply is reversible, no-clobber, hash-reviewed, and
   disabled for capture-only hooks.
6. Cross-runtime gate: Claude/Codex manifests are generated or verified from one
   source of truth without expanding default runtime cost.

## Recommended Architecture

The next architecture layer should be a measured improvement flywheel:

1. Hook/capture evidence remains the low-level sensor layer.
2. A trace writer turns workflow/hook events into normalized local JSONL traces.
3. A scenario eval runner reads traces and scores decisions with deterministic
   graders first; model graders can be optional later.
4. A loop controller consumes tasks and eval results, not raw optimism.
5. A trust-aware installer uses the same catalog and evidence state to decide
   which hooks can be applied.

This keeps Athanor's current strength, replayable evidence, while adding the
missing loop/eval discipline expected by current harness and loop engineering
practice.

## Ranked Work Program

### P5: Hook Performance Budget + Capture-Only Fixture Infrastructure

Goal: make catalog budgets executable and make capture-only evidence importable
without pretending unsupported events are replayable.

Expected effect:

- Performance discipline: 7.3 -> 9.4
- Evidence/replay rigor: 9.7 -> 9.8
- Hook lifecycle breadth: 7.8 -> 8.6

This is the safest next implementation. It is small, measurable, and removes a
known future bottleneck before any broader loop/installer work.

### P6: Trace And Scenario Eval Harness

Goal: add a local trace schema, scenario fixtures, deterministic graders, and a
runner that scores Athanor workflow behavior.

Expected effect:

- Eval/observability: 6.5 -> 9.5
- Harness engineering: 8.6 -> 9.4
- Workflow engineering: 8.8 -> 9.4

This is the key bridge from "many tests" to "agent workflow quality is
measurable."

### P7: Durable Loop Controller

Goal: add an outer state-machine loop that can discover/resume work, dispatch
roles, enforce attempt budgets, consume eval evidence, and escalate instead of
spinning.

Expected effect:

- Loop engineering: 7.0 -> 9.5
- Workflow engineering: 9.4 -> 9.6 after P6

This should be built only after P6, because a loop without trace/eval is a
larger way to make unmeasured mistakes.

### P8: Trust-Aware Installer Apply Path

Goal: extend the P4 dry-run planner into reversible apply/remove operations
with hook hashes, trust status, conflict policy, and no-clobber guarantees.

Expected effect:

- Trust/install UX: 6.8 -> 9.5
- Hook catalog/installer UX: 7.8 -> 9.5

This should remain after P5 and preferably after P6, because installer writes
should depend on measured cost and evidence state.

### P9: Cross-Runtime Conformance Generator

Goal: generate or verify Claude/Codex hook manifests from one catalog source
while keeping runtime defaults unchanged.

Expected effect:

- Cross-runtime portability: 8.1 -> 9.5

This is valuable, but lower priority than P5-P8 because Athanor's current users
benefit more from measurement, eval, loop, and trust first.

## Immediate Decision

Proceed with P5 first. It is the narrowest implementation that directly serves
the 9.5+ objective and unlocks the later trace/eval/loop/installer work.

P5 design should be conservative:

- Add `scripts/gates/check_hook_performance_budget.py`.
- Measure enabled catalog hooks with representative safe payload fixtures.
- Fail CI when median or max runtime exceeds budget by a documented threshold.
- Let `import_hook_fixture.py` accept capture-only live-redacted fixtures for
  cataloged events while marking them non-replayable.
- Let `replay_hook_fixtures.py` validate fixture safety/provenance before
  skipping unsupported capture-only events with an explicit `skipped` result.
- Do not fabricate live fixtures. Real capture-only promotion still requires a
  live Claude/Codex event captured through the opt-in harness.
- Do not install or enable new default hooks.

