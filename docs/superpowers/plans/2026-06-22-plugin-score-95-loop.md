# Plugin Score 95 Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Raise the engineering score from 82/100 toward 95/100 by removing the concrete runtime, test isolation, and packaging weaknesses found in the audit.

**Architecture:** Keep runtime behavior minimal and fail-open where the hooks already require it, but make root/session discovery use the same project anchor in installed plugin contexts. Keep live Claude CLI validation in the explicit distribution smoke gate while making regular pytest deterministic and fast.

**Tech Stack:** Python stdlib hook scripts, pytest, uv project metadata, JSON schema-backed gates.

---

### Task 1: Root Pytest Isolation

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/test_regression_pytest_isolation.py`

- [ ] **Step 1: Write the failing test**

```python
def test_root_pytest_collects_repo_tests_without_ref_tree():
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "ref/" not in proc.stdout.replace("\\", "/")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_regression_pytest_isolation.py -q`

Expected: FAIL because root pytest collection currently enters `ref/`.

- [ ] **Step 3: Add pytest configuration**

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
norecursedirs = [".athanor", ".git", ".pytest_cache", ".venv", "__pycache__", "ref"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_regression_pytest_isolation.py -q`

Expected: PASS, root collect-only stays inside `tests/`.

### Task 2: Installed Hook Project Root

**Files:**
- Modify: `scripts/hooks/_athanor_hook_runtime.py`
- Modify: `tests/test_regression_v017_hook_runtime.py`
- Modify: `tests/test_regression_v019_posttool_evidence_sniffer.py`

- [ ] **Step 1: Write failing tests**

```python
def test_resolve_project_root_prefers_claude_project_dir(monkeypatch, tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "athanor.json").write_text("{}", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project))
    with chdir(outside):
        assert runtime.resolve_project_root() == project.resolve()
```

```python
def test_env_project_dir_allows_installed_hook_cwd_to_write_evidence(sniffer, monkeypatch, tmp_path):
    root, session_dir = _project_with_session(tmp_path)
    outside = tmp_path / "plugin-cache"
    outside.mkdir()
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    monkeypatch.chdir(outside)
    exit_code, stderr = sniffer.evaluate_payload(_bash_payload("pytest tests -q", exit_code=0))
    assert exit_code == 0
    assert stderr == ""
    assert _records(session_dir)[0]["session_id"] == session_dir.name
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_regression_v017_hook_runtime.py::test_resolve_project_root_prefers_claude_project_dir tests/test_regression_v019_posttool_evidence_sniffer.py::test_env_project_dir_allows_installed_hook_cwd_to_write_evidence -q`

Expected: FAIL because `resolve_project_root()` only walks from cwd.

- [ ] **Step 3: Implement environment-aware root discovery**

Add `CLAUDE_PROJECT_DIR` handling to `resolve_project_root()` when the env path contains `.git/` or `athanor.json`; otherwise keep the existing cwd walk-up behavior.

- [ ] **Step 4: Run targeted tests**

Run: `python -m pytest tests/test_regression_v017_hook_runtime.py tests/test_regression_v019_posttool_evidence_sniffer.py -q`

Expected: PASS.

### Task 3: Pytest Evidence Scope

**Files:**
- Modify: `scripts/hooks/posttool_evidence_sniffer.py`
- Modify: `tests/test_regression_v019_posttool_evidence_sniffer.py`

- [ ] **Step 1: Write the failing test**

```python
def test_pytest_without_targets_marks_full_suite_scope(sniffer, tmp_path):
    root, session_dir = _project_with_session(tmp_path)
    payload = _bash_payload("python -m pytest -q", exit_code=0, stdout="1491 passed")
    exit_code, stderr = sniffer.evaluate_payload(payload, project_root=root)
    assert exit_code == 0
    assert stderr == ""
    assert _records(session_dir)[0]["scope"] == "full_suite"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_regression_v019_posttool_evidence_sniffer.py::test_pytest_without_targets_marks_full_suite_scope -q`

Expected: FAIL because targetless pytest is currently `unspecified`.

- [ ] **Step 3: Treat no explicit pytest targets as full suite**

Change `_scope_for_targets([])` to return `full_suite`.

- [ ] **Step 4: Run targeted tests**

Run: `python -m pytest tests/test_regression_v019_posttool_evidence_sniffer.py -q`

Expected: PASS.

### Task 4: Fast Regression Smoke

**Files:**
- Modify: `tests/test_regression_distribution_smoke.py`
- Modify: `docs/distribution-smoke.md`

- [ ] **Step 1: Keep live CLI validation in the gate**

The CI workflow must keep `python scripts/gates/distribution_smoke.py --json`.

- [ ] **Step 2: Make regular pytest skip live Claude CLI**

Change current-repo distribution smoke regression calls to pass `--skip-claude`; keep explicit assertions that the manifest fallback still validates package inventory.

- [ ] **Step 3: Run targeted tests**

Run: `python -m pytest tests/test_regression_distribution_smoke.py -q`

Expected: PASS with no live Claude CLI dependency.

### Task 5: Ship Profile Metadata Classification

**Files:**
- Modify: `scripts/gates/package_footprint_policy.py`
- Modify: `tests/test_regression_package_footprint_policy.py`
- Modify: `docs/package-footprint-policy.md`
- Modify: `docs/package-footprint-reduction.md`

- [ ] **Step 1: Write failing test**

Add `pyproject.toml`, `.python-version`, and `uv.lock` to the footprint fixture and assert they are `development_metadata` with explicit ship-profile decisions.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_regression_package_footprint_policy.py::test_build_report_classifies_ship_profile_buckets -q`

Expected: FAIL because those files currently fall into `other` and ship profile.

- [ ] **Step 3: Add exact-file development metadata handling**

Classify those exact files as `development_metadata` and exclude them from the default ship profile.

- [ ] **Step 4: Run targeted tests and gates**

Run: `python -m pytest tests/test_regression_package_footprint_policy.py -q`

Expected: PASS.

### Task 6: Verification and Score Reassessment

**Files:**
- No new files.

- [ ] **Step 1: Run focused tests**

Run: `python -m pytest tests/test_regression_pytest_isolation.py tests/test_regression_v017_hook_runtime.py tests/test_regression_v019_posttool_evidence_sniffer.py tests/test_regression_distribution_smoke.py tests/test_regression_package_footprint_policy.py -q`

- [ ] **Step 2: Run key gates**

Run:

```bash
python scripts/gates/runtime_conformance.py --json
python scripts/gates/distribution_smoke.py --json
python scripts/gates/package_footprint_policy.py --json
python scripts/gates/codex_mirror_parity.py --json
python scripts/gates/package_knowledge_index.py --json
```

- [ ] **Step 3: Re-score**

95/100 requires these concrete conditions:
- root pytest collection ignores `ref/`;
- PostToolUse evidence writes from installed-plugin cwd when `CLAUDE_PROJECT_DIR` points at the project;
- targetless pytest evidence counts as full-suite evidence;
- regular regression smoke avoids live CLI latency while live gate remains available;
- Python project metadata is explicitly classified in the ship profile.
