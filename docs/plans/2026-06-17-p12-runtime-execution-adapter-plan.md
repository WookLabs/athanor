# P12 Runtime Execution Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a read-only runtime execution adapter that recommends Athanor execution backends and isolation policies from normalized task-shape input.

**Architecture:** Add a stdlib-only gate script with an importable recommendation function, JSON schema, committed fixture cases, operator docs, CI wiring, and release-story tests. The adapter is contract-first: it never launches dynamic workflows, agent teams, subagents, or worktrees.

**Tech Stack:** Python standard library, pytest, jsonschema, existing Athanor gate/report conventions, GitHub Actions.

---

## File Structure

- Create: `scripts/gates/runtime_execution_adapter.py`
  - Defines `recommend_backend(request: dict[str, Any]) -> dict[str, Any]`.
  - Defines `evaluate_fixture_root(fixture_root: Path, generated_at: str | None = None) -> dict[str, Any]`.
  - Exposes direct request mode and fixture mode through CLI.
- Create: `schemas/runtime-execution-adapter-report.schema.json`
  - Defines fixture report structure and recommendation fields.
- Create: `tests/fixtures/runtime_execution/solo-small-patch.json`
- Create: `tests/fixtures/runtime_execution/subagent-wave-parallel.json`
- Create: `tests/fixtures/runtime_execution/dynamic-workflow-fanout.json`
- Create: `tests/fixtures/runtime_execution/manual-worktree-conflict.json`
- Create: `tests/fixtures/runtime_execution/agent-team-peer-coordination.json`
- Create: `tests/fixtures/runtime_execution/agent-team-fallback.json`
  - Each fixture has `id`, `request`, and `expect`.
- Create: `tests/test_regression_runtime_execution_adapter.py`
  - Covers schema, direct rules, fixture pass/fail, invalid input, and fallback warnings.
- Create: `docs/runtime-execution-adapter.md`
  - Documents CLI, report shape, backend semantics, and non-goals.
- Modify: `.github/workflows/validate-plugin.yml`
  - Adds named `Runtime execution adapter fixture gate`.
- Modify: `CHANGELOG.md`
  - Adds Unreleased P12 story.
- Modify: `tests/test_regression_v019_release_story.py`
  - Asserts CI and changelog mention P12.
- Modify: `docs/plans/2026-06-17-p12-runtime-execution-adapter-plan.md`
  - Check off steps as work lands.

---

## Task 1: Write Runtime Execution Adapter RED Tests

**Files:**
- Create: `tests/test_regression_runtime_execution_adapter.py`

- [x] **Step 1: Add failing regression tests**

Create `tests/test_regression_runtime_execution_adapter.py` with:

