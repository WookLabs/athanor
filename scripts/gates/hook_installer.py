#!/usr/bin/env python3
"""Trust helpers for the Athanor hook installer."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

PLUGIN_ROOT_TOKEN = "${CLAUDE_PLUGIN_ROOT}/"
PLUGIN_ROOT_PATH_RE = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\"'\s]+)")


class HookInstallerTrustError(ValueError):
    """Raised when hook installer trust state cannot be loaded safely."""


def _sha256_bytes(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def _string_field(entry: dict[str, Any], field_name: str) -> str:
    value = entry.get(field_name)
    if not isinstance(value, str):
        return ""
    return value


def _normalize_source_path(raw_path: str) -> str:
    normalized = raw_path.replace("\\", "/").lstrip("/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _plugin_root_sources(command: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for match in PLUGIN_ROOT_PATH_RE.finditer(command):
        source_path = _normalize_source_path(match.group(1))
        if source_path and source_path not in seen:
            seen.add(source_path)
            out.append(source_path)
    return sorted(out)


def build_hook_fingerprint(entry: dict[str, Any], repo_root: Path | str) -> dict[str, Any]:
    """Return command/source hashes for one catalog hook entry."""
    root = Path(repo_root)
    command = _string_field(entry, "command")
    hook_id = _string_field(entry, "id")
    source_hashes: list[dict[str, str]] = []
    missing_sources: list[str] = []

    for source_path in _plugin_root_sources(command):
        path = root.joinpath(*source_path.split("/"))
        if not path.is_file():
            missing_sources.append(source_path)
            continue
        source_hashes.append(
            {
                "path": source_path,
                "sha256": _sha256_bytes(path.read_bytes()),
            }
        )

    return {
        "schema_version": 1,
        "hook_id": hook_id,
        "command_hash": _sha256_text(command),
        "source_hashes": source_hashes,
        "missing_sources": missing_sources,
    }


def load_trust_state(path: Path | str) -> dict[str, Any]:
    """Load hook installer trust state, returning an empty state when missing."""
    trust_path = Path(path)
    if not trust_path.exists():
        return {"schema_version": 1, "trusted_hooks": {}}
    if not trust_path.is_file():
        raise HookInstallerTrustError(f"trust state is not a file: {trust_path}")
    try:
        parsed = json.loads(trust_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HookInstallerTrustError(
            f"trust state is not valid JSON: {exc.msg}"
        ) from exc
    except OSError as exc:
        raise HookInstallerTrustError(f"trust state read error: {exc}") from exc
    if not isinstance(parsed, dict):
        raise HookInstallerTrustError("trust state root must be an object")
    if parsed.get("schema_version") != 1:
        raise HookInstallerTrustError("trust state schema_version must be 1")
    trusted_hooks = parsed.get("trusted_hooks")
    if not isinstance(trusted_hooks, dict):
        raise HookInstallerTrustError("trust state trusted_hooks must be an object")
    return parsed


def _fingerprint_payload(fingerprint: dict[str, Any]) -> dict[str, Any]:
    return {
        "hook_id": fingerprint.get("hook_id", ""),
        "command_hash": fingerprint.get("command_hash", ""),
        "source_hashes": fingerprint.get("source_hashes", []),
        "missing_sources": fingerprint.get("missing_sources", []),
    }


def _status(
    status: str,
    reason: str,
    fingerprint: dict[str, Any],
) -> dict[str, Any]:
    payload = _fingerprint_payload(fingerprint)
    payload["trust_status"] = status
    payload["reason"] = reason
    return payload


def _normalized_hashes(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    normalized: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        sha256 = item.get("sha256")
        if isinstance(path, str) and isinstance(sha256, str):
            normalized.append({"path": path, "sha256": sha256})
    return sorted(normalized, key=lambda item: (item["path"], item["sha256"]))


def trust_status(
    entry: dict[str, Any],
    fingerprint: dict[str, Any],
    trust_state: dict[str, Any],
) -> dict[str, Any]:
    """Return trusted/untrusted/mismatch status for one hook fingerprint."""
    missing_sources = fingerprint.get("missing_sources", [])
    if isinstance(missing_sources, list) and missing_sources:
        return _status("missing-source", "hook source file is missing", fingerprint)

    hook_id = _string_field(entry, "id")
    trusted_hooks = trust_state.get("trusted_hooks")
    if not isinstance(trusted_hooks, dict):
        return _status("untrusted", "trust state has no trusted_hooks object", fingerprint)

    trusted = trusted_hooks.get(hook_id)
    if not isinstance(trusted, dict) or trusted.get("status") != "trusted":
        return _status("untrusted", "hook id is not trusted", fingerprint)

    if trusted.get("command_hash") != fingerprint.get("command_hash"):
        return _status("mismatch", "trust command hash mismatch", fingerprint)

    trusted_sources = _normalized_hashes(trusted.get("source_hashes"))
    fingerprint_sources = _normalized_hashes(fingerprint.get("source_hashes"))
    if trusted_sources != fingerprint_sources:
        return _status("mismatch", "trust source hash mismatch", fingerprint)

    return _status("trusted", "trusted hook fingerprint matched", fingerprint)
