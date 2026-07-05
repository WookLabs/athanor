#!/usr/bin/env python3
"""Check enabled hook runtimes against catalog performance budgets.

This is a CI/development gate. It measures hook process overhead with safe
fixture payloads and does not assert hook policy correctness.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.gates.replay_hook_fixtures import (
    _fixture_safety_errors,
    _load_index,
    _make_project,
    _materialize_payload,
)

DEFAULT_CATALOG = REPO_ROOT / "hooks" / "catalog.json"
DEFAULT_FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "hooks"
VALID_HOOK_EXIT_CODES = {0, 2}
MIN_MEASURED_SAMPLES = 3

# v0.24.3 (N1): enabled hooks are invoked through the portable launcher shim
# `sh run_hook.sh <target.py>` (see scripts/hooks/run_hook.sh). The gate
# budgets the TARGET hook script hermetically with the CI interpreter —
# routing through the shim would measure PATH-probe noise, not the hook.
# Any other command form (including a revert to bare `python3 …`) is
# fail-loud rejected so a drive-by rewrite goes red here AND in
# tests/test_regression_portable_hook_interpreter.py.
_SH_LAUNCHER_COMMAND = re.compile(
    r'^sh\s+"\$\{CLAUDE_PLUGIN_ROOT\}/scripts/hooks/run_hook\.sh"\s+'
    r'"\$\{CLAUDE_PLUGIN_ROOT\}/(?P<path>[^"]+)"$'
)


def _load_catalog(path: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not load hook catalog {path}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("hook catalog root must be a JSON object")
    hooks = parsed.get("hooks")
    if not isinstance(hooks, list):
        raise ValueError("hook catalog must contain hooks[]")
    return parsed


def _parse_override_budget(raw: list[str]) -> dict[str, int]:
    overrides: dict[str, int] = {}
    for item in raw:
        if "=" not in item:
            raise ValueError(f"invalid budget override {item!r}; expected hook-id=ms")
        hook_id, value = item.split("=", 1)
        if not hook_id:
            raise ValueError(f"invalid budget override {item!r}; missing hook id")
        try:
            budget = int(value)
        except ValueError as exc:
            raise ValueError(
                f"invalid budget override {item!r}; budget must be integer ms"
            ) from exc
        if budget < 0:
            raise ValueError(f"invalid budget override {item!r}; budget must be >= 0")
        overrides[hook_id] = budget
    return overrides


def _enabled_hooks(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    hooks = []
    for item in catalog["hooks"]:
        if isinstance(item, dict) and item.get("runtime_default") == "enabled":
            hooks.append(item)
    return hooks


def _select_fixtures(index: dict[str, Any], event: str) -> list[dict[str, Any]]:
    fixtures = [
        item
        for item in index["fixtures"]
        if isinstance(item, dict) and item.get("event") == event
    ]
    live = [item for item in fixtures if item.get("source_level") == "live-redacted"]
    if live:
        return live
    return [item for item in fixtures if item.get("source_level") == "synthetic"]


def _resolve_command(command: str) -> list[str]:
    match = _SH_LAUNCHER_COMMAND.match(command.strip())
    if not match:
        raise ValueError(
            "unsupported hook command form (expected "
            'sh "${CLAUDE_PLUGIN_ROOT}/scripts/hooks/run_hook.sh" '
            '"${CLAUDE_PLUGIN_ROOT}/<target.py>"): '
            f"{command!r}"
        )
    script = REPO_ROOT / match.group("path")
    if not script.is_file():
        raise ValueError(f"hook script does not exist: {script}")
    return [sys.executable, str(script)]


def _run_once(command: list[str], payload: dict[str, Any], hook_id: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix=f"athanor-hook-budget-{hook_id}-") as tmp:
        project, _session_dir = _make_project(Path(tmp), {"id": hook_id})
        materialized = _materialize_payload(payload, project)
        env = os.environ.copy()
        env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
        start = time.perf_counter()
        proc = subprocess.run(
            command,
            input=json.dumps(materialized),
            text=True,
            capture_output=True,
            cwd=str(project),
            env=env,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
    return {
        "duration_ms": elapsed_ms,
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def _measure_hook(
    *,
    hook: dict[str, Any],
    fixtures: list[dict[str, Any]],
    samples: int,
    overrides: dict[str, int],
) -> dict[str, Any]:
    hook_id = str(hook.get("id", "<missing-id>"))
    event = str(hook.get("event", "<missing-event>"))
    budget_ms = overrides.get(hook_id, hook.get("performance_budget_ms"))
    if not isinstance(budget_ms, int):
        return {
            "id": hook_id,
            "event": event,
            "budget_ms": budget_ms,
            "median_ms": None,
            "max_ms": None,
            "runs": [],
            "fixtures": [],
            "status": "fail",
            "reason": "missing integer performance_budget_ms",
        }
    if not fixtures:
        return {
            "id": hook_id,
            "event": event,
            "budget_ms": budget_ms,
            "median_ms": None,
            "max_ms": None,
            "runs": [],
            "fixtures": [],
            "status": "fail",
            "reason": "no safe fixture payload found for enabled hook event",
        }

    safety_errors: list[str] = []
    for fixture in fixtures:
        safety_errors.extend(_fixture_safety_errors(fixture))
    if safety_errors:
        return {
            "id": hook_id,
            "event": event,
            "budget_ms": budget_ms,
            "median_ms": None,
            "max_ms": None,
            "runs": [],
            "fixtures": [str(item.get("id", "<missing-id>")) for item in fixtures],
            "status": "fail",
            "reason": "; ".join(safety_errors),
        }

    try:
        command = _resolve_command(str(hook.get("command", "")))
    except ValueError as exc:
        return {
            "id": hook_id,
            "event": event,
            "budget_ms": budget_ms,
            "median_ms": None,
            "max_ms": None,
            "runs": [],
            "fixtures": [str(item.get("id", "<missing-id>")) for item in fixtures],
            "status": "fail",
            "reason": str(exc),
        }

    measured_samples = max(MIN_MEASURED_SAMPLES, samples)
    selected = fixtures[: max(1, min(measured_samples, len(fixtures)))]

    warmup_fixture = selected[0]
    warmup_payload = warmup_fixture.get("payload")
    if not isinstance(warmup_payload, dict):
        return {
            "id": hook_id,
            "event": event,
            "budget_ms": budget_ms,
            "median_ms": None,
            "max_ms": None,
            "runs": [],
            "fixtures": [str(item.get("id", "<missing-id>")) for item in selected],
            "status": "fail",
            "reason": "fixture payload must be a JSON object",
        }
    warmup = _run_once(command, warmup_payload, hook_id)
    if warmup["exit_code"] not in VALID_HOOK_EXIT_CODES:
        return {
            "id": hook_id,
            "event": event,
            "budget_ms": budget_ms,
            "median_ms": None,
            "max_ms": None,
            "runs": [],
            "fixtures": [str(item.get("id", "<missing-id>")) for item in selected],
            "status": "fail",
            "reason": f"warmup hook exited with unsupported code {warmup['exit_code']}",
        }

    runs: list[dict[str, Any]] = []
    for index in range(measured_samples):
        fixture = selected[index % len(selected)]
        payload = fixture.get("payload")
        if not isinstance(payload, dict):
            return {
                "id": hook_id,
                "event": event,
                "budget_ms": budget_ms,
                "median_ms": None,
                "max_ms": None,
                "runs": runs,
                "fixtures": [str(item.get("id", "<missing-id>")) for item in selected],
                "status": "fail",
                "reason": "fixture payload must be a JSON object",
            }
        actual = _run_once(command, payload, hook_id)
        runs.append(
            {
                "fixture_id": str(fixture.get("id", "<missing-id>")),
                "duration_ms": round(actual["duration_ms"], 3),
                "exit_code": actual["exit_code"],
            }
        )
        if actual["exit_code"] not in VALID_HOOK_EXIT_CODES:
            return {
                "id": hook_id,
                "event": event,
                "budget_ms": budget_ms,
                "median_ms": None,
                "max_ms": None,
                "runs": runs,
                "fixtures": [run["fixture_id"] for run in runs],
                "status": "fail",
                "reason": f"hook exited with unsupported code {actual['exit_code']}",
            }

    durations = [run["duration_ms"] for run in runs]
    median_ms = round(float(statistics.median(durations)), 3)
    max_ms = round(max(durations), 3)
    if median_ms > budget_ms:
        status = "fail"
        reason = f"median runtime {median_ms}ms exceeds budget {budget_ms}ms"
    else:
        status = "pass"
        reason = f"median runtime within budget; max observation {max_ms}ms"
    return {
        "id": hook_id,
        "event": event,
        "budget_ms": budget_ms,
        "median_ms": median_ms,
        "max_ms": max_ms,
        "runs": runs,
        "fixtures": [run["fixture_id"] for run in runs],
        "measured_samples": measured_samples,
        "status": status,
        "reason": reason,
    }


def check_budgets(
    *,
    catalog_path: Path,
    fixture_root: Path,
    samples: int,
    overrides: dict[str, int],
) -> dict[str, Any]:
    catalog = _load_catalog(catalog_path)
    index = _load_index(fixture_root)
    hooks = []
    for hook in _enabled_hooks(catalog):
        event = hook.get("event")
        if not isinstance(event, str):
            fixtures: list[dict[str, Any]] = []
        else:
            fixtures = _select_fixtures(index, event)
        hooks.append(
            _measure_hook(
                hook=hook,
                fixtures=fixtures,
                samples=samples,
                overrides=overrides,
            )
        )
    status = "pass" if all(item["status"] == "pass" for item in hooks) else "fail"
    return {
        "schema_version": 1,
        "status": status,
        "samples": samples,
        "catalog": str(catalog_path),
        "fixture_root": str(fixture_root),
        "hooks": hooks,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check hook performance budgets.")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--fixture-root", type=Path, default=DEFAULT_FIXTURE_ROOT)
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--json", action="store_true", help="Emit JSON report.")
    parser.add_argument(
        "--override-budget-ms",
        action="append",
        default=[],
        metavar="HOOK_ID=MS",
        help="Override one hook budget for testing.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    if args.samples < 1:
        print("hook performance budget: --samples must be >= 1", file=sys.stderr)
        return 1
    try:
        report = check_budgets(
            catalog_path=args.catalog,
            fixture_root=args.fixture_root,
            samples=args.samples,
            overrides=_parse_override_budget(args.override_budget_ms),
        )
    except ValueError as exc:
        print(f"hook performance budget: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for hook in report["hooks"]:
            print(
                f"{hook['status']}: {hook['id']} "
                f"median={hook['median_ms']}ms "
                f"max={hook['max_ms']}ms budget={hook['budget_ms']}ms"
            )
            if hook["status"] != "pass":
                print(f"  - {hook['reason']}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
