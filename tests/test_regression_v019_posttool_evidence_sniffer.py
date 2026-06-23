"""Regression tests for v0.19.0 PostToolUse pytest evidence sniffer.

The sniffer is evidence-only in v1: it records pytest Bash results after the
tool finishes, but it never blocks a Claude Code session. Later work may use
the JSONL evidence stream to enforce Spec-then-TDD result claims.
"""
from __future__ import annotations

import importlib
import json
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_HOOKS = REPO_ROOT / "scripts" / "hooks"
SNIFTER_SCRIPT = SCRIPTS_HOOKS / "posttool_evidence_sniffer.py"
HOOKS_JSON = REPO_ROOT / "hooks" / "hooks.json"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "validate-plugin.yml"
PYPROJECT = REPO_ROOT / "pyproject.toml"

if str(SCRIPTS_HOOKS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_HOOKS))


@pytest.fixture
def sniffer():
    sys.modules.pop("posttool_evidence_sniffer", None)
    return importlib.import_module("posttool_evidence_sniffer")


def _project_with_session(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "project"
    session_dir = root / ".athanor" / "sessions" / "2026-06-14-001"
    (session_dir / ".hook-state").mkdir(parents=True)
    (root / "athanor.json").write_text(
        json.dumps({"hooks": {"profile": "standard"}}),
        encoding="utf-8",
    )
    return root, session_dir


def _bash_payload(
    command: str,
    *,
    exit_code: int = 1,
    stdout: str = "",
    stderr: str = "",
) -> dict:
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "tool_response": {
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
        },
    }


def _records(session_dir: Path) -> list[dict]:
    path = session_dir / ".hook-state" / "test-evidence.jsonl"
    assert path.is_file(), f"missing evidence file at {path}"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _health_records(root: Path) -> list[dict]:
    path = root / ".athanor" / "hook-health.jsonl"
    assert path.is_file(), f"missing health file at {path}"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_script_exists_and_has_python_shebang():
    assert SNIFTER_SCRIPT.is_file(), f"missing {SNIFTER_SCRIPT}"
    first = SNIFTER_SCRIPT.read_text(encoding="utf-8").splitlines()[0]
    assert first.startswith("#!") and "python" in first


def test_evaluate_payload_is_importable(sniffer):
    assert hasattr(sniffer, "evaluate_payload")
    assert callable(sniffer.evaluate_payload)


def test_malformed_payload_fails_open_without_evidence(sniffer, tmp_path):
    root, session_dir = _project_with_session(tmp_path)
    exit_code, stderr = sniffer.evaluate_payload(
        ["not", "a", "dict"], project_root=root, session_dir=session_dir
    )
    assert exit_code == 0
    assert stderr == ""
    assert not (session_dir / ".hook-state" / "test-evidence.jsonl").exists()


def test_non_bash_payload_is_ignored(sniffer, tmp_path):
    root, session_dir = _project_with_session(tmp_path)
    payload = {"hook_event_name": "PostToolUse", "tool_name": "Read"}
    exit_code, stderr = sniffer.evaluate_payload(
        payload, project_root=root, session_dir=session_dir
    )
    assert exit_code == 0
    assert stderr == ""
    assert not (session_dir / ".hook-state" / "test-evidence.jsonl").exists()


def test_non_pytest_bash_payload_is_ignored(sniffer, tmp_path):
    root, session_dir = _project_with_session(tmp_path)
    exit_code, stderr = sniffer.evaluate_payload(
        _bash_payload("echo hello", exit_code=0),
        project_root=root,
        session_dir=session_dir,
    )
    assert exit_code == 0
    assert stderr == ""
    assert not (session_dir / ".hook-state" / "test-evidence.jsonl").exists()


def test_pytest_payload_appends_targeted_evidence(sniffer, tmp_path):
    root, session_dir = _project_with_session(tmp_path)
    stdout = "\n".join(f"line-{i}" for i in range(30))
    payload = _bash_payload(
        "python -m pytest tests/test_demo.py::test_red -v",
        exit_code=1,
        stdout=stdout,
        stderr="FAILED tests/test_demo.py::test_red",
    )

    exit_code, stderr = sniffer.evaluate_payload(
        payload, project_root=root, session_dir=session_dir
    )

    assert exit_code == 0
    assert stderr == ""
    [record] = _records(session_dir)
    assert record["schema_version"] == 1
    assert record["hook_event_name"] == "PostToolUse"
    assert record["tool_name"] == "Bash"
    assert record["command"] == "python -m pytest tests/test_demo.py::test_red -v"
    assert record["test_targets"] == ["tests/test_demo.py::test_red"]
    assert record["primary_target"] == "tests/test_demo.py::test_red"
    assert record["scope"] == "targeted"
    assert record["exit_code"] == 1
    assert record["session_id"] == "2026-06-14-001"
    assert "line-0" not in record["output_tail"]
    assert "line-29" in record["output_tail"]
    assert "FAILED tests/test_demo.py::test_red" in record["output_tail"]


def test_pytest_payload_marks_full_suite_scope(sniffer, tmp_path):
    root, session_dir = _project_with_session(tmp_path)
    payload = _bash_payload(
        "pytest tests/ -q",
        exit_code=0,
        stdout="975 passed in 10.00s",
    )

    exit_code, _ = sniffer.evaluate_payload(
        payload, project_root=root, session_dir=session_dir
    )

    assert exit_code == 0
    [record] = _records(session_dir)
    assert record["test_targets"] == ["tests/"]
    assert record["primary_target"] == "tests/"
    assert record["scope"] == "full_suite"
    assert record["exit_code"] == 0


