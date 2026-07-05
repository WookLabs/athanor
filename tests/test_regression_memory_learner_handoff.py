"""Regression tests for Learner memory export and compact handoff guidance."""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LEARNER = REPO_ROOT / "agents" / "learner.md"
WORK_LEARNER_REFERENCE = REPO_ROOT / "skills" / "work" / "references" / "learner-cleaner.md"
LFG_GOAL = REPO_ROOT / "skills" / "lfg-loop" / "SKILL.md"
HANDOFF_ARTIFACT = REPO_ROOT / "docs" / "handoff-artifact.md"
TOPOLOGY_CONTRACT = REPO_ROOT / "docs" / "agent-topology-contract.json"
AGENTS_DIR = REPO_ROOT / "agents"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_learner_emits_memory_indexable_fields_without_new_agent() -> None:
    text = _text(LEARNER)

    assert "memory-indexable" in text
    assert "stable id" in text
    assert "source artifact path" in text
    assert "summary" in text
    assert "evidence refs" in text
    assert "confidence" in text
    assert "stale-after" in text
    assert "safe-to-inject summary" in text

    registered_memory_indexers = []
    for path in AGENTS_DIR.glob("*.md"):
        content = _text(path)
        if re.search(r"^name:\s*memory-indexer\s*$", content, re.MULTILINE):
            registered_memory_indexers.append(path.name)

    assert registered_memory_indexers == []


def test_work_reference_mentions_searchable_lesson_ids() -> None:
    text = _text(WORK_LEARNER_REFERENCE)

    assert "searchable lesson ids" in text
    assert "memory-indexable" in text
    assert "safe-to-inject summary" in text
    assert "evidence_refs" in text


def test_lfg_loop_mentions_compact_handoff_artifact() -> None:
    text = _text(LFG_GOAL)

    assert "compact handoff artifact" in text
    assert "docs/handoff-artifact.md" in text
    assert "relevant memory ids" in text
    assert "resume command" in text


def test_handoff_artifact_contract_names_required_fields() -> None:
    text = _text(HANDOFF_ARTIFACT)

    for token in (
        "current goal",
        "recent decisions",
        "active plan or work item",
        "latest run-log reference",
        "relevant memory ids",
        "resume command",
        "open risks",
    ):
        assert token in text

    assert "/handoff " not in text
    assert "/handoff`" not in text


def test_topology_still_has_exactly_four_registered_agents() -> None:
    contract = json.loads(_text(TOPOLOGY_CONTRACT))

    assert len(contract["registered_agents"]) == 4
    assert {agent["name"] for agent in contract["registered_agents"]} == {
        "ci-watcher",
        "codex-dispatcher",
        "learner",
        "releaser",
    }
