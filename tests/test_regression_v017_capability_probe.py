"""Regression tests for v0.17.0 (S08) hook capability spike probe.

Covers `scripts/hooks/capability_probe.py` — a passive probe that emits
`.athanor/hook-capability.json` documenting what athanor KNOWS about the
four hook event classes that matter for v0.18.0 / v0.19.0 design:

  - SessionStart      (platform mechanism; NOT athanor hook surface)
  - UserPromptSubmit  (forward-compat — stdout additionalContext)
  - PostToolUse       (forward-compat — v0.19.0 pytest exit-code sniffer)
  - PreCompact        (forward-compat — pre-compaction snapshots)

The probe is informational, not a runtime gate; honesty label "passive".
These tests assert the contract enumerated in the S08 subtask:

  1. test_probe_script_exists
  2. test_probe_script_executable
  3. test_probe_emits_valid_json (run in a tmp project root)
  4. test_capability_json_schema_documented

Plus a small set of structural-honesty checks (each event must record
`supported: false` until a spike lands, mirroring the v0.7.7 → v0.7.8 honesty
arc for the Stop hook label).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PROBE_SCRIPT = REPO_ROOT / "scripts" / "hooks" / "capability_probe.py"
SCRIPTS_HOOKS = REPO_ROOT / "scripts" / "hooks"
if str(SCRIPTS_HOOKS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_HOOKS))


# ---------------------------------------------------------------------------
# Contract 1: probe script exists
# ---------------------------------------------------------------------------


def test_probe_script_exists():
    """The probe script must live at the documented path."""
    assert PROBE_SCRIPT.is_file(), (
        f"capability probe script missing at {PROBE_SCRIPT.relative_to(REPO_ROOT)}"
    )


# ---------------------------------------------------------------------------
# Contract 2: probe script is executable (chmod +x) AND has a python shebang
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX executable bit not used on Windows")
def test_probe_script_executable():
    """The probe must be runnable as a script.

    Two layers:
      - file mode has at least one executable bit set (chmod +x), so users
        can invoke it as `./scripts/hooks/capability_probe.py`.
      - first line is a python shebang, so the OS knows what interpreter to
        use when the file is run directly.

    Skipped on Windows — POSIX executable bits are not used there; functional
    invocability is covered by the subprocess-based tests.
    """
    mode = PROBE_SCRIPT.stat().st_mode
    is_executable = bool(mode & 0o111)
    assert is_executable, (
        "capability_probe.py is not executable (chmod +x required so users "
        "can run it directly per /athanor:setup integration)."
    )
    first_line = PROBE_SCRIPT.read_text(encoding="utf-8").splitlines()[0]
    assert first_line.startswith("#!") and "python" in first_line, (
        f"capability_probe.py must begin with a python shebang; got: {first_line!r}"
    )


# ---------------------------------------------------------------------------
# Contract 3: probe emits a valid JSON document with the documented schema
# ---------------------------------------------------------------------------


def _run_probe_in(tmp_root: Path, *, extra_args: list[str] | None = None) -> tuple[int, str, str]:
    """Invoke the probe with a synthetic project root.

    We pass `--project-root` rather than `cd`-ing so the test stays
    deterministic across pytest invocation modes.
    """
    cmd = [sys.executable, str(PROBE_SCRIPT), "--project-root", str(tmp_root)]
    if extra_args:
        cmd.extend(extra_args)
    proc = subprocess.run(cmd, text=True, capture_output=True, cwd=str(tmp_root))
    return proc.returncode, proc.stdout, proc.stderr


def _make_synthetic_repo(tmp_path: Path) -> Path:
    """Build a minimal repo skeleton the probe knows how to inspect.

    Mirrors the real athanor layout so the inspection branches in
    capability_probe.py actually have something to read.
    """
    root = tmp_path / "synthrepo"
    root.mkdir()
    (root / ".git").mkdir()  # walk-up boundary marker
    (root / "athanor.json").write_text("{}", encoding="utf-8")
    # hooks/hooks.json — registers Stop + PreToolUse like real athanor
    (root / "hooks").mkdir()
    (root / "hooks" / "hooks.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "Stop": [{"hooks": [{"type": "command", "command": "x"}]}],
                    "PreToolUse": [{"hooks": [{"type": "command", "command": "y"}]}],
                }
            }
        ),
        encoding="utf-8",
    )
    # CLAUDE.md — minimal text containing the strings the inspector greps
    (root / "CLAUDE.md").write_text(
        "SessionStart is a Claude Code platform mechanism.\n",
        encoding="utf-8",
    )
    # docs/STATE.md — minimal U3 reference so the SessionStart-fiction
    # branch fires
    (root / "docs").mkdir()
    (root / "docs" / "STATE.md").write_text(
        "SessionStart fiction — athanor never wired SessionStart.\n",
        encoding="utf-8",
    )
    # spec-then-tdd-handler.md — minimal forward-compat anchor
    (root / "skills" / "work" / "references").mkdir(parents=True)
    (root / "skills" / "work" / "references" / "spec-then-tdd-handler.md").write_text(
        "PostToolUse test-evidence sniffer — v0.19.0 anchor.\n",
        encoding="utf-8",
    )
    return root


def test_probe_emits_valid_json(tmp_path):
    """Running the probe writes a parseable JSON document at the expected path."""
    root = _make_synthetic_repo(tmp_path)
    rc, _stdout, stderr = _run_probe_in(root)
    assert rc == 0, f"probe exited non-zero: rc={rc} stderr={stderr!r}"
    out_path = root / ".athanor" / "hook-capability.json"
    assert out_path.is_file(), (
        f"probe did not write {out_path.relative_to(root)} (stderr: {stderr!r})"
    )
    text = out_path.read_text(encoding="utf-8")
    # Must be valid JSON
    data = json.loads(text)
    # Top-level keys per documented schema
    assert isinstance(data, dict), "report root must be a JSON object"
    for key in (
        "schema_version",
        "probed_at",
        "probe_mode",
        "claude_code_version",  # may be null
        "athanor_registered_events",
        "events",
        "recommendations_for_v018_v019",
    ):
        assert key in data, f"missing required top-level key: {key!r}"
    # The four event keys S08 names must each appear with the documented shape
    assert set(data["events"].keys()) == {
        "SessionStart",
        "UserPromptSubmit",
        "PostToolUse",
        "PreCompact",
    }, (
        "events dict must enumerate exactly the four S08-named event types; "
        f"got {sorted(data['events'].keys())}"
    )
    # Recommendations must be a non-empty list of strings
    recs = data["recommendations_for_v018_v019"]
    assert isinstance(recs, list) and len(recs) > 0, (
        "recommendations_for_v018_v019 must be a non-empty list"
    )
    for r in recs:
        assert isinstance(r, str) and r.strip(), (
            f"recommendation must be non-empty string; got {r!r}"
        )


def test_probe_records_registered_events_from_hooks_json(tmp_path):
    """The probe must echo athanor's current hooks.json registrations.

    This is the structural-honesty anchor: if a future PR drops Stop or
    PreToolUse registration, the report should change accordingly — the
    probe is doing real inspection, not returning a static blob.
    """
    root = _make_synthetic_repo(tmp_path)
    rc, _stdout, stderr = _run_probe_in(root)
    assert rc == 0, f"probe failed: rc={rc} stderr={stderr!r}"
    data = json.loads((root / ".athanor" / "hook-capability.json").read_text())
    assert sorted(data["athanor_registered_events"]) == ["PreToolUse", "Stop"], (
        f"probe should report {{PreToolUse, Stop}} as the registered events; "
        f"got {data['athanor_registered_events']}"
    )


def test_probe_marks_all_four_events_unsupported(tmp_path):
    """Honesty invariant — until a spike lands, each event stays `supported: false`.

    This mirrors the v0.7.7 → v0.7.8 honesty arc for the Stop label. The
    probe must not silently claim capability athanor hasn't empirically
    verified.
    """
    root = _make_synthetic_repo(tmp_path)
    rc, _stdout, stderr = _run_probe_in(root)
    assert rc == 0, f"probe failed: rc={rc} stderr={stderr!r}"
    data = json.loads((root / ".athanor" / "hook-capability.json").read_text())
    for event_name, body in data["events"].items():
        assert body["supported"] is False, (
            f"event {event_name!r} must report supported=False until an "
            f"empirical spike lands; got {body!r}"
        )


def test_probe_post_tool_use_forward_compat_anchor_detected(tmp_path):
    """The PostToolUse branch must detect the v0.19.0 anchor in the handler ref."""
    root = _make_synthetic_repo(tmp_path)
    rc, _stdout, stderr = _run_probe_in(root)
    assert rc == 0, f"probe failed: rc={rc} stderr={stderr!r}"
    data = json.loads((root / ".athanor" / "hook-capability.json").read_text())
    post = data["events"]["PostToolUse"]
    assert post.get("forward_compat_anchor_present") is True, (
        "probe should detect the v0.19.0 PostToolUse sniffer anchor in "
        f"skills/work/references/spec-then-tdd-handler.md; got: {post!r}"
    )


def test_probe_handles_missing_hooks_json(tmp_path):
    """The probe must not raise when hooks/hooks.json is absent — passive
    probes never fail the caller."""
    root = tmp_path / "bare"
    root.mkdir()
    (root / ".git").mkdir()
    (root / "athanor.json").write_text("{}", encoding="utf-8")
    rc, _stdout, stderr = _run_probe_in(root)
    assert rc == 0, (
        f"probe must exit 0 even with missing inputs (passive probe contract); "
        f"rc={rc} stderr={stderr!r}"
    )
    out_path = root / ".athanor" / "hook-capability.json"
    assert out_path.is_file()
    data = json.loads(out_path.read_text())
    assert data["athanor_registered_events"] == [], (
        "with no hooks.json, registered_events must be empty list"
    )


# ---------------------------------------------------------------------------
# Contract 4: capability JSON schema is documented (in the script itself)
# ---------------------------------------------------------------------------


def test_capability_json_schema_documented():
    """The probe script must document its output schema.

    We treat the script's own module-docstring + per-event helper
    docstrings as the authoritative schema doc. The honesty rule: every
    top-level key in the emitted JSON must be name-checkable against the
    script source.
    """
    src = PROBE_SCRIPT.read_text(encoding="utf-8")
    required_doc_strings = [
        # Section headers / API surface that must be discoverable in source
        "SessionStart",
        "UserPromptSubmit",
        "PostToolUse",
        "PreCompact",
        # Top-level fields the report emits
        "schema_version",
        "probed_at",
        "probe_mode",
        "athanor_registered_events",
        "recommendations_for_v018_v019",
        # Honesty anchors
        "passive",
    ]
    missing = [s for s in required_doc_strings if s not in src]
    assert not missing, (
        "capability_probe.py must document its schema; missing strings: "
        f"{missing}"
    )


def test_real_repo_probe_runs_against_athanor_itself():
    """Smoke: running the probe against the real athanor repo succeeds and
    produces a JSON file at .athanor/hook-capability.json.

    This is the integration anchor — it ensures the inspection branches
    that read real CLAUDE.md / STATE.md / handler.md don't crash on the
    real (large, unicode-rich) inputs.
    """
    cmd = [sys.executable, str(PROBE_SCRIPT), "--project-root", str(REPO_ROOT)]
    proc = subprocess.run(cmd, text=True, capture_output=True, cwd=str(REPO_ROOT))
    assert proc.returncode == 0, (
        f"probe failed against real repo: rc={proc.returncode} "
        f"stderr={proc.stderr!r}"
    )
    out_path = REPO_ROOT / ".athanor" / "hook-capability.json"
    assert out_path.is_file()
    data = json.loads(out_path.read_text(encoding="utf-8"))
    # Real athanor registers exactly Stop + PreToolUse as of v0.17.0
    assert "Stop" in data["athanor_registered_events"]
    assert "PreToolUse" in data["athanor_registered_events"]


# ---------------------------------------------------------------------------
# Bonus: probe is importable for white-box testing of the report builder
# ---------------------------------------------------------------------------


def test_build_capability_report_is_importable(tmp_path):
    """The probe's `build_capability_report` helper is importable from tests
    so future regression locks can exercise specific event branches without
    spawning a subprocess."""
    import capability_probe  # noqa: F401 — verifies module loads
    root = _make_synthetic_repo(tmp_path)
    report = capability_probe.build_capability_report(root)
    assert isinstance(report, dict)
    assert report["schema_version"] == 1
    assert report["probe_mode"] == "passive"
