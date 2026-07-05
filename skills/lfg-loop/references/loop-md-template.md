# LFG Loop <loop-id>: <summary>

## Objective

<verbatim or normalized user objective>

## Mode

- type: delivery | score-target | review-blocker | ci-stabilization | mixed
- evaluator: receipt-only | assess | review | assess+review | custom

## Acceptance Markers

- [ ] L1 - <observable outcome>
  - acceptance_criterion: <MUST-style criterion>
  - Verify command: <command or no-command rationale>
  - Test-count command: <command or not applicable>
  - closed_by: <CNNN or empty>
  - evidence_refs: []

## Budgets

- max_cycles: 5
- no_progress_threshold: 2
- max_wall_minutes:
- max_token_estimate:
- min_attempts:

## Evaluation Policy

- baseline_required: true | false
- delta_required_after_valid_cycle: true | false
- assessment_skill: `/athanor:assess`
- target_overall_score:
- target_min_dimension_score:
- max_allowed_regression:
- baseline_assessment_ref:
- latest_assessment_ref:
- score_history: []
- waived_dimensions: []
- review_blocker_policy:

### `## Score target`

Optional section for score-target mode. Keep `assessment_skill` set to
`/athanor:assess`; record `target_overall_score`, `target_min_dimension_score`,
`baseline_assessment_ref`, `latest_assessment_ref`, `score_history`, and
`waived_dimensions`.

- `assessment_skill`: `/athanor:assess`
- `target_overall_score`:
- `target_min_dimension_score`:
- `baseline_assessment_ref`:
- `latest_assessment_ref`:
- `score_history`: []
- `waived_dimensions`: []

## Stop Conditions

- complete: markers closed + valid receipts + configured evaluator gates + human ratification when required
- no_progress: no progress for N consecutive decisions
- max_iterations: cycle cap reached before another delivery cycle
- blocked: environment, permission, destructive action, or human decision
- aborted: explicit user abort

## Scope Changes

| id | timestamp | summary | status | decision |
|---|---|---|---|---|

- scope_change: none | proposed | accepted | rejected | escalated
