# LFG Loop State Shape

Durable state lives at `.athanor/loops/<loop-id>/state.json`.

Required fields:

```json
{
  "schema_version": 1,
  "loop_id": "36470e54",
  "cycle_state": "bootstrapping",
  "cycle_phase": null,
  "current_cycle": 0,
  "acting_on": "36470e54",
  "loop_run_log": "run-log.jsonl",
  "max_iterations": 5,
  "budget": {
    "max_cycles": 5,
    "max_wall_minutes": null,
    "max_token_estimate": null
  },
  "min_attempts": 0,
  "no_progress_threshold": 2,
  "last_receipt_path": null,
  "last_validator_status": "not_yet_run",
  "last_evaluator_role": null,
  "lock_status": "active",
  "tier2_last_verdict": null,
  "aborted_reason": null,
  "no_progress_count": 0,
  "stop_reason": null,
  "updated_at": "2026-07-05T00:00:00Z"
}
```

Cycle states:

- `bootstrapping`
- `cycle_n_in_progress`
- `cycle_n_complete`
- `scope_change_pending`
- `loop_complete`
- `aborted`

Cycle phases for `cycle_n_in_progress`:

- `not_started`
- `lfg_done_seen`
- `receipt_validated`
- `tier1_checked`
- `tier2_checked`
- `tier3_pending`
- `tier3_ratified`

Controller decisions must be derived from `state.json` plus
`evidence/latest.json`; assistant prose is not controller evidence.

Run-log and safety fields:

- `acting_on`: loop id currently locked by the leader.
- `loop_run_log`: append-only JSONL path, usually `run-log.jsonl`.
- `budget.max_cycles`: configured cycle cap.
- `budget.max_wall_minutes`: optional wall-clock budget.
- `budget.max_token_estimate`: optional token budget.
- `min_attempts`: minimum cycles before risky or score-target completion.
- `last_evaluator_role`: last assessor/reviewer/judge that supplied evidence.
- `lock_status`: `active`, `conflict`, or `released`.

Legacy resume compatibility is narrow. If an existing state file lacks the
new run-log and safety fields (`acting_on`, `loop_run_log`, `budget`,
`min_attempts`, `last_evaluator_role`, `lock_status`), controller load
normalizes them to the current shape with explicit defaults:
`acting_on=<loop_id>`, `loop_run_log=.athanor/loops/<loop_id>/run-log.jsonl`,
`budget.max_cycles=max_iterations`, nullable budget limits as `null`,
`min_attempts=0`, `last_evaluator_role=null`, and `lock_status=active`.
Invalid values and unrelated missing fields remain hard errors.
