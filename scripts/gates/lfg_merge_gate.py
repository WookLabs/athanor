#!/usr/bin/env python3
"""Merge-readiness verdict gate for /athanor:lfg Step 8.5 (G0–G4 disposition).

Lifts the safety-critical merge disposition of `/athanor:lfg` Step 8.5 out of
hand-interpreted leader bash into a single executable, fail-loud, regression-
tested **pure verdict function**. It consumes one ``gh pr view --json …`` snapshot
on stdin (+ named ``--findings-file`` paths) and emits a machine verdict
(``merge | block | skip``) with the deciding clause, via an explicit exit-code
map (0=merge, 2=malformed, 3=block, 4=skip). The script is **verdict-only**: it
structurally cannot run a merge, so it cannot add an admin-bypass flag or skip
branch protection — the merge command itself stays in leader prose.

Honesty label: ADVISORY — leader-prose-bound. A real exit code now exists (a
strict upgrade over hand-interpreted bash comments), but NO PreToolUse/Stop
runtime hook forces the leader to honor the verdict — the same enforcement class
as ``scripts/loops/lfg_fix_round_counter.py``.

The one genuinely-new safety property over today's prose: an unknown
``mergeStateStatus``/``mergeable`` enum **raises (exit 2) instead of silently
passing** — never an ``else: merge`` / ``.get(default)`` fallback.

Division of labor: the script judges G0 (entry/re-entry), G1 (draft), G2 (review
blocker, from the PR ``body`` + named ``--findings-file`` paths), G3 (unresolved-
CI header in ``body``), and G4 (GitHub merge-state disposition). G5 (merge queue)
stays leader-owned — it is a merge-time outcome read from ``gh pr merge`` stderr,
not derivable from a ``gh pr view`` snapshot. A ``merge`` verdict means "G0–G4
pass, safe to *attempt* the merge".
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
MERGE_METHOD = "rebase"  # a configurable merge method is out of scope for v1

EXIT_MERGE = 0
EXIT_MALFORMED = 2
EXIT_BLOCK = 3
EXIT_SKIP = 4

# Structured machine token for a review merge-blocker (NOT freeform prose).
_BLOCKER_RE = re.compile(r"(?im)^[-*] *severity: *blocker")
_RESIDUAL_HEADER = "## Residual Review Findings"
_UNRESOLVED_CI_HEADER = "## CI Failures Unresolved"

# Frozen disposition data — dicts, not branches; a value absent from a dict
# (and not the separately-handled JSON null) raises → exit 2 (the fail-loud crux).
MERGEABLE_DISPOSITION = {        # 3 recognized inputs (None handled separately)
    "MERGEABLE": "continue",     # fall through to the mergeStateStatus table
    "CONFLICTING": "block",      # clause G4
    "UNKNOWN": "unsettled",      # re-poll (skip) unless --repoll-exhausted
}
MERGE_STATE_DISPOSITION = {      # EXACTLY 8 keys = the GitHub enum (fail-loud crux)
    "CLEAN": "merge-ok",
    "UNKNOWN": "unsettled",      # re-poll (skip) unless --repoll-exhausted
    "BEHIND": "block",
    "BLOCKED": "block",          # branch protection — never an admin bypass
    "DIRTY": "block",
    "DRAFT": "block",            # G1 isDraft is primary; this is the backstop
    "HAS_HOOKS": "block",
    "UNSTABLE": "block",         # C1: settled, NOT mergeable in v1
}


class MergeGateError(ValueError):
    """Raised when the gate input is malformed or carries an unknown enum."""


def _stderr(msg: str) -> None:
    print(f"lfg merge gate: {msg}", file=sys.stderr)


def _verdict(
    verdict: str,
    clause: str | None,
    detail: str,
    merge_state: str | None = None,
    mergeable: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "verdict": verdict,
        "clause": clause,
        "method": MERGE_METHOD if verdict == "merge" else None,
        "mergeStateStatus": merge_state,
        "mergeable": mergeable,
        "detail": detail,
    }


def decide(pr: dict | None, findings_blocker: bool, repoll_exhausted: bool) -> dict[str, Any]:
    """Pure verdict function — ordered G0→G1→G2→G3→G4 conjunction, fail-fast.

    Raises MergeGateError on an unknown mergeStateStatus/mergeable enum (the
    caller maps it to exit 2). Never an ``else``/``.get(default)`` that yields a
    verdict.
    """
    # G0 — entry / re-entry.
    if not pr:
        return _verdict("skip", "G0-no-pr", "no PR object — nothing to merge")
    state = pr.get("state")
    if state == "MERGED":
        return _verdict(
            "skip", "G0-already-merged", "PR already merged — never blocked-by-gate"
        )
    if state == "CLOSED":
        return _verdict("skip", "G0-pr-closed", "PR is closed un-merged — skip")
    if pr.get("headRefName") is not None and pr.get("headRefName") == pr.get("baseRefName"):
        return _verdict(
            "skip", "G0-head-equals-base", "head == base — nothing to merge, skip"
        )

    # G1 — draft (isDraft is the authoritative primary signal).
    if pr.get("isDraft") is True:
        return _verdict("block", "G1", "PR is a draft")

    # G2 — review merge-blocker (dual-source: PR body section OR --findings-file).
    body = pr.get("body") or ""
    body_blocker = bool(_BLOCKER_RE.search(_residual_section(body)))
    if body_blocker or findings_blocker:
        return _verdict(
            "block", "G2", "review merge-blocker present (severity: blocker)"
        )

    # G3 — unresolved-CI section in the PR body.
    if _UNRESOLVED_CI_HEADER in body:
        return _verdict("block", "G3", "PR body has an unresolved-CI section")

    # G4 — GitHub merge-state disposition (the crux).
    mergeable = pr.get("mergeable")
    merge_state = pr.get("mergeStateStatus")

    # mergeable: JSON null → unsettled; else exhaustive lookup (unknown → raise).
    if mergeable is None:
        mergeable_disp = "unsettled"
    else:
        if mergeable not in MERGEABLE_DISPOSITION:
            raise MergeGateError(f"unknown mergeable enum: {mergeable!r}")
        mergeable_disp = MERGEABLE_DISPOSITION[mergeable]

    if mergeable_disp == "block":
        return _verdict(
            "block", "G4", "conflicts with base", merge_state, mergeable
        )

    # mergeStateStatus: exhaustive lookup (unknown → raise). Looked up even when
    # mergeable is unsettled so an unknown enum still fails loud.
    if merge_state not in MERGE_STATE_DISPOSITION:
        raise MergeGateError(f"unknown mergeStateStatus enum: {merge_state!r}")
    state_disp = MERGE_STATE_DISPOSITION[merge_state]

    if state_disp == "block":
        if merge_state == "BLOCKED":
            detail = (
                "merge blocked by branch protection / required reviews — human "
                "approval required; merge manually (never bypass protection)"
            )
        else:
            detail = f"mergeStateStatus={merge_state} is not mergeable in v1"
        return _verdict("block", "G4", detail, merge_state, mergeable)

    # Unsettled branch: mergeable ∈ {UNKNOWN, null} OR mergeStateStatus == UNKNOWN.
    if mergeable_disp == "unsettled" or state_disp == "unsettled":
        if repoll_exhausted:
            return _verdict(
                "block",
                "G4",
                "GitHub mergeability did not settle after 3×5s — do not merge; re-run later",
                merge_state,
                mergeable,
            )
        return _verdict(
            "skip",
            "G4-unsettled",
            "GitHub mergeability not settled — leader re-polls",
            merge_state,
            mergeable,
        )

    # All clauses pass — CLEAN + MERGEABLE.
    return _verdict("merge", None, "all clauses pass — safe to attempt merge", merge_state, mergeable)


def _residual_section(body: str) -> str:
    """Return the ``## Residual Review Findings`` section body, or '' if absent.

    Scoping the body blocker check to the section avoids false-FAILing on an
    unrelated `severity: blocker` line elsewhere in the body.
    """
    idx = body.find(_RESIDUAL_HEADER)
    if idx == -1:
        return ""
    rest = body[idx + len(_RESIDUAL_HEADER):]
    nxt = rest.find("\n## ")
    return rest if nxt == -1 else rest[:nxt]


def _read_findings_blocker(paths: list[str]) -> bool:
    """True iff any present --findings-file contains a `severity: blocker` line.

    A missing file is a no-op (the leader passes both branch-named and SHA-named
    candidates; usually only 0–1 exist). A present-but-unreadable file → raise
    (fail-loud).
    """
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise MergeGateError(f"could not read findings file: {path}") from exc
        if _BLOCKER_RE.search(content):
            return True
    return False


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="/athanor:lfg Step 8.5 merge-readiness verdict gate (advisory)."
    )
    parser.add_argument(
        "--findings-file",
        action="append",
        default=[],
        metavar="PATH",
        help="Repeatable G2 fallback file; missing file = no-op.",
    )
    parser.add_argument(
        "--repoll-exhausted",
        action="store_true",
        help="Convert a G4-unsettled skip into a block (exhaustion is BLOCK, never merge).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    raw = sys.stdin.read()
    try:
        pr = json.loads(raw)
    except json.JSONDecodeError as exc:
        _stderr(f"malformed stdin JSON: {exc.msg}")
        return EXIT_MALFORMED
    if pr is not None and not isinstance(pr, dict):
        _stderr("stdin must be a JSON object (the PR view snapshot) or null")
        return EXIT_MALFORMED

    try:
        findings_blocker = _read_findings_blocker(args.findings_file)
        result = decide(pr, findings_blocker, args.repoll_exhausted)
    except MergeGateError as exc:
        _stderr(str(exc))
        return EXIT_MALFORMED

    print(json.dumps(result, ensure_ascii=True))
    return {"merge": EXIT_MERGE, "block": EXIT_BLOCK, "skip": EXIT_SKIP}[result["verdict"]]


if __name__ == "__main__":
    raise SystemExit(main())
