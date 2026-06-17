# P17 Trace-Memory Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only trace-to-memory quality gate so Athanor lesson promotion, decay, quarantine, and injected-memory comparisons are evidence-backed.

**Architecture:** Keep the gate dependency-free and local-first. The new CLI parses lesson markdown frontmatter, reads memory thresholds from `athanor.json`, optionally reads deterministic comparison fixtures, emits a schema-validated JSON report, and fails only on unsafe invariants such as unbacked promotion or degraded injected memory.

**Tech Stack:** Python stdlib, pytest, jsonschema, GitHub Actions, markdown docs.

---

## File Structure

- Create `scripts/gates/trace_memory_quality.py`
  - Pure-Python CLI and reusable functions.
  - Owns frontmatter parsing, config loading, lesson classification,
    comparison validation, report construction, and exit codes.

- Create `schemas/trace-memory-quality-report.schema.json`
  - Machine-readable contract for the JSON report.

- Create `tests/fixtures/trace_memory_quality/lessons/*.md`
  - Stable committed lesson fixtures.

- Create `tests/fixtures/trace_memory_quality/comparisons.json`
  - Stable comparison fixture where injected lesson score does not degrade.

- Create `tests/test_regression_trace_memory_quality.py`
  - CLI, schema, fixture, and failure regression tests.

- Create `docs/trace-memory-quality.md`
  - Operator-facing documentation.

- Modify `.github/workflows/validate-plugin.yml`
  - Add a named `Trace-memory quality gate` before broad pytest.

- Modify `agents/learner.md`
  - Add optional evidence refs to the lesson template and rules.

- Modify `skills/work/references/learner-cleaner.md`
  - Keep inline Learner/Cleaner reference aligned with the registered learner.

- Modify `CHANGELOG.md`
  - Add the P17 release story under `[Unreleased]`.

- Modify `tests/test_regression_v019_release_story.py`
  - Assert the CI gate and changelog story remain present.

---

### Task 1: Add RED Tests And Fixtures

**Files:**
- Create: `tests/test_regression_trace_memory_quality.py`
- Create: `tests/fixtures/trace_memory_quality/lessons/work-2026-06-17-001.md`
- Create: `tests/fixtures/trace_memory_quality/lessons/work-2026-06-01-002.md`
- Create: `tests/fixtures/trace_memory_quality/lessons/debug-2026-06-01-003.md`
- Create: `tests/fixtures/trace_memory_quality/lessons/plan-2026-06-17-004.md`
- Create: `tests/fixtures/trace_memory_quality/comparisons.json`

- [ ] **Step 1: Create committed fixture lessons**

Create four lessons:

`tests/fixtures/trace_memory_quality/lessons/work-2026-06-17-001.md`

```markdown
---
type: lesson
skill: work
contract-id: trace-memory-quality
version-at-time-of-lesson: v0.18.8
confidence: high
source: session-p17
access_count: 6
date: 2026-06-17
created: 2026-06-17
importance: working
trace_refs:
  - tests/fixtures/workflow_evals/scenarios.json#work-happy-path
eval_refs:
  - tests/fixtures/workflow_evals/scenarios.json#work-happy-path
---

## Lesson: Evidence-backed work promotion

Use trace-backed evidence before promoting high-access work lessons.
```

`tests/fixtures/trace_memory_quality/lessons/work-2026-06-01-002.md`

```markdown
---
type: lesson
skill: work
contract-id: stale-working-example
version-at-time-of-lesson: v0.18.8
confidence: medium
source: session-p17
access_count: 1
date: 2026-06-01
created: 2026-06-01
importance: working
---

## Lesson: Stale low-access working memory

This fixture should be reported as a decay candidate, not promoted.
```

`tests/fixtures/trace_memory_quality/lessons/debug-2026-06-01-003.md`

```markdown
---
type: lesson
skill: debug
contract-id: degraded-debug-example
version-at-time-of-lesson: v0.18.8
confidence: low
source: session-p17
access_count: 2
date: 2026-06-01
created: 2026-06-01
importance: quarantine
memory_outcome: degraded
trace_refs:
  - tests/fixtures/workflow_evals/scenarios.json#debug-regression
---

## Lesson: Quarantined degraded memory

This fixture proves harmful memory can be retained only as quarantine.
```

