# P16 Distribution Smoke Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a release-time distribution smoke gate that checks the actual Claude plugin loader inventory, token-cost surface, manifest/marketplace pins, and package footprint, then correct Athanor's loader-visible agent surface to the documented 4-agent contract.

**Architecture:** Add a stdlib-only `scripts/gates/distribution_smoke.py` gate that always performs local JSON/package checks and conditionally runs `claude plugin validate` plus `claude --plugin-dir . plugin details athanor` when the CLI is available. Use the gate to make runtime-visible component inventory authoritative instead of relying only on static frontmatter tests. Prefer constraining the plugin manifest `agents` list to the 4 intended agent files; if the loader still reports 11, move the 7 reference docs out of plugin-root `agents/`.

**Tech Stack:** Python stdlib, pytest, jsonschema, Claude Code CLI when available, GitHub Actions.

---

### Task 1: Regression Tests For Distribution Smoke

**Files:**
- Create: `tests/test_regression_distribution_smoke.py`
- Create: `schemas/distribution-smoke-report.schema.json`
- Create: `scripts/gates/distribution_smoke.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_regression_distribution_smoke.py` with these behaviors:

```python
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "gates" / "distribution_smoke.py"
SCHEMA = REPO_ROOT / "schemas" / "distribution-smoke-report.schema.json"


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
    (root / "agents" / "learner.md").write_text("---\nname: learner\n---\n", encoding="utf-8")
    return root


def test_distribution_smoke_report_passes_on_current_repo():
    result = _run_report()
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["schema_version"] == 1
    assert report["status"] == "pass"
    assert report["plugin"]["name"] == "athanor"
    assert report["plugin"]["manifest_version"] == report["plugin"]["marketplace_version"]
    assert report["component_inventory"]["expected_agents"] == [
        "ci-watcher",
        "codex-dispatcher",
        "learner",
        "releaser",
    ]
    assert report["component_inventory"]["agent_count"] == 4
    assert report["cost_surface"]["always_on_tokens"] <= 2200


def test_distribution_smoke_schema_validates_report():
    result = _run_report()
    assert result.returncode == 0, result.stdout + result.stderr
    jsonschema.validate(json.loads(result.stdout), json.loads(SCHEMA.read_text(encoding="utf-8")))


def test_distribution_smoke_fails_on_marketplace_version_drift(tmp_path):
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


def test_distribution_smoke_skips_claude_when_path_is_empty():
    env = {"PATH": ""}
    result = _run_report("--skip-claude", env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["claude_cli"]["status"] == "skipped"
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
python -m pytest tests/test_regression_distribution_smoke.py -q
```

Expected: fail because `scripts/gates/distribution_smoke.py` and `schemas/distribution-smoke-report.schema.json` do not exist.

- [ ] **Step 3: Commit tests and plan**

```bash
git add docs/architecture/2026-06-17-p16-deep-research-refresh.md docs/plans/2026-06-17-p16-distribution-smoke-plan.md tests/test_regression_distribution_smoke.py
git commit -m "docs: plan p16 distribution smoke"
```

### Task 2: Distribution Smoke Gate

**Files:**
- Create: `scripts/gates/distribution_smoke.py`
- Create: `schemas/distribution-smoke-report.schema.json`
- Modify: `.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`

- [ ] **Step 1: Implement the gate**

`scripts/gates/distribution_smoke.py` must:

- parse `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`;
- fail if plugin name or version drifts;
- require marketplace `description`;
- require expected agent list `ci-watcher`, `codex-dispatcher`, `learner`, `releaser`;
- compute package footprint excluding `.git`, `.pytest_cache`, `.athanor`, `ref`, and `__pycache__`;
- run `claude plugin validate` and `claude --plugin-dir <repo> plugin details athanor` unless `--skip-claude` is set or `claude` is unavailable;
- parse `plugin details` component counts and always-on token estimate;
- fail when the live loader reports agent count other than 4;
- fail when always-on token estimate exceeds `--max-always-on-tokens` default `2200`;
- emit schema-versioned JSON.

- [ ] **Step 2: Add manifest/marketplace distribution fixes**

Modify `.claude-plugin/plugin.json` to include only the 4 intended agent files:

```json
"agents": [
  "./agents/ci-watcher.md",
  "./agents/codex-dispatcher.md",
  "./agents/learner.md",
  "./agents/releaser.md"
]
```

Modify `.claude-plugin/marketplace.json` to add a top-level `description`.

- [ ] **Step 3: Verify GREEN**

Run:

```bash
python -m pytest tests/test_regression_distribution_smoke.py -q
python scripts/gates/distribution_smoke.py --json
claude --plugin-dir . plugin details athanor
```

