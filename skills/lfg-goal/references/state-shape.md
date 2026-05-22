# lfg-goal State Shape

Goal-loop state shape — the JSON written to `.athanor/goals/<goal_id>/state.json` after each cycle phase transition.

## Required fields (≥7)

- `goal_id` — sha256 prefix (8 hex chars) derived from the goal text + creation timestamp. Stable across resume.
- `cycle_state` — enum:
  - `bootstrapping` — goal.md authored, cycle 1 not yet started
  - `cycle_n_in_progress` — current cycle dispatched, no receipt yet
  - `cycle_n_complete` — receipt validated, awaiting next-cycle decision or Tier 2 judge
  - `goal_complete` — Tier 2 judges agreed `goal_met: true`
  - `aborted` — user abort, max-iterations cap hit, or unrecoverable error
  - `scope_change_pending` — user modified goal.md; scope-change-critic dispatched, awaiting decision
- `current_cycle` — integer 0..maxIterations
- `last_receipt_path` — string (path to most recent `cycle-N/receipt.md`) OR null
- `last_validator_status` — enum: `all_valid | invalid_steps_present | not_yet_run`
- `tier2_last_verdict` — object `{judge_a: {goal_met: bool}, judge_b: {goal_met: bool}}` OR null (null until Tier 2 first dispatched)
- `aborted_reason` — string (one-line cause) OR null

## Update protocol

`state.json` is overwritten atomically after each cycle phase transition. Use the write-temp-then-rename pattern to avoid partial writes on crash.

## Resume semantics

On `/athanor:lfg-goal` re-invocation, if `state.json` exists AND `cycle_state` is neither `goal_complete` nor `aborted`, resume from `current_cycle + 1` with the same `goal_id`. The leader prints the resume banner with the prior `cycle_state` and prompts the user for explicit continue/abort.

If `cycle_state` is `goal_complete` or `aborted`, treat the goal directory as terminal: the leader refuses to re-enter the loop and instructs the user to start a fresh invocation.
