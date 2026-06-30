# lfg-goal State Shape

Goal-loop state shape — the JSON written to `.athanor/goals/<goal_id>/state.json` after each cycle phase transition.

## Required fields (≥8)

- `goal_id` — sha256 prefix (8 hex chars) derived from the goal text + creation timestamp. Stable across resume.
- `cycle_state` — enum (6 macro states):
  - `bootstrapping` — goal.md authored, cycle 1 not yet started
  - `cycle_n_in_progress` — current cycle dispatched, no receipt yet
  - `cycle_n_complete` — receipt validated, awaiting next-cycle decision or Tier 2 judge
  - `goal_complete` — 3-tier check completed: Tier 1 mechanical passed, Tier 2 cross-model judges both agreed `goal_met: true`, AND Tier 3 user ratification confirmed. All three tiers must conjoin for this terminal state.
  - `aborted` — user abort, max-iterations cap hit, or unrecoverable error
  - `scope_change_pending` — user modified goal.md; scope-change-critic dispatched, awaiting decision
- `cycle_phase` — enum (7 within-cycle sub-states). Only meaningful when `cycle_state == cycle_n_in_progress`; for the other 5 macro states it is `null` or absent.
  - `not_started` — cycle allocated but `/athanor:lfg` not yet dispatched
  - `lfg_done_seen` — `/athanor:lfg` completed (DONE sentinel received); receipt-validator not yet dispatched
  - `receipt_validated` — receipt-validator returned; aggregate status recorded in `last_validator_status`
  - `tier1_checked` — Tier 1 mechanical check completed
  - `tier2_checked` — Tier 2 adversarial cross-model judge dispatch completed; verdicts recorded in `tier2_last_verdict`
  - `tier3_pending` — Tier 3 user ratification prompt issued, awaiting user response
  - `tier3_ratified` — Tier 3 user ratification received (any response: yes / continue-iterating / abort); cycle ready for state transition
- `current_cycle` — integer 0..maxIterations
- `last_receipt_path` — string (path to most recent `cycle-N/receipt.md`) OR null
- `last_validator_status` — enum: `all_valid | completed_with_residuals | invalid_steps_present | not_yet_run`
  - `all_valid` — every one of the 9 receipt steps is VALID
  - `completed_with_residuals` — ≥1 step is `completed-with-residuals`, 0 `failed`, 0 `missing`
  - `invalid_steps_present` — ≥1 step is `failed` or `missing`
  - `not_yet_run` — receipt-validator has not yet been dispatched for this cycle
- `tier2_last_verdict` — object `{judge_a: {goal_met: bool}, judge_b: {goal_met: bool}}` OR null (null until Tier 2 first dispatched)
- `aborted_reason` — string (one-line cause) OR null
- `acting_on` — goal id currently claimed by the loop runner. If a caller
  requests a different id, the run-log helper reports a lock conflict instead
  of silently continuing.
- `loop_run_log` — path to the append-only run log JSONL file, relative to the
  goal directory unless absolute. Default: `run-log.jsonl`.
- `budget.max_cycles` — per-goal cycle budget checked before another cycle.
- `budget.max_wall_minutes` — wall-time budget hint checked by the run-log
  inspector when the caller supplies elapsed minutes.
- `budget.max_token_estimate` — token estimate budget hint checked by the
  run-log inspector when the caller supplies token estimates.
- `min_attempts` — minimum attempt count before risky or score-target work can
  be treated as ready for final evaluation.
- `last_evaluator_role` — last evaluator role that inspected the goal, such as
  `judge-a`, `judge-b`, `critic`, or `operator`.
- `lock_status` — enum: `active | conflict | released`.

## Update protocol

`state.json` is overwritten atomically after each cycle phase transition. Use the write-temp-then-rename pattern to avoid partial writes on crash. Each `cycle_phase` transition triggers an atomic write — the file always reflects the last successfully completed phase.

Append-only run log records are written separately to `loop_run_log`; they are
not folded into `state.json`. Use `scripts/loops/loop_run_log.py inspect` to
check lock status, budget warnings, and the min-attempt gate before starting or
finishing a cycle.

## Controller evidence packet

The durable controller reads the state above plus a separate evidence packet
validated by `schemas/durable-loop-evidence.schema.json`.

Score-target evidence adds two optional objects:

- `score_target` — target policy with `overall_score` and
  `min_dimension_score`.
