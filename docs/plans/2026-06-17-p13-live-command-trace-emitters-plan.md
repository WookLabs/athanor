# P13 Live Command Trace Emitters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local live command trace emitter so Athanor command skills can write P6-compatible workflow trace JSONL records during real command execution.

**Architecture:** Extend the existing P6 trace record schema with optional command/session metadata, add a stdlib-only emitter CLI, then wire `plan`, `work`, `review`, `lfg`, and `lfg-goal` skill docs to call it at lifecycle anchors. Keep the default runtime local-first and do not add hooks or external telemetry.

**Tech Stack:** Python standard library, pytest, jsonschema, existing Athanor workflow trace helpers, Claude Code skill markdown.

---

## File Structure

- Modify: `scripts/evals/workflow_trace.py`
  - Preserve optional `timestamp`, `command`, `session_id`, `worker_id`,
    `parent_seq`, and `duration_ms` fields in normalized trace records.
- Modify: `schemas/workflow-trace.schema.json`
  - Add the same optional fields while keeping `schema_version: 1`.
- Create: `scripts/evals/emit_workflow_trace.py`
  - CLI wrapper around `TraceWriter`.
  - Emits one valid record to `.athanor/traces/<session-id>.jsonl` by default.
- Create: `tests/test_regression_live_command_trace_emitters.py`
  - RED/GREEN coverage for optional metadata, CLI writes, append sequencing,
    invalid evidence JSON, and skill anchors.
- Modify: `docs/workflow-trace-evals.md`
  - Document P13 live command emission.
- Modify: `skills/plan/SKILL.md`
- Modify: `skills/work/SKILL.md`
- Modify: `skills/review/SKILL.md`
- Modify: `skills/lfg/SKILL.md`
- Modify: `skills/lfg-goal/SKILL.md`
  - Add short "P13 live trace emission" sections with exact emitter commands.
- Modify: `CHANGELOG.md`
  - Add Unreleased P13 story.
- Modify: `tests/test_regression_v019_release_story.py`
  - Assert Unreleased documents the P13 live command trace emitter.
- Modify: `docs/plans/2026-06-17-p13-live-command-trace-emitters-plan.md`
  - Check off steps as work lands.

---

## Task 1: Write Live Trace RED Tests

**Files:**
- Create: `tests/test_regression_live_command_trace_emitters.py`

- [ ] **Step 1: Add failing regression tests**

Create `tests/test_regression_live_command_trace_emitters.py` with tests for:

- `TraceWriter.append(...)` preserving P13 optional metadata.
- CLI writing one event to an explicit `--trace-path`.
- CLI appending two events with incrementing `seq`.
- CLI deriving `.athanor/traces/<session-id>.jsonl` when only `--root` and
  `--session-id` are provided.
- CLI rejecting invalid evidence JSON with exit `2` and no traceback.
- Core command skills containing `scripts/evals/emit_workflow_trace.py` and
  `workflow.started` / `workflow.finished` anchors.

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
python -m pytest tests/test_regression_live_command_trace_emitters.py -q
```

Expected:

- FAIL because `scripts/evals/emit_workflow_trace.py` does not exist and
  `workflow_trace.py` does not preserve the new optional fields.

- [ ] **Step 3: Commit RED tests**

```bash
git add tests/test_regression_live_command_trace_emitters.py
git commit -m "test: cover live command trace emitters"
```

---

## Task 2: Extend Workflow Trace Metadata

**Files:**
- Modify: `scripts/evals/workflow_trace.py`
- Modify: `schemas/workflow-trace.schema.json`

- [ ] **Step 1: Preserve optional metadata in `validate_record`**

Extend `workflow_trace.py` with helpers:

```python
OPTIONAL_STRING_FIELDS = {"command", "session_id", "timestamp", "worker_id"}


def _optional_non_empty_string(
    record: dict[str, Any],
    normalized: dict[str, Any],
    field: str,
) -> None:
    if field not in record:
        return
    normalized[field] = _non_empty_string(record.get(field), field)


def _optional_positive_int(
    record: dict[str, Any],
    normalized: dict[str, Any],
    field: str,
) -> None:
    if field not in record:
        return
    normalized[field] = _positive_int(record.get(field), field)


def _optional_non_negative_int(
    record: dict[str, Any],
    normalized: dict[str, Any],
    field: str,
) -> None:
    if field not in record:
        return
    value = record.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    normalized[field] = value
```

Then, after the existing `normalized` dict is built, preserve:

```python
    for field in sorted(OPTIONAL_STRING_FIELDS):
        _optional_non_empty_string(record, normalized, field)
    _optional_positive_int(record, normalized, "parent_seq")
    _optional_non_negative_int(record, normalized, "duration_ms")