`tests/fixtures/trace_memory_quality/lessons/plan-2026-06-17-004.md`

```markdown
---
type: lesson
skill: plan
contract-id: permanent-backed-example
version-at-time-of-lesson: v0.18.8
confidence: high
source: session-p17
access_count: 9
date: 2026-06-17
created: 2026-06-17
importance: permanent
evidence_refs:
  - docs/architecture/2026-06-17-p17-trace-memory-quality-design.md#gate-rules
---

## Lesson: Permanent lessons need evidence

Permanent memory is allowed only when evidence-backed.
```

- [ ] **Step 2: Create a non-degrading comparison fixture**

Create `tests/fixtures/trace_memory_quality/comparisons.json`:

```json
{
  "schema_version": 1,
  "comparisons": [
    {
      "id": "work-lesson-improves-happy-path",
      "lesson_id": "work-2026-06-17-001",
      "scenario_id": "work-happy-path",
      "baseline_score": 0.8,
      "injected_score": 1.0,
      "trace_refs": [
        "tests/fixtures/workflow_evals/scenarios.json#work-happy-path"
      ]
    }
  ]
}
```

- [ ] **Step 3: Write RED regression tests**

Create `tests/test_regression_trace_memory_quality.py`:

```python
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "gates" / "trace_memory_quality.py"
SCHEMA = REPO_ROOT / "schemas" / "trace-memory-quality-report.schema.json"
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "trace_memory_quality"
LESSONS = FIXTURE_ROOT / "lessons"
COMPARISONS = FIXTURE_ROOT / "comparisons.json"


def _run_report(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--json", "--today", "2026-06-17", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _write_lesson(root: Path, name: str, frontmatter: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / name
    path.write_text(f"---\n{frontmatter.strip()}\n---\n\n## Lesson\nBody.\n", encoding="utf-8")
    return path


def test_trace_memory_quality_fixture_report_passes() -> None:
    result = _run_report("--lesson-root", str(LESSONS), "--comparison-file", str(COMPARISONS))

    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["schema_version"] == 1
    assert report["status"] == "pass"
    assert report["summary"]["lessons"] == 4
    assert report["summary"]["violations"] == 0
    actions = {lesson["lesson_id"]: lesson["action"] for lesson in report["lessons"]}
    assert actions["work-2026-06-17-001"] == "promote_candidate"
    assert actions["work-2026-06-01-002"] == "decay"
    assert actions["debug-2026-06-01-003"] == "quarantine"
    assert actions["plan-2026-06-17-004"] == "keep"


def test_trace_memory_quality_report_matches_schema() -> None:
    result = _run_report("--lesson-root", str(LESSONS), "--comparison-file", str(COMPARISONS))

    assert result.returncode == 0, result.stdout + result.stderr
    jsonschema.validate(
        json.loads(result.stdout),
        json.loads(SCHEMA.read_text(encoding="utf-8")),
    )


def test_permanent_lesson_without_evidence_fails(tmp_path: Path) -> None:
    lessons = tmp_path / "lessons"
    _write_lesson(
        lessons,
        "plan-2026-06-17-999.md",
        """
type: lesson
skill: plan
contract-id: missing-evidence
version-at-time-of-lesson: v0.18.8
confidence: high
source: session-p17
access_count: 10
date: 2026-06-17
importance: permanent
""",
    )

    result = _run_report("--lesson-root", str(lessons))

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["status"] == "fail"
    assert report["summary"]["violations"] == 1
    assert report["lessons"][0]["action"] == "violation"
    assert "evidence" in report["lessons"][0]["reason"]


def test_promotion_candidate_without_evidence_fails(tmp_path: Path) -> None:
    lessons = tmp_path / "lessons"
    _write_lesson(
        lessons,
        "work-2026-06-01-999.md",
        """
type: lesson
skill: work
contract-id: unbacked-promotion
version-at-time-of-lesson: v0.18.8
confidence: medium
source: session-p17
access_count: 8
date: 2026-06-01
importance: working
""",
    )

    result = _run_report("--lesson-root", str(lessons))

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["lessons"][0]["action"] == "violation"
    assert "promotion candidate" in report["lessons"][0]["reason"]


def test_degraded_lesson_without_quarantine_fails(tmp_path: Path) -> None:
    lessons = tmp_path / "lessons"
    _write_lesson(
        lessons,
        "debug-2026-06-17-999.md",
        """
type: lesson
skill: debug
contract-id: degraded-not-quarantined
version-at-time-of-lesson: v0.18.8
confidence: low
source: session-p17
access_count: 1
date: 2026-06-17
importance: working
memory_outcome: degraded
trace_refs:
  - tests/fixtures/workflow_evals/scenarios.json#debug-regression
""",
    )

    result = _run_report("--lesson-root", str(lessons))

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["lessons"][0]["action"] == "violation"
    assert "quarantine" in report["lessons"][0]["reason"]


def test_degraded_comparison_fails(tmp_path: Path) -> None:
    comparison = tmp_path / "comparisons.json"
    comparison.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "comparisons": [
                    {
                        "id": "bad-injection",
                        "lesson_id": "work-2026-06-17-001",
                        "scenario_id": "work-happy-path",
                        "baseline_score": 1.0,
                        "injected_score": 0.5,
                        "trace_refs": ["trace.jsonl#workflow.finished"],
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = _run_report("--lesson-root", str(LESSONS), "--comparison-file", str(comparison))

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["status"] == "fail"
    assert report["comparisons"][0]["status"] == "fail"
    assert "degraded" in report["comparisons"][0]["reason"]
```

