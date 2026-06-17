# P9 Cross-Runtime Conformance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an executable cross-runtime conformance gate that keeps Athanor's Claude Code plugin, Codex companion plugin, hook catalog, and documented runtime matrix from drifting.

**Architecture:** Keep `hooks/catalog.json` as the hook source of truth and add a small machine-readable runtime-surface contract for non-hook distribution surfaces. A new gate reads actual manifests, skill directories, hook manifests, and the contract, then emits a schema-versioned JSON report and exits non-zero on drift. This is a verifier, not a generator, and it must not write plugin manifests or settings.

**Tech Stack:** Python standard library, pytest, JSON schema docs, GitHub Actions workflow step, existing `docs/plans/` tracking.

---

## Scope Boundary

P9 must improve cross-runtime portability without expanding runtime behavior:

- Do not add new default hooks.
- Do not generate or rewrite `.claude-plugin/`, `.agents/`, `plugins/athanor-codex/`, or `hooks/` files.
- Do not change Codex companion skill behavior except where a test reveals a real conformance drift.
- Treat `skills/ce-test-browser` as vendored Claude-only and not part of the Codex companion mirror.
- Treat `plugins/athanor-codex` as a companion with no hooks, MCP servers, apps, or Claude runtime claims.

## File Map

- Create `docs/runtime-conformance.md`: operator-facing description of the cross-runtime contract, supported surfaces, and non-generator boundary.
- Create `docs/runtime-surface-contract.json`: machine-readable expected skill and manifest surface for Claude/Codex distribution.
- Create `schemas/runtime-conformance-report.schema.json`: JSON report schema for CI and future trend tooling.
- Create `scripts/gates/runtime_conformance.py`: read-only verifier and report CLI.
- Create `tests/test_regression_runtime_conformance.py`: unit/regression tests for the verifier.
- Extend `.github/workflows/validate-plugin.yml`: named CI gate before broad pytest.
- Extend `tests/test_regression_v019_release_story.py`: release-story lock for the CI gate, docs, and changelog.
- Update `CHANGELOG.md`: Unreleased P9 entry.
- Update `docs/plans/2026-06-17-p9-cross-runtime-conformance-plan.md`: check off completed tasks as evidence lands.

---

## Task 1: Runtime Surface Contract

**Files:**
- Create: `docs/runtime-surface-contract.json`
- Create: `docs/runtime-conformance.md`
- Test: `tests/test_regression_runtime_conformance.py`

- [x] **Step 1: Write failing contract/documentation tests**

Add tests that assert:

```python
def test_runtime_surface_contract_exists_and_names_expected_surfaces():
    contract = _load_json(REPO_ROOT / "docs" / "runtime-surface-contract.json")
    assert contract["schema_version"] == 1
    assert contract["claude_plugin"]["name"] == "athanor"
    assert contract["codex_companion"]["name"] == "athanor-codex"
    assert "analyze" in contract["claude_plugin"]["native_skills"]
    assert "athanor-analyze" in contract["codex_companion"]["skills"]
    assert "ce-test-browser" in contract["claude_plugin"]["vendored_claude_only_skills"]
    assert "athanor-ce-test-browser" not in contract["codex_companion"]["skills"]


def test_runtime_conformance_docs_state_non_generator_boundary():
    body = (REPO_ROOT / "docs" / "runtime-conformance.md").read_text(encoding="utf-8")
    for token in (
        "read-only verifier",
        "not a generator",
        "hooks/catalog.json",
        "plugins/athanor-codex",
        "ce-test-browser",
        "Cross-runtime conformance gate",
    ):
        assert token in body
```

Run: `python -m pytest tests/test_regression_runtime_conformance.py -q`

Expected: FAIL because the contract and docs do not exist.

- [x] **Step 2: Add `docs/runtime-surface-contract.json`**

Use this initial content:

```json
{
  "schema_version": 1,
  "claude_plugin": {
    "name": "athanor",
    "manifest": ".claude-plugin/plugin.json",
    "marketplace": ".claude-plugin/marketplace.json",
    "hook_manifest": "hooks/hooks.json",
    "native_skills": [
      "analyze",
      "debug",
      "discuss",
      "lfg",
      "lfg-goal",
      "plan",
      "review",
      "scope-drift",
      "setup",
      "verification-before-completion",
      "work"
    ],
    "vendored_claude_only_skills": [
      "ce-test-browser"
    ]
  },
  "codex_companion": {
    "name": "athanor-codex",
    "manifest": "plugins/athanor-codex/.codex-plugin/plugin.json",
    "marketplace": ".agents/plugins/marketplace.json",
    "skills": [
      "athanor-analyze",
      "athanor-ci-watch",
      "athanor-debug",
      "athanor-discuss",
      "athanor-lfg",
      "athanor-lfg-goal",
      "athanor-plan",
      "athanor-release",
      "athanor-review",
      "athanor-scope-drift",
      "athanor-setup",
      "athanor-verify",
      "athanor-work"
    ],
    "forbidden_manifest_keys": [
      "hooks",
      "mcpServers",
      "apps"
    ]
  },
  "hook_catalog": {
    "catalog": "hooks/catalog.json",
    "enabled_runtime_events": [
      "PostToolUse",
      "PreToolUse",
      "Stop"
    ],
    "allow_capture_only": true
  }
}
```

