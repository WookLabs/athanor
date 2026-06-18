"""Regression tests for the UserPromptSubmit log-only spike harness."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS_JSON = REPO_ROOT / "hooks" / "hooks.json"
SPIKE_DOC = REPO_ROOT / "docs" / "spikes" / "userpromptsubmit-spike.md"
SPIKE_SCRIPT = REPO_ROOT / "scripts" / "hooks" / "user_prompt_submit_spike.py"
ROADMAP = REPO_ROOT / "docs" / "ROADMAP.md"

sys.path.insert(0, str(REPO_ROOT / "scripts" / "hooks"))


def _payload() -> dict:
    return {
        "hook_event_name": "UserPromptSubmit",
        "session_id": "sess-123",
        "prompt": "secret prompt text that must not be copied into summaries",
        "cwd": str(REPO_ROOT),
        "nested": {
            "messages": [
                {"role": "user", "content": "another sensitive prompt"},
            ],
        },
    }


def _raw_payload_files(path: Path) -> list[Path]:
    return sorted(
        p for p in path.glob("ups-payload-*.json")
        if not p.name.endswith(".summary.json")
    )


def _summary_payload_files(path: Path) -> list[Path]:
    return sorted(path.glob("ups-payload-*.summary.json"))


def test_userpromptsubmit_spike_script_exists_and_is_importable():
    assert SPIKE_SCRIPT.is_file(), f"missing spike harness at {SPIKE_SCRIPT}"
    import user_prompt_submit_spike

    assert callable(user_prompt_submit_spike.main)


def test_userpromptsubmit_spike_reuses_shared_capture_utils():
    body = SPIKE_SCRIPT.read_text(encoding="utf-8")

    assert "hook_capture_utils" in body
    assert "capture_payload" in body


def test_valid_payload_writes_raw_and_redacted_summary(tmp_path):
    import user_prompt_submit_spike

    output_dir = tmp_path / "spikes"
    rc = user_prompt_submit_spike.capture_payload(_payload(), output_dir)

    assert rc == 0
    raw_files = _raw_payload_files(output_dir)
    summary_files = _summary_payload_files(output_dir)
    assert len(raw_files) == 1
    assert len(summary_files) == 1

    raw = json.loads(raw_files[0].read_text(encoding="utf-8"))
    assert raw["prompt"] == _payload()["prompt"]

    summary_text = summary_files[0].read_text(encoding="utf-8")
    assert _payload()["prompt"] not in summary_text
    assert "another sensitive prompt" not in summary_text
    summary = json.loads(summary_text)
    assert summary["schema_version"] == 1
    assert summary["event_name"] == "UserPromptSubmit"
    assert summary["top_level_keys"] == [
        "cwd",
        "hook_event_name",
        "nested",
        "prompt",
        "session_id",
    ]
    assert len(summary["raw_sha256"]) == 64
    assert summary["shape"]["prompt"]["type"] == "str"
    assert summary["shape"]["prompt"]["length"] == len(_payload()["prompt"])
    assert "sha256_12" in summary["shape"]["prompt"]


def test_hook_mode_malformed_stdin_exits_zero_and_writes_nothing(tmp_path):
    proc = subprocess.run(
        [
            sys.executable,
            str(SPIKE_SCRIPT),
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
            str(SPIKE_SCRIPT),
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


def test_print_settings_snippet_does_not_mutate_repo(tmp_path):
    claude_dir_existed = (REPO_ROOT / ".claude").exists()
    proc = subprocess.run(
        [
            sys.executable,
            str(SPIKE_SCRIPT),
            "--project-root",
            str(REPO_ROOT),
            "--print-settings-snippet",
        ],
        text=True,
        capture_output=True,
        cwd=str(REPO_ROOT),
    )

    assert proc.returncode == 0
    assert "UserPromptSubmit" in proc.stdout
    assert "user_prompt_submit_spike.py" in proc.stdout
    snippet = json.loads(proc.stdout)
    command = snippet["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
    assert str(SPIKE_SCRIPT) in command
    assert (REPO_ROOT / ".claude").exists() is claude_dir_existed


def test_repo_hooks_json_still_does_not_register_userpromptsubmit():
    hooks = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))["hooks"]

    assert "UserPromptSubmit" not in hooks


def test_capability_probe_reports_spike_harness_available():
    import capability_probe

    report = capability_probe.build_capability_report(REPO_ROOT)
    ups = report["events"]["UserPromptSubmit"]
    assert ups["supported"] is False
    assert ups["registered_in_hooks_json"] is False
    assert ups["spike_harness_available"] is True
    assert ups["live_payload_captured"] is False
    assert ups["latest_payload_summary"] is None


def test_spike_doc_and_roadmap_point_to_harness():
    assert SPIKE_DOC.is_file(), f"missing spike doc at {SPIKE_DOC}"
    doc = SPIKE_DOC.read_text(encoding="utf-8")
    for token in (
        "user_prompt_submit_spike.py",
        "--print-settings-snippet",
        ".athanor/spikes",
        "Redacted summary",
    ):
        assert token in doc

    roadmap = ROADMAP.read_text(encoding="utf-8")
    assert "docs/spikes/userpromptsubmit-spike.md" in roadmap
