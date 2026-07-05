"""Regression tests for the P25 package-facing knowledge index gate."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "gates" / "package_knowledge_index.py"
SCHEMA = REPO_ROOT / "schemas" / "package-knowledge-index-report.schema.json"
INDEX = REPO_ROOT / "docs" / "package-knowledge-index.md"

REQUIRED_DOCS = {
    "docs/distribution-smoke.md",
    "docs/package-footprint-policy.md",
    "docs/package-footprint-reduction.md",
    "docs/maintenance-profile.md",
    "docs/harness-decision-ledger.md",
    "docs/native-runtime-probe.md",
    "docs/native-runtime-playbook.md",
    "docs/reactive-channel-fixtures.md",
    "docs/work-item-stage-transitions.md",
    "docs/memory-index.md",
    "docs/memory-retrieval-eval.md",
    "docs/workflow-trace-evals.md",
    "docs/handoff-artifact.md",
    "docs/durable-loop-controller.md",
    "docs/catalog-admission-policy.md",
    "docs/codex-mirror-source-map.md",
}
REQUIRED_GATES = {
    "scripts/gates/check_skill_quality.py",
    "scripts/gates/distribution_smoke.py",
    "scripts/gates/package_footprint_policy.py",
    "scripts/gates/maintenance_profile.py",
    "scripts/gates/harness_decision_ledger.py",
    "scripts/gates/native_runtime_probe.py",
    "scripts/gates/native_runtime_playbook.py",
    "scripts/gates/reactive_channel_fixture.py",
    "scripts/gates/work_item_stage.py",
    "scripts/gates/memory_index.py",
    "scripts/gates/memory_retrieval_eval.py",
    "scripts/evals/workflow_trace_query.py",
    "scripts/loops/loop_run_log.py",
    "scripts/loops/check_pre_lfg_stage_receipts.py",
    "scripts/gates/catalog_admission.py",
    "scripts/gates/codex_mirror_parity.py",
}

RELEASE_FACING_CLIS = {
    "scripts/gates/check_skill_quality.py",
    "scripts/loops/check_pre_lfg_stage_receipts.py",
}


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


def test_cli_emits_schema_valid_runtime_facing_report() -> None:
    assert SCRIPT.is_file(), "P25 gate script must exist"
    assert SCHEMA.is_file(), "P25 report schema must exist"
    assert INDEX.is_file(), "P25 package-facing index must exist"

    proc = _run_cli("--json")

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    jsonschema.validate(report, _load_json(SCHEMA))
    assert report["schema_version"] == 1
    assert report["status"] == "pass"
    assert report["profile"]["mutates_files_by_default"] is False
    assert report["profile"]["external_telemetry"] is False
    assert report["summary"]["irreversible_actions"] == 0
    assert report["summary"]["forbidden_refs"] == 0
    assert report["summary"]["unresolved_links"] == 0
    assert report["summary"]["missing_required_refs"] == 0


def test_index_links_current_docs_and_gates_without_history_surface() -> None:
    proc = _run_cli("--json")

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    refs = {item["path"]: item for item in report["required_refs"]}
    assert REQUIRED_DOCS <= set(refs)
    assert REQUIRED_GATES <= set(refs)
    assert all(refs[path]["status"] == "pass" for path in REQUIRED_DOCS | REQUIRED_GATES)
    assert report["forbidden_refs"] == []

    body = INDEX.read_text(encoding="utf-8")
    assert "docs/plans/" not in body
    assert "docs/archive/" not in body
    assert "docs/architecture/" not in body
    assert "tests/" not in body
    assert "ref/" not in body


def test_readme_and_claude_link_to_package_index() -> None:
    proc = _run_cli("--json")

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    entry_points = {item["path"]: item for item in report["entry_points"]}
    assert entry_points["README.md"]["status"] == "pass"
    assert entry_points["CLAUDE.md"]["status"] == "pass"
    assert "docs/package-knowledge-index.md" in entry_points["README.md"]["links"]
    assert "docs/package-knowledge-index.md" in entry_points["CLAUDE.md"]["links"]


def test_forbidden_history_link_fails_gate(tmp_path: Path) -> None:
    root = tmp_path / "plugin"
    _write_minimal_index_root(root)
    index = root / "docs" / "package-knowledge-index.md"
    index.write_text(
        index.read_text(encoding="utf-8")
        + "\nForbidden: [old plan](plans/2026-06-18-old-plan.md)\n",
        encoding="utf-8",
    )
    (root / "docs" / "plans").mkdir(parents=True)
    (root / "docs" / "plans" / "2026-06-18-old-plan.md").write_text(
        "history\n",
        encoding="utf-8",
    )

    proc = _run_cli("--repo-root", str(root), "--json")

    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert report["status"] == "fail"
    assert report["summary"]["forbidden_refs"] == 1
    assert report["forbidden_refs"][0]["path"] == "docs/plans/2026-06-18-old-plan.md"


def test_missing_entry_point_backlink_fails_gate(tmp_path: Path) -> None:
    root = tmp_path / "plugin"
    _write_minimal_index_root(root)
    (root / "CLAUDE.md").write_text("No index link here.\n", encoding="utf-8")

    proc = _run_cli("--repo-root", str(root), "--json")

    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    assert report["status"] == "fail"
    entry_points = {item["path"]: item for item in report["entry_points"]}
    assert entry_points["CLAUDE.md"]["status"] == "fail"


def test_missing_release_facing_cli_links_fail_gate(tmp_path: Path) -> None:
    root = tmp_path / "plugin"
    _write_minimal_index_root(root)
    index = root / "docs" / "package-knowledge-index.md"
    body = index.read_text(encoding="utf-8")
    for rel in RELEASE_FACING_CLIS:
        body = body.replace(f"- [{rel}](../{rel})\n", "")
    index.write_text(body, encoding="utf-8")

    proc = _run_cli("--repo-root", str(root), "--json")

    assert proc.returncode == 1
    report = json.loads(proc.stdout)
    failing_required_refs = {
        item["path"]
        for item in report["required_refs"]
        if item["status"] == "fail"
    }
    assert RELEASE_FACING_CLIS <= failing_required_refs


def _write_minimal_index_root(root: Path) -> None:
    for rel in REQUIRED_DOCS | REQUIRED_GATES:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{rel}\n", encoding="utf-8")
    (root / "README.md").write_text(
        "[Package knowledge index](docs/package-knowledge-index.md)\n",
        encoding="utf-8",
    )
    (root / "CLAUDE.md").write_text(
        "[Package knowledge index](docs/package-knowledge-index.md)\n",
        encoding="utf-8",
    )
    docs = "\n".join(f"- [{rel}]({rel.removeprefix('docs/')})" for rel in sorted(REQUIRED_DOCS))
    gates = "\n".join(f"- [{rel}](../{rel})" for rel in sorted(REQUIRED_GATES))
    (root / "docs" / "package-knowledge-index.md").write_text(
        f"""# Package Knowledge Index

Last reviewed: 2026-06-18.

## Runtime Surface

- README and CLAUDE point here.

## Operator Gate Map

{docs}

{gates}

## Safety Contracts

- read-only, no external telemetry, irreversible actions stay 0.

## Ship Profile Boundary

- repo-local history stays outside this package-facing index.

## Freshness

- Run `python scripts/gates/package_knowledge_index.py --json`.
""",
        encoding="utf-8",
    )
