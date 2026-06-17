# Package-Facing Knowledge Index Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a short package-facing knowledge index and a CI gate that keeps it current, runtime-focused, and free of development-history dependencies.

**Architecture:** The index lives at `docs/package-knowledge-index.md` and links only to current runtime/operator docs plus root entry points. The gate at `scripts/gates/package_knowledge_index.py` validates the index shape, freshness, link targets, forbidden history links, and entry-point back-links from `README.md` and `CLAUDE.md`.

**Tech Stack:** Python standard library, JSON Schema, pytest, existing GitHub Actions validation workflow.

---

### Task 1: Add RED tests for the knowledge index contract

**Files:**
- Create: `tests/test_regression_package_knowledge_index.py`
- Modify: `tests/test_regression_v019_release_story.py`

- [ ] **Step 1: Write failing gate tests**

Add tests that expect `scripts/gates/package_knowledge_index.py`, `schemas/package-knowledge-index-report.schema.json`, and `docs/package-knowledge-index.md` to exist. The tests should validate JSON schema output, required current docs/gates, zero irreversible actions, no external telemetry, forbidden history-link failures, and README/CLAUDE back-links.

- [ ] **Step 2: Run tests to verify RED**

Run:

```text
python -m pytest tests/test_regression_package_knowledge_index.py tests/test_regression_v019_release_story.py::test_ci_runs_package_knowledge_index_gate tests/test_regression_v019_release_story.py::test_unreleased_documents_package_knowledge_index -q
```

Expected: FAIL because the script, schema, docs, CI step, and changelog entry do not exist yet.

### Task 2: Implement the read-only knowledge index gate

**Files:**
- Create: `scripts/gates/package_knowledge_index.py`
- Create: `schemas/package-knowledge-index-report.schema.json`

- [ ] **Step 1: Implement report builder**

Build a report containing `schema_version`, `status`, `generated_at`, `profile`, `summary`, `entry_points`, `required_refs`, `links`, `forbidden_refs`, and `checks`.

- [ ] **Step 2: Enforce the runtime-facing contract**

The gate must pass only when:

- `docs/package-knowledge-index.md` exists;
- the index is short enough for package-facing use;
- it contains required sections: Runtime Surface, Operator Gate Map, Safety Contracts, Ship Profile Boundary, Freshness;
- it links current docs and gate scripts for distribution smoke, package footprint, maintenance profile, harness decisions, native runtime probe, native runtime playbook, and reactive channel fixtures;
- it does not link `docs/plans/**`, `docs/archive/**`, `docs/architecture/**`, `tests/**`, `ref/**`, `.github/**`, or `.athanor/**`;
- `README.md` and `CLAUDE.md` link back to the index;
- all local links resolve inside the repository;
- `irreversible_actions` is 0 and external telemetry is false.

- [ ] **Step 3: Verify GREEN for the focused gate tests**

Run the focused pytest command from Task 1 and the direct CLI:

```text
python scripts/gates/package_knowledge_index.py --json
```

Expected: focused tests pass and direct CLI returns exit code 0.

### Task 3: Add operator-facing index and release wiring

**Files:**
- Create: `docs/package-knowledge-index.md`
- Modify: `README.md`
- Modify: `CLAUDE.md`
- Modify: `.github/workflows/validate-plugin.yml`
- Modify: `CHANGELOG.md`
- Create: `docs/harness-decisions/2026-06-18-p25-package-knowledge-index.json`

- [ ] **Step 1: Write short package-facing index**

Keep the index concise. Link only current runtime/operator docs and scripts. Explain that development history remains repo-local and that the index is the starting point for packaged workers.

- [ ] **Step 2: Add runtime entry-point back-links**

Add one short link in `README.md` and one short link in `CLAUDE.md` to `docs/package-knowledge-index.md`.

- [ ] **Step 3: Add CI and changelog coverage**

Add `Package knowledge index gate` to `.github/workflows/validate-plugin.yml` and document P25 in `CHANGELOG.md`.

- [ ] **Step 4: Add harness decision ledger entry**

Add a read-only P25 decision JSON with `change_type: knowledge_surface`.

### Task 4: Update scorecard and verify all gates

**Files:**
- Modify: `docs/architecture/2026-06-18-current-workflow-loop-harness-research-comparison.md`

- [ ] **Step 1: Raise knowledge score after evidence**

After focused verification passes, update Knowledge surface freshness from `9.25` to `9.55` and record the P25 evidence.

- [ ] **Step 2: Run final verification**

Run:

```text
python scripts/gates/package_knowledge_index.py --json
python scripts/gates/package_footprint_policy.py --json
python scripts/gates/maintenance_profile.py --skip-claude --ref-warn-days 99999 --samples 1 --json
python scripts/gates/harness_decision_ledger.py --json
python -m pytest tests/ -q
git diff --check
```

Expected: direct P25 gate passes, footprint/maintenance remain warning-only with zero failures, ledger passes with 9 decisions, all tests pass, and `git diff --check` has no whitespace errors beyond line-ending warnings.
