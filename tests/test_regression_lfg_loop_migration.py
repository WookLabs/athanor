"""Regression locks for the lfg-loop migration and Stop hook removal."""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _is_historical_allowlist(path: Path) -> bool:
    rel = path.relative_to(REPO_ROOT).as_posix()
    if rel == "CHANGELOG.md":
        return True
    if rel.startswith(("docs/archive/", "docs/plans/", "docs/brainstorms/")):
        return True
    if rel.startswith("docs/residual-review-findings/"):
        return True
    if rel.startswith("docs/architecture/"):
        name = path.name
        return name.startswith("2026-") or name.startswith("v0")
    if rel.startswith("docs/") and re.match(r"docs/v\d+\.\d+\.\d+-migration\.md$", rel):
        return True
    return False


def _state_current_text(text: str) -> str:
    """Keep current-facing STATE.md sections while dropping history ledgers."""
    history_start = text.find("## History")
    live_start = text.find("## Live invariants")
    if history_start != -1 and live_start != -1 and history_start < live_start:
        text = text[:history_start] + text[live_start:]
    spike_start = text.find("## Command-hook Stop blocking spike")
    if spike_start != -1:
        text = text[:spike_start]
    return text


def _is_negative_test_reference(path: Path, line: str) -> bool:
    rel = path.relative_to(REPO_ROOT).as_posix()
    if not rel.startswith("tests/"):
        return False
    if rel == "tests/test_regression_lfg_loop_migration.py":
        return True
    lowered = line.lower()
    return any(
        marker in lowered
        for marker in (
            "assert",
            "forbidden",
            "must not",
            "not in",
            "not re.search",
            "removed",
            "stale",
            "old ",
            "absence",
            "missing",
        )
    )


def test_lfg_loop_skill_replaces_lfg_goal_surface() -> None:
    parent = REPO_ROOT / "skills" / "lfg-loop" / "SKILL.md"
    mirror = (
        REPO_ROOT
        / "plugins"
        / "athanor-codex"
        / "skills"
        / "athanor-lfg-loop"
        / "SKILL.md"
    )

    assert parent.is_file()
    assert mirror.is_file()
    assert not (REPO_ROOT / "skills" / "lfg-goal").exists()
    assert not (
        REPO_ROOT / "plugins" / "athanor-codex" / "skills" / "athanor-lfg-goal"
    ).exists()

    text = parent.read_text(encoding="utf-8")
    assert "name: lfg-loop" in text
    assert "/athanor:lfg-loop" in text
    for required in [
        "deep research",
        "planning",
        "architecture",
        "implementation",
        "assessment",
        "review",
        "verification",
        "persistence",
        "next-loop",
        "per-cycle receipts",
        "human escalation",
    ]:
        assert required in text.lower()
    assert "Stop hook runtime gate" not in text


def test_lfg_loop_config_replaces_lfg_goal() -> None:
    root_config = json.loads(_read("athanor.json"))
    template_config = json.loads(_read("templates/athanor.json"))
    schema = json.loads(_read("schemas/athanor-config.schema.json"))

    assert "lfgLoop" in root_config
    assert "lfgLoop" in template_config
    assert root_config["lfgLoop"] == template_config["lfgLoop"]
    assert "lfgLoop" in schema["properties"]
    assert "lfgGoal" not in root_config
    assert "lfgGoal" not in template_config
    assert "lfgGoal" not in schema["properties"]


def test_stop_completion_claim_hook_is_not_active() -> None:
    hooks = json.loads(_read("hooks/hooks.json"))["hooks"]
    catalog = json.loads(_read("hooks/catalog.json"))["hooks"]

    assert "Stop" not in hooks
    assert {entry["event"] for entry in catalog if entry["runtime_default"] == "enabled"} == {
        "PreToolUse",
        "PostToolUse",
    }
    assert "stop-verify-claims" not in {entry["id"] for entry in catalog}
    assert "stop_verify_claims.py" not in json.dumps(hooks)
    assert "stop_verify_claims.py" not in json.dumps(catalog)


def test_active_surface_has_no_lfg_goal_or_stop_claim_identity() -> None:
    active_roots = [
        "AGENTS.md",
        "CLAUDE.md",
        "README.md",
        "NOTICE.md",
        "athanor.json",
        "pyproject.toml",
        ".claude-plugin",
        ".github",
        "agents",
        "templates/athanor.json",
        "schemas",
        "skills",
        "plugins/athanor-codex",
        "hooks",
        "scripts",
        "docs",
        "tests",
    ]
    text_suffixes = {".md", ".json", ".py", ".yml", ".yaml", ".toml", ".txt"}
    forbidden = re.compile(
        r"/athanor:lfg-goal|athanor-lfg-goal|lfgGoal|goal_loop_controller|"
        r"run_goal_loop|Stop hook runtime gate|Completion-Claim Verification|"
        r"stop_verify_claims\.py|stop-verify-claims|PreToolUse/Stop|"
        r"Stop \+ PreToolUse"
    )
    hits: list[str] = []
    for root in active_roots:
        path = REPO_ROOT / root
        files = (
            [path]
            if path.is_file()
            else [
                p
                for p in path.rglob("*")
                if p.is_file() and p.suffix.lower() in text_suffixes
            ]
        )
        for file_path in files:
            if _is_historical_allowlist(file_path):
                continue
            text = file_path.read_text(encoding="utf-8")
            if file_path.relative_to(REPO_ROOT).as_posix() == "docs/STATE.md":
                text = _state_current_text(text)
            for line_no, line in enumerate(text.splitlines(), start=1):
                if not forbidden.search(line):
                    continue
                if _is_negative_test_reference(file_path, line):
                    continue
                hits.append(f"{file_path.relative_to(REPO_ROOT).as_posix()}:{line_no}")

    assert hits == []


def test_codex_mirror_map_points_to_lfg_loop() -> None:
    source_map = _read("docs/codex-mirror-source-map.md")
    runtime_contract = json.loads(_read("docs/runtime-surface-contract.json"))

    assert "skills/lfg-loop/SKILL.md" in source_map
    assert "athanor-lfg-loop" in source_map
    assert "skills/lfg-goal/SKILL.md" not in source_map
    assert "athanor-lfg-goal" not in source_map
    assert "lfg-loop" in runtime_contract["claude_plugin"]["native_skills"]
    assert "lfg-goal" not in runtime_contract["claude_plugin"]["native_skills"]
    assert "athanor-lfg-loop" in runtime_contract["codex_companion"]["skills"]
    assert "athanor-lfg-goal" not in runtime_contract["codex_companion"]["skills"]
    assert runtime_contract["hook_catalog"]["enabled_runtime_events"] == [
        "PostToolUse",
        "PreToolUse",
    ]
