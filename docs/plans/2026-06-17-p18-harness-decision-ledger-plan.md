# P18 Harness Decision Ledger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a machine-readable harness decision ledger and CI gate so harness changes declare expected metrics, verification commands, observed results, and rollback/follow-up decisions.

**Architecture:** Use committed JSON files under `docs/harness-decisions/` as the source of truth. A dependency-free Python gate validates ledger shape, duplicate ids, observed-result evidence, expected metric directions, and emits a schema-backed JSON report.

**Tech Stack:** Python stdlib, pytest, jsonschema, GitHub Actions, markdown docs.

---

## File Structure

- Create `scripts/gates/harness_decision_ledger.py`
  - Reads ledger JSON files.
  - Validates decision entries.
  - Emits report with `pass`/`fail`.

- Create `schemas/harness-decision-ledger-report.schema.json`
  - Report schema.

- Create `docs/harness-decisions/2026-06-17-p17-trace-memory-quality.json`
  - First observed decision entry.

- Create `docs/harness-decision-ledger.md`
  - Operator docs and schema contract.

- Create `tests/test_regression_harness_decision_ledger.py`
  - RED/GREEN tests for report, schema, duplicates, missing observed evidence,
    invalid metric directions, and blank commands.

- Modify `.github/workflows/validate-plugin.yml`
  - Add named `Harness decision ledger gate`.

- Modify `CHANGELOG.md`
  - Add P18 release story.

- Modify `tests/test_regression_v019_release_story.py`
  - Lock CI and changelog coverage.

---

### Task 1: RED Tests And Initial Ledger Fixture

**Files:**
- Create: `tests/test_regression_harness_decision_ledger.py`
- Create: `docs/harness-decisions/2026-06-17-p17-trace-memory-quality.json`

- [ ] **Step 1: Add first decision ledger entry**

Create `docs/harness-decisions/2026-06-17-p17-trace-memory-quality.json`:

```json
{
  "schema_version": 1,
  "decisions": [
    {
      "id": "p17-trace-memory-quality",
      "date": "2026-06-17",
      "status": "observed",
      "change_type": "memory",
      "summary": "Add read-only trace-memory quality gate.",
      "expected_metrics": [
        {
          "metric": "trace_memory_quality.violations",
          "direction": "stay_or_decrease",
          "target": "0 violations on committed fixture gate"
        }
      ],
      "verification_commands": [
        {
          "command": "python scripts/gates/trace_memory_quality.py --lesson-root tests/fixtures/trace_memory_quality/lessons --comparison-file tests/fixtures/trace_memory_quality/comparisons.json --today 2026-06-17 --json",
          "expected": "status pass with 0 violations"
        }
      ],
      "observed_results": [
        {
          "status": "pass",
          "summary": "Fixture gate passed with 0 violations and 1 decay warning.",
          "evidence_refs": [
            "tests/test_regression_trace_memory_quality.py",
            "docs/trace-memory-quality.md"
          ]
        }
      ],
      "decision": "keep",
      "rollback_or_follow_up": "If the gate becomes noisy, keep it fixture-scoped in CI and revise the evidence contract before applying it to local user lessons."
    }
  ]
}
```

- [ ] **Step 2: Write RED tests**

Create `tests/test_regression_harness_decision_ledger.py`:

```python
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "gates" / "harness_decision_ledger.py"
SCHEMA = REPO_ROOT / "schemas" / "harness-decision-ledger-report.schema.json"
LEDGER_ROOT = REPO_ROOT / "docs" / "harness-decisions"


def _run_report(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--json", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _write_ledger(root: Path, name: str, decisions: list[dict]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / name
    path.write_text(
        json.dumps({"schema_version": 1, "decisions": decisions}, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def _decision(**overrides: object) -> dict:
    item = {
        "id": "decision-a",
        "date": "2026-06-17",
        "status": "observed",
        "change_type": "gate",
        "summary": "Fixture decision.",
        "expected_metrics": [
            {
                "metric": "fixture.metric",
                "direction": "increase",
                "target": "higher is better",
            }
        ],
        "verification_commands": [
            {"command": "python fixture.py --json", "expected": "status pass"}
        ],
        "observed_results": [
            {
                "status": "pass",
                "summary": "Observed pass.",
                "evidence_refs": ["tests/fixture.py"],
            }
        ],
        "decision": "keep",
        "rollback_or_follow_up": "Revert fixture gate if it becomes noisy.",
    }
    item.update(overrides)
    return item


def test_committed_harness_decision_ledger_passes() -> None:
    result = _run_report("--ledger-root", str(LEDGER_ROOT))

    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["schema_version"] == 1
    assert report["status"] == "pass"
    assert report["summary"]["decisions"] >= 1
    assert report["summary"]["errors"] == 0
    assert "p17-trace-memory-quality" in {item["id"] for item in report["decisions"]}


def test_harness_decision_ledger_report_matches_schema() -> None:
    result = _run_report("--ledger-root", str(LEDGER_ROOT))

    assert result.returncode == 0, result.stdout + result.stderr
    jsonschema.validate(
        json.loads(result.stdout),
        json.loads(SCHEMA.read_text(encoding="utf-8")),
    )


def test_duplicate_decision_ids_fail(tmp_path: Path) -> None:
    _write_ledger(tmp_path, "a.json", [_decision(id="dupe")])
    _write_ledger(tmp_path, "b.json", [_decision(id="dupe")])

    result = _run_report("--ledger-root", str(tmp_path))

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["status"] == "fail"
    assert any(error["code"] == "duplicate_id" for error in report["errors"])


def test_observed_decision_without_observed_results_fails(tmp_path: Path) -> None:
    _write_ledger(tmp_path, "a.json", [_decision(observed_results=[])])

    result = _run_report("--ledger-root", str(tmp_path))

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert any(error["code"] == "missing_observed_results" for error in report["errors"])


def test_observed_result_without_evidence_refs_fails(tmp_path: Path) -> None:
    item = _decision(
        observed_results=[
            {"status": "pass", "summary": "Observed pass.", "evidence_refs": []}
        ]
    )
    _write_ledger(tmp_path, "a.json", [item])

    result = _run_report("--ledger-root", str(tmp_path))

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert any(error["code"] == "missing_evidence_refs" for error in report["errors"])


def test_invalid_metric_direction_fails(tmp_path: Path) -> None:
    item = _decision(
        expected_metrics=[
            {"metric": "fixture.metric", "direction": "sideways", "target": "invalid"}
        ]
    )
    _write_ledger(tmp_path, "a.json", [item])

    result = _run_report("--ledger-root", str(tmp_path))

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert any(error["code"] == "invalid_metric_direction" for error in report["errors"])


def test_blank_verification_command_fails(tmp_path: Path) -> None:
    item = _decision(verification_commands=[{"command": " ", "expected": "status pass"}])
    _write_ledger(tmp_path, "a.json", [item])

    result = _run_report("--ledger-root", str(tmp_path))

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert any(error["code"] == "blank_verification_command" for error in report["errors"])
```

