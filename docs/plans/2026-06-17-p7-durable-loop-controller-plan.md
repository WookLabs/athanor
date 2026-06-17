# P7 Durable Loop Controller Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development or superpowers:executing-plans when
> available. Implement task-by-task with tests before production code.

**Goal:** Add an executable local durable loop controller for lfg-goal state,
resume routing, stop decisions, progress budgets, and P6 trace emission.

**Architecture:** Standard-library Python under `scripts/loops/`. The
controller validates `.athanor/goals/<goal_id>/state.json`, consumes a narrow
evidence summary, returns a normalized decision, atomically persists state
changes when policy requires it, and optionally appends a P6 trace record.

**Boundary:** P7 does not invoke Claude Code commands, enable hooks, or perform
autonomous merge/deploy/install actions. It provides the deterministic
controller contract that future live instrumentation can call.

---

## File Structure

- Create `schemas/durable-loop-state.schema.json`
- Create `schemas/durable-loop-evidence.schema.json`
- Create `scripts/loops/__init__.py`
- Create `scripts/loops/goal_loop_controller.py`
- Create `scripts/loops/run_goal_loop_controller.py`
- Create `scripts/loops/run_goal_loop_fixtures.py`
- Create `tests/fixtures/durable_loops/scenarios.json`
- Create `docs/durable-loop-controller.md`
- Add tests:
  - `tests/test_regression_durable_loop_state.py`
  - `tests/test_regression_durable_loop_controller.py`
  - `tests/test_regression_durable_loop_cli.py`
  - `tests/test_regression_durable_loop_docs.py`
  - extend `tests/test_regression_workflow_eval_runner.py`
  - extend `tests/test_regression_v019_release_story.py` or add a v020 story

## Task 1: State Schema, Loader, And Atomic Writer

**Files:**
- Create `schemas/durable-loop-state.schema.json`
- Create `scripts/loops/__init__.py`
- Create `scripts/loops/goal_loop_controller.py`
- Create `tests/test_regression_durable_loop_state.py`

- [ ] **Step 1: Write failing tests**

Add tests that prove:

- a valid state round-trips through `load_loop_state()` and
  `write_loop_state_atomic()`;
- malformed JSON raises `LoopStateError`;
- missing required fields raises `LoopStateError`;
- unsupported enum values raise `LoopStateError`;
- legacy state without `cycle_phase` loads only with a `legacy_missing_phase`
  warning flag;
- terminal `goal_complete` and `aborted` states load but are marked terminal.

- [ ] **Step 2: Run RED**

```bash
python -m pytest tests/test_regression_durable_loop_state.py -q
```

Expected: import failure because `scripts.loops.goal_loop_controller` does not
exist.

- [ ] **Step 3: Implement minimal state helpers**

Implement:

- `LoopStateError`
- `LoopState`
- `load_loop_state(path: Path) -> LoopState`
- `write_loop_state_atomic(path: Path, state: LoopState) -> None`
- enum validation constants
- `is_terminal_state(state: LoopState) -> bool`

Use write-temp-then-rename via `Path.replace()`. Sort keys in JSON output for
stable diffs.

- [ ] **Step 4: Add JSON Schema**

Mirror the design data model in `schemas/durable-loop-state.schema.json`.

- [ ] **Step 5: Run state tests**

```bash
python -m pytest tests/test_regression_durable_loop_state.py -q
```

Expected: pass.

## Task 2: Decision Engine

**Files:**
- Extend `scripts/loops/goal_loop_controller.py`
- Create `tests/test_regression_durable_loop_controller.py`

- [ ] **Step 1: Write failing decision tests**

Cover:

- each documented `cycle_phase` resume route;
- `cycle_n_complete` starts the next cycle;
- `scope_change_pending` resumes scope-change review;
- terminal states return `refuse_terminal_state`;
- invalid state returns or raises `abort_invalid_state`;
- `current_cycle >= max_iterations` returns `stop_max_iterations` and persists
  `aborted`;
- repeated `progress_made=false` reaches `stop_no_progress`;
- `eval_status=missing` returns `require_eval_evidence` for evidence-required
  transitions.

- [ ] **Step 2: Run RED**

```bash
python -m pytest tests/test_regression_durable_loop_controller.py -q
```

- [ ] **Step 3: Implement decision model**

Implement:

- `EvidenceSummary`
- `LoopDecision`
- `decide_next_action(state: LoopState, evidence: EvidenceSummary) -> LoopDecision`
- `apply_decision(state: LoopState, decision: LoopDecision) -> LoopState`

Keep decisions pure. Only CLI and fixture runners should write state files.

- [ ] **Step 4: Run controller tests**

```bash
python -m pytest tests/test_regression_durable_loop_controller.py -q
```

Expected: pass.

## Task 3: CLI And Trace Emission

**Files:**
- Create `schemas/durable-loop-evidence.schema.json`
- Create `scripts/loops/run_goal_loop_controller.py`
- Create `tests/test_regression_durable_loop_cli.py`

- [ ] **Step 1: Write failing CLI tests**

Use temporary state and evidence files. Assert:

- `--json` emits normalized decision JSON;
- `--trace-path` appends a valid P6 trace record with
  `event_type=loop.decision`;
- `--write-state` persists stop decisions atomically;
- invalid state exits `2`;
- stop decisions exit `1`;
- non-terminal decisions exit `0`.

- [ ] **Step 2: Run RED**

```bash
python -m pytest tests/test_regression_durable_loop_cli.py -q
```

