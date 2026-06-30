#!/usr/bin/env python3
"""
Athanor v0.19.0 PostToolUse pytest evidence sniffer.

Evidence-only v1: after a Bash tool finishes, detect pytest-family commands
and append observed result evidence to:

  .athanor/sessions/<latest>/.hook-state/test-evidence.jsonl

This hook never blocks Claude Code. Missing stdin, unknown payload shapes,
missing session state, and write errors all fail open with exit code 0. The
evidence stream is intended for later Spec-then-TDD cross-checking; v1 only
collects the facts.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
import shlex
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import _athanor_hook_runtime as _runtime  # noqa: E402
import freeze_guard as _freeze_guard  # noqa: E402

_SESSION_ID_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{3}$")
_PYTEST_NAMES = {"pytest", "pytest.exe", "py.test", "py.test.exe"}
_PYTHON_NAMES = {"python", "python.exe", "python3", "python3.exe", "py", "py.exe"}
_SHELL_BREAK_TOKENS = {"&&", "||", ";", "|"}
_FILE_TOOL_NAMES = {"Edit", "Write", "MultiEdit"}
_FILE_CHANGE_RESPONSE_FIELDS = {
    "changed_files",
    "created_files",
    "deleted_files",
    "file_changes",
    "files_changed",
    "modified_files",
}
_FILE_CHANGE_PATH_KEYS = {
    "file",
    "file_path",
    "filePath",
    "filename",
    "name",
    "path",
}
_FILE_CHANGE_CONTAINER_KEYS = {
    "changed",
    "created",
    "deleted",
    "files",
    "modified",
    "paths",
}
# Anchored to a pytest COUNT-summary token (`<n> failed/error(s)`), mirroring
# the pass regex, so a green run whose tail merely MENTIONS the word
# 'error'/'failed' (e.g. a deprecation note) is no longer inferred as red.
_PYTEST_FAILURE_SUMMARY_RE = re.compile(r"\b\d+\s+(?:failed|error|errors)\b", re.IGNORECASE)
_PYTEST_PASS_SUMMARY_RE = re.compile(r"\b\d+\s+passed\b", re.IGNORECASE)
_OPTIONS_WITH_VALUE = {
    "-c",
    "-k",
    "-m",
    "-n",  # xdist worker count (`-n auto`)
    "-o",
    "-p",  # plugin (de)activation (`-p no:cacheprovider`)
    "-W",  # warning filter (long form: --pythonwarnings)
    "--basetemp",
    "--cache-clear",
    "--capture",
    "--color",
    "--confcutdir",
    "--cov",
    "--cov-append",
    "--cov-config",
    "--cov-fail-under",
    "--cov-report",
    "--deselect",
    "--dist",  # xdist distribution mode
    "--ignore",
    "--ignore-glob",
    "--junit-prefix",
    "--junit-xml",
    "--junitxml",
    "--maxfail",
    "--numprocesses",  # xdist worker count (long form of -n)
    "--override-ini",
    "--pyargs",
    "--pythonwarnings",  # warning filter (long form of -W)
    "--rootdir",
    "--tb",
}


def _stderr(msg: str) -> None:
    print(f"athanor (posttool evidence): {msg}", file=sys.stderr)


def _read_config_at(project_root: Path | None) -> dict:
    if project_root is None:
        return _runtime.read_athanor_config()
    path = project_root / "athanor.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _tool_name(payload: dict) -> str:
    for key in ("tool_name", "toolName"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
    tool = payload.get("tool")
    if isinstance(tool, dict):
        value = tool.get("name")
        if isinstance(value, str):
            return value
    return ""


def _tool_input(payload: dict) -> dict:
    for key in ("tool_input", "toolInput", "input"):
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _tool_response(payload: dict) -> dict:
    for key in ("tool_response", "toolResponse", "response", "result"):
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _command_from_payload(payload: dict) -> str:
    tool_input = _tool_input(payload)
    value = tool_input.get("command")
    if isinstance(value, str):
        return value
    value = payload.get("command")
    return value if isinstance(value, str) else ""


def _basename(token: str) -> str:
    cleaned = token.strip("'\"").replace("\\", "/")
    return cleaned.rsplit("/", 1)[-1].lower()


def _split_command(command: str) -> list[str]:
    try:
        return shlex.split(command, posix=True)
    except ValueError:
        return command.split()


def _pytest_args(command: str) -> list[str] | None:
    tokens = _split_command(command)
    if not tokens:
        return None

    first = _basename(tokens[0])
    if first in _PYTEST_NAMES:
        return tokens[1:]

    if first in _PYTHON_NAMES and len(tokens) >= 3:
        if tokens[1] == "-m" and tokens[2] == "pytest":
            return tokens[3:]

    return None


def _extract_test_targets(pytest_args: list[str]) -> list[str]:
    targets: list[str] = []
    skip_next = False
    passthrough = False

    for token in pytest_args:
        if token in _SHELL_BREAK_TOKENS:
            break
        if skip_next:
            skip_next = False
            continue
        if token == "--":
            passthrough = True
            continue
        if not passthrough and token.startswith("-"):
            option = token.split("=", 1)[0]
            if "=" not in token and option in _OPTIONS_WITH_VALUE:
                skip_next = True
            continue
        targets.append(token)

    return targets


def _scope_for_targets(targets: list[str]) -> str:
    if not targets:
        return "full_suite"
    normalized = {t.replace("\\", "/").rstrip("/") for t in targets}
    if normalized == {"tests"} or normalized == {"."}:
        return "full_suite"
    return "targeted"


def _extract_exit_code(payload: dict) -> int | None:
    response = _tool_response(payload)
    for container in (response, payload):
        for key in ("exit_code", "exitCode", "returncode", "return_code", "code", "status"):
            value = container.get(key)
            if isinstance(value, bool):
                continue
            if isinstance(value, int):
                return value
            if isinstance(value, str):
                try:
                    return int(value)
                except ValueError:
                    continue
    return None


def _infer_pytest_exit_code_from_output(payload: dict) -> int | None:
    output = _output_tail(payload)
    if _PYTEST_FAILURE_SUMMARY_RE.search(output):
        return 1
    if _PYTEST_PASS_SUMMARY_RE.search(output):
        return 0
    return None


def _extract_exit_code_with_source(payload: dict) -> tuple[int | None, str]:
    direct = _extract_exit_code(payload)
    if direct is not None:
        return direct, "tool_response"
    inferred = _infer_pytest_exit_code_from_output(payload)
    if inferred is not None:
        return inferred, "pytest_output"
    return None, "unavailable"


def _string_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    if isinstance(value, (int, float, bool)):
        return str(value)
    return ""


def _output_tail(payload: dict, *, max_lines: int = 20, max_chars: int = 4000) -> str:
    response = _tool_response(payload)
    parts: list[str] = []
    for container in (response, payload):
        for key in ("stdout", "stderr", "output", "text"):
            value = _string_value(container.get(key))
            if value:
                parts.append(value)
    combined = "\n".join(parts)
    lines = combined.splitlines()
    tail = "\n".join(lines[-max_lines:]) if lines else combined
    if len(tail) > max_chars:
        tail = tail[-max_chars:]
    return tail


def _freeze_mode(config: dict) -> str:
    hooks = config.get("hooks")
    if not isinstance(hooks, dict):
        return "off"
    freeze = hooks.get("freeze")
    if not isinstance(freeze, dict):
        return "off"
    mode = freeze.get("mode", "off")
    return mode if isinstance(mode, str) else "off"


def _load_freeze_allowlist(session_dir: Path) -> dict | None:
    allowlist_path = session_dir / "freeze-allowlist.json"
    try:
        parsed = json.loads(allowlist_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(parsed, dict):
        return None
    parsed.setdefault("_session_dir", str(session_dir))
    return parsed


def _paths_from_change_value(value: Any) -> list[str]:
    paths: list[str] = []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        for item in value:
            paths.extend(_paths_from_change_value(item))
        return paths
    if not isinstance(value, dict):
        return paths

    for key in _FILE_CHANGE_PATH_KEYS:
        raw = value.get(key)
        if isinstance(raw, str):
            paths.append(raw)

    for key in _FILE_CHANGE_CONTAINER_KEYS:
        if key in value:
            paths.extend(_paths_from_change_value(value[key]))
    return paths


def _add_candidate(candidates: list[dict], path: str, source: str) -> None:
    if not isinstance(path, str) or not path.strip():
        return
    candidates.append({"path": path, "source": source})


def _freeze_change_candidates(payload: dict) -> list[dict]:
    tool_name = _tool_name(payload)
    tool_input = _tool_input(payload)
    response = _tool_response(payload)
    candidates: list[dict] = []

    if tool_name in _FILE_TOOL_NAMES:
        value = tool_input.get("file_path")
        if isinstance(value, str):
            _add_candidate(candidates, value, "tool_input.file_path")

    if tool_name == "Bash":
        command = _command_from_payload(payload)
        for target in _freeze_guard.extract_bash_write_targets(command):
            _add_candidate(candidates, target, "tool_input.command")

    for field in sorted(_FILE_CHANGE_RESPONSE_FIELDS):
        if field not in response:
            continue
        for path in _paths_from_change_value(response[field]):
            _add_candidate(candidates, path, f"tool_response.{field}")

    seen: set[tuple[str, str]] = set()
    deduped: list[dict] = []
    for candidate in candidates:
        key = (candidate["path"].replace("\\", "/"), candidate["source"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def _classify_freeze_candidates(
    candidates: list[dict],
    allowlist: dict | None,
    config: dict,
) -> list[dict]:
    paths: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for candidate in candidates:
        classified = _freeze_guard.classify_paths_against_allowlist(
            [candidate["path"]],
            allowlist,
            config,
        )
        if not classified:
            continue
        item = {
            "path": classified[0]["path"],
            "source": candidate["source"],
            "allowlist_status": classified[0]["allowlist_status"],
        }
        key = (item["path"], item["source"])
        if key in seen:
            continue
        seen.add(key)
        paths.append(item)
    return paths


def _append_freeze_change_evidence(
    payload: dict,
    *,
    config: dict,
    session_dir: Path | None,
) -> str:
    candidates = _freeze_change_candidates(payload)
    if not candidates:
        return ""
    if session_dir is None:
        return "no session directory found; passing (fail-open)"

    allowlist = _load_freeze_allowlist(session_dir)
    paths = _classify_freeze_candidates(candidates, allowlist, config)
    if not paths:
        return ""

    record = {
        "schema_version": 1,
        "timestamp": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "hook_event_name": payload.get("hook_event_name") or payload.get("hookEventName") or "PostToolUse",
        "tool_name": _tool_name(payload),
        "command": _command_from_payload(payload),
        "session_id": session_dir.name,
        "freeze_mode": _freeze_mode(config),
        "allowlist_loaded": allowlist is not None,
        "paths": paths,
    }
    evidence_path = session_dir / ".hook-state" / "freeze-change-evidence.jsonl"
    try:
        _append_jsonl(evidence_path, record)
    except OSError as exc:
        return f"could not write freeze change evidence: {exc}; passing (fail-open)"
    return ""


def _latest_session_dir(project_root: Path) -> Path | None:
    sessions_dir = project_root / ".athanor" / "sessions"
    if not sessions_dir.is_dir():
        return None
    try:
        candidates = [
            child
            for child in sessions_dir.iterdir()
            if child.is_dir() and _SESSION_ID_PATTERN.match(child.name)
        ]
    except OSError:
        return None
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: p.name)[-1]


def _resolve_root(project_root: Path | str | None) -> Path | None:
    if project_root is not None:
        return Path(project_root)
    return _runtime.resolve_project_root()


def _resolve_session_dir(
    root: Path | None,
    session_dir: Path | str | None,
) -> Path | None:
    if session_dir is not None:
        return Path(session_dir)
    if root is None:
        return None
    return _latest_session_dir(root)


def _append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def _append_hook_health(
    root: Path | None,
    *,
    event: str,
    message: str,
    payload: dict,
) -> None:
    if root is None:
        return
    record = {
        "schema_version": 1,
        "timestamp": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "hook_name": "posttool_evidence_sniffer",
        "hook_event_name": payload.get("hook_event_name") or payload.get("hookEventName") or "PostToolUse",
        "event": event,
        "severity": "warning",
        "fail_open": True,
        "message": message,
        "tool_name": _tool_name(payload),
        "command": _command_from_payload(payload),
    }
    try:
        _append_jsonl(root / ".athanor" / "hook-health.jsonl", record)
    except OSError:
        return


def evaluate_payload(
    payload: Any,
    *,
    project_root: Path | str | None = None,
    session_dir: Path | str | None = None,
) -> tuple[int, str]:
    """Evaluate one PostToolUse payload.

    Returns ``(exit_code, stderr_message)``. The exit code is always 0 in v1;
    stderr is a breadcrumb for fail-open infrastructure issues only.
    """
    if not isinstance(payload, dict):
        return 0, ""

    root = _resolve_root(project_root)
    config = _read_config_at(root)
    if _runtime.is_hook_profile_off(config):
        return 0, ""

    resolved_session = _resolve_session_dir(root, session_dir)
    freeze_stderr = _append_freeze_change_evidence(
        payload,
        config=config,
        session_dir=resolved_session,
    )

    if _tool_name(payload) != "Bash":
        return 0, freeze_stderr

    command = _command_from_payload(payload)
    pytest_args = _pytest_args(command)
    if pytest_args is None:
        return 0, freeze_stderr

    if resolved_session is None:
        message = freeze_stderr or "no session directory found; passing (fail-open)"
        _append_hook_health(
            root,
            event="missing_session_dir",
            message=message,
            payload=payload,
        )
        return 0, message

    targets = _extract_test_targets(pytest_args)
    primary_target = targets[0] if targets else None
    observed_exit_code, exit_code_source = _extract_exit_code_with_source(payload)
    record = {
        "schema_version": 1,
        "timestamp": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "hook_event_name": payload.get("hook_event_name") or payload.get("hookEventName") or "PostToolUse",
        "tool_name": "Bash",
        "command": command,
        "test_targets": targets,
        "primary_target": primary_target,
        "scope": _scope_for_targets(targets),
        "exit_code": observed_exit_code,
        "exit_code_source": exit_code_source,
        "output_tail": _output_tail(payload),
        "session_id": resolved_session.name,
    }

    evidence_path = resolved_session / ".hook-state" / "test-evidence.jsonl"
    try:
        _append_jsonl(evidence_path, record)
    except OSError as exc:
        message = f"could not write test evidence: {exc}; passing (fail-open)"
        _append_hook_health(
            root,
            event="write_test_evidence_failed",
            message=message,
            payload=payload,
        )
        return 0, message
    return 0, freeze_stderr


def main() -> int:
    payload = _runtime.read_stdin_payload()
    if payload is None:
        return 0
    exit_code, stderr = evaluate_payload(payload)
    if stderr:
        _stderr(stderr)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
