<!-- Relocated from CLAUDE.md at v0.16.0.
     Canonical runtime reference remains in CLAUDE.md §Defense Mechanisms status table.
     This file contains historical post-mortem detail moved here to reduce per-session token load. -->

# Stop Hook Post-Mortem (Historical)

## v0.11.3 Input-Layer Fix

#### Stop hook v0.11.3 input-layer fix (post-mortem)

For 5 release cycles (v0.7.8 → v0.11.2), the script's stdin parser assumed
the Stop event payload contained `last_assistant_message: <string>`. Claude
Code actually sends `transcript_path: <jsonl-path>` and the message lives
inside that file. Every Stop event silently fail-opened (`exit 0` with stderr
`"last_assistant_message missing or non-string"`). The 35+ existing tests in
`tests/test_regression_stop_hook_script.py` used the same incorrect assumed
payload shape, so they passed while production fail-opened.

v0.11.3 introduces `_read_last_assistant_message()` and `_content_to_text()`
in `scripts/hooks/stop_verify_claims.py`. The new parser accepts BOTH the
legacy shape (preserves the 35+ existing tests as a backwards-compat lock)
AND the real Claude Code shape (`transcript_path` → JSONL → reverse-scan
to the first main-session `entry.type == "assistant"` with `isSidechain
!= true` → join `text` blocks from `message.content`). Sub-agent assistant
turns are skipped so only the main-session model response gates. The
`stop_hook_active` flag is pass-through; re-entry semantics remain governed
by the existing `hook_state` circuit breaker per v0.7.9 design.

The detection logic shipped in v0.7.9 (nonce sentinel), v0.10.2 (paraphrase
regex + NFKC + Cyrillic fold + vendor-aware whitelist), and v0.10.3 (Greek/
Armenian fold + conditional-tense suppression + attribution skip) is
code-correct and unchanged; it was simply unreachable in production until
v0.11.3 fixed the input layer. The `**enforced (command-based)**` label
in the status table above is now honest.

`tests/test_regression_v011_3_stop_hook_input_layer.py` adds 25 mandatory +
1 xfail-tolerant tests against the real Claude Code payload shape. The
2026-05-18 dry-run spike documented in `docs/STATE.md` confirmed `exit 2`
behavior but did not validate the stdin parsing path (it tested the gate
by manually piping JSON, which masked the production gap).

Scope note (added v0.11.4): the v0.11.3 fix above was reachable only in
athanor's source repo until v0.11.4's `${CLAUDE_PLUGIN_ROOT}` path fix —
see §"Stop hook v0.11.4 plugin-root deployment fix (post-mortem)" below.

- **Skill source:** `skills/verification-before-completion/SKILL.md` (MIT, vendored)
- **Hook config:** `hooks/hooks.json` → Stop event, type `command` → `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/hooks/stop_verify_claims.py"` (plugin-root expansion since v0.11.4; bare relative path in v0.7.8 → v0.11.3 was the deployment-path bug)
- **Detection scope:** material claims (edits applied / files
  created-removed-renamed / tests passing-failing / lint-typecheck clean /
  builds succeeding / bug fixed / requirements met / releases shipped /
  migrations completed / deployments succeeded / agent task completed /
  verification output) — English + Korean phrase whitelist. Explicitly
  skipped (no exit 2): pure analysis, planning, design, opinions, research
  Q&A, tool-output summaries that don't assert work status.

**What it catches:** material-claim turns without fresh evidence — the
model must invoke the verification skill before Stop succeeds. Adversarial
rationalization that previously bypassed the v0.7.7 prompt nudge now hits
a runtime exit-2 gate.

**What it does NOT catch:** material claims phrased outside the whitelist
(false negative — the whitelist mirrors v0.7.7's well-tuned set; expand
deliberately, not greedily), or quoted historical references that contain
trigger phrases (e.g., "the v0.7.6 docs claimed 'tests pass'"). Sentence-
level attributed-history detection was originally promised as v0.8.0+ work
but shipped in v0.10.3 R3 (attribution / paired-quote / attributed-verb
suppression in `stop_verify_claims.py`); residual semantic-similarity and
multi-paragraph quote-span detection is deferred to v0.11.8+. Users
encountering false positives can set `profile: "off"` as the escape hatch.

## v0.11.4 Plugin-Root Deployment Fix

#### Stop hook v0.11.4 plugin-root deployment fix (post-mortem)

