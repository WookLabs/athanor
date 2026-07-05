# Observability Trends

P10 adds local-only observability trend tooling. It does not enable new hooks,
mutate Claude or Codex settings, start scheduled tasks, or export data to an
external service.

The tooling turns existing point-in-time gates into local history:

- workflow scenario scores from `scripts/evals/run_workflow_scenarios.py`
- hook latency ratios from `scripts/gates/check_hook_performance_budget.py`
- durable loop actions and decision statuses from
  `scripts/loops/run_lfg_loop_fixtures.py`

## Collect A Snapshot

Print one snapshot:

```bash
python scripts/observability/collect_trend_snapshot.py --json
```

Append one snapshot to local history:

```bash
python scripts/observability/collect_trend_snapshot.py --append --json
```

The default history path is `.athanor/observability/trends.jsonl`. The
`.athanor/` directory is ignored local runtime state, so snapshot history stays
on the operator machine unless it is explicitly copied into a tracked fixture.

Use `--samples 1` for a faster CI smoke gate and the default sample count for
local review.

## Report Trends

Read the default local history:

```bash
python scripts/observability/report_trends.py --json
```

Read a specific history file:

```bash
python scripts/observability/report_trends.py --history path/to/trends.jsonl --json
```

The report summarizes:

- workflow mean-score delta and latest failed scenarios;
- hook max-budget-ratio delta and latest slowest hook;
- durable loop action counts;
- durable loop failure and escalation counts.

Reports with only one snapshot are still valid, but deltas are only meaningful
after at least two snapshots.

## Promote A Trace

Promote a reviewed workflow trace JSONL into a deterministic scenario fixture:

```bash
python scripts/observability/promote_trace_scenario.py \
  --trace .athanor/traces/example.jsonl \
  --scenario-id promoted-example \
  --description "Promoted example trace" \
  --output tests/fixtures/workflow_evals/promoted-example.json
```

The promotion command validates the trace with
`scripts/evals/workflow_trace.py`, generates conservative deterministic
graders, and refuses to overwrite existing output unless `--force` is passed.
Review the generated fixture before committing it.

## Boundary

P10 is observability plumbing. It does not claim that every live slash-command
already emits complete traces. Later workflow adapter work can write richer
live traces into the same schema and feed the same trend and promotion tools.
