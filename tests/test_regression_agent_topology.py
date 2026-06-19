"""Regression tests for the agent/skill topology contract.

The registered-agent count is already locked elsewhere. These tests make the
current operating model executable: every public skill must have an explicit
route, prompt-gen must stay an intake/framing skill instead of becoming a new
registered agent, and the read-only gate must catch drift.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACT = REPO_ROOT / "docs" / "agent-topology-contract.json"
TOPOLOGY_DOC = REPO_ROOT / "docs" / "agent-topology.md"
GATE = REPO_ROOT / "scripts" / "gates" / "agent_topology.py"

REGISTERED_AGENTS = {
    "ci-watcher",
    "codex-dispatcher",
    "learner",
    "releaser",
}
REFERENCE_ROLES = {
    "analyst",
    "cleaner",
    "critic",
    "executor",
    "planner",
    "researcher",
    "reviewer",
}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_gate(repo_root: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/gates/agent_topology.py", "--json"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )


def _check_ids(report: dict) -> set[str]:
    return {str(check["id"]) for check in report["checks"]}


def _check_by_id(report: dict, check_id: str) -> dict:
    for check in report["checks"]:
        if check["id"] == check_id:
            return check
    raise AssertionError(f"missing check id: {check_id}")


def _copy_minimal_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    for source in (
        "docs/agent-topology-contract.json",
        "docs/agent-topology.md",
        "scripts/gates/agent_topology.py",
        "CLAUDE.md",
        "README.md",
        "docs/package-knowledge-index.md",
    ):
        src = REPO_ROOT / source
        dest = repo / source
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    for directory in ("agents", "docs/agent-roles", "skills"):
        for item in (REPO_ROOT / directory).iterdir():
            if item.is_dir():
                (repo / directory / item.name).mkdir(parents=True, exist_ok=True)
                skill = item / "SKILL.md"
                if skill.exists():
                    dest = repo / directory / item.name / "SKILL.md"
                    dest.write_text(skill.read_text(encoding="utf-8"), encoding="utf-8")
            elif item.suffix == ".md":
                dest = repo / directory / item.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(item.read_text(encoding="utf-8"), encoding="utf-8")
    return repo


def test_agent_topology_contract_names_current_surface() -> None:
    contract = _load_json(CONTRACT)

    assert contract["schema_version"] == 1
    assert {item["name"] for item in contract["registered_agents"]} == REGISTERED_AGENTS
    assert {item["name"] for item in contract["reference_roles"]} == REFERENCE_ROLES
    assert contract["registration_policy"]["default_for_new_skill"] == "skill_route"
    assert contract["registration_policy"]["new_registered_agent_requires"] == [
        "standalone_invocation_need",
        "session_path_independent_prompt",
        "documented_reuse_across_two_or_more_skills",
        "topology_contract_update",
    ]


def test_agent_topology_contract_routes_every_skill() -> None:
    contract = _load_json(CONTRACT)
    routes = {item["skill"]: item for item in contract["skill_routes"]}
    actual_skills = {
        item.name
        for item in (REPO_ROOT / "skills").iterdir()
        if item.is_dir() and not item.name.startswith(".")
    }

    assert set(routes) == actual_skills
    assert routes["prompt-gen"]["leader_kind"] == "intake-framing"
    assert routes["prompt-gen"]["registered_agents"] == []
    assert "plan" in routes["prompt-gen"]["next_skill_handoffs"]
    assert "discuss" in routes["prompt-gen"]["next_skill_handoffs"]
    assert "work" in routes["prompt-gen"]["next_skill_handoffs"]


def test_agent_topology_doc_and_entry_points_link_contract() -> None:
    topology = TOPOLOGY_DOC.read_text(encoding="utf-8")
    claude = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    index = (REPO_ROOT / "docs" / "package-knowledge-index.md").read_text(
        encoding="utf-8"
    )

    for token in (
        "80/100",
        "92/100",
        "prompt-gen",
        "No new registered agent",
        "agent-topology-contract.json",
    ):
        assert token in topology
    assert "docs/agent-topology.md" in claude
    assert "docs/agent-topology.md" in readme
    assert "agent-topology.md" in index
    assert "agent_topology.py" in index


def test_agent_topology_gate_reports_pass_on_current_repo() -> None:
    result = _run_gate()

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["schema_version"] == 1
    assert report["status"] == "pass"
    assert report["summary"]["errors"] == 0
    assert report["summary"]["registered_agents"] == 4
    assert report["summary"]["reference_roles"] == 7
    assert report["summary"]["skill_routes"] == len(
        [
            item
            for item in (REPO_ROOT / "skills").iterdir()
            if item.is_dir() and not item.name.startswith(".")
        ]
    )


def test_agent_topology_gate_fails_when_skill_route_is_missing(tmp_path: Path) -> None:
    repo = _copy_minimal_repo(tmp_path)
    contract_path = repo / "docs" / "agent-topology-contract.json"
    contract = _load_json(contract_path)
    contract["skill_routes"] = [
        route for route in contract["skill_routes"] if route["skill"] != "prompt-gen"
    ]
    contract_path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")

    result = _run_gate(repo)

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["status"] == "fail"
    assert "skills.routes_cover_actual" in _check_ids(report)
    check = _check_by_id(report, "skills.routes_cover_actual")
    assert check["missing"] == ["prompt-gen"]


def test_agent_topology_gate_fails_when_reference_role_is_registered(
    tmp_path: Path,
) -> None:
    repo = _copy_minimal_repo(tmp_path)
    role = repo / "docs" / "agent-roles" / "planner.md"
    text = role.read_text(encoding="utf-8")
    role.write_text(text.replace("description:", "name: athanor-planner\nmodel: sonnet\ndescription:", 1), encoding="utf-8")

    result = _run_gate(repo)

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["status"] == "fail"
    assert "reference_roles.not_registered" in _check_ids(report)
    check = _check_by_id(report, "reference_roles.not_registered")
    assert "planner" in check["actual"]


def test_agent_topology_gate_fails_when_registered_agent_is_added(
    tmp_path: Path,
) -> None:
    repo = _copy_minimal_repo(tmp_path)
    shutil.copyfile(
        repo / "agents" / "learner.md",
        repo / "agents" / "intake-framer.md",
    )

    result = _run_gate(repo)

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["status"] == "fail"
    assert "registered_agents.files" in _check_ids(report)
    check = _check_by_id(report, "registered_agents.files")
    assert check["unexpected"] == ["intake-framer"]
