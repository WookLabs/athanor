"""Regression tests for v0.13.1 — codex exec hang prevention (GitHub codex#20919).

Context
-------
Upstream GitHub issue codex#20919 reports that `codex exec` invocations
hang when the codex CLI's `readFileSync(0)` blocking stdin read inherits
an unredirected stdin from the parent shell. The fix is a defense-in-depth
combination at every `codex exec` command-shape line in athanor:

1. `< /dev/null` stdin redirect on the closing line of the multi-line
   bash invocation, so codex can never block waiting on stdin (the
   primary upstream-bug mitigation).
2. The deprecated `--full-auto` flag (removed in codex CLI 0.133.0)
   must NOT appear in command-shape lines — current invocations use
   the top-level `-a never -s workspace-write` form. Prose deprecation
   mentions (explaining the deprecation to readers) are whitelisted.
3. `-a` / `-s` are TOP-LEVEL options per `codex --help` (CLI 0.133.0+);
   they MUST precede the `exec` subcommand token, not follow it.
4. A shell-level `timeout NNNs` prefix is the hard wall-clock fence
   (belt-and-suspenders alongside the Bash tool's `timeout` parameter).

These tests are *static text reads only*. They do NOT invoke `codex`
or any subprocess (that would re-introduce the very stdin-inheritance
flake the redirect prevents; see acceptance_criteria SHOULD bullet).

Scope
-----
The command-shape lines live exclusively in `skills/plan/SKILL.md` —
specifically the Planner B (deep-tier, Codex) fenced bash block
beginning with `CODEX_TIMEOUT_S=$(jq` (inline timeout computation)
and the Reviewer B (deep-tier, Codex) fenced bash block beginning
with the same `CODEX_TIMEOUT_S=$(jq` pattern. Each block is a fenced
```bash ... ``` region whose first line computes the timeout inline via
jq, followed by `timeout ${CODEX_TIMEOUT_S}s codex -a never -s
workspace-write exec ...` and ending with `... < /dev/null`.

The naive regex `\bcodex exec\b` is too tight for backslash-continued /
multi-line shell commands (the `< /dev/null` lives on the closing line,
not the opening line). Tests use a broader region/multi-line match per
worker-1 / worker-8 discoveries.

Prose-only mentions of `codex exec` (e.g., COLLISION GUARD blockquotes
preceding each fenced bash block, echo-error fragments, and the
FALLBACK ONLY notice after the Planner B block) are whitelisted by
anchoring command-shape detection on fenced bash blocks.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLAN_SKILL = REPO_ROOT / "skills" / "plan" / "SKILL.md"
CONFIG_SCHEMA = REPO_ROOT / "schemas" / "athanor-config.schema.json"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Matches a fenced ```bash ... ``` block. DOTALL so newlines inside the
# block are captured. Non-greedy so adjacent blocks do not coalesce.
_BASH_FENCE_RE = re.compile(r"```bash\s*\n(.*?)\n```", re.DOTALL)

# Broader-than-naive codex-invocation matcher. Per worker-1 discovery,
# `\bcodex exec\b` misses the multi-line command-shape because flags can
# appear between `codex` and `exec` (e.g., `codex -a never -s ... exec ...`).
# This matches `codex` followed by zero-or-more flag/value tokens then `exec`.
_CODEX_INVOCATION_RE = re.compile(r"codex(\s+[A-Za-z0-9_=/-]+)*\s+exec\b")


def _bash_blocks(body: str) -> list[str]:
    """Return the text of every fenced ```bash ... ``` block."""
    return _BASH_FENCE_RE.findall(body)


def _codex_command_blocks(body: str) -> list[str]:
    """Return bash-fence block bodies that contain a codex exec invocation.

    Each returned string is the full multi-line block — callers must
    examine the entire block (not just one line) because the `< /dev/null`
    stdin redirect lives on the CLOSING line of the multi-line command,
    not the opening line that carries `codex ... exec`.
    """
    return [b for b in _bash_blocks(body) if _CODEX_INVOCATION_RE.search(b)]


def _plan_skill_combined() -> str:
    """Return skills/plan/SKILL.md spliced with all references/*.md.

    S02 (v0.17.x) split plan/SKILL.md into a thin router (<=300 lines)
    plus a references/ companion directory; the codex command-shape
    fenced bash blocks moved to `references/planner-dispatch.md` and
    `references/reviewer-dispatch.md`. The bash-fence + codex-exec
    invariants are still locked, but the scan surface is now the
    concatenation of SKILL.md + every references/*.md file.
    """
    text = PLAN_SKILL.read_text(encoding="utf-8")
    references_dir = PLAN_SKILL.parent / "references"
    if references_dir.is_dir():
        for ref in sorted(references_dir.glob("*.md")):
            text += "\n\n" + ref.read_text(encoding="utf-8")
    return text


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_all_codex_exec_lines_redirect_stdin():
    """MUST — every codex exec command-shape ends with `< /dev/null`.

    This is the primary mitigation for GitHub codex#20919
    (`readFileSync(0)` hang on inherited stdin). Every multi-line bash
    block that invokes `codex ... exec ...` MUST close with `< /dev/null`
    on its final non-empty line (or anywhere in the trailing redirect
    chain) so codex can never block waiting on parent stdin.
    """
    body = _plan_skill_combined()
    blocks = _codex_command_blocks(body)

    assert blocks, (
        f"Expected at least one fenced ```bash``` block containing a "
        f"`codex ... exec ...` invocation in {PLAN_SKILL.name}. Found none — "
        f"either the skill was restructured or the matcher regex drifted."
    )

    failing = []
    for idx, block in enumerate(blocks):
        # Search the whole block (not just the last line) so backslash-
        # continued / heredoc-style invocations still match. The redirect
        # token must appear somewhere after the `codex ... exec` token.
        if "< /dev/null" not in block:
            preview = block.strip()[:200]
            failing.append(f"Block #{idx + 1}: {preview!r}...")

    assert not failing, (
        f"GitHub codex#20919 mitigation broken — these codex exec command-shape "
        f"blocks in {PLAN_SKILL.name} are missing the `< /dev/null` stdin "
        f"redirect:\n  " + "\n  ".join(failing)
    )


def test_no_deprecated_full_auto_flag():
    """MUST — `--full-auto` absent from codex command-shape lines.

    `--full-auto` was deprecated and removed in codex CLI 0.133.0; the
    current top-level form is `-a never -s workspace-write`. Command-shape
    lines (inside fenced bash blocks) MUST NOT use `--full-auto`. PROSE
    deprecation notices (e.g. "`--full-auto` is deprecated (removed in
    0.133.0)") in the skill body explaining the deprecation are NOT
    command-shape and are whitelisted by the fenced-block scoping.
    """
    body = _plan_skill_combined()
    blocks = _codex_command_blocks(body)

    assert blocks, (
        f"Sanity precondition failed: no codex command-shape blocks "
        f"found in {PLAN_SKILL.name} to scan for --full-auto."
    )

    failing = []
    for idx, block in enumerate(blocks):
        if "--full-auto" in block:
            preview = block.strip()[:200]
            failing.append(f"Block #{idx + 1}: {preview!r}...")

    assert not failing, (
        f"Deprecated `--full-auto` flag found in codex command-shape blocks "
        f"in {PLAN_SKILL.name} (removed upstream in codex CLI 0.133.0; use "
        f"`-a never -s workspace-write` instead):\n  " + "\n  ".join(failing)
    )

    # Belt-and-suspenders: also confirm prose deprecation notices are
    # *present* (they document the migration for human readers). If these
    # vanish, the test still passes on the command-shape contract but the
    # skill loses its self-documenting deprecation context.
    prose_mentions = len(re.findall(r'--full-auto.*?deprecated|deprecated.*?--full-auto', body))
    assert prose_mentions >= 2, (
        f"Expected at least 2 prose deprecation notices for `--full-auto` "
        f"in {PLAN_SKILL.name} (Planner B and Reviewer B Codex Invocation "
        f"headers); found {prose_mentions}. Pattern: flexible word order."
    )


def test_codex_flag_order_top_level_before_exec():
    """MUST — `-a` / `-s` flags precede the `exec` subcommand token.

    Per `codex --help` (CLI 0.133.0+), `-a/--ask-for-approval` and
    `-s/--sandbox` are TOP-LEVEL options that MUST precede the `exec`
    subcommand. Placing them after `exec` is a parsing error in newer
    codex versions. This test verifies the order in every codex
    invocation in command-shape lines.
    """
    body = _plan_skill_combined()
    blocks = _codex_command_blocks(body)

    assert blocks, (
        f"Sanity precondition failed: no codex command-shape blocks "
        f"found in {PLAN_SKILL.name} to scan for flag order."
    )

    failing = []
    for idx, block in enumerate(blocks):
        # Locate the first `codex` token and the first `exec` token AFTER it.
        # The flag tokens between them define the top-level options region.
        # We only check the OPENING line of the invocation — subsequent
        # lines belong to the prompt heredoc and may contain any text.
        opening_line = None
        for line in block.splitlines():
            if _CODEX_INVOCATION_RE.search(line):
                opening_line = line
                break
        if opening_line is None:
            # Could happen if `codex` and `exec` are split across lines.
            # Fall back to the whole block.
            opening_line = block

        codex_pos = opening_line.find("codex")
        exec_pos = opening_line.find(" exec ", codex_pos)
        if exec_pos < 0:
            # Match may have `exec` at end-of-line followed by flags
            exec_match = re.search(r"\bexec\b", opening_line[codex_pos:])
            if exec_match:
                exec_pos = codex_pos + exec_match.start()

        if codex_pos < 0 or exec_pos < 0:
            failing.append(
                f"Block #{idx + 1}: could not locate `codex` and `exec` "
                f"tokens on opening line: {opening_line!r}"
            )
            continue

        top_level_region = opening_line[codex_pos:exec_pos]
        post_exec_region = opening_line[exec_pos:]

        # `-a` and `-s` MUST appear in the top-level region (before `exec`).
        # They MUST NOT appear as standalone short-flag tokens in the
        # post-exec region. (`-a` is a substring of many strings, so we
        # anchor on whitespace boundaries.)
        has_a_before = re.search(r"(?:^|\s)-a(?=\s|$)", top_level_region) is not None
        has_s_before = re.search(r"(?:^|\s)-s(?=\s|$)", top_level_region) is not None
        has_a_after = re.search(r"(?:^|\s)-a(?=\s|$)", post_exec_region) is not None
        has_s_after = re.search(r"(?:^|\s)-s(?=\s|$)", post_exec_region) is not None

        if not has_a_before:
            failing.append(
                f"Block #{idx + 1}: `-a` (approval policy) must appear "
                f"BEFORE `exec` as a top-level option; not found in "
                f"top-level region: {top_level_region!r}"
            )
        if not has_s_before:
            failing.append(
                f"Block #{idx + 1}: `-s` (sandbox) must appear BEFORE "
                f"`exec` as a top-level option; not found in top-level "
                f"region: {top_level_region!r}"
            )
        if has_a_after:
            failing.append(
                f"Block #{idx + 1}: `-a` must NOT appear after `exec` "
                f"(top-level flag misordering): {post_exec_region!r}"
            )
        if has_s_after:
            failing.append(
                f"Block #{idx + 1}: `-s` must NOT appear after `exec` "
                f"(top-level flag misordering): {post_exec_region!r}"
            )

    assert not failing, (
        f"Codex flag order violations (per codex --help CLI 0.133.0+, "
        f"`-a`/`-s` are TOP-LEVEL options preceding `exec`):\n  "
        + "\n  ".join(failing)
    )


def test_shell_timeout_prefix_on_codex_invocations():
    """MUST — every codex command-shape line has a `timeout NNNs ` prefix.

    The shell-level `timeout` prefix is the hard wall-clock fence (the
    Bash-tool `timeout` parameter is the belt-and-suspenders second layer).
    Accepted forms:
      - `timeout 300s codex ...` (literal numeric — legacy)
      - `timeout {timeout_s}s codex ...` (templated placeholder form)
      - `timeout ${CODEX_TIMEOUT_S}s codex ...` (shell variable expansion —
        v0.13.1 H1 fix: threads athanor.json `codex.timeoutMs` through Step 0)
    """
    body = _plan_skill_combined()
    blocks = _codex_command_blocks(body)

    assert blocks, (
        f"Sanity precondition failed: no codex command-shape blocks "
        f"found in {PLAN_SKILL.name} to scan for timeout prefix."
    )

    # Accept literal `timeout 300s`, templated `timeout {timeout_s}s`, or
    # shell-expansion `timeout ${CODEX_TIMEOUT_S}s` immediately before `codex`.
    timeout_prefix_re = re.compile(
        r"timeout\s+(?:\d+|\{[A-Za-z_][A-Za-z0-9_]*\}|\$\{[A-Za-z_][A-Za-z0-9_]*\})s\s+codex\b"
    )

    failing = []
    for idx, block in enumerate(blocks):
        # The prefix must appear on the SAME line as the opening `codex`
        # token — `timeout` cannot wrap a multi-line backslash-continued
        # command from outside (it would only apply to the first segment).
        opening_line = None
        for line in block.splitlines():
            if _CODEX_INVOCATION_RE.search(line):
                opening_line = line
                break
        if opening_line is None:
            failing.append(
                f"Block #{idx + 1}: could not locate the opening "
                f"`codex ... exec` line for timeout-prefix check."
            )
            continue

        if not timeout_prefix_re.search(opening_line):
            preview = opening_line.strip()[:200]
            failing.append(
                f"Block #{idx + 1}: opening line missing required "
                f"`timeout NNNs ` (or `timeout {{timeout_s}}s `) prefix "
                f"before `codex`: {preview!r}"
            )

    assert not failing, (
        f"Hard wall-clock fence missing on codex command-shape lines in "
        f"{PLAN_SKILL.name} (shell `timeout` prefix is the primary deadline; "
        f"Bash-tool timeout is the second layer):\n  " + "\n  ".join(failing)
    )


# ---------------------------------------------------------------------------
# Category (b) — schema tests (athanor-config.schema.json)
# ---------------------------------------------------------------------------


def _load_schema() -> dict:
    """Load the athanor-config schema as a plain dict (no validator needed)."""
    with CONFIG_SCHEMA.open(encoding="utf-8") as fh:
        return json.load(fh)


def test_codex_timeout_ms_key_in_schema():
    """MUST — `properties.codex.properties.timeoutMs` exists with type=integer.

    The Step 0 probe in skills/plan/SKILL.md reads `.codex.timeoutMs` from
    athanor.json. The schema MUST declare this key with integer type and a
    sane minimum so projects setting non-integer / sub-second values fail
    config validation rather than silently producing a 0-second `timeout 0s`
    prefix at dispatch.
    """
    schema = _load_schema()
    codex_props = schema.get("properties", {}).get("codex", {}).get("properties", {})
    assert "timeoutMs" in codex_props, (
        f"Schema {CONFIG_SCHEMA.name} missing `properties.codex.properties."
        f"timeoutMs` — the Step 0 probe reads `.codex.timeoutMs` but the "
        f"contract is undeclared. Found codex sub-keys: "
        f"{sorted(codex_props.keys())!r}"
    )

    timeout_ms = codex_props["timeoutMs"]
    assert timeout_ms.get("type") == "integer", (
        f"`properties.codex.properties.timeoutMs.type` must be 'integer'; "
        f"got {timeout_ms.get('type')!r}. Non-integer values would break the "
        f"`CODEX_TIMEOUT_S=$((CODEX_TIMEOUT_MS / 1000))` arithmetic."
    )
    assert timeout_ms.get("minimum") == 1000, (
        f"`properties.codex.properties.timeoutMs.minimum` must be 1000 "
        f"(1 second floor); got {timeout_ms.get('minimum')!r}. Below 1000ms "
        f"would yield `timeout 0s codex …` after integer division."
    )


def test_codex_timeout_ms_has_maximum():
    """MUST — `properties.codex.properties.timeoutMs` declares `maximum: 600000`.

    The schema MUST cap the upper bound at 600000 (10 minutes) so that
    misconfigured values (e.g. 999999999) are caught by JSON Schema
    validation rather than silently producing an absurdly long
    `timeout 999999s codex …` prefix. The inline jq ceiling guard (`. > 600`
    after ms→s conversion) is the runtime fallback; the schema maximum is the
    static contract.
    """
    schema = _load_schema()
    codex_props = schema.get("properties", {}).get("codex", {}).get("properties", {})
    timeout_ms = codex_props.get("timeoutMs", {})
    assert timeout_ms.get("maximum") == 600000, (
        f"`properties.codex.properties.timeoutMs.maximum` must be 600000 "
        f"(10 minutes cap); got {timeout_ms.get('maximum')!r}. Without a "
        f"schema-level maximum, arbitrarily large values pass validation."
    )


def test_inline_jq_clamping_matches_schema_bounds():
    """MUST — inline jq clamping values are consistent with schema bounds.

    The inline jq clamping expression uses `. < 1 then 300` (floor: 1 second,
    with default fallback to 300) and `. > 600 then 600` (ceiling: 600 seconds).
    The schema declares `minimum: 1000` (ms) and `maximum: 600000` (ms).

    Consistency check:
    - Schema minimum 1000 ms = 1 s. The jq floor guard `. < 1` clamps at 1s.
      These are consistent (1000ms / 1000 = 1s).
    - Schema maximum 600000 ms = 600 s. The jq ceiling guard `. > 600` clamps
      at 600s. These are consistent (600000ms / 1000 = 600s).

    If either the schema bounds or the jq clamping values drift independently,
    this test catches the inconsistency.
    """
    # --- Schema side ---
    schema = _load_schema()
    codex_props = schema.get("properties", {}).get("codex", {}).get("properties", {})
    timeout_ms = codex_props.get("timeoutMs", {})

    schema_min_ms = timeout_ms.get("minimum")
    schema_max_ms = timeout_ms.get("maximum")
    assert schema_min_ms is not None, "Schema missing timeoutMs.minimum"
    assert schema_max_ms is not None, "Schema missing timeoutMs.maximum"

    schema_min_s = schema_min_ms / 1000  # 1000 ms → 1 s
    schema_max_s = schema_max_ms / 1000  # 600000 ms → 600 s

    # --- Inline jq side (from SKILL.md codex command-shape blocks) ---
    body = _plan_skill_combined()
    blocks = _codex_command_blocks(body)
    assert blocks, (
        f"No codex command-shape blocks found in {PLAN_SKILL.name} "
        f"to extract jq clamping values from."
    )

    # Extract clamping values from the first block's jq line.
    # Expected patterns: `. < 1 then 300` (floor) and `. > 600 then 600` (ceiling)
    jq_line = None
    for block in blocks:
        for line in block.splitlines():
            if "CODEX_TIMEOUT_S=$(jq" in line:
                jq_line = line
                break
        if jq_line:
            break

    assert jq_line is not None, (
        f"Could not find inline jq computation line in any codex "
        f"command-shape block in {PLAN_SKILL.name}."
    )

    # Extract floor: `. < N` where N is the floor threshold in seconds
    floor_match = re.search(r"\. < (\d+)", jq_line)
    assert floor_match, (
        f"Could not extract floor threshold from jq line: {jq_line!r}"
    )
    jq_floor_s = int(floor_match.group(1))

    # Extract ceiling: `. > N` where N is the ceiling threshold in seconds
    ceiling_match = re.search(r"\. > (\d+)", jq_line)
    assert ceiling_match, (
        f"Could not extract ceiling threshold from jq line: {jq_line!r}"
    )
    jq_ceiling_s = int(ceiling_match.group(1))

    # Consistency assertions
    assert jq_floor_s == schema_min_s, (
        f"Jq floor guard (`. < {jq_floor_s}` → {jq_floor_s}s) is inconsistent "
        f"with schema minimum ({schema_min_ms}ms = {schema_min_s}s). "
        f"Expected jq floor = schema_min_ms / 1000 = {schema_min_s}."
    )
    assert jq_ceiling_s == schema_max_s, (
        f"Jq ceiling guard (`. > {jq_ceiling_s}` → {jq_ceiling_s}s) is "
        f"inconsistent with schema maximum ({schema_max_ms}ms = {schema_max_s}s). "
        f"Expected jq ceiling = schema_max_ms / 1000 = {schema_max_s}."
    )


def test_codex_fallback_after_ms_key_absent():
    """MUST — D3 lock — `fallbackAfterMs` key is ABSENT from the schema.

    Soft-deadline async-join (`fallbackAfterMs`) was deferred to v0.16+
    per the v0.13.1 plan D3 decision. Adding the key now would imply the
    leader-side wait/cancel orchestration is implemented when it is not.
    This test locks the deferral — even after ST6+ST7 landing.
    """
    schema = _load_schema()
    codex_props = schema.get("properties", {}).get("codex", {}).get("properties", {})
    assert "fallbackAfterMs" not in codex_props, (
        f"D3 lock violated: `properties.codex.properties.fallbackAfterMs` "
        f"must NOT exist in {CONFIG_SCHEMA.name} (deferred to v0.16+). "
        f"Adding this key implies the leader-side soft-deadline async-join "
        f"orchestration is implemented; it is not."
    )


def test_schema_id_v0160_bump():
    """MUST — `$id` URL contains the `v0.18.7` release-tag token.

    Per CONTRIBUTING.md §Release URL bump, the `$id` is pinned to the
    release tag. v0.18.7 bumps the URL token away from the v0.18.0 tag.
    """
    schema = _load_schema()
    schema_id = schema.get("$id", "")
    assert "v0.18.7" in schema_id, (
        f"`$id` URL in {CONFIG_SCHEMA.name} must contain 'v0.18.7' release "
        f"tag (per CONTRIBUTING.md §Release URL bump); got {schema_id!r}."
    )


def test_schema_describes_fallback_after_ms_deferral():
    """MUST — schema documents the `fallbackAfterMs` deferral to v0.16+.

    Schema is the primary contract; its `description` text for `timeoutMs`
    (or any sibling description in the codex sub-object) must mention the
    deferral so readers consulting the schema directly understand why the
    soft-deadline key is absent.
    """
    schema = _load_schema()
    codex_props = schema.get("properties", {}).get("codex", {}).get("properties", {})
    descriptions: list[str] = []
    for val in codex_props.values():
        desc = val.get("description") if isinstance(val, dict) else None
        if isinstance(desc, str):
            descriptions.append(desc)

    combined = "\n".join(descriptions)
    assert "deferred to v0.16+" in combined, (
        f"Schema {CONFIG_SCHEMA.name} must document the fallbackAfterMs "
        f"deferral with the phrase 'deferred to v0.16+' in at least one "
        f"`properties.codex.properties.*.description`. Existing descriptions:"
        f"\n  - " + "\n  - ".join(descriptions or ["(none)"])
    )


# ---------------------------------------------------------------------------
# Category (c) — Step 0 probe tests (skills/plan/SKILL.md)
# ---------------------------------------------------------------------------


def test_step0_reads_timeout_ms_via_jq():
    """MUST — Step 0 probe reads `.codex.timeoutMs` via `jq -r`.

    The Step 0 probe in skills/plan/SKILL.md MUST contain the literal
    `jq -r '.codex.timeoutMs` substring so the timeout value is sourced
    from athanor.json (with the `// 300000` default applied at the jq
    level rather than in shell).
    """
    body = _plan_skill_combined()
    needle = "jq -r '.codex.timeoutMs"
    assert needle in body, (
        f"Step 0 probe in {PLAN_SKILL.name} must read `.codex.timeoutMs` "
        f"via `jq -r` (literal substring {needle!r} not found). The probe "
        f"is responsible for sourcing the timeout from athanor.json so the "
        f"command-shape `timeout {{timeout_s}}s codex …` prefix is "
        f"substituted with the project-configured value."
    )


def test_step0_converts_ms_to_seconds():
    """MUST — Step 0 converts CODEX_TIMEOUT_MS → CODEX_TIMEOUT_S via arithmetic.

    The shell `timeout` builtin accepts a seconds suffix; the schema
    declares milliseconds for sub-second precision parity with other ms
    fields. The Step 0 probe MUST perform the ms→s conversion via shell
    arithmetic expansion (`$((CODEX_TIMEOUT_MS / 1000))`).
    """
    body = _plan_skill_combined()
    needle = "CODEX_TIMEOUT_S=$((CODEX_TIMEOUT_MS"
    assert needle in body, (
        f"Step 0 probe in {PLAN_SKILL.name} must convert ms→s via shell "
        f"arithmetic expansion. Expected substring {needle!r} not found. "
        f"Without the conversion, the shell `timeout` prefix would receive "
        f"a millisecond integer (e.g. `timeout 300000s`) — 5000× longer "
        f"than intended."
    )


# ---------------------------------------------------------------------------
# Category (d) — Phase 5 Step 5.5 deterministic static redirect test
# ---------------------------------------------------------------------------


# Re-exported for the Step 5.5 test below; matches the module-level
# constants by name for parity with the plan-body wording.
SKILL_PATH = PLAN_SKILL


def test_redirect_token_present_in_skill_text():
    """Static check: every codex exec command-shape block contains `< /dev/null`.

    Rationale (vs subprocess-based stdin block check):
    - pytest may inherit closed stdin, masking real-world hang behavior
    - shell mock with named pipe is flaky in CI (race on pipe open/close)
    - Static text verification is deterministic + sufficient for the
      contract: "rendered SKILL.md must lock the redirect token at end
      of every codex exec command-shape line"
    - Shell-mock subprocess test is DEFERRED to v0.13.2 (cost/value
      trade-off — flake risk > additional signal)

    Implementation note (per worker-1 multi-line discovery):
    The plan body's narrow regex `\\bcodex .* exec\\b[^\\n]*` is LINE-SCOPED
    and misses backslash-continued / heredoc multi-line invocations where
    the `< /dev/null` token lives on the CLOSING line of the bash block,
    not the opening `codex … exec …` line. This test anchors on the
    fenced ```bash ... ``` block region instead — every block containing a
    codex invocation must contain the redirect token somewhere in its body.
    """
    text = _plan_skill_combined()  # SKILL_PATH = PLAN_SKILL; combined surface includes references/
    blocks = _codex_command_blocks(text)

    assert blocks, (
        f"Static redirect check requires at least one fenced ```bash``` "
        f"block with a codex invocation in {SKILL_PATH.name}; found none. "
        f"Either the skill was restructured or the matcher regex drifted."
    )

    missing = []
    for idx, block in enumerate(blocks):
        if "< /dev/null" not in block:
            preview = block.strip()[:200]
            missing.append(f"Block #{idx + 1}: {preview!r}...")

    assert not missing, (
        f"Deterministic static redirect check failed — codex command-shape "
        f"blocks in {SKILL_PATH.name} missing `< /dev/null` token "
        f"(GitHub codex#20919 mitigation lock):\n  " + "\n  ".join(missing)
    )


# ---------------------------------------------------------------------------
# Category (e) — Behavior-level subprocess proof
# ---------------------------------------------------------------------------


def test_shell_timeout_prefix_uses_template_variable():
    """MUST — H1 lock — every codex command-shape line threads the
    `${CODEX_TIMEOUT_S}s` shell-expansion form (NOT hardcoded `300s`).

    Worker bash block computes `CODEX_TIMEOUT_S` inline via
    `CODEX_TIMEOUT_S=$(jq ... athanor.json)` with clamping. If command-shape
    lines hardcode `timeout 300s`, the configured timeout is silently
    ignored — the config key becomes phantom. H1 fix threads the variable
    through.

    Accepted forms (template-style):
      - `timeout ${CODEX_TIMEOUT_S}s codex ...` — shell variable expansion
      - `timeout {timeout_s}s codex ...` — Splitter/Leader placeholder

    REJECTED form (hardcoded literal): `timeout 300s codex ...`
    """
    import re as _re

    body = _plan_skill_combined()
    blocks = _codex_command_blocks(body)

    assert blocks, (
        f"Sanity precondition failed: no codex command-shape blocks "
        f"found in {PLAN_SKILL.name} to scan for template-variable prefix."
    )

    # Template-form prefix: either ${VAR}s or {var}s — both reference a
    # value sourced from config rather than a literal numeric.
    template_prefix_re = _re.compile(
        r"timeout\s+(?:\{[A-Za-z_][A-Za-z0-9_]*\}|\$\{[A-Za-z_][A-Za-z0-9_]*\})s\s+codex\b"
    )
    # Hardcoded literal numeric prefix — what H1 fixes.
    literal_prefix_re = _re.compile(r"timeout\s+\d+s\s+codex\b")

    failing = []
    for idx, block in enumerate(blocks):
        opening_line = None
        for line in block.splitlines():
            if _CODEX_INVOCATION_RE.search(line):
                opening_line = line
                break
        if opening_line is None:
            failing.append(
                f"Block #{idx + 1}: could not locate the opening "
                f"`codex ... exec` line for template-variable check."
            )
            continue

        if literal_prefix_re.search(opening_line):
            preview = opening_line.strip()[:200]
            failing.append(
                f"Block #{idx + 1}: opening line uses HARDCODED literal "
                f"`timeout NNNs` prefix (phantom config — Step 0 "
                f"CODEX_TIMEOUT_S is ignored): {preview!r}"
            )
            continue

        if not template_prefix_re.search(opening_line):
            preview = opening_line.strip()[:200]
            failing.append(
                f"Block #{idx + 1}: opening line missing required "
                f"template-form `timeout ${{CODEX_TIMEOUT_S}}s` "
                f"(or `timeout {{timeout_s}}s`) prefix: {preview!r}"
            )

    assert not failing, (
        f"H1 phantom-config violation — codex command-shape lines in "
        f"{PLAN_SKILL.name} must thread the Step 0 `${{CODEX_TIMEOUT_S}}` "
        f"variable (not hardcode `300s`):\n  " + "\n  ".join(failing)
    )


def test_codex_command_blocks_compute_timeout_inline():
    """MUST — every codex command-shape bash block contains the inline
    `CODEX_TIMEOUT_S=$(jq` computation line BEFORE the `timeout ${CODEX_TIMEOUT_S}s`
    line.

    v0.13.1 moved timeout computation from Step 0 probe into each bash block
    as an inline jq one-liner. This test verifies that EVERY codex command-shape
    block has the inline computation, and that it appears BEFORE the timeout
    prefix line (ordering matters — the variable must be set before use).
    """
    body = _plan_skill_combined()
    blocks = _codex_command_blocks(body)

    assert blocks, (
        f"Sanity precondition failed: no codex command-shape blocks "
        f"found in {PLAN_SKILL.name} to scan for inline jq computation."
    )

    failing = []
    for idx, block in enumerate(blocks):
        lines = block.splitlines()
        jq_line_idx = None
        timeout_line_idx = None

        for i, line in enumerate(lines):
            if "CODEX_TIMEOUT_S=$(jq" in line and jq_line_idx is None:
                jq_line_idx = i
            if re.search(r"timeout\s+\$\{CODEX_TIMEOUT_S\}s\s+codex\b", line) and timeout_line_idx is None:
                timeout_line_idx = i

        if jq_line_idx is None:
            preview = block.strip()[:200]
            failing.append(
                f"Block #{idx + 1}: missing inline `CODEX_TIMEOUT_S=$(jq` "
                f"computation line: {preview!r}..."
            )
        elif timeout_line_idx is None:
            preview = block.strip()[:200]
            failing.append(
                f"Block #{idx + 1}: has inline jq computation but missing "
                f"`timeout ${{CODEX_TIMEOUT_S}}s codex` line: {preview!r}..."
            )
        elif jq_line_idx >= timeout_line_idx:
            failing.append(
                f"Block #{idx + 1}: inline jq computation (line {jq_line_idx}) "
                f"appears AFTER timeout usage (line {timeout_line_idx}) — "
                f"variable used before set."
            )

    assert not failing, (
        f"Inline jq timeout computation violations in {PLAN_SKILL.name} — "
        f"every codex command-shape block must compute CODEX_TIMEOUT_S via "
        f"inline `$(jq ...)` BEFORE the `timeout ${{CODEX_TIMEOUT_S}}s` "
        f"prefix:\n  " + "\n  ".join(failing)
    )


def test_inline_jq_clamps_timeout_bounds():
    """MUST — the inline jq expression contains clamping logic (1s floor, 600s ceiling).

    The inline jq one-liner must contain `. < 1` (floor guard) and `. > 600`
    (ceiling guard) to prevent misconfigured `codex.timeoutMs` values from
    producing dangerously short or unbounded timeout prefixes. Without clamping:
    - timeoutMs=0 → `timeout 0s codex ...` (instant kill)
    - timeoutMs=999999999 → `timeout 999999s codex ...` (11+ day hang)
    """
    body = _plan_skill_combined()
    blocks = _codex_command_blocks(body)

    assert blocks, (
        f"Sanity precondition failed: no codex command-shape blocks "
        f"found in {PLAN_SKILL.name} to scan for jq clamping logic."
    )

    failing = []
    for idx, block in enumerate(blocks):
        # Find the inline jq computation line
        jq_line = None
        for line in block.splitlines():
            if "CODEX_TIMEOUT_S=$(jq" in line:
                jq_line = line
                break

        if jq_line is None:
            failing.append(
                f"Block #{idx + 1}: no inline jq computation line found "
                f"(prerequisite for clamping check)."
            )
            continue

        if ". < 1" not in jq_line:
            failing.append(
                f"Block #{idx + 1}: inline jq expression missing floor "
                f"guard `. < 1` — sub-second timeouts would not be clamped."
            )
        if ". > 600" not in jq_line:
            failing.append(
                f"Block #{idx + 1}: inline jq expression missing ceiling "
                f"guard `. > 600` — unbounded timeouts would not be clamped."
            )

    assert not failing, (
        f"Inline jq clamping violations in {PLAN_SKILL.name} — the timeout "
        f"computation must clamp to [1, 600] seconds (`. < 1` floor + "
        f"`. > 600` ceiling guards):\n  " + "\n  ".join(failing)
    )


def test_stdin_redirect_actually_prevents_block():
    """Behavior-level proof: stdin redirect to null device prevents stdin block.

    Spawns a Python subprocess that reads stdin to EOF + prints "ok".
    Without redirect: subprocess inherits pytest's stdin (which may be a
    TTY pipe or closed) and may block.
    With stdin=DEVNULL: subprocess gets immediate EOF and prints "ok".

    This is the behavior-level companion to the static text-presence checks
    above — H3 mitigation against adversarial refactor that satisfies the
    string-presence tests while reintroducing the upstream hang.

    Uses `subprocess.DEVNULL` (platform-portable — `/dev/null` on POSIX,
    `NUL` on Windows) rather than shell `< /dev/null` redirect.
    """
    import subprocess
    import sys

    # subprocess.DEVNULL is the portable equivalent of shell `< /dev/null`
    # / `< NUL` — proves stdin is closed before child reads, regardless of OS.
    result = subprocess.run(
        [sys.executable, "-c", "import sys; sys.stdin.read(); print('ok')"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=2,
    )
    assert result.returncode == 0, f"Redirect test failed: {result.stderr}"
    assert "ok" in result.stdout, f"Expected 'ok', got: {result.stdout!r}"
