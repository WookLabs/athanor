# P15 Eval Episode Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add portable local workflow eval episode packages that can be created from existing scenario fixtures and executed directly by the workflow scenario runner.

**Architecture:** Keep scenario JSON and deterministic graders as the source of truth. Add a stdlib-only episode module, manifest schema, packager CLI, and `--episode-root` runner path that delegates back to the existing evaluator.

**Tech Stack:** Python stdlib, JSON schemas, pytest, GitHub Actions.

---

## File Structure

- Create `scripts/evals/workflow_episode.py`: manifest creation, validation,
  scenario copying, and episode-root resolution.
- Create `scripts/evals/package_workflow_episode.py`: CLI wrapper for packaging
  scenarios into episode directories.
- Create `schemas/workflow-eval-episode.schema.json`: machine-readable episode
  manifest contract.
- Create `docs/workflow-eval-episodes.md`: operator and harness-facing docs.
- Create `tests/test_regression_workflow_eval_episode.py`: RED/GREEN coverage
  for packaging, manifest validation, episode execution, and docs/schema
  references.
- Modify `scripts/evals/run_workflow_scenarios.py`: add `--episode-root` as a
  mutually exclusive alternative to `--scenario-root`.
- Modify `.github/workflows/validate-plugin.yml`: add a named CI gate that
  packages committed workflow scenarios and runs the packaged episode.
- Modify `docs/workflow-trace-evals.md`: link P15 packaging from existing eval
  docs.
- Modify `tests/test_regression_workflow_eval_docs.py` and
  `tests/test_regression_v019_release_story.py`: keep documentation and release
  story gates aligned.
- Modify `CHANGELOG.md`: document P15 in `[Unreleased]`.

## Task 1: RED Tests For Episode Packaging

**Files:**
- Create: `tests/test_regression_workflow_eval_episode.py`

- [ ] **Step 1: Add failing package and runner tests**

Add tests that expect:

```python
PACKAGE = REPO_ROOT / "scripts" / "evals" / "package_workflow_episode.py"
RUNNER = REPO_ROOT / "scripts" / "evals" / "run_workflow_scenarios.py"
SCENARIO_ROOT = REPO_ROOT / "tests" / "fixtures" / "workflow_evals"
SCHEMA = REPO_ROOT / "schemas" / "workflow-eval-episode.schema.json"
DOC = REPO_ROOT / "docs" / "workflow-eval-episodes.md"
```

Test behaviors:

- packager creates `episode.json`, `README.md`, and `scenarios/scenarios.json`;
- manifest includes local-only runtime, scorer, sandbox, limit, and privacy
  metadata;
- runner accepts `--episode-root` and returns the same passing scenario ids;
- invalid manifest with `network_access: true` is rejected;
- schema and docs contain the manifest and CLI tokens.

- [ ] **Step 2: Verify RED**

Run:

```bash
python -m pytest tests/test_regression_workflow_eval_episode.py -q
```

Expected: fail because the packager script, schema, docs, and runner flag do
not exist yet.

## Task 2: Episode Module And Schema

**Files:**
- Create: `scripts/evals/workflow_episode.py`
- Create: `schemas/workflow-eval-episode.schema.json`

- [ ] **Step 1: Implement focused module functions**

Implement:

```python
def create_episode(source_root: Path, output_dir: Path, *, episode_id: str | None = None) -> dict[str, Any]
def load_episode(root: Path) -> dict[str, Any]
def resolve_episode_scenario_root(root: Path) -> Path
```

The module should copy scenario JSON files to `scenarios/`, evaluate the copied
suite, build the manifest, write `episode.json`, write `README.md`, and reject
manifest policies that require network or point outside the episode root.

- [ ] **Step 2: Add schema**

The schema must require:

```json
[
  "schema_version",
  "episode_id",
  "title",
  "description",
  "created_by",
  "source",
  "runtime",
  "artifacts",
  "scorers",
  "sandbox",
  "limits",
  "privacy"
]
```

