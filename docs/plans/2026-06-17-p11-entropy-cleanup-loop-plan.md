# P11 Entropy Cleanup Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a read-only entropy cleanup report gate that surfaces stale plans, aging capture-only hook candidates, reference freshness, and mirror/conformance drift as structured JSON.

**Architecture:** Add `scripts/gates/entropy_cleanup.py` as a stdlib-only gate that composes existing runtime conformance logic instead of duplicating it. Add a report schema, candidate lifecycle metadata in `hooks/catalog.json`, focused regression tests, operator docs, CI smoke coverage, and an Unreleased changelog story.

**Tech Stack:** Python stdlib, pytest, jsonschema, existing Athanor gate/report conventions.

---

## File Structure

- Create: `scripts/gates/entropy_cleanup.py`
  - Builds a read-only report.
  - Scans plan files, hook candidate metadata, local ref repositories, and runtime conformance status.
  - Exposes `build_report(...)` for tests and `main(...)` for CLI.
- Create: `schemas/entropy-cleanup-report.schema.json`
  - Defines report status, summaries, checks, actions, and categories.
- Create: `tests/test_regression_entropy_cleanup.py`
  - TDD coverage for current repo pass/warn behavior, schema validation, candidate metadata failures, stale plan warnings, and conformance failure propagation.
- Modify: `hooks/catalog.json`
  - Add `candidate_since` and `review_after_days` to `capture-only` hook candidates.
- Modify: `schemas/hook-catalog.schema.json`
  - Permit and constrain candidate lifecycle metadata.
- Create: `docs/entropy-cleanup.md`
  - Document CLI, output semantics, strict mode, and non-goals.
- Modify: `.github/workflows/validate-plugin.yml`
  - Add named CI step: `Entropy cleanup report gate`.
- Modify: `CHANGELOG.md`
  - Add Unreleased P11 bullet.
- Modify: `tests/test_regression_v019_release_story.py`
  - Assert CI and changelog story name the P11 gate.
- Modify: `docs/plans/2026-06-17-p11-entropy-cleanup-loop-plan.md`
  - Check off implementation steps as work lands.

---

## Task 1: Write Entropy Cleanup Regression Tests

**Files:**
- Create: `tests/test_regression_entropy_cleanup.py`

- [x] **Step 1: Add failing tests for the P11 report gate**

Create `tests/test_regression_entropy_cleanup.py` with:

