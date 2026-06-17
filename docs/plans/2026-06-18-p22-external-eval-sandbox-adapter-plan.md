# P22 External Eval Sandbox Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Export Athanor workflow eval episodes into an Inspect/Harbor-like external eval layout with explicit sandbox metadata and no default external execution.

**Architecture:** Reuse the existing P15 `episode.json` package as the source of truth. Add a small adapter layer that creates external-facing `manifest.json`, `tasks/workflow-evals.json`, `scorers/deterministic-workflow.json`, and `sandbox/manifest.json` files, then validates that the exported package stays local-only and executable through the existing deterministic runner.

**Tech Stack:** Python stdlib, existing `scripts/evals/workflow_episode.py`, existing workflow scenario runner, JSON schemas, pytest.

---

## File Structure

- Create `scripts/evals/external_eval_adapter.py`: pure helpers that load a packaged episode, build external manifest/task/scorer/sandbox JSON, write files, and validate local-only policy.
- Create `scripts/evals/export_external_eval_adapter.py`: CLI wrapper around the helper.
- Create `schemas/external-eval-adapter.schema.json`: schema for the adapter report and top-level external manifest.
- Create `tests/test_regression_external_eval_adapter.py`: RED/GREEN regression coverage for export shape, local-only sandbox policy, stale output cleanup, and invalid episode rejection.
- Modify `.github/workflows/validate-plugin.yml`: add named external adapter gate after the workflow episode package gate.
- Modify `tests/test_regression_v019_release_story.py`: assert CI and changelog mention P22.
- Modify `CHANGELOG.md`: document the adapter in Unreleased.
- Create `docs/external-eval-adapter.md`: operator usage and safety notes.
- Create `docs/architecture/2026-06-18-p22-external-eval-sandbox-adapter-design.md`: architecture rationale and score impact.
- Create `docs/harness-decisions/2026-06-18-p22-external-eval-sandbox-adapter.json`: decision ledger entry.

## Task 1: RED Tests

- [ ] Add `tests/test_regression_external_eval_adapter.py` with tests that call:

```text
python scripts/evals/package_workflow_episode.py --scenario-root tests/fixtures/workflow_evals --output-dir <tmp>/episode --json
python scripts/evals/export_external_eval_adapter.py --episode-root <tmp>/episode --output-dir <tmp>/external --json
```

- [ ] Assert the exporter creates:

```text
external-eval.json
tasks/workflow-evals.json
scorers/deterministic-workflow.json
sandbox/manifest.json
README.md
```

- [ ] Assert `external-eval.json` has `schema_version: 1`, `adapter: "athanor-external-eval-adapter"`, `compatibility_profiles: ["inspect-like", "harbor-like"]`, `external_execution.default_enabled: false`, and `external_execution.dependencies: []`.
- [ ] Assert `sandbox/manifest.json` has `network_access: false`, `setup_commands: []`, `external_telemetry: false`, and `filesystem.write_paths: ["stdout"]`.
- [ ] Assert invalid episode manifests that require network are rejected through the existing episode loader.
- [ ] Run the focused test and confirm it fails because `export_external_eval_adapter.py` does not exist yet.

## Task 2: Exporter Implementation

- [ ] Add `external_eval_adapter.py` with `export_adapter(episode_root: Path, output_dir: Path) -> dict`.
- [ ] Load and validate the episode with `load_episode(episode_root)`.
- [ ] Remove stale generated JSON files inside the adapter output directories before writing fresh files.
- [ ] Write deterministic JSON with sorted keys and trailing newlines.
- [ ] Keep execution metadata descriptive only: no Docker install, no Inspect/Harbor install, no network, no external telemetry, no setup commands.
- [ ] Add CLI `export_external_eval_adapter.py` with `--episode-root`, `--output-dir`, and `--json`.
- [ ] Run the focused test and confirm it passes.

## Task 3: Schema, CI, Docs, Ledger

- [ ] Add `schemas/external-eval-adapter.schema.json` covering the report and manifest fields used by tests.
- [ ] Add CI step:

```text
External eval adapter gate
python scripts/evals/export_external_eval_adapter.py --episode-root .athanor/episodes/workflow-evals --output-dir .athanor/external-evals/workflow-evals --json
```

- [ ] Update release-story tests to require the CI gate and changelog tokens.
- [ ] Update `CHANGELOG.md`, `docs/external-eval-adapter.md`, architecture note, and harness decision ledger.
- [ ] Run focused tests and direct exporter command.

## Task 4: Verification

- [ ] Run:

```text
python -m pytest tests/test_regression_external_eval_adapter.py tests/test_regression_workflow_eval_episode.py tests/test_regression_v019_release_story.py -q
python scripts/evals/package_workflow_episode.py --scenario-root tests/fixtures/workflow_evals --output-dir .athanor/episodes/workflow-evals --json
python scripts/evals/export_external_eval_adapter.py --episode-root .athanor/episodes/workflow-evals --output-dir .athanor/external-evals/workflow-evals --json
python scripts/gates/harness_decision_ledger.py --json
python -m pytest tests/ -q
git diff --check
```

- [ ] Commit once all verification is green.

## Self-Review

- Spec coverage: P22 covers external eval adapter, sandbox manifest, CI visibility, docs, and ledger.
- Placeholder scan: no TBD/TODO/fill-in-later placeholders.
- Type consistency: `episode_root`, `output_dir`, `external-eval.json`, `sandbox/manifest.json`, and `compatibility_profiles` names are consistent across tests, implementation, schema, and docs.
