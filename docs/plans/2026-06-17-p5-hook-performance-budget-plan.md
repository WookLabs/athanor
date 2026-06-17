# P5 Hook Performance Budget Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add executable hook performance budget checks and safe capture-only fixture handling without enabling new default hooks or fabricating live evidence.

**Architecture:** Keep the catalog as the source of truth. A new gate reads enabled hooks from `hooks/catalog.json`, replays representative safe payloads, measures runtimes, and reports pass/fail. Fixture import/replay gains a non-replayable capture-only path so live-redacted payloads can be stored and safety-validated before replay support exists.

**Tech Stack:** Python standard library, pytest, GitHub Actions, existing hook catalog and fixture corpus.

---

## File Structure

- Create `scripts/gates/check_hook_performance_budget.py`
  - Reads `hooks/catalog.json`.
  - Selects `runtime_default == "enabled"` hooks only.
  - Maps each event to existing safe fixture payloads.
  - Executes hook commands through the Python interpreter where possible.
  - Emits JSON with per-hook samples, median/max runtime, budget, status.
  - Exits non-zero if a required enabled hook has no safe sample or exceeds
    budget.
- Modify `scripts/gates/import_hook_fixture.py`
  - Allows cataloged capture-only events to be imported as `replayable: false`.
  - Still rejects unknown events and unsafe source levels.
- Modify `scripts/gates/replay_hook_fixtures.py`
  - Safety-validates every fixture before dispatch.
  - Reports unsupported capture-only fixtures as skipped instead of failed.
  - Still fails if an enabled/replayable event has no handler.
- Modify `.github/workflows/validate-plugin.yml`
  - Adds named "Hook performance budget gate" step.
- Modify `docs/hook-payload-corpus.md`
  - Documents live-redacted capture-only import and replay skip semantics.
- Modify `docs/hook-catalog.md`
  - Documents executable performance budgets.
- Add tests:
  - `tests/test_regression_hook_performance_budget.py`
  - Extend `tests/test_regression_hook_payload_import.py`
  - Extend `tests/test_regression_hook_payload_replay.py`
  - Extend `tests/test_regression_v019_release_story.py`

## Task 1: Performance Gate Red Test

**Files:**
- Create: `tests/test_regression_hook_performance_budget.py`
- Later create: `scripts/gates/check_hook_performance_budget.py`

- [ ] **Step 1: Write failing tests**

```python
"""Regression tests for executable hook performance budgets."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "gates" / "check_hook_performance_budget.py"


def run_budget_gate(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )


def test_budget_gate_exists_and_reports_enabled_hooks() -> None:
    result = run_budget_gate("--json", "--samples", "1")

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    hook_ids = {entry["id"] for entry in report["hooks"]}

    assert "stop-verify-claims" in hook_ids
    assert "pretool-dispatcher" in hook_ids
    assert "posttool-evidence-sniffer" in hook_ids
    assert all(entry["status"] == "pass" for entry in report["hooks"])


def test_budget_gate_fails_when_budget_is_too_low() -> None:
    result = run_budget_gate(
        "--json",
        "--samples",
        "1",
        "--override-budget-ms",
        "stop-verify-claims=0",
    )

    assert result.returncode == 1
    report = json.loads(result.stdout)
    stop_entry = next(
        entry for entry in report["hooks"] if entry["id"] == "stop-verify-claims"
    )
    assert stop_entry["status"] == "fail"
    assert "budget" in stop_entry["reason"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_regression_hook_performance_budget.py -q
```

Expected: fail because `scripts/gates/check_hook_performance_budget.py` does not
exist yet.

## Task 2: Implement Performance Gate

**Files:**
- Create: `scripts/gates/check_hook_performance_budget.py`

- [ ] **Step 1: Add the gate**

Implement these contracts:

- CLI:
  - `--catalog hooks/catalog.json`
  - `--fixture-root tests/fixtures/hooks`
  - `--samples 3`
  - `--json`
  - `--override-budget-ms hook-id=ms` for regression testing
