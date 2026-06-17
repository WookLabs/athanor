"""Regression tests for the P8 hook installer apply mode."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.gates.hook_installer import build_hook_fingerprint

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


def _minimal_entry(command: str = "python3 demo.py") -> dict[str, object]:
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
        "description": "Demo hook for apply-mode tests.",
        "source_refs": ["tests/test_regression_hook_installer_apply.py"],
    }


def _minimal_catalog(entry: dict[str, object] | None = None) -> dict[str, object]:
    payload = _minimal_entry()
    if entry:
        payload.update(entry)
    return {"version": 1, "hooks": [payload]}


def _write_trust_state(path: Path, entry: dict[str, object], repo_root: Path) -> None:
    fingerprint = build_hook_fingerprint(entry, repo_root)
    _write_json(
        path,
        {
            "schema_version": 1,
            "trusted_hooks": {
                entry["id"]: {
                    "status": "trusted",
                    "command_hash": fingerprint["command_hash"],
                    "source_hashes": fingerprint["source_hashes"],
                    "reviewed_at": "2026-06-17T00:00:00Z",
                    "reviewer": "test",
                }
            },
        },
    )


def test_apply_trusted_would_add_hook_writes_settings_atomically(tmp_path: Path) -> None:
    catalog_path = tmp_path / "catalog.json"
    hooks_path = tmp_path / "hooks.json"
    settings_path = tmp_path / "nested" / ".claude" / "settings.json"
    trust_path = tmp_path / ".athanor" / "hook-installer-trust.json"
    entry = _minimal_entry()
    _write_json(catalog_path, {"version": 1, "hooks": [entry]})
    _write_json(hooks_path, {"hooks": {}})
    _write_trust_state(trust_path, entry, REPO_ROOT)

    result = _run_cli(
        "--mode",
        "apply",
        "--catalog",
        str(catalog_path),
        "--hooks",
        str(hooks_path),
        "--settings",
        str(settings_path),
        "--trust-state",
        str(trust_path),
        "--json",
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["mode"] == "apply"
    assert report["summary"]["applied"] == 1
    assert report["writes"] == [{"kind": "settings", "path": str(settings_path.resolve())}]
    action = report["actions"][0]
    assert action["status"] == "applied"
    assert action["trust_status"] == "trusted"
    assert settings_path.is_file()
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert settings["hooks"]["PreToolUse"] == [
        {"hooks": [{"type": "command", "command": "python3 demo.py"}]}
    ]
    assert list(settings_path.parent.glob("*.tmp")) == []


def test_apply_creates_backup_when_settings_file_exists(tmp_path: Path) -> None:
    catalog_path = tmp_path / "catalog.json"
    hooks_path = tmp_path / "hooks.json"
    settings_path = tmp_path / ".claude" / "settings.json"
    trust_path = tmp_path / ".athanor" / "hook-installer-trust.json"
    entry = _minimal_entry()
    _write_json(catalog_path, {"version": 1, "hooks": [entry]})
    _write_json(hooks_path, {"hooks": {}})
    _write_json(settings_path, {"theme": "dark"})
    before = settings_path.read_text(encoding="utf-8")
    _write_trust_state(trust_path, entry, REPO_ROOT)

    result = _run_cli(
        "--mode",
        "apply",
        "--catalog",
        str(catalog_path),
        "--hooks",
        str(hooks_path),
        "--settings",
        str(settings_path),
        "--trust-state",
        str(trust_path),
        "--json",
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    backup_writes = [item for item in report["writes"] if item["kind"] == "backup"]
    assert len(backup_writes) == 1
    backup_path = Path(backup_writes[0]["path"])
    assert backup_path.read_text(encoding="utf-8") == before
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert settings["theme"] == "dark"
    assert settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"] == "python3 demo.py"


def test_apply_blocks_capture_only_include_without_writing(tmp_path: Path) -> None:
    settings_path = tmp_path / ".claude" / "settings.json"

    result = _run_cli(
        "--mode",
        "apply",
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
    action = next(action for action in report["actions"] if action["id"] == "generic-payload-capture")
    assert action["status"] == "blocked"
    assert "capture-only" in action["reason"]
    assert report["writes"] == []
    assert not settings_path.exists()


def test_apply_blocks_untrusted_would_add_without_writing(tmp_path: Path) -> None:
    catalog_path = tmp_path / "catalog.json"
    hooks_path = tmp_path / "hooks.json"
    settings_path = tmp_path / ".claude" / "settings.json"
    _write_json(catalog_path, _minimal_catalog())
    _write_json(hooks_path, {"hooks": {}})

    result = _run_cli(
        "--mode",
        "apply",
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
    assert report["summary"]["blocked"] == 1
    action = report["actions"][0]
    assert action["status"] == "blocked"
    assert "trust" in action["reason"]
    assert report["writes"] == []
    assert not settings_path.exists()


def test_apply_existing_non_matching_event_hook_blocks_without_write(tmp_path: Path) -> None:
    catalog_path = tmp_path / "catalog.json"
    hooks_path = tmp_path / "hooks.json"
    settings_path = tmp_path / ".claude" / "settings.json"
    trust_path = tmp_path / ".athanor" / "hook-installer-trust.json"
    entry = _minimal_entry()
    _write_json(catalog_path, {"version": 1, "hooks": [entry]})
    _write_json(hooks_path, {"hooks": {}})
    _write_json(
        settings_path,
        {
            "hooks": {
                "PreToolUse": [
                    {"hooks": [{"type": "command", "command": "python3 user-hook.py"}]}
                ]
            }
        },
    )
    before = settings_path.read_text(encoding="utf-8")
    _write_trust_state(trust_path, entry, REPO_ROOT)

    result = _run_cli(
        "--mode",
        "apply",
        "--catalog",
        str(catalog_path),
        "--hooks",
        str(hooks_path),
        "--settings",
        str(settings_path),
        "--trust-state",
        str(trust_path),
        "--json",
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["summary"]["conflict"] == 1
    assert report["actions"][0]["status"] == "conflict"
    assert report["writes"] == []
    assert settings_path.read_text(encoding="utf-8") == before