```python
"""Regression tests for the P12 runtime execution adapter."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "gates" / "runtime_execution_adapter.py"
SCHEMA = REPO_ROOT / "schemas" / "runtime-execution-adapter-report.schema.json"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "runtime_execution"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_module():
    spec = importlib.util.spec_from_file_location("runtime_execution_adapter", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_fixture_gate_emits_schema_valid_pass_report() -> None:
    proc = _run_cli("--fixture-root", str(FIXTURES), "--json")

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    jsonschema.validate(report, _load_json(SCHEMA))
    assert report["schema_version"] == 1
    assert report["status"] == "pass"
    assert report["summary"]["failed"] == 0
    assert report["summary"]["fixtures"] >= 6


def test_small_low_risk_patch_recommends_solo_current_checkout() -> None:
    module = _load_module()

    recommendation = module.recommend_backend(
        {
            "id": "unit-solo",
            "task": "Adjust one docs typo",
            "risk": "low",
            "estimated_files": 1,
            "parallel_workers": 0,
            "same_file_risk": "low",
            "long_running": False,
            "requires_isolation": False,
            "requires_peer_coordination": False,
            "requires_rerunnable_script": False,
            "requires_human_review": False,
        }
    )

    assert recommendation["recommended_backend"] == "solo"
    assert recommendation["isolation"] == "current-checkout"
    assert recommendation["confidence"] == "high"
    assert {reason["id"] for reason in recommendation["reasons"]} >= {
        "small-task",
        "low-conflict",
    }


def test_agent_team_unknown_falls_back_to_subagent_wave_with_warning() -> None:
    module = _load_module()

    recommendation = module.recommend_backend(
        {
            "id": "unit-agent-team-fallback",
            "task": "Have reviewers compare competing hypotheses",
            "risk": "medium",
            "estimated_files": 4,
            "parallel_workers": 3,
            "same_file_risk": "low",
            "long_running": False,
            "requires_isolation": False,
            "requires_peer_coordination": True,
            "requires_rerunnable_script": False,
            "requires_human_review": True,
            "capabilities": {"agent_team": "unknown", "subagent_wave": "available"},
        }
    )

    assert recommendation["recommended_backend"] == "subagent-wave"
    assert recommendation["fallback_backend"] == "agent-team"
    assert "agent-team-unknown" in {warning["id"] for warning in recommendation["warnings"]}
    assert "agent_team" in recommendation["blocked_capabilities"]


def test_fixture_mismatch_exits_one(tmp_path: Path) -> None:
    fixture_root = tmp_path / "fixtures"
    fixture_root.mkdir()
    (fixture_root / "bad.json").write_text(
        json.dumps(
            {
                "id": "bad",
                "request": {
                    "task": "Small patch",
                    "risk": "low",
                    "estimated_files": 1,
                    "parallel_workers": 0,
                    "same_file_risk": "low",
                    "long_running": False,
                    "requires_isolation": False,
                    "requires_peer_coordination": False,
                    "requires_rerunnable_script": False,
                    "requires_human_review": False,
                },
                "expect": {"recommended_backend": "agent-team"},
            }
        ),
        encoding="utf-8",
    )

    proc = _run_cli("--fixture-root", str(fixture_root), "--json")

    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert report["status"] == "fail"
    assert report["summary"]["failed"] == 1
    assert report["fixtures"][0]["status"] == "fail"


def test_invalid_request_exits_two(tmp_path: Path) -> None:
    request = tmp_path / "request.json"
    request.write_text(
        json.dumps(
            {
                "task": "Invalid risk",
                "risk": "severe",
                "estimated_files": 1,
                "parallel_workers": 0,
                "same_file_risk": "low",
                "long_running": False,
                "requires_isolation": False,
                "requires_peer_coordination": False,
                "requires_rerunnable_script": False,
                "requires_human_review": False,
            }
        ),
        encoding="utf-8",
    )

    proc = _run_cli("--request", str(request), "--json")

    assert proc.returncode == 2
    assert "unsupported risk" in proc.stderr
```

- [x] **Step 2: Run tests to verify RED**

Run:

```bash
python -m pytest tests/test_regression_runtime_execution_adapter.py -q
```

Expected:

- FAIL because `scripts/gates/runtime_execution_adapter.py`, schema, and
  fixtures do not exist.

- [x] **Step 3: Commit RED tests**

```bash
git add tests/test_regression_runtime_execution_adapter.py
git commit -m "test: cover runtime execution adapter"
```

---

## Task 2: Add Schema And Runtime Execution Fixtures

**Files:**
- Create: `schemas/runtime-execution-adapter-report.schema.json`
- Create: `tests/fixtures/runtime_execution/*.json`

- [x] **Step 1: Add report schema**

