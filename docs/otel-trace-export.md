# OTel-Style Trace Export

P14 adds a local export adapter for Athanor workflow traces.

Run it against a P13 JSONL trace:

```bash
python scripts/evals/export_otel_trace.py \
  --trace-path .athanor/traces/2026-06-17-001.jsonl \
  --output .athanor/traces/2026-06-17-001.otel.json \
  --json
```

Without `--output`, the exporter prints the export envelope to stdout:

```bash
python scripts/evals/export_otel_trace.py \
  --trace-path .athanor/traces/2026-06-17-001.jsonl
```

The export is local JSON described by
`schemas/otel-trace-export.schema.json`. It is not OTLP and does not send
anything to an OpenTelemetry collector.

## Privacy Defaults

By default, raw `message`, `evidence`, and `references` values are omitted from
span attributes. The exporter records redaction markers, evidence keys, and
reference counts instead.

Opt in only when local policy allows raw trace content in the exported file:

```bash
python scripts/evals/export_otel_trace.py \
  --trace-path .athanor/traces/2026-06-17-001.jsonl \
  --include-message \
  --include-evidence \
  --include-references
```

## Mapping

The adapter maps Athanor records to GenAI-style attributes where source data is
stable and low-cardinality:

- `gen_ai.operation.name`
- `gen_ai.workflow.name`
- `gen_ai.agent.name`
- `gen_ai.conversation.id`
- `gen_ai.tool.name`
- `gen_ai.tool.type`
- `gen_ai.evaluation.name`
- `gen_ai.evaluation.score.label`

Local-only details remain under the `athanor.*` namespace, including trace id,
sequence number, phase, event type, actor, status, command, session id, worker
id, parent sequence, duration, redaction flags, evidence keys, and reference
counts.

## Boundary

This adapter has no OpenTelemetry SDK dependency, no network export, no hooks,
and no automatic command instrumentation. It converts already-captured Athanor
workflow traces into an interoperable local JSON shape for later tools.
