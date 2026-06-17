# P6 Trace Eval Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic local workflow trace schema, trace writer, scenario fixtures, and eval runner so Athanor workflow behavior can be scored in CI-style checks.

**Architecture:** Keep P6 as a local harness layer. A small trace writer appends normalized JSONL records. A scenario runner evaluates deterministic grader fixtures for required events, forbidden events, event ordering, and artifact references. No runtime hooks or user settings change.

**Tech Stack:** Python standard library, JSON Schema, pytest, existing `scripts/` and `tests/fixtures/` conventions.

---

## File Structure

- Create `schemas/workflow-trace.schema.json`
  - JSON Schema for a single trace record.
- Create `schemas/workflow-eval-scenario.schema.json`
  - JSON Schema for a scenario fixture.
- Create `scripts/evals/__init__.py`
  - Package marker.
- Create `scripts/evals/workflow_trace.py`
  - Trace record validation and JSONL writer/reader helpers.
- Create `scripts/evals/run_workflow_scenarios.py`
  - Deterministic grader runner and CLI.
- Create `tests/fixtures/workflow_evals/scenarios.json`
  - Three initial scenarios: work happy path, work escalation, lfg-goal receipt loop.
- Create `docs/workflow-trace-evals.md`
  - Operator and contributor documentation.
- Add tests:
  - `tests/test_regression_workflow_trace.py`
  - `tests/test_regression_workflow_eval_runner.py`
  - `tests/test_regression_workflow_eval_docs.py`
  - Extend `tests/test_regression_v019_release_story.py` or add a v020 story test if a CI gate is added.

## Task 1: Trace Schema And Writer

**Files:**
- Create: `schemas/workflow-trace.schema.json`
- Create: `scripts/evals/__init__.py`
- Create: `scripts/evals/workflow_trace.py`
- Create: `tests/test_regression_workflow_trace.py`

- [ ] **Step 1: Write failing tests**

Add tests that prove:

```python
from pathlib import Path

from scripts.evals.workflow_trace import TraceWriter, load_trace


def test_trace_writer_appends_schema_v1_records(tmp_path: Path) -> None:
    path = tmp_path / "trace.jsonl"
    writer = TraceWriter(path, trace_id="trace-demo")

    first = writer.append(
        phase="work",
        event_type="workflow.started",
        actor="leader",
        status="started",
        message="work started",
    )
    second = writer.append(
        phase="work",
        event_type="verifier.result",
        actor="gate",
        status="pass",
        message="pytest evidence matched",
        references=[".athanor/sessions/2026-06-17-001/.hook-state/test-evidence.jsonl"],
        evidence={"command": "python -m pytest tests/test_demo.py -q"},
    )

    records = load_trace(path)
    assert first["seq"] == 1
    assert second["seq"] == 2
    assert records[0]["schema_version"] == 1
    assert records[1]["event_type"] == "verifier.result"
    assert records[1]["references"][0].endswith("test-evidence.jsonl")
```

Add a second test:

```python
import pytest


def test_trace_writer_rejects_unknown_status(tmp_path: Path) -> None:
    writer = TraceWriter(tmp_path / "trace.jsonl", trace_id="trace-demo")
    with pytest.raises(ValueError, match="unsupported status"):
        writer.append(
            phase="work",
            event_type="workflow.finished",
            actor="leader",
            status="done",
            message="bad status",
        )
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
python -m pytest tests/test_regression_workflow_trace.py -q
```

Expected: import fails because `scripts.evals.workflow_trace` does not exist.

- [ ] **Step 3: Implement minimal trace writer**

Create `workflow_trace.py` with:

- constants for allowed actors and statuses;
- `validate_record(record: dict) -> dict`;
- `TraceWriter(path: Path, trace_id: str)`;
- `TraceWriter.append(...) -> dict`;
- `load_trace(path: Path) -> list[dict]`.

- [ ] **Step 4: Add JSON Schema**

Create `schemas/workflow-trace.schema.json` with required fields:

```json
["schema_version", "trace_id", "seq", "phase", "event_type", "actor", "status", "message"]
```

Keep `references` as an array of strings and `evidence` as an object.

- [ ] **Step 5: Run trace tests**

Run:

```bash
python -m pytest tests/test_regression_workflow_trace.py -q
```

Expected: pass.