- [ ] **Step 4: Run tests and verify RED**

Run:

```powershell
python -m pytest tests\test_regression_trace_memory_quality.py -q
```

Expected: FAIL because `scripts/gates/trace_memory_quality.py` and the schema
do not exist.

---

### Task 2: Implement Trace-Memory Gate And Schema

**Files:**
- Create: `scripts/gates/trace_memory_quality.py`
- Create: `schemas/trace-memory-quality-report.schema.json`
- Test: `tests/test_regression_trace_memory_quality.py`

- [ ] **Step 1: Create the report schema**

Create `schemas/trace-memory-quality-report.schema.json` with required top-level
fields:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Athanor Trace Memory Quality Report",
  "type": "object",
  "required": [
    "schema_version",
    "status",
    "config",
    "summary",
    "lesson_root",
    "comparison_file",
    "lessons",
    "comparisons"
  ],
  "properties": {
    "schema_version": { "const": 1 },
    "status": { "enum": ["pass", "fail"] },
    "config": {
      "type": "object",
      "required": ["decay_days", "promotion_threshold", "max_age_days"],
      "properties": {
        "decay_days": { "type": "integer", "minimum": 0 },
        "promotion_threshold": { "type": "integer", "minimum": 0 },
        "max_age_days": { "type": "integer", "minimum": 0 }
      },
      "additionalProperties": false
    },
    "summary": {
      "type": "object",
      "required": ["lessons", "comparisons", "violations", "warnings"],
      "properties": {
        "lessons": { "type": "integer", "minimum": 0 },
        "comparisons": { "type": "integer", "minimum": 0 },
        "violations": { "type": "integer", "minimum": 0 },
        "warnings": { "type": "integer", "minimum": 0 }
      },
      "additionalProperties": false
    },
    "lesson_root": { "type": "string" },
    "comparison_file": { "type": ["string", "null"] },
    "lessons": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "lesson_id",
          "path",
          "importance",
          "access_count",
          "age_days",
          "evidence_refs",
          "action",
          "status",
          "reason"
        ],
        "properties": {
          "lesson_id": { "type": "string" },
          "path": { "type": "string" },
          "importance": { "type": "string" },
          "access_count": { "type": "integer", "minimum": 0 },
          "age_days": { "type": ["integer", "null"], "minimum": 0 },
          "evidence_refs": { "type": "array", "items": { "type": "string" } },
          "action": {
            "enum": ["keep", "promote_candidate", "decay", "quarantine", "violation"]
          },
          "status": { "enum": ["pass", "warn", "fail"] },
          "reason": { "type": "string" }
        },
        "additionalProperties": true
      }
    },
    "comparisons": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "id",
          "lesson_id",
          "scenario_id",
          "baseline_score",
          "injected_score",
          "status",
          "reason"
        ],
        "properties": {
          "id": { "type": "string" },
          "lesson_id": { "type": "string" },
          "scenario_id": { "type": "string" },
          "baseline_score": { "type": "number" },
          "injected_score": { "type": "number" },
          "status": { "enum": ["pass", "fail"] },
          "reason": { "type": "string" },
          "trace_refs": { "type": "array", "items": { "type": "string" } }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": false
}
```

- [ ] **Step 2: Implement the CLI**

Create `scripts/gates/trace_memory_quality.py` with:

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LESSON_ROOT = REPO_ROOT / ".athanor" / "lessons"
DEFAULT_CONFIG = REPO_ROOT / "athanor.json"
EVIDENCE_FIELDS = ("trace_refs", "eval_refs", "evidence_refs")
DEGRADED_OUTCOMES = {"harmful", "degraded", "regressed", "negative"}


class TraceMemoryInputError(Exception):
    pass


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    lower = value.lower()
    if lower in {"true", "false"}:
        return lower == "true"
    try:
        return int(value)
    except ValueError:
        return value.strip('"').strip("'")


def parse_frontmatter(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    metadata: dict[str, Any] = {}
    index = 1
    current_key: str | None = None
    while index < len(lines):
        raw = lines[index]
        stripped = raw.strip()
        if stripped == "---":
            break
        if stripped.startswith("- ") and current_key:
            existing = metadata.setdefault(current_key, [])
            if not isinstance(existing, list):
                existing = [existing]
                metadata[current_key] = existing
            existing.append(_parse_scalar(stripped[2:]))
        elif ":" in raw:
            key, value = raw.split(":", 1)
            current_key = key.strip()
            value = value.strip()
            metadata[current_key] = [] if value == "" else _parse_scalar(value)
        index += 1
    return metadata


def load_config(path: Path) -> dict[str, int]:
    if not path.is_file():
        return {"decay_days": 7, "promotion_threshold": 5, "max_age_days": 30}
    data = json.loads(path.read_text(encoding="utf-8"))
    memory = data.get("memory", {}) if isinstance(data, dict) else {}
    return {
        "decay_days": int(memory.get("decayDays", 7)),
        "promotion_threshold": int(memory.get("promotionThreshold", 5)),
        "max_age_days": int(memory.get("maxAgeDays", 30)),
    }


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _age_days(meta: dict[str, Any], today: date) -> int | None:
    raw = meta.get("date") or meta.get("created")
    if not isinstance(raw, str) or not raw:
        return None
    try:
        lesson_date = datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None
    return max((today - lesson_date).days, 0)


def _lesson_id(path: Path, meta: dict[str, Any]) -> str:
    for key in ("lesson_id", "lesson-id", "id"):
        value = meta.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return path.stem


def _evidence_refs(meta: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for field in EVIDENCE_FIELDS:
        refs.extend(_as_list(meta.get(field)))
    return refs


def classify_lesson(path: Path, root: Path, meta: dict[str, Any], config: dict[str, int], today: date) -> dict[str, Any]:
    lesson_id = _lesson_id(path, meta)
    importance = str(meta.get("importance", "working")).strip().lower()
    access_count = int(meta.get("access_count", 0) or 0)
    age = _age_days(meta, today)
    refs = _evidence_refs(meta)
    outcome = str(meta.get("memory_outcome", "")).strip().lower()
    quarantined = importance == "quarantine" or meta.get("quarantine") is True
    status = "pass"
    action = "keep"
    reason = "lesson is within trace-memory policy"

    if outcome in DEGRADED_OUTCOMES and not quarantined:
        status = "fail"
        action = "violation"
        reason = "degraded memory must be quarantined"
    elif quarantined:
        action = "quarantine"
        reason = "degraded or explicitly quarantined memory is isolated"
    elif importance == "permanent" and not refs:
        status = "fail"
        action = "violation"
        reason = "permanent lessons require trace/eval/evidence refs"
    elif importance == "working" and access_count >= config["promotion_threshold"]:
        if refs:
            action = "promote_candidate"
            reason = "working lesson reached promotion threshold with evidence"
        else:
            status = "fail"
            action = "violation"
            reason = "promotion candidate requires trace/eval/evidence refs"
    elif importance == "working" and age is not None and age > config["decay_days"]:
        status = "warn"
        action = "decay"
        reason = "stale low-access working lesson should decay"

    return {
        "lesson_id": lesson_id,
        "path": path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path),
        "importance": importance,
        "access_count": access_count,
        "age_days": age,
        "evidence_refs": refs,
        "action": action,
        "status": status,
        "reason": reason,
    }


def load_lessons(root: Path, config: dict[str, int], today: date) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    if not root.is_dir():
        raise TraceMemoryInputError(f"lesson root is not a directory: {root}")
    lessons: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.md")):
        meta = parse_frontmatter(path.read_text(encoding="utf-8"))
        lessons.append(classify_lesson(path, root, meta, config, today))
    return lessons


def load_comparisons(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    if not path.is_file():
        raise TraceMemoryInputError(f"comparison file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise TraceMemoryInputError("comparison file schema_version must be 1")
    raw = data.get("comparisons")
    if not isinstance(raw, list):
        raise TraceMemoryInputError("comparison file must contain comparisons[]")
    comparisons: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise TraceMemoryInputError("comparison entries must be objects")
        baseline = float(item["baseline_score"])
        injected = float(item["injected_score"])
        status = "pass" if injected >= baseline else "fail"
        reason = "injected memory did not degrade scenario score" if status == "pass" else "injected memory degraded scenario score"
        comparisons.append(
            {
                "id": str(item["id"]),
                "lesson_id": str(item["lesson_id"]),
                "scenario_id": str(item["scenario_id"]),
                "baseline_score": baseline,
                "injected_score": injected,
                "status": status,
                "reason": reason,
                "trace_refs": _as_list(item.get("trace_refs")),
            }
        )
    return comparisons


def build_report(lesson_root: Path, comparison_file: Path | None, config_path: Path, today: date) -> dict[str, Any]:
    config = load_config(config_path)
    lessons = load_lessons(lesson_root, config, today)
    comparisons = load_comparisons(comparison_file)
    violations = sum(1 for lesson in lessons if lesson["status"] == "fail") + sum(1 for comp in comparisons if comp["status"] == "fail")
    warnings = sum(1 for lesson in lessons if lesson["status"] == "warn")
    return {
        "schema_version": 1,
        "status": "fail" if violations else "pass",
        "config": config,
        "summary": {
            "lessons": len(lessons),
            "comparisons": len(comparisons),
            "violations": violations,
            "warnings": warnings,
        },
        "lesson_root": str(lesson_root),
        "comparison_file": str(comparison_file) if comparison_file else None,
        "lessons": lessons,
        "comparisons": comparisons,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Athanor trace-memory quality gate.")
    parser.add_argument("--lesson-root", type=Path, default=DEFAULT_LESSON_ROOT)
    parser.add_argument("--comparison-file", type=Path, default=None)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--today", default=date.today().isoformat())
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    try:
        today = datetime.strptime(args.today, "%Y-%m-%d").date()
        report = build_report(args.lesson_root, args.comparison_file, args.config, today)
    except (OSError, KeyError, ValueError, json.JSONDecodeError, TraceMemoryInputError) as exc:
        print(f"trace-memory quality: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"{report['status']}: lessons={report['summary']['lessons']} violations={report['summary']['violations']}")
        for lesson in report["lessons"]:
            if lesson["status"] != "pass":
                print(f"  - {lesson['lesson_id']}: {lesson['action']} - {lesson['reason']}")
        for comparison in report["comparisons"]:
            if comparison["status"] != "pass":
                print(f"  - {comparison['id']}: {comparison['reason']}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Run focused tests and verify GREEN**

Run:

```powershell
python -m pytest tests\test_regression_trace_memory_quality.py -q
```

Expected: all tests pass.

- [ ] **Step 4: Run the committed fixture gate directly**

Run:

```powershell
python scripts\gates\trace_memory_quality.py --lesson-root tests\fixtures\trace_memory_quality\lessons --comparison-file tests\fixtures\trace_memory_quality\comparisons.json --today 2026-06-17 --json
```

Expected: JSON report with `status: "pass"`, 4 lessons, 1 comparison, 0
violations.

---

### Task 3: Document And Wire CI/Release Story

**Files:**
- Create: `docs/trace-memory-quality.md`
- Modify: `.github/workflows/validate-plugin.yml`
- Modify: `CHANGELOG.md`
- Modify: `tests/test_regression_v019_release_story.py`

- [ ] **Step 1: Create operator docs**

Create `docs/trace-memory-quality.md` with:

```markdown
# Trace-Memory Quality Gate