- Payload selection:
  - Use `tests/fixtures/hooks/index.json`.
  - Prefer fixtures whose event matches the catalog event and whose source level
    is `live-redacted`.
  - Fall back to synthetic fixtures only when no live-redacted fixture exists.
  - Require at least one safe fixture for each enabled hook.
- Execution:
  - Resolve `python3 "${CLAUDE_PLUGIN_ROOT}/path.py"` to
    `[sys.executable, repo_root / "path.py"]`.
  - Set `CLAUDE_PLUGIN_ROOT` to the repo root.
  - Pipe the fixture payload to stdin.
  - Measure with `time.perf_counter()`.
  - Treat exit codes 0 and 2 as valid hook completions; performance gate is not
    a policy correctness gate.
- Output:
  - JSON object with `status`, `hooks`, `samples`, and `fixture_root`.
  - Per hook: `id`, `event`, `budget_ms`, `median_ms`, `max_ms`, `runs`,
    `fixtures`, `status`, `reason`.
- Exit codes:
  - `0` if every enabled hook passes.
  - `1` if any hook is missing fixtures, command parsing fails, subprocess
    launch fails, or runtime exceeds budget.

- [ ] **Step 2: Run targeted performance tests**

Run:

```bash
python -m pytest tests/test_regression_hook_performance_budget.py -q
```

Expected: pass.

- [ ] **Step 3: Run the new gate directly**

Run:

```bash
python scripts/gates/check_hook_performance_budget.py --json --samples 1
```

Expected: JSON `status` is `pass` and includes the three enabled hook IDs.

## Task 3: Capture-Only Import Red Tests

**Files:**
- Modify: `tests/test_regression_hook_payload_import.py`
- Later modify: `scripts/gates/import_hook_fixture.py`

- [ ] **Step 1: Add failing test for capture-only import**

Add a test that builds a temporary raw `SessionStart` payload and imports it
with `source_level: live-redacted`.

Expected assertions:

```python
assert imported_index_entry["event"] == "SessionStart"
assert imported_index_entry["source_level"] == "live-redacted"
assert imported_index_entry["replayable"] is False
assert imported_index_entry["redaction"]["reviewed"] is True
```

- [ ] **Step 2: Run the focused import test**

Run:

```bash
python -m pytest tests/test_regression_hook_payload_import.py -q
```

Expected: fail because the importer still rejects non-replayable events.

## Task 4: Implement Capture-Only Import

**Files:**
- Modify: `scripts/gates/import_hook_fixture.py`

- [ ] **Step 1: Update event policy**

Implementation contract:

- Load `hooks/catalog.json`.
- Allow import when event is either:
  - replayable core event: `Stop`, `PreToolUse`, `PostToolUse`; or
  - cataloged event with `runtime_default == "capture-only"`.
- Set `replayable: true` only for replayable core events.
- Set `replayable: false` for capture-only events.
- Keep rejecting unknown events and disabled non-capture events.
- Preserve all existing redaction and unsafe-token checks.

- [ ] **Step 2: Run import tests**

Run:

```bash
python -m pytest tests/test_regression_hook_payload_import.py -q
```

Expected: pass.

## Task 5: Replay Skip Red Tests

**Files:**
- Modify: `tests/test_regression_hook_payload_replay.py`
- Later modify: `scripts/gates/replay_hook_fixtures.py`

- [ ] **Step 1: Add capture-only skip test**

Add a test fixture index entry for a safe `SessionStart` capture-only fixture
with `replayable: false`.

Expected behavior:

```python
assert result.returncode == 0
report = json.loads(result.stdout)
skipped = [item for item in report["results"] if item["status"] == "skipped"]
assert skipped[0]["event"] == "SessionStart"
assert "capture-only" in skipped[0]["reason"]
```

- [ ] **Step 2: Run replay tests**

Run:

```bash
python -m pytest tests/test_regression_hook_payload_replay.py -q
```

Expected: fail because unsupported events currently fail instead of skip.

## Task 6: Implement Replay Skip Semantics

