"""Regression tests for repository-root pytest isolation.

The repo keeps external reference clones under ``ref/``. Those repositories are
analysis inputs, not part of Athanor's pytest suite.
"""
from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = REPO_ROOT / "pyproject.toml"


def test_pyproject_limits_pytest_discovery_to_tests_tree() -> None:
    config = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    pytest_options = config["tool"]["pytest"]["ini_options"]

    assert pytest_options["testpaths"] == ["tests"]
    assert set(pytest_options["norecursedirs"]) >= {
        ".athanor",
        ".git",
        ".pytest_cache",
        ".venv",
        "__pycache__",
        "ref",
    }


def test_root_pytest_collects_repo_tests_without_ref_tree() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )

    output = (proc.stdout + proc.stderr).replace("\\", "/")
    assert proc.returncode == 0, output
    assert "ref/" not in output
