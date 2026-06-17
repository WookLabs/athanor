# P19 Native Runtime Probe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only native runtime probe gate that turns P12 backend recommendations into audited capability and dry-run launch-plan evidence.

**Architecture:** Add one stdlib-only gate script, one report schema, fixture profiles, regression tests, docs, CI wiring, changelog, and a harness decision ledger entry. The gate never launches native Claude sessions or creates worktrees.

**Tech Stack:** Python stdlib, pytest, jsonschema, GitHub Actions YAML, JSON fixtures.

---

## File Structure

- Create `scripts/gates/native_runtime_probe.py`: profile validation, launch-plan generation, fixture expectation evaluation, CLI.
- Create `schemas/native-runtime-probe-report.schema.json`: fixture-mode report schema.
- Create `tests/test_regression_native_runtime_probe.py`: RED/GREEN coverage for gate behavior.
- Create `tests/fixtures/native_runtime_probe/*.json`: positive and negative capability fixtures.
- Create `docs/native-runtime-probe.md`: operator docs.
- Modify `.github/workflows/validate-plugin.yml`: add named CI gate.
- Modify `tests/test_regression_v019_release_story.py`: lock CI/changelog story.
- Modify `CHANGELOG.md`: document P19.
- Add `docs/harness-decisions/2026-06-17-p19-native-runtime-probe.json`: expected/observed harness decision.

## Tasks

### Task 1: RED Tests And Fixtures

**Files:**
- Create: `tests/test_regression_native_runtime_probe.py`
- Create: `tests/fixtures/native_runtime_probe/ci-conservative.json`
- Create: `tests/fixtures/native_runtime_probe/runtime-available-dry-run.json`
- Create: `tests/fixtures/native_runtime_probe/auto-launch-violation.json`
- Modify: `tests/test_regression_v019_release_story.py`

- [ ] Write tests that call the future script through subprocess and direct module import.
- [ ] Assert fixture-mode output validates `schemas/native-runtime-probe-report.schema.json`.
- [ ] Assert dynamic workflow and agent-team launch plans are `dry-run-only`.
- [ ] Assert auto-launch fixture is treated as an expected policy failure.
- [ ] Assert malformed profiles exit 2 with a clear message.
- [ ] Assert CI workflow and changelog mention P19.
- [ ] Run `python -m pytest tests/test_regression_native_runtime_probe.py tests/test_regression_v019_release_story.py -q`; expected RED because the script/schema/docs are missing.

### Task 2: Gate And Schema

**Files:**
- Create: `scripts/gates/native_runtime_probe.py`
- Create: `schemas/native-runtime-probe-report.schema.json`

- [ ] Implement profile validation with allowed statuses:
  `available`, `documented`, `manual`, `unavailable`, `unknown`.
- [ ] Normalize missing surfaces to `unknown`.
- [ ] Map backends to surfaces:
  `manual-worktree -> worktree`,
  `dynamic-workflow -> dynamic_workflow`,
  `agent-team -> agent_team`,
  `solo -> none`,
  `subagent-wave -> none`.
- [ ] Generate launch plans with `mode: dry-run-only`,
  `auto_launch_allowed: false`, and `operator_approval_required: true`
  for native surfaces.
- [ ] Fail any profile that sets `auto_launch_allowed: true`.
- [ ] Implement fixture expectation comparison so expected negative fixtures can
  pass the gate while still proving policy failures are detected.
- [ ] Run `python -m pytest tests/test_regression_native_runtime_probe.py -q`;
  expected GREEN.

### Task 3: Docs, CI, Ledger

**Files:**
- Create: `docs/native-runtime-probe.md`
- Modify: `.github/workflows/validate-plugin.yml`
- Modify: `CHANGELOG.md`
- Add: `docs/harness-decisions/2026-06-17-p19-native-runtime-probe.json`

- [ ] Document the CLI, surface statuses, safety rules, and non-goals.
- [ ] Add a CI step:
  `python scripts/gates/native_runtime_probe.py --fixture-root tests/fixtures/native_runtime_probe --json`.
- [ ] Add P19 to the Unreleased changelog.
- [ ] Add a harness decision with expected metrics, verification commands, observed results, and follow-up.
- [ ] Run focused tests:
  `python -m pytest tests/test_regression_native_runtime_probe.py tests/test_regression_v019_release_story.py -q`.
- [ ] Run direct gates:
  `python scripts/gates/native_runtime_probe.py --fixture-root tests/fixtures/native_runtime_probe --json`
  and `python scripts/gates/harness_decision_ledger.py --json`.

### Task 4: Final Verification And Merge

**Files:**
- All P19 files.

- [ ] Run `python -m pytest tests/ -q`.
- [ ] Run `git diff --check`.
- [ ] Commit as `feat: add native runtime probe`.
- [ ] Fast-forward merge to `main`.
- [ ] Re-run full tests on merged `main`.
- [ ] Push `main` and delete the feature branch.

