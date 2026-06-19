# goal.md Template

Canonical `.athanor/goals/<goal_id>/goal.md` structure. Written once at bootstrap; G-markers lock at cycle 1 start. Mid-flight edits route through `scope-change-critic.md`.

## Mandatory sections

Use these exact headings in this order.

### `# Goal: <verbatim user-stated goal text>`

First H1. Copies the user-provided goal text verbatim (no paraphrase).

### `## Metadata`

- `created`: ISO 8601 UTC timestamp
- `goal_id`: 8-char sha256 prefix
- `source`: `inline` | `--goal-file` (D10 — both invocation forms supported; for `--goal-file` add a `goal_file_path` pointer line)

### `## G-markers`

`G1`, `G2`, ... each with acceptance criteria. Locked once cycle 1 starts; subsequent edits flow through scope_change.

### `## R/A/F/AE-IDs`

Optional cross-references from the ce-brainstorm pattern:
- `R-N` requirement IDs
- `A-N` assumption IDs
- `F-N` follow-up IDs
- `AE-N` acceptance example IDs (each AE pairs with a test command)

### `## Verify command`

MANDATORY. Single Bash one-liner running the full acceptance test suite. Tier 2 judges + receipt-validator use this as the goal-met oracle.

Example: `pytest tests/acceptance_goal_<goal_id>.py -v`

### `## Test-count command`

MANDATORY. Single Bash one-liner returning baseline test count for cross-cycle delta tracking.

Example: `pytest --collect-only -q | tail -1`

### `## Score target`

OPTIONAL. Include this section when the goal is to raise a multi-lens
assessment score through repeated cycles.

Required fields when present:

- `enabled`: `true`
- `assessment_skill`: `/athanor:assess`
- `target_overall_score`: integer 0-100
- `target_min_dimension_score`: integer 0-100
- `max_allowed_regression`: integer 0-100
- `baseline_assessment_ref`: path to the bootstrap assess report
- `latest_assessment_ref`: path to the latest assess report
- `score_history`: append-only cycle score list
- `waived_dimensions`: empty list unless the user explicitly accepts a
  dimension below the floor

Completion requires the latest assessment final score to meet
`target_overall_score`, every non-waived dimension to meet
`target_min_dimension_score`, and no dimension to regress by more than
`max_allowed_regression`.

### `## Cycle queue`

Upcoming cycle work items. Initially empty; leader populates after Tier 1/2 checks. Row shape: `| cycle | targets | status |`.

### `## Stop conditions`

Termination criteria (e.g., "all G-markers checked AND Verify command exits 0 AND post-cycle test count ≥ baseline"). Load-bearing for the SKILL.md loop pseudocode.

### `## scope_change`

Append-only audit table.

```
| cycle | timestamp | proposed_delta | critic_decision | reasoning |
|-------|-----------|----------------|-----------------|-----------|
```

Rows appended verbatim from `scope-change-critic.md` output `scope_change_row` field.