P17 adds a read-only gate for Athanor lesson memory. It verifies that promoted
or permanent lessons have trace/eval evidence, stale working lessons are visible
as decay candidates, harmful lessons are quarantined, and optional with/without
lesson comparison fixtures do not show degraded scenario scores.

## Run

```text
python scripts/gates/trace_memory_quality.py --json
```

For committed fixtures:

```text
python scripts/gates/trace_memory_quality.py \
  --lesson-root tests/fixtures/trace_memory_quality/lessons \
  --comparison-file tests/fixtures/trace_memory_quality/comparisons.json \
  --today 2026-06-17 \
  --json
```

## Lesson Evidence Fields

The gate recognizes these optional frontmatter fields:

- `trace_refs`
- `eval_refs`
- `evidence_refs`

Permanent lessons and promotion candidates need at least one evidence ref.

## Actions

- `keep`: lesson is within policy.
- `promote_candidate`: working lesson crossed the age/access threshold and has evidence.
- `decay`: stale low-access working lesson should be deleted by Cleaner.
- `quarantine`: degraded memory is explicitly isolated.
- `violation`: hard invariant failure.

## Hard Failures

The gate fails when:

- `importance: permanent` lacks evidence refs;
- a working lesson has enough `access_count` for promotion and lacks evidence refs;
- a harmful/degraded/regressed lesson is not quarantined;
- injected memory comparison score is lower than baseline.

