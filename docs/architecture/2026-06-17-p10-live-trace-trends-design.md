# P10 Live Trace Trends Design

Date: 2026-06-17
Branch: `feat/p10-live-trace-trends`

## Goal

Turn Athanor's existing point-in-time workflow evidence into local,
trendable observability without adding default hooks, external services, or
new autonomous runtime behavior.

P6 created the workflow trace and deterministic scenario-eval contract. P7
added a durable loop decision kernel. P8 and P9 made install trust and
cross-runtime conformance credible. P10 connects those pieces by collecting
repeatable local snapshots, reporting trends, and allowing real trace JSONL to
be promoted into regression scenario fixtures.

## Current Context

Existing local evidence streams:

- workflow trace records: `schemas/workflow-trace.schema.json`
- workflow eval scenarios: `tests/fixtures/workflow_evals/scenarios.json`
- workflow eval runner: `scripts/evals/run_workflow_scenarios.py`
- hook latency budget runner: `scripts/gates/check_hook_performance_budget.py`
- durable loop fixture runner: `scripts/loops/run_goal_loop_fixtures.py`
- hook evidence JSONL under `.athanor/sessions/*/.hook-state/`
- durable loop decisions via `scripts/loops/run_goal_loop_controller.py`

Those are strong gates, but they are mostly single-run checks. They do not
answer whether scenario scores are drifting, whether hook latency is trending
toward budget limits, whether durable loop stop reasons are clustering, or
which real traces should be promoted into regression datasets.

## Design Options

### Option A: Local Observability CLI First

Add a small standard-library observability layer that imports the existing
eval, hook-budget, and durable-loop runners, writes one normalized snapshot to
`.athanor/observability/trends.jsonl`, reports trends from that history, and
promotes selected workflow trace JSONL files into scenario fixture files.

Trade-off: it does not instrument every live slash-command yet. It does create
the missing trend history and promotion path with low runtime risk.

### Option B: Instrument Every Skill Immediately

Modify `/athanor:plan`, `/athanor:work`, `/athanor:review`, `/athanor:lfg`,
and `/athanor:lfg-goal` prompt surfaces so live runs emit trace records
directly.

Trade-off: highest coverage, but high blast radius. Most skill files are
prompt surfaces, so immediate broad instrumentation risks changing behavior
before the trend/promotion tools are proven.

### Option C: External Observability Integration

Add optional exporters for LangSmith, Braintrust, OpenAI tracing, or another
external observability system.

Trade-off: aligned with the market baseline, but too much default dependency
surface for a local Claude Code plugin. Athanor needs a reliable local ledger
first.

## Selected Approach

Use Option A.

P10 is a local observability layer. It keeps Athanor's default runtime surface
unchanged and builds on committed, deterministic gates. Later work can add
live slash-command trace emitters that write the same record format and feed
the same trend and promotion tools.

## Architecture

### Snapshot Collector

Create `scripts/observability/collect_trend_snapshot.py`.

The collector emits and optionally appends a normalized JSON object:

```json
{
  "schema_version": 1,
  "captured_at": "2026-06-17T12:00:00Z",
  "git": {
    "branch": "feat/p10-live-trace-trends",
    "sha": "abcdef0"
  },
  "workflow_eval": {
    "status": "pass",
    "scenario_count": 4,
    "min_score": 1.0,
    "mean_score": 1.0,
    "failed_scenarios": []
  },
  "hook_performance": {
    "status": "pass",
    "hook_count": 3,
    "max_budget_ratio": 0.18,
    "hooks": [
      {
        "id": "posttool-evidence-sniffer",
        "event": "PostToolUse",
        "max_ms": 64.0,
        "budget_ms": 500,
        "budget_ratio": 0.128,
        "status": "pass"
      }
    ]
  },
  "durable_loop": {
    "status": "pass",
    "scenario_count": 5,
    "actions": {
      "run_tier1_check": 1,
      "stop_no_progress": 1
    },
    "decision_statuses": {
      "pass": 1,
      "failure": 2,
      "skipped": 1,
      "escalated": 1
    }
  }
}
```

Inputs:

