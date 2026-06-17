# Workflow Trace Evals

P6 adds a local deterministic eval harness for Athanor workflow behavior. It
does not instrument every live skill yet and it does not enable new runtime
hooks. It defines the trace and scenario contract that later loop work can
consume.

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

P6 does not claim that live `/athanor:*` commands emit complete traces yet. It
creates the local trace/eval contract and CI gate. P7 can then build a durable
loop controller that consumes scenario reports instead of relying on raw
optimism.