- [ ] **Step 3: Implement CLI**

Add argument parsing for:

- `--state`
- `--evidence`
- `--trace-path`
- `--trace-id`
- `--write-state`
- `--json`

Use `scripts.evals.workflow_trace.TraceWriter` for trace output.

- [ ] **Step 4: Run CLI tests**

```bash
python -m pytest tests/test_regression_durable_loop_cli.py -q
```

Expected: pass.

## Task 4: Fixture Runner And Workflow Eval Scenario

**Files:**
- Create `scripts/loops/run_goal_loop_fixtures.py`
- Create `tests/fixtures/durable_loops/scenarios.json`
- Extend `tests/test_regression_durable_loop_cli.py`
- Extend `tests/fixtures/workflow_evals/scenarios.json`
- Extend `tests/test_regression_workflow_eval_runner.py`

- [ ] **Step 1: Write failing fixture test**

Fixture runner should evaluate committed scenarios:

- resume after `receipt_validated` routes to `run_tier1_check`;
- terminal `goal_complete` refuses re-entry;
- max iterations stops with `stop_max_iterations`;
- no progress stops with `stop_no_progress`;
- missing eval evidence escalates with `require_eval_evidence`.

- [ ] **Step 2: Implement fixture runner**

The fixture runner emits a JSON report with top-level `status`, per-scenario
decision action/status, and mismatch reasons. It exits `0` only when all
scenarios pass.

- [ ] **Step 3: Add workflow eval durable-loop scenario**

Extend P6 workflow scenarios with a trace containing:

- `workflow.started`
- `loop.decision` with `action=stop_no_progress`
- `escalation.required`
- `workflow.finished` with `status=concern`

Graders should require the loop decision before escalation and forbid a false
success finish.

- [ ] **Step 4: Run fixture and workflow eval tests**

```bash
python -m pytest tests/test_regression_durable_loop_cli.py tests/test_regression_workflow_eval_runner.py -q
python scripts/loops/run_goal_loop_fixtures.py --fixture-root tests/fixtures/durable_loops --json
python scripts/evals/run_workflow_scenarios.py --scenario-root tests/fixtures/workflow_evals --json
```

Expected: pass.

## Task 5: Docs And Release Gate Story

**Files:**
- Create `docs/durable-loop-controller.md`
- Create `tests/test_regression_durable_loop_docs.py`
- Extend `.github/workflows/validate-plugin.yml`
- Extend `tests/test_regression_v019_release_story.py` or add v020 story

- [ ] **Step 1: Write failing docs/story tests**

Docs must mention:

- `scripts/loops/run_goal_loop_controller.py`
- `scripts/loops/run_goal_loop_fixtures.py`
- `.athanor/goals/<goal_id>/state.json`
- `loop.decision`
- `stop_no_progress`
- `stop_max_iterations`
- `require_eval_evidence`
- the P7 boundary that no live Claude Code command is invoked.

Release story must mention the durable-loop fixture gate.

- [ ] **Step 2: Add docs and CI gate**

Add a CI workflow step after the workflow scenario eval gate:

```yaml
      - name: Durable loop fixture gate
        shell: bash
        run: python scripts/loops/run_goal_loop_fixtures.py --fixture-root tests/fixtures/durable_loops --json
```

- [ ] **Step 3: Run docs/story tests**

```bash
python -m pytest tests/test_regression_durable_loop_docs.py tests/test_regression_v019_release_story.py -q
```

Expected: pass.

## Task 6: Verification And Commit

- [ ] **Step 1: Run targeted P7 tests**

```bash
python -m pytest tests/test_regression_durable_loop_state.py tests/test_regression_durable_loop_controller.py tests/test_regression_durable_loop_cli.py tests/test_regression_durable_loop_docs.py tests/test_regression_workflow_eval_runner.py tests/test_regression_v019_release_story.py -q
```

- [ ] **Step 2: Run new gates directly**

```bash
python scripts/loops/run_goal_loop_fixtures.py --fixture-root tests/fixtures/durable_loops --json
python scripts/evals/run_workflow_scenarios.py --scenario-root tests/fixtures/workflow_evals --json
```

- [ ] **Step 3: Run existing gates and full suite**

```bash
python scripts/check_release_ready.py --ci
python scripts/gates/replay_hook_fixtures.py --fixture-root tests/fixtures/hooks --json
python scripts/gates/check_hook_performance_budget.py --json
python -m pytest tests/ -q
git diff --check
```

- [ ] **Step 4: Commit**

```bash
git add schemas/durable-loop-state.schema.json schemas/durable-loop-evidence.schema.json scripts/loops tests/fixtures/durable_loops docs/durable-loop-controller.md docs/architecture/2026-06-17-p7-durable-loop-controller-design.md docs/plans/2026-06-17-p7-durable-loop-controller-plan.md tests/test_regression_durable_loop_state.py tests/test_regression_durable_loop_controller.py tests/test_regression_durable_loop_cli.py tests/test_regression_durable_loop_docs.py tests/test_regression_workflow_eval_runner.py tests/test_regression_v019_release_story.py tests/fixtures/workflow_evals/scenarios.json .github/workflows/validate-plugin.yml
git commit -m "feat: add durable loop controller"
```

## Self-Review

- P7 makes the existing lfg-goal state contract executable.
- It preserves Athanor's conservative runtime boundary.
- It consumes summarized evidence instead of arbitrary model text.
- It emits P6 traces so future evals can score durable-loop behavior.
- It leaves live command instrumentation to P10.