- workflow scenario root, default `tests/fixtures/workflow_evals`
- hook catalog, default `hooks/catalog.json`
- hook fixture root, default `tests/fixtures/hooks`
- durable loop fixture root, default `tests/fixtures/durable_loops`
- output history path, default `.athanor/observability/trends.jsonl`

Behavior:

- `--json` prints the snapshot.
- `--append` atomically creates the parent directory and appends one JSONL
  line to the history file.
- invalid underlying reports exit non-zero through the same status model used
  by existing gates.
- it does not write tracked files unless explicitly pointed at a tracked path
  in tests.

### Trend Reporter

Create `scripts/observability/report_trends.py`.

The reporter reads a JSONL history file and emits a compact trend report:

- number of snapshots
- first and latest git refs
- workflow mean-score delta
- workflow failed-scenario changes
- hook max-budget-ratio latest and delta
- slowest latest hook
- durable loop action counts
- durable loop failure/escalation counts
- top concerns when status is not `pass`

The report is JSON with a small human-readable default output. JSON is the
stable interface used by tests and future CI gates.

### Trace Promotion

Create `scripts/observability/promote_trace_scenario.py`.

The promotion command reads a real workflow trace JSONL file using
`scripts/evals/workflow_trace.load_trace`, validates the records, and writes a
single scenario fixture compatible with
`schemas/workflow-eval-scenario.schema.json`.

Required inputs:

- `--trace PATH`
- `--scenario-id ID`
- `--description TEXT`
- `--output PATH`

Default graders are deterministic and deliberately conservative:

- require the first trace phase to contain `workflow.started`
- require at least one final `workflow.finished`
- require order from `workflow.started` to `workflow.finished`
- if the trace contains an `escalation.required` event, require that event
- if the trace contains a `verifier.result` event with references, require the
  first referenced artifact basename

The command refuses an output path that already exists unless `--force` is
provided. This makes trace promotion reviewable and avoids accidental fixture
replacement.

### Documentation And Release Story

Add `docs/observability-trends.md` explaining:

- why P10 is local-only;
- how to collect a snapshot;
- how to report trends;
- how to promote a real trace into a scenario fixture;
- why `.athanor/observability/trends.jsonl` is ignored local state.

Update `CHANGELOG.md` and the release-story regression tests so this feature
does not disappear from CI/release documentation.

## Boundaries

P10 does not:

- enable new hooks;
- add SessionStart or scheduled tasks;
- export to external observability services;
- mutate Claude or Codex settings;
- claim every live skill emits complete traces;
- use model-graded evals.

P10 does:

- make existing eval, hook, and loop evidence trendable;
- create a local snapshot history format;
- report score, latency, stop-action, and escalation trends;
- provide a trace-to-scenario promotion path;
- keep all new behavior explicit CLI behavior.

## Architecture Review

Strengths:

- Low runtime risk: all behavior is explicit CLI use, no always-on runtime
  behavior.
- Uses existing sources of truth: P6/P7/P5 reports remain authoritative.
- Standard-library only: no dependency or service lock-in.
- Clear promotion path: real traces can become regression fixtures without
  inventing a second scenario format.

Risks and mitigations:

- Risk: history records become too broad. Mitigation: snapshot schema stores
  summaries, not raw hook payloads or large command output.
- Risk: trends over too few snapshots look meaningful when they are not.
  Mitigation: reports include snapshot count and deltas only when at least two
  records exist.
- Risk: promotion creates weak scenarios. Mitigation: generated graders cover
  event presence, event order, and available evidence references, and users can
  review the generated fixture before committing it.
- Risk: live slash-command instrumentation remains incomplete. Mitigation:
  document that P10 is observability plumbing and promotion; P12 can extend the
  trace schema for worker/session IDs and dynamic workflow adapters.

## Score Impact

Expected after P10:

- Eval/observability: 8.9 -> 9.6
- Harness engineering: 9.2 -> 9.6
- Workflow engineering: 9.3 -> 9.6

The remaining 9.5 program after P10 is P11 entropy cleanup and P12 dynamic
workflow/agent-team/worktree adapters.
