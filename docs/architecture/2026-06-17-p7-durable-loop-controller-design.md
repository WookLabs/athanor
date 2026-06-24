# P7 Durable Loop Controller Design

Date: 2026-06-17

## Goal

Turn the documented `/athanor:lfg-goal` ledger loop into an executable local
state-machine controller. P7 should make resume decisions, progress checks,
attempt budgets, stop reasons, and trace emission deterministic before any
higher-autonomy loop is attempted.

## Context

P6 added the workflow trace and deterministic scenario eval harness. The next
gap is loop durability. `skills/lfg-goal/references/state-shape.md` already
defines the intended `.athanor/goals/<goal_id>/state.json` contract, including
macro state, `cycle_phase`, receipt validation status, Tier 2 verdicts, and
terminal states. That contract is currently prose. It is not yet enforced by a
loader, decision engine, fixture runner, or CI gate.

Modern loop and harness references point to the same failure mode: a recurring
agent loop without durable state and explicit stop conditions creates repeated
work, hidden drift, and optimistic completion claims. P7 should therefore add a
small executable controller that consumes state and evidence, records its
decision, and refuses unsafe re-entry.

## Non-Goals

P7 does not:

- invoke Claude Code commands or `/athanor:lfg` directly;
- create autonomous merge, deploy, or install behavior;
- enable new hooks;
- add model-graded evals;
- replace the existing lfg-goal skill text.

P7 does:

- validate and normalize durable goal-loop state;
- decide the next loop action from state, config, and evidence summaries;
- persist state changes atomically;
- emit P6 workflow trace records for every decision;
- add fixture scenarios that prove resume, stop, and escalation behavior.

## Design Options

### Option A: Instrument `/athanor:lfg-goal` Directly

This would edit the prompt skill to call a controller and attempt live runtime
resume behavior immediately.

Trade-off: high visible impact, but the weakest verification story. Most of the
runtime surface is prompt text rather than code, so implementation defects would
be hard to exercise in CI.

### Option B: Executable Local Controller First

Create a Python state schema, loader, decision engine, trace writer integration,
fixture runner, and tests. The lfg-goal skill can consume this contract later.

Trade-off: does not fully automate live lfg-goal yet. It creates the durable
semantics that live instrumentation can safely depend on.

### Option C: Adopt A Durable Workflow Engine

Use an external engine such as Temporal or LangGraph for orchestration.

Trade-off: strong durability primitives, but too much dependency and operating
surface for Athanor's current plugin layer. Athanor needs a local controller
contract before deciding whether an external engine is useful.

## Selected Approach

Use Option B.

P7 will add a repo-local controller under `scripts/loops/`. The controller will
be deterministic, standard-library only, and compatible with the P6 trace
schema. It will not claim live skill orchestration until P10 wires real workflow
traces into command execution.

## Data Model

### Loop State

The controller reads and writes `.athanor/goals/<goal_id>/state.json` using a
schema versioned object:

- `schema_version`: `1`
- `goal_id`: 8-character lowercase hex id
- `cycle_state`: one of `bootstrapping`, `cycle_n_in_progress`,
  `cycle_n_complete`, `goal_complete`, `aborted`, `scope_change_pending`
- `cycle_phase`: `null` or one of `not_started`, `lfg_done_seen`,
  `receipt_validated`, `tier1_checked`, `tier2_checked`, `tier3_pending`,
  `tier3_ratified`
- `current_cycle`: integer, `0..max_iterations`
- `max_iterations`: positive integer
- `no_progress_threshold`: positive integer
- `last_receipt_path`: string or `null`
- `last_validator_status`: one of `all_valid`,
  `completed_with_residuals`, `invalid_steps_present`, `not_yet_run`
- `tier2_last_verdict`: `null` or judge verdict object
- `aborted_reason`: string or `null`
- `no_progress_count`: integer, `0..no_progress_threshold`
- `stop_reason`: string or `null`
- `updated_at`: ISO-8601 UTC timestamp

P7 will accept legacy state without `schema_version` or `cycle_phase` only
through an explicit compatibility path. Malformed JSON, missing required fields,
or contradictory state produces an abort decision rather than silent fallback.

### Loop Decision

The controller returns a normalized decision object:

- `schema_version`: `1`
- `goal_id`
- `action`
- `status`: `pass`, `concern`, `failure`, `skipped`, or `escalated`
- `reason`
- `next_cycle_state`
- `next_cycle_phase`
- `references`
- `evidence`

Initial action enum:

- `bootstrap_goal`
- `resume_cycle_from_start`
- `validate_receipt`
- `run_tier1_check`
- `run_tier2_judges`
- `prompt_tier3_user`
- `start_next_cycle`
- `resume_scope_change_review`
- `complete_goal`
- `stop_no_progress`
- `stop_max_iterations`
- `refuse_terminal_state`
- `abort_invalid_state`
- `require_eval_evidence`

### Evidence Summary

P7 should not parse arbitrary model output. It consumes a small evidence
summary, either passed as a JSON file or constructed by fixture tests:

- `eval_status`: `pass`, `fail`, `missing`, or `not_applicable`
- `validator_status`: optional lfg-goal receipt validator status
- `tier1_passed`: optional boolean
- `tier2_goal_met`: optional boolean
- `tier3_user_response`: optional `yes`, `continue`, or `abort`
- `progress_made`: optional boolean
- `references`: optional artifact references

