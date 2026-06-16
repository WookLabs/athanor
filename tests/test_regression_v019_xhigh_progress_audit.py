"""Regression tests for the xhigh remediation audit ledger.

The 2026-06-14 xhigh report started at 7.3/10. This branch implements the
eight recommended work items plus memory-honesty cleanup, so the saved report
must not keep presenting the original score and missing-work language as the
current state.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT = REPO_ROOT / "docs" / "plans" / "2026-06-14-athanor-xhigh-audit.md"


def _body() -> str:
    return AUDIT.read_text(encoding="utf-8")


def test_xhigh_audit_distinguishes_original_score_from_current_score() -> None:
    body = _body()
    assert "## Original Score" in body
    assert "## Current Evidence Score" in body
    assert "7.3 / 10" in body

    current = re.search(r"## Current Evidence Score\s+\*\*(\d+\.\d+) / 10\*\*", body)
    assert current, "xhigh audit must record a current post-remediation score"
    assert float(current.group(1)) >= 9.5


def test_xhigh_audit_marks_all_original_recommendations_completed() -> None:
    body = _body()
    status_section = body.split("## Remediation Status", 1)[1].split("##", 1)[0]
    for item in range(1, 9):
        assert f"| {item} |" in status_section
    assert status_section.count("| done |") == 8
    assert "PostToolUse evidence sniffer" in status_section
    assert "Evidence-bound Spec-then-TDD gate" in status_section
    assert "Release/version story" in status_section


def test_xhigh_audit_records_live_fixture_completion_and_residuals() -> None:
    body = _body()
    assert "## 9.5 Completion Evidence" in body
    assert "## 9.7 Hardening Evidence" in body
    completion = body.split("## 9.5 Completion Evidence", 1)[1].split("##", 1)[0]
    hardening = body.split("## 9.7 Hardening Evidence", 1)[1].split("##", 1)[0]
    residuals = body.split("## Residuals After 9.7", 1)[1]
    assert "live-claude-2-1-177-stop-basic" in completion
    assert "live-claude-2-1-177-pretool-bash-echo" in completion
    assert "live-claude-2-1-177-posttool-bash-echo" in completion
    assert "live-claude-2-1-178-posttool-pytest-targeted" in hardening
    assert "hook_capture_utils.py" in hardening
    assert "hook-health.jsonl" in hardening
    assert "hook_payload_capture.py" in body
    assert "strict" in residuals.lower()
    assert "mem-search" in residuals
    assert "not yet achieved" not in body.lower()
    assert "python -m pytest tests\\ -q" in body
    assert "passed" in body
    assert "check_release_ready.py --ci" in body
