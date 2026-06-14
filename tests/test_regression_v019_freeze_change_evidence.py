"""Regression tests for v0.19.0 Freeze D2 PostToolUse evidence.

The D2 follow-up is evidence-only: PostToolUse records observed file-change
paths after tools finish, classifies them against the Freeze allowlist when
available, and never blocks the session.
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_HOOKS = REPO_ROOT / "scripts" / "hooks"
HOOKS_JSON = REPO_ROOT / "hooks" / "hooks.json"

if str(SCRIPTS_HOOKS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_HOOKS))


def _project_with_session(
    tmp_path: Path,
    *,
    freeze_mode: str = "session",
    allowlist_paths: list[str] | None = None,
    write_allowlist: bool = True,
) -> tuple[Path, Path]:
    root = tmp_path / "project"
    session_dir = root / ".athanor" / "sessions" / "2026-06-14-001"
    (session_dir / ".hook-state").mkdir(parents=True)
    (root / "athanor.json").write_text(
        json.dumps({"hooks": {"profile": "standard", "freeze": {"mode": freeze_mode}}}),
        encoding="utf-8",
    )
    if write_allowlist:
        allowed = [
            ".athanor/sessions/2026-06-14-001/**",
            ".athanor/lessons/**",
        ] + list(allowlist_paths or [])
        (session_dir / "freeze-allowlist.json").write_text(
            json.dumps(
                {
                    "session_id": "2026-06-14-001",
                    "built_at": "2026-06-14T00:00:00Z",
                    "allowed_paths": allowed,
                }
            ),
            encoding="utf-8",
        )
    return root, session_dir


def _sniffer():
    sys.modules.pop("posttool_evidence_sniffer", None)
    return importlib.import_module("posttool_evidence_sniffer")


def _records(session_dir: Path) -> list[dict]:
    path = session_dir / ".hook-state" / "freeze-change-evidence.jsonl"
    assert path.is_file(), f"missing freeze change evidence file at {path}"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_bash_tool_response_files_changed_marks_out_of_allowlist(tmp_path):
    root, session_dir = _project_with_session(tmp_path, allowlist_paths=["src/foo.py"])
    payload = {
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "python -c \"open('src/secret.py','w').write('x')\""},
        "tool_response": {"exit_code": 0, "files_changed": ["src/secret.py"]},
    }

    exit_code, stderr = _sniffer().evaluate_payload(
        payload, project_root=root, session_dir=session_dir
    )

    assert exit_code == 0
    assert stderr == ""
    [record] = _records(session_dir)
    assert record["schema_version"] == 1
    assert record["hook_event_name"] == "PostToolUse"
    assert record["tool_name"] == "Bash"
    assert record["command"] == payload["tool_input"]["command"]
    assert record["session_id"] == "2026-06-14-001"
    assert record["freeze_mode"] == "session"
    assert record["allowlist_loaded"] is True
    assert record["paths"] == [
        {
            "path": "src/secret.py",
            "source": "tool_response.files_changed",
            "allowlist_status": "out_of_allowlist",
        }
    ]


def test_file_tool_input_path_marks_in_allowlist(tmp_path):
    root, session_dir = _project_with_session(tmp_path, allowlist_paths=["src/foo.py"])
    payload = {
        "hook_event_name": "PostToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": "src/foo.py"},
        "tool_response": {},
    }

    exit_code, stderr = _sniffer().evaluate_payload(
        payload, project_root=root, session_dir=session_dir
    )

    assert exit_code == 0
    assert stderr == ""
    [record] = _records(session_dir)
    assert record["paths"] == [
        {
            "path": "src/foo.py",
            "source": "tool_input.file_path",
            "allowlist_status": "in_allowlist",
        }
    ]


def test_missing_allowlist_marks_observed_paths_unknown_allowlist(tmp_path):
    root, session_dir = _project_with_session(tmp_path, write_allowlist=False)
    payload = {
        "hook_event_name": "PostToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": "src/secret.py"},
        "tool_response": {},
    }

    exit_code, stderr = _sniffer().evaluate_payload(
        payload, project_root=root, session_dir=session_dir
    )

    assert exit_code == 0
    assert stderr == ""
    [record] = _records(session_dir)
    assert record["allowlist_loaded"] is False
    assert record["paths"] == [
        {
            "path": "src/secret.py",
            "source": "tool_input.file_path",
            "allowlist_status": "unknown_allowlist",
        }
    ]


def test_non_pytest_bash_without_file_change_fields_writes_no_evidence(tmp_path):
    root, session_dir = _project_with_session(tmp_path, allowlist_paths=["src/foo.py"])
    payload = {
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "echo hello"},
        "tool_response": {"exit_code": 0, "stdout": "hello\n"},
    }

    exit_code, stderr = _sniffer().evaluate_payload(
        payload, project_root=root, session_dir=session_dir
    )

    assert exit_code == 0
    assert stderr == ""
    assert not (session_dir / ".hook-state" / "freeze-change-evidence.jsonl").exists()
    assert not (session_dir / ".hook-state" / "test-evidence.jsonl").exists()


def test_bash_syntactic_write_target_is_recorded_when_no_response_field(tmp_path):
    root, session_dir = _project_with_session(tmp_path, allowlist_paths=["src/foo.py"])
    payload = {
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "echo data > src/secret.py"},
        "tool_response": {"exit_code": 0},
    }

    exit_code, stderr = _sniffer().evaluate_payload(
        payload, project_root=root, session_dir=session_dir
    )

    assert exit_code == 0
    assert stderr == ""
    [record] = _records(session_dir)
    assert record["paths"] == [
        {
            "path": "src/secret.py",
            "source": "tool_input.command",
            "allowlist_status": "out_of_allowlist",
        }
    ]


def test_hooks_json_does_not_register_filechanged():
    data = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
    events = set(data["hooks"].keys())
    assert events == {"Stop", "PreToolUse", "PostToolUse"}
    assert "FileChanged" not in events