- [ ] **Step 3: Verify RED**

Run:

```powershell
python -m pytest tests\test_regression_harness_decision_ledger.py -q
```

Expected: fail because script/schema do not exist.

---

### Task 2: Implement Gate And Schema

**Files:**
- Create: `scripts/gates/harness_decision_ledger.py`
- Create: `schemas/harness-decision-ledger-report.schema.json`

- [ ] **Step 1: Implement schema**

Create a report schema requiring:

- `schema_version`
- `status`
- `ledger_root`
- `summary`
- `decisions`
- `errors`

Decision report entries include `id`, `path`, `status`, `change_type`, and
`date`. Errors include `code`, `message`, `path`, and optional `decision_id`.

- [ ] **Step 2: Implement script**

Implement:

- CLI args: `--ledger-root`, `--allow-empty`, `--json`
- JSON file discovery under the root
- per-file schema version check
- duplicate id detection
- required string fields
- expected metric direction validation:
  `increase`, `decrease`, `stay`, `stay_or_increase`, `stay_or_decrease`
- observed-result enforcement for `status: observed`
- evidence refs enforcement for observed results
- blank verification command detection
- exit 0 on pass, 1 on validation errors, 2 on malformed input

- [ ] **Step 3: Verify GREEN**

Run:

```powershell
python -m pytest tests\test_regression_harness_decision_ledger.py -q
```

Expected: all tests pass.

---

### Task 3: Docs, CI, Release Story

**Files:**
- Create: `docs/harness-decision-ledger.md`
- Modify: `.github/workflows/validate-plugin.yml`
- Modify: `CHANGELOG.md`
- Modify: `tests/test_regression_v019_release_story.py`

- [ ] **Step 1: Create docs**

Document:

- why the ledger exists;
- file path;
- required fields;
- valid metric directions;
- example command.

- [ ] **Step 2: Add CI gate**

Add after the trace-memory quality gate:

```yaml
      - name: Harness decision ledger gate
        shell: bash
        run: python scripts/gates/harness_decision_ledger.py --json
```

- [ ] **Step 3: Add release-story tests**

Add tests asserting:

- CI contains `Harness decision ledger gate`;
- changelog mentions `Harness decision ledger`, the script, expected metrics,
  observed results, and rollback/follow-up.

- [ ] **Step 4: Add changelog**

Add under `[Unreleased]`:

```markdown
- **Harness decision ledger.** Adds committed `docs/harness-decisions/*.json`
  records plus `scripts/gates/harness_decision_ledger.py` so harness changes
  declare expected metrics, verification commands, observed results, and
  rollback/follow-up decisions before the harness can claim self-improvement.
```

---

### Task 4: Verification And Commit

**Files:** all P18 files.

- [ ] **Step 1: Run focused tests**

```powershell
python -m pytest tests\test_regression_harness_decision_ledger.py tests\test_regression_v019_release_story.py -q
```

- [ ] **Step 2: Run direct gate**

```powershell
python scripts\gates\harness_decision_ledger.py --json
```

- [ ] **Step 3: Run touched CI gates**

```powershell
python scripts\gates\trace_memory_quality.py --lesson-root tests\fixtures\trace_memory_quality\lessons --comparison-file tests\fixtures\trace_memory_quality\comparisons.json --today 2026-06-17 --json
python scripts\gates\distribution_smoke.py --json
python scripts\gates\runtime_conformance.py --json
```

- [ ] **Step 4: Run full tests**

```powershell
python -m pytest tests\ -q
```

- [ ] **Step 5: Whitespace check**

```powershell
git diff --check
```

- [ ] **Step 6: Commit**

```powershell
git add scripts/gates/harness_decision_ledger.py schemas/harness-decision-ledger-report.schema.json docs/harness-decisions docs/harness-decision-ledger.md docs/architecture/2026-06-17-p18-harness-decision-ledger-design.md docs/plans/2026-06-17-p18-harness-decision-ledger-plan.md tests/test_regression_harness_decision_ledger.py tests/test_regression_v019_release_story.py .github/workflows/validate-plugin.yml CHANGELOG.md
git commit -m "feat: add harness decision ledger"
```

---

## Self-Review Checklist

- Spec coverage: design requirements map to Tasks 1-3.
- Placeholder scan: no TBD/TODO placeholders.
- Scope: read-only ledger validation only; no automatic metric parsing.

