# P14 OTel Trace Export Adapter Implementation Plan

> For agentic workers: REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dependency-free local OTel GenAI-style export adapter for Athanor workflow traces.

**Architecture:** Keep `scripts/evals/workflow_trace.py` as the trace source of truth. Add a separate exporter CLI that maps JSONL records into a local span envelope, validates privacy defaults, and writes either stdout or an output file.

**Tech Stack:** Python stdlib, pytest, JSON Schema documents, existing Athanor trace helpers.

---

## Files

- Create: `scripts/evals/export_otel_trace.py`
- Create: `schemas/otel-trace-export.schema.json`
- Create: `docs/otel-trace-export.md`
- Create: `tests/test_regression_otel_trace_export.py`
- Modify: `docs/workflow-trace-evals.md`
- Modify: `CHANGELOG.md`
- Modify: `tests/test_regression_v019_release_story.py`

## Task 1: RED Tests For Export Mapping And Privacy

- [ ] Add `tests/test_regression_otel_trace_export.py` with tests that create a temporary trace via `TraceWriter`, then import the planned exporter functions.
- [ ] Cover default redaction: raw `message`, `evidence`, and `references` are absent from span attributes, but redaction booleans/counts/keys exist.
- [ ] Cover OTel-style mapping: workflow events map to `invoke_workflow`, agent events to `invoke_agent`, gate/review/verifier events to `execute_tool`, and plan phase to `plan`.
- [ ] Cover deterministic ids: `span_id` is 16 lowercase hex chars and `parent_seq` resolves to `parent_span_id`.
- [ ] Cover opt-in flags: including message/evidence/references adds raw Athanor attributes.
- [ ] Cover CLI output file mode and stdout mode.
- [ ] Run:

```bash
python -m pytest tests\test_regression_otel_trace_export.py -q
```

Expected before implementation: fail because `scripts.evals.export_otel_trace` does not exist.

## Task 2: Implement Exporter Core

- [ ] Create `scripts/evals/export_otel_trace.py`.
- [ ] Import `load_trace` from `scripts.evals.workflow_trace`.
- [ ] Implement deterministic `_span_id(trace_id, seq)` with SHA-256 and 16 lowercase hex chars.
- [ ] Implement operation mapping:
  - command/phase `plan` -> `plan`;
  - `agent.dispatched` and `worker.started` -> `invoke_agent`;
  - `verifier.result`, `gate.evaluated`, and `review.result` -> `execute_tool`;
  - all workflow/loop events -> `invoke_workflow`.
- [ ] Implement status mapping:
  - `failure`, `concern`, `escalated` -> `{"code": "ERROR"}` plus `error.type: "_OTHER"`;
  - everything else -> `{"code": "OK"}`.
- [ ] Implement `export_trace(records, include_message=False, include_evidence=False, include_references=False)`.
- [ ] Run the focused test and make the mapping/privacy tests pass.

## Task 3: Implement CLI

- [ ] Add argparse for `--trace-path`, `--output`, `--include-message`, `--include-evidence`, `--include-references`, and `--json`.
- [ ] Print full export JSON to stdout when `--output` is omitted.
- [ ] Write full export JSON to `--output` when provided.
- [ ] When `--json` and `--output` are both provided, print a status report with `schema_version`, `status`, `output`, `trace_id`, and `spans`.
- [ ] Return exit code `2` without traceback for invalid traces or write errors.
- [ ] Run the focused test and make CLI tests pass.

## Task 4: Schema And Documentation

- [ ] Add `schemas/otel-trace-export.schema.json` for the local export envelope.
- [ ] Add `docs/otel-trace-export.md` with examples and the privacy boundary.
- [ ] Update `docs/workflow-trace-evals.md` to mention P14 export after P13 local trace emission.
- [ ] Update `CHANGELOG.md` with the P14 entry.
- [ ] Update `tests/test_regression_v019_release_story.py` so release story expects the P14 artifacts.
- [ ] Add schema-shape assertions in `tests/test_regression_otel_trace_export.py` without adding a new dependency.

## Task 5: Verification And Integration

- [ ] Run focused tests:

```bash
python -m pytest tests\test_regression_otel_trace_export.py tests\test_regression_workflow_trace.py tests\test_regression_live_command_trace_emitters.py -q
```

- [ ] Run workflow eval gate:

```bash
python scripts/evals/run_workflow_scenarios.py --scenario-root tests/fixtures/workflow_evals --json
```

- [ ] Run release story test:

```bash
python -m pytest tests\test_regression_v019_release_story.py -q
```

- [ ] Run full regression suite:

```bash
python -m pytest tests\ -q
```

- [ ] Run whitespace check:

```bash
git diff --check
```

## Task 6: Commit, Merge, Push

- [ ] Commit design/research/plan docs.
- [ ] Commit RED tests.
- [ ] Commit exporter/schema/docs implementation.
- [ ] After verification passes, merge feature branch to `main`.
- [ ] Push `main`.
