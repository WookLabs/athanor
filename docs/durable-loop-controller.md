# Durable Loop Controller

P7 adds an executable local controller for the `/athanor:lfg-goal` durable
ledger loop. It turns the documented state contract in
`.athanor/goals/<goal_id>/state.json` into deterministic decisions that can be
tested, traced, and gated in CI.

## Boundary

The controller does not invoke Claude Code, does not call `/athanor:lfg`, does
not enable hooks, and does not merge or deploy changes. It reads state and
evidence summaries, returns a decision, optionally writes the updated state,
and can emit a P6 workflow trace event.

The companion run-log helper,
`scripts/loops/loop_run_log.py`, is narrower: it appends JSONL records to the
goal directory and inspects lock, budget, and min-attempt posture. It reports
`irreversible_actions: 0`; appending a log record is the only write it performs.

## State And Evidence

State files follow `schemas/durable-loop-state.schema.json` and live at:

```bash
.athanor/goals/<goal_id>/state.json
```

Evidence summaries follow `schemas/durable-loop-evidence.schema.json`. They are
intentionally narrow: eval status, receipt validator status, Tier 1/Tier 2/Tier
3 signals, progress status, optional score-target policy, optional structured
assessment evidence, and artifact references.

When `score_target` is absent, the controller uses the legacy durable resume
router. When `score_target` is present, `/athanor:lfg-goal` uses the adaptive
controller model:

- `work` remains the task/subtask execution engine inside a cycle.
- `lfg` remains one delivery loop.
- `assess` is the quality and goal-fit evaluation gate.
- `lfg-goal` is the adaptive goal controller that chooses the next sub-loop
  from receipt and assessment evidence.

The adaptive controller emits machine-readable actions:

- `run_baseline_assess` before the first score-target delivery loop when no
  baseline assessment packet exists.
- `run_delta_assess` after a valid cycle receipt when no delta assessment packet
  exists.
- `run_lfg_cycle` when the latest assessment is below target and the loop should
  run another delivery/fix cycle. The decision evidence carries
  `target_dimensions` and `priority_plan_items`.
- `prompt_tier3_user` when final assessment evidence meets the score target and
  completion gates have passed.
- `run_scope_drift`, `require_receipt_validation`,
  `require_assessment_evidence`, `stop_no_progress`, and
  `stop_max_iterations` when the controller cannot honestly advance.

Assessment packets are fail-loud: malformed score fields, missing dimension
data, non-boolean target flags, or contradictory `target_met` claims are not
treated as success. The controller derives the actual minimum dimension score
from `assessment.dimensions[*].score` and blocks if it disagrees with the packet
field `assessment.min_dimension_score`. A final assessment's `target_met` flag is
checked both ways: `true` must also meet `score_target.overall_score`,
`score_target.min_dimension_score`, dimension floors, and no-regression
requirements before the controller can emit `prompt_tier3_user`; `false` is also
blocked when those computed requirements are satisfied.

Current evidence wins over stale state. If `evidence.validator_status` is
`invalid_steps_present`, the controller blocks even when `state.json` still says
`last_validator_status: all_valid`. If `eval_status` is `fail`, the controller
emits `block_failed_eval` instead of continuing to tier checks or another cycle.

A persistent block is bounded by the No-Progress Budget. An `eval_status=fail`
block (`block_failed_eval`) or an `invalid_steps_present` block (`run_scope_drift`)
with no positive progress (`progress_made` not `true`) increments
`no_progress_count` without advancing `current_cycle`/`cycle_state`/`cycle_phase`.
When that count reaches `no_progress_threshold` the controller returns
`stop_no_progress` (terminal `aborted`) instead of the block action, so a stuck
"eval keeps failing" or "receipt keeps coming back invalid" loop still terminates.
A subsequent `progress_made=true` cycle resets `no_progress_count` to `0`, so the
legitimate "block once → user fixes it → continue" path never aborts.

The max-iteration cap is enforced when the controller would start another
delivery/fix loop. It does not block `prompt_tier3_user` for a valid final
assessment on the last allowed cycle.

Run-log records follow `schemas/loop-run-log-record.schema.json` and live at
the `loop_run_log` path in `state.json`, defaulting to
`.athanor/goals/<goal_id>/run-log.jsonl`.

The optional run-log fields in `state.json` are:

- `acting_on`: goal id currently claimed by the runner.
- `loop_run_log`: append-only JSONL path.
- `budget.max_cycles`, `budget.max_wall_minutes`, `budget.max_token_estimate`.
- `min_attempts`: minimum attempts before risky or score-target finalization.
- `last_evaluator_role`: latest evaluator role name.
- `lock_status`: `active`, `conflict`, or `released`.

## Controller CLI

Run one decision:

```bash
python scripts/loops/run_goal_loop_controller.py \
  --state .athanor/goals/36470e54/state.json \
  --evidence .athanor/goals/36470e54/evidence/latest.json \
  --trace-path .athanor/traces/goal-36470e54.jsonl \
  --json
```

Use `--write-state` when the caller wants the decision applied back to
`state.json`. Stop decisions such as `stop_no_progress` and
`stop_max_iterations` persist `cycle_state=aborted` with a concrete
`stop_reason` when `--write-state` is present.

Append and inspect run-log posture:

```bash
python scripts/loops/loop_run_log.py append \
  --goal-dir .athanor/goals/36470e54 \
  --event cycle_started \
  --json

python scripts/loops/loop_run_log.py inspect \
  --goal-dir .athanor/goals/36470e54 \
  --requested-goal-id 36470e54 \
  --json
```

`inspect` reports lock conflict, budget warnings, and min-attempt gate status
without mutating files.

Exit codes (typed contract — `exit 0` ⟺ the controller authorized a forward
action):

- `0`: the controller authorized a **forward** action (e.g. `run_lfg_cycle`,
  `run_baseline_assess`, `run_delta_assess`, `prompt_tier3_user`,
  `bootstrap_goal`, `start_next_cycle`, `resume_*`, `run_tier1_check`).
- `1`: the controller **halted or refused to advance** — any terminal stop
  (`stop_max_iterations`, `stop_no_progress`) **or** block/refuse action
  (`block_failed_eval`, `run_scope_drift`, `require_assessment_evidence`,
  `require_receipt_validation`, `require_eval_evidence`, `refuse_terminal_state`).
  A re-driver branching on exit code must treat `1` as "do not proceed."
- `2`: invalid state, invalid evidence, or CLI usage error
  (`LoopStateError`).

When `--trace-path` is supplied, the CLI appends a P6 trace record:

- `phase`: `lfg-goal`
- `event_type`: `loop.decision`
- `actor`: `gate`
- `status`: decision status

## Fixture Gate

Run committed durable-loop scenarios:

```bash
python scripts/loops/run_goal_loop_fixtures.py \
  --fixture-root tests/fixtures/durable_loops \
  --json
```

The fixture gate covers:

- resume after `receipt_validated`
- terminal `goal_complete` refusing re-entry
- `stop_max_iterations`
- `stop_no_progress`
- `require_eval_evidence`

These fixtures are deterministic. They do not use model output or live Claude
Code sessions.
