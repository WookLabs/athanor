# P6 Trace And Scenario Eval Harness Design

Date: 2026-06-17

## Goal

Add a deterministic local trace and scenario-eval layer for Athanor workflow
quality. This closes the current observability gap without changing runtime
policy, enabling new hooks, or turning `/athanor:lfg-goal` into an autonomous
loop before eval evidence exists.

## Context

Athanor already has strong low-level evidence streams:

- PostToolUse test evidence in `.athanor/sessions/*/.hook-state/test-evidence.jsonl`
- Freeze file-change evidence in `.hook-state/freeze-change-evidence.jsonl`
- hook payload replay fixtures in `tests/fixtures/hooks/index.json`
- lfg-goal receipt validation prompts and judge rubrics

Those streams prove specific gates, but they do not describe a complete
workflow run. Current harness references expect traces that can represent
model/tool calls, handoffs, guardrail outcomes, verifier decisions, and final
stop/escalation behavior. P6 adds that missing layer.

## Design Options

### Option A: Instrument Every Existing Skill Immediately

This would add trace writes into `/athanor:plan`, `/athanor:work`, `/athanor:lfg`,
and hook scripts in one change.

Trade-off: high coverage, but high risk. Many skill files are prompt surfaces,
not Python code, and adding instrumentation everywhere would mix runtime behavior
with an unproven trace schema.

### Option B: Local Trace/Eval Harness First

Add a schema, a small Python trace writer, deterministic scenario fixtures, and
a local scenario runner. Existing workflows can adopt it later, but the trace
contract and graders become executable immediately.

Trade-off: does not claim full runtime instrumentation yet. It does create the
measured foundation needed before a durable loop controller.

### Option C: Use External Eval Frameworks

Adopt Inspect AI or another eval framework as the primary runner.

Trade-off: mature concepts, but unnecessary dependency surface for Athanor's
current local plugin gates. Athanor needs a tiny deterministic runner first;
external graders can be optional after the local contract is stable.

## Selected Approach

Use Option B.

P6 will create a repo-local trace/eval harness with no new runtime default
behavior. It will be deterministic, JSON-based, and CI-friendly. Later phases
can instrument live commands and feed the same trace format into P7's loop
controller.

## Architecture

### Trace Record

A workflow trace is a JSONL file of normalized records. Each record has:

- `schema_version`: `1`
- `trace_id`: stable run identifier
- `seq`: positive integer sequence number
- `phase`: workflow phase such as `plan`, `work`, `review`, `lfg`, or `lfg-goal`
- `event_type`: normalized event such as `workflow.started`,
  `agent.dispatched`, `gate.evaluated`, `verifier.result`,
  `escalation.required`, or `workflow.finished`
- `actor`: `leader`, `worker`, `hook`, `gate`, or `external`
- `status`: `started`, `pass`, `concern`, `failure`, `skipped`, or `escalated`
- `message`: short human-readable summary
- `references`: optional list of repo-relative paths or stable ids
- `evidence`: optional JSON object with deterministic evidence fields

The trace writer is intentionally small. It appends validated records, assigns
sequence numbers, and leaves interpretation to graders.

### Scenario Fixture

A scenario fixture is a JSON file containing:

- `schema_version`: `1`
- `id`
- `description`
- `min_score`
- `trace`: an inline list of trace records, or later a path to a trace file
- `graders`: deterministic checks

Supported grader kinds for P6:

- `require_event`: at least one record matches all requested fields
- `forbid_event`: no record matches all requested fields
- `require_order`: a matching `before` event appears before a matching `after`
  event
- `require_reference`: a matching event references a required artifact path

The runner reports each grader as `pass` or `fail`, computes
`score = passed / total`, and marks a scenario as pass only when score meets
`min_score`.

### Runner

`scripts/evals/run_workflow_scenarios.py` reads all JSON fixtures from a
scenario root, evaluates them, and emits a JSON report:

- top-level `status`
- per-scenario `score`, `status`, `passed`, `total`
- per-grader result and reason

It exits `0` only when every scenario passes. This gives CI a future gate while
keeping P6 local and deterministic.

## Initial Scenario Set

P6 ships three scenarios:

1. `work-evidence-happy-path`: `/athanor:work` dispatches an executor, records
   passing verifier evidence, and finishes with a pass status.
2. `work-missing-evidence-escalates`: missing evidence must produce a concern
   and an explicit escalation before workflow finish.
3. `lfg-goal-receipt-loop`: `/athanor:lfg-goal` evaluates a receipt, invokes a
   judge, and only then records goal-loop completion.

These scenarios are not model-quality evals yet. They are harness-quality evals:
they prove the trace contract can score workflow decisions, evidence
production, stopping conditions, and escalation behavior.

## Boundaries

P6 does not:

- enable new hooks;
- call a model grader;
- mutate user settings;
- run `/athanor:lfg-goal` autonomously;
- claim every live workflow is instrumented.

P6 does:

- define the trace contract;
- provide a deterministic local scenario runner;
- add scenario fixtures that exercise the workflow quality dimensions named in
  the 9.5+ audit;
- prepare P7 to consume trace/eval results instead of raw optimism.

## Architecture Review

Strengths:

- Low blast radius: new scripts and fixtures, no runtime default changes.
- Strong measurement path: local deterministic scores before model graders.
- Fits Athanor's existing evidence style: JSONL, CI gate, schema/doc/test lock.
- Keeps P7 honest: a loop controller can consume scenario reports later.

Risks and mitigations:

- Risk: scenario fixtures become artificial checklists. Mitigation: require
  workflow-specific events, artifact references, and order checks, not only
  token presence.
- Risk: trace schema grows into a broad observability platform. Mitigation:
  keep P6 schema v1 minimal and defer live instrumentation breadth.
- Risk: tests pass while skills remain uninstrumented. Mitigation: document the
  boundary honestly and treat live instrumentation as a follow-up, not part of
  P6's completion claim.

## Score Impact

Expected after P6:

- Eval/observability: 6.5 -> 9.5 for local deterministic harness quality
- Harness engineering: 8.6 -> 9.4
- Workflow engineering: 8.8 -> 9.4

Remaining gap after P6: live workflow instrumentation and durable loop control
belong to P7.