- `assessment` — structured `/athanor:assess` evidence with
  `kind: baseline | delta | final`, `report_path`, `overall_score`,
  `min_dimension_score`, `target_met`, `priority_plan_items`, and per-dimension
  `score`, `target`, `floor`, `target_met`, and `regressed` fields.

With `score_target` present, machine-readable controller actions replace ad hoc
leader branching:

- `bootstrapping` + missing baseline assessment → `run_baseline_assess`.
- valid `cycle_n_complete` receipt + missing assessment → `run_delta_assess`.
- below-target delta/final assessment → `run_lfg_cycle`, carrying target
  dimensions and Priority Plan items into the next cycle.
- final assessment target met + Tier 1/Tier 2 completion gates passed →
  `prompt_tier3_user`.
- invalid receipt, invalid assessment shape, no-progress, or max-iteration
  conditions surface as explicit block/stop decisions, not silent success.

The controller validates `target_met` against the computed score target in both
directions: `true` with failing score/floor/regression evidence blocks Tier 3
prompting, and `false` with passing score/floor/regression evidence blocks
another delivery loop. It also derives the actual minimum dimension score from
`assessment.dimensions[*].score` and treats disagreement with
`assessment.min_dimension_score` as contradictory assessment evidence.

## Resume semantics

On `/athanor:lfg-goal` re-invocation, the leader reads `state.json` and routes based on both `cycle_state` (macro) and `cycle_phase` (within-cycle granularity).

### cycle_phase-aware resume (v0.15.0+)

When `cycle_phase` is present in `state.json`, the leader uses it for granular within-cycle resume positioning:

- `cycle_state == bootstrapping` → next invocation finishes goal.md bootstrap (resume from the goal-shape user confirmation prompt). `cycle_phase` is `null` in this state.
- `cycle_state == cycle_n_in_progress` with `cycle_phase == not_started` → RE-RUN the cycle from the beginning (does NOT increment counter). User is prompted before re-run with reason from `state.json`.
- `cycle_state == cycle_n_in_progress` with `cycle_phase == lfg_done_seen` → dispatch receipt-validator on the existing cycle session (skip re-running `/athanor:lfg`).
- `cycle_state == cycle_n_in_progress` with `cycle_phase == receipt_validated` → skip receipt validation; proceed to Tier 1 mechanical check.
- `cycle_state == cycle_n_in_progress` with `cycle_phase == tier1_checked` → skip Tier 1; proceed to Tier 2 adversarial cross-model judge dispatch.
- `cycle_state == cycle_n_in_progress` with `cycle_phase == tier2_checked` → skip Tier 1+2; proceed to Tier 3 user ratification prompt.
- `cycle_state == cycle_n_in_progress` with `cycle_phase == tier3_pending` → re-issue Tier 3 user ratification prompt (user response was lost mid-session).
- `cycle_state == cycle_n_in_progress` with `cycle_phase == tier3_ratified` → cycle is effectively closed; next invocation starts cycle+1 (equivalent to `cycle_n_complete`).
- `cycle_state == cycle_n_complete` → cycle is closed; next invocation starts cycle+1.
- `cycle_state == scope_change_pending` → next invocation resumes from the scope-change-critic verdict / user ratification gate.
- `cycle_state ∈ {goal_complete, aborted}` → terminal; leader refuses to re-enter the loop and instructs the user to start a fresh invocation.

For all non-terminal states, the leader prints the resume banner with the prior `cycle_state`, `cycle_phase`, and `current_cycle`, then prompts the user for explicit continue/abort.

### Legacy fallback (pre-v0.15.0 state files)

If `state.json` does NOT contain a `cycle_phase` field (written by ≤v0.14.x), the leader falls back to coarse-grained resume using only `cycle_state` and `current_cycle`:

- `cycle_state == cycle_n_in_progress` → resume from `current_cycle + 1` (conservative: assumes the in-progress cycle may be incomplete; user is warned that mid-cycle position is unknown).
- All other `cycle_state` values → same semantics as the cycle_phase-aware path above (bootstrapping, cycle_n_complete, scope_change_pending, goal_complete, aborted are unambiguous without cycle_phase).

The leader logs a one-line warning when falling back: `"state.json missing cycle_phase field (pre-v0.15.0 format); using coarse-grained resume"`.

Malformed `state.json` (unparseable JSON, missing required fields) triggers an explicit abort message (NOT silent fall-back). User can repair manually or start a fresh goal-id.
