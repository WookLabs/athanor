# Trace-Memory Quality Gate

P17 adds a read-only gate for Athanor lesson memory. It verifies that promoted
or permanent lessons have trace/eval evidence, stale working lessons are visible
as decay candidates, harmful lessons are quarantined, and optional with/without
lesson comparison fixtures do not show degraded scenario scores.

## Run

```text
python scripts/gates/trace_memory_quality.py --json
```

For committed fixtures:

```text
python scripts/gates/trace_memory_quality.py \
  --lesson-root tests/fixtures/trace_memory_quality/lessons \
  --comparison-file tests/fixtures/trace_memory_quality/comparisons.json \
  --today 2026-06-17 \
  --json
```

## Lesson Evidence Fields

The gate recognizes these optional frontmatter fields:

- `trace_refs`
- `eval_refs`
- `evidence_refs`

Permanent lessons and promotion candidates need at least one evidence ref.

## Actions

- `keep`: lesson is within policy.
- `promote_candidate`: working lesson crossed the access threshold and has evidence.
- `decay`: stale low-access working lesson should be deleted by Cleaner.
- `quarantine`: degraded memory is explicitly isolated.
- `violation`: hard invariant failure.

## Hard Failures

The gate fails when:

- `importance: permanent` lacks evidence refs;
- a working lesson has enough `access_count` for promotion and lacks evidence refs;
- a harmful/degraded/regressed lesson is not quarantined;
- injected memory comparison score is lower than baseline.

The gate does not write lesson files and does not implement mem-search
persistence.