```

- [ ] **Step 2: Extend JSON schema**

Add optional properties:

```json
"timestamp": { "type": "string", "minLength": 1 },
"command": { "type": "string", "minLength": 1 },
"session_id": { "type": "string", "minLength": 1 },
"worker_id": { "type": "string", "minLength": 1 },
"parent_seq": { "type": "integer", "minimum": 1 },
"duration_ms": { "type": "integer", "minimum": 0 }
```

Keep `additionalProperties: false` and keep all existing required fields
unchanged.

- [ ] **Step 3: Run focused trace tests**

Run:

```bash
python -m pytest tests/test_regression_live_command_trace_emitters.py tests/test_regression_workflow_trace.py -q
```

Expected:

- Metadata preservation tests still fail only because the emitter CLI is not
  implemented.
- Existing workflow trace tests continue to pass.

- [ ] **Step 4: Commit metadata extension**

```bash
git add scripts/evals/workflow_trace.py schemas/workflow-trace.schema.json
git commit -m "feat: preserve command trace metadata"
```

---

## Task 3: Implement Emitter CLI

**Files:**
- Create: `scripts/evals/emit_workflow_trace.py`

- [ ] **Step 1: Add emitter CLI**

Create `scripts/evals/emit_workflow_trace.py` with:

```python
#!/usr/bin/env python3
"""Emit one Athanor workflow trace record from live command skills."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evals.workflow_trace import TraceWriter


def _iso_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _default_trace_id(session_id: str | None) -> str:
    return f"athanor-{session_id}" if session_id else "athanor-live"


def _default_trace_path(root: Path, session_id: str | None, trace_id: str) -> Path:
    name = session_id or trace_id
    return root / ".athanor" / "traces" / f"{name}.jsonl"


def _load_evidence(raw: str | None) -> dict[str, Any]:
    if raw is None:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"evidence JSON is invalid: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("evidence JSON must be an object")
    return parsed


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Emit one Athanor workflow trace record.")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--trace-path", type=Path)
    parser.add_argument("--trace-id")
    parser.add_argument("--session-id")
    parser.add_argument("--command")
    parser.add_argument("--worker-id")
    parser.add_argument("--parent-seq", type=int)
    parser.add_argument("--duration-ms", type=int)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--event-type", required=True)
    parser.add_argument("--actor", required=True)
    parser.add_argument("--status", required=True)
    parser.add_argument("--message", required=True)
    parser.add_argument("--reference", action="append", default=[])
    parser.add_argument("--evidence-json")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def build_record_args(args: argparse.Namespace) -> tuple[Path, str, dict[str, Any]]:
    trace_id = args.trace_id or _default_trace_id(args.session_id)
    trace_path = args.trace_path or _default_trace_path(args.root, args.session_id, trace_id)
    evidence = _load_evidence(args.evidence_json)
    event: dict[str, Any] = {
        "phase": args.phase,
        "event_type": args.event_type,
        "actor": args.actor,
        "status": args.status,
        "message": args.message,
        "references": args.reference,
        "evidence": evidence,
    }
    metadata = {
        "timestamp": _iso_now(),
        "command": args.command,
        "session_id": args.session_id,
        "worker_id": args.worker_id,
        "parent_seq": args.parent_seq,
        "duration_ms": args.duration_ms,
    }
    event["metadata"] = {key: value for key, value in metadata.items() if value is not None}
    return trace_path, trace_id, event


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    try:
        trace_path, trace_id, event = build_record_args(args)
        metadata = event.pop("metadata")
        writer = TraceWriter(trace_path, trace_id=trace_id)
        record = writer.append(**event, **metadata)
    except ValueError as exc:
        print(f"emit workflow trace: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "pass",
                    "trace_path": str(trace_path),
                    "record": record,
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(
            "workflow-trace "
            f"path={trace_path} seq={record['seq']} event={record['event_type']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run emitter tests**

Run:

```bash
python -m pytest tests/test_regression_live_command_trace_emitters.py tests/test_regression_workflow_trace.py -q
```

Expected:

- CLI behavior passes.
- Skill anchor tests still fail until Task 4.

- [ ] **Step 3: Commit emitter CLI**

```bash
git add scripts/evals/emit_workflow_trace.py tests/test_regression_live_command_trace_emitters.py
git commit -m "feat: emit live command workflow traces"
```

---

## Task 4: Wire Command Skills And Docs

**Files:**
- Modify: `skills/plan/SKILL.md`
- Modify: `skills/work/SKILL.md`
- Modify: `skills/review/SKILL.md`
- Modify: `skills/lfg/SKILL.md`
- Modify: `skills/lfg-goal/SKILL.md`
- Modify: `docs/workflow-trace-evals.md`

- [ ] **Step 1: Add skill trace anchors**

Add a short `### P13 Live Trace Emission` section to each skill. Each section
must name `scripts/evals/emit_workflow_trace.py`, `workflow.started`, and
`workflow.finished`.

For example, in `skills/work/SKILL.md`:

```markdown
### P13 Live Trace Emission

After Step 0 resolves `<LATEST>`, emit `workflow.started`:

```bash
python scripts/evals/emit_workflow_trace.py \
  --session-id "<LATEST>" \
  --command work \
  --phase work \
  --event-type workflow.started \
  --actor leader \
  --status started \
  --message "work execution started" \
  --json
```

Emit `agent.dispatched` for each worker wave or solo worker, emit
`verifier.result` when evidence gates run, emit `escalation.required` for
missing evidence/blockers, and emit `workflow.finished` before the final
summary.
```
```

Use the same pattern for:

- `plan`: `plan`, `agent.dispatched`, `review.result`, `workflow.finished`
- `review`: `review`, `agent.dispatched`, `review.result`, `workflow.finished`
- `lfg`: `lfg`, `workflow.started`, `gate.evaluated`, `workflow.finished`
- `lfg-goal`: `lfg-goal`, `loop.decision`, `gate.evaluated`,
  `workflow.finished`

- [ ] **Step 2: Update docs**

Add a `Live Command Emission` section to `docs/workflow-trace-evals.md` with:

- emitter CLI example;
- default `.athanor/traces/<session-id>.jsonl` path;
- command lifecycle anchors;
- note that P13 is local-first and does not add external telemetry or hooks.

- [ ] **Step 3: Run docs/anchor tests**

Run:

```bash
python -m pytest tests/test_regression_live_command_trace_emitters.py tests/test_regression_workflow_eval_docs.py -q
```

Expected:

- PASS.

- [ ] **Step 4: Commit docs and skill anchors**

```bash
git add skills/plan/SKILL.md skills/work/SKILL.md skills/review/SKILL.md skills/lfg/SKILL.md skills/lfg-goal/SKILL.md docs/workflow-trace-evals.md tests/test_regression_live_command_trace_emitters.py
git commit -m "docs: wire live command trace anchors"
```

---

## Task 5: Release Story, Verification, Merge

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `tests/test_regression_v019_release_story.py`
- Modify: `docs/plans/2026-06-17-p13-live-command-trace-emitters-plan.md`

- [ ] **Step 1: Add release-story test**

Extend `tests/test_regression_v019_release_story.py` to assert the
Unreleased section contains:

- `Live command trace emitter`
- `scripts/evals/emit_workflow_trace.py`
- `.athanor/traces`
- `workflow.started`
- `workflow.finished`
- `local-first`

- [ ] **Step 2: Verify RED**

Run:

```bash
python -m pytest tests/test_regression_v019_release_story.py -q
```

Expected:

- FAIL until the changelog story is added.

- [ ] **Step 3: Add changelog story**

Add under `[Unreleased]`:

```markdown
- **Live command trace emitter.** Adds local-first
  `scripts/evals/emit_workflow_trace.py` and command skill anchors so
  Athanor command leaders can write `.athanor/traces` JSONL records for
  `workflow.started`, worker/evidence events, escalations, and
  `workflow.finished` without enabling new default hooks or external telemetry.
```

- [ ] **Step 4: Run focused verification**

Run:

```bash
python -m pytest tests/test_regression_live_command_trace_emitters.py tests/test_regression_workflow_trace.py tests/test_regression_workflow_eval_runner.py tests/test_regression_workflow_eval_docs.py tests/test_regression_v019_release_story.py -q
python scripts/evals/run_workflow_scenarios.py --scenario-root tests/fixtures/workflow_evals --json
git diff --check
```

Expected:

- All pytest tests pass.
- Workflow scenario eval exits `0`.
- `git diff --check` exits `0`.

- [ ] **Step 5: Run full regression suite**

Run:

```bash
python -m pytest tests\ -q
```

Expected:

- PASS with the existing skip/xpass profile.

- [ ] **Step 6: Commit release story and verification record**

```bash
git add CHANGELOG.md tests/test_regression_v019_release_story.py docs/plans/2026-06-17-p13-live-command-trace-emitters-plan.md
git commit -m "docs: record live command trace verification"
```

- [ ] **Step 7: Merge and push**

```bash
git checkout main
git pull --ff-only origin main
git merge --ff-only feat/p13-live-command-trace-emitters
python -m pytest tests\ -q
python scripts/evals/run_workflow_scenarios.py --scenario-root tests/fixtures/workflow_evals --json
git diff --check
git push origin main
git branch --delete feat/p13-live-command-trace-emitters
```

---

## Self-Review

- Spec coverage: tasks cover metadata, schema, emitter CLI, command skill
  anchors, docs, release story, verification, and merge.
- Completion-marker scan: no unresolved markers or unspecified implementation
  steps are left.
- Scope control: P13 does not add default hooks, SDK launchers, external
  telemetry, OTel export, or model-judge evals.
- Compatibility: existing P6 trace records remain valid because new fields are
  optional.
