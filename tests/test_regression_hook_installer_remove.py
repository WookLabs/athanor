"""Regression tests for the P8 hook installer remove mode."""

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


def _entry(command: str = "python3 demo.py") -> dict[str, object]:
    return {
        "id": "demo-hook",
        "event": "PreToolUse",
        "matcher": "",
        "command": command,
        "runtime_default": "enabled",
        "policy_mode": "warn",
        "evidence_level": "replay-gated",
        "performance_budget_ms": 100,
        "dependencies": ["python3"],
        "risk": "low",
        "description": "Demo hook for remove-mode tests.",
        "source_refs": ["tests/test_regression_hook_installer_remove.py"],
    }


def _catalog(entry: dict[str, object] | None = None) -> dict[str, object]:
    payload = _entry()
    if entry:
        payload.update(entry)
    return {"version": 1, "hooks": [payload]}


def test_remove_deletes_exact_athanor_hook_and_preserves_unrelated_same_event(tmp_path: Path) -> None:
    catalog_path = tmp_path / "catalog.json"
    hooks_path = tmp_path / "hooks.json"
    settings_path = tmp_path / ".claude" / "settings.json"
    _write_json(catalog_path, _catalog())
    _write_json(hooks_path, {"hooks": {}})
    _write_json(
        settings_path,
        {
            "theme": "dark",
            "hooks": {
                "PreToolUse": [
                    {
                        "hooks": [
                            {"type": "command", "command": "python3 demo.py"},
                            {"type": "command", "command": "python3 user-hook.py"},
                        ]
                    }
                ]
            },
        },
    )

    result = _run_cli(
        "--mode",
        "remove",
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
    assert report["mode"] == "remove"
    assert report["summary"]["removed"] == 1
    assert report["actions"][0]["status"] == "removed"
    assert report["actions"][0]["removed_count"] == 1
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert settings["theme"] == "dark"
    assert settings["hooks"]["PreToolUse"] == [
        {"hooks": [{"type": "command", "command": "python3 user-hook.py"}]}
    ]


def test_remove_drops_empty_event_array_and_creates_backup(tmp_path: Path) -> None:
    catalog_path = tmp_path / "catalog.json"
    hooks_path = tmp_path / "hooks.json"
    settings_path = tmp_path / ".claude" / "settings.json"
    _write_json(catalog_path, _catalog())
    _write_json(hooks_path, {"hooks": {}})
    _write_json(
        settings_path,
        {
            "hooks": {
                "PreToolUse": [
                    {"hooks": [{"type": "command", "command": "python3 demo.py"}]}
                ]
            }
        },
    )
    before = settings_path.read_text(encoding="utf-8")

    result = _run_cli(
        "--mode",
        "remove",
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
    assert report["summary"]["removed"] == 1
    backup_writes = [item for item in report["writes"] if item["kind"] == "backup"]
    assert len(backup_writes) == 1
    assert Path(backup_writes[0]["path"]).read_text(encoding="utf-8") == before
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert "PreToolUse" not in settings["hooks"]


def test_remove_noop_reports_already_absent_without_writing(tmp_path: Path) -> None:
    catalog_path = tmp_path / "catalog.json"
    hooks_path = tmp_path / "hooks.json"
    settings_path = tmp_path / ".claude" / "settings.json"
    _write_json(catalog_path, _catalog())
    _write_json(hooks_path, {"hooks": {}})

    result = _run_cli(
        "--mode",
        "remove",
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
    assert report["summary"]["already-absent"] == 1
    assert report["actions"][0]["status"] == "already-absent"
    assert report["writes"] == []
    assert not settings_path.exists()


def test_remove_invalid_settings_json_exits_without_write(tmp_path: Path) -> None:
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text("{not-json", encoding="utf-8")
    before = settings_path.read_text(encoding="utf-8")

    result = _run_cli(
        "--mode",
        "remove",
        "--repo-root",
        str(REPO_ROOT),
        "--settings",
        str(settings_path),
        "--json",
    )

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["mode"] == "remove"
    assert report["status"] == "error"
    assert "settings is not valid JSON" in report["error"]
    assert report["writes"] == []
    assert settings_path.read_text(encoding="utf-8") == before
