"""Regression: lfg-goal score-target optimization loop contract."""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LFG_GOAL_SKILL = REPO_ROOT / "skills" / "lfg-goal" / "SKILL.md"
JUDGE_RUBRIC = REPO_ROOT / "skills" / "lfg-goal" / "references" / "judge-rubric.md"
GOAL_TEMPLATE = REPO_ROOT / "skills" / "lfg-goal" / "references" / "goal-md-template.md"
CODEX_LFG_GOAL = (
    REPO_ROOT / "plugins" / "athanor-codex" / "skills" / "athanor-lfg-goal" / "SKILL.md"
)
ROOT_CONFIG = REPO_ROOT / "athanor.json"
TEMPLATE_CONFIG = REPO_ROOT / "templates" / "athanor.json"
SCHEMA = REPO_ROOT / "schemas" / "athanor-config.schema.json"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_lfg_goal_documents_score_target_loop() -> None:
    body = _read(LFG_GOAL_SKILL)
    required = [
        "Score-target form",
        "--score-target",
        "--min-dimension",
        "Score target (optional)",
        "target_overall_score",
        "target_min_dimension_score",
        "baseline_assessment_ref",
        "latest_assessment_ref",
        "Score-Target Optimization Loop",
        "invoke_skill(\"athanor:assess\"",
        "enqueue_next_cycle_from_lowest_dimensions",
        "score_target_reached",
    ]
    missing = [token for token in required if token not in body]
    assert not missing, f"lfg-goal SKILL.md missing score-target contract: {missing}"


def test_score_target_is_part_of_completion_gate() -> None:
    body = _read(LFG_GOAL_SKILL)
    required = [
        "final score must be `>= target_overall_score`",
        "dimension score must be `>= target_min_dimension_score`",
        "max_allowed_regression",
        "Tier 2 judges confirm the score is",
        "Tier 3 user ratifies",
    ]
    missing = [token for token in required if token not in body]
    assert not missing, f"score-target completion gate is incomplete: {missing}"


def test_judge_rubric_audits_score_target_evidence() -> None:
    rubric = _read(JUDGE_RUBRIC)
    required = [
        "Score-target satisfaction",
        "target_overall_score",
        "target_min_dimension_score",
        "max_allowed_regression",
        "Weighted-average improvement alone is a",
        "score_target_met",
        "lowest_dimension_score",
    ]
    missing = [token for token in required if token not in rubric]
    assert not missing, f"judge rubric missing score-target audit fields: {missing}"


def test_goal_template_supports_optional_score_target_section() -> None:
    template = _read(GOAL_TEMPLATE)
    required = [
        "### `## Score target`",
        "`assessment_skill`: `/athanor:assess`",
        "`target_overall_score`",
        "`target_min_dimension_score`",
        "`baseline_assessment_ref`",
        "`latest_assessment_ref`",
        "`score_history`",
        "`waived_dimensions`",
    ]
    missing = [token for token in required if token not in template]
    assert not missing, f"goal template missing score-target fields: {missing}"


def test_codex_companion_documents_score_target_parity() -> None:
    body = _read(CODEX_LFG_GOAL)
    required = [
        "Score-Target Mode",
        "--score-target 95 --min-dimension 90",
        "athanor-assess",
        "target_overall_score",
        "target_min_dimension_score",
        "max_allowed_regression",
        "lowest-scoring",
        "inflated scores",
    ]
    missing = [token for token in required if token not in body]
    assert not missing, f"Codex companion missing score-target parity: {missing}"


def test_score_target_config_defaults_and_schema() -> None:
    root = json.loads(ROOT_CONFIG.read_text(encoding="utf-8"))
    template = json.loads(TEMPLATE_CONFIG.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    expected = {
        "enabled": False,
        "targetOverall": 95,
        "targetMinDimension": 90,
        "maxAllowedRegression": 2,
    }
    assert root["lfgGoal"]["scoreTarget"] == expected
    assert template["lfgGoal"]["scoreTarget"] == expected

    props = schema["properties"]["lfgGoal"]["properties"]["scoreTarget"]["properties"]
    for key in expected:
        assert key in props
    assert props["targetOverall"]["maximum"] == 100
    assert props["targetMinDimension"]["maximum"] == 100
