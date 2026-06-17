# P18 Harness Decision Ledger Design

Date: 2026-06-17
Branch: `feat/p18-harness-decision-ledger`
Status: design for implementation

## Goal

Make Athanor harness changes accountable. A harness change should state the
metric it expects to move, the command that proves the movement, the observed
result, and the rollback or follow-up decision.

## Current State

Athanor now has many executable harness surfaces:

- hook replay;
- hook performance budgets;
- trust install/remove;
- runtime conformance;
- observability trend snapshots;
- entropy cleanup;
- runtime execution adapter fixtures;
- workflow eval episodes;
- distribution smoke;
- trace-memory quality.

These gates make the system safer, but the repo does not yet have a
machine-readable record explaining why each harness change was added and
whether it improved the intended signal.

## Design

P18 adds a committed JSON ledger under:

```text
docs/harness-decisions/*.json
```

Each file contains one or more decision entries:

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
          "summary": "Fixture gate passed with 0 violations and 1 decay warning.",
          "evidence_refs": [
            "tests/test_regression_trace_memory_quality.py",
            "docs/trace-memory-quality.md"
          ]
        }
      ],
      "decision": "keep",
      "rollback_or_follow_up": "If the gate becomes noisy, keep it fixture-scoped in CI and revise the evidence contract before applying it to local user lessons."
    }
  ]
}
```

## Gate

`scripts/gates/harness_decision_ledger.py` is read-only. It scans the ledger
directory, validates required fields, rejects duplicate decision ids, and emits
a JSON report. The gate fails when:

1. a ledger file is malformed;
2. a decision id is duplicated;
3. a required field is missing or blank;
4. an expected metric has an invalid direction;
5. an observed decision has no observed result;
6. an observed result has no evidence refs;
7. a verification command is blank.

The gate passes empty ledgers only when `--allow-empty` is provided. CI should
use the committed ledger and require at least one decision.

## Non-Goals

- Do not parse command output automatically in P18.
- Do not require every historical gate to be backfilled.
- Do not mutate `.athanor` state.
- Do not block non-harness docs-only changes.
- Do not add a hosted dashboard.

## Why This Design

This closes the last major self-evolution gap without increasing runtime
autonomy. It is intentionally boring: the ledger is committed JSON, the gate is
deterministic, and future harness changes can be reviewed by diff.

