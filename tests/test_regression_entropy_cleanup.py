"""Regression tests for the P11 entropy cleanup report gate."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "gates" / "entropy_cleanup.py"
SCHEMA = REPO_ROOT / "schemas" / "entropy-cleanup-report.schema.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_cli(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(repo_root), "--json", *args],
        cwd=REPO_ROOT,
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


def _check_by_id(report: dict, check_id: str) -> dict:
    for check in report["checks"]:
        if check["id"] == check_id:
            return check
    raise AssertionError(f"missing check id: {check_id}")


def _action_ids(report: dict) -> set[str]:
    return {str(action["id"]) for action in report["actions"]}


def test_entropy_cleanup_cli_emits_schema_valid_report_for_current_repo() -> None:
    proc = _run_cli(REPO_ROOT, "--ref-warn-days", "99999")

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    jsonschema.validate(report, _load_json(SCHEMA))
    assert report["schema_version"] == 1
    assert report["status"] in {"pass", "warn"}
    assert report["summary"]["errors"] == 0
    for category in ("plans", "hook_candidates", "refs", "mirrors"):
        assert category in report["categories"]
    assert "mirrors.runtime_conformance" in {check["id"] for check in report["checks"]}


def test_capture_only_candidate_missing_lifecycle_metadata_fails(tmp_path: Path) -> None:
    repo = _copy_minimal_repo(tmp_path)
    catalog_path = repo / "hooks" / "catalog.json"
    catalog = _load_json(catalog_path)
    for entry in catalog["hooks"]:
        if entry["runtime_default"] == "capture-only":
            entry.pop("candidate_since", None)
            entry.pop("review_after_days", None)
            break
    catalog_path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")

    proc = _run_cli(repo)

    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert report["status"] == "fail"
    check = _check_by_id(report, "hook_candidates.lifecycle_metadata")
    assert check["status"] == "fail"
    assert check["details"]["missing"][0]["field"] == "candidate_since"


def test_old_capture_only_candidate_emits_warning_action(tmp_path: Path) -> None:
    repo = _copy_minimal_repo(tmp_path)
    catalog_path = repo / "hooks" / "catalog.json"
    catalog = _load_json(catalog_path)
    for entry in catalog["hooks"]:
        if entry["runtime_default"] == "capture-only":
            entry["candidate_since"] = "2026-01-01"
            entry["review_after_days"] = 1
    catalog_path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")

    proc = _run_cli(repo)

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["status"] == "warn"
    assert "review-hook-candidates" in _action_ids(report)


def test_old_plan_with_unchecked_steps_emits_warning_action(tmp_path: Path) -> None:
    repo = _copy_minimal_repo(tmp_path)
    plan_dir = repo / "docs" / "plans"
    plan_dir.mkdir(parents=True)
    (plan_dir / "2026-01-01-old-plan.md").write_text(
        "# Old Plan\n\n- [ ] **Step 1: Finish the work**\n",
        encoding="utf-8",
    )

    proc = _run_cli(repo, "--plan-warn-days", "1")

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["status"] == "warn"
    assert "review-open-plans" in _action_ids(report)


def test_runtime_conformance_failure_is_reported_as_mirror_failure(tmp_path: Path) -> None:
    repo = _copy_minimal_repo(tmp_path)
    shutil.rmtree(repo / "plugins" / "athanor-codex" / "skills" / "athanor-review")

    proc = _run_cli(repo)

    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert report["status"] == "fail"
    check = _check_by_id(report, "mirrors.runtime_conformance")
    assert check["status"] == "fail"
    assert "codex.skills" in check["details"]["failed_checks"]
