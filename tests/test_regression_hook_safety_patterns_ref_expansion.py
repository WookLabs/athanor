from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from scripts.hooks import safety_patterns
from scripts.hooks.safety_patterns import SafetyFinding

classify_pretool_payload = safety_patterns.classify_pretool_payload
classify_file_payload = safety_patterns.classify_file_payload
classify_shell_command = safety_patterns.classify_shell_command

REPO_ROOT = Path(__file__).resolve().parents[1]
DISPATCHER = REPO_ROOT / "scripts" / "hooks" / "pretool_dispatcher.py"
CORPUS_DOC = REPO_ROOT / "docs" / "hook-safety-pattern-corpus.md"
CATALOG_DOC = REPO_ROOT / "docs" / "hook-catalog.md"


def _ids(findings: list[SafetyFinding]) -> set[str]:
    return {finding.pattern_id for finding in findings}


def _classify_file_read(tool_name: str, path: str) -> list[SafetyFinding]:
    classifier = getattr(safety_patterns, "classify_file_read", None)
    assert callable(classifier), "safety corpus must expose classify_file_read"
    return classifier(tool_name, path)


def _write_config(project: Path, mode: str) -> None:
    project.mkdir(parents=True, exist_ok=True)
    (project / "athanor.json").write_text(
        json.dumps(
            {
                "version": "1.0",
                "hooks": {
                    "profile": "standard",
                    "freeze": {"mode": "off", "allowedPaths": []},
                    "evidence": {"mode": "warn"},
                    "safetyCorpus": {"mode": mode},
                },
            }
        ),
        encoding="utf-8",
    )


def _run_dispatcher(project: Path, payload: dict) -> tuple[int, str, str]:
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project)
    proc = subprocess.run(
        [sys.executable, str(DISPATCHER)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=str(project),
        env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_ref_expansion_detects_dangerous_deletion_variants() -> None:
    assert "shell-rm-rf-broad-delete" in _ids(classify_shell_command("rm -rf ./build/*"))
    assert "git-clean-force-delete" in _ids(classify_shell_command("git clean -fdx"))


def test_ref_expansion_detects_secret_path_reads() -> None:
    assert "read-env-secret-path" in _ids(_classify_file_read("Read", ".env"))
    assert "read-ssh-private-key-path" in _ids(
        classify_pretool_payload(
            {
                "tool_name": "Read",
                "tool_input": {"file_path": "~/.ssh/id_ed25519"},
            }
        )
    )
    assert _classify_file_read("Read", ".env.example") == []


def test_ref_expansion_detects_edit_and_multiedit_new_strings() -> None:
    edit_payload = {
        "tool_name": "Edit",
        "tool_input": {
            "file_path": "src/config.py",
            "old_string": "OPENAI_API_KEY=''",
            "new_string": "OPENAI_API_KEY='sk-test_123456789012'",
        },
    }
    multiedit_payload = {
        "tool_name": "MultiEdit",
        "tool_input": {
            "file_path": "src/config.py",
            "edits": [
                {
                    "old_string": "GITHUB_TOKEN=''",
                    "new_string": "GITHUB_TOKEN='ghp_12345678901234567890'",
                }
            ],
        },
    }

    assert "write-token-shaped-secret" in _ids(classify_pretool_payload(edit_payload))
    assert "write-token-shaped-secret" in _ids(classify_pretool_payload(multiedit_payload))


def test_ref_expansion_avoids_plain_sk_word_false_positive() -> None:
    assert classify_file_payload("Write", "notes.txt", "skateboarding is a sport") == []


def test_ref_expansion_findings_are_observe_stage_with_promotion_metadata() -> None:
    findings = (
        classify_shell_command("rm -rf ./build/*")
        + classify_shell_command("git clean -fdx")
        + _classify_file_read("Read", ".env")
    )
    assert findings
    for record in [finding.to_record() for finding in findings]:
        assert record["stage"] == "observe"
        assert record["source_ref"].startswith("ref/")
        assert record["risk"] in {"medium", "high"}
        assert "promotion" in record["promotion_condition"].lower()


def test_observe_mode_records_broad_delete_without_blocking(tmp_path: Path) -> None:
    _write_config(tmp_path, "observe")
    rc, out, err = _run_dispatcher(
        tmp_path,
        {"tool_name": "Bash", "tool_input": {"command": "rm -rf ./build/*"}},
    )

    assert rc == 0
    assert out == ""
    assert err == ""
    log_path = tmp_path / ".athanor" / "hook-safety.jsonl"
    records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert records[0]["pattern_id"] == "shell-rm-rf-broad-delete"
    assert records[0]["stage"] == "observe"


def test_hook_docs_expose_list_info_preview_apply_flow() -> None:
    catalog = CATALOG_DOC.read_text(encoding="utf-8")
    corpus = CORPUS_DOC.read_text(encoding="utf-8")
    for token in (
        "list -> info -> preview -> dry-run install -> explicit apply",
        "List metadata",
        "Info metadata",
        "dry-run install",
        "explicit apply",
    ):
        assert token in catalog
    for token in (
        "source_ref",
        "promotion_condition",
    ):
        assert token in corpus
