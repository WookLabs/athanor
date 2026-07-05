# LFG Loop Completion Judge Rubric

The judge decides whether the loop is ready for human ratification. It does not
mark the loop complete by itself.

Inputs:

- `loop.md`
- latest receipt
- `evidence/latest.json`
- latest assessment report when configured
- latest review report when configured
- relevant diffs, work logs, CI state, and residual artifacts

Return:

```json
{
  "completion_met": true,
  "score_target_met": true,
  "lowest_dimension_score": 92,
  "confidence": "high",
  "blocking_findings": [],
  "residuals": [],
  "evidence_refs": []
}
```

Pass conditions:

- acceptance markers are closed by receipt-backed evidence;
- receipt aggregate has no invalid rows;
- each receipt row cites R-ID and AE-ID / AE-IDs evidence identifiers;
- assessment/review gates configured by the loop are satisfied or residualized;
- no high scope drift remains unresolved;
- terminal artifact can name exact evidence paths.

Score-target satisfaction:

- `target_overall_score` is met by the latest assessment.
- `target_min_dimension_score` is met by `lowest_dimension_score`.
- `max_allowed_regression` is not exceeded by any non-waived dimension.
- Weighted-average improvement alone is a fail when any required dimension is
  still below floor.

Any unsupported claim, missing artifact, inflated assessment, or unwaived review
blocker returns `completion_met: false`. The judge cannot infer missing evidence
from assistant prose.
