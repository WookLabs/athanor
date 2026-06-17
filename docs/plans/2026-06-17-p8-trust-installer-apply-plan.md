# P8 Trust-Aware Installer Apply Implementation Plan

> **For agentic workers:** Use test-first implementation. Keep every mutation
> path scoped to temporary test settings until final verification.

**Goal:** Extend the hook install dry-run planner into a trust-aware
apply/remove installer with hash review, backups, atomic writes, no-clobber
conflict handling, and shared reports.

**Architecture:** Prefer extracting reusable installer logic into
`scripts/gates/hook_installer.py`, then keep
`scripts/gates/hook_install_dry_run.py` as the CLI entry point for backward
compatibility. Default mode remains `dry-run`.

---

## Task 1: Trust Hash Model

**Files:**
- Create `schemas/hook-installer-trust.schema.json`
- Create or extend `scripts/gates/hook_installer.py`
- Add `tests/test_regression_hook_installer_trust.py`

- [x] Write failing tests for:
  - command hash calculation;
  - `${CLAUDE_PLUGIN_ROOT}` source path resolution;
  - source file sha256 calculation;
  - missing source file reported as untrusted;
  - trust state matching and mismatch detection.
- [x] Implement minimal trust model helpers:
  - `build_hook_fingerprint(entry, repo_root)`
  - `load_trust_state(path)`
  - `trust_status(entry, fingerprint, trust_state)`
- [x] Add schema and docs tokens.
- [x] Run targeted trust tests.

## Task 2: Shared Report Model

**Files:**
- Extend `scripts/gates/hook_installer.py`
- Update `scripts/gates/hook_install_dry_run.py`
- Extend `tests/test_regression_hook_install_dry_run.py`

- [x] Write failing tests that dry-run report includes:
  - `schema_version: 2`
  - `mode`
  - `trust_status`
  - `command_hash`
  - `source_hashes`
  - empty `writes`
- [x] Preserve existing dry-run behavior and CLI compatibility.
- [x] Run dry-run regression tests.

## Task 3: Apply Mode

**Files:**
- Extend installer CLI and module.
- Add `tests/test_regression_hook_installer_apply.py`

- [x] Write failing tests for:
  - trusted `would-add` hook writes settings;
  - settings parent directory creation;
  - atomic temp+replace write;
  - backup file creation when settings exists;
  - capture-only include stays blocked;
  - untrusted include stays blocked;
  - existing non-matching event hooks block apply with no write.
- [x] Implement `--mode apply`.
- [x] Run apply tests.

## Task 4: Remove Mode

**Files:**
- Extend installer CLI and module.
- Add `tests/test_regression_hook_installer_remove.py`

- [x] Write failing tests for:
  - exact Athanor hook removal;
  - unrelated same-event hooks preserved;
  - empty event arrays removed;
  - backup creation;
  - no-op remove reports `already-absent`;
  - invalid settings JSON exits without write.
- [x] Implement `--mode remove`.
- [x] Run remove tests.

## Task 5: Docs, CI Story, And Changelog

**Files:**
- Create `docs/hook-installer.md`
- Extend `docs/hook-catalog.md`
- Extend `tests/test_regression_v019_release_story.py` or create P8 story test.
- Update `CHANGELOG.md`

- [x] Docs must mention:
  - `--mode dry-run`
  - `--mode apply`
  - `--mode remove`
  - `--trust-state`
  - hash review
  - backup/rollback
  - capture-only blocked by policy
- [x] CI story must lock installer tests.
- [x] Changelog must describe the trust-aware apply/remove path.

## Task 6: Verification And Merge

- [ ] Run targeted installer tests:

```bash
python -m pytest tests/test_regression_hook_install_dry_run.py tests/test_regression_hook_installer_trust.py tests/test_regression_hook_installer_apply.py tests/test_regression_hook_installer_remove.py -q
```

- [ ] Run existing gates:

```bash
python scripts/check_release_ready.py --ci
python scripts/gates/replay_hook_fixtures.py --fixture-root tests/fixtures/hooks --json
python scripts/gates/check_hook_performance_budget.py --json
python scripts/loops/run_goal_loop_fixtures.py --fixture-root tests/fixtures/durable_loops --json
python scripts/evals/run_workflow_scenarios.py --scenario-root tests/fixtures/workflow_evals --json
python -m pytest tests/ -q
git diff --check
```

- [ ] Fast-forward merge to `main` and push when clean.

## Self-Review

- Apply path must never infer trust silently.
- Remove path must not delete arbitrary user hooks.
- Capture-only entries remain blocked unless a future branch promotes them with
  live-redacted evidence and replay support.