The gate does not write lesson files and does not implement mem-search
persistence.
```

- [ ] **Step 2: Add CI gate**

In `.github/workflows/validate-plugin.yml`, add after the distribution smoke
gate:

```yaml
      - name: Trace-memory quality gate
        shell: bash
        run: python scripts/gates/trace_memory_quality.py --lesson-root tests/fixtures/trace_memory_quality/lessons --comparison-file tests/fixtures/trace_memory_quality/comparisons.json --today 2026-06-17 --json
```

- [ ] **Step 3: Add release-story tests**

Append to `tests/test_regression_v019_release_story.py`:

```python
def test_ci_runs_trace_memory_quality_gate():
    """P17 trace-memory quality should fail before broad pytest."""
    workflow = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
    assert "Trace-memory quality gate" in workflow
    assert "python scripts/gates/trace_memory_quality.py" in workflow
    assert "--lesson-root tests/fixtures/trace_memory_quality/lessons" in workflow
    assert "--comparison-file tests/fixtures/trace_memory_quality/comparisons.json" in workflow


def test_unreleased_documents_trace_memory_quality_gate():
    """The Unreleased story must name the P17 trace-memory quality gate."""
    section = _unreleased_section()
    required = [
        "Trace-memory quality gate",
        "scripts/gates/trace_memory_quality.py",
        "promotion",
        "decay",
        "quarantine",
        "with/without lesson",
    ]
    missing = [token for token in required if token not in section]
    assert not missing, (
        "CHANGELOG [Unreleased] must explain P17 trace-memory quality; "
        f"missing: {missing}"
    )
