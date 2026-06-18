"""Regression tests for the generic hook payload capture harness."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS_JSON = REPO_ROOT / "hooks" / "hooks.json"
CORPUS_DOC = REPO_ROOT / "docs" / "hook-payload-corpus.md"
CAPTURE_SCRIPT = REPO_ROOT / "scripts" / "hooks" / "hook_payload_capture.py"

sys.path.insert(0, str(REPO_ROOT / "scripts" / "hooks"))


def _payload() -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "session_id": "sess-456",
        "cwd": str(REPO_ROOT),
        "tool_name": "Write",
        "tool_input": {
            "file_path": str(REPO_ROOT / "private.txt"),
            "content": "secret fixture capture content",
        },
        "nested": [
            {
                "private_url": "https://private-user-images.githubusercontent.com/abc",
                "token": "sk-live_abcdefghijklmnopqrstuvwxyz123456",
            }
        ],
    }


def _raw_payload_files(path: Path) -> list[Path]:
    return sorted(
        p for p in path.glob("hook-payload-*.json")
        if not p.name.endswith(".summary.json")
    )


def _summary_payload_files(path: Path) -> list[Path]:
    return sorted(path.glob("hook-payload-*.summary.json"))


def test_hook_payload_capture_script_exists_and_is_importable():
    assert CAPTURE_SCRIPT.is_file(), f"missing hook payload capture harness at {CAPTURE_SCRIPT}"
    import hook_payload_capture

    assert callable(hook_payload_capture.main)


def test_shared_capture_utils_are_importable():
    import hook_capture_utils

    assert callable(hook_capture_utils.capture_payload)
    assert callable(hook_capture_utils.settings_snippet)


def test_valid_payload_writes_raw_and_redacted_shape_summary(tmp_path):
    import hook_payload_capture

    output_dir = tmp_path / "hook-payloads"
    rc = hook_payload_capture.capture_payload(_payload(), output_dir, event="PreToolUse")

    assert rc == 0
    raw_files = _raw_payload_files(output_dir)
    summary_files = _summary_payload_files(output_dir)
    assert len(raw_files) == 1
    assert len(summary_files) == 1
    assert raw_files[0].name.startswith("hook-payload-PreToolUse-")

    raw = json.loads(raw_files[0].read_text(encoding="utf-8"))
    assert raw["tool_input"]["content"] == "secret fixture capture content"

    summary_text = summary_files[0].read_text(encoding="utf-8")
    assert "secret fixture capture content" not in summary_text
    assert "sk-live_" not in summary_text
    assert "private-user-images.githubusercontent.com" not in summary_text
    summary = json.loads(summary_text)
    assert summary["schema_version"] == 1
    assert summary["event_name"] == "PreToolUse"
    assert summary["raw_event_name"] == "PreToolUse"
    assert summary["top_level_keys"] == [
        "cwd",
        "hook_event_name",
        "nested",
        "session_id",
        "tool_input",
        "tool_name",
    ]
    assert len(summary["raw_sha256"]) == 64
    assert summary["shape"]["tool_input"]["values"]["content"]["type"] == "str"
    assert summary["shape"]["tool_input"]["values"]["content"]["length"] == len(
        "secret fixture capture content"
    )
    assert "sha256_12" in summary["shape"]["tool_input"]["values"]["content"]


def test_hook_mode_malformed_stdin_exits_zero_and_writes_nothing(tmp_path):
    proc = subprocess.run(
        [
            sys.executable,
            str(CAPTURE_SCRIPT),
            "--event",
            "Stop",
            "--output-dir",
            str(tmp_path),
        ],
        input="{not json",
        text=True,
        capture_output=True,
        cwd=str(REPO_ROOT),
    )

    assert proc.returncode == 0
    assert proc.stdout == ""
    assert list(tmp_path.glob("*")) == []


def test_hook_mode_valid_payload_has_empty_stdout(tmp_path):
    proc = subprocess.run(
        [
            sys.executable,
            str(CAPTURE_SCRIPT),
            "--event",
            "PostToolUse",
            "--output-dir",
            str(tmp_path),
        ],
        input=json.dumps(_payload()),
        text=True,
        capture_output=True,
        cwd=str(REPO_ROOT),
    )

    assert proc.returncode == 0
    assert proc.stdout == ""
    assert len(_raw_payload_files(tmp_path)) == 1
    assert len(_summary_payload_files(tmp_path)) == 1
    assert _raw_payload_files(tmp_path)[0].name.startswith("hook-payload-PostToolUse-")


def test_print_settings_snippet_covers_core_hooks_and_does_not_mutate_repo():
    claude_dir_existed = (REPO_ROOT / ".claude").exists()
    proc = subprocess.run(
        [
            sys.executable,
            str(CAPTURE_SCRIPT),
            "--project-root",
            str(REPO_ROOT),
            "--print-settings-snippet",
        ],
        text=True,
        capture_output=True,
        cwd=str(REPO_ROOT),
    )

    assert proc.returncode == 0
    snippet = json.loads(proc.stdout)
    for event_name in [
        "FileChanged",
        "PostToolUse",
        "PreToolUse",
        "Stop",
    ]:
        assert event_name in snippet["hooks"]
    for event_name, event_entries in snippet["hooks"].items():
        command = event_entries[0]["hooks"][0]["command"]
        assert event_entries[0]["matcher"] == "*"
        assert str(CAPTURE_SCRIPT) in command
        assert f'--event "{event_name}"' in command
        assert ".athanor" in command
        assert "hook-payloads" in command
    assert (REPO_ROOT / ".claude").exists() is claude_dir_existed


def test_print_settings_snippet_covers_capture_first_lifecycle_events():
    proc = subprocess.run(
        [
            sys.executable,
            str(CAPTURE_SCRIPT),
            "--project-root",
            str(REPO_ROOT),
            "--print-settings-snippet",
        ],
        text=True,
        capture_output=True,
        cwd=str(REPO_ROOT),
    )

    assert proc.returncode == 0
    snippet = json.loads(proc.stdout)
    assert sorted(snippet["hooks"].keys()) == [
        "FileChanged",
        "PermissionRequest",
        "PostToolUse",
        "PostToolUseFailure",
        "PreCompact",
        "PreToolUse",
        "SessionStart",
        "Stop",
        "SubagentStop",
        "UserPromptSubmit",
    ]


def test_repo_hooks_json_still_does_not_register_hook_payload_capture():
    hooks_text = HOOKS_JSON.read_text(encoding="utf-8")

    assert "hook_payload_capture.py" not in hooks_text


def test_corpus_doc_mentions_capture_then_import_workflow():
    doc = CORPUS_DOC.read_text(encoding="utf-8")

    for token in (
        "hook_payload_capture.py",
        "--print-settings-snippet",
        ".athanor/spikes/hook-payloads",
        "FileChanged",
        "import_hook_fixture.py",
        "not registered in repo `hooks/hooks.json`",
    ):
        assert token in doc
