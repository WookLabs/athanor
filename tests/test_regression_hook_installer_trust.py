"""Regression tests for the P8 hook installer trust model."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.gates.hook_installer import (
    HookInstallerTrustError,
    build_hook_fingerprint,
    load_trust_state,
    trust_status,
)


def _entry(command: str = 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/hooks/demo.py"') -> dict[str, object]:
    return {
        "id": "demo-hook",
        "event": "PreToolUse",
        "matcher": "",
        "command": command,
        "runtime_default": "enabled",
        "policy_mode": "warn",
        "evidence_level": "replay-gated",
    }


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_command_hash_is_sha256_prefixed_and_stable(tmp_path: Path) -> None:
    entry = _entry("python3 demo.py")

    fingerprint = build_hook_fingerprint(entry, tmp_path)

    expected = hashlib.sha256(b"python3 demo.py").hexdigest()
    assert fingerprint["command_hash"] == f"sha256:{expected}"
    assert fingerprint["source_hashes"] == []
    assert fingerprint["missing_sources"] == []


def test_claude_plugin_root_source_path_is_resolved_and_hashed(tmp_path: Path) -> None:
    source = tmp_path / "scripts" / "hooks" / "demo.py"
    source.parent.mkdir(parents=True)
    source.write_text("print('demo')\n", encoding="utf-8")

    fingerprint = build_hook_fingerprint(_entry(), tmp_path)

    expected = hashlib.sha256(source.read_bytes()).hexdigest()
    assert fingerprint["source_hashes"] == [
        {
            "path": "scripts/hooks/demo.py",
            "sha256": f"sha256:{expected}",
        }
    ]
    assert fingerprint["missing_sources"] == []


def test_missing_source_file_is_reported(tmp_path: Path) -> None:
    fingerprint = build_hook_fingerprint(_entry(), tmp_path)

    assert fingerprint["source_hashes"] == []
    assert fingerprint["missing_sources"] == ["scripts/hooks/demo.py"]


def test_windows_command_participates_in_trust_fingerprint(tmp_path: Path) -> None:
    for rel_path in (
        "scripts/hooks/run_hook.sh",
        "scripts/hooks/run_hook.cmd",
        "scripts/hooks/demo.py",
    ):
        path = tmp_path.joinpath(*rel_path.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{rel_path}\n", encoding="utf-8")
    entry = _entry(
        'sh "${CLAUDE_PLUGIN_ROOT}/scripts/hooks/run_hook.sh" '
        '"${CLAUDE_PLUGIN_ROOT}/scripts/hooks/demo.py"'
    )
    entry["command_windows"] = (
        'powershell.exe -NoProfile -NonInteractive -Command '
        '^& "$env:CLAUDE_PLUGIN_ROOT\\scripts\\hooks\\run_hook.cmd" '
        '"$env:CLAUDE_PLUGIN_ROOT\\scripts\\hooks\\demo.py"'
    )

    fingerprint = build_hook_fingerprint(entry, tmp_path)

    expected_payload = json.dumps(
        {
            "command": entry["command"],
            "command_windows": entry["command_windows"],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    expected_hash = hashlib.sha256(expected_payload).hexdigest()
    assert fingerprint["command_hash"] == f"sha256:{expected_hash}"
    assert fingerprint["missing_sources"] == []
    assert [item["path"] for item in fingerprint["source_hashes"]] == [
        "scripts/hooks/demo.py",
        "scripts/hooks/run_hook.cmd",
        "scripts/hooks/run_hook.sh",
    ]


def test_missing_trust_state_loads_empty_state(tmp_path: Path) -> None:
    trust_state = load_trust_state(tmp_path / ".athanor" / "missing-trust.json")

    assert trust_state == {"schema_version": 1, "trusted_hooks": {}}


def test_invalid_trust_state_json_raises_without_silent_trust(tmp_path: Path) -> None:
    path = tmp_path / ".athanor" / "hook-installer-trust.json"
    path.parent.mkdir(parents=True)
    path.write_text("{not-json", encoding="utf-8")

    with pytest.raises(HookInstallerTrustError, match="trust state is not valid JSON"):
        load_trust_state(path)


def test_matching_trust_state_marks_hook_trusted(tmp_path: Path) -> None:
    source = tmp_path / "scripts" / "hooks" / "demo.py"
    source.parent.mkdir(parents=True)
    source.write_text("print('demo')\n", encoding="utf-8")
    fingerprint = build_hook_fingerprint(_entry(), tmp_path)
    trust_state = {
        "schema_version": 1,
        "trusted_hooks": {
            "demo-hook": {
                "status": "trusted",
                "command_hash": fingerprint["command_hash"],
                "source_hashes": fingerprint["source_hashes"],
                "reviewed_at": "2026-06-17T00:00:00Z",
                "reviewer": "test",
            }
        },
    }

    status = trust_status(_entry(), fingerprint, trust_state)

    assert status["trust_status"] == "trusted"
    assert status["reason"] == "trusted hook fingerprint matched"


def test_missing_trust_state_marks_hook_untrusted(tmp_path: Path) -> None:
    source = tmp_path / "scripts" / "hooks" / "demo.py"
    source.parent.mkdir(parents=True)
    source.write_text("print('demo')\n", encoding="utf-8")
    fingerprint = build_hook_fingerprint(_entry(), tmp_path)

    status = trust_status(_entry(), fingerprint, {"schema_version": 1, "trusted_hooks": {}})

    assert status["trust_status"] == "untrusted"
    assert status["reason"] == "hook id is not trusted"


def test_mismatched_command_hash_marks_hook_mismatch(tmp_path: Path) -> None:
    source = tmp_path / "scripts" / "hooks" / "demo.py"
    source.parent.mkdir(parents=True)
    source.write_text("print('demo')\n", encoding="utf-8")
    fingerprint = build_hook_fingerprint(_entry(), tmp_path)
    trust_state = {
        "schema_version": 1,
        "trusted_hooks": {
            "demo-hook": {
                "status": "trusted",
                "command_hash": "sha256:0",
                "source_hashes": fingerprint["source_hashes"],
                "reviewed_at": "2026-06-17T00:00:00Z",
                "reviewer": "test",
            }
        },
    }

    status = trust_status(_entry(), fingerprint, trust_state)

    assert status["trust_status"] == "mismatch"
    assert status["reason"] == "trust command hash mismatch"


def test_missing_source_blocks_trust_even_when_state_exists(tmp_path: Path) -> None:
    fingerprint = build_hook_fingerprint(_entry(), tmp_path)
    trust_state = {
        "schema_version": 1,
        "trusted_hooks": {
            "demo-hook": {
                "status": "trusted",
                "command_hash": fingerprint["command_hash"],
                "source_hashes": [],
                "reviewed_at": "2026-06-17T00:00:00Z",
                "reviewer": "test",
            }
        },
    }

    status = trust_status(_entry(), fingerprint, trust_state)

    assert status["trust_status"] == "missing-source"
    assert status["reason"] == "hook source file is missing"
    assert status["missing_sources"] == ["scripts/hooks/demo.py"]


def test_trust_schema_accepts_current_shape(tmp_path: Path) -> None:
    schema_path = Path(__file__).resolve().parent.parent / "schemas" / "hook-installer-trust.schema.json"
    source = tmp_path / "scripts" / "hooks" / "demo.py"
    source.parent.mkdir(parents=True)
    source.write_text("print('demo')\n", encoding="utf-8")
    fingerprint = build_hook_fingerprint(_entry(), tmp_path)
    trust_path = tmp_path / ".athanor" / "hook-installer-trust.json"
    payload = {
        "schema_version": 1,
        "trusted_hooks": {
            "demo-hook": {
                "status": "trusted",
                "command_hash": fingerprint["command_hash"],
                "source_hashes": fingerprint["source_hashes"],
                "reviewed_at": "2026-06-17T00:00:00Z",
                "reviewer": "test",
            }
        },
    }
    _write_json(trust_path, payload)

    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(load_trust_state(trust_path), json.loads(schema_path.read_text(encoding="utf-8")))