```python
"""Regression tests for the P11 entropy cleanup report gate."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "gates" / "entropy_cleanup.py"
SCHEMA = REPO_ROOT / "schemas" / "entropy-cleanup-report.schema.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_cli(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(repo_root), "--json", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _copy_minimal_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    for source in (
        "docs/runtime-surface-contract.json",
        "hooks/catalog.json",
        "hooks/hooks.json",
        ".claude-plugin/plugin.json",
        "plugins/athanor-codex/.codex-plugin/plugin.json",
        "scripts/gates/runtime_conformance.py",
    ):
        src = REPO_ROOT / source
        dest = repo / source
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    for skill_dir in (REPO_ROOT / "skills").iterdir():
        if skill_dir.is_dir() and not skill_dir.name.startswith("."):
            (repo / "skills" / skill_dir.name).mkdir(parents=True)

    codex_skills = REPO_ROOT / "plugins" / "athanor-codex" / "skills"
    for skill_dir in codex_skills.iterdir():
        if skill_dir.is_dir() and not skill_dir.name.startswith("."):
            (repo / "plugins" / "athanor-codex" / "skills" / skill_dir.name).mkdir(
                parents=True
            )

    return repo


def _check_by_id(report: dict, check_id: str) -> dict:
    for check in report["checks"]:
        if check["id"] == check_id:
            return check
    raise AssertionError(f"missing check id: {check_id}")


def _action_ids(report: dict) -> set[str]:
    return {str(action["id"]) for action in report["actions"]}


def test_entropy_cleanup_cli_emits_schema_valid_report_for_current_repo() -> None:
    proc = _run_cli(REPO_ROOT, "--ref-warn-days", "99999")

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    jsonschema.validate(report, _load_json(SCHEMA))
    assert report["schema_version"] == 1
    assert report["status"] in {"pass", "warn"}
    assert report["summary"]["errors"] == 0
    for category in ("plans", "hook_candidates", "refs", "mirrors"):
        assert category in report["categories"]
    assert "mirrors.runtime_conformance" in {check["id"] for check in report["checks"]}


def test_capture_only_candidate_missing_lifecycle_metadata_fails(tmp_path: Path) -> None:
    repo = _copy_minimal_repo(tmp_path)
    catalog_path = repo / "hooks" / "catalog.json"
    catalog = _load_json(catalog_path)
    for entry in catalog["hooks"]:
        if entry["runtime_default"] == "capture-only":
            entry.pop("candidate_since", None)
            entry.pop("review_after_days", None)
            break
    catalog_path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")

    proc = _run_cli(repo)

    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert report["status"] == "fail"
    check = _check_by_id(report, "hook_candidates.lifecycle_metadata")
    assert check["status"] == "fail"
    assert check["details"]["missing"][0]["field"] == "candidate_since"


def test_old_capture_only_candidate_emits_warning_action(tmp_path: Path) -> None:
    repo = _copy_minimal_repo(tmp_path)
    catalog_path = repo / "hooks" / "catalog.json"
    catalog = _load_json(catalog_path)
    for entry in catalog["hooks"]:
        if entry["runtime_default"] == "capture-only":
            entry["candidate_since"] = "2026-01-01"
            entry["review_after_days"] = 1
    catalog_path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")

    proc = _run_cli(repo)

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["status"] == "warn"
    assert "review-hook-candidates" in _action_ids(report)


def test_old_plan_with_unchecked_steps_emits_warning_action(tmp_path: Path) -> None:
    repo = _copy_minimal_repo(tmp_path)
    plan_dir = repo / "docs" / "plans"
    plan_dir.mkdir(parents=True)
    (plan_dir / "2026-01-01-old-plan.md").write_text(
        "# Old Plan\n\n- [ ] **Step 1: Finish the work**\n",
        encoding="utf-8",
    )

    proc = _run_cli(repo, "--plan-warn-days", "1")

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["status"] == "warn"
    assert "review-open-plans" in _action_ids(report)


def test_runtime_conformance_failure_is_reported_as_mirror_failure(tmp_path: Path) -> None:
    repo = _copy_minimal_repo(tmp_path)
    shutil.rmtree(repo / "plugins" / "athanor-codex" / "skills" / "athanor-review")

    proc = _run_cli(repo)

    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert report["status"] == "fail"
    check = _check_by_id(report, "mirrors.runtime_conformance")
    assert check["status"] == "fail"
    assert "codex.skills" in check["details"]["failed_checks"]
```

- [x] **Step 2: Run tests to verify RED**

Run:

```bash
python -m pytest tests/test_regression_entropy_cleanup.py -q
```

Expected:

- FAIL because `scripts/gates/entropy_cleanup.py` and `schemas/entropy-cleanup-report.schema.json` do not exist.

- [x] **Step 3: Commit RED tests**

```bash
git add tests/test_regression_entropy_cleanup.py
git commit -m "test: cover entropy cleanup report gate"
```

---

## Task 2: Implement Entropy Cleanup Report Gate

**Files:**
- Create: `schemas/entropy-cleanup-report.schema.json`
- Create: `scripts/gates/entropy_cleanup.py`
- Modify: `schemas/hook-catalog.schema.json`
- Modify: `hooks/catalog.json`
- Modify: `tests/test_regression_hook_catalog.py`

- [x] **Step 1: Add report schema**

