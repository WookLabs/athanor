# P14 OTel Trace Export Adapter Design

Date: 2026-06-17
Branch: `feat/p14-otel-trace-export`
Status: design for implementation

## Goal

Add a dependency-free local exporter that maps Athanor workflow trace JSONL
records into an OpenTelemetry GenAI-style span envelope.

P14 is an interoperability adapter, not an external telemetry integration. It
does not send data to a collector, install the OpenTelemetry SDK, add runtime
hooks, or make trace export automatic.

## Why This Is Next

P13 gave Athanor live command trace emission anchors. The next low-risk
observability step is vocabulary alignment: the local trace records should be
exportable into a shape that downstream OTel-style tools and future adapters
can understand.

The current OpenTelemetry GenAI semantic conventions include development-stage
agent/workflow/tool/eval concepts:

- `gen_ai.operation.name`;
- `gen_ai.workflow.name`;
- `gen_ai.agent.name`;
- `gen_ai.conversation.id`;
- `gen_ai.tool.name`;
- `gen_ai.tool.type`;
- `gen_ai.evaluation.name`;
- `gen_ai.evaluation.score.label`;
- operations such as `invoke_workflow`, `invoke_agent`, `execute_tool`, and
  `plan`.

Those conventions also mark message content, tool arguments, tool results,
memory records, and system instructions as sensitive or opt-in content. Athanor
therefore needs privacy-safe defaults before any export is useful.

## Design Choices

### Approach A: Add OpenTelemetry SDK And OTLP Export

Rejected for P14. It would introduce a runtime dependency, environment
configuration, collector semantics, and privacy risk before Athanor has a
stable local export contract.

### Approach B: Rename Native Trace Fields To OTel Fields

Rejected. Athanor trace records are the local source of truth and are already
used by deterministic scenario evals. Renaming the native schema would create
churn without improving local correctness.

### Approach C: Local Export Adapter Over Existing Trace Records

Selected. Add a stdlib-only CLI that reads P13 workflow trace JSONL and writes a
local JSON export envelope. The envelope contains deterministic span ids,
parent links, OTel-style attributes where current source data supports them,
and Athanor namespaced attributes for local-only semantics.

## Architecture

Create:

- `scripts/evals/export_otel_trace.py`
- `schemas/otel-trace-export.schema.json`
- `docs/otel-trace-export.md`
- `tests/test_regression_otel_trace_export.py`

Update:

- `docs/workflow-trace-evals.md`
- `CHANGELOG.md`
- `tests/test_regression_v019_release_story.py`

The exporter must use only Python stdlib and `scripts.evals.workflow_trace`.

## Export Envelope

Top-level shape:

```json
{
  "schema_version": 1,
  "source_schema": "athanor.workflow_trace.v1",
  "exporter": "athanor-otel-trace-export",
  "otel_semconv": "gen_ai.development.local",
  "trace_id": "athanor-2026-06-17-001",
  "privacy": {
    "message_content": "redacted",
    "evidence_content": "redacted",
    "reference_content": "redacted"
  },
  "spans": []
}
```

The envelope is intentionally local JSON, not OTLP protobuf or network export.

## Span Shape

Each input record becomes one span-like object:

```json
{
  "span_id": "16 lowercase hex chars",
  "parent_span_id": "16 lowercase hex chars or omitted",
  "trace_id": "athanor-2026-06-17-001",
  "name": "invoke_workflow work",
  "kind": "INTERNAL",
  "status": {"code": "OK"},
  "start_time": "2026-06-17T13:00:00Z",
  "attributes": {}
}
```

Span ids are deterministic from `trace_id` and `seq` using SHA-256 truncated to
8 bytes. `parent_seq` maps to `parent_span_id` when the referenced sequence
exists.

## Attribute Mapping

Always include Athanor attributes:

- `athanor.trace_id`;
- `athanor.seq`;
- `athanor.phase`;
- `athanor.event_type`;
- `athanor.actor`;
- `athanor.status`;
- `athanor.message.redacted`;
- `athanor.evidence.redacted`;
- `athanor.references.redacted`;
- optional `athanor.command`;
- optional `athanor.session_id`;
- optional `athanor.worker_id`;
- optional `athanor.parent_seq`;
- optional `athanor.duration_ms`.

Add GenAI attributes when low-cardinality source data exists:

- `gen_ai.workflow.name`: command when present, otherwise phase.
- `gen_ai.conversation.id`: session id when present.
- `gen_ai.agent.name`: worker id when present, otherwise actor for
  worker/leader events.
- `gen_ai.operation.name`: mapped from event type and phase:
  - `workflow.started`, `workflow.finished`, `loop.decision` ->
    `invoke_workflow`;
  - `agent.dispatched`, `worker.started` -> `invoke_agent`;
  - `verifier.result`, `gate.evaluated`, `review.result` ->
    `execute_tool`;
  - phase `plan` or command `plan` -> `plan`;
  - otherwise `invoke_workflow`.
- `gen_ai.tool.name`: event type for tool-like gate/review/verifier events.
- `gen_ai.tool.type`: `function` for local gate/review/verifier events.
- `gen_ai.evaluation.name`: event type for `*.result` and `gate.evaluated`
  events.
- `gen_ai.evaluation.score.label`: Athanor status for evaluation events.

Use `error.type: _OTHER` and span status `ERROR` for Athanor statuses
`failure`, `concern`, or `escalated`. Use span status `OK` for `pass`,
`started`, and `skipped`.

## Privacy Defaults

Default export must not include raw `message`, `evidence`, or `references`.
Instead it records redaction markers and counts:

- `athanor.message.redacted: true`;
- `athanor.evidence.redacted: true`;
- `athanor.evidence.keys: [...]`;
- `athanor.references.redacted: true`;
- `athanor.references.count: N`.

Opt-in flags:

- `--include-message` adds `athanor.message`;
- `--include-evidence` adds `athanor.evidence`;
- `--include-references` adds `athanor.references`.

These flags only affect local output. The script still performs no network
export.

## CLI

Example:

```bash
python scripts/evals/export_otel_trace.py \
  --trace-path .athanor/traces/2026-06-17-001.jsonl \
  --output .athanor/traces/2026-06-17-001.otel.json \
  --json
```

Arguments:

- `--trace-path`: required input JSONL trace.
- `--output`: optional output path. If omitted, print export JSON to stdout.
- `--include-message`: opt in raw message text.
- `--include-evidence`: opt in raw evidence object.
- `--include-references`: opt in raw references array.
- `--json`: print a compact status report when `--output` is used.

Exit codes:

- `0`: export produced.
- `2`: invalid input, invalid trace, invalid output path, or write failure.

## Non-Goals

- No OpenTelemetry SDK dependency.
- No OTLP, HTTP, gRPC, or collector export.
- No automatic export during `/athanor:*` command execution.
- No hook expansion.
- No raw content by default.
- No trace schema v2 migration.

## Architecture Review

This design raises Athanor's OTel/interoperability score without weakening its
local-first safety posture. It keeps P13 JSONL as the source of truth, creates a
stable local export artifact, and keeps sensitive content opt-in. The main
risk is pretending the export is full OTel compliance. The mitigation is clear
naming: this is an OTel GenAI-style local export envelope, not OTLP.

## Self-Review

- Placeholder scan: no placeholders.
- Scope check: one exporter, one schema, focused docs/tests.
- Privacy check: raw message/evidence/references excluded by default.
- Runtime check: no network, hooks, SDK dependency, or settings mutation.
- Testability check: mapping, redaction, opt-in content, parent span ids, CLI,
  and schema are all testable with local fixtures.
