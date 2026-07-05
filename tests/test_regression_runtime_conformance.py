"""Regression tests for cross-runtime conformance.

P9 turns the Claude/Codex companion relationship into an executable contract:
the gate should catch drift without generating manifests or installing hooks.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_CONTRACT = REPO_ROOT / "docs" / "runtime-surface-contract.json"
RUNTIME_DOC = REPO_ROOT / "docs" / "runtime-conformance.md"
RUNTIME_SCHEMA = REPO_ROOT / "schemas" / "runtime-conformance-report.schema.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_report() -> dict:
    result = subprocess.run(
        [sys.executable, "scripts/gates/runtime_conformance.py", "--json"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _run_cli(repo_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/gates/runtime_conformance.py", "--json"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )


def _copy_minimal_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()

    for source in (
        "docs/runtime-surface-contract.json",
        "hooks/catalog.json",
        "hooks/hooks.json",
        ".claude-plugin/plugin.json",
        "plugins/athanor-codex/.codex-plugin/plugin.json",
        "scripts/gates/runtime_conformance.py",
    ):
        src = REPO_ROOT / source
        dest = repo / source
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    for skill_dir in (REPO_ROOT / "skills").iterdir():
        if skill_dir.is_dir() and not skill_dir.name.startswith("."):
            (repo / "skills" / skill_dir.name).mkdir(parents=True)

    codex_skills = REPO_ROOT / "plugins" / "athanor-codex" / "skills"
    for skill_dir in codex_skills.iterdir():
        if skill_dir.is_dir() and not skill_dir.name.startswith("."):
            (repo / "plugins" / "athanor-codex" / "skills" / skill_dir.name).mkdir(
                parents=True
            )

    return repo


def _check_ids(report: dict) -> set[str]:
    return {str(check["id"]) for check in report["checks"]}


def _check_by_id(report: dict, check_id: str) -> dict:
    for check in report["checks"]:
        if check["id"] == check_id:
            return check
    raise AssertionError(f"missing check id: {check_id}")


def test_runtime_surface_contract_exists_and_names_expected_surfaces():
    contract = _load_json(RUNTIME_CONTRACT)

    assert contract["schema_version"] == 1
    assert contract["claude_plugin"]["name"] == "athanor"
    assert contract["codex_companion"]["name"] == "athanor-codex"
    assert "analyze" in contract["claude_plugin"]["native_skills"]
    assert "athanor-analyze" in contract["codex_companion"]["skills"]
    assert "ce-test-browser" in contract["claude_plugin"]["vendored_claude_only_skills"]
    assert "athanor-ce-test-browser" not in contract["codex_companion"]["skills"]


def test_runtime_conformance_docs_state_non_generator_boundary():
    body = RUNTIME_DOC.read_text(encoding="utf-8")

    for token in (
        "read-only verifier",
        "not a generator",
        "hooks/catalog.json",
        "plugins/athanor-codex",
        "ce-test-browser",
        "Cross-runtime conformance gate",
    ):
        assert token in body


def test_runtime_conformance_cli_reports_pass_on_current_repo():
    report = _run_report()

    assert report["schema_version"] == 1
    assert report["status"] == "pass"
    assert report["summary"]["errors"] == 0
    assert report["surfaces"]["claude"]["plugin_name"] == "athanor"
    assert report["surfaces"]["codex"]["plugin_name"] == "athanor-codex"
    assert report["surfaces"]["hooks"]["enabled_events"] == [
        "PostToolUse",
        "PreToolUse",
    ]


def test_runtime_conformance_schema_validates_report():
    report = _run_report()
    schema = _load_json(RUNTIME_SCHEMA)

    jsonschema.validate(report, schema)


def test_runtime_conformance_fails_when_codex_skill_is_missing(tmp_path):
    repo = _copy_minimal_repo(tmp_path)
    shutil.rmtree(repo / "plugins" / "athanor-codex" / "skills" / "athanor-review")

    result = _run_cli(repo)

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["status"] == "fail"
    assert "codex.skills" in _check_ids(report)
    check = _check_by_id(report, "codex.skills")
    assert check["missing"] == ["athanor-review"]
    assert check["unexpected"] == []


def test_runtime_conformance_fails_when_enabled_hook_missing_from_runtime_manifest(
    tmp_path,
):
    repo = _copy_minimal_repo(tmp_path)
    hooks_path = repo / "hooks" / "hooks.json"
    hooks = _load_json(hooks_path)
    hooks["hooks"].pop("PreToolUse", None)
    hooks_path.write_text(json.dumps(hooks, indent=2) + "\n", encoding="utf-8")

    result = _run_cli(repo)

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["status"] == "fail"
    assert "hooks.enabled_runtime_manifest" in _check_ids(report)
    check = _check_by_id(report, "hooks.enabled_runtime_manifest")
    assert check["missing"][0]["event"] == "PreToolUse"


def test_runtime_conformance_fails_when_codex_manifest_adds_hooks(tmp_path):
    repo = _copy_minimal_repo(tmp_path)
    manifest_path = repo / "plugins" / "athanor-codex" / ".codex-plugin" / "plugin.json"
    manifest = _load_json(manifest_path)
    manifest["hooks"] = "./hooks/hooks.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    result = _run_cli(repo)

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["status"] == "fail"
    assert "codex.forbidden_manifest_keys" in _check_ids(report)
    check = _check_by_id(report, "codex.forbidden_manifest_keys")
    assert check["unexpected"] == ["hooks"]
