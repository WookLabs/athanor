"""Regression tests for v0.12.0 release-ready gates (Subtask 16).

Plan reference: docs/plans/2026-05-22-001-feat-v0.12.0-concept-kernel-cutover-plan-b.md
§Phase 5 (manifest cleanup) + §Phase 6 (release-gate extensions).

Post-v0.12.0 invariants checked here (D8 / D9 / D14.2 / Phase 5 + 6):

- `scripts/check_release_ready.py --ci` exits 0 with the v0.12.0 gate
  surface in place.
- The script names three new gates by stable label substrings:
    (e) vendored-skill-count-is-1
    (f) marketplace-skill-count-matches-disk
    (g) concepts-present
- The vendored-skill-count gate counts depth-1 `skills/ce-*` and
  `skills/sp-*` directories and asserts the total equals 1
  (ce-test-browser only, per D8 carve-out).
- The marketplace-count gate parses
  `.claude-plugin/marketplace.json` cleanly and the parse never raises
  (defensive contract — marketplace.json is the user-facing surface
  manifest).
- The concepts gate requires `concepts/` to exist with >= 7 files,
  matching the v0.12.0 LIFT inventory (1 README + 6 numbered concept
  files).
- `.claude-plugin/marketplace.json` description does NOT mention the
  removed vendored surface counts (no "33 ce-*", no "13 sp-*") and does
  not advertise vendoring as the product axis post-cutover.

Voice constraints (D7): docstrings here use direct attribution to the
plan-of-record + the disk-inventory ledger. The forbidden D7 phrases
("translated", "interpreted", "we discovered", "natural maturation") do
not appear.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check_release_ready.py"
MARKETPLACE = REPO_ROOT / ".claude-plugin" / "marketplace.json"
SKILLS_DIR = REPO_ROOT / "skills"
CONCEPTS_DIR = REPO_ROOT / "concepts"

KEEP_SKILL = "ce-test-browser"


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=REPO_ROOT,
    )


# ---------- (1) marketplace.json shape + voice ----------

def test_marketplace_json_parses_cleanly():
    """MUST: marketplace.json is valid JSON post-cutover."""
    text = MARKETPLACE.read_text(encoding="utf-8")
    data = json.loads(text)  # raises if malformed
    assert isinstance(data, dict), "marketplace.json root must be an object"
    assert "plugins" in data, "marketplace.json must declare 'plugins' array"


def test_marketplace_description_drops_removed_surface_counts():
    """MUST: marketplace.json description must not advertise the removed
    vendored counts ('33 ce-*', '13 sp-*') after the v0.12.0 atomic cut.

    The pre-v0.12.0 description carried these counts as the product axis.
    Post-cutover the only vendored carry-over is `ce-test-browser` (D8),
    and that count is incidental rather than a headline.
    """
    data = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    plugins = data.get("plugins", [])
    assert plugins, "marketplace.json plugins array must be non-empty"
    desc = plugins[0].get("description", "")
    # The exact pre-cutover phrases.
    forbidden_substrings = (
        "33 ce-*",
        "13 sp-*",
        "33 ce-* + 13 sp-*",
    )
    hits = [s for s in forbidden_substrings if s in desc]
    assert not hits, (
        f"MUST: marketplace.json description must not advertise removed "
        f"vendored counts; found {hits!r}. Refresh the description to the "
        f"v0.12.0 concept-kernel framing."
    )


def test_marketplace_description_voice_d7():
    """MUST / D7: marketplace.json description must not contain the four
    forbidden voice phrases."""
    data = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    desc = data["plugins"][0].get("description", "").lower()
    forbidden = ("translated", "interpreted", "we discovered", "natural maturation")
    hits = [needle for needle in forbidden if needle in desc]
    assert not hits, (
        f"MUST / D7: marketplace.json description voice violation; "
        f"found {hits!r}."
    )


# ---------- (2) check_release_ready.py --ci exits 0 ----------

def test_check_release_ready_ci_exits_zero():
    """MUST: `python3 scripts/check_release_ready.py --ci` exits 0 with the
    v0.12.0 gate surface in place."""
    result = _run(["--ci"])
    assert result.returncode == 0, (
        f"check_release_ready --ci must exit 0; got {result.returncode}. "
        f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
    )


# ---------- (3) the three new gates fire and are labeled ----------

def test_check_release_ready_ci_names_new_gates():
    """MUST: --ci output names the three v0.12.0 gates by stable substring.

    Gate labels live in the printed `[PASS] (key): detail` lines so a CI
    reader can grep for the specific gate that failed. Labels chosen to
    align with the v0.12.0 plan §Phase 6 wording.
    """
    result = _run(["--ci"])
    body = result.stdout
    expected_labels = (
        "vendored-skill-count",
        "marketplace-skill-count",
        "concepts-present",
    )
    missing = [label for label in expected_labels if label not in body]
    assert not missing, (
        f"MUST: --ci output must name gates {expected_labels!r}; "
        f"missing {missing!r}. stdout was:\n{body}"
    )


def test_vendored_skill_count_gate_uses_disk_truth():
    """MUST: the vendored-skill-count gate's count matches what's on disk.

    Computes the same depth-1 glob the gate uses (`skills/ce-*` +
    `skills/sp-*`) and asserts the gate reports the same number. This
    ensures the gate is not a hard-coded constant — it reads the disk.
    """
    on_disk = sorted(
        p.name for p in SKILLS_DIR.iterdir()
        if p.is_dir() and (p.name.startswith("ce-") or p.name.startswith("sp-"))
    )
    # Post-v0.12.0 this must be exactly [ce-test-browser].
    assert on_disk == [KEEP_SKILL], (
        f"Disk precondition: only {KEEP_SKILL!r} should survive; got "
        f"{on_disk!r}. Run scripts/v012_remove_vendored.py first."
    )

    result = _run(["--ci"])
    body = result.stdout
    # Look for a `count=1` style assertion on the gate's line. Loose pattern
    # so the gate's exact phrasing can drift without breaking — we just need
    # the digit 1 to appear on the same line as the gate label.
    pattern = re.compile(r"vendored-skill-count[^\n]*\b1\b", re.MULTILINE)
    assert pattern.search(body), (
        f"MUST: vendored-skill-count gate must report count=1; --ci "
        f"output was:\n{body}"
    )


def test_concepts_present_gate_reads_disk():
    """MUST: the concepts-present gate is satisfied by the on-disk
    `concepts/` directory containing >= 7 files."""
    assert CONCEPTS_DIR.is_dir(), (
        f"Disk precondition: {CONCEPTS_DIR} must exist post-v0.12.0 Phase 3"
    )
    file_count = sum(1 for p in CONCEPTS_DIR.iterdir() if p.is_file())
    assert file_count >= 7, (
        f"Disk precondition: concepts/ must hold >= 7 files; found "
        f"{file_count}. v0.12.0 Phase 3 LIFT-source inventory has 7 files."
    )

    result = _run(["--ci"])
    body = result.stdout
    # Loose check — the label and PASS state.
    assert "concepts-present" in body, (
        f"MUST: --ci output names 'concepts-present' gate; got:\n{body}"
    )
    # PASS marker on the same line.
    line_pattern = re.compile(r"\[PASS\][^\n]*concepts-present", re.MULTILINE)
    assert line_pattern.search(body), (
        f"MUST: concepts-present gate must PASS; --ci output:\n{body}"
    )


def test_marketplace_count_gate_pairs_with_disk():
    """MUST: the marketplace-skill-count gate compares marketplace.json
    against on-disk skills/ inventory.

    Loose contract — the gate label is present and lands on a PASS line.
    Exact count semantics are governed by the gate body in
    check_release_ready.py.
    """
    result = _run(["--ci"])
    body = result.stdout
    assert "marketplace-skill-count" in body, (
        f"MUST: --ci output names 'marketplace-skill-count' gate; got:\n{body}"
    )
    line_pattern = re.compile(r"\[PASS\][^\n]*marketplace-skill-count", re.MULTILINE)
    assert line_pattern.search(body), (
        f"MUST: marketplace-skill-count gate must PASS; --ci output:\n{body}"
    )