## Task 2: Scenario Runner Red Tests

**Files:**
- Create: `tests/test_regression_workflow_eval_runner.py`
- Later create: `scripts/evals/run_workflow_scenarios.py`
- Later create: `schemas/workflow-eval-scenario.schema.json`

- [ ] **Step 1: Write failing runner tests**

Tests should create a temporary scenario file with inline trace records and
graders:

```python
def test_eval_runner_scores_required_event_and_order(tmp_path: Path) -> None:
    scenario_root = tmp_path / "scenarios"
    scenario_root.mkdir()
    _write_json(
        scenario_root / "work.json",
        {
            "schema_version": 1,
            "scenarios": [
                {
                    "id": "work-happy",
                    "description": "work emits evidence before finish",
                    "min_score": 1.0,
                    "trace": [
                        {
                            "schema_version": 1,
                            "trace_id": "trace-work",
                            "seq": 1,
                            "phase": "work",
                            "event_type": "workflow.started",
                            "actor": "leader",
                            "status": "started",
                            "message": "start",
                        },
                        {
                            "schema_version": 1,
                            "trace_id": "trace-work",
                            "seq": 2,
                            "phase": "work",
                            "event_type": "verifier.result",
                            "actor": "gate",
                            "status": "pass",
                            "message": "evidence matched",
                            "references": [".hook-state/test-evidence.jsonl"],
                        },
                        {
                            "schema_version": 1,
                            "trace_id": "trace-work",
                            "seq": 3,
                            "phase": "work",
                            "event_type": "workflow.finished",
                            "actor": "leader",
                            "status": "pass",
                            "message": "finish",
                        },
                    ],
                    "graders": [
                        {
                            "id": "requires-verifier-pass",
                            "kind": "require_event",
                            "match": {"event_type": "verifier.result", "status": "pass"},
                        },
                        {
                            "id": "evidence-before-finish",
                            "kind": "require_order",
                            "before": {"event_type": "verifier.result"},
                            "after": {"event_type": "workflow.finished"},
                        },
                        {
                            "id": "references-test-evidence",
                            "kind": "require_reference",
                            "match": {"event_type": "verifier.result"},
                            "reference": "test-evidence.jsonl",
                        },
                    ],
                }
            ],
        },
    )

    proc = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "evals" / "run_workflow_scenarios.py"),
            "--scenario-root",
            str(scenario_root),
            "--json",
        ],
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["status"] == "pass"
    assert report["scenarios"][0]["score"] == 1.0
```

Add a failure test where `workflow.finished` has status `pass` but the required
`escalation.required` event is missing. Expected CLI exit code is `1`.

- [ ] **Step 2: Run RED**

Run:

```bash
python -m pytest tests/test_regression_workflow_eval_runner.py -q
```

Expected: fail because runner does not exist.

## Task 3: Implement Scenario Runner

**Files:**
- Create: `scripts/evals/run_workflow_scenarios.py`
- Create: `schemas/workflow-eval-scenario.schema.json`

- [ ] **Step 1: Implement grader functions**

Implement:

- `_record_matches(record, match)`
- `_require_event(trace, grader)`
- `_forbid_event(trace, grader)`
- `_require_order(trace, grader)`
- `_require_reference(trace, grader)`
- `evaluate_scenario(scenario)`
- `evaluate_root(scenario_root)`

Each grader returns:

```python
{"id": "...", "kind": "...", "status": "pass" | "fail", "reason": "..."}
```

- [ ] **Step 2: Implement CLI**

CLI:

```bash
python scripts/evals/run_workflow_scenarios.py --scenario-root tests/fixtures/workflow_evals --json
```

Exit `0` when all scenarios pass, else `1`.

- [ ] **Step 3: Run runner tests**

Run:

```bash
python -m pytest tests/test_regression_workflow_eval_runner.py -q
```

Expected: pass.

## Task 4: Committed Scenario Fixtures

**Files:**
- Create: `tests/fixtures/workflow_evals/scenarios.json`
- Extend: `tests/test_regression_workflow_eval_runner.py`

- [ ] **Step 1: Add fixture regression test**

Add:

