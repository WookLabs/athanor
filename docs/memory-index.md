# Memory Index

The memory index is a local, read-only search surface for Athanor memory
artifacts. It indexes lessons, workflow traces, active goal ledgers, and
completed-goal summaries without starting a daemon or sending data outside the
repository.

Run the fixture gate:

```text
python scripts/gates/memory_index.py --fixture-root tests/fixtures/memory_index --json
```

Run against local Athanor state:

```text
python scripts/gates/memory_index.py --source .athanor --json
```

## Progressive Disclosure

The index exposes memory in three stages:

1. `search`: returns ids, titles, summaries, source paths, hashes, and token
   estimates.
2. `context`: returns a budgeted context block assembled from search summaries.
3. `detail`: returns the full content for one explicit id.

Search results intentionally omit full content. Workers must request detail by
id when a summary is not enough.

## Safety Contract

- `mutates_files_by_default` is false.
- `external_telemetry` is false.
- `irreversible_actions` is 0.
- No transcript ingestion happens by default.
- No vector database, web viewer, server, or background worker is required.
- Context blocks must obey the requested token budget.

## Indexed Sources

Supported source shapes:

- `lessons/*.md` for Learner output and reusable lessons.
- `traces/*.jsonl` for workflow trace records.
- `goals/*.md` for active goal ledgers.
- `goals-completed/*.md` for completed goal summaries.

Records carry stable ids, `kind`, `source_path`, `content_hash`, `title`,
`summary`, and `tokens_estimate`. Duplicate normalized content hashes collapse
to one record so repeated lessons do not inflate the memory surface.

## Relationship To Learner And Loops

The Learner remains the owner of lesson extraction. The memory index does not
add a registered agent. It gives `plan`, `work`, `review`, and `lfg-goal` a
small retrieval primitive that can cite prior lessons and traces without
injecting large raw history into the worker context.

`lfg-goal` should prefer memory ids and source references in handoff artifacts
instead of copying full historical content.

## Freshness

Memory search is only evidence when the report includes the source path and
content hash for the cited record. Stale or low-confidence lessons should remain
working memory until trace/eval evidence justifies promotion.