```

- [ ] **Step 4: Add changelog entry**

Under `CHANGELOG.md` `[Unreleased]`, add:

```markdown
- **Trace-memory quality gate.** `scripts/gates/trace_memory_quality.py`,
  `schemas/trace-memory-quality-report.schema.json`, and committed fixtures now
  make lesson promotion, stale decay, quarantine, and with/without lesson
  comparisons evidence-backed before memory can be treated as self-improving.
```

- [ ] **Step 5: Run focused docs/story tests**

Run:

```powershell
python -m pytest tests\test_regression_trace_memory_quality.py tests\test_regression_v019_release_story.py -q
```

Expected: all tests pass.

---

### Task 4: Align Learner/Cleaner Contracts

**Files:**
- Modify: `agents/learner.md`
- Modify: `skills/work/references/learner-cleaner.md`
- Modify: `tests/test_regression_memory_honesty.py`

- [ ] **Step 1: Update registered Learner lesson template**

In `agents/learner.md`, add optional evidence fields to the lesson frontmatter
template after `importance`:

```markdown
trace_refs: []
eval_refs: []
evidence_refs: []
```

Add this rule near the existing schema-key rule:

```markdown
- When a lesson is marked `importance: permanent` or is likely to be promoted
  by repeated access, include at least one `trace_refs`, `eval_refs`, or
  `evidence_refs` entry so `scripts/gates/trace_memory_quality.py` can verify
  the promotion is evidence-backed.