**Files:**
- Modify: `scripts/gates/replay_hook_fixtures.py`

- [ ] **Step 1: Validate before skip**

Implementation contract:

- Load and validate fixture payload/redaction metadata before deciding skip.
- If `replayable is False` and the event is cataloged capture-only, append:

```json
{
  "id": "...",
  "event": "SessionStart",
  "status": "skipped",
  "reason": "capture-only fixture has no replay handler"
}
```

- Keep failing unsupported replayable events.
- Keep failing unsafe payloads even when capture-only.

- [ ] **Step 2: Run replay tests**

Run:

```bash
python -m pytest tests/test_regression_hook_payload_replay.py -q
```

Expected: pass.

## Task 7: CI And Docs

**Files:**
- Modify: `.github/workflows/validate-plugin.yml`
- Modify: `tests/test_regression_v019_release_story.py`
- Modify: `docs/hook-payload-corpus.md`
- Modify: `docs/hook-catalog.md`
- Modify: `docs/architecture/2026-06-17-loop-harness-deep-research.md` if final
  P5 details differ from this plan.

- [ ] **Step 1: Add CI regression test**

Extend `tests/test_regression_v019_release_story.py` to assert:

```python
assert "Hook performance budget gate" in workflow
assert "python scripts/gates/check_hook_performance_budget.py" in workflow
assert "--json" in workflow
```

- [ ] **Step 2: Update workflow**

Add a named step after the hook replay gate:

```yaml
      - name: Hook performance budget gate
        run: python scripts/gates/check_hook_performance_budget.py --json
```

- [ ] **Step 3: Update docs**

Document:

- `performance_budget_ms` is executable for enabled hooks.
- Capture-only live-redacted fixtures may be imported as non-replayable.
- Replay validates safety/provenance before reporting capture-only skip.
- Live capture-only fixtures must not be fabricated.

- [ ] **Step 4: Run CI/docs tests**

Run:

```bash
python -m pytest tests/test_regression_v019_release_story.py tests/test_regression_hook_catalog.py tests/test_regression_hook_payload_capture.py -q
```

Expected: pass.

## Task 8: Full Verification

**Files:**
- All changed files.

- [ ] **Step 1: Run targeted suite**

Run:

```bash
python -m pytest tests/test_regression_hook_performance_budget.py tests/test_regression_hook_payload_import.py tests/test_regression_hook_payload_replay.py tests/test_regression_v019_release_story.py -q
```

Expected: pass.

- [ ] **Step 2: Run hook gates**

Run:

```bash
python scripts/gates/replay_hook_fixtures.py --fixture-root tests/fixtures/hooks --json
python scripts/gates/check_hook_performance_budget.py --json
```

Expected: both pass.

- [ ] **Step 3: Run release readiness and full tests**

Run:

```bash
python scripts/check_release_ready.py --ci
python -m pytest tests/ -q
git diff --check
```

Expected: all pass.

- [ ] **Step 4: Commit**

Run:

```bash
git add scripts/gates/check_hook_performance_budget.py scripts/gates/import_hook_fixture.py scripts/gates/replay_hook_fixtures.py .github/workflows/validate-plugin.yml docs/hook-payload-corpus.md docs/hook-catalog.md docs/architecture/2026-06-17-loop-harness-deep-research.md docs/plans/2026-06-17-p5-hook-performance-budget-plan.md tests/test_regression_hook_performance_budget.py tests/test_regression_hook_payload_import.py tests/test_regression_hook_payload_replay.py tests/test_regression_v019_release_story.py
git commit -m "feat: add hook performance budget gate"
```

Expected: one focused P5 commit.

## Self-Review

- Spec coverage: P5 covers executable performance budgets and capture-only
  fixture infrastructure. It intentionally does not collect fake live fixtures,
  enable new hooks, or add installer writes.
- Marker scan: no incomplete markers remain.
- Type consistency: plan consistently uses `replayable`, `runtime_default`,
  `performance_budget_ms`, and existing catalog event names.
