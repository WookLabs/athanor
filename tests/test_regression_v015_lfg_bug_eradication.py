"""Current LFG/LFG-loop regression locks after Stop-hook removal."""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LFG_SKILL = REPO_ROOT / "skills" / "lfg" / "SKILL.md"
LFG_LOOP_SKILL = REPO_ROOT / "skills" / "lfg-loop" / "SKILL.md"
STATE_SHAPE = REPO_ROOT / "skills" / "lfg-loop" / "references" / "state-shape.md"
RECEIPT_VALIDATOR = (
    REPO_ROOT / "skills" / "lfg-loop" / "references" / "receipt-validator.md"
)
SCHEMA_PATH = REPO_ROOT / "schemas" / "athanor-config.schema.json"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "lfg_loop"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _frontmatter_value(text: str, key: str) -> str:
    head = text.split("---", 2)[1]
    for line in head.splitlines():
        if line.startswith(f"{key}:"):
            return line.split(":", 1)[1].strip()
    return ""


def test_lfg_loop_state_shape_has_cycle_phase_and_terminal_states() -> None:
    body = _read(STATE_SHAPE)
    for value in [
        "bootstrapping",
        "cycle_n_in_progress",
        "cycle_n_complete",
        "scope_change_pending",
        "loop_complete",
        "aborted",
        "not_started",
        "lfg_done_seen",
        "receipt_validated",
        "tier1_checked",
        "tier2_checked",
        "tier3_pending",
        "tier3_ratified",
    ]:
        assert value in body


def test_receipt_validator_and_fixtures_use_canonical_statuses() -> None:
    canonical = {"all_valid", "completed_with_residuals", "invalid_steps_present"}
    body = _read(RECEIPT_VALIDATOR)
    for value in canonical:
        assert value in body

    fixture_files = list(FIXTURE_DIR.glob("receipt_*.md"))
    assert fixture_files
    for fixture in fixture_files:
        text = _read(fixture)
        status_lines = [
            line for line in text.splitlines() if line.strip().startswith("validator_status:")
        ]
        assert status_lines, f"missing validator_status in {fixture.name}"
        for line in status_lines:
            value = line.split(":", 1)[1].strip()
            assert value in canonical


def test_lfg_skill_keeps_thin_leader_for_review_and_ci_fixes() -> None:
    body = _read(LFG_SKILL)
    collapsed = " ".join(body.lower().split())
    forbidden = [
        "lfg leader applies fix",
        "the lfg leader applies fix",
        "leader applies fixes",
        "apply a fix in the working tree",
    ]
    assert not [pattern for pattern in forbidden if pattern in collapsed]


def test_lfg_skill_tools_and_timeout_contracts() -> None:
    body = _read(LFG_SKILL)
    allowed = _frontmatter_value(body, "allowed-tools")
    assert "Write" in allowed
    assert "Task" in allowed

    step8_start = body.find("### Step 8")
    step9_start = body.find("### Step 9")
    assert step8_start >= 0
    assert step9_start >= 0
    step8_body = body[step8_start:step9_start]
    assert "timeout" in step8_body.lower()
    assert "<run-id>" not in step8_body


def test_lfg_loop_config_and_archive_contract_are_current() -> None:
    schema = json.loads(_read(SCHEMA_PATH))
    assert "lfgLoop" in schema["properties"]
    assert "lfgGoal" not in schema["properties"]
    archive_desc = (
        schema["properties"]["lfgLoop"]["properties"]["archiveOnComplete"].get(
            "description", ""
        )
    )
    assert ".athanor/loops/_archive/" not in archive_desc
    assert "docs/loops-completed" in archive_desc


def test_claude_lfg_rows_reference_current_commands_only() -> None:
    body = _read(CLAUDE_MD)
    lfg_lines = [
        line for line in body.splitlines() if "| `/athanor:lfg" in line
    ]
    assert lfg_lines
    joined = "\n".join(lfg_lines)
    assert "/athanor:ce-lfg" not in joined
    assert "/athanor:lfg-goal" not in joined


def test_no_stale_stop_claim_or_goal_loop_tokens_in_current_skills() -> None:
    for path in [LFG_SKILL, LFG_LOOP_SKILL]:
        body = _read(path)
        assert "stop_verify_claims.py" not in body
        assert "Stop hook runtime gate" not in body
        assert not re.search(r"/athanor:lfg-goal|lfgGoal|goal_loop_controller", body)
