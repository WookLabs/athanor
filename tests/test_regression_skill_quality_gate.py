"""Regression tests for the reusable skill quality gate."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.gates.check_skill_quality import build_report

REPO_ROOT = Path(__file__).resolve().parent.parent


def _write_skill(root: Path, rel: str, frontmatter: str, body: str) -> Path:
    path = root / rel / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter}---\n\n{body}\n", encoding="utf-8")
    return path


def _write_mirror_inputs(
    root: Path,
    *,
    parent_skills: list[str] | None = None,
    codex_skills: list[str] | None = None,
) -> tuple[Path, Path]:
    parent_skills = parent_skills or ["plan"]
    codex_skills = codex_skills or ["athanor-plan"]
    docs = root / "docs"
    docs.mkdir(parents=True, exist_ok=True)

    contract = {
        "schema_version": 1,
        "claude_plugin": {
            "native_skills": parent_skills,
            "vendored_claude_only_skills": [],
        },
        "codex_companion": {"skills": codex_skills},
    }
    contract_path = docs / "runtime-surface-contract.json"
    contract_path.write_text(json.dumps(contract), encoding="utf-8")

    rows = [
        "| Claude surface | Claude source | Codex surface | Codex source | Status | Description anchor |",
        "|---|---|---|---|---|---|",
    ]
    for parent, codex in zip(parent_skills, codex_skills, strict=True):
        rows.append(
            f"| {parent} | `skills/{parent}/SKILL.md` | {codex} | "
            f"`plugins/athanor-codex/skills/{codex}/SKILL.md` | mirror | plan |"
        )
    source_map_path = docs / "codex-mirror-source-map.md"
    source_map_path.write_text(
        "\n".join(rows)
        + "\n\n"
        + "\n".join(
            [
                "Unsupported Claude-only runtime surfaces:",
                "- hook-backed enforcement",
                "- Claude PreToolUse",
                "- Claude Task",
                "- Freeze enforcement",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return contract_path, source_map_path


def _valid_fixture(root: Path) -> tuple[Path, Path]:
    _write_skill(
        root,
        "skills/plan",
        "name: plan\ndescription: Parent plan skill.\n",
        "Use plan mode. plan.",
    )
    _write_skill(
        root,
        "plugins/athanor-codex/skills/athanor-plan",
        "name: athanor-plan\ndescription: Codex plan skill.\n",
        "Use Codex plan mode. plan. Do not claim hook-backed enforcement.",
    )
    return _write_mirror_inputs(root)


def test_current_repo_skill_quality_gate_passes() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/gates/check_skill_quality.py", "--json"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads(result.stdout)
    assert report["schema_version"] == 1
    assert report["status"] == "pass"
    assert report["profile"]["id"] == "skill-quality"
    assert report["profile"]["mutates_files_by_default"] is False
    assert report["checks_by_id"]["skills.frontmatter"]["status"] == "pass"
    assert report["checks_by_id"]["mirror.source_map_coverage"]["status"] == "pass"
    assert report["checks_by_id"]["codex.unsupported_runtime_claims"]["status"] == "pass"
    assert report["checks_by_id"]["codex.lfg_loop_reference_concepts"]["status"] == "pass"


def test_gate_reports_missing_frontmatter_and_empty_description(tmp_path: Path) -> None:
    contract_path, source_map_path = _valid_fixture(tmp_path)
    bad = tmp_path / "skills" / "bad" / "SKILL.md"
    bad.parent.mkdir(parents=True)
    bad.write_text("No frontmatter here.\n", encoding="utf-8")
    _write_skill(
        tmp_path,
        "plugins/athanor-codex/skills/empty-description",
        "name: empty-description\ndescription: ''\n",
        "Empty description fixture.",
    )

    report, exit_code = build_report(
        repo_root=tmp_path,
        contract_path=contract_path,
        source_map_path=source_map_path,
    )

    assert exit_code == 1
    check = report["checks_by_id"]["skills.frontmatter"]
    assert check["status"] == "fail"
    assert "skills/bad/SKILL.md" in check["invalid_paths"]
    assert "plugins/athanor-codex/skills/empty-description/SKILL.md" in check["invalid_paths"]


def test_gate_ignores_runtime_disclaimers_but_flags_positive_claims(
    tmp_path: Path,
) -> None:
    contract_path, source_map_path = _valid_fixture(tmp_path)
    report, exit_code = build_report(
        repo_root=tmp_path,
        contract_path=contract_path,
        source_map_path=source_map_path,
    )
    assert exit_code == 0, report

    codex_skill = tmp_path / "plugins" / "athanor-codex" / "skills" / "athanor-plan" / "SKILL.md"
    codex_skill.write_text(
        "---\n"
        "name: athanor-plan\n"
        "description: Codex plan skill.\n"
        "---\n\n"
        "plan. Claude PreToolUse enforcement blocks unsafe edits.\n",
        encoding="utf-8",
    )

    report, exit_code = build_report(
        repo_root=tmp_path,
        contract_path=contract_path,
        source_map_path=source_map_path,
    )

    assert exit_code == 1
    check = report["checks_by_id"]["codex.unsupported_runtime_claims"]
    assert check["status"] == "fail"
    assert check["claims"][0]["path"] == "plugins/athanor-codex/skills/athanor-plan/SKILL.md"
    assert "Claude PreToolUse enforcement blocks" in check["claims"][0]["line"]


def test_gate_surfaces_lfg_loop_companion_reference_drift(tmp_path: Path) -> None:
    _write_skill(
        tmp_path,
        "skills/lfg-loop",
        "name: lfg-loop\ndescription: Parent loop skill.\n",
        "plan lfg-loop receipt-validator 3-tier CNNN-lfg-receipt.md "
        "G-markers maxIterations all_valid UNDETERMINED invalid_steps_present. "
        "No hidden completion hook. state.json cycle_state cycle_phase "
        "current_cycle acting_on loop_run_log last_receipt_path "
        "last_validator_status tier3_pending evidence/latest.json. "
        "R000-research-receipt.md P000-planning-receipt.md "
        "A000-architecture-receipt.md status: skipped loop.md "
        "Accepted plan path Public contracts.",
    )
    _write_skill(
        tmp_path,
        "plugins/athanor-codex/skills/athanor-lfg-loop",
        "name: athanor-lfg-loop\ndescription: Codex loop skill.\n",
        "plan lfg-loop receipt-validator 3-tier G-markers.",
    )
    contract_path, source_map_path = _write_mirror_inputs(
        tmp_path,
        parent_skills=["lfg-loop"],
        codex_skills=["athanor-lfg-loop"],
    )

    report, exit_code = build_report(
        repo_root=tmp_path,
        contract_path=contract_path,
        source_map_path=source_map_path,
    )

    assert exit_code == 1
    check = report["checks_by_id"]["codex.lfg_loop_reference_concepts"]
    assert check["status"] == "fail"
    assert "CNNN-lfg-receipt.md" in check["missing"]
    assert "UNDETERMINED" in check["missing"]
    assert "No hidden completion hook" in check["missing"]
    assert "state.json" in check["missing"]
    assert "loop_run_log" in check["missing"]
    assert "R000-research-receipt.md" in check["missing"]
    assert "P000-planning-receipt.md" in check["missing"]
    assert "A000-architecture-receipt.md" in check["missing"]