Expected:

- pytest passes;
- distribution smoke status is `pass`;
- `plugin details` reports `Agents (4)`;
- always-on token estimate is at or below the chosen budget.

- [ ] **Step 4: Commit implementation**

```bash
git add scripts/gates/distribution_smoke.py schemas/distribution-smoke-report.schema.json .claude-plugin/plugin.json .claude-plugin/marketplace.json tests/test_regression_distribution_smoke.py
git commit -m "feat: add plugin distribution smoke gate"
```

### Task 3: CI, Docs, And Release Story

**Files:**
- Create: `docs/distribution-smoke.md`
- Modify: `.github/workflows/validate-plugin.yml`
- Modify: `docs/workflow-trace-evals.md` if distribution ordering needs a reference
- Modify: `tests/test_regression_v019_release_story.py`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Write release-story tests**

Add two tests to `tests/test_regression_v019_release_story.py`:

```python
def test_ci_runs_distribution_smoke_gate():
    workflow = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
    assert "Distribution smoke gate" in workflow
    assert "python scripts/gates/distribution_smoke.py --json" in workflow


def test_unreleased_documents_distribution_smoke_gate():
    section = _unreleased_section()
    required = [
        "Distribution smoke gate",
        "scripts/gates/distribution_smoke.py",
        "claude plugin details",
        "4-agent",
        "always-on",
    ]
    missing = [token for token in required if token not in section]
    assert not missing, (
        "CHANGELOG [Unreleased] must explain P16 distribution smoke; "
        f"missing: {missing}"
    )
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
python -m pytest tests/test_regression_v019_release_story.py::test_ci_runs_distribution_smoke_gate tests/test_regression_v019_release_story.py::test_unreleased_documents_distribution_smoke_gate -q
```

Expected: fail because workflow and changelog are not updated yet.

- [ ] **Step 3: Update CI and docs**

Add a named `Distribution smoke gate` step before broad pytest:

```yaml
- name: Distribution smoke gate
  shell: bash
  run: python scripts/gates/distribution_smoke.py --json
```

Create `docs/distribution-smoke.md` documenting:

- local manifest checks;
- optional Claude CLI validation;
- `plugin details` inventory/cost parsing;
- allowed validation warnings;
- 4-agent loader-surface invariant;
- package footprint boundary;
- CI behavior when the Claude CLI is available.

Add a CHANGELOG Unreleased entry naming P16.

- [ ] **Step 4: Verify GREEN and commit**

Run:

```bash
python -m pytest tests/test_regression_distribution_smoke.py tests/test_regression_v019_release_story.py -q
python scripts/gates/distribution_smoke.py --json
git diff --check
```

Commit:

```bash
git add .github/workflows/validate-plugin.yml docs/distribution-smoke.md tests/test_regression_v019_release_story.py CHANGELOG.md
git commit -m "docs: wire distribution smoke into release story"
```

### Task 4: Final Verification And Integration

**Files:**
- No new files.

- [ ] **Step 1: Run focused gates**

```bash
python scripts/gates/distribution_smoke.py --json
python scripts/gates/runtime_conformance.py --json
python scripts/evals/run_workflow_scenarios.py --scenario-root tests/fixtures/workflow_evals --json
python scripts/evals/package_workflow_episode.py --scenario-root tests/fixtures/workflow_evals --output-dir .athanor/episodes/workflow-evals --json
python scripts/evals/run_workflow_scenarios.py --episode-root .athanor/episodes/workflow-evals --json
```

- [ ] **Step 2: Run full test suite**

```bash
python -m pytest tests/ -q
git diff --check
```

- [ ] **Step 3: Confirm live loader inventory**

```bash
claude --plugin-dir . plugin details athanor
```

Expected:

- `Agents (4)`;
- always-on token estimate at or below `2200`;
- no unexpected loader warnings.

- [ ] **Step 4: Merge and push only after verification**

```bash
git status --short --branch
git switch main
git merge --ff-only feat/p16-distribution-smoke
git push origin main
git branch -d feat/p16-distribution-smoke
```

## Self-Review

Spec coverage:

- Loader inventory drift is covered by `distribution_smoke.py` and live `plugin details`.
- Token/cost surface is covered by `cost_surface.always_on_tokens`.
- Marketplace version and description are covered by manifest checks.
- CI/release story is covered by release-story tests.

Placeholder scan:

- No placeholder sections remain.

Type consistency:

- Report fields are consistently named `plugin`, `claude_cli`, `component_inventory`, `cost_surface`, `package`, and `checks`.
