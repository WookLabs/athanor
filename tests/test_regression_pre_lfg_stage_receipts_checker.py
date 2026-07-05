"""Regression tests for the pre-LFG stage receipt readiness checker."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPO_ROOT / "scripts" / "loops" / "check_pre_lfg_stage_receipts.py"


def _write_receipt(loop_dir: Path, filename: str, body: str) -> None:
    receipt_path = loop_dir / "receipts" / filename
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(body.strip() + "\n", encoding="utf-8")


def _valid_loop_dir(tmp_path: Path) -> Path:
    loop_dir = tmp_path / ".athanor" / "loops" / "loop-1234"
    loop_dir.mkdir(parents=True)
    (loop_dir / "loop.md").write_text("# Loop\n", encoding="utf-8")
    _write_receipt(
        loop_dir,
        "R000-research-receipt.md",
        """
        status: complete
        loop: loop.md
        Source files: skills/lfg-loop/SKILL.md
        External references: none
        Unresolved facts: none
        Findings: pre-cycle contract is local.
        """,
    )
    _write_receipt(
        loop_dir,
        "P000-planning-receipt.md",
        """
        status: complete
        loop_ref: loop.md
        Accepted plan path: .athanor/sessions/2026-07-05-001/plan.md
        Acceptance markers: AM-1
        Verification commands: pytest tests/test_regression_pre_lfg_stage_receipts_checker.py
        Cycle boundaries: C001 only
        Known risks: checker is heuristic.
        """,
    )
    _write_receipt(
        loop_dir,
        "A000-architecture-receipt.md",
        """
        status: skipped
        reason: no public contracts or cross-module design decisions were needed for this loop.
        loop.md
        Public contracts: unchanged
        Cross-module design decisions: none
        Rejected alternatives: none
        Follow-up constraints: keep checker read-only.
        """,
    )
    return loop_dir


def _run_checker(loop_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), "--loop-dir", str(loop_dir), "--json"],
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


def test_pre_lfg_receipt_checker_passes_valid_receipts(tmp_path: Path) -> None:
    loop_dir = _valid_loop_dir(tmp_path)

    proc = _run_checker(loop_dir)

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["schema_version"] == 1
    assert report["status"] == "pass"
    assert report["loop_dir"] == str(loop_dir)
    assert {stage["stage"] for stage in report["stages"]} == {
        "research",
        "planning",
        "architecture",
    }
    assert all(stage["status"] == "pass" for stage in report["stages"])


def test_pre_lfg_receipt_checker_reports_missing_and_invalid_evidence(
    tmp_path: Path,
) -> None:
    loop_dir = _valid_loop_dir(tmp_path)
    (loop_dir / "receipts" / "P000-planning-receipt.md").unlink()
    (loop_dir / "receipts" / "A000-architecture-receipt.md").write_text(
        """
        status: skipped
        reason: TBD
        loop.md
        Public contracts: unchanged
        """,
        encoding="utf-8",
    )

    proc = _run_checker(loop_dir)

    assert proc.returncode == 1, proc.stdout + proc.stderr
    report = json.loads(proc.stdout)
    assert report["status"] == "fail"
    stages = {stage["stage"]: stage for stage in report["stages"]}
    assert stages["research"]["status"] == "pass"
    assert stages["planning"]["status"] == "fail"
    assert "missing_receipt" in stages["planning"]["errors"]
    assert stages["architecture"]["status"] == "fail"
    assert "skipped_without_concrete_reason" in stages["architecture"]["errors"]


def test_pre_lfg_receipt_checker_allows_minimal_skipped_receipt(
    tmp_path: Path,
) -> None:
    loop_dir = _valid_loop_dir(tmp_path)
    _write_receipt(
        loop_dir,
        "A000-architecture-receipt.md",
        """
        status: skipped
        reason: Architecture review was unnecessary because no public contracts or cross-module boundaries changed.
        loop.md
        """,
    )

    proc = _run_checker(loop_dir)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads(proc.stdout)
    stages = {stage["stage"]: stage for stage in report["stages"]}
    architecture = stages["architecture"]
    assert architecture["status"] == "pass"
    assert "missing_stage_evidence_keywords" not in architecture["errors"]


def test_pre_lfg_receipt_checker_requires_status_for_skipped_receipt(
    tmp_path: Path,
) -> None:
    loop_dir = _valid_loop_dir(tmp_path)
    _write_receipt(
        loop_dir,
        "A000-architecture-receipt.md",
        """
        reason: Architecture review was unnecessary because no public contracts or cross-module boundaries changed.
        loop.md
        Public contracts: unchanged
        Cross-module design decisions: none
        Rejected alternatives: none
        Follow-up constraints: keep checker read-only.
        """,
    )

    proc = _run_checker(loop_dir)

    assert proc.returncode == 1, proc.stdout + proc.stderr
    report = json.loads(proc.stdout)
    stages = {stage["stage"]: stage for stage in report["stages"]}
    assert stages["architecture"]["status"] == "fail"
    assert "missing_status" in stages["architecture"]["errors"]


def test_pre_lfg_receipt_checker_requires_loop_reference_for_skipped_receipt(
    tmp_path: Path,
) -> None:
    loop_dir = _valid_loop_dir(tmp_path)
    _write_receipt(
        loop_dir,
        "A000-architecture-receipt.md",
        """
        status: skipped
        reason: Architecture review was unnecessary because no public contracts or cross-module boundaries changed.
        """,
    )

    proc = _run_checker(loop_dir)

    assert proc.returncode == 1, proc.stdout + proc.stderr
    report = json.loads(proc.stdout)
    stages = {stage["stage"]: stage for stage in report["stages"]}
    assert stages["architecture"]["status"] == "fail"
    assert "missing_loop_md_reference" in stages["architecture"]["errors"]


def test_pre_lfg_receipt_checker_non_skipped_receipts_require_stage_evidence(
    tmp_path: Path,
) -> None:
    loop_dir = _valid_loop_dir(tmp_path)
    _write_receipt(
        loop_dir,
        "A000-architecture-receipt.md",
        """
        status: complete
        loop.md
        Public contracts: unchanged
        """,
    )

    proc = _run_checker(loop_dir)

    assert proc.returncode == 1, proc.stdout + proc.stderr
    report = json.loads(proc.stdout)
    stages = {stage["stage"]: stage for stage in report["stages"]}
    assert stages["architecture"]["status"] == "fail"
    assert "missing_stage_evidence_keywords" in stages["architecture"]["errors"]