It must constrain `schema_version` to `1`,
`created_by` to `athanor-workflow-episode-packager`, and
`sandbox.network_access` to `false`.

- [ ] **Step 3: Run targeted tests**

Run:

```bash
python -m pytest tests/test_regression_workflow_eval_episode.py -q
```

Expected: remaining failures are CLI/runner/docs related only.

## Task 3: Packager CLI

**Files:**
- Create: `scripts/evals/package_workflow_episode.py`

- [ ] **Step 1: Add CLI**

Support:

```bash
python scripts/evals/package_workflow_episode.py \
  --scenario-root tests/fixtures/workflow_evals \
  --output-dir .athanor/episodes/workflow-evals \
  --json
```

Return `0` for passing package creation, `1` for evaluated failing scenario
suites, and `2` for invalid input/manifest errors.

- [ ] **Step 2: Run package tests**

Run:

```bash
python -m pytest tests/test_regression_workflow_eval_episode.py -q
```

Expected: runner/docs failures may remain, packager tests pass.

## Task 4: Runner Episode Support

**Files:**
- Modify: `scripts/evals/run_workflow_scenarios.py`

- [ ] **Step 1: Add mutually exclusive CLI inputs**

Use argparse's mutually exclusive group:

```python
group = parser.add_mutually_exclusive_group()
group.add_argument("--scenario-root", type=Path, default=None)
group.add_argument("--episode-root", type=Path, default=None)
```

Default to `DEFAULT_SCENARIO_ROOT` when neither is supplied. If
`--episode-root` is supplied, resolve the packaged scenario root with
`resolve_episode_scenario_root()`.

- [ ] **Step 2: Run episode runner tests**

Run:

```bash
python -m pytest tests/test_regression_workflow_eval_episode.py tests/test_regression_workflow_eval_runner.py -q
```

Expected: pass for runner behavior.

## Task 5: Docs, CI Gate, And Release Story

**Files:**
- Create: `docs/workflow-eval-episodes.md`
- Modify: `docs/workflow-trace-evals.md`
- Modify: `tests/test_regression_workflow_eval_docs.py`
- Modify: `tests/test_regression_v019_release_story.py`
- Modify: `.github/workflows/validate-plugin.yml`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Add docs and doc tests**

Document local package creation, episode execution, manifest shape, sandbox
policy, and non-goals.

- [ ] **Step 2: Add CI gate**

Add a named step before broad pytest:

```yaml
- name: Workflow episode package gate
  shell: bash
  run: |
    python scripts/evals/package_workflow_episode.py --scenario-root tests/fixtures/workflow_evals --output-dir .athanor/episodes/workflow-evals --json
    python scripts/evals/run_workflow_scenarios.py --episode-root .athanor/episodes/workflow-evals --json
```

- [ ] **Step 3: Run release/doc tests**

Run:

```bash
python -m pytest tests/test_regression_workflow_eval_docs.py tests/test_regression_v019_release_story.py -q
```

Expected: pass.

## Task 6: Focus And Full Verification

- [ ] **Step 1: Run focused suite**

```bash
python -m pytest tests/test_regression_workflow_eval_episode.py tests/test_regression_workflow_eval_runner.py tests/test_regression_workflow_eval_docs.py -q
python scripts/evals/package_workflow_episode.py --scenario-root tests/fixtures/workflow_evals --output-dir .athanor/episodes/workflow-evals --json
python scripts/evals/run_workflow_scenarios.py --episode-root .athanor/episodes/workflow-evals --json
```

- [ ] **Step 2: Run full suite and diff check**

```bash
python -m pytest tests\ -q
git diff --check
```

- [ ] **Step 3: Commit and integrate**

Commit on `feat/p15-eval-episode-packaging`, merge fast-forward to `main`,
verify again on `main`, push, and delete the feature branch.