The v0.11.3 input-layer fix was correct in code but only reachable when
Claude Code resolved the hook command relative to athanor's own source
repo. The hook command in `hooks/hooks.json` was registered with a
bare relative path (`python3 scripts/hooks/stop_verify_claims.py`)
which CC resolves relative to the user's PROJECT cwd, not the plugin
install dir. For any user with athanor installed user-scope but
working in another project, CC would fail to find the script and exit
2 with stderr `python3: can't open file '<project>/scripts/hooks/
stop_verify_claims.py'`. CC treats that stderr pattern as
"hook script missing" — non-blocking — so the gate was silently
absent in every project except athanor's source repo from v0.7.8
through v0.11.3 inclusive.

v0.11.4 closes the deployment-path arc. `hooks/hooks.json` now uses
`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/hooks/stop_verify_claims.py"`
— the env var `${CLAUDE_PLUGIN_ROOT}` is set by Claude Code for plugin
hooks and expands to the plugin install path. This matches the
industry pattern used by `superpowers`, `claude-mem`, and `openai-codex`
plugin hook registrations. The v0.11.3 input-layer fix and the v0.11.4
deployment-path fix are companion-fixes of the same latent bug arc —
script wrong (closed v0.11.3) + path wrong (closed v0.11.4). The
shared meta-cause: manual testing only inside athanor's source repo
hid both bugs simultaneously.

`tests/test_regression_stop_command_hook.py::test_stop_hook_command_uses_plugin_root_or_absolute_path`
locks the invariant — bare relative paths in the Stop hook command
string will fail this test post-v0.11.4.

The detection layers shipped in v0.7.9 / v0.10.2 / v0.10.3 + v0.11.3
input-layer fix are unchanged and now actually reach every project
where athanor is installed.

## Companion-Fix Arc (v0.7.8 → v0.11.7)

The Stop hook went through a 5-layer companion-fix arc from v0.7.8 (where
the gate was first claimed `**enforced**`) through v0.11.7 (where the final
honesty residuals were reclassified and a minimal B1 detection shipped).
The arc is referenced in CLAUDE.md §Defense Mechanisms status table:

> The companion-fix arc 5 layers (v0.11.3 input parser → v0.11.4 plugin-root
> path → v0.11.5 doc drift → v0.11.6 sentinel body hash → v0.11.7 scanner
> extension + B1 minimal) survive the cutover intact (D10). Honesty
> residuals (v0.11.8+): LLM-class semantic similarity, conditional /
> speculative tense without prefix marker, multi-paragraph quote spans,
> Cherokee / full-width-Latin homoglyphs.

### Companion-fix arc 5 layers (canonical table from `docs/STATE.md`)

| Layer | Release | Bug |
|---|---|---|
| 1. Runtime stdin parser shape | v0.11.3 | script wrong (last_assistant_message vs transcript_path) |
| 2. Hook command path resolution | v0.11.4 | path wrong (relative vs ${CLAUDE_PLUGIN_ROOT}) |
| 3. CLAUDE.md doc drift class | v0.11.5 | Markdown untestable claims |
| 4. Sentinel body-hash binding | v0.11.6 | trailing-whitespace round-trip mismatch |
| **5. Scanner extension + Residual reclassification + B1 minimal** | **v0.11.7** | **Python docstrings + STATE.md outside scanner; documented bugs carried as anonymous "candidates"; profile mutation undetected** |

### Arc summary

v0.11.3 (script wrong) → v0.11.4 (path wrong) → v0.11.5 (CLAUDE.md doc drift)
→ v0.11.6 (sentinel body-hash binding) → v0.11.7 (scanner extension +
Residual reclassification + B1 minimal). The 5-layer circuit was not
disturbed by the v0.11.8 vendoring pivot or the v0.12.0 atomic cut. Stop
hook script (`scripts/hooks/stop_verify_claims.py`) + regression suite +
Spec-then-TDD discipline + cross-model `/athanor:plan` all preserved.

Shared meta-cause across the arc: documentation surface drifts faster than
test coverage; the "Residual known limitations" block became a
hold-everything bin and required the v0.11.6 reclassification pattern to be
applied more broadly. v0.11.7 labeled each entry with a ship-capable intent
(Severity / Target / Acceptance) so the bin was cleaned up.

### Residuals carried forward (v0.11.8+)

- LLM-class semantic similarity (paraphrase outside whitelist + regex set)
- Conditional / speculative tense without prefix marker
- Multi-paragraph quote spans (attributed-history detection only covers
  inline quote pairs)
- Cherokee / full-width-Latin homoglyph confusable folds (Cyrillic / Greek
  / Armenian shipped at v0.10.2 / v0.10.3)
- B1 full architectural treatment (snapshot / cache / lock + legitimate
  cross-session edit handling — v0.11.7 ship was detection-only)