Create `schemas/entropy-cleanup-report.schema.json` with:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://wooklabs.github.io/athanor/schemas/entropy-cleanup-report.schema.json",
  "title": "Athanor Entropy Cleanup Report",
  "type": "object",
  "required": ["schema_version", "status", "summary", "generated_at", "categories", "checks", "actions"],
  "properties": {
    "schema_version": { "const": 1 },
    "status": { "enum": ["pass", "warn", "fail"] },
    "generated_at": { "type": "string" },
    "summary": {
      "type": "object",
      "required": ["checks", "warnings", "errors", "actions"],
      "properties": {
        "checks": { "type": "integer", "minimum": 0 },
        "warnings": { "type": "integer", "minimum": 0 },
        "errors": { "type": "integer", "minimum": 0 },
        "actions": { "type": "integer", "minimum": 0 }
      },
      "additionalProperties": true
    },
    "categories": {
      "type": "object",
      "required": ["plans", "hook_candidates", "refs", "mirrors"],
      "additionalProperties": true
    },
    "checks": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "category", "status", "message"],
        "properties": {
          "id": { "type": "string" },
          "category": { "enum": ["plans", "hook_candidates", "refs", "mirrors"] },
          "status": { "enum": ["pass", "warn", "fail"] },
          "message": { "type": "string" }
        },
        "additionalProperties": true
      }
    },
    "actions": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "severity", "category", "target", "recommendation"],
        "properties": {
          "id": { "type": "string" },
          "severity": { "enum": ["info", "warn", "fail"] },
          "category": { "enum": ["plans", "hook_candidates", "refs", "mirrors"] },
          "target": { "type": "string" },
          "recommendation": { "type": "string" }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true
}
```

- [x] **Step 2: Extend hook catalog schema for candidate lifecycle metadata**

Modify `schemas/hook-catalog.schema.json` so hook entries allow:

```json
"candidate_since": {
  "type": "string",
  "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
},
"review_after_days": {
  "type": "integer",
  "minimum": 0
}
```

Keep these fields optional at schema level because only `capture-only` entries
need them, and the entropy gate enforces that conditional policy.

- [x] **Step 3: Add candidate lifecycle metadata to capture-only hook entries**

In `hooks/catalog.json`, add to every entry where `"runtime_default": "capture-only"`:

```json
"candidate_since": "2026-06-16",
"review_after_days": 30
```

Use the same date for all current candidates because they were introduced by
the current ref/deep-research hook expansion pass.

- [x] **Step 4: Extend hook catalog regression coverage**

Add this test to `tests/test_regression_hook_catalog.py`:

```python
def test_capture_only_hooks_carry_candidate_lifecycle_metadata():
    for entry in _catalog_entries():
        if entry["runtime_default"] != "capture-only":
            continue
        assert entry["candidate_since"].count("-") == 2
        assert isinstance(entry["review_after_days"], int)
        assert entry["review_after_days"] >= 0
```

- [x] **Step 5: Implement `scripts/gates/entropy_cleanup.py`**

Implement these public functions:

```python
def build_report(
    *,
    repo_root: Path,
    generated_at: str | None = None,
    plan_warn_days: int = 30,
    ref_warn_days: int = 45,
) -> dict[str, Any]:
    ...


def main(argv: list[str] | None = None) -> int:
    ...
```

Implementation requirements:

- `--repo-root` defaults to repository root.
- `--plan-warn-days` defaults to `30`.
- `--ref-warn-days` defaults to `45`.
- `--strict` converts warnings to exit `1`.
- `--json` prints formatted JSON.
- Non-json mode prints a one-line summary.
- Use `scripts.gates.runtime_conformance.build_report` for mirror checks.
- Catch runtime conformance input errors and report a mirror failure or input
  error as appropriate.
- Do not mutate files.
- Do not fetch network refs.

Use helper structure like:

```python
def _add_check(checks: list[dict[str, Any]], check_id: str, category: str, status: str, message: str, **extra: Any) -> None:
    item = {"id": check_id, "category": category, "status": status, "message": message}
    item.update({key: value for key, value in extra.items() if value is not None})
    checks.append(item)
```

- [x] **Step 6: Run GREEN verification for entropy tests**

Run:

```bash
python -m pytest tests/test_regression_entropy_cleanup.py tests/test_regression_hook_catalog.py -q
```

Expected:

- PASS.

- [x] **Step 7: Run CLI smoke**

Run:

```bash
python scripts/gates/entropy_cleanup.py --json --ref-warn-days 99999
```

Expected:

- Exit `0`.
- JSON parses.
- `summary.errors` is `0`.

- [x] **Step 8: Commit implementation**

```bash
git add schemas/entropy-cleanup-report.schema.json schemas/hook-catalog.schema.json hooks/catalog.json scripts/gates/entropy_cleanup.py tests/test_regression_entropy_cleanup.py tests/test_regression_hook_catalog.py
git commit -m "feat: report harness entropy cleanup signals"
```

---

## Task 3: Wire P11 Into Docs, CI, And Release Story

**Files:**
- Create: `docs/entropy-cleanup.md`
- Modify: `.github/workflows/validate-plugin.yml`
- Modify: `CHANGELOG.md`
- Modify: `tests/test_regression_v019_release_story.py`

- [x] **Step 1: Add failing release-story tests**

Append to `tests/test_regression_v019_release_story.py`:

```python
def test_ci_runs_entropy_cleanup_report_gate():
    """P11 entropy cleanup should run before broad pytest."""
    workflow = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
    assert "Entropy cleanup report gate" in workflow
    assert "python scripts/gates/entropy_cleanup.py --json" in workflow


def test_unreleased_documents_entropy_cleanup_loop():
    """The Unreleased story must name the P11 entropy cleanup loop."""
    section = _unreleased_section()
    required = [
        "Entropy cleanup report gate",
        "scripts/gates/entropy_cleanup.py",
        "capture-only hook candidates",
        "ref freshness",
        "read-only",
    ]
    missing = [token for token in required if token not in section]
    assert not missing, (
        "CHANGELOG [Unreleased] must explain P11 entropy cleanup; "
        f"missing: {missing}"
    )
