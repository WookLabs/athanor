"""Regression tests for P16 plugin distribution smoke.

P16 makes Claude's real plugin loader inventory and token-cost surface a
release signal. Static frontmatter tests are not enough: Claude Code 2.1.179
reports files under plugin-root ``agents/`` as agent components even when those
files lack a ``name:`` field.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "gates" / "distribution_smoke.py"
SCHEMA = REPO_ROOT / "schemas" / "distribution-smoke-report.schema.json"

EXPECTED_AGENTS = [
    "ci-watcher",
    "codex-dispatcher",
    "learner",
    "releaser",
]


def _run_report(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--json", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def _minimal_plugin(tmp_path: Path) -> Path:
    root = tmp_path / "plugin"
    (root / ".claude-plugin").mkdir(parents=True)
    (root / "skills" / "work").mkdir(parents=True)
    (root / "agents").mkdir(parents=True)
    (root / ".claude-plugin" / "plugin.json").write_text(
        json.dumps(
            {
                "name": "athanor",
                "version": "1.0.0",
                "description": "fixture",
                "agents": ["./agents/learner.md"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (root / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps(
            {
                "name": "athanor",
                "description": "fixture marketplace",
                "plugins": [{"name": "athanor", "version": "1.0.0", "source": "./"}],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "agents" / "learner.md").write_text(
        "---\nname: learner\n---\n",
        encoding="utf-8",
    )
    return root


def test_distribution_smoke_report_passes_on_current_repo() -> None:
    result = _run_report()

    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["schema_version"] == 1
    assert report["status"] == "pass"
    assert report["plugin"]["name"] == "athanor"
    assert report["plugin"]["manifest_version"] == report["plugin"]["marketplace_version"]
    assert report["component_inventory"]["expected_agents"] == EXPECTED_AGENTS
    assert report["component_inventory"]["agent_count"] == 4
    assert report["cost_surface"]["always_on_tokens"] <= 2200


def test_distribution_smoke_schema_validates_report() -> None:
    result = _run_report()

    assert result.returncode == 0, result.stdout + result.stderr
    jsonschema.validate(
        json.loads(result.stdout),
        json.loads(SCHEMA.read_text(encoding="utf-8")),
    )


def test_distribution_smoke_fails_on_marketplace_version_drift(tmp_path: Path) -> None:
    root = _minimal_plugin(tmp_path)
    market = root / ".claude-plugin" / "marketplace.json"
    data = json.loads(market.read_text(encoding="utf-8"))
    data["plugins"][0]["version"] = "2.0.0"
    market.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    result = _run_report("--repo-root", str(root), "--skip-claude")

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["status"] == "fail"
    assert "manifest.marketplace_version" in {check["id"] for check in report["checks"]}


def test_distribution_smoke_skips_claude_when_requested() -> None:
    result = _run_report("--skip-claude")

    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["claude_cli"]["status"] == "skipped"
    assert report["component_inventory"]["source"] == "manifest"
