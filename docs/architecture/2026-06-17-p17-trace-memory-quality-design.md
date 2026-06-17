# P17 Trace-To-Memory Quality Design

Date: 2026-06-17
Branch: `feat/p17-trace-to-memory`
Status: design for implementation

## Goal

Close Athanor's trace-to-memory gap without adding a risky live memory mutator.
P17 adds a read-only gate that verifies lesson promotion, decay, and quarantine
decisions are backed by trace/eval evidence.

## Current State

Athanor already has:

- local workflow traces (`scripts/evals/workflow_trace.py`);
- deterministic workflow scenario evals
  (`scripts/evals/run_workflow_scenarios.py`);
- portable workflow eval episodes;
- memory config in `athanor.json`;
- Learner lesson files under `.athanor/lessons/`;
- Cleaner rules for age/access-count based promotion and deletion.

The weakness is that a lesson can become `permanent` or meet the access-count
promotion threshold without any machine-readable trace/eval reference proving
it improved behavior. Stale or harmful lessons also lack a gate that forces a
decay/quarantine decision.

## Non-Goals

- Do not write to `.athanor/lessons/` in P17.
- Do not implement mem-search permanent persistence.
- Do not add external telemetry or a hosted eval service.
- Do not replace Learner/Cleaner. P17 adds an executable contract around them.
- Do not make LLM-judge scoring a release gate.

## Proposed Files

- `scripts/gates/trace_memory_quality.py`
  - Read-only CLI.
  - Parses lesson markdown frontmatter.
  - Reads memory thresholds from `athanor.json`.
  - Optionally reads comparison fixtures.
  - Emits a JSON report and exits non-zero on unsafe memory invariants.

- `schemas/trace-memory-quality-report.schema.json`
  - JSON schema for the gate report.

- `tests/fixtures/trace_memory_quality/`
  - Committed lessons and comparisons covering backed promotion, stale decay,
    quarantine, and with/without lesson comparison.

- `tests/test_regression_trace_memory_quality.py`
  - RED/GREEN regression coverage for the CLI, report schema, and failing
    cases.

- `docs/trace-memory-quality.md`
  - Operator documentation.

- `.github/workflows/validate-plugin.yml`
  - Adds a named CI gate.

- `agents/learner.md`
- `skills/work/references/learner-cleaner.md`
  - Document optional `trace_refs`, `eval_refs`, and `evidence_refs` fields.

- `CHANGELOG.md`
- `tests/test_regression_v019_release_story.py`
  - Release story coverage.

## Lesson Contract

P17 supports existing lesson fields and adds optional evidence fields:

```yaml
---
type: lesson
skill: work
contract-id: trace-memory-quality
version-at-time-of-lesson: v0.18.8
confidence: high
source: session-2026-06-17
access_count: 6
date: 2026-06-17
created: 2026-06-17
importance: working
trace_refs:
  - .athanor/traces/work-2026-06-17.jsonl#workflow.finished
eval_refs:
  - tests/fixtures/workflow_evals/scenarios.json#work-happy-path
evidence_refs:
  - docs/trace-memory-quality.md#operator-contract
---
```

`trace_refs`, `eval_refs`, and `evidence_refs` may be YAML-ish lists or single
strings. The gate intentionally uses a small frontmatter parser so it stays
dependency-free in CI before `pip install` runs.

## Gate Rules

P17 reports every lesson with an action:

- `keep`: the lesson is within policy;
- `promote_candidate`: a working lesson reached promotion thresholds;
- `decay`: a stale working lesson should be deleted or left to Cleaner;
- `quarantine`: a harmful/degraded lesson is explicitly quarantined;
- `violation`: the lesson breaks a hard invariant.

Hard invariant failures:

1. Any `importance: permanent` lesson must include trace/eval/evidence refs.
2. Any working lesson with `access_count >= memory.promotionThreshold` must
   include evidence refs because it has promotion pressure.
3. Any lesson marked harmful/degraded/regressed must be quarantined with either
   `importance: quarantine` or `quarantine: true`.
4. Any comparison where injected memory scores lower than baseline fails.

Warnings/non-failing actions:

- stale working lessons below the promotion threshold are reported as `decay`;
- missing lesson roots pass with an empty report so fresh installs are not
  broken;
- malformed optional comparison files fail because comparison input is a gate
  contract.

## Comparison Contract

Optional comparison fixtures live in JSON:

```json
{
  "schema_version": 1,
  "comparisons": [
    {
      "id": "work-lesson-improves-happy-path",
      "lesson_id": "work-2026-06-17-001",
      "scenario_id": "work-happy-path",
      "baseline_score": 0.8,
      "injected_score": 1.0,
      "trace_refs": [
        "tests/fixtures/workflow_evals/scenarios.json#work-happy-path"
      ]
    }
  ]
}
```

The comparison file is intentionally simple. P17 does not run a live injected
memory experiment. It records local deterministic evidence when such evidence
exists, and it fails if the evidence says injection degraded behavior.

## CLI

```text
python scripts/gates/trace_memory_quality.py --json
python scripts/gates/trace_memory_quality.py \
  --lesson-root tests/fixtures/trace_memory_quality/lessons \
  --comparison-file tests/fixtures/trace_memory_quality/comparisons.json \
  --json
```

Defaults:

- `--lesson-root .athanor/lessons`
- `--config athanor.json`
- no comparison file unless provided
- report date defaults to today's UTC date, overrideable via `--today` for
  deterministic tests

## Why This Design

This is the smallest useful closure of the trace-to-memory loop. It makes
promotion evidence-backed, makes stale memory visible, and creates a path for
with/without lesson comparisons without changing runtime memory behavior. That
keeps the default plugin safe while raising the memory quality score above the
current 8.2/10 gap.
