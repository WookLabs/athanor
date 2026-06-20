# Memory Retrieval Eval

Last reviewed: 2026-06-20.

This read-only gate measures whether the local memory index returns expected
records for query/gold-id fixtures. It complements `docs/memory-index.md` and
does not add a daemon, vector store, web viewer, external telemetry, or default
transcript ingestion.

Run the committed fixture eval:

```text
python scripts/gates/memory_retrieval_eval.py \
  --fixture-root tests/fixtures/memory_index \
  --queries tests/fixtures/memory_retrieval_eval/queries.json \
  --json
```

The query fixture contains:

- `id`: stable query id.
- `query`: text passed to `scripts/gates/memory_index.py` search logic.
- `gold_ids`: expected memory record ids.
- `top_k`: retrieval window for P@K and R@K.

The report records `precision_at_k`, `recall_at_k`, `hit`, missing gold ids,
aggregate hit rate, average precision, and average recall. Default thresholds
require all committed gold ids to be found.

## Boundary

- Read-only by default.
- No network and no external telemetry.
- No automatic context injection.
- No model-graded relevance judgment.
- Failing retrieval fixtures mean the query, gold ids, or local index behavior
  changed and must be reviewed before relying on memory recall in loop work.