Create `schemas/runtime-execution-adapter-report.schema.json` with:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://wooklabs.github.io/athanor/schemas/runtime-execution-adapter-report.schema.json",
  "title": "Athanor Runtime Execution Adapter Report",
  "type": "object",
  "required": ["schema_version", "status", "summary", "generated_at", "fixtures"],
  "properties": {
    "schema_version": { "const": 1 },
    "status": { "enum": ["pass", "fail"] },
    "generated_at": { "type": "string" },
    "summary": {
      "type": "object",
      "required": ["fixtures", "passed", "failed"],
      "properties": {
        "fixtures": { "type": "integer", "minimum": 0 },
        "passed": { "type": "integer", "minimum": 0 },
        "failed": { "type": "integer", "minimum": 0 }
      },
      "additionalProperties": true
    },
    "fixtures": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "status", "recommendation"],
        "properties": {
          "id": { "type": "string" },
          "status": { "enum": ["pass", "fail"] },
          "recommendation": {
            "type": "object",
            "required": [
              "schema_version",
              "request_id",
              "recommended_backend",
              "isolation",
              "risk_level",
              "confidence",
              "reasons",
              "warnings",
              "required_capabilities",
              "blocked_capabilities",
              "notes"
            ],
            "properties": {
              "schema_version": { "const": 1 },
              "request_id": { "type": "string" },
              "recommended_backend": {
                "enum": [
                  "solo",
                  "subagent-wave",
                  "dynamic-workflow",
                  "agent-team",
                  "manual-worktree"
                ]
              },
              "fallback_backend": {
                "enum": [
                  "solo",
                  "subagent-wave",
                  "dynamic-workflow",
                  "agent-team",
                  "manual-worktree"
                ]
              },
              "isolation": {
                "enum": [
                  "current-checkout",
                  "worktree-recommended",
                  "worktree-required"
                ]
              },
              "risk_level": { "enum": ["low", "medium", "high"] },
              "confidence": { "enum": ["low", "medium", "high"] },
              "reasons": { "type": "array" },
              "warnings": { "type": "array" },
              "required_capabilities": { "type": "array" },
              "blocked_capabilities": { "type": "array" },
              "notes": { "type": "array" }
            },
            "additionalProperties": true
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true
}
```

- [x] **Step 2: Add committed fixtures**

Create these six files:

`tests/fixtures/runtime_execution/solo-small-patch.json`

```json
{
  "id": "solo-small-patch",
  "request": {
    "task": "Adjust one documentation typo",
    "risk": "low",
    "estimated_files": 1,
    "parallel_workers": 0,
    "same_file_risk": "low",
    "long_running": false,
    "requires_isolation": false,
    "requires_peer_coordination": false,
    "requires_rerunnable_script": false,
    "requires_human_review": false
  },
  "expect": {
    "recommended_backend": "solo",
    "isolation": "current-checkout",
    "reason_ids": ["small-task", "low-conflict"]
  }
}
```

`tests/fixtures/runtime_execution/subagent-wave-parallel.json`

```json
{
  "id": "subagent-wave-parallel",
  "request": {
    "task": "Review three independent modules and summarize findings",
    "risk": "medium",
    "estimated_files": 6,
    "parallel_workers": 3,
    "same_file_risk": "low",
    "long_running": false,
    "requires_isolation": false,
    "requires_peer_coordination": false,
    "requires_rerunnable_script": false,
    "requires_human_review": true,
    "capabilities": {
      "subagent_wave": "available"
    }
  },
  "expect": {
    "recommended_backend": "subagent-wave",
    "isolation": "current-checkout",
    "reason_ids": ["bounded-parallelism"]
  }
}
```

`tests/fixtures/runtime_execution/dynamic-workflow-fanout.json`

```json
{
  "id": "dynamic-workflow-fanout",
  "request": {
    "task": "Run a codebase-wide migration audit with reusable orchestration",
    "risk": "medium",
    "estimated_files": 45,
    "parallel_workers": 8,
    "same_file_risk": "low",
    "long_running": true,
    "requires_isolation": false,
    "requires_peer_coordination": false,
    "requires_rerunnable_script": true,
    "requires_human_review": true,
    "capabilities": {
      "dynamic_workflow": "available",
      "subagent_wave": "available"
    }
  },
  "expect": {
    "recommended_backend": "dynamic-workflow",
    "isolation": "current-checkout",
    "required_capabilities": ["dynamic_workflow"],
    "reason_ids": ["large-fanout", "rerunnable-script"]
  }
}
```

`tests/fixtures/runtime_execution/manual-worktree-conflict.json`

```json
{
  "id": "manual-worktree-conflict",
  "request": {
    "task": "Have several workers modify the same runtime files",
    "risk": "high",
    "estimated_files": 8,
    "parallel_workers": 4,
    "same_file_risk": "high",
    "long_running": false,
    "requires_isolation": true,
    "requires_peer_coordination": false,
    "requires_rerunnable_script": false,
    "requires_human_review": true,
    "capabilities": {
      "worktree": "manual",
      "subagent_wave": "available"
    }
  },
  "expect": {
    "recommended_backend": "manual-worktree",
    "isolation": "worktree-required",
    "reason_ids": ["same-file-conflict", "isolation-required"]
  }
}
```

`tests/fixtures/runtime_execution/agent-team-peer-coordination.json`

```json
{
  "id": "agent-team-peer-coordination",
  "request": {
    "task": "Coordinate frontend, backend, and verification teammates on a feature review",
    "risk": "medium",
    "estimated_files": 9,
    "parallel_workers": 3,
    "same_file_risk": "low",
    "long_running": false,
    "requires_isolation": false,
    "requires_peer_coordination": true,
    "requires_rerunnable_script": false,
    "requires_human_review": true,
    "capabilities": {
      "agent_team": "available",
      "subagent_wave": "available"
    }
  },
  "expect": {
    "recommended_backend": "agent-team",
    "isolation": "current-checkout",
    "required_capabilities": ["agent_team"],
    "reason_ids": ["peer-coordination"]
  }
}
```

`tests/fixtures/runtime_execution/agent-team-fallback.json`

```json
{
  "id": "agent-team-fallback",
  "request": {
    "task": "Compare competing debugging hypotheses with independent reviewers",
    "risk": "medium",
    "estimated_files": 4,
    "parallel_workers": 3,
    "same_file_risk": "low",
    "long_running": false,
    "requires_isolation": false,
    "requires_peer_coordination": true,
    "requires_rerunnable_script": false,
    "requires_human_review": true,
    "capabilities": {
      "agent_team": "unknown",
      "subagent_wave": "available"
    }
  },
  "expect": {
    "recommended_backend": "subagent-wave",
    "fallback_backend": "agent-team",
    "isolation": "current-checkout",
    "warning_ids": ["agent-team-unknown"],
    "blocked_capabilities": ["agent_team"]
  }
}
```

- [x] **Step 3: Commit schema and fixtures**

```bash
git add schemas/runtime-execution-adapter-report.schema.json tests/fixtures/runtime_execution
git commit -m "test: add runtime adapter fixtures"
```

---

## Task 3: Implement Runtime Execution Adapter

**Files:**
- Create: `scripts/gates/runtime_execution_adapter.py`

- [x] **Step 1: Implement adapter script**

Create `scripts/gates/runtime_execution_adapter.py` with:

```python
#!/usr/bin/env python3
"""Read-only runtime execution backend recommendation gate for Athanor."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BACKENDS = {"solo", "subagent-wave", "dynamic-workflow", "agent-team", "manual-worktree"}
ISOLATION = {"current-checkout", "worktree-recommended", "worktree-required"}
RISK = {"low", "medium", "high"}
CAPABILITY = {"available", "unavailable", "unknown"}
WORKTREE_CAPABILITY = {"available", "unavailable", "manual", "unknown"}

DEFAULT_CAPABILITIES = {
    "subagent_wave": "available",
    "dynamic_workflow": "unknown",
    "agent_team": "unknown",
    "worktree": "manual",
}


class AdapterInputError(Exception):
    """Raised when an adapter request or fixture is invalid."""


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise AdapterInputError(f"{label} not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AdapterInputError(f"{label} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise AdapterInputError(f"{label} must be a JSON object")
    return data
```

Continue the file with:

```python
def _bool(value: Any, field: str) -> bool:
    if isinstance(value, bool):
        return value
    raise AdapterInputError(f"{field} must be a boolean")


def _int(value: Any, field: str) -> int:
    if isinstance(value, int) and value >= 0:
        return value
    raise AdapterInputError(f"{field} must be a non-negative integer")


def _enum(value: Any, field: str, allowed: set[str]) -> str:
    if isinstance(value, str) and value in allowed:
        return value
    raise AdapterInputError(f"unsupported {field}: {value!r}")


def _capabilities(raw: Any) -> dict[str, str]:
    result = dict(DEFAULT_CAPABILITIES)
    if raw is None:
        return result
    if not isinstance(raw, dict):
        raise AdapterInputError("capabilities must be an object")
    for key, value in raw.items():
        if key not in DEFAULT_CAPABILITIES:
            raise AdapterInputError(f"unsupported capability: {key}")
        allowed = WORKTREE_CAPABILITY if key == "worktree" else CAPABILITY
        result[key] = _enum(value, key, allowed)
    return result


def _normalize_request(raw: dict[str, Any]) -> dict[str, Any]:
    task = raw.get("task", "")
    if not isinstance(task, str) or not task.strip():
        raise AdapterInputError("task must be a non-empty string")
    request_id = raw.get("id", "request")
    if not isinstance(request_id, str) or not request_id.strip():
        raise AdapterInputError("id must be a non-empty string when provided")
    return {
        "id": request_id,
        "task": task,
        "risk": _enum(raw.get("risk", "medium"), "risk", RISK),
        "estimated_files": _int(raw.get("estimated_files", 0), "estimated_files"),
        "parallel_workers": _int(raw.get("parallel_workers", 0), "parallel_workers"),
        "same_file_risk": _enum(raw.get("same_file_risk", "low"), "same_file_risk", RISK),
        "long_running": _bool(raw.get("long_running", False), "long_running"),
        "requires_isolation": _bool(raw.get("requires_isolation", False), "requires_isolation"),
        "requires_peer_coordination": _bool(raw.get("requires_peer_coordination", False), "requires_peer_coordination"),
        "requires_rerunnable_script": _bool(raw.get("requires_rerunnable_script", False), "requires_rerunnable_script"),
        "requires_human_review": _bool(raw.get("requires_human_review", False), "requires_human_review"),
        "capabilities": _capabilities(raw.get("capabilities")),
    }
```

Then add helper and recommendation logic:

```python
def _reason(items: list[dict[str, str]], reason_id: str, message: str) -> None:
    items.append({"id": reason_id, "message": message})


def _warning(items: list[dict[str, str]], warning_id: str, message: str) -> None:
    items.append({"id": warning_id, "message": message})


def _dynamic_shape(request: dict[str, Any]) -> bool:
    return (
        request["parallel_workers"] >= 4
        or request["estimated_files"] >= 20
        or request["long_running"]
        or request["requires_rerunnable_script"]
    )


def _isolation(request: dict[str, Any]) -> str:
    if request["requires_isolation"] or request["same_file_risk"] == "high":
        return "worktree-required"
    if request["risk"] == "high" or request["same_file_risk"] == "medium":
        return "worktree-recommended"
    return "current-checkout"


def _base_result(request: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "request_id": request["id"],
        "recommended_backend": "solo",
        "isolation": _isolation(request),
        "risk_level": request["risk"],
        "confidence": "medium",
        "reasons": [],
        "warnings": [],
        "required_capabilities": [],
        "blocked_capabilities": [],
        "notes": [],
    }
```

Add `recommend_backend`:

```python
def recommend_backend(raw_request: dict[str, Any]) -> dict[str, Any]:
    request = _normalize_request(raw_request)
    caps = request["capabilities"]
    result = _base_result(request)
    reasons = result["reasons"]
    warnings = result["warnings"]
    required = result["required_capabilities"]
    blocked = result["blocked_capabilities"]

    if request["estimated_files"] <= 2 and request["parallel_workers"] <= 1:
        _reason(reasons, "small-task", "Task is small enough for one focused session.")
    if request["same_file_risk"] == "low":
        _reason(reasons, "low-conflict", "Same-file conflict risk is low.")
    if request["requires_isolation"] or request["same_file_risk"] == "high":
        _reason(reasons, "isolation-required", "Task shape requires isolated filesystem changes.")
    if request["same_file_risk"] == "high":
        _reason(reasons, "same-file-conflict", "High same-file risk should not be handled by generic parallel workers.")

    if result["isolation"] == "worktree-required" and caps["worktree"] in {"manual", "unknown", "unavailable"}:
        result["recommended_backend"] = "manual-worktree"
        result["confidence"] = "high" if caps["worktree"] == "manual" else "medium"
        if caps["worktree"] == "unavailable":
            _warning(warnings, "worktree-unavailable", "Worktree isolation is required but unavailable.")
            blocked.append("worktree")
        return result

    if request["requires_peer_coordination"]:
        _reason(reasons, "peer-coordination", "Workers need peer coordination, not only summarized reports.")
        if caps["agent_team"] == "available":
            result["recommended_backend"] = "agent-team"
            result["confidence"] = "high"
            required.append("agent_team")
            return result
        result["recommended_backend"] = "subagent-wave" if caps["subagent_wave"] == "available" else "solo"
        result["fallback_backend"] = "agent-team"
        result["confidence"] = "medium"
        _warning(warnings, "agent-team-unknown", "Agent team capability is not confirmed; using a conservative fallback.")
        blocked.append("agent_team")
        return result

    if _dynamic_shape(request):
        if request["parallel_workers"] >= 4:
            _reason(reasons, "large-fanout", "Task shape needs more fanout than a small worker wave.")
        if request["requires_rerunnable_script"]:
            _reason(reasons, "rerunnable-script", "Task asks for reusable orchestration.")
        if caps["dynamic_workflow"] == "available":
            result["recommended_backend"] = "dynamic-workflow"
            result["confidence"] = "high"
            required.append("dynamic_workflow")
            return result
        result["recommended_backend"] = "subagent-wave" if caps["subagent_wave"] == "available" else "solo"
        result["fallback_backend"] = "dynamic-workflow"
        result["confidence"] = "medium"
        _warning(warnings, "dynamic-workflow-unknown", "Dynamic workflow capability is not confirmed; using a conservative fallback.")
        blocked.append("dynamic_workflow")
        return result

    if request["parallel_workers"] >= 2:
        _reason(reasons, "bounded-parallelism", "Task can be split into a bounded worker wave.")
        if caps["subagent_wave"] == "available":
            result["recommended_backend"] = "subagent-wave"
            result["confidence"] = "high"
            required.append("subagent_wave")
            return result
        _warning(warnings, "subagent-wave-unavailable", "Subagent wave capability is unavailable; using solo execution.")
        blocked.append("subagent_wave")

    result["recommended_backend"] = "solo"
    result["confidence"] = "high" if result["isolation"] == "current-checkout" else "medium"
    return result
```

Add fixture evaluation and CLI:

```python
def _expectation_failures(recommendation: dict[str, Any], expect: dict[str, Any]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    reason_ids = {item["id"] for item in recommendation["reasons"]}
    warning_ids = {item["id"] for item in recommendation["warnings"]}
    for key in ("recommended_backend", "fallback_backend", "isolation"):
        if key in expect and recommendation.get(key) != expect[key]:
            failures.append({"field": key, "expected": expect[key], "actual": recommendation.get(key)})
    for key in ("required_capabilities", "blocked_capabilities"):
        if key in expect and sorted(recommendation.get(key, [])) != sorted(expect[key]):
            failures.append({"field": key, "expected": sorted(expect[key]), "actual": sorted(recommendation.get(key, []))})
    for key, values, actual in (
        ("reason_ids", expect.get("reason_ids", []), reason_ids),
        ("warning_ids", expect.get("warning_ids", []), warning_ids),
    ):
        missing = [value for value in values if value not in actual]
        if missing:
            failures.append({"field": key, "missing": missing, "actual": sorted(actual)})
    return failures


def evaluate_fixture_root(fixture_root: Path, generated_at: str | None = None) -> dict[str, Any]:
    files = sorted(fixture_root.glob("*.json"))
    if not files:
        raise AdapterInputError(f"no runtime execution fixtures found: {fixture_root}")
    items: list[dict[str, Any]] = []
    for path in files:
        fixture = _read_json(path, "runtime execution fixture")
        if "request" not in fixture or "expect" not in fixture:
            raise AdapterInputError(f"fixture must contain request and expect: {path}")
        fixture_id = str(fixture.get("id", path.stem))
        recommendation = recommend_backend(fixture["request"])
        failures = _expectation_failures(recommendation, fixture["expect"])
        item = {
            "id": fixture_id,
            "path": path.as_posix(),
            "status": "pass" if not failures else "fail",
            "recommendation": recommendation,
        }
        if failures:
            item["failures"] = failures
        items.append(item)
    failed = sum(1 for item in items if item["status"] == "fail")
    return {
        "schema_version": 1,
        "status": "fail" if failed else "pass",
        "summary": {"fixtures": len(items), "passed": len(items) - failed, "failed": failed},
        "generated_at": generated_at or _iso_now(),
        "fixtures": items,
    }
```

Finish with CLI:

```python
def _request_from_args(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "id": args.id,
        "task": args.task,
        "risk": args.risk,
        "estimated_files": args.estimated_files,
        "parallel_workers": args.parallel_workers,
        "same_file_risk": args.same_file_risk,
        "long_running": args.long_running,
        "requires_isolation": args.requires_isolation,
        "requires_peer_coordination": args.requires_peer_coordination,
        "requires_rerunnable_script": args.requires_rerunnable_script,
        "requires_human_review": args.requires_human_review,
        "capabilities": {
            "subagent_wave": args.subagent_wave,
            "dynamic_workflow": args.dynamic_workflow,
            "agent_team": args.agent_team,
            "worktree": args.worktree,
        },
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recommend an Athanor runtime execution backend.")
    parser.add_argument("--fixture-root", type=Path)
    parser.add_argument("--request", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--id", default="request")
    parser.add_argument("--task", default="Ad hoc Athanor task")
    parser.add_argument("--risk", default="medium")
    parser.add_argument("--estimated-files", type=int, default=0)
    parser.add_argument("--parallel-workers", type=int, default=0)
    parser.add_argument("--same-file-risk", default="low")
    parser.add_argument("--long-running", action="store_true")
    parser.add_argument("--requires-isolation", action="store_true")
    parser.add_argument("--requires-peer-coordination", action="store_true")
    parser.add_argument("--requires-rerunnable-script", action="store_true")
    parser.add_argument("--requires-human-review", action="store_true")
    parser.add_argument("--subagent-wave", default="available")
    parser.add_argument("--dynamic-workflow", default="unknown")
    parser.add_argument("--agent-team", default="unknown")
    parser.add_argument("--worktree", default="manual")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    try:
        if args.fixture_root:
            report = evaluate_fixture_root(args.fixture_root)
            if args.json:
                print(json.dumps(report, indent=2, sort_keys=True))
            else:
                print(
                    "runtime-adapter "
                    f"status={report['status']} "
                    f"fixtures={report['summary']['fixtures']} "
                    f"failed={report['summary']['failed']}"
                )
            return 0 if report["status"] == "pass" else 1

        request = _read_json(args.request, "runtime adapter request") if args.request else _request_from_args(args)
        recommendation = recommend_backend(request)
    except AdapterInputError as exc:
        print(f"runtime execution adapter: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(recommendation, indent=2, sort_keys=True))
    else:
        print(
            "runtime-adapter "
            f"backend={recommendation['recommended_backend']} "
            f"isolation={recommendation['isolation']} "
            f"confidence={recommendation['confidence']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [x] **Step 2: Run GREEN verification for adapter tests**

Run:

```bash
python -m pytest tests/test_regression_runtime_execution_adapter.py -q
```

Expected:

- PASS.

- [x] **Step 3: Run fixture gate directly**

Run:

```bash
python scripts/gates/runtime_execution_adapter.py --fixture-root tests/fixtures/runtime_execution --json
```

Expected:

- Exit `0`.
- JSON report has `status: pass`.
- `summary.failed` is `0`.

- [x] **Step 4: Commit implementation**

```bash
git add scripts/gates/runtime_execution_adapter.py schemas/runtime-execution-adapter-report.schema.json tests/fixtures/runtime_execution tests/test_regression_runtime_execution_adapter.py
git commit -m "feat: recommend runtime execution backends"
```

---

## Task 4: Wire P12 Into Docs, CI, And Release Story

**Files:**
- Create: `docs/runtime-execution-adapter.md`
- Modify: `.github/workflows/validate-plugin.yml`
- Modify: `CHANGELOG.md`
- Modify: `tests/test_regression_v019_release_story.py`

- [x] **Step 1: Add failing release-story tests**

Append to `tests/test_regression_v019_release_story.py`:

```python
def test_ci_runs_runtime_execution_adapter_fixture_gate():
    """P12 runtime backend routing should be checked before broad pytest."""
    workflow = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
    assert "Runtime execution adapter fixture gate" in workflow
    assert "python scripts/gates/runtime_execution_adapter.py" in workflow
    assert "--fixture-root tests/fixtures/runtime_execution --json" in workflow


def test_unreleased_documents_runtime_execution_adapter():
    """The Unreleased story must name the P12 runtime execution adapter."""
    section = _unreleased_section()
    required = [
        "Runtime execution adapter",
        "scripts/gates/runtime_execution_adapter.py",
        "dynamic workflow",
        "agent team",
        "worktree",
        "read-only",
    ]
    missing = [token for token in required if token not in section]
    assert not missing, (
        "CHANGELOG [Unreleased] must explain P12 runtime execution adapter; "
        f"missing: {missing}"
    )
```

- [x] **Step 2: Run release-story tests to verify RED**

Run:

```bash
python -m pytest tests/test_regression_v019_release_story.py -q
```

Expected:

- FAIL because docs/CI/changelog are not wired yet.

- [x] **Step 3: Add operator docs**

Create `docs/runtime-execution-adapter.md` with:

```markdown
# Runtime Execution Adapter

P12 adds a read-only runtime backend recommendation layer for Athanor.

Run the fixture gate:

```bash
python scripts/gates/runtime_execution_adapter.py --fixture-root tests/fixtures/runtime_execution --json
```

Run one direct recommendation:

```bash
python scripts/gates/runtime_execution_adapter.py \
  --task "Review three independent modules" \
  --risk medium \
  --estimated-files 6 \
  --parallel-workers 3 \
  --same-file-risk low \
  --json
```

Backends:

- `solo`: one focused session in the current checkout.
- `subagent-wave`: bounded parallel workers reporting to one lead.
- `dynamic-workflow`: large or rerunnable fanout when the capability is available.
- `agent-team`: peer-coordinated Claude Code sessions when explicitly available.
- `manual-worktree`: isolated manual workspace path for high conflict or required isolation.

The adapter does not launch dynamic workflows, spawn agent teams, create
worktrees, mutate settings, or export telemetry. It emits a decision contract
that future live command flows can consume.
```

- [x] **Step 4: Add CI gate**

In `.github/workflows/validate-plugin.yml`, after the Entropy cleanup report
gate, add:

```yaml
      - name: Runtime execution adapter fixture gate
        shell: bash
        run: python scripts/gates/runtime_execution_adapter.py --fixture-root tests/fixtures/runtime_execution --json
```

- [x] **Step 5: Add changelog story**

In `CHANGELOG.md` under `[Unreleased]`, add:

```markdown
- **Runtime execution adapter.** Adds read-only
  `scripts/gates/runtime_execution_adapter.py` plus fixture coverage to
  recommend `solo`, `subagent-wave`, `dynamic-workflow`, `agent-team`, or
  `manual-worktree` backends before future live orchestration work launches
  dynamic workflow, agent team, or worktree surfaces.
```

- [x] **Step 6: Run docs/release GREEN verification**

Run:

```bash
python -m pytest tests/test_regression_v019_release_story.py tests/test_regression_runtime_execution_adapter.py -q
```

Expected:

- PASS.

- [x] **Step 7: Commit docs and CI wiring**

```bash
git add docs/runtime-execution-adapter.md .github/workflows/validate-plugin.yml CHANGELOG.md tests/test_regression_v019_release_story.py
git commit -m "docs: wire runtime execution adapter gate"
```

---

## Task 5: Final Verification And Merge

**Files:**
- Modify: `docs/plans/2026-06-17-p12-runtime-execution-adapter-plan.md`

- [x] **Step 1: Run focused verification**

```bash
python -m pytest tests/test_regression_runtime_execution_adapter.py tests/test_regression_runtime_conformance.py tests/test_regression_v019_release_story.py -q
python scripts/gates/runtime_execution_adapter.py --fixture-root tests/fixtures/runtime_execution --json
python scripts/gates/runtime_conformance.py --json
python scripts/gates/entropy_cleanup.py --json --ref-warn-days 99999
git diff --check
```

Expected:

- Pytest PASS.
- Runtime execution adapter fixture gate exits `0`.
- Runtime conformance exits `0`.
- Entropy cleanup with relaxed refs exits `0`.
- `git diff --check` exits `0`.

- [x] **Step 2: Run full regression suite**

```bash
python -m pytest tests\ -q
```

Expected:

- PASS with the existing skip/xpass profile.

- [x] **Step 3: Mark verification steps complete and commit**

```bash
git add docs/plans/2026-06-17-p12-runtime-execution-adapter-plan.md
git commit -m "docs: record runtime execution adapter verification"
```

- [ ] **Step 4: Fast-forward merge to main and push**

```bash
git checkout main
git pull --ff-only origin main
git merge --ff-only feat/p12-runtime-execution-adapter
python -m pytest tests\ -q
python scripts/gates/runtime_execution_adapter.py --fixture-root tests/fixtures/runtime_execution --json
git diff --check
git push origin main
```

- [ ] **Step 5: Mark merge complete, commit, push, and delete feature branch**

```bash
git add docs/plans/2026-06-17-p12-runtime-execution-adapter-plan.md
git commit -m "docs: mark p12 merge complete"
git push origin main
git branch --delete feat/p12-runtime-execution-adapter
```

---

## Self-Review

- Spec coverage: tasks cover the P12 design doc, read-only adapter, schema,
  fixtures, tests, docs, CI, release story, verification, and merge.
- Placeholder scan: no `TBD`, `TODO`, or unstated implementation steps remain.
- Type consistency: backend, isolation, risk, and capability enums match the
  design doc and tests.
- Scope control: dynamic workflow launching, agent team spawning, worktree
  creation, settings mutation, external telemetry, and command-level trace
  emission stay out of scope.