```python
def test_committed_workflow_eval_scenarios_pass() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "evals" / "run_workflow_scenarios.py"),
            "--scenario-root",
            str(REPO_ROOT / "tests" / "fixtures" / "workflow_evals"),
            "--json",
        ],
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )
    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert {item["id"] for item in report["scenarios"]} == {
        "work-evidence-happy-path",
        "work-missing-evidence-escalates",
        "lfg-goal-receipt-loop",
    }
```

- [ ] **Step 2: Run RED**

Run:

```bash
python -m pytest tests/test_regression_workflow_eval_runner.py::test_committed_workflow_eval_scenarios_pass -q
```

Expected: fail because committed scenarios do not exist.

- [ ] **Step 3: Create scenarios**

Create `tests/fixtures/workflow_evals/scenarios.json` with the three scenarios
defined in the design document.

- [ ] **Step 4: Run fixture test**

Run:

```bash
python -m pytest tests/test_regression_workflow_eval_runner.py -q
```

Expected: pass.

## Task 5: Docs And CI Story

**Files:**
- Create: `docs/workflow-trace-evals.md`
- Create: `tests/test_regression_workflow_eval_docs.py`
- Modify: `.github/workflows/validate-plugin.yml`
- Extend: `tests/test_regression_v019_release_story.py` or create `tests/test_regression_v020_trace_eval_story.py`

- [ ] **Step 1: Add docs tests**

Assert docs mention:

- `scripts/evals/run_workflow_scenarios.py`
- `schemas/workflow-trace.schema.json`
- `workflow.started`
- `verifier.result`
- `escalation.required`
- deterministic graders

- [ ] **Step 2: Add CI story test**

Assert workflow contains:

- `Workflow scenario eval gate`
- `python scripts/evals/run_workflow_scenarios.py`
- `--scenario-root tests/fixtures/workflow_evals --json`

- [ ] **Step 3: Run RED**

Run:

```bash
python -m pytest tests/test_regression_workflow_eval_docs.py tests/test_regression_v019_release_story.py -q
```

Expected: fail until docs and CI are updated.

- [ ] **Step 4: Update docs and workflow**

Add the workflow step after hook performance budget gate:

```yaml
      - name: Workflow scenario eval gate
        shell: bash
        run: python scripts/evals/run_workflow_scenarios.py --scenario-root tests/fixtures/workflow_evals --json
```

- [ ] **Step 5: Run docs/story tests**

Run:

```bash
python -m pytest tests/test_regression_workflow_eval_docs.py tests/test_regression_v019_release_story.py -q
```

Expected: pass.

## Task 6: Verification And Commit

**Files:**
- All P6 files.

- [ ] **Step 1: Run targeted P6 tests**

Run:

```bash
python -m pytest tests/test_regression_workflow_trace.py tests/test_regression_workflow_eval_runner.py tests/test_regression_workflow_eval_docs.py tests/test_regression_v019_release_story.py -q
```

- [ ] **Step 2: Run eval gate directly**

Run:

```bash
python scripts/evals/run_workflow_scenarios.py --scenario-root tests/fixtures/workflow_evals --json
```

- [ ] **Step 3: Run existing gates and full suite**

Run:

```bash
python scripts/check_release_ready.py --ci
python scripts/gates/replay_hook_fixtures.py --fixture-root tests/fixtures/hooks --json
python scripts/gates/check_hook_performance_budget.py --json
python -m pytest tests/ -q
git diff --check
```

- [ ] **Step 4: Commit**

Run:

```bash
git add schemas/workflow-trace.schema.json schemas/workflow-eval-scenario.schema.json scripts/evals tests/fixtures/workflow_evals docs/workflow-trace-evals.md docs/architecture/2026-06-17-p6-trace-eval-harness-design.md docs/plans/2026-06-17-p6-trace-eval-harness-plan.md tests/test_regression_workflow_trace.py tests/test_regression_workflow_eval_runner.py tests/test_regression_workflow_eval_docs.py tests/test_regression_v019_release_story.py .github/workflows/validate-plugin.yml
git commit -m "feat: add workflow trace eval harness"
```

## Self-Review

- Spec coverage: trace schema, writer, scenario runner, fixtures, docs, and CI
  story are covered.
- Boundary: P6 does not claim live skill instrumentation; it creates the local
  deterministic harness required before P7.
- TDD: every production file has a failing test before implementation.
- Risk: scenario graders are intentionally simple. This keeps P6 deterministic;
  richer model-graded evals remain a later extension.
