"""Regression tests for the P4 hook installer dry-run planner.

The planner is intentionally read-only. It previews hook settings changes,
records conflict/block reasons, and must never mutate user settings.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLI = REPO_ROOT / "scripts" / "gates" / "hook_install_dry_run.py"


def _run_cli(*args: str, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _minimal_catalog(entry: dict[str, object]) -> dict[str, object]:
    base = {
        "id": "demo-hook",
        "event": "PreToolUse",
        "matcher": "",
        "command": "python3 demo.py",
        "runtime_default": "enabled",
        "policy_mode": "warn",
        "evidence_level": "replay-gated",
        "performance_budget_ms": 100,
        "dependencies": ["python3"],
        "risk": "low",
        "description": "Demo hook for dry-run planner tests.",
        "source_refs": ["tests/test_regression_hook_install_dry_run.py"],
    }
    base.update(entry)
    return {"version": 1, "hooks": [base]}


def test_default_dry_run_reports_enabled_runtime_hooks_and_never_writes(tmp_path):
    settings_path = tmp_path / ".claude" / "settings.json"

    result = _run_cli(
        "--repo-root",
        str(REPO_ROOT),
        "--settings",
        str(settings_path),
        "--json",
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["schema_version"] == 2
    assert report["mode"] == "dry-run"
    assert report["writes"] == []
    assert not settings_path.exists()

    by_id = {action["id"]: action for action in report["actions"]}
    assert set(by_id) == {
        "pretool-dispatcher",
        "posttool-evidence-sniffer",
    }
    assert {action["status"] for action in by_id.values()} == {"already-present"}
    assert report["summary"]["already-present"] == 2
    assert report["summary"]["would-add"] == 0
    assert report["summary"]["blocked"] == 0
    assert report["summary"]["conflict"] == 0
    assert report["trust_state_path"].endswith(".athanor/hook-installer-trust.json") or report[
        "trust_state_path"
    ].endswith(".athanor\\hook-installer-trust.json")


def test_dry_run_report_schema_v2_includes_trust_fingerprint_fields(tmp_path):
    settings_path = tmp_path / ".claude" / "settings.json"

    result = _run_cli(
        "--repo-root",
        str(REPO_ROOT),
        "--settings",
        str(settings_path),
        "--json",
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["schema_version"] == 2
    assert report["mode"] == "dry-run"
    assert report["writes"] == []
    for action in report["actions"]:
        assert action["command_hash"].startswith("sha256:")
        assert action["trust_status"] in {
            "missing-source",
            "mismatch",
            "trusted",
            "untrusted",
        }
        assert isinstance(action["source_hashes"], list)
        assert isinstance(action["missing_sources"], list)


def test_capture_only_include_is_blocked_until_live_replay_evidence(tmp_path):
    settings_path = tmp_path / ".claude" / "settings.json"

    result = _run_cli(
        "--repo-root",
        str(REPO_ROOT),
        "--settings",
        str(settings_path),
        "--include",
        "generic-payload-capture",
        "--json",
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["schema_version"] == 2
    action = next(action for action in report["actions"] if action["id"] == "generic-payload-capture")
    assert action["status"] == "blocked"
    assert "capture-only" in action["reason"]
    assert "live-redacted" in action["reason"]
    assert report["writes"] == []
    assert not settings_path.exists()


def test_disabled_include_is_blocked_without_command_or_runtime_default(tmp_path):
    settings_path = tmp_path / ".claude" / "settings.json"

    result = _run_cli(
        "--repo-root",
        str(REPO_ROOT),
        "--settings",
        str(settings_path),
        "--include",
        "pretool-safety-pattern-corpus",
        "--json",
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["schema_version"] == 2
    action = next(
        action for action in report["actions"] if action["id"] == "pretool-safety-pattern-corpus"
    )
    assert action["status"] == "blocked"
    assert "disabled" in action["reason"]
    assert "command" in action["reason"]
    assert report["writes"] == []
    assert not settings_path.exists()


def test_would_add_when_enabled_hook_is_missing_from_runtime_and_settings(tmp_path):
    catalog_path = tmp_path / "catalog.json"
    hooks_path = tmp_path / "hooks.json"
    settings_path = tmp_path / ".claude" / "settings.json"
    _write_json(catalog_path, _minimal_catalog({}))
    _write_json(hooks_path, {"hooks": {}})

    result = _run_cli(
        "--catalog",
        str(catalog_path),
        "--hooks",
        str(hooks_path),
        "--settings",
        str(settings_path),
        "--json",
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["schema_version"] == 2
    assert report["writes"] == []
    assert not settings_path.exists()
    assert report["summary"]["would-add"] == 1
    action = report["actions"][0]
    assert action["status"] == "would-add"
    assert action["proposed_entry"] == {
        "hooks": [{"type": "command", "command": "python3 demo.py"}]
    }


def test_would_add_preserves_windows_command_override(tmp_path):
    catalog_path = tmp_path / "catalog.json"
    hooks_path = tmp_path / "hooks.json"
    settings_path = tmp_path / ".claude" / "settings.json"
    _write_json(
        catalog_path,
        _minimal_catalog(
            {
                "command_windows": "py -3 demo.py",
            }
        ),
    )
    _write_json(hooks_path, {"hooks": {}})

    result = _run_cli(
        "--catalog",
        str(catalog_path),
        "--hooks",
        str(hooks_path),
        "--settings",
        str(settings_path),
        "--json",
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    action = report["actions"][0]
    assert action["command_windows"] == "py -3 demo.py"
    assert action["proposed_entry"] == {
        "hooks": [
            {
                "type": "command",
                "command": "python3 demo.py",
                "command_windows": "py -3 demo.py",
            }
        ]
    }


def test_conflicting_existing_settings_hook_is_reported_without_clobber(tmp_path):
    catalog_path = tmp_path / "catalog.json"
    hooks_path = tmp_path / "hooks.json"
    settings_path = tmp_path / ".claude" / "settings.json"
    _write_json(catalog_path, _minimal_catalog({}))
    _write_json(hooks_path, {"hooks": {}})
    _write_json(
        settings_path,
        {
            "hooks": {
                "PreToolUse": [
                    {
                        "hooks": [
                            {"type": "command", "command": "python3 user-hook.py"},
                        ],
                    }
                ]
            }
        },
    )
    before = settings_path.read_text(encoding="utf-8")

    result = _run_cli(
        "--catalog",
        str(catalog_path),
        "--hooks",
        str(hooks_path),
        "--settings",
        str(settings_path),
        "--json",
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["schema_version"] == 2
    assert report["writes"] == []
    assert settings_path.read_text(encoding="utf-8") == before
    assert report["summary"]["conflict"] == 1
    action = report["actions"][0]
    assert action["status"] == "conflict"
    assert "existing hook entries" in action["reason"]
    assert action["existing_count"] == 1


def test_invalid_settings_json_fails_cleanly_and_does_not_rewrite(tmp_path):
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text("{not-json", encoding="utf-8")
    before = settings_path.read_text(encoding="utf-8")

    result = _run_cli(
        "--repo-root",
        str(REPO_ROOT),
        "--settings",
        str(settings_path),
        "--json",
    )

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["schema_version"] == 2
    assert report["status"] == "error"
    assert "settings is not valid JSON" in report["error"]
    assert report["writes"] == []
    assert settings_path.read_text(encoding="utf-8") == before


def test_human_summary_reports_status_counts_without_json(tmp_path):
    settings_path = tmp_path / ".claude" / "settings.json"

    result = _run_cli(
        "--repo-root",
        str(REPO_ROOT),
        "--settings",
        str(settings_path),
    )

    assert result.returncode == 0, result.stderr
    assert "Athanor hook install dry-run" in result.stdout
    assert "already-present: 2" in result.stdout
    assert "would-add: 0" in result.stdout
    assert "writes: 0" in result.stdout
    assert not settings_path.exists()