def test_pytest_without_targets_marks_full_suite_scope(sniffer, tmp_path):
    root, session_dir = _project_with_session(tmp_path)
    payload = _bash_payload(
        "python -m pytest -q",
        exit_code=0,
        stdout="1491 passed in 20.00s",
    )

    exit_code, stderr = sniffer.evaluate_payload(payload, project_root=root)

    assert exit_code == 0
    assert stderr == ""
    [record] = _records(session_dir)
    assert record["test_targets"] == []
    assert record["primary_target"] is None
    assert record["scope"] == "full_suite"
    assert record["exit_code"] == 0


def test_env_project_dir_allows_installed_hook_cwd_to_write_evidence(
    sniffer,
    monkeypatch,
    tmp_path,
):
    root, session_dir = _project_with_session(tmp_path)
    outside = tmp_path / "plugin-cache"
    outside.mkdir()
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    monkeypatch.chdir(outside)

    exit_code, stderr = sniffer.evaluate_payload(
        _bash_payload("pytest tests -q", exit_code=0)
    )

    assert exit_code == 0
    assert stderr == ""
    [record] = _records(session_dir)
    assert record["session_id"] == session_dir.name
    assert record["scope"] == "full_suite"


def test_pytest_payload_infers_green_exit_code_from_output_when_direct_code_absent(sniffer, tmp_path):
    root, session_dir = _project_with_session(tmp_path)
    payload = _bash_payload(
        "python -m pytest tests/test_demo.py::test_green -q",
        stdout=".                                                                        [100%]\n1 passed in 0.44s",
    )
    payload["tool_response"].pop("exit_code")

    exit_code, stderr = sniffer.evaluate_payload(payload, project_root=root)

    assert exit_code == 0
    assert stderr == ""
    [record] = _records(session_dir)
    assert record["exit_code"] == 0
    assert record["exit_code_source"] == "pytest_output"


def test_pytest_payload_infers_red_exit_code_from_output_when_direct_code_absent(sniffer, tmp_path):
    root, session_dir = _project_with_session(tmp_path)
    payload = _bash_payload(
        "python -m pytest tests/test_demo.py::test_red -q",
        stdout="FAILED tests/test_demo.py::test_red\n1 failed in 0.12s",
    )
    payload["tool_response"].pop("exit_code")

    exit_code, stderr = sniffer.evaluate_payload(payload, project_root=root)

    assert exit_code == 0
    assert stderr == ""
    [record] = _records(session_dir)
    assert record["exit_code"] == 1
    assert record["exit_code_source"] == "pytest_output"


def test_payload_without_session_dir_fails_open(sniffer, tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    payload = _bash_payload("pytest tests/test_demo.py -q", exit_code=0)

    exit_code, stderr = sniffer.evaluate_payload(payload, project_root=root)

    assert exit_code == 0
    assert "session" in stderr.lower()


def test_missing_session_dir_records_fail_open_health_diagnostic(sniffer, tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "athanor.json").write_text(
        json.dumps({"hooks": {"profile": "standard"}}),
        encoding="utf-8",
    )

    exit_code, stderr = sniffer.evaluate_payload(
        _bash_payload("python -m pytest tests/test_demo.py -q", exit_code=0),
        project_root=root,
    )

    assert exit_code == 0
    assert "fail-open" in stderr
    [record] = _health_records(root)
    assert record["schema_version"] == 1
    assert record["hook_name"] == "posttool_evidence_sniffer"
    assert record["event"] == "missing_session_dir"
    assert record["severity"] == "warning"
    assert record["fail_open"] is True
    assert record["tool_name"] == "Bash"
    assert record["command"] == "python -m pytest tests/test_demo.py -q"


def test_subprocess_entry_fails_open_on_malformed_json(tmp_path):
    root, _session_dir = _project_with_session(tmp_path)
    proc = subprocess.run(
        [sys.executable, str(SNIFTER_SCRIPT)],
        input="not json",
        text=True,
        capture_output=True,
        cwd=str(root),
    )
    assert proc.returncode == 0
    assert "Traceback" not in proc.stderr


def test_hooks_json_registers_posttooluse_sniffer():
    data = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
    entries = data["hooks"].get("PostToolUse")
    assert isinstance(entries, list) and len(entries) == 1
    inner = entries[0].get("hooks")
    assert isinstance(inner, list) and len(inner) == 1
    item = inner[0]
    assert item["type"] == "command"
    assert "${CLAUDE_PLUGIN_ROOT}" in item["command"]
    assert "posttool_evidence_sniffer.py" in item["command"]


def test_capability_probe_reports_posttooluse_evidence_only_supported():
    import capability_probe

    report = capability_probe.build_capability_report(REPO_ROOT)
    post = report["events"]["PostToolUse"]
    assert post["registered_in_hooks_json"] is True
    assert post["supported"] is True
    assert post["support_level"] == "evidence-only"
    assert post["tool_response_available"] is None
    assert post["payload_keys_source"] == "expected"
    assert set(post["evidence_streams"]) == {
        "test_evidence",
        "freeze_change_evidence",
    }


def test_ci_uses_locked_uv_environment_with_yaml_dependency():
    body = CI_WORKFLOW.read_text(encoding="utf-8").lower()
    assert "astral-sh/setup-uv" in body
    assert "uv sync --locked --dev" in body
    assert "uv run python -m pytest tests/ -v" in body

    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    dev_dependencies = pyproject["dependency-groups"]["dev"]
    assert any(item.lower().startswith("pyyaml") for item in dev_dependencies)