- [x] **Step 3: Add `docs/runtime-conformance.md`**

The doc must state:

- the gate is a read-only verifier and not a generator;
- `hooks/catalog.json` remains the hook metadata source of truth;
- `docs/runtime-surface-contract.json` is the distribution-surface contract;
- `ce-test-browser` is Claude-only vendored skill surface;
- Codex companion must stay hook/MCP/app free;
- CI runs the Cross-runtime conformance gate before broad pytest.

- [x] **Step 4: Re-run Task 1 tests**

Run: `python -m pytest tests/test_regression_runtime_conformance.py -q`

Expected: PASS for the two contract/documentation tests.

- [x] **Step 5: Commit**

```bash
git add docs/runtime-surface-contract.json docs/runtime-conformance.md tests/test_regression_runtime_conformance.py
git commit -m "docs: add runtime surface conformance contract"
```

## Task 2: Conformance Report Schema And CLI

**Files:**
- Create: `schemas/runtime-conformance-report.schema.json`
- Create: `scripts/gates/runtime_conformance.py`
- Modify: `tests/test_regression_runtime_conformance.py`

- [ ] **Step 1: Write failing CLI/report tests**

Add tests that execute the CLI and parse JSON:

```python
def test_runtime_conformance_cli_reports_pass_on_current_repo():
    result = subprocess.run(
        [sys.executable, "scripts/gates/runtime_conformance.py", "--json"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["schema_version"] == 1
    assert report["status"] == "pass"
    assert report["summary"]["errors"] == 0
    assert report["surfaces"]["claude"]["plugin_name"] == "athanor"
    assert report["surfaces"]["codex"]["plugin_name"] == "athanor-codex"
    assert report["surfaces"]["hooks"]["enabled_events"] == [
        "PostToolUse",
        "PreToolUse",
        "Stop",
    ]


def test_runtime_conformance_schema_validates_report():
    report = _run_report()
    schema = _load_json(REPO_ROOT / "schemas" / "runtime-conformance-report.schema.json")
    jsonschema.validate(report, schema)
```

Run: `python -m pytest tests/test_regression_runtime_conformance.py -q`

Expected: FAIL because the CLI and schema do not exist.

- [ ] **Step 2: Implement `schemas/runtime-conformance-report.schema.json`**

Required top-level fields:

- `schema_version`
- `status`
- `summary`
- `surfaces`
- `checks`

Keep the schema permissive for future checks but require check objects to have
`id`, `status`, and `message`.

- [ ] **Step 3: Implement `scripts/gates/runtime_conformance.py`**

Required behavior:

- accept `--json`;
- accept optional `--contract docs/runtime-surface-contract.json`;
- load JSON with clear non-zero failure on invalid/missing files;
- compare actual Claude plugin name against contract;
- assert `.claude-plugin/plugin.json` has no explicit `hooks`, `mcpServers`, or `apps` keys;
- compare `skills/` directories against `native_skills + vendored_claude_only_skills`;
- compare `plugins/athanor-codex/.codex-plugin/plugin.json` name against contract;
- assert Codex companion manifest lacks `hooks`, `mcpServers`, and `apps`;
- compare Codex companion skill directories against contract;
- compare enabled catalog events against `hook_catalog.enabled_runtime_events`;
- compare `hooks/hooks.json` command triples against enabled catalog entries;
- emit JSON to stdout;
- exit 0 only when every check passes.

- [ ] **Step 4: Re-run CLI/report tests**

Run: `python -m pytest tests/test_regression_runtime_conformance.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add schemas/runtime-conformance-report.schema.json scripts/gates/runtime_conformance.py tests/test_regression_runtime_conformance.py
git commit -m "feat: add cross-runtime conformance gate"
```

## Task 3: Negative Drift Tests

**Files:**
- Modify: `tests/test_regression_runtime_conformance.py`
- Modify: `scripts/gates/runtime_conformance.py` only if the tests expose missing diagnostics.

- [ ] **Step 1: Add failing drift tests using temp repos**

Add tests for these cases:

```python
def test_runtime_conformance_fails_when_codex_skill_is_missing(tmp_path):
    repo = _copy_minimal_repo(tmp_path)
    shutil.rmtree(repo / "plugins" / "athanor-codex" / "skills" / "athanor-review")
    result = _run_cli(repo)
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["status"] == "fail"
    assert "codex.skills" in _check_ids(report)


def test_runtime_conformance_fails_when_enabled_hook_missing_from_runtime_manifest(tmp_path):
    repo = _copy_minimal_repo(tmp_path)
    hooks_path = repo / "hooks" / "hooks.json"
    hooks = _load_json(hooks_path)
    hooks["hooks"].pop("Stop", None)
    hooks_path.write_text(json.dumps(hooks, indent=2) + "\n", encoding="utf-8")
    result = _run_cli(repo)
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert "hooks.enabled_runtime_manifest" in _check_ids(report)


def test_runtime_conformance_fails_when_codex_manifest_adds_hooks(tmp_path):
    repo = _copy_minimal_repo(tmp_path)
    manifest_path = repo / "plugins" / "athanor-codex" / ".codex-plugin" / "plugin.json"
    manifest = _load_json(manifest_path)
    manifest["hooks"] = "./hooks/hooks.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    result = _run_cli(repo)
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert "codex.forbidden_manifest_keys" in _check_ids(report)
```

Run: `python -m pytest tests/test_regression_runtime_conformance.py -q`

Expected: FAIL until the CLI reports these specific check IDs.

- [ ] **Step 2: Make diagnostics stable**

If needed, adjust the CLI so failures include these check IDs:

- `codex.skills`
- `hooks.enabled_runtime_manifest`
- `codex.forbidden_manifest_keys`

- [ ] **Step 3: Re-run runtime conformance tests**

Run: `python -m pytest tests/test_regression_runtime_conformance.py -q`

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add scripts/gates/runtime_conformance.py tests/test_regression_runtime_conformance.py
git commit -m "test: lock cross-runtime drift failures"
```

## Task 4: CI, Release Story, And Changelog

**Files:**
- Modify: `.github/workflows/validate-plugin.yml`
- Modify: `tests/test_regression_v019_release_story.py`
- Modify: `CHANGELOG.md`
- Modify: `docs/plans/2026-06-17-p9-cross-runtime-conformance-plan.md`

- [ ] **Step 1: Add failing release-story tests**

Add tests:

```python
def test_ci_runs_cross_runtime_conformance_gate():
    workflow = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
    assert "Cross-runtime conformance gate" in workflow
    assert "python scripts/gates/runtime_conformance.py --json" in workflow


def test_unreleased_documents_cross_runtime_conformance_gate():
    section = _unreleased_section()
    for token in (
        "Cross-runtime conformance gate",
        "runtime-surface contract",
        "Codex companion",
        "hooks/catalog.json",
    ):
        assert token in section
```

Run: `python -m pytest tests/test_regression_v019_release_story.py -q`

Expected: FAIL until CI and changelog are updated.

- [ ] **Step 2: Add CI step**

Add this before broad pytest:

```yaml
      - name: Cross-runtime conformance gate
        shell: bash
        run: python scripts/gates/runtime_conformance.py --json
```

- [ ] **Step 3: Add changelog entry**

Add an Unreleased bullet:

```markdown
- **Cross-runtime conformance gate.** Adds a read-only runtime-surface
  contract and `scripts/gates/runtime_conformance.py` so Claude Code plugin
  metadata, Codex companion skills, and `hooks/catalog.json` enabled runtime
  hooks fail CI on drift before any generator or settings writer expands the
  surface.
```

- [ ] **Step 4: Re-run release-story and conformance tests**

Run:

```bash
python -m pytest tests/test_regression_v019_release_story.py tests/test_regression_runtime_conformance.py -q
python scripts/gates/runtime_conformance.py --json
git diff --check
```

Expected: all commands exit 0.

- [ ] **Step 5: Mark Task 1-4 checkboxes and commit**

```bash
git add .github/workflows/validate-plugin.yml tests/test_regression_v019_release_story.py CHANGELOG.md docs/plans/2026-06-17-p9-cross-runtime-conformance-plan.md
git commit -m "docs: wire cross-runtime conformance into CI story"
```

## Task 5: Verification And Merge

- [ ] Run targeted gate:

```bash
python scripts/gates/runtime_conformance.py --json
python -m pytest tests/test_regression_runtime_conformance.py tests/test_regression_cross_runtime_hook_matrix.py tests/test_regression_codex_companion.py -q
```

- [ ] Run release and workflow gates:

```bash
python scripts/check_release_ready.py --ci
python scripts/gates/replay_hook_fixtures.py --fixture-root tests/fixtures/hooks --json
python scripts/gates/check_hook_performance_budget.py --json
python scripts/loops/run_goal_loop_fixtures.py --fixture-root tests/fixtures/durable_loops --json
python scripts/evals/run_workflow_scenarios.py --scenario-root tests/fixtures/workflow_evals --json
python -m pytest tests/ -q
git diff --check
```

- [ ] Fast-forward merge to `main` and push when clean.

## Self-Review

- Spec coverage: P9 covers the deep-research gap for cross-runtime portability by adding an executable verifier and CI gate, while leaving hook expansion and generation out of scope.
- Placeholder scan: no `TBD`, `TODO`, or open-ended implementation step remains.
- Type consistency: contract paths and expected check IDs match the planned tests and CLI behavior.
