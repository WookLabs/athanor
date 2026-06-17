# P23 Native Runtime Playbook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the P19 native runtime probe's dry-run launch plans into explicit operator-approved playbooks for worktree, dynamic workflow, and agent-team lifecycles without enabling default auto-execution.

**Architecture:** Reuse `scripts/gates/native_runtime_probe.py` as the source of truth. Add a read-only playbook builder that consumes a profile or fixture root, fails if the underlying probe fails, and emits structured recipes with preflight commands, approval text, manual command templates, evidence requirements, cleanup commands, and safety metadata.

**Tech Stack:** Python stdlib, existing native runtime probe helpers, JSON schemas, pytest.

---

## File Structure

- Create `scripts/gates/native_runtime_playbook.py`: read-only playbook builder and CLI.
- Create `schemas/native-runtime-playbook-report.schema.json`: fixture report and single-profile report schema.
- Create `tests/test_regression_native_runtime_playbook.py`: RED/GREEN coverage for recipes, schema validity, auto-launch rejection, and read-only policy.
- Modify `.github/workflows/validate-plugin.yml`: add named native runtime playbook gate after the native runtime probe gate.
- Modify `tests/test_regression_v019_release_story.py`: assert CI and changelog mention P23.
- Modify `CHANGELOG.md`: document the playbook in Unreleased.
- Create `docs/native-runtime-playbook.md`: operator usage and safety notes.
- Create `docs/architecture/2026-06-18-p23-native-runtime-playbook-design.md`: architecture rationale and score impact.
- Create `docs/harness-decisions/2026-06-18-p23-native-runtime-playbook.json`: decision ledger entry.

## Task 1: RED Tests

- [ ] Add tests that call:

```text
python scripts/gates/native_runtime_playbook.py --fixture-root tests/fixtures/native_runtime_probe --json
```

- [ ] Assert the report has `schema_version: 1`, `status: "pass"`, three fixtures, and zero irreversible actions.
- [ ] Assert recipes exist for `manual-worktree`, `dynamic-workflow`, and `agent-team`.
- [ ] Assert every native recipe has `auto_execute: false`, `operator_approval_required: true`, `mutates_files_by_default: false`, `external_telemetry: false`, and an approval phrase that includes `I approve`.
- [ ] Assert the manual worktree recipe includes `git status --short`, `git worktree list --porcelain`, `git worktree add`, `git worktree remove`, and `git worktree prune`.
- [ ] Assert a profile that sets native `auto_launch_allowed: true` fails through the playbook gate with `auto_launch_not_allowed`.
- [ ] Assert the schema and operator docs exist.
- [ ] Run the focused tests and confirm they fail because the playbook script/schema/docs do not exist yet.

## Task 2: Playbook Builder

- [ ] Add `build_playbook(raw_profile: dict) -> dict` that calls `build_probe`.
- [ ] Refuse to emit executable recipes when `probe["status"] != "pass"`.
- [ ] Emit a recipe per probe launch plan with deterministic fields:
  - `backend`
  - `surface`
  - `surface_status`
  - `dry_run_source_mode`
  - `auto_execute`
  - `operator_approval_required`
  - `mutates_files_by_default`
  - `external_telemetry`
  - `preflight_commands`
  - `approval_prompt`
  - `manual_commands`
  - `evidence_required`
  - `cleanup_commands`
- [ ] Keep command templates descriptive and never run them.
- [ ] Add `evaluate_fixture_root(fixture_root)` that builds playbooks for existing P19 fixtures.
- [ ] Add CLI `--fixture-root`, `--profile`, and `--json`.

## Task 3: Schema, CI, Docs, Ledger

- [ ] Add `schemas/native-runtime-playbook-report.schema.json`.
- [ ] Add CI step:

```text
Native runtime playbook gate
python scripts/gates/native_runtime_playbook.py --fixture-root tests/fixtures/native_runtime_probe --json
```

- [ ] Update release-story tests, changelog, operator docs, architecture note, and harness decision ledger.
- [ ] Update the current workflow/loop/harness comparison so P23 is recorded as the next score movement.

## Task 4: Verification

- [ ] Run:

```text
python -m pytest tests/test_regression_native_runtime_playbook.py tests/test_regression_native_runtime_probe.py tests/test_regression_v019_release_story.py -q
python scripts/gates/native_runtime_playbook.py --fixture-root tests/fixtures/native_runtime_probe --json
python scripts/gates/native_runtime_probe.py --fixture-root tests/fixtures/native_runtime_probe --json
python scripts/gates/harness_decision_ledger.py --json
python -m pytest tests/ -q
git diff --check
```

- [ ] Commit, merge to `main`, push, and reassess the remaining P24 reactive channel gap.

## Self-Review

- Spec coverage: P23 covers operator-approved recipes, safety metadata, CI visibility, docs, and decision ledger.
- Placeholder scan: no TBD/TODO/fill-in-later placeholders.
- Type consistency: `native_runtime_playbook`, `manual_commands`, `approval_prompt`, and `auto_execute` names are consistent across tests, implementation, schema, and docs.

