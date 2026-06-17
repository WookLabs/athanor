# Workflow Trace Evals

P6 adds a local deterministic eval harness for Athanor workflow behavior. P13
adds a local live command emitter and command-skill lifecycle anchors. The trace
contract stays local-first: no external telemetry, new runtime hooks, or model
grader is required.

## Trace Records

Each workflow trace record is one JSON object. JSONL traces use the schema in
`schemas/workflow-trace.schema.json`.

Required fields:

- `schema_version`: `1`
- `trace_id`: stable run identifier
- `seq`: positive sequence number
- `phase`: workflow phase such as `work`, `plan`, `review`, or `lfg-goal`
- `event_type`: normalized event such as `workflow.started`,
  `agent.dispatched`, `verifier.result`, `gate.evaluated`,
  `escalation.required`, or `workflow.finished`
- `actor`: `leader`, `worker`, `gate`, `hook`, or `external`
- `status`: `started`, `pass`, `concern`, `failure`, `skipped`, or `escalated`
- `message`: short human-readable summary

Optional fields:

- `timestamp`: UTC event time from live command emission
- `command`: command family such as `plan`, `work`, `review`, `lfg`, or
  `lfg-goal`
- `session_id`: Athanor session id used for the default trace path
- `worker_id`: optional leader or worker identifier
- `parent_seq`: optional parent event sequence number
- `duration_ms`: optional non-negative event duration
- `references`: repo-relative paths or stable ids, such as
  `.hook-state/test-evidence.jsonl`
- `evidence`: deterministic JSON evidence fields

Use `scripts/evals/workflow_trace.py` when writing local traces in tests or
future instrumentation:

```python
from scripts.evals.workflow_trace import TraceWriter

writer = TraceWriter(".athanor/traces/demo.jsonl", trace_id="demo")
writer.append(
    phase="work",
    event_type="workflow.started",
    actor="leader",
    status="started",
    message="work started",
)
writer.append(
    phase="work",
    event_type="verifier.result",
    actor="gate",
    status="pass",
    message="pytest evidence matched",
    references=[".hook-state/test-evidence.jsonl"],
)
```

## Live Command Emission

P13 adds `scripts/evals/emit_workflow_trace.py` so live command skills can append
P6-compatible JSONL records without installing hooks or external telemetry. When
`--trace-path` is omitted, the emitter writes
`.athanor/traces/<session-id>.jsonl`.

Example:

```bash
python scripts/evals/emit_workflow_trace.py \
  --session-id "2026-06-17-001" \
  --command work \
  --phase work \
  --event-type workflow.started \
  --actor leader \
  --status started \
  --message "work execution started" \
  --json
```

Core command skills (`plan`, `work`, `review`, `lfg`, and `lfg-goal`) carry
anchors for `workflow.started`, command-specific dispatch/gate events, and
`workflow.finished`. The emitter appends one record per invocation and preserves
optional command/session metadata through `TraceWriter`.

## Scenario Fixtures

Scenario fixtures live under `tests/fixtures/workflow_evals/` and follow
`schemas/workflow-eval-scenario.schema.json`. A fixture contains one or more
scenarios, each with inline trace records and deterministic graders.

The initial committed scenarios cover:

- `work-evidence-happy-path`
- `work-missing-evidence-escalates`
- `lfg-goal-receipt-loop`

These are harness-quality evals. They score whether workflow decisions,
evidence production, stopping conditions, and escalation behavior are present in
the trace.

## Deterministic Graders

The runner supports deterministic graders only:

- `require_event`: at least one trace record matches the requested fields.
- `forbid_event`: no trace record matches the requested fields.
- `require_order`: a `before` match appears before an `after` match.
- `require_reference`: a matched event references a required artifact path.

Model-graded evals are intentionally deferred. P6 must be stable in local CI
before any subjective grader is added.

## Runner

Run the committed scenario suite with:

```bash
python scripts/evals/run_workflow_scenarios.py --scenario-root tests/fixtures/workflow_evals --json
```

The runner emits a JSON report with top-level `status`, per-scenario scores,
and per-grader pass/fail reasons. It exits `0` only when every scenario reaches
its `min_score`.

The GitHub Actions workflow runs this as the named `Workflow scenario eval gate`
before the broad pytest suite.

## Boundary

P13 gives live `/athanor:*` command skills a local trace emitter and lifecycle
anchors, but it does not claim exhaustive span coverage for every nested worker
or subprocess. External telemetry export, OpenTelemetry vocabulary mapping, and
hook-level automatic capture remain separate follow-up work.