```

- [ ] **Step 2: Update inline Learner reference**

In `skills/work/references/learner-cleaner.md`, add the same optional evidence
fields to the lesson template and add the same rule after the dedup/update
access-count instructions.

- [ ] **Step 3: Extend memory honesty tests**

Append to `tests/test_regression_memory_honesty.py`:

```python
def test_learner_contract_mentions_trace_memory_quality_gate() -> None:
    """P17 — Learner must produce evidence refs for promoted memory."""
    body = (REPO_ROOT / "agents" / "learner.md").read_text(encoding="utf-8")
    for token in ("trace_refs", "eval_refs", "evidence_refs", "trace_memory_quality.py"):
        assert token in body


def test_work_learner_reference_mentions_trace_memory_quality_gate() -> None:
    """P17 — inline Learner prompt must stay aligned with registered Learner."""
    body = (REPO_ROOT / "skills" / "work" / "references" / "learner-cleaner.md").read_text(encoding="utf-8")
    for token in ("trace_refs", "eval_refs", "evidence_refs", "trace_memory_quality.py"):
        assert token in body
```

- [ ] **Step 4: Run focused memory tests**

Run:

```powershell
python -m pytest tests\test_regression_memory_honesty.py tests\test_regression_trace_memory_quality.py -q
```

Expected: all tests pass.

---

### Task 5: Verification And Commit

**Files:**
- All files touched in P17.

- [ ] **Step 1: Run focused P17 gate**

Run:

```powershell
python scripts\gates\trace_memory_quality.py --lesson-root tests\fixtures\trace_memory_quality\lessons --comparison-file tests\fixtures\trace_memory_quality\comparisons.json --today 2026-06-17 --json
```

Expected: `status` is `pass`.

- [ ] **Step 2: Run focused tests**

Run:

```powershell
python -m pytest tests\test_regression_trace_memory_quality.py tests\test_regression_memory_honesty.py tests\test_regression_v019_release_story.py -q
```

Expected: all tests pass.

- [ ] **Step 3: Run CI-equivalent gates touched by P17**

Run:

```powershell
python scripts\gates\distribution_smoke.py --json
python scripts\gates\runtime_conformance.py --json
python scripts\evals\run_workflow_scenarios.py --scenario-root tests\fixtures\workflow_evals --json
```

Expected: all pass.

- [ ] **Step 4: Run full tests**

Run:

```powershell
python -m pytest tests\ -q
```

Expected: all tests pass, with existing skips/xpasses unchanged.

- [ ] **Step 5: Run whitespace check**

Run:

```powershell
git diff --check
```

Expected: no output and exit 0.

- [ ] **Step 6: Commit P17**

Run:

```powershell
git add scripts/gates/trace_memory_quality.py schemas/trace-memory-quality-report.schema.json tests/fixtures/trace_memory_quality tests/test_regression_trace_memory_quality.py docs/trace-memory-quality.md docs/architecture/2026-06-17-p17-trace-memory-quality-design.md docs/architecture/2026-06-17-post-p16-workflow-loop-harness-deep-research.md docs/plans/2026-06-17-p17-trace-memory-quality-plan.md agents/learner.md skills/work/references/learner-cleaner.md tests/test_regression_memory_honesty.py tests/test_regression_v019_release_story.py .github/workflows/validate-plugin.yml CHANGELOG.md
git commit -m "feat: add trace memory quality gate"
```

Expected: commit succeeds.

---

## Self-Review Checklist

- Spec coverage: P17 design requirements map to Tasks 1-4.
- Placeholder scan: no TBD/TODO/deferred implementation placeholder.
- Type consistency: report field names match tests and schema.
- Scope: read-only gate only; no live lesson mutation or mem-search claim.