The evidence summary is intentionally narrower than P6 traces. P6 traces
record the trajectory; P7 decisions consume summarized evidence and then emit
their own trace event.

## Decision Rules

### Terminal Guard

`goal_complete` and `aborted` states are terminal. The controller must return
`refuse_terminal_state` and must not advance the loop.

### Invalid State Guard

Malformed state, missing required fields, unsupported enum values, or impossible
combinations return `abort_invalid_state`. The CLI exits with a non-zero code.

### Resume Routing

The controller mirrors `state-shape.md`:

- `bootstrapping` -> `bootstrap_goal`
- `cycle_n_in_progress` + `not_started` -> `resume_cycle_from_start`
- `cycle_n_in_progress` + `lfg_done_seen` -> `validate_receipt`
- `cycle_n_in_progress` + `receipt_validated` -> `run_tier1_check`
- `cycle_n_in_progress` + `tier1_checked` -> `run_tier2_judges`
- `cycle_n_in_progress` + `tier2_checked` -> `prompt_tier3_user`
- `cycle_n_in_progress` + `tier3_pending` -> `prompt_tier3_user`
- `cycle_n_in_progress` + `tier3_ratified` -> `start_next_cycle`
- `cycle_n_complete` -> `start_next_cycle`
- `scope_change_pending` -> `resume_scope_change_review`

Legacy state without `cycle_phase` gets one explicit coarse fallback decision:
`resume_cycle_from_start` with `status=concern` and a warning reason.

### Attempt Budget

Current executable behavior is narrower than the original June 2026 design
sketch: `current_cycle >= max_iterations` returns `stop_max_iterations` only
when the controller would start another delivery/fix loop, such as
`start_next_cycle`, `resume_cycle_from_start`, or `run_lfg_cycle`. It does not
block ratification-only routes such as `prompt_tier3_user` for a completed
final assessment or legacy `tier2_checked` / `tier3_pending` resume path. When
`stop_max_iterations` is returned, the persisted state becomes `aborted` with a
concrete `aborted_reason`.

### No-Progress Budget

If summarized evidence says `progress_made=false`, increment
`no_progress_count`. A **persistent block** counts as no-progress the same
way: an `eval_status=fail` cycle (emitting `block_failed_eval`) or an
`invalid_steps_present` cycle (emitting `run_scope_drift`) with no positive
progress (`progress_made` not `true`) also increments `no_progress_count`.
A block is "stay put and surface the failure," so it does not advance
`current_cycle`/`cycle_state`/`cycle_phase` — only the `no_progress_count`
accumulator moves. If the count reaches `no_progress_threshold`, return
`stop_no_progress` and persist `aborted`, including when the threshold is
reached on a blocking cycle (the controller returns `stop_no_progress`
instead of the block action).

If evidence says `progress_made=true`, reset `no_progress_count` to `0` —
a single block followed by a progress cycle (the legitimate
"block once → user fixes it → continue" path) never aborts.

### Eval Evidence Guard

When the requested action requires prior evidence and `eval_status=missing`,
return `require_eval_evidence`. This prevents the durable loop from advancing
purely on optimism.

## Trace Emission

Every decision writes one P6 trace record when `--trace-path` is supplied:

- `phase`: `lfg-goal`
- `event_type`: `loop.decision`
- `actor`: `gate`
- `status`: decision status
- `message`: decision reason
- `references`: state path and any evidence references
- `evidence`: action, cycle state, cycle phase, current cycle, stop reason

The trace ID defaults to `goal-<goal_id>` and can be overridden for fixture
runs.

## CLI

Add:

```bash
python scripts/loops/run_goal_loop_controller.py \
  --state .athanor/goals/36470e54/state.json \
  --evidence .athanor/goals/36470e54/evidence/latest.json \
  --trace-path .athanor/traces/goal-36470e54.jsonl \
  --json
```

CLI behavior:

- exit `0` for non-terminal pass/concern decisions that are safe to surface;
- exit `1` for stop decisions that abort the loop by policy;
- exit `2` for invalid state, invalid evidence, or CLI usage errors;
- emit normalized JSON for downstream gates.

## Fixture Runner

Add a deterministic fixture runner:

```bash
python scripts/loops/run_goal_loop_fixtures.py \
  --fixture-root tests/fixtures/durable_loops \
  --json
```

Each fixture contains initial state, evidence summary, expected decision, and
expected state mutation. This keeps loop behavior testable without live Claude
Code sessions.

## Acceptance Criteria

P7 is complete when:

- loop state schema exists and is documented;
- state loader rejects malformed files and handles legacy files explicitly;
- atomic state writes are covered by tests;
- decision tests cover all documented `cycle_phase` resume routes;
- no-progress and max-iteration stops persist explicit abort reasons;
- missing eval evidence produces a non-advancing escalation decision;
- trace emission writes valid P6 records;
- fixture runner passes committed durable-loop scenarios;
- workflow scenario evals include at least one durable-loop trace scenario;
- release-ready or CI story includes the durable-loop fixture gate.

## Score Impact

Expected after P7:

- Loop engineering: 7.6 -> 9.5
- Workflow engineering: 9.2 -> 9.6
- Eval/observability: small lift through trace adoption, larger live lift waits
  for P10

The remaining gap after P7 is live workflow instrumentation, not durable
semantics.
