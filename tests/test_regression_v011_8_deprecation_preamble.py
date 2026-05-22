"""Regression tests for v0.11.8 → v0.12.0 deprecation cycle closure.

## Scope

v0.11.8 (2026-05-22) shipped a deprecation warning cycle that injected an
in-skill preamble (`<!-- athanor:deprecated v=1 since=0.11.8 removal=0.12.0 -->`)
into 45 vendored SKILL.md files (5 LIFT + 40 DROP). v0.12.0 (Subtask 15)
completes the cycle by atomically removing those files via
`scripts/v012_remove_vendored.py`.

This test file was rewritten in Subtask 15 because its pre-v0.12.0 form
asserted that the 45 SKILL.md files exist on disk and carry the
deprecation sentinel. Post-removal those files are gone, so the
existence-and-sentinel assertions no longer apply. The rewritten test
file pins three v0.12.0-state invariants instead:

  1. The 45 DEPRECATION_TARGETS paths are absent on disk (the cycle's
     promised removal completed).
  2. `ce-test-browser` (D8 KEEP) survives.
  3. The Stop hook carve-out for the deprecation sentinel still triggers
     correctly — relevant when historical CHANGELOG / archive prose
     quotes the sentinel literal in a fresh assistant turn.

D14.2 correction: scope is 45 files (5 LIFT + 40 DROP), not 44.

D8 carve-out: ce-test-browser is the sole KEEP.

D7 voice constraints: forbidden phrases ("translated", "interpreted",
"we discovered", "natural maturation") do not appear in this test file.

Plan reference: docs/plans/2026-05-22-001-feat-v0.12.0-concept-kernel-cutover-plan-b.md
§Subtask 15. Earlier plan: v0.11.8 deprecation cycle.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
STOP_VERIFY_CLAIMS = REPO_ROOT / "scripts" / "hooks" / "stop_verify_claims.py"
HOOK_STATE_DIR = REPO_ROOT / ".athanor" / "sessions" / "active" / ".hook-state"

SENTINEL = "<!-- athanor:deprecated v=1 since=0.11.8 removal=0.12.0 -->"


# ---------------------------------------------------------------------------
# D14.2 target list — 45 SKILL.md paths (5 LIFT + 40 DROP). These were the
# deprecation targets in v0.11.8 and the removal targets in v0.12.0.
# Hardcoded so disk drift cannot silently change scope.
# ---------------------------------------------------------------------------

LIFT_TARGETS: list[str] = [
    "ce-brainstorm",
    "ce-code-review",
    "ce-doc-review",
    "sp-systematic-debugging",
    "sp-using-superpowers",
]

DROP_TARGETS: list[str] = [
    # ce-* DROP (28 entries)
    "ce-agent-native-architecture",
    "ce-agent-native-audit",
    "ce-clean-gone-branches",
    "ce-commit",
    "ce-commit-push-pr",
    "ce-compound",
    "ce-compound-refresh",
    "ce-debug",
    "ce-demo-reel",
    "ce-dhh-rails-style",
    "ce-frontend-design",
    "ce-gemini-imagegen",
    "ce-ideate",
    "ce-lfg",
    "ce-optimize",
    "ce-plan",
    "ce-polish-beta",
    "ce-product-pulse",
    "ce-proof",
    "ce-resolve-pr-feedback",
    "ce-riffrec-feedback-analysis",
    "ce-sessions",
    "ce-simplify-code",
    "ce-slack-research",
    "ce-strategy",
    "ce-test-xcode",
    "ce-work",
    "ce-work-beta",
    "ce-worktree",
    # sp-* DROP (12 entries)
    "sp-brainstorming",
    "sp-dispatching-parallel-agents",
    "sp-executing-plans",
    "sp-finishing-a-development-branch",
    "sp-receiving-code-review",
    "sp-requesting-code-review",
    "sp-subagent-driven-development",
    "sp-test-driven-development",
    "sp-using-git-worktrees",
    "sp-writing-plans",
    "sp-writing-skills",
]

DEPRECATION_TARGETS: list[str] = LIFT_TARGETS + DROP_TARGETS

KEEP_SKILLS: list[str] = ["ce-test-browser"]


# ---------------------------------------------------------------------------
# Scope sanity (covers D14.2 count + KEEP carve-out)
# ---------------------------------------------------------------------------


def test_deprecation_target_count_is_45():
    """D14.2: scope is 5 LIFT + 40 DROP = 45 SKILL.md files."""
    assert len(LIFT_TARGETS) == 5, f"expected 5 LIFT entries, got {len(LIFT_TARGETS)}"
    assert len(DROP_TARGETS) == 40, f"expected 40 DROP entries, got {len(DROP_TARGETS)}"
    assert len(DEPRECATION_TARGETS) == 45, (
        f"D14.2 corrected count is 45 (5 LIFT + 40 DROP); got {len(DEPRECATION_TARGETS)}"
    )


def test_keep_skill_is_only_ce_test_browser():
    """D8: ce-test-browser is the only KEEP carve-out."""
    assert KEEP_SKILLS == ["ce-test-browser"]


# ---------------------------------------------------------------------------
# v0.12.0 cycle-closure invariants
# ---------------------------------------------------------------------------


def test_all_45_deprecation_targets_removed_in_v012():
    """v0.12.0 closure: every path in DEPRECATION_TARGETS is absent on
    disk post-Subtask-15. The v0.11.8 deprecation cycle promised removal
    at v0.12.0; Subtask 15 fulfils that promise."""
    still_present: list[str] = []
    for name in DEPRECATION_TARGETS:
        if (SKILLS_DIR / name).exists():
            still_present.append(name)
    assert not still_present, (
        f"v0.12.0 closure: {len(still_present)} of 45 deprecation targets "
        f"still present on disk: {still_present!r}. Re-run "
        f"`python3 scripts/v012_remove_vendored.py` to complete the cut."
    )


def test_ce_test_browser_keep_skill_still_present():
    """D8 invariant: ce-test-browser survives the v0.12.0 cut.

    The pre-v0.12.0 test asserted the sentinel was absent from the file;
    post-v0.12.0 we assert the file itself survives — that's the D8
    carve-out's structural commitment.
    """
    keep_path = SKILLS_DIR / "ce-test-browser" / "SKILL.md"
    assert keep_path.is_file(), (
        f"D8 invariant: ce-test-browser KEEP skill must survive v0.12.0 "
        f"cut at {keep_path}"
    )


# ---------------------------------------------------------------------------
# Stop hook carve-out for the deprecation sentinel — remains relevant
# because CHANGELOG / archive prose may quote the sentinel literal in a
# fresh assistant turn (e.g., "v0.11.8 injected the
# <!-- athanor:deprecated v=1 since=0.11.8 removal=0.12.0 --> sentinel
# into 45 SKILL.md files"). The hook must NOT block such retrospective
# turns.
# ---------------------------------------------------------------------------


def _clean_hook_state():
    if HOOK_STATE_DIR.exists():
        shutil.rmtree(HOOK_STATE_DIR, ignore_errors=True)


def _setup_project_for_stop_hook(tmp_path: Path) -> Path:
    """Create a minimal project dir with athanor.json + hook-state dir."""
    (tmp_path / ".athanor" / "sessions" / "active" / ".hook-state").mkdir(
        parents=True, exist_ok=True
    )
    (tmp_path / "athanor.json").write_text(
        '{"hooks": {"profile": "standard", "stopLoopThreshold": 3}}',
        encoding="utf-8",
    )
    return tmp_path


def _write_transcript_with_response(tmp_path: Path, response_text: str) -> Path:
    """Write a single-line transcript JSONL with one main-session assistant
    entry whose text content is `response_text`."""
    tpath = tmp_path / "transcript.jsonl"
    entry = {
        "type": "assistant",
        "isSidechain": False,
        "message": {
            "role": "assistant",
            "content": [{"type": "text", "text": response_text}],
        },
    }
    tpath.write_text(json.dumps(entry) + "\n", encoding="utf-8")
    return tpath


def _run_stop_hook(payload: dict, cwd: Path) -> tuple[int, str]:
    """Invoke stop_verify_claims.py with payload; return (exit_code, stderr)."""
    result = subprocess.run(
        [sys.executable, str(STOP_VERIFY_CLAIMS)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=cwd,
    )
    return result.returncode, result.stderr


def test_stop_hook_exits_0_when_response_starts_with_deprecation_sentinel(
    tmp_path: Path,
):
    """MUST 3 invariant carry-forward: stop_verify_claims.py must exit 0
    (not 2) when the model response begins with the deprecation sentinel.

    Pre-v0.12.0 this guarded the v0.11.8 deprecation-cycle turns from
    re-entering the gate. Post-v0.12.0 the same carve-out remains useful
    for retrospective turns that quote the sentinel literal.
    """
    _clean_hook_state()
    try:
        project = _setup_project_for_stop_hook(tmp_path)
        body = (
            f"{SENTINEL}\n"
            "ce-foo is deprecated and removed in v0.12.0. "
            "tests pass on my machine after the migration."
        )
        transcript = _write_transcript_with_response(project, body)
        payload = {
            "session_id": "test-deprecation",
            "transcript_path": str(transcript),
            "stop_hook_active": False,
            "hook_event_name": "Stop",
        }
        exit_code, stderr = _run_stop_hook(payload, project)
        assert exit_code == 0, (
            f"Stop hook must carve out the deprecation sentinel and "
            f"exit 0. Got exit={exit_code} stderr={stderr!r}"
        )
    finally:
        _clean_hook_state()
