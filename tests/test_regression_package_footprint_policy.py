"""Regression tests for the P21 package footprint policy gate."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "gates" / "package_footprint_policy.py"
SCHEMA = REPO_ROOT / "schemas" / "package-footprint-policy-report.schema.json"
DOC = REPO_ROOT / "docs" / "package-footprint-policy.md"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_module():
    spec = importlib.util.spec_from_file_location("package_footprint_policy", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_cli_emits_schema_valid_read_only_report_on_current_repo() -> None:
    assert SCRIPT.is_file(), "P21 gate script must exist"
    assert SCHEMA.is_file(), "P21 report schema must exist"

    proc = _run_cli("--json")

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    jsonschema.validate(report, _load_json(SCHEMA))
    assert report["schema_version"] == 1
    assert report["status"] in {"pass", "warn"}
    assert report["profile"]["mutates_files_by_default"] is False
    assert report["profile"]["external_telemetry"] is False
    assert report["summary"]["irreversible_actions"] == 0
    assert report["package"]["file_count"] > 0
    assert report["package"]["total_bytes"] > 0


def test_current_repo_reports_dev_only_candidates_without_failing_default() -> None:
    proc = _run_cli("--json")

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["status"] == "warn"
    check_ids = {check["id"] for check in report["checks"]}
    assert "footprint.dev_only_candidates" in check_ids

    candidate_paths = {candidate["path"] for candidate in report["dev_only_candidates"]}
    assert any(path.startswith("tests/") for path in candidate_paths)
    assert any(path.startswith("docs/plans/") for path in candidate_paths)
    assert not any(path.startswith(".venv/") for path in candidate_paths)
    assert all(
        candidate["recommended_action"] == "exclude-from-ship-profile"
        for candidate in report["dev_only_candidates"]
    )


def test_strict_mode_fails_on_warn_only_dev_candidates(tmp_path: Path) -> None:
    root = tmp_path / "plugin"
    (root / ".claude-plugin").mkdir(parents=True)
    (root / "skills" / "work").mkdir(parents=True)
    (root / "tests").mkdir(parents=True)
    (root / ".claude-plugin" / "plugin.json").write_text(
        '{"name":"athanor","version":"1.0.0"}\n',
        encoding="utf-8",
    )
    (root / "skills" / "work" / "SKILL.md").write_text(
        "---\nname: work\ndescription: fixture\n---\n",
        encoding="utf-8",
    )
    (root / "tests" / "test_fixture.py").write_text("def test_fixture(): pass\n", encoding="utf-8")

    default_proc = _run_cli("--repo-root", str(root), "--json")
    strict_proc = _run_cli("--repo-root", str(root), "--strict", "--json")

    assert default_proc.returncode == 0, default_proc.stderr
    assert json.loads(default_proc.stdout)["status"] == "warn"
    assert strict_proc.returncode == 1
    assert json.loads(strict_proc.stdout)["status"] == "warn"


def test_total_byte_budget_failure_is_hard_fail(tmp_path: Path) -> None:
    root = tmp_path / "plugin"
    root.mkdir()
    (root / "README.md").write_text("fixture\n", encoding="utf-8")

    proc = _run_cli("--repo-root", str(root), "--max-total-bytes", "1", "--json")

    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert report["status"] == "fail"
    failing_checks = {check["id"] for check in report["checks"] if check["status"] == "fail"}
    assert "footprint.total_bytes_budget" in failing_checks


def test_build_report_classifies_ship_profile_buckets(tmp_path: Path) -> None:
    module = _load_module()
    root = tmp_path / "plugin"
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / "docs" / "plans").mkdir(parents=True)
    (root / "docs" / "archive").mkdir(parents=True)
    (root / "skills" / "work").mkdir(parents=True)
    (root / "tests").mkdir(parents=True)
    (root / ".claude-plugin" / "plugin.json").write_text("{}", encoding="utf-8")
    (root / ".python-version").write_text("3.14\n", encoding="utf-8")
    (root / "pyproject.toml").write_text("[project]\nname = \"fixture\"\n", encoding="utf-8")
    (root / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    (root / ".github" / "workflows" / "validate.yml").write_text("name: ci\n", encoding="utf-8")
    (root / "docs" / "plans" / "2026-06-18-plan.md").write_text("plan\n", encoding="utf-8")
    (root / "docs" / "archive" / "STATE-history.md").write_text("history\n", encoding="utf-8")
    (root / "skills" / "work" / "SKILL.md").write_text("skill\n", encoding="utf-8")
    (root / "tests" / "test_work.py").write_text("test\n", encoding="utf-8")

    report = module.build_report(repo_root=root)

    buckets = {item["bucket"]: item for item in report["classifications"]}
    assert buckets["runtime"]["files"] == 1
    assert buckets["distribution_metadata"]["files"] == 1
    assert buckets["development_metadata"]["files"] == 3
    assert buckets["development_ci"]["files"] == 1
    assert buckets["development_history"]["files"] == 2
    assert buckets["tests"]["files"] == 1
    candidate_paths = {candidate["path"] for candidate in report["dev_only_candidates"]}
    assert candidate_paths >= {
        ".github/workflows/validate.yml",
        "docs/plans/2026-06-18-plan.md",
        "docs/archive/STATE-history.md",
        "tests/test_work.py",
    }
    decision_prefixes = {decision["path_prefix"] for decision in report["ship_profile_decisions"]}
    assert ".venv/" in decision_prefixes
    assert {".python-version", "pyproject.toml", "uv.lock"} <= decision_prefixes


def test_operator_docs_explain_ship_profile_and_read_only_policy() -> None:
    assert DOC.is_file(), "P21 operator doc must exist"
    body = DOC.read_text(encoding="utf-8")
    for token in (
        "ship profile",
        "repo-local",
        "dev-only candidates",
        "read-only",
        "exclude-from-ship-profile",
        "scripts/gates/package_footprint_policy.py",
    ):
        assert token in body


def test_build_report_uses_pruned_walk_instead_of_recursive_rglob(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _load_module()
    root = tmp_path / "plugin"
    root.mkdir()
    (root / "README.md").write_text("fixture\n", encoding="utf-8")
    (root / "ref").mkdir()
    (root / "ref" / "external.py").write_text("external\n", encoding="utf-8")

    def _raise_on_rglob(self, pattern):  # noqa: ANN001
        raise AssertionError("package footprint policy must prune excluded dirs before traversal")

    monkeypatch.setattr(Path, "rglob", _raise_on_rglob)

    report = module.build_report(repo_root=root)

    assert report["package"]["file_count"] == 1
    assert report["ship_profile"]["file_count"] == 1
