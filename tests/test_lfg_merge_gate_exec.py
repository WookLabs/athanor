"""Executable regression — /athanor:lfg Step 8.5 merge-readiness verdict GATE.

Locks the EXECUTABLE disposition of `scripts/gates/lfg_merge_gate.py` (C001/G1):
the safety-critical G0–G4 merge verdict is lifted out of hand-interpreted leader
bash into a single fail-loud, regression-tested pure verdict function. The script
consumes one `gh pr view --json …` snapshot on stdin (+ named `--findings-file`
paths) and emits a machine verdict (`merge | block | skip`) with the deciding
clause, via an explicit exit-code map (0=merge, 2=malformed, 3=block, 4=skip).

The one genuinely-new safety property over today's prose: an unknown
`mergeStateStatus`/`mergeable` enum **ERRORS (exit 2) instead of silently
passing** (the fail-loud crux — fixtures 5/6). `{UNSTABLE}` resolves to **block**
(C1: a settled state, NOT mergeable in v1; re-poll is keyed only on
`mergeable ∈ {UNKNOWN, null}` / `mergeStateStatus == UNKNOWN`).

Subprocess style mirrors `tests/test_regression_lfg_fix_round_counter.py`. This
file matches the `tests/test_*lfg_merge_gate*.py` glob (R4/AE1) and leaves
`tests/test_regression_lfg_merge_gate.py` byte-untouched (R5/AE3). These tests are
RED before the script exists.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLI = REPO_ROOT / "scripts" / "gates" / "lfg_merge_gate.py"

EXIT_MERGE = 0
EXIT_MALFORMED = 2
EXIT_BLOCK = 3
EXIT_SKIP = 4


def _run(stdin: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        input=stdin,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


def _pr(**overrides) -> str:
    """A baseline OPEN, non-draft, MERGEABLE/CLEAN PR snapshot as a JSON string."""
    pr = {
        "number": 69,
        "url": "https://example.test/pr/69",
        "state": "OPEN",
        "isDraft": False,
        "mergeable": "MERGEABLE",
        "mergeStateStatus": "CLEAN",
        "headRefName": "feature/x",
        "baseRefName": "main",
        "body": "All good. Nothing to see here.",
    }
    pr.update(overrides)
    return json.dumps(pr)


# ---------------------------------------------------------------------------
# Smoke
# ---------------------------------------------------------------------------
def test_cli_file_exists():
    assert CLI.is_file(), f"gate CLI not at {CLI}"


# ---------------------------------------------------------------------------
# Fixture 1 — {UNSTABLE} → BLOCK / G4 / exit 3 (C1: settled, NOT mergeable v1).
# ---------------------------------------------------------------------------
def test_unstable_is_block_not_skip():
    p = _run(_pr(mergeStateStatus="UNSTABLE"))
    assert p.returncode == EXIT_BLOCK, (
        f"UNSTABLE must BLOCK (exit 3), never skip/re-poll (C1); got "
        f"{p.returncode}, stdout={p.stdout!r} stderr={p.stderr!r}"
    )
    v = json.loads(p.stdout)
    assert v["verdict"] == "block", f"UNSTABLE verdict must be block; got {v!r}"
    assert v["clause"] == "G4", f"UNSTABLE clause must be G4; got {v!r}"
    assert v["method"] is None, f"a block verdict carries method=null; got {v!r}"
    assert v["mergeStateStatus"] == "UNSTABLE", f"must echo mergeStateStatus; got {v!r}"


# ---------------------------------------------------------------------------
# Fixture 2a/2b — {mergeable:null} unsettled → skip; --repoll-exhausted → block.
# ---------------------------------------------------------------------------
def test_mergeable_null_unsettled_skips():
    p = _run(_pr(mergeable=None, mergeStateStatus="UNKNOWN"))
    assert p.returncode == EXIT_SKIP, (
        f"unsettled mergeability (mergeable=null) must SKIP (exit 4) for the "
        f"leader to re-poll; got {p.returncode}, stdout={p.stdout!r}"
    )
    v = json.loads(p.stdout)
    assert v["verdict"] == "skip", f"unsettled verdict must be skip; got {v!r}"
    assert v["clause"] == "G4-unsettled", f"clause must be G4-unsettled; got {v!r}"


def test_repoll_exhausted_converts_unsettled_to_block():
    p = _run(_pr(mergeable=None, mergeStateStatus="UNKNOWN"), "--repoll-exhausted")
    assert p.returncode == EXIT_BLOCK, (
        f"--repoll-exhausted must convert unsettled SKIP into BLOCK (exit 3) — "
        f"exhaustion is BLOCK, never merge; got {p.returncode}, stdout={p.stdout!r}"
    )
    v = json.loads(p.stdout)
    assert v["verdict"] == "block", f"exhausted unsettled verdict must be block; got {v!r}"
    assert v["clause"] == "G4", f"exhausted unsettled clause must be G4; got {v!r}"


# ---------------------------------------------------------------------------
# Fixture 3 — {BLOCKED} → BLOCK / G4 / exit 3 + branch-protection trace, no --admin.
# ---------------------------------------------------------------------------
def test_blocked_is_block_branch_protection_never_admin():
    p = _run(_pr(mergeStateStatus="BLOCKED"))
    assert p.returncode == EXIT_BLOCK, (
        f"BLOCKED must BLOCK (exit 3); got {p.returncode}, stdout={p.stdout!r}"
    )
    v = json.loads(p.stdout)
    assert v["verdict"] == "block", f"BLOCKED verdict must be block; got {v!r}"
    assert v["clause"] == "G4", f"BLOCKED clause must be G4; got {v!r}"
    assert v["method"] is None, f"block carries method=null; got {v!r}"
    assert v["mergeStateStatus"] == "BLOCKED", f"must echo mergeStateStatus; got {v!r}"
    detail = v["detail"].lower()
    assert "protection" in detail, f"BLOCKED detail must name branch protection; got {v!r}"
    assert "--admin" not in v["detail"], f"detail must never carry --admin; got {v!r}"


# ---------------------------------------------------------------------------
# Fixture 4 — {CLEAN} → MERGE / clause null / method rebase / exit 0.
# ---------------------------------------------------------------------------
def test_clean_is_the_only_merge():
    p = _run(_pr())  # baseline is CLEAN/MERGEABLE/OPEN/non-draft/clean body
    assert p.returncode == EXIT_MERGE, (
        f"CLEAN+MERGEABLE+OPEN must MERGE (exit 0); got {p.returncode}, "
        f"stdout={p.stdout!r} stderr={p.stderr!r}"
    )
    v = json.loads(p.stdout)
    assert v["verdict"] == "merge", f"clean verdict must be merge; got {v!r}"
    assert v["clause"] is None, f"merge verdict carries clause=null; got {v!r}"
    assert v["method"] == "rebase", f"merge method must be rebase; got {v!r}"
    assert v["mergeStateStatus"] == "CLEAN", f"must echo mergeStateStatus; got {v!r}"


# ---------------------------------------------------------------------------
# Fixture 5/6 — unknown enum → fail-loud exit 2 + stderr, NO merge verdict.
# ---------------------------------------------------------------------------
def test_unknown_merge_state_status_fails_loud():
    p = _run(_pr(mergeStateStatus="FROBNICATE"))
    assert p.returncode == EXIT_MALFORMED, (
        f"an unknown mergeStateStatus enum must fail-loud (exit 2), never "
        f"silently pass; got {p.returncode}, stdout={p.stdout!r}"
    )
    assert p.stderr.strip(), "exit 2 must carry a stderr diagnostic (fail-loud)."
    assert "FROBNICATE" in p.stderr, (
        f"stderr must name the offending value; got {p.stderr!r}"
    )
    assert "merge" not in p.stdout, (
        f"an unknown enum must NOT emit a verdict on stdout; got {p.stdout!r}"
    )


def test_unknown_mergeable_fails_loud():
    p = _run(_pr(mergeable="WEIRD"))
    assert p.returncode == EXIT_MALFORMED, (
        f"an unknown mergeable enum must fail-loud (exit 2); got {p.returncode}, "
        f"stdout={p.stdout!r}"
    )
    assert p.stderr.strip(), "exit 2 must carry a stderr diagnostic."
    assert "WEIRD" in p.stderr, f"stderr must name the offending value; got {p.stderr!r}"
    assert "merge" not in p.stdout, (
        f"an unknown mergeable must NOT emit a verdict on stdout; got {p.stdout!r}"
    )


# ---------------------------------------------------------------------------
# Fixture 7 — {MERGED} re-entry → SKIP / G0-already-merged / exit 4 (never block).
# ---------------------------------------------------------------------------
def test_merged_reentry_skips_never_blocks():
    p = _run(_pr(state="MERGED"))
    assert p.returncode == EXIT_SKIP, (
        f"a MERGED re-entry must SKIP (exit 4), never block; got {p.returncode}, "
        f"stdout={p.stdout!r}"
    )
    v = json.loads(p.stdout)
    assert v["verdict"] == "skip", f"MERGED verdict must be skip; got {v!r}"
    assert v["clause"] == "G0-already-merged", f"clause must be G0-already-merged; got {v!r}"


# ---------------------------------------------------------------------------
# Fixture 8 — isDraft=true → BLOCK / G1 / exit 3.
# ---------------------------------------------------------------------------
def test_draft_is_block_g1():
    p = _run(_pr(isDraft=True))
    assert p.returncode == EXIT_BLOCK, (
        f"a draft PR must BLOCK (exit 3); got {p.returncode}, stdout={p.stdout!r}"
    )
    v = json.loads(p.stdout)
    assert v["verdict"] == "block", f"draft verdict must be block; got {v!r}"
    assert v["clause"] == "G1", f"draft clause must be G1; got {v!r}"


# ---------------------------------------------------------------------------
# Fixture 9 — head == base → SKIP / G0-head-equals-base / exit 4.
# ---------------------------------------------------------------------------
def test_head_equals_base_skips():
    p = _run(_pr(headRefName="main", baseRefName="main"))
    assert p.returncode == EXIT_SKIP, (
        f"head==base must SKIP (exit 4); got {p.returncode}, stdout={p.stdout!r}"
    )
    v = json.loads(p.stdout)
    assert v["verdict"] == "skip", f"head==base verdict must be skip; got {v!r}"
    assert v["clause"] == "G0-head-equals-base", f"clause must be G0-head-equals-base; got {v!r}"


# ---------------------------------------------------------------------------
# Fixture 10a/10b — G2 dual-source blocker → BLOCK / G2 / exit 3.
# ---------------------------------------------------------------------------
def test_g2_body_residual_blocker_is_block():
    body = "intro\n## Residual Review Findings\n- severity: blocker — fix the thing\n"
    p = _run(_pr(body=body))
    assert p.returncode == EXIT_BLOCK, (
        f"a body `severity: blocker` in `## Residual Review Findings` must BLOCK "
        f"(exit 3); got {p.returncode}, stdout={p.stdout!r}"
    )
    v = json.loads(p.stdout)
    assert v["verdict"] == "block", f"G2 body blocker verdict must be block; got {v!r}"
    assert v["clause"] == "G2", f"G2 body blocker clause must be G2; got {v!r}"


def test_g2_findings_file_blocker_is_block(tmp_path):
    findings = tmp_path / "feature-x.md"
    findings.write_text("- severity: blocker — found on disk\n", encoding="utf-8")
    # Clean body — the blocker lives ONLY in the fallback findings file.
    p = _run(_pr(body="clean body, no findings section"), "--findings-file", str(findings))
    assert p.returncode == EXIT_BLOCK, (
        f"a `severity: blocker` in a --findings-file must BLOCK even with a clean "
        f"body (closes the body-only false-PASS hole); got {p.returncode}, "
        f"stdout={p.stdout!r}"
    )
    v = json.loads(p.stdout)
    assert v["verdict"] == "block", f"G2 findings-file blocker verdict must be block; got {v!r}"
    assert v["clause"] == "G2", f"G2 findings-file blocker clause must be G2; got {v!r}"


def test_g2_missing_findings_file_is_noop(tmp_path):
    """A missing --findings-file is a no-op, not an error (the leader passes both
    branch-named and SHA-named candidates; usually only 0–1 exist)."""
    missing = tmp_path / "does-not-exist.md"
    p = _run(_pr(), "--findings-file", str(missing))
    assert p.returncode == EXIT_MERGE, (
        f"a missing --findings-file must be a no-op (clean PR still merges); got "
        f"{p.returncode}, stdout={p.stdout!r} stderr={p.stderr!r}"
    )


# ---------------------------------------------------------------------------
# Q1-1 (HIGH) — G2 fail-open closure. `/athanor:review` emits critical/high
# severities (never the literal `blocker`), so a blocker-token-only G2 fell
# OPEN on an unresolved CRITICAL residual and let it reach a MERGE verdict. The
# broadened token must BLOCK `severity: critical|high` markers (+ indented /
# numbered-bullet variants) on an OTHERWISE-CLEAN PR, while keeping the literal
# `severity: blocker` form green. Fail-safe: can only block more, never merge.
# ---------------------------------------------------------------------------
def test_g2_critical_high_severity_markers_block():
    variants = (
        # canonical critical marker on an otherwise-mergeable PR
        "intro\n## Residual Review Findings\n- severity: critical — SQLi in auth handler\n",
        # `high` is also merge-blocking vocabulary
        "intro\n## Residual Review Findings\n- severity: high — unsafe deserialize\n",
        # indented sub-bullet (column-0 miss in the old `^[-*]` token)
        "intro\n## Residual Review Findings\n  - severity: critical — indented finding\n",
        # numbered-bullet marker
        "intro\n## Residual Review Findings\n1. severity: critical — numbered finding\n",
        # the literal `blocker` form must STILL block (back-compat)
        "intro\n## Residual Review Findings\n* severity: blocker — keep literal token green\n",
    )
    for body in variants:
        p = _run(_pr(body=body))
        assert p.returncode == EXIT_BLOCK, (
            f"a `severity: critical|high|blocker` residual marker must BLOCK "
            f"(exit 3) on a clean PR; body={body!r} got {p.returncode}, "
            f"stdout={p.stdout!r}"
        )
        v = json.loads(p.stdout)
        assert v["verdict"] == "block", f"verdict must be block; body={body!r} got {v!r}"
        assert v["clause"] == "G2", f"clause must be G2; body={body!r} got {v!r}"


def test_g2_critical_in_findings_file_blocks(tmp_path):
    """The broadened token also fires via the --findings-file fallback source."""
    findings = tmp_path / "feature-x.md"
    findings.write_text(
        "## Residual Review Findings\n- severity: critical — found on disk\n",
        encoding="utf-8",
    )
    p = _run(_pr(body="clean body, no findings section"), "--findings-file", str(findings))
    assert p.returncode == EXIT_BLOCK, (
        f"a `severity: critical` in a --findings-file must BLOCK; got "
        f"{p.returncode}, stdout={p.stdout!r}"
    )
    v = json.loads(p.stdout)
    assert v["clause"] == "G2", f"clause must be G2; got {v!r}"


def test_g2_prose_severity_word_alone_does_not_false_block():
    """A residual that only MENTIONS 'critical'/'blocker' in prose (no
    `severity:` token line) must NOT false-FAIL — the clean PR still merges."""
    body = (
        "intro\n## Residual Review Findings\n"
        "- This is a critical-sounding but non-structured note about a blocker.\n"
    )
    p = _run(_pr(body=body))
    assert p.returncode == EXIT_MERGE, (
        f"prose mentioning 'critical'/'blocker' without a `severity:` marker line "
        f"must not block; got {p.returncode}, stdout={p.stdout!r}"
    )


# ---------------------------------------------------------------------------
# Q1-5 — a non-UTF-8 --findings-file must fail-loud (exit 2 EXIT_MALFORMED),
# never crash to an uncaught traceback / exit 1. UnicodeDecodeError is a
# ValueError (NOT an OSError) so it previously escaped the `except OSError`.
# ---------------------------------------------------------------------------
def test_non_utf8_findings_file_fails_loud(tmp_path):
    findings = tmp_path / "mojibake.md"
    findings.write_bytes(b"\xff\xfe- severity: blocker\n")
    p = _run(_pr(body="clean body"), "--findings-file", str(findings))
    assert p.returncode == EXIT_MALFORMED, (
        f"a non-UTF-8 findings file must fail-loud (exit 2 EXIT_MALFORMED), never "
        f"crash to exit 1; got {p.returncode}, stdout={p.stdout!r} stderr={p.stderr!r}"
    )
    assert p.stderr.strip(), "exit 2 must carry a stderr diagnostic (fail-loud)."
    assert "merge" not in p.stdout, (
        f"a malformed findings file must NOT emit a verdict on stdout; got {p.stdout!r}"
    )


# ---------------------------------------------------------------------------
# Fixture 11 — G3 unresolved-CI section → BLOCK / G3 / exit 3.
# ---------------------------------------------------------------------------
def test_g3_unresolved_ci_is_block():
    body = "summary\n## CI Failures Unresolved\n- pytest still red after 3 cycles\n"
    p = _run(_pr(body=body))
    assert p.returncode == EXIT_BLOCK, (
        f"a `## CI Failures Unresolved` header must BLOCK (exit 3); got "
        f"{p.returncode}, stdout={p.stdout!r}"
    )
    v = json.loads(p.stdout)
    assert v["verdict"] == "block", f"G3 verdict must be block; got {v!r}"
    assert v["clause"] == "G3", f"G3 clause must be G3; got {v!r}"


# ---------------------------------------------------------------------------
# Fixture 12 — malformed stdin → fail-loud exit 2 + stderr, no verdict.
# ---------------------------------------------------------------------------
def test_malformed_stdin_fails_loud():
    p = _run("{ this is not json ")
    assert p.returncode == EXIT_MALFORMED, (
        f"malformed stdin JSON must fail-loud (exit 2); got {p.returncode}, "
        f"stdout={p.stdout!r} stderr={p.stderr!r}"
    )
    assert p.stderr.strip(), "exit 2 must carry a stderr diagnostic (fail-loud)."
    assert "merge" not in p.stdout, (
        f"malformed input must NOT emit a verdict on stdout; got {p.stdout!r}"
    )


# ---------------------------------------------------------------------------
# G0 — a null/empty PR object → SKIP / G0-no-pr / exit 4.
# ---------------------------------------------------------------------------
def test_null_pr_skips_no_pr():
    p = _run("null")
    assert p.returncode == EXIT_SKIP, (
        f"a null PR object must SKIP (exit 4) clause G0-no-pr; got {p.returncode}, "
        f"stdout={p.stdout!r}"
    )
    v = json.loads(p.stdout)
    assert v["verdict"] == "skip", f"null PR verdict must be skip; got {v!r}"
    assert v["clause"] == "G0-no-pr", f"null PR clause must be G0-no-pr; got {v!r}"


# ---------------------------------------------------------------------------
# CONFLICTING vs mergeable==null — distinguished outputs (block G4 vs skip).
# ---------------------------------------------------------------------------
def test_conflicting_is_block_distinct_from_unsettled():
    p = _run(_pr(mergeable="CONFLICTING"))
    assert p.returncode == EXIT_BLOCK, (
        f"CONFLICTING must BLOCK (exit 3), distinct from the unsettled skip; got "
        f"{p.returncode}, stdout={p.stdout!r}"
    )
    v = json.loads(p.stdout)
    assert v["verdict"] == "block", f"CONFLICTING verdict must be block; got {v!r}"
    assert v["clause"] == "G4", f"CONFLICTING clause must be G4; got {v!r}"


# ---------------------------------------------------------------------------
# Source-grep — the gate is verdict-only: no subprocess/gh/git/net/admin token.
# ---------------------------------------------------------------------------
def test_source_has_no_banned_tokens():
    src = CLI.read_text(encoding="utf-8")
    for banned in (
        "subprocess",
        " gh ",
        "git ",
        "urllib",
        "requests",
        "socket",
        "--admin",
        "CHANGELOG",
        "mergeMethod",
    ):
        assert banned not in src, (
            f"the verdict-only gate source must not contain {banned!r} — it is "
            "structurally incapable of running a merge or bypassing protection."
        )
