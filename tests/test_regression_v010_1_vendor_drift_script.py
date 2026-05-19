"""Regression test for v0.10.1 U1 invariant — `scripts/check_vendor_drift.py`
exists, is invocable, and produces sensible exit codes.

Exit code contract:
  0 — no drift detected (vendored tree matches upstream caches)
  1 — drift detected
  2 — upstream cache unreachable

Plan reference: docs/plans/2026-05-19-004-feat-v0.10.1-vendor-hygiene-plan.md
§U1.

CI note: GitHub Actions runners do not have the upstream plugin caches
installed. Tests that need a working cache use a tiny on-disk fixture
under tmp_path to simulate the cache structure expected by the script.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check_vendor_drift.py"


def _run_drift(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=REPO_ROOT,
        **kwargs,
    )


def _make_minimal_cache(tmp_path: Path) -> Path:
    """Build a minimal plugin-cache structure with one CE skill + one
    superpowers skill that matches what's currently vendored. Returns
    the cache root for --cache-root override.
    """
    cache_root = tmp_path / "cache"
    # CE: skills/ce-plan/SKILL.md — copy from athanor's vendored copy with
    # provenance stripped (so the script's normalization passes).
    ce_skill_src = REPO_ROOT / "skills" / "ce-plan" / "SKILL.md"
    if not ce_skill_src.exists():
        pytest.skip("No vendored skill available to build cache fixture")
    ce_dst = cache_root / "compound-engineering-plugin" / "compound-engineering" / "3.8.3" / "skills" / "ce-plan"
    ce_dst.mkdir(parents=True, exist_ok=True)
    text = ce_skill_src.read_text(encoding="utf-8")
    start = text.find("<!-- Provenance:")
    end = text.find("-->", start) + len("-->") if start >= 0 else 0
    if start >= 0:
        # Strip the provenance block AND its surrounding blank-line padding
        # so the fixture's body matches what the script will see when it
        # strips provenance from the vendored side.
        text = text[:start].rstrip() + "\n" + text[end:].lstrip()
    ce_dst.joinpath("SKILL.md").write_text(text, encoding="utf-8")
    # Superpowers: skills/brainstorming/SKILL.md (upstream name UNPREFIXED)
    sp_skill_src = REPO_ROOT / "skills" / "sp-brainstorming" / "SKILL.md"
    if sp_skill_src.exists():
        sp_dst = cache_root / "claude-plugins-official" / "superpowers" / "5.1.0" / "skills" / "brainstorming"
        sp_dst.mkdir(parents=True, exist_ok=True)
        text = sp_skill_src.read_text(encoding="utf-8")
        start = text.find("<!-- Provenance:")
        end = text.find("-->", start) + len("-->") if start >= 0 else 0
        if start >= 0:
            text = text[:start].rstrip() + "\n" + text[end:].lstrip()
        # Also restore the upstream frontmatter `name:` (vendor renamed it)
        text = text.replace("name: sp-brainstorming", "name: brainstorming", 1)
        sp_dst.joinpath("SKILL.md").write_text(text, encoding="utf-8")
    return cache_root


def test_script_exists_and_is_executable_python():
    """MUST: script file exists and starts with a Python shebang."""
    assert SCRIPT.exists(), f"Drift script missing: {SCRIPT}"
    first_line = SCRIPT.read_text(encoding="utf-8").splitlines()[0]
    assert first_line.startswith("#!") and "python" in first_line, (
        f"Drift script shebang must invoke python; first line: {first_line!r}"
    )


def test_script_help_works():
    """MUST: --help exits 0 and prints a usage banner."""
    result = _run_drift(["--help"])
    assert result.returncode == 0
    assert "drift" in result.stdout.lower() or "vendor" in result.stdout.lower()


def test_unreachable_cache_yields_exit_2():
    """MUST: pointing the script at a non-existent cache root returns
    exit code 2 (upstream unreachable)."""
    result = _run_drift(["--cache-root", "/tmp/__athanor_nonexistent_cache__"])
    assert result.returncode == 2, (
        f"Expected exit 2 for missing cache; got {result.returncode}. "
        f"stderr: {result.stderr[:200]}"
    )


def test_single_skill_filter_works(tmp_path):
    """MUST: --skill filter limits the diff to one skill.

    Uses a fixture cache so CI runners without the real upstream plugin
    caches can still exercise the filter.
    """
    cache_root = _make_minimal_cache(tmp_path)
    result = _run_drift(["--skill", "ce-plan", "--ci", "--cache-root", str(cache_root)])
    assert "total=1" in result.stdout, (
        f"--skill filter must restrict to total=1. stdout: {result.stdout!r} "
        f"stderr: {result.stderr!r}"
    )


def test_ci_mode_suppresses_per_skill_output(tmp_path):
    """MUST: --ci mode prints only the one-line summary (per-skill drift
    bodies suppressed)."""
    cache_root = _make_minimal_cache(tmp_path)
    result = _run_drift(["--ci", "--cache-root", str(cache_root)])
    assert "@@" not in result.stdout, (
        "--ci mode must not emit unified-diff bodies"
    )
    assert "check_vendor_drift:" in result.stdout, (
        f"--ci mode must still print the summary line. stdout: {result.stdout!r}"
    )