```

- [x] **Step 2: Run release-story tests to verify RED**

Run:

```bash
python -m pytest tests/test_regression_v019_release_story.py -q
```

Expected:

- FAIL because the CI step and changelog story are not wired yet.

- [x] **Step 3: Add operator docs**

Create `docs/entropy-cleanup.md` with:

```markdown
# Entropy Cleanup Report

P11 adds a read-only cleanup sensor for Athanor harness entropy.

Run:

```bash
python scripts/gates/entropy_cleanup.py --json
```

The gate scans dated implementation plans, capture-only hook candidates, local
`ref/` repositories, and runtime conformance. It does not delete files, update
refs, enable hooks, install hooks, or write settings.

Statuses:

- `pass`: no warnings or failures.
- `warn`: cleanup actions exist, but no structural failure was found.
- `fail`: required metadata or runtime conformance is broken.

Warnings exit `0` by default so CI can collect the report without turning
historical cleanup work into a release blocker. Use `--strict` when a scheduled
cleanup run or release pass intentionally wants a zero-warning queue.
```

- [x] **Step 4: Add CI gate**

In `.github/workflows/validate-plugin.yml`, after the Observability trend
snapshot gate, add:

```yaml
      - name: Entropy cleanup report gate
        shell: bash
        run: python scripts/gates/entropy_cleanup.py --json
```

- [x] **Step 5: Add changelog story**

In `CHANGELOG.md` under `[Unreleased]`, add:

```markdown
- **Entropy cleanup report gate.** Adds read-only `scripts/gates/entropy_cleanup.py`
  plus `schemas/entropy-cleanup-report.schema.json` to surface stale plans,
  capture-only hook candidates, ref freshness, and runtime mirror/conformance
  drift as structured cleanup actions before P12 expands live orchestration.
```

- [x] **Step 6: Run docs/release GREEN verification**

Run:

```bash
python -m pytest tests/test_regression_v019_release_story.py tests/test_regression_entropy_cleanup.py -q
```

Expected:

- PASS.

- [x] **Step 7: Commit docs and CI wiring**

```bash
git add docs/entropy-cleanup.md .github/workflows/validate-plugin.yml CHANGELOG.md tests/test_regression_v019_release_story.py
git commit -m "docs: wire entropy cleanup gate into release story"
```

---

## Task 4: Final Verification And Merge

**Files:**
- Modify: `docs/plans/2026-06-17-p11-entropy-cleanup-loop-plan.md`

- [x] **Step 1: Run focused verification**

```bash
python -m pytest tests/test_regression_entropy_cleanup.py tests/test_regression_hook_catalog.py tests/test_regression_runtime_conformance.py tests/test_regression_v019_release_story.py -q
python scripts/gates/entropy_cleanup.py --json --ref-warn-days 99999
python scripts/gates/runtime_conformance.py --json
git diff --check
```

Expected:

- Pytest PASS.
- Entropy cleanup exits `0`.
- Runtime conformance exits `0`.
- `git diff --check` exits `0`.

- [x] **Step 2: Run full regression suite**

```bash
python -m pytest tests\ -q
```

Expected:

- PASS with the existing skip/xpass profile.

- [x] **Step 3: Mark verification steps complete and commit**

```bash
git add docs/plans/2026-06-17-p11-entropy-cleanup-loop-plan.md
git commit -m "docs: record entropy cleanup verification"
```

- [ ] **Step 4: Fast-forward merge to main and push**

```bash
git checkout main
git pull --ff-only origin main
git merge --ff-only feat/p11-entropy-cleanup-loop
python -m pytest tests\ -q
git diff --check
git push origin main
```

- [ ] **Step 5: Mark merge complete, commit, push, and delete feature branch**

```bash
git add docs/plans/2026-06-17-p11-entropy-cleanup-loop-plan.md
git commit -m "docs: mark p11 merge complete"
git push origin main
git branch --delete feat/p11-entropy-cleanup-loop
```

---

## Self-Review

- Spec coverage: tasks cover P11 report gate, schema, hook candidate lifecycle metadata, plan/ref/mirror sensors, docs, CI, release story, and merge verification.
- Placeholder scan: no placeholders or deferred implementation notes remain.
- Type consistency: report fields match the schema and test expectations.
- Scope control: P12 runtime adapters, external telemetry, scheduled tasks, and automatic deletion remain out of scope.
