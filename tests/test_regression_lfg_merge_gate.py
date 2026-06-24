"""Regression — /athanor:lfg Step 8.5 merge-readiness gate disposition LOGIC.

Contract under lock
-------------------
`/athanor:lfg` Step 8.5 adds an **opt-out (default-ON) merge** of a green PR
to its base branch, gated behind a **fail-loud conjunctive merge-readiness
gate**. Three properties make lfg identity-bearing here and are the reason a
*logic* lock (not just a vocabulary lock) is required:

1. **Opt-out, default-ON.** Merging a green PR to its base branch happens by
   default, but only after the conjunctive readiness gate passes — disabling it
   is a one-flag opt-out. The fail-safe *disable* direction wins ties:
   `--unmerge` (default ``true`` via `lfg.autoMerge`) hard-disables even when
   config enables it; `--merge` explicitly enables when config is ``false``.

2. **Conjunctive (AND) gate.** Merge proceeds **iff ALL** clauses G1–G5 hold
   (after a G0 entry/re-entry check). A static test that asserted only that the
   substrings exist would still pass if a future edit inverted "ALL must hold"
   into "ANY may hold" while keeping every word. So these tests assert the
   **disposition mapping** — each `mergeStateStatus` enum value co-occurs with
   its expected verdict (CLEAN→merge-OK, UNKNOWN→re-poll, the other six→block),
   the re-poll is keyed on the correct `mergeable` field, and the AND keyword is
   tied to the merge action — not merely that the tokens appear somewhere.

3. **Exhaustive disposition + honest boundaries.** All 8 GitHub `mergeStateStatus`
   enum values get an explicit verdict (whitelisting only CLEAN silently
   mishandled UNSTABLE/HAS_HOOKS); the re-entry `already-merged` state reports
   merged (never `blocked-by-gate`) after a mid-merge crash; the merge never
   `--admin`-bypasses branch protection; and lfg-merge merges only — it never
   version-bumps/tags/edits CHANGELOG (that stays the `athanor-releaser`
   ceremony). The gate is honestly labeled **advisory** (leader-prose-enforced),
   NOT enforced — no runtime hook blocks the merge.

These checks are **static reads only** (`skills/lfg/SKILL.md`, `athanor.json`,
`templates/athanor.json`, `schemas/athanor-config.schema.json`, `CLAUDE.md`,
each read with ``encoding="utf-8"``). No subprocess, no `gh`, no network, no
file writes — the same shape as ``test_regression_lfg_pr_body_persistence.py``.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LFG = REPO_ROOT / "skills" / "lfg" / "SKILL.md"
ATHANOR_JSON = REPO_ROOT / "athanor.json"
TEMPLATE_JSON = REPO_ROOT / "templates" / "athanor.json"
SCHEMA_JSON = REPO_ROOT / "schemas" / "athanor-config.schema.json"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"


# ---------------------------------------------------------------------------
# Helpers — section slicing so assertions are scoped to the gate prose, not
# the whole document (a co-occurrence in an unrelated section must not satisfy
# a clause-specific assertion).
# ---------------------------------------------------------------------------
def _lfg_text() -> str:
    return LFG.read_text(encoding="utf-8")


def _step_8_5_block(text: str | None = None) -> str:
    """Return the Step 8.5 section body (from `### Step 8.5` to `### Step 9`)."""
    text = text if text is not None else _lfg_text()
    start = text.find("### Step 8.5")
    assert start != -1, "skills/lfg/SKILL.md must contain a '### Step 8.5' section."
    end = text.find("### Step 9", start)
    return text[start : end if end != -1 else len(text)]


def _step_9_block(text: str | None = None) -> str:
    """Return the Step 9 section body (from `### Step 9` to the next H2/EOF)."""
    text = text if text is not None else _lfg_text()
    start = text.find("### Step 9")
    assert start != -1, "skills/lfg/SKILL.md must contain a '### Step 9' section."
    end = text.find("\n## ", start)
    return text[start : end if end != -1 else len(text)]


def _row_for(block: str, value: str) -> str:
    """Return the single markdown table row whose first cell names ``value``.

    Used to prove a disposition VALUE co-occurs with its VERDICT *in the same
    table row* (proximity), not merely that both words appear in the document.
    """
    pat = re.compile(r"^\|\s*`?" + re.escape(value) + r"`?\s*\|.*$", re.MULTILINE)
    m = pat.search(block)
    return m.group(0) if m else ""


# ---------------------------------------------------------------------------
# 1. Step 8.5 placement — BETWEEN Step 8 and Step 9 (ordering, not presence).
# ---------------------------------------------------------------------------
def test_step_8_5_between_8_and_9() -> None:
    text = _lfg_text()
    off_8 = text.find("### Step 8\n")
    if off_8 == -1:
        off_8 = text.find("### Step 8 ")
    off_85 = text.find("### Step 8.5")
    off_9 = text.find("### Step 9")
    assert off_8 != -1, "skills/lfg/SKILL.md must retain '### Step 8'."
    assert off_85 != -1, "skills/lfg/SKILL.md must add '### Step 8.5'."
    assert off_9 != -1, "skills/lfg/SKILL.md must retain '### Step 9'."
    assert off_8 < off_85 < off_9, (
        "Step 8.5 must sit BETWEEN Step 8 (CI green) and Step 9 (DONE sentinel): "
        f"offsets Step8={off_8}, Step8.5={off_85}, Step9={off_9}."
    )


# ---------------------------------------------------------------------------
# 2. All 8 mergeStateStatus tokens present AND mapped to the right verdict.
#    Asserted via table-row co-occurrence, not document-wide presence.
# ---------------------------------------------------------------------------
def test_merge_state_status_all_eight_present() -> None:
    block = _step_8_5_block()
    for tok in ("CLEAN", "UNKNOWN", "BEHIND", "BLOCKED", "DIRTY", "DRAFT", "HAS_HOOKS", "UNSTABLE"):
        assert tok in block, (
            f"Step 8.5 must enumerate the mergeStateStatus value {tok!r} "
            "(exhaustive 8-value disposition table)."
        )


def test_clean_is_the_only_merge_ok_state() -> None:
    block = _step_8_5_block()
    clean_row = _row_for(block, "CLEAN")
    assert clean_row, "Step 8.5 must have a `CLEAN` disposition table row."
    assert re.search(r"merge-?ok", clean_row, re.IGNORECASE), (
        "The `CLEAN` row must tie CLEAN to a MERGE-OK verdict in the same row; "
        f"got: {clean_row!r}"
    )
    # CLEAN is the ONLY merge-ok state — no blocked state may carry merge-ok.
    for blocked in ("BEHIND", "BLOCKED", "DIRTY", "DRAFT", "HAS_HOOKS", "UNSTABLE"):
        row = _row_for(block, blocked)
        assert row, f"Step 8.5 must have a `{blocked}` disposition row."
        assert not re.search(r"merge-?ok", row, re.IGNORECASE), (
            f"The `{blocked}` row must NOT be tagged MERGE-OK — only CLEAN merges. "
            f"got: {row!r}"
        )


def test_blocking_states_tied_to_block_verdict() -> None:
    block = _step_8_5_block()
    # Each of these six must co-occur with a BLOCK verdict in its own table row.
    for blocked in ("UNSTABLE", "HAS_HOOKS", "BLOCKED", "DIRTY", "DRAFT", "BEHIND"):
        row = _row_for(block, blocked)
        assert row, f"Step 8.5 must have a `{blocked}` disposition row."
        assert re.search(r"\bBLOCK\b", row), (
            f"The `{blocked}` row must tie {blocked} to a BLOCK verdict in the "
            f"same row (not just mention BLOCK elsewhere); got: {row!r}"
        )


def test_unknown_tied_to_re_poll() -> None:
    block = _step_8_5_block()
    row = _row_for(block, "UNKNOWN")
    assert row, "Step 8.5 must have an `UNKNOWN` mergeStateStatus disposition row."
    assert re.search(r"re-?poll", row, re.IGNORECASE), (
        "The mergeStateStatus `UNKNOWN` row must tie UNKNOWN to RE-POLL in the "
        f"same row; got: {row!r}"
    )


# ---------------------------------------------------------------------------
# 3. Re-poll keyed on `mergeable` UNKNOWN/null + 3 and 5 budget; exhaustion → block.
# ---------------------------------------------------------------------------
def test_re_poll_keyed_on_mergeable_field_with_budget() -> None:
    block = _step_8_5_block()
    # Locate the re-poll paragraph and assert the predicate is on `mergeable`
    # (NOT only mergeStateStatus) — a freshly-pushed PR reports mergeable: null.
    assert "re-poll" in block.lower(), "Step 8.5 must document a bounded re-poll."
    assert "mergeable" in block, "Re-poll predicate must reference the `mergeable` field."
    # mergeable ∈ {UNKNOWN, null}: both the UNKNOWN and null sentinels named.
    assert re.search(r"mergeable[^.\n]{0,80}null", block) or re.search(
        r"null[^.\n]{0,80}mergeable", block
    ), "Re-poll must key on `mergeable` == null (async post-push transient)."
    assert "UNKNOWN" in block and "null" in block, (
        "Re-poll predicate must name BOTH UNKNOWN and null for `mergeable`."
    )
    # Bounded budget: 3 attempts × ~5s.
    assert "3" in block and "5" in block, "Re-poll budget must show 3 (attempts) and 5 (seconds)."
    assert re.search(r"3\s*[x×]\s*~?\s*5", block) or re.search(
        r"3 attempts[^.\n]{0,40}5", block
    ), "Re-poll budget must express the bounded 3 × ~5s shape."


def test_re_poll_exhaustion_blocks_never_merges() -> None:
    block = _step_8_5_block().lower()
    # Exhaustion is BLOCK, never merge — the load-bearing safety direction.
    assert "exhaustion" in block, "Re-poll must define exhaustion behavior."
    assert re.search(r"exhaustion is block", block) or re.search(
        r"exhaustion[^.\n]{0,80}(block|never merge)", block
    ), "Re-poll exhaustion must resolve to BLOCK (never merge on unsettled state)."
    assert "never merge" in block, (
        "Re-poll exhaustion must explicitly state it never merges on an "
        "unsettled mergeability."
    )


# ---------------------------------------------------------------------------
# 4. AND-semantics keyword tied to the merge action.
# ---------------------------------------------------------------------------
def test_and_semantics_keyword_tied_to_merge() -> None:
    block = _step_8_5_block()
    # The conjunction word must sit next to the merge action — "iff ALL"/"iff every".
    has_iff_all = re.search(r"\biff\b[^.\n]{0,40}\bALL\b", block) is not None
    has_iff_every = re.search(r"\biff\b[^.\n]{0,40}\bevery\b", block, re.IGNORECASE) is not None
    assert has_iff_all or has_iff_every, (
        "Step 8.5 must tie the AND keyword (ALL / every / iff) to the merge "
        "action, e.g. 'merge proceeds iff ALL clauses ... hold' — locking the "
        "conjunction so an ALL→ANY inversion fails this test."
    )
    # And the merge action must appear in proximity to the conjunction keyword.
    assert re.search(r"merge[^.\n]{0,60}\b(iff|ALL|every)\b", block) or re.search(
        r"\b(iff|ALL|every)\b[^.\n]{0,60}merge", block
    ), "The AND keyword must be adjacent to the merge action, not free-floating."


# ---------------------------------------------------------------------------
# 5. Dual-source G2: PR body section AND fallback path; `severity: blocker` key.
# ---------------------------------------------------------------------------
def test_g2_dual_source_blocker_check() -> None:
    block = _step_8_5_block()
    assert "## Residual Review Findings" in block, (
        "G2 must name the PR-body `## Residual Review Findings` section as one "
        "blocker source."
    )
    assert "docs/residual-review-findings" in block, (
        "G2 must name the fallback path `docs/residual-review-findings/...` as "
        "the second blocker source (the body-only check false-PASSes on-disk "
        "blockers)."
    )
    assert re.search(r"severity:\s*blocker", block, re.IGNORECASE), (
        "G2 must key on the structured `severity: blocker` machine token, not "
        "freeform prose mentioning 'blocker'."
    )


# ---------------------------------------------------------------------------
# 6. Merge-queue detected and respected.
# ---------------------------------------------------------------------------
def test_merge_queue_detected_and_respected() -> None:
    block = _step_8_5_block()
    assert re.search(r"merge queue", block, re.IGNORECASE), (
        "G5 must reference a GitHub 'merge queue'."
    )
    assert "blocked-merge-queue" in block, (
        "G5 must classify a queue-required merge as the `blocked-merge-queue` "
        "result state (do not fight the queue)."
    )


# ---------------------------------------------------------------------------
# 7. Step 9 `merge:` result line carries ALL 8 states.
# ---------------------------------------------------------------------------
def test_result_packet_has_all_eight_merge_states() -> None:
    block = _step_9_block()
    assert "merge:" in block, "Step 9 result packet must emit a `merge:` outcome line."
    for state in (
        "merged",
        "already-merged",
        "blocked-by-gate",
        "blocked-merge-queue",
        "skipped-merge-disabled",
        "skipped-no-pr",
        "skipped-pr-closed",
        "skipped-head-equals-base",
    ):
        assert state in block, (
            f"Step 9 result packet must list the `merge:` state {state!r} "
            "(exhaustive 8-state disposition vocabulary)."
        )


# ---------------------------------------------------------------------------
# 8. already-merged / state == MERGED re-entry → merged, NEVER blocked-by-gate.
# ---------------------------------------------------------------------------
def test_already_merged_reentry_never_blocked() -> None:
    block = _step_8_5_block()
    # The re-entry clause must name MERGED state and the already-merged result.
    assert "MERGED" in block, "G0 re-entry must check `state == MERGED`."
    assert "already-merged" in block, (
        "G0 re-entry on a merged PR must report `merge: already-merged`."
    )
    # And it must be tied to a 'never blocked-by-gate'-class statement nearby.
    merged_idx = block.find('"MERGED"')
    if merged_idx == -1:
        merged_idx = block.find("MERGED")
    window = block[merged_idx : merged_idx + 400]
    assert re.search(r"never[^.\n]{0,60}blocked-by-gate", window, re.IGNORECASE), (
        "The re-entry MERGED branch must explicitly state it reports merged and "
        "NEVER `blocked-by-gate` (honest report after a mid-merge crash); "
        f"window did not contain that statement: {window!r}"
    )


# ---------------------------------------------------------------------------
# 9. --rebase present; --admin ABSENT from the merge command + never-admin rule.
# ---------------------------------------------------------------------------
def test_merge_command_rebase_no_admin() -> None:
    block = _step_8_5_block()
    # Find the ACTUAL merge command line — the executable `gh pr merge` that
    # carries flags (the prose mentions like "`gh pr merge` exits non-zero" in
    # G5 have no flags and are not the command). Scan all `gh pr merge ...`
    # occurrences for the one with --rebase.
    candidates = re.findall(r"gh pr merge[^\n]*", block)
    assert candidates, "Step 8.5 must contain a `gh pr merge ...` command line."
    merge_cmds = [c for c in candidates if "--rebase" in c]
    assert merge_cmds, (
        "The executable merge command must use --rebase (repo convention); "
        f"found only: {candidates!r}"
    )
    merge_cmd = merge_cmds[0]
    # The actual merge command line MUST NOT carry --admin (no protection bypass).
    assert "--admin" not in merge_cmd, (
        f"The merge command line MUST NOT contain --admin (no protection "
        f"bypass); got: {merge_cmd!r}"
    )
    # No `gh pr merge` invocation anywhere in Step 8.5 may carry --admin.
    for c in candidates:
        assert "--admin" not in c, (
            f"No `gh pr merge` invocation may use --admin; offending: {c!r}"
        )


def test_never_admin_prohibition_present() -> None:
    block = _step_8_5_block()
    # A MUST NOT / never + admin prohibition must be stated in prose.
    assert re.search(r"(MUST NOT|never|no)[^.\n]{0,60}--?admin", block, re.IGNORECASE) or (
        re.search(r"--?admin", block) and re.search(r"\bnever\b", block, re.IGNORECASE)
    ), (
        "Step 8.5 must carry an explicit prohibition tying `never`/`MUST NOT` to "
        "`--admin` (no branch-protection bypass)."
    )


# ---------------------------------------------------------------------------
# 10. isDraft block clause; head == base skip clause.
# ---------------------------------------------------------------------------
def test_is_draft_block_clause() -> None:
    block = _step_8_5_block()
    assert "isDraft" in block, "G1 must name `isDraft` as the primary draft block signal."
    assert re.search(r"isDraft[^.\n]{0,80}(FAIL|draft)", block) or "isDraft == false" in block, (
        "G1 must use `isDraft` as a block clause (isDraft == false to pass)."
    )


def test_head_equals_base_skip_clause() -> None:
    block = _step_8_5_block()
    has_refnames = "headRefName" in block and "baseRefName" in block
    has_prose = re.search(r"head\s*==\s*base", block) is not None
    assert has_refnames or has_prose, (
        "G0 must name the head==base skip clause via `headRefName`/`baseRefName` "
        "equality or 'head == base'."
    )
    assert "skipped-head-equals-base" in block, (
        "G0 head==base must resolve to `merge: skipped-head-equals-base`."
    )


# ---------------------------------------------------------------------------
# 11. Opt-out default-ON: --merge/--unmerge + lfg.autoMerge + literal default-on.
# ---------------------------------------------------------------------------
def test_opt_out_default_on_statement() -> None:
    block = _step_8_5_block()
    assert "--merge" in block, (
        "Step 8.5 must document the `--merge` explicit-enable flag (kept as the "
        "symmetric counterpart of `--unmerge`)."
    )
    assert "--unmerge" in block, (
        "Step 8.5 must document `--unmerge` (the hard-disable / fail-safe opt-out "
        "flag that replaced `--no-merge`)."
    )
    assert "--no-merge" not in block, (
        "Step 8.5 must NOT retain the old `--no-merge` flag — it was renamed to "
        "`--unmerge` for the opt-out (default-on) design."
    )
    assert "lfg.autoMerge" in block, (
        "Step 8.5 must document the `lfg.autoMerge` config knob."
    )
    lowered = block.lower()
    assert (
        "default `true`" in lowered
        or "default true" in lowered
        or re.search(r"default[^.\n]{0,20}true", lowered)
        or "on by default" in lowered
        or "opt-out" in lowered
    ), (
        "Step 8.5 must carry a literal default-ON statement (e.g. 'default "
        "`true`', 'ON by default', or 'opt-out')."
    )


# ---------------------------------------------------------------------------
# 12. Stale-CI honest caveat present.
# ---------------------------------------------------------------------------
def test_stale_ci_caveat_present() -> None:
    block = _step_8_5_block().lower()
    has_up_to_date = "require" in block and "up-to-date" in block.replace(" ", "-") or (
        "require" in block and "up to date" in block
    )
    has_stale_base = "stale" in block and "base" in block
    assert has_up_to_date or has_stale_base, (
        "Step 8.5 must surface the stale-CI residual honestly — either "
        "'require ... up to date' or 'stale ... base' phrasing."
    )


# ---------------------------------------------------------------------------
# 13. Post-merge boundary names the releaser and the version/tag/CHANGELOG scope-out.
# ---------------------------------------------------------------------------
def test_post_merge_boundary_vs_releaser() -> None:
    block = _step_8_5_block()
    assert "releaser" in block.lower(), (
        "Step 8.5 must name the `athanor-releaser` as the owner of the release "
        "ceremony (post-merge boundary)."
    )
    # A 'does not / never' + version/tag/CHANGELOG scope-out must be present.
    assert re.search(
        r"(does\s+\*?\*?not\*?\*?|never)[^.\n]{0,120}(version|tag|CHANGELOG)",
        block,
        re.IGNORECASE,
    ), (
        "Step 8.5 must state lfg-merge does NOT / never version-bump/tag/edit "
        "CHANGELOG — that stays the releaser ceremony."
    )


# ---------------------------------------------------------------------------
# 14. Config: athanor.json AND template default-ON; schema knob is boolean.
# ---------------------------------------------------------------------------
def test_athanor_json_auto_merge_default_true() -> None:
    config = json.loads(ATHANOR_JSON.read_text(encoding="utf-8"))
    assert "lfg" in config, "athanor.json must declare an `lfg` block."
    assert config["lfg"].get("autoMerge") is True, (
        "athanor.json `lfg.autoMerge` must be the boolean True by default "
        "(the load-bearing default-ON value; opt-out via `--unmerge`)."
    )


def test_template_athanor_json_auto_merge_default_true() -> None:
    config = json.loads(TEMPLATE_JSON.read_text(encoding="utf-8"))
    assert "lfg" in config, "templates/athanor.json must declare an `lfg` block."
    assert config["lfg"].get("autoMerge") is True, (
        "templates/athanor.json `lfg.autoMerge` must be the boolean True by "
        "default (shipped scaffold mirrors the default-ON value)."
    )


def test_schema_auto_merge_is_boolean() -> None:
    schema = json.loads(SCHEMA_JSON.read_text(encoding="utf-8"))
    lfg_props = (
        schema.get("properties", {})
        .get("lfg", {})
        .get("properties", {})
    )
    auto_merge = lfg_props.get("autoMerge")
    assert isinstance(auto_merge, dict), (
        "schema must define properties.lfg.properties.autoMerge (documentary knob)."
    )
    assert auto_merge.get("type") == "boolean", (
        "schema properties.lfg.properties.autoMerge.type must be 'boolean'; "
        f"got {auto_merge.get('type')!r}."
    )


# ---------------------------------------------------------------------------
# 15. CLAUDE.md: Core Principle lfg exception bullet + advisory Defense row.
# ---------------------------------------------------------------------------
def _claude_lfg_exception_bullet(text: str) -> str:
    """Return the §Core Principle lfg git/gh plumbing exception bullet."""
    for line in text.splitlines():
        if line.lstrip().startswith("-") and "/athanor:lfg" in line and "plumbing" in line:
            return line
    # Fallback: the bullet that names commit/push/PR plumbing under lfg.
    for line in text.splitlines():
        if line.lstrip().startswith("-") and "lfg" in line.lower() and "git/gh" in line:
            return line
    return ""


def test_claude_core_principle_merge_exception_bullet() -> None:
    text = CLAUDE_MD.read_text(encoding="utf-8")
    bullet = _claude_lfg_exception_bullet(text)
    assert bullet, (
        "CLAUDE.md §Core Principle must retain an lfg git/gh plumbing exception "
        "bullet."
    )
    assert "merge" in bullet.lower(), (
        "The lfg exception bullet must add a `merge` token (opt-in merge is now "
        "inside the documented plumbing exception)."
    )
    # The scope-out must be INLINE in the same bullet: never + version/tag/changelog.
    assert re.search(r"never", bullet, re.IGNORECASE), (
        "The lfg exception bullet must carry an inline `never` scope-out."
    )
    assert re.search(r"version|tag|changelog", bullet, re.IGNORECASE), (
        "The lfg exception bullet must scope OUT version-bump/tag/CHANGELOG "
        "inline (so a reader cannot infer tagging is permitted)."
    )


def test_claude_defense_row_lfg_merge_advisory_not_enforced() -> None:
    text = CLAUDE_MD.read_text(encoding="utf-8")
    # Find the lfg merge-readiness gate Defense Mechanisms row specifically.
    row = ""
    for line in text.splitlines():
        if line.lstrip().startswith("|") and re.search(
            r"lfg merge-readiness gate", line, re.IGNORECASE
        ):
            row = line
            break
    assert row, (
        "CLAUDE.md §Defense Mechanisms must add a distinct row for the "
        "'lfg merge-readiness gate'."
    )
    # The advisory label must belong to THIS row (proximity to the lfg-merge
    # marker), not be borrowed from the enforced Stop-hook row.
    assert re.search(r"advisory", row, re.IGNORECASE), (
        "The lfg merge-readiness gate row must be labeled `advisory` in its own "
        "row text."
    )
    assert "lfg merge-readiness gate" in row.lower(), (
        "The advisory label must be tied to the lfg-merge gate marker."
    )
    # It must NOT claim the gate is enforced (the word 'enforced' may appear only
    # when negated, e.g. 'NOT enforced' / 'no ... runtime hook'). Assert there is
    # no bare positive 'enforced (' claim for this gate.
    assert "**enforced" not in row.lower(), (
        "The lfg merge-readiness gate row MUST NOT claim it is **enforced** — it "
        "is advisory (leader-prose-enforced); a runtime hook does not block the "
        "merge."
    )
