# P20 Maintenance Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package read-only maintenance gates into one recurring operator profile for CI and Claude `/loop` use.

**Architecture:** Add one stdlib-only gate that imports existing gate functions, emits one schema-validated report, and documents the exact `/loop` prompt. The profile does not mutate files or register a scheduler.

**Tech Stack:** Python stdlib, pytest, jsonschema, GitHub Actions YAML, JSON schema.

---

## File Structure

- Create `scripts/gates/maintenance_profile.py`: composite report builder and CLI.
- Create `schemas/maintenance-profile-report.schema.json`: report schema.
- Create `tests/test_regression_maintenance_profile.py`: behavior and CLI tests.
- Create `docs/maintenance-profile.md`: operator docs and `/loop` prompt.
- Modify `.github/workflows/validate-plugin.yml`: add named CI gate.
- Modify `tests/test_regression_v019_release_story.py`: lock CI/changelog story.
- Modify `CHANGELOG.md`: document P20.
- Add `docs/harness-decisions/2026-06-18-p20-maintenance-profile.json`: ledger entry.

## Tasks

### Task 1: RED Tests

**Files:**
- Create: `tests/test_regression_maintenance_profile.py`
- Modify: `tests/test_regression_v019_release_story.py`

- [ ] Add subprocess test for `python scripts/gates/maintenance_profile.py --skip-claude --ref-warn-days 99999 --samples 1 --json`.
- [ ] Validate output against `schemas/maintenance-profile-report.schema.json`.
- [ ] Assert report has steps for entropy cleanup, distribution smoke, observability snapshot, native runtime probe, and harness decision ledger.
- [ ] Assert `irreversible_actions == 0`.
- [ ] Assert the report includes a `/loop` prompt and a CI command.
- [ ] Add release-story assertions for CI and changelog.
- [ ] Run focused tests and confirm RED from missing script/schema/docs.

### Task 2: Gate And Schema

**Files:**
- Create: `scripts/gates/maintenance_profile.py`
- Create: `schemas/maintenance-profile-report.schema.json`

- [ ] Implement `build_report(repo_root, skip_claude, samples, plan_warn_days, ref_warn_days)`.
- [ ] Import and call existing read-only report builders.
- [ ] Map each child report to a maintenance step with `status`, `command`, and `summary`.
- [ ] Set top-level status to `fail` if any step fails, `warn` if any step warns, otherwise `pass`.
- [ ] Keep `irreversible_actions` fixed at 0.
- [ ] Implement CLI and `--strict`.
- [ ] Run focused tests and confirm GREEN.

### Task 3: Docs, CI, Ledger

**Files:**
- Create: `docs/maintenance-profile.md`
- Modify: `.github/workflows/validate-plugin.yml`
- Modify: `CHANGELOG.md`
- Add: `docs/harness-decisions/2026-06-18-p20-maintenance-profile.json`

- [ ] Document local command, CI command, `/loop` prompt, included checks, and non-goals.
- [ ] Add the CI step:
  `python scripts/gates/maintenance_profile.py --skip-claude --ref-warn-days 99999 --samples 1 --json`.
- [ ] Add changelog entry.
- [ ] Add harness decision ledger entry.
- [ ] Run direct maintenance profile and harness ledger gates.

### Task 4: Verification And Merge

**Files:**
- All P20 files.

- [ ] Run `python -m pytest tests/ -q`.
- [ ] Run `git diff --check`.
- [ ] Commit as `feat: add maintenance profile gate`.
- [ ] Fast-forward merge to main.
- [ ] Re-run full tests on main.
- [ ] Push main and delete the feature branch.

