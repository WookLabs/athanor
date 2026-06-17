"""Regression tests for the P23 native runtime playbook gate."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "gates" / "native_runtime_playbook.py"
SCHEMA = REPO_ROOT / "schemas" / "native-runtime-playbook-report.schema.json"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "native_runtime_probe"
DOC = REPO_ROOT / "docs" / "native-runtime-playbook.md"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _recipes_by_backend(playbook: dict) -> dict[str, dict]:
    return {recipe["backend"]: recipe for recipe in playbook["recipes"]}


def _successful_playbooks(report: dict) -> list[dict]:
    return [
        fixture["playbook"]
        for fixture in report["fixtures"]
        if fixture["playbook"]["status"] == "pass"
    ]


def test_fixture_gate_emits_schema_valid_operator_playbooks() -> None:
    proc = _run_cli("--fixture-root", str(FIXTURES), "--json")

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    jsonschema.validate(report, _load_json(SCHEMA))
    assert report["schema_version"] == 1
    assert report["status"] == "pass"
    assert report["summary"]["fixtures"] == 3
    assert report["summary"]["failed"] == 0
    assert report["summary"]["auto_executable_recipes"] == 0
    assert report["summary"]["irreversible_actions"] == 0

    recipes: dict[str, dict] = {}
    for playbook in _successful_playbooks(report):
        recipes.update(_recipes_by_backend(playbook))

    for backend in ("manual-worktree", "dynamic-workflow", "agent-team"):
        assert backend in recipes
        recipe = recipes[backend]
        assert recipe["dry_run_source_mode"] == "dry-run-only"
        assert recipe["auto_execute"] is False
        assert recipe["operator_approval_required"] is True
        assert recipe["mutates_files_by_default"] is False
        assert recipe["external_telemetry"] is False
        assert "I approve" in recipe["approval_prompt"]
        assert backend in recipe["approval_prompt"]


def test_manual_worktree_recipe_has_preflight_creation_and_cleanup() -> None:
    proc = _run_cli("--fixture-root", str(FIXTURES), "--json")

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    recipes: dict[str, dict] = {}
    for playbook in _successful_playbooks(report):
        recipes.update(_recipes_by_backend(playbook))

    worktree = recipes["manual-worktree"]
    preflight = "\n".join(worktree["preflight_commands"])
    commands = "\n".join(worktree["manual_commands"])
    cleanup = "\n".join(worktree["cleanup_commands"])
    assert "git status --short" in preflight
    assert "git worktree list --porcelain" in preflight
    assert "git worktree add" in commands
    assert "git worktree remove" in cleanup
    assert "git worktree prune" in cleanup
    assert any("worktree" in item for item in worktree["evidence_required"])


def test_profile_autolaunch_violation_stays_blocked(tmp_path: Path) -> None:
    profile = tmp_path / "profile.json"
    profile.write_text(
        json.dumps(
            {
                "id": "autolaunch-blocked",
                "surfaces": {
                    "agent_team": {
                        "status": "available",
                        "auto_launch_allowed": True,
                        "evidence_refs": ["unit"],
                    }
                },
                "requested_backends": ["agent-team"],
            }
        ),
        encoding="utf-8",
    )

    proc = _run_cli("--profile", str(profile), "--json")

    assert proc.returncode == 1
    playbook = json.loads(proc.stdout)
    assert playbook["status"] == "fail"
    assert playbook["recipes"] == []
    assert "auto_launch_not_allowed" in {error["code"] for error in playbook["errors"]}
    assert playbook["summary"]["auto_executable_recipes"] == 0
    assert playbook["summary"]["irreversible_actions"] == 0


def test_live_profile_playbook_shape_is_read_only(tmp_path: Path) -> None:
    profile = tmp_path / "profile.json"
    profile.write_text(
        json.dumps(
            {
                "id": "read-only-shape",
                "surfaces": {
                    "worktree": {
                        "status": "manual",
                        "evidence_refs": ["git worktree list --porcelain"],
                    },
                    "dynamic_workflow": {
                        "status": "documented",
                        "evidence_refs": ["Claude Code dynamic workflows documentation"],
                    },
                },
                "requested_backends": ["manual-worktree", "dynamic-workflow"],
            }
        ),
        encoding="utf-8",
    )

    proc = _run_cli("--profile", str(profile), "--json")

    assert proc.returncode == 0, proc.stderr
    playbook = json.loads(proc.stdout)
    assert playbook["profile_id"] == "read-only-shape"
    assert playbook["status"] == "pass"
    assert playbook["safety"]["read_only_report"] is True
    assert playbook["safety"]["executes_commands"] is False
    assert playbook["safety"]["writes_runtime_state"] is False
    assert playbook["summary"]["auto_executable_recipes"] == 0
    assert playbook["summary"]["irreversible_actions"] == 0


def test_schema_docs_and_architecture_are_tracked() -> None:
    assert SCHEMA.is_file()
    assert DOC.is_file()
    assert (
        REPO_ROOT
        / "docs"
        / "architecture"
        / "2026-06-18-p23-native-runtime-playbook-design.md"
    ).is_file()
    assert (
        REPO_ROOT
        / "docs"
        / "plans"
        / "2026-06-18-p23-native-runtime-playbook-plan.md"
    ).is_file()
