# Harness Decision Ledger

P18 adds a committed ledger for Athanor harness changes. The ledger prevents
the harness from accumulating unmeasured gates, prompts, and workflows by
requiring each harness change to state what it expects to improve and what was
observed.

## Location

```text
docs/harness-decisions/*.json
```

## Run

```text
python scripts/gates/harness_decision_ledger.py --json
```

## Required Decision Fields

Each decision entry must include:

- `id`
- `date`
- `status`
- `change_type`
- `summary`
- `expected_metrics`
- `verification_commands`
- `observed_results` when `status` is `observed`
- `decision`
- `rollback_or_follow_up`

Valid decision statuses:

- `planned`
- `observed`
- `follow_up`
- `rolled_back`

Valid expected metric directions:

- `increase`
- `decrease`
- `stay`
- `stay_or_increase`
- `stay_or_decrease`

## Example

```json
{
  "schema_version": 1,
  "decisions": [
    {
      "id": "p17-trace-memory-quality",
      "date": "2026-06-17",
      "status": "observed",
      "change_type": "memory",
      "summary": "Add read-only trace-memory quality gate.",
      "expected_metrics": [
        {
          "metric": "trace_memory_quality.violations",
          "direction": "stay_or_decrease",
          "target": "0 violations on committed fixture gate"
        }
      ],
      "verification_commands": [
        {
          "command": "python scripts/gates/trace_memory_quality.py --lesson-root tests/fixtures/trace_memory_quality/lessons --comparison-file tests/fixtures/trace_memory_quality/comparisons.json --today 2026-06-17 --json",
          "expected": "status pass with 0 violations"
        }
      ],
      "observed_results": [
        {
          "status": "pass",
          "summary": "Fixture gate passed with 0 violations.",
          "evidence_refs": ["tests/test_regression_trace_memory_quality.py"]
        }
      ],
      "decision": "keep",
      "rollback_or_follow_up": "Revise the evidence contract if the gate becomes noisy."
    }
  ]
}
```

The gate is read-only. It does not run the recorded commands and does not
rewrite ledger files.
