# Changelog

All notable changes to Athanor are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [0.8.0] — 2026-05-19

**Spec-then-TDD discipline integration — advisory, planner-classified.** The
v0.8.0 release moves athanor beyond pure agentic orchestration into a
gentle-discipline regime: `/athanor:plan` Planner A produces Verify fields as
MUST/SHOULD observable assertions for behavior-bearing phases, the
`/athanor:work` Task Splitter classifies each generated subtask into
`spec-then-tdd | test-aware | direct`, and the Executor branches the
dispatch packet accordingly — red-first 5 steps for spec-then-tdd, broader
`tests/**` end-gate for test-aware, current Ralph-Loop for direct. Same
honesty arc as v0.7.7→v0.7.9: this is **advisory** (no runtime Stop-hook
enforcement of the discipline itself), the framing stays "advisory
(planner-classified)" throughout, and the limitations are documented in
plain language.

Plan: `docs/plans/2026-05-19-001-feat-v0.8.0-tdd-sdd-integration-plan.md`
Origin: `docs/brainstorms/2026-05-19-001-tdd-sdd-integration-requirements.md`

### Added (advisory — planner-classified Spec-then-TDD)

- **`execution_note` field on subtasks** (U2): `/athanor:work` Task Splitter
  assigns one of `spec-then-tdd | test-aware | direct` per subtask using
  inline classification heuristics in `skills/work/SKILL.md` Step 0.5 Rules:
  source-code + new behavior → spec-then-tdd; source-code + behavior
  preservation → test-aware; prose-only edits (`.md`, `_doc`, CHANGELOG) →
  direct.
- **`acceptance_criteria` propagation** (U2): spec-then-tdd subtasks inherit
  the parent phase's `Verify:` MUST/SHOULD bullets as their
  acceptance_criteria field. If the parent Verify is prose-only, the Splitter
  reclassifies the subtask to test-aware with an explanation in the task
  description.
- **Red-first 5-step Executor branch** (U3): for `execution_note: spec-then-tdd`,
  the Executor dispatch prompt walks each acceptance criterion through WRITE
  → RUN → VERIFY RED → IMPLEMENT → VERIFY GREEN, requiring per-criterion
  `red_evidence` (command, test_node_id, exit_code, output_tail) in
  ATHANOR_RESULT.
- **Broader test-aware gate** (U3): the test-aware end gate accepts any
  `tests/**` path modification (test_*.py, conftest.py, fixtures/, snapshots,
  golden files), not just `tests/test_*.py` — chosen after Codex review
  flagged the narrower pattern as too restrictive.
- **Auto-downgrade on `never_red`** (U4): the leader validates the worker's
  `red_evidence` shape and computes `red_status_resolved`. If any criterion
  has missing/malformed evidence or `exit_code == 0`, the subtask is silently
  auto-downgraded to `test-aware` completion criteria with a work-log
  breadcrumb. No user escalation.
- **Critic two-axis rubric** (U5): `/athanor:plan` Critic (all four variants —
  deep 4-input, deep 2-input review-skipped, standard 2-input, self-critic
  fallback) evaluates plans along axis (A) acceptance_criteria coverage AND
  axis (B) classification appropriateness — flagging both over-classification
  (CHANGELOG-only phase with MUST/SHOULD) and under-classification (source
  code with prose-only Verify).
- **CLAUDE.md Defense Mechanisms row + subsection** (U6): new
  `Spec-then-TDD Discipline | advisory (planner-classified)` row in the
  status table and a new `### Spec-then-TDD Discipline (advisory —
  planner-classified)` subsection with full mechanism description and
  honesty paragraphs.
- **6 new regression-test files** (U1+U2+U3+U4+U5+U7 contributions): pin the
  prompt-level and result-handler contracts across the affected skills.
  Total test count: 154 baseline + 13 Phase A + 20 Phase B + 6 Phase C =
  193 passing.

### Changed

- Plan / plugin version: v0.7.9 → v0.8.0 (minor bump — new feature surface).
- JSON Schema `$id` URL release-tag pin: v0.7.9 → v0.8.0.
- `skills/plan/SKILL.md` Plan Structure template: `Verify: {how to verify}`
  → `Verify (MUST/SHOULD for behavior-bearing phases; prose for non-behavior)`
  with MUST/SHOULD example bullets and behavior-bearing vs non-behavior
  guidance prose.
- `skills/work/SKILL.md` Step 0.5 Splitter prompt: Rules block extended with
  classification heuristics + AC propagation rule; Output Format template
  shows `execution_note:` and `acceptance_criteria:` fields; Post-split
  Validation rules 7-8 check execution_note presence + AC for spec-then-tdd.
- `skills/work/SKILL.md` Step 2a Dispatch Packet: §"Execution Instructions"
  replaces the prior single Ralph-Loop block with three conditional blocks
  (Direct, Spec-then-TDD, Test-Aware End Gate) plus the grandfathered fallback
  to Direct.
- `skills/work/SKILL.md` Step 2b Process Result: new v0.8.0 result-handler
  with four phases (red_evidence shape validation, downgrade rule, test-aware
  gate enforcement, grandfathered breadcrumb) runs before the existing
  success/failure branching.
- `skills/plan/SKILL.md` Step 4 Critic Refinement: new shared `#### v0.8.0
  Critic Rubric — Spec-then-TDD Readiness` subsection invoked by all Critic
  variants.

### Voice / honesty

- **advisory (planner-classified)** — the mechanism is NOT a Stop-hook gate.
  v0.7.7~v0.7.9 advisory/enforced labeling discipline maintained: the new
  Defense Mechanisms row reads "advisory" exactly because the discipline is
  prompt-only, not runtime-enforced.
- "TDD enforced" / "Spec-driven required" overclaim phrases are intentionally
  avoided across CLAUDE.md, CHANGELOG, and skill prompts. A regression test
  in `tests/test_regression_claude_md_honesty.py` asserts absence.
- **R6 semantics drift acknowledged**: the brainstorm origin said "work skill
  detects" non-RED; the actual implementation is "leader validates worker's
  self-reported red_evidence shape." Adversarial forgery (worker fabricating
  evidence) is not caught; only the most common honest mistake (worker forgot
  the RED step entirely → no evidence) is caught.
- **Planner-time visibility limit acknowledged**: because execution_note is
  Splitter-generated (work-skill side), `/athanor:plan` output and Critic
  review do NOT see the final subtask classifications. Mitigations: (1) the
  Critic predicts classifications from phase file-sets and flags
  misclassification risk; (2) the user can edit plan.md between Splitter
  output and `/athanor:work` execution; (3) work-log accumulates the actual
  classifications for post-hoc analysis.
- Splitter misclassification (false-positive / false-negative) is a real
  first-cycle risk. v0.8.x will refine the heuristic based on operational
  data. v0.8.1+ candidate: verification-before-completion skill extension
  that checks test-commit existence at Stop-hook gate (advisory → runtime).

### Migration

- Existing `/athanor:plan` users: no command-line change. New plan outputs
  carry the new fields automatically; old plan docs are grandfathered.
- 4 grandfathered plans in `docs/plans/` (`2026-04-08-001-*`,
  `2026-05-18-001-*`, `2026-05-18-002-*`, `2026-05-19-001-*` — this plan
  itself) have no `execution_note` field. `/athanor:work` falls back to
  `direct` for any subtask with a missing `execution_note`, logged in
  ATHANOR_RESULT as `execution_note_source: grandfathered`.
- Per-project opt-out: no `athanor.json` flag (the discipline is advisory).
  Users can manually edit plan.md `## Subtasks` block to set
  `execution_note: direct` on any subtask, or add a
  `<!-- athanor:subtasks:manual -->` marker to bypass the Splitter entirely.

### Deferred (post v0.8.0)

- **v0.8.1+**: verification-before-completion skill extension (Stop-hook
  validates test-commit existence for spec-then-tdd subtasks at session
  close). baseline 효과 측정 후 결정.
- **v0.8.x**: classification heuristic refinement based on operational
  false-positive / false-negative data.
- **v0.9.0+**: BDD Given/When/Then format option for acceptance_criteria
  (currently observable-assertion MUST/SHOULD single format).

## [0.7.9] — 2026-05-18

**Stop hook hardening — closes 2 of 3 P0 architectural findings from PR #16
ce-code-review (sentinel forgery + parent-dir athanor.json hijack).** Paraphrase
bypass (P0 #3) deferred to a follow-up PR to keep this release focused. Same
security-honesty arc as v0.7.7 → v0.7.8: the "enforced (command-based)" label
gets less asterisks each release as actual bypass paths close.

Plan: `docs/plans/2026-05-18-002-feat-v0.7.9-stop-hook-hardening-plan.md`
(633 lines, 8 units). This release implements U1, U2, U3, U4, U6, U8; defers
U5 (paraphrase regex) + full U7 doc rewrite to a v0.7.9.1 follow-up PR.

### Added

- `scripts/hooks/hook_state.py` (new, U1) — per-session state-file helpers
  (nonce + stop-counter) with atomic writes (tempfile + os.replace),
  60-second nonce TTL, path-traversal-safe session ID whitelist.
- `scripts/hooks/sentinel_helper.py` (new, U2) — invoked by the verification
  skill via Bash to generate a nonce + body SHA-256 hash, write state, and
  print a v=2 sentinel for the model to emit.
- `hooks.stopLoopThreshold` config field (U6) — configurable circuit-breaker
  threshold (integer ≥1, default 3). After N consecutive exit-2 blocks per
  session, the gate releases (exit 0) to prevent infinite loops when the
  verification skill misbehaves.
- 33 new regression tests covering state helpers, v=2 sentinel binding,
  body-tampering rejection, one-shot deletion, v=1 legacy rejection,
  missing-state forgery rejection, `$CLAUDE_PROJECT_DIR` env-var honored,
  parent-dir hijack blocked by `.git` boundary, git-root resolution
  mechanism.

### Changed (P0 closures)

- **P0 #1 sentinel forgery — CLOSED**: `validate_emission_sentinel` does full
  v=2 protocol verification (nonce match + TTL + body SHA-256 hash + atomic
  delete on success). v=1 bare-string sentinels are rejected with a stderr
  deprecation warning. Forgery cost raised from "emit one string" to "write
  JSON state with matching SHA-256 + emit matching sentinel".
- **P0 #2 parent-dir hijack — CLOSED**: `_find_athanor_config` rewritten with
  priority chain `$CLAUDE_PROJECT_DIR` → git-root → walk-up-stops-at-`.git`.
  Walk-up never crosses a `.git/` boundary upward. Resolution mechanism
  surfaced in the profile=off audit breadcrumb.
- **Circuit breaker (U6)**: per-session counter increments on each exit-2.
  After `hooks.stopLoopThreshold` (default 3), the gate releases with a
  stderr warning. Counter resets on successful v=2 validation.

### Verification skill (U2)

`skills/verification-before-completion/SKILL.md` §Emission Sentinel rewritten
for v=2 protocol. 3-step procedure: (1) compute evidence body, (2) pipe
through `sentinel_helper.py emit`, (3) emit sentinel + body verbatim. The
helper writes nonce state; the hook validates body-hash equality on Stop.

### Migration

- v=1 sentinels (v0.7.8 format) are no longer accepted — they were trivially
  forgeable. Skill responses with v=1 sentinels will fall through to
  material-claim check, but the verification skill (vendored) is upgraded
  atomically in the same release so no version-skew scenario exists for
  default installs.
- No mandatory config changes. `hooks.stopLoopThreshold` is optional
  (defaults to 3 if missing).

### Deferred to v0.7.9.1

- **P0 #3 paraphrase bypass (U5)**: regex pattern layer + verb-anchor
  heuristics + NFKC unicode normalization with curated confusables fold.
  Plan §U5 specifies the design; deferred to keep this release scope-limited.
- **Full CLAUDE.md / STATE.md honesty refresh (U7)**: ships with the U5
  follow-up PR so both updates land together.

### Spike reference

v=2 protocol design rests on the 2026-05-18 spike (docs/STATE.md) that
verified Claude Code runtime honors `type: command` Stop hooks with `exit 2`.
No new spike needed for v0.7.9.

## [0.7.8] — 2026-05-18

**Stop hook command-mode release — the v0.7.7-promised enforcement upgrade.**
v0.7.7 demoted the Stop hook label from "enforced" to "advisory (prompt-based)"
because the implementation was a prompt nudge, not a runtime gate, and promised
v0.7.8 would deliver real enforcement (per the 2026-05-18 spike PASS). This
release delivers it: `hooks/hooks.json` now registers `type: command` invoking
`scripts/hooks/stop_verify_claims.py`, which reads the Stop event payload,
detects material claims, and exits 2 to block Stop with stderr fed back to the
model as continuation context.

Same security-honesty framing as v0.7.7 — we said v0.7.8 would deliver
enforcement; v0.7.8 delivers it. If the spike had failed (`exit 2` didn't
actually block), this release would have shipped an honest "no, the runtime
doesn't support it yet" instead. The spike PASSED, so the upgrade is real.

Session: `2026-05-18-001` (continuation of v0.7.7 session). Plan:
`docs/plans/2026-05-18-001-feat-v0.7.8-stop-hook-command-mode-plan.md`.

### Why this release

Three threads converge:

1. **v0.7.7 promised it.** CLAUDE.md and CHANGELOG both stated v0.7.8 would
   re-promote the label to `enforced (command-based)` if the spike confirmed
   the runtime contract. Not delivering would be a fresh trust-erosion event
   identical to the one v0.7.7 fixed.
2. **The spike PASSED.** Empirically verified (`docs/STATE.md` §"Command-hook
   Stop blocking spike (2026-05-18)") that Claude Code runtime honors
   `type: command` Stop hooks with `exit 2` and feeds stderr back as model
   continuation context.
3. **PR #10 dual review caught 4 Majors v0.7.7 deferred.** Bundling them here
   keeps the residual list closed rather than letting it grow.

### Added

- `scripts/hooks/stop_verify_claims.py` (replaces v0.7.7 spike no-op stub) —
  production Stop-hook gate script. Reads stdin (Stop event JSON), extracts
  `last_assistant_message`, checks `hooks.profile` (off → exit 0 silently;
  unknown → fail-open with stderr warning), checks emission sentinel
  anchored at response-start (skip on match), runs material-claim detection
  via English + Korean phrase whitelist ported verbatim from the v0.7.7
  prompt, exits 2 with stderr directing the model to invoke
  `verification-before-completion`.
- `skills/verification-before-completion/SKILL.md` §"Emission Sentinel" —
  required prefix `<!-- athanor:verification-emission v=1 -->` (HTML
  comment, invisible in rendered Markdown, anchored at first non-whitespace
  line). Hook script detects and exits 0 to prevent re-entry loops on the
  skill's own evidence output. Versioned (v=1) for forward compatibility.
- `tests/test_regression_stop_command_hook.py` (7 tests) — hooks.json
  registration contract (`type=command`, command field, script existence
  + executable bit, no leftover prompt-type hook).
- `tests/test_regression_stop_hook_script.py` (21 tests) — script decision
  flow with synthetic stdin (empty/unparseable, English + Korean material
  claims, sentinel anchoring including line-2-not-detected, version-tag
  forward-compat, profile=off opt-out, profile=standard engagement,
  unknown-profile fallback warning, missing athanor.json default,
  two-turn re-entry prevention).
- `docs/plans/2026-05-18-001-feat-v0.7.8-stop-hook-command-mode-plan.md`
  — full implementation plan covering U1-U12 with KTDs, risks, phased
  delivery, and rollback notes.

### Changed

- **M1 (re-promote)** — CLAUDE.md status table row and §Completion-Claim
  Verification subsection re-promoted from `advisory (prompt-based)` to
  `enforced (command-based)`. Subsection rewritten to describe the 5-step
  decision flow, cite the spike evidence, document the sentinel mechanism,
  and surface the `hooks.profile: "off"` per-project opt-out.
  `tests/test_regression_claude_md_honesty.py` retargeted: now asserts the
  v0.7.8 contract (enforced label, script path cited, sentinel mentioned,
  opt-out documented, spike cited). The v0.7.6 false phrase "Enforced at
  plugin layer" remains forbidden — that exact phrasing was a lie even
  though "enforced (command-based)" is now true.
- **C2 (configurable)** — `hooks.profile` is now consumed by the gate script.
  Schema enum tightened to `["off", "standard"]` (lenient/strict deferred
  per plan §10). `hooks._doc` rewritten to describe the working contract
  (cites the script, both profiles, fail-open on unknown values).
  `tests/test_regression_doc_string_honesty.py` split: `models._doc`
  retains the v0.7.7 DEPRECATED-lead invariant; `hooks._doc` switches to
  a working-contract invariant.
- **`hooks/hooks.json`** — Stop entry converted from `type: prompt`
  (v0.7.7) to `type: command` invoking
  `python3 scripts/hooks/stop_verify_claims.py`.
- **PR #10 review residuals** (4 Majors):
  - **U8** — `skills/plan/SKILL.md` Step 2 intro tier-aware (parallel to
    v0.7.7 Step 3/4 fix). "Dispatch TWO planners simultaneously" replaced
    with explicit Deep/Standard/Lite preamble.
  - **U9** — `skills/plan/SKILL.md` deep-tier 2-input Critic variant.
    Previous 4-input block silently malformed when `review_strategy=none`.
    New `#### Deep Tier: 2-Input Synthesis Critic (when review_strategy ==
    none)` subsection with concrete dispatch prompt reading only the two
    plans and prepending the review-skipped header.
  - **U10** — `skills/work/SKILL.md` detects `<!-- athanor:review-skipped -->`
    marker prepended to `plan.md` by U9 (and v0.7.7 standard-tier pass-
    through). Announces `⚠ Working from an unreviewed plan` advisory
    before proceeding.
  - **U11** — `skills/analyze/SKILL.md:301` residual "earlier today"
    prose replaced with canonical Session Lookup Convention reference.
    `tests/test_regression_session_lookup_convention.py` blocklist widened
    to catch `earlier today` and `user ran /athanor` paraphrases.
- **`docs/STATE.md`** — Current Phase header bumped to v0.7.8, Live
  invariants table updated (stop-hook-command-contract replaces
  stop-hook-liveness; schema/template/_doc/session-lookup contracts added),
  History section appended with v0.7.6 / v0.7.7 / v0.7.8 summaries (file
  had been frozen at v0.7.2).

### Removed

- `hooks.disabled[]` from `athanor.json` + `templates/athanor.json` +
  `schemas/athanor-config.schema.json`. The key was unread in v0.7.7
  (marked deprecated in schema) and is now formally gone.
- `tests/test_regression_stop_prompt.py` — its `type: prompt` invariant
  is obsolete after the v0.7.8 contract change. Replaced atomically by
  `tests/test_regression_stop_command_hook.py` in the same commit. The
  legacy fixture `tests/fixtures/fixture_wrong_stop_prompt.json` is
  preserved as historical regression evidence.

### Migration

- **For users who set `hooks.profile`** to a non-default value in v0.7.7:
  - `"off"` — fully honored in v0.7.8; the script exits 0 silently. Same
    semantic as "no Stop gate"; you keep your opt-out.
  - `"standard"` — fully honored; same as default. No action.
  - `"lenient"` or `"strict"` — these values had no effect in v0.7.7
    (orphan config). v0.7.8 logs a stderr warning at every Stop event:
    `unknown hooks.profile value '<X>'; treating as 'standard'`. To
    silence the warning, set the value to `"off"` or `"standard"`
    explicitly, or remove the field. The values themselves remain
    deferred per plan §10.
- **For users with `hooks.disabled` in their config**: the key was
  always orphan; v0.7.8 schema rejects it via `additionalProperties:
  false`. Remove the field from your `athanor.json`. CHANGELOG entry
  in v0.7.7 already flagged this as the deprecation target.
- **For workflows depending on the v0.7.7 prompt-mode hook**: the
  trigger surface (claim phrases) is identical between v0.7.7 prompt
  mode and v0.7.8 command mode — the script's whitelist is a verbatim
  port of the prompt's whitelist. Behavioral difference: v0.7.8 blocks
  Stop with exit 2 (vs. v0.7.7 nudging the model via prompt injection).
  Recoverable: invoke the verification skill (with the new emission
  sentinel) to satisfy the gate.

### CI

- `.github/workflows/validate-plugin.yml` unchanged from v0.7.7 (the
  hook-script behavior tests are pure-Python with synthetic stdin —
  fully portable on the existing ubuntu-latest + windows-latest matrix).

### Spike result reference

`docs/STATE.md` §"Command-hook Stop blocking spike (2026-05-18)" remains
the authoritative empirical record. v0.7.7 forward-referenced it; v0.7.8
fulfills the forward-reference. The spike entry now has a companion
v0.7.8-landed history note in the same file.

## [0.7.7] — 2026-05-18

**Truth-in-documentation release.** Discovered that several documented
surfaces did not match code; correcting transparently rather than letting
the gap widen. No new features — every change brings code and docs back
into agreement. Security-honesty framing: when "enforced" doesn't enforce
and "config keys" aren't read, the right move is to say so plainly.

Session: `2026-05-18-001` (full audit + adversarial planning + cross-review
artifacts under `.athanor/sessions/2026-05-18-001/`).

### Why this release

A two-perspective audit (Claude Explore + Codex independent review) of
the v0.7.6 plugin surface found a cluster of trust-eroding drift:

- `CLAUDE.md` Defense Mechanisms table labeled the Stop hook
  **enforced** when in fact it is a `type: prompt` injection — the
  model self-classifies; the plugin layer cannot force invocation.
- `athanor.json` `_doc` claimed `models` and `hooks.profile`/`disabled`
  are honored by skills/env-vars — grep confirmed zero readers anywhere.
- `$schema` URL pointed at `schemas/athanor-config.schema.json`, a path
  that did not exist in the repository.
- `/athanor:setup`'s inline config template carried ghost `debugger` /
  `debugger-tracer` model keys absent from the real `athanor.json` (the
  v0.7.6 C4 drift class).
- `skills/plan/SKILL.md` Step 3 prose presumed deep-tier ("After BOTH
  planners return") even when standard/lite tiers run; misled readers.
- `skills/work/SKILL.md` looked up "most recent today" while
  `skills/scope-drift/SKILL.md` used lexicographic max — a plan made
  at 23:45 was unreachable next morning by `/work`.
- `skills/plan/SKILL.md` Step 0 ignored `athanor.json codex.enabled`
  entirely (only probed `codex --version` CLI presence).

### Fixed

- **M1 (docs honesty)**: Stop hook in CLAUDE.md status table relabeled
  **advisory (prompt-based)**. The §Completion-Claim Verification
  subsection renamed and rewritten with an explicit **Limitation**
  paragraph (model self-classifies; plugin layer cannot force
  invocation). Forward-references v0.7.8 spike result (see Spike below).
- **M3 (codex.enabled config wired)**: `skills/plan/SKILL.md` Step 0
  now reads `athanor.json codex.enabled` via `jq` (with graceful
  jq-absence fallback to shipped defaults), AND-gates with
  `codex --version` CLI probe, and honors `codex.fallback`
  (self-critic / skip / fail) via a new `review_strategy` variable
  threaded through Planner B / Reviewer A / Reviewer B / Critic
  dispatch sites. `skills/discuss/SKILL.md` gets the same matrix
  threaded into its Researcher B branch.
- **M4 (session lookup canonicalized)**: New CLAUDE.md §Session
  Lookup Convention defines the rule (lexicographic max of
  `^\d{4}-\d{2}-\d{2}-\d{3}$` dirs, no "today" semantics, with
  stale-session announcement when LATEST date ≠ today). All 6
  session-touching skills (work, plan, discuss, analyze, debug,
  review) updated to reference the convention instead of restating
  inline.
- **M5 (plan tier prose corrected)**: `skills/plan/SKILL.md` Step 3
  and Step 4 intros rewritten tier-aware. Deep / Standard / Lite tier
  branching explicit; no more generic "After BOTH planners/reviewers
  return" preamble. Cross-multiplied with `review_strategy` so the
  prose accurately describes every combination.
- **C3 (broken $schema URL fixed)**: New
  `schemas/athanor-config.schema.json` (JSON Schema draft-07) ships
  with the release. `athanor.json` `$schema` URL re-pinned to the
  v0.7.7 release tag. The schema covers every key that is actually
  honored by code, and marks `models` (v0.7.9 deletion target) and
  `hooks.profile`/`hooks.disabled` (v0.7.8 deletion target) as
  `"deprecated": true`.
- **C4 (template extraction)**: New `templates/athanor.json` is the
  canonical default copied by `/athanor:setup`. The inline JSON block
  in `skills/setup/SKILL.md` is preserved as an embedded fallback
  (with a loud `⚠ template file not found` warning when fallback
  fires — packaging-regression safety). Ghost `debugger` /
  `debugger-tracer` keys removed from the template; the real
  `athanor.json` never had them.

### Added

- `schemas/athanor-config.schema.json` — first machine-readable config
  contract.
- `templates/athanor.json` — canonical default config copied at
  `/athanor:setup` time; byte-mirror of root with `_doc` fields preserved.
- `CLAUDE.md` §"Session Lookup Convention" — single canonical rule
  with Bash reference implementation.
- 9 new regression test files (41 tests) pinning every v0.7.7
  invariant: schema validation, schema URL version pin, template
  keyset match, no ghost keys, plugin manifest packaging, CLAUDE.md
  honesty, session lookup convention, plan-skill tier prose, and
  plan/discuss codex matrix.
- `tests/fixtures/fixture_athanor_invalid.json` — broken-config fixture
  for schema-validation negative test.
- `docs/STATE.md` §"Command-hook Stop blocking spike (2026-05-18)" —
  empirical evidence that v0.7.8 command-hook design is feasible.
- `scripts/hooks/stop_verify_claims.py` — no-op stub (v0.7.8 starting
  point; will be extended in v0.7.8 with real claim-classification +
  sentinel-detection logic).

### Deprecated

- `athanor.json` `models` block — `_doc` previously claimed skills
  read this for dispatch model selection; grep confirms no reader.
  Schema marks the block `"deprecated": true`. **v0.7.9 will remove
  the block entirely.** Migration: if you depended on the
  (non-functional) keys, fork the affected `skills/<name>/SKILL.md`
  and edit the inline `model:` fields.
- `athanor.json` `hooks.profile` and `hooks.disabled` — `_doc`
  previously claimed honoring via `ATHANOR_HOOK_PROFILE` /
  `ATHANOR_DISABLED_HOOKS` env vars; no reader exists.
  Schema marks both `"deprecated": true`. **v0.7.8 will replace
  these with real command-hook gating** (spike PASS — see below).

### Spike — Command-hook Stop blocking feasibility (PASS)

Per `.athanor/sessions/2026-05-18-001/plan.md` §SPIKE, this release was
gated on empirical verification that Claude Code runtime honors
`type: "command"` Stop hooks with `exit 2` blocking. Spike (2026-05-18)
PASSED on all four questions: hook executes, exit 0 → normal Stop, exit
2 → Stop blocked, stderr fed back as `Stop hook feedback: ...`
continuation context. Full result in `docs/STATE.md`. v0.7.8 will
upgrade the Stop hook from prompt-based to command-based using this
verified runtime contract.

### Resolved decisions

User-confirmed during planning (2026-05-18):

1. **Spike timing**: runs before v0.7.7 ships (M1 wording is
   forward-reference-aware: PASS path).
2. **CHANGELOG voice**: security-honesty correction (this entry).
3. **Template `_doc` fields**: kept (root parity; inline schema
   substitute until v0.8.0).
4. **Schema URL host**: pinned to release tag (`/v0.7.7/`), not
   `main` (no transient drift on releases).

### CI

- `.github/workflows/validate-plugin.yml` updated to install
  `jsonschema` alongside `pytest` for the regression-fixtures step.

## [0.7.6] — 2026-05-02

5-agent ref deep-dive + Codex cross-validation outcome (session
`2026-05-02-001`). Closes the most critical contract default
(missing `athanor.json`) and lands the highest-ROI quick-win from the
collective audit (confidence-anchored review findings, pattern from
compound-engineering ce-* persona reviewers).

### Why this release
The 5-parallel-agent ref mining audit identified ~80 upgrade candidates
across claudekit, superpowers, compound-engineering, gstack, GSD, ECC,
Octopus, ralph-wiggum, wshobson-agents, bmad-plugin, roboco-plugins,
and claude-code-templates. The highest-priority discovery was a
**contract default**: `athanor.json` is referenced from `CLAUDE.md`
line 53 and 116 ("project root, NOT inside .athanor/") and from
`docs/DESIGN.md` §Configuration as the source of truth for memory /
codex / work / team / triggers settings — but the file did not exist
in the repository. User installs of the plugin had no template to
copy from, and athanor's own development could not honor its
documented contract. v0.7.6 ships the missing file.

### Fixed
- **Critical contract default**: `athanor.json` now exists in the
  repository root with the documented schema. Includes inline `_doc:`
  fields for every section explaining what each setting controls,
  pulled from `docs/DESIGN.md` §Configuration and the working
  documentation in skills/. New `hooks` section reserves
  `profile: standard` and `disabled: []` for v0.7.7+ HOOK_PROFILE
  gating work (Researcher D #2 from the audit). New `review` section
  with `lenses: [...]` and `minConfidence: 25` to back the
  v0.7.6 reviewer confidence-rubric work below.
- `agents/cleaner.md` model dropped to `haiku` already in v0.7.3 —
  athanor.json now codifies that decision in the `models` block, so
  future drift is caught by the next run that reads `athanor.json`.

### Changed
- `agents/reviewer.md` §Process — added Step 5 "Confidence anchoring"
  with the 4-anchor rubric (100 mechanically constructible / 75
  traceable from code / 50 judgment-based / 25 speculative / <25
  suppress). Pattern adapted from compound-engineering's ce-* persona
  reviewer agents (julik / kieran / dhh / adversarial), where every
  finding carries an anchored confidence value to fight finding-flood
  fatigue. Severity (critical/high/medium/low) and confidence (0-100)
  are now orthogonal dimensions: severity = "how bad if true",
  confidence = "how sure I am it's true".
- `agents/reviewer.md` §Output Format — Critical/High/Medium/Low
  finding template now includes `confidence: {0-100}` next to the
  `file:line` reference. Findings with confidence < 25 must be
  suppressed at the worker level (do not surface in `ATHANOR_RESULT`).
- `skills/review/SKILL.md` Step 2 dispatch prompt — every Reviewer is
  instructed to attach a `confidence:` value (0-100) on the rubric,
  and to suppress findings below `min_confidence` (sourced from
  athanor.json `review.minConfidence`, default 25).
- `skills/review/SKILL.md` Step 3 consolidation — added a 2.5
  "Confidence-based suppression" rule. When the same `file:line`
  appears across multiple lenses, the consolidated finding's
  confidence is the **max** across lenses (not sum, not average —
  confidence is a max-evidence claim, not a democracy).

### Notes on the audit
The 5-agent + Codex audit will continue to ship in subsequent v0.7.7,
v0.7.8, v0.7.9, v0.8.0 releases per the priority matrix in the audit
session digest. v0.7.6 deliberately stays small (XS-S only, no infra
change, no new hook) so the full audit's larger work — HANDOFF.json /
PreCompact hook (Researcher A/C/D triple-vote), Stop-event Todo Gate
+ transcript-parser (Codex review #4 follow-up), Lessons-Refresh
(Researcher B), Lens-based plan review (Researcher C), File-Guard
(Researcher A) — can each get their own focused PR.

Audit artifact: `.athanor/sessions/2026-05-02-001/codex-hook-review.md`
+ codex-plan-critique + codex-memory-comparison (gitignored, local).

## [0.7.5] — 2026-05-02

Cross-model hook audit follow-up (Codex review session
`2026-05-02-001/codex-hook-review.md`). Closes the four highest-ROI
findings (Codex TOP 5 #1, #2, #3, #5) from a Codex CLI deep review of
Athanor's Stop hook architecture against six reference plugins
(claudekit, ralph-wiggum, GSD, ECC, superpowers, octopus).

### Why this release
The v0.7.2 narrowing reduced user-fatigue but introduced a documented
false-negative vector: "evidence already present in same turn"
self-rationalization, in which the model treats prior-turn or
earlier-in-same-turn tool output as evidence and skips fresh
verification. Codex review §2 traced this to a structural conflict
between the prompt's skip-list ("summaries of tool output you just
read") and material-list ("verification output"). v0.7.5 disambiguates
both sides and adds Korean-verb parity that the v0.7.2 narrowing did
not cover.

### Changed
- `hooks/hooks.json` Stop prompt — disambiguation pass:
  - Material-claim list expanded to include `files created/removed/
    renamed`, `lint/typecheck clean`, `builds succeeding`, `bug fixed`,
    `requirements met`, `agent task completed`. Previously these were
    in the verification skill body but not in the hook gate, creating
    whitelist drift.
  - Korean-verb parity added: `수정/반영/구현/완료/통과/성공/배포/생성/
    삭제/수행/적용했습니다`, `테스트 통과`, `빌드 성공`, `머지 완료`,
    `마이그레이션 완료`, `배포됨` flagged as material when describing
    repo/tests/build/release/migration/deployment/verification state.
    Closes Codex review §3 (self-classification ambiguity for Korean
    final responses).
  - Tool-output skip carve-out tightened: skippable summaries are
    those that "describe what the tool printed" only. Summaries that
    claim `tests pass`, `build succeeded`, `files changed`, `merged`,
    `통과/성공/완료/배포`, or `verification confirmed` remain material.
    Closes the false-negative vector in Codex review §1+§2.
  - Fresh-evidence requirement made explicit: evidence must be IN THIS
    RESPONSE; references to prior turns or earlier-in-same-turn tool
    output do NOT satisfy the gate. Closes the rationalization
    documented in this session's transcript.
- `CLAUDE.md` §Defense Mechanisms — added Status table at the top
  of the section. Each mechanism marked `enforced` (Stop hook only) /
  `advisory` (stop-phrase, read-before-edit) / `on-demand` (scope-drift).
  Closes Codex review §10 expectation-mismatch concern. Read-Before-Edit
  rule clarified that Claude Code runtime auto-enforces it on Claude
  workers, so the rule applies primarily to Codex/non-Claude dispatches.

### Added
- `tests/test_regression_stop_prompt.py` — 5 new semantic fixture tests
  (Codex review TOP 5 #3) that lock the v0.7.5 contract:
  - `test_prompt_lists_expanded_material_categories` — whitelist parity
    enforced (builds/files/lint/bug fixed/requirements met present)
  - `test_prompt_marks_korean_success_verbs_as_material` — Korean
    parity enforced (수정/통과/성공/배포/완료 listed)
  - `test_prompt_disambiguates_tool_output_summary_from_status_claim`
    — skip-list/material-list conflict resolution locked in
  - `test_prompt_requires_fresh_evidence_in_this_response` —
    rationalization closure verified
  - `test_prompt_length_within_cognitive_budget` — prompt ≤ 2500 chars,
    crossing the limit signals it is time to migrate to type=command
    + transcript-parser (Codex TOP 5 #4, deferred)
- pytest count: 31 → 36 (+5 new semantic cases). Total runtime ≈ 0.25s.

### Deferred to v0.7.6+
- Codex TOP 5 #4: `type=prompt` → `type=command` + transcript-parser
  migration. Listed as M-difficulty in the review and requires a
  polyglot wrapper (Windows-first), transcript JSONL parser, and a
  loop-guard. v0.7.5's prompt is now within cognitive budget (verified
  by `test_prompt_length_within_cognitive_budget`); migration is the
  next-natural step but a larger PR.

## [0.7.4] — 2026-05-02

5-agent audit Tier-3 follow-up (item H): adds the missing self-review
step to the Athanor pipeline. Stacked on top of v0.7.3.

### Added
- `agents/reviewer.md` — new `athanor-reviewer` worker. Single-lens
  review per dispatch (one of: architecture, quality, security,
  performance, testing, documentation). `model: opus`. Read-only —
  never edits files.
- `skills/review/SKILL.md` — new `/athanor:review` skill, user-invocable.
  Trigger keywords (Korean + English): "리뷰", "review", "코드 리뷰",
  "코드리뷰", "리뷰해줘", "code review", "PR 리뷰", "변경 점검",
  "다각도 리뷰". Pipeline:
  1. Session setup (reuses `.athanor/sessions/{id}/` convention).
  2. Scope detection — three modes: (a) default = recent changes on
     branch via `git diff --stat`, (b) explicit path/glob, (c) PR mode
     via `gh pr diff` with `git fetch pull/<num>/head` fallback.
  3. File-type filter — claudekit pattern. Source code gets all 6
     lenses; doc-only gets just documentation; test-only gets testing
     + quality; config-only gets security + architecture; mixed = union.
  4. **Parallel dispatch** — one Reviewer per lens, single Task batch.
  5. Worker Output Defense — same stop-phrase + format check as the
     other plan-mode skills (v0.7.3 propagation).
  6. Consolidate — Leader writes `review.md` grouped by severity
     (Critical → High → Medium → Low), deduplicated across lenses,
     with cross-lens flag promotion and a 6-row score table.
  7. User confirmation — point at the report file, do not auto-fix.
- `CLAUDE.md` Commands table and `README.md` headline updated:
  "9 commands. ... 6-lens parallel review. ..." (was "8 commands").

### Notes on the design
- Pattern adapted from `ref/claudekit/src/commands/code-review.md`
  (6-lens parallel `code-review-expert` agent dispatch). Athanor uses
  a single `athanor-reviewer` agent with a `lens:` mode parameter
  rather than 6 distinct agents — keeps the agent inventory at 8 (was
  7) instead of 13. compound-engineering's 20+ ce-*-reviewer agents
  were rejected as too heavyweight for athanor's "8 commands" promise.
- `work.autoReview` config flag is reserved as a contract slot in this
  release (NOT enabled by default). Future release may auto-trigger
  `/athanor:review` from `/athanor:work` Step 6.
- v0.7.3's `agent_descriptions_unique_check` regression already covers
  the new agent — its description prefix was crafted to differ from the
  existing 7 agents by the first 60 chars (verified by green pytest).

### Verified
- `pytest tests/ -v` → 31 passed (no new tests added in v0.7.4 — the
  v0.7.3 lint regression suite already locks the new agent's
  description-prefix-uniqueness contract).
- `python scripts/check_release_ready.py --ci` → green at v0.7.4.
- `python -m scripts.gates.lint_checks agent-descriptions agents` →
  ok (8 files).

## [0.7.3] — 2026-05-02

5-agent parallel audit (T2/T3 of session `2026-05-02-001`). Fixes
doc-drift, agent-frontmatter contradictions, mojibake, and adds five
new lint guards + Windows CI matrix to close audit gaps that the v0.7.x
regression suite did not cover.

### Fixed
- `agents/critic.md` Plan Synthesis input — stale `plan-claude.md` /
  `plan-codex.md` / `review-of-claude.md` / `review-of-codex.md` paths
  (left over from v0.5.0 file-name neutralization) corrected to
  `plan-a.md` / `plan-b.md` / `review-of-a.md` / `review-of-b.md` with
  deep-tier-only annotation. Manual `@athanor-critic` invocation no
  longer fails on missing files.
- `agents/learner.md` lesson template — added `contract-id`, `date`,
  and `version-at-time-of-lesson` fields required by
  `agents/cleaner.md` §Schema-Validation. New lessons created on or
  after 2026-04-17 will no longer be flagged for deletion by the next
  Cleaner run (self-cancelling-loop closed).
- `skills/work/SKILL.md` stop-phrase check — added missing 5th pattern
  ("좋은 체크포인트" / "Good checkpoint") and English aliases on the
  other 4 patterns. CLAUDE.md §Defense Mechanisms and the work skill
  now match exactly.
- `skills/scope-drift/SKILL.md` self-reference exclusion — fictitious
  example paths (`.athanor/CLAUDE.md`, `.athanor/plugin.json`,
  `athanor/skills/**`) replaced with the real project layout
  (`CLAUDE.md`, `.claude-plugin/plugin.json`, `skills/**`,
  `agents/**`, `hooks/**`, `scripts/**`, `tests/**`, `docs/**`).
- `docs/STATE.md` — frozen at "v0.1.0" since 2026-04-08. Synced to
  current SHIPPING/v0.7.2 baseline plus a Live invariants table and
  Known gaps section pointing at the items that this and future
  releases will close.
- UTF-8 mojibake — 4 occurrences in `docs/DESIGN.md` (`기능�� 많이`,
  `(���)`, `���고 �����하기`) and `skills/analyze/SKILL.md` (`스���트
  트레��스`) repaired to legible Korean.

### Changed
- `agents/*.md` × 7 — `description:` frontmatter rewritten from the
  contradictory "Standalone manual assistant for X. Invoke directly via
  @-mention for independent use." pattern to "{specialization}.
  Dispatched by Athanor skills via inline prompt; also available
  standalone via @-mention." Aligns with the explicit Note ("Skills
  dispatch workers using inline prompts, not this file directly")
  already in the body.
- `skills/*/SKILL.md` × 10 — added `allowed-tools` frontmatter field
  (per-skill minimum tool set: `Bash, Read, Grep, Glob, Task` for
  analyze/debug; `+Write` for plan-tier and discuss; `+Edit` for work;
  `Bash, Read` for verification-before-completion; `Bash, Read, Glob,
  Grep` for scope-drift). Reduces permission-prompt frequency during
  worker dispatch, mirrors gstack/superpowers convention.
- Model mapping converged onto a single source of truth across
  `agents/cleaner.md` (sonnet→haiku), `docs/DESIGN.md` (executor: sonnet
  →opus, two locations), `skills/setup/SKILL.md` athanor.json template
  (cleaner: sonnet→haiku), and `README.md` (executor: sonnet→opus). All
  five locations now agree: planner=critic=opus, executor=opus,
  researcher=analyst=learner=sonnet, cleaner=haiku.
- `skills/setup/SKILL.md` Check #11 (contract-ledger) — fast-path INFO
  branch added. `.athanor/sessions/` is gitignored, so user-install
  fresh checkouts started every first `/athanor:setup` with a red X.
  Now reports `PASS (info)` with a hint that contract-ledger is
  enforced at release-tag time, not at setup. Existing release gate
  (`scripts/check_release_ready.py`) remains the authoritative
  enforcement point.
- Stop-phrase enforcement extended from `skills/work/SKILL.md` (where
  it lived alone) into `skills/{discuss,analyze,debug}/SKILL.md` as a
  new "Step 2.5: Worker Output Defense" section, and into
  `skills/plan/SKILL.md` as a Protocol-level "Worker Output Defense"
  section that covers Planner A, Planner B, both Reviewers, and the
  Critic. `lite-plan` and `deep-plan` inherit via the shared Protocol.
  All five plan-mode skills now grep worker output for the same five
  stop-phrase patterns and re-dispatch on hit.
- CI workflow `.github/workflows/validate-plugin.yml` now runs on
  `[ubuntu-latest, windows-latest]` matrix. `claude plugin validate`
  is conditionally Linux-only (CLI install path differs); JSON-syntax,
  release gate, and pytest run on both OSes. Closes the v0.7.1 follow-
  up "Path.resolve() vs os.path.abspath" class of regression: it can
  now be detected on PR.

### Added
- `scripts/gates/lint_checks.py` — five new frontmatter/manifest guard
  functions plus a CLI dispatcher:
  - `marketplace_version_sync_check` — `plugin.json.version ==
    marketplace.json.plugins[0].version`
  - `agent_descriptions_unique_check` — agents/*.md description
    first-60-char prefix uniqueness (closes v0.6.2 Codex dispatch
    collision class — previously had **zero** regression coverage)
  - `hook_events_known_check` — hooks.json event keys against
    Claude-Code-2026-05 whitelist (24 known events)
  - `hook_items_well_formed_check` — type→required-field mapping
    (`command`→`command`, `prompt`→`prompt`, `http`→`url`,
    `mcp_tool`→`tool`, `agent`→`agent`)
  - `vendored_skill_provenance_check` — vendored SKILL.md must carry
    `<!-- Provenance:` block within first 60 lines of body
  - CLI: `python -m scripts.gates.lint_checks {marketplace-sync,agent-
    descriptions,hook-events,hook-items,skill-provenance} ...`
- `tests/test_regression_lint_checks.py` (13 cases) + 5 fixtures under
  `tests/fixtures/`:
  - `fixture_marketplace_version_drift.json` (plugins[0].version=0.7.0
    vs plugin.json=0.7.3)
  - `fixture_agent_description_collision.md` (analyst-prefix collision)
  - `fixture_hook_unknown_event.json` (`Stoped` typo)
  - `fixture_hook_command_missing_command.json` (type=command without
    `command` field)
  - `fixture_skill_missing_provenance.md` (vendored skill without
    Provenance comment)
- pytest count: 18 → 31 (added 13 new cases). Total runtime ≈ 0.18s.

## [0.7.2] — 2026-04-24

### Changed
- Stop hook: narrow completion-claim trigger to material claims (edits/tests/releases/migrations/deployments/verification-output); explicitly skip analysis, planning, opinions, research Q&A, and tool-output summaries.
  - Previously fired on any "completion/success/done" claim, producing user-fatigue events on research Q&A turns (see `.athanor/sessions/2026-04-24-001/replay.md` — 5/5 fires in that session would skip under new prompt).
  - Infra cascade preserved: 5 regression tests pass, 3 active contracts (`stop-hook-liveness`, `hook-uniqueness`, `manifest-no-hooks-field`) unaffected, CLAUDE.md §Defense Mechanisms synced.
  - Session: 2026-04-24-001

### Added
- `tests/fixtures/fixture_narrowed_stop_prompt.json` — positive-test fixture for narrowed gating markers.
- `tests/test_regression_stop_prompt.py` gained `test_current_hooks_contains_narrowed_gating_markers()` — asserts both `material` and `Explicitly skip` substrings are present in the shipped Stop prompt. Prevents future silent re-broadening.

## [0.7.1] — 2026-04-18

PR #3 adversarial-review follow-up fixes. Closes the three concrete bypass/divergence vectors surfaced after v0.7.0 merge (Check #9 substring-grep defect, 3-way duplicate-hooks mirror, `check_a_evidence` missing THIS-run linkage) with the stronger forms (structural over substring, `Path.resolve()` over `os.path.abspath`, graceful degradation over hard-dep). Session `2026-04-17-002`.

### Changed
- `check_a_evidence` now requires the latest session's `work-log.md` to contain a `## v<version>` section header matching the current `plugin.json` version. Pure-prose mentions no longer satisfy the gate (regex `^##\s*v?{VERSION}\b` is word-boundary-terminated).
  **Migration**: local-dev users running `scripts/check_release_ready.py` on a fresh checkout must add a `## v<version>` section to the latest session's `work-log.md` OR pass `--session <id>` pointing at an older session that already has the expected header.
- New `--session <id>` CLI flag on `scripts/check_release_ready.py` for pinning an alternate session. Missing session dir produces a clean stderr message + exit 2 (no Python traceback).
- `scripts/` is now a Python package (`scripts/__init__.py`, `scripts/gates/__init__.py`) — required for the shared-module consolidation below.

### Fixed
- Check #9 (hook-uniqueness) was a substring-grep that missed 2-entries-in-Stop arrays. Now uses a structural check via a jq → python → warning graceful-degradation ladder in `/athanor:setup`; CI exercises the structural path via pytest.
- Duplicate-hooks check had three mirrored implementations (CI inline, pytest, release gate) with divergent canonical-path forms. Consolidated onto `scripts/gates/manifest_checks.py::duplicate_hooks_path_check`; CI inline block removed (audit pointer preserved as YAML comment).
- Canonical-path form converged onto `Path.resolve()` (was split between `os.path.abspath` and `Path.resolve()`); closes the case-insensitive-filesystem (macOS/Windows) divergence vector.

### Added
- `scripts/gates/manifest_checks.py` with `duplicate_hooks_path_check`, `hook_uniqueness_check`, and a `__main__` CLI dispatcher (`python -m scripts.gates.manifest_checks {uniqueness,duplicate-hooks}`).
- `tests/test_regression_hook_uniqueness.py` (4 cases: duplicate fixture fails, current hooks.json passes, malformed JSON fails clean, missing file fails clean).
- `tests/test_regression_check_a_version_binding.py` (7 cases: positive header match, positive no-v-prefix, negative substring `v10.7.1`, negative dot-extension `0.7.10`, negative prose mention, missing file, `--session` error-path subprocess test).

## [0.7.0] — 2026-04-17

Contract-first audit + executable regression defense. 28-subtask `/athanor:work --team` session closing 11 contracts (6 audit findings + 3 regression RCA entries, session `2026-04-17-001`).

### Added
- `CHANGELOG.md` bootstrapped with all 15 historical tags (Subtask 26)
- `scripts/check_release_ready.py` — cross-platform Python release gate that writes `live-session-evidence.md` (Subtask 21)
- 3 regression pytest fixtures under `tests/fixtures/` + `tests/test_regression_*.py` covering duplicate `hooks` in manifest, Stop-hook prompt shape, and manifest `hooks` reference invariants (Subtasks 22/23/24)
- `/athanor:setup` self-audit checks 7–11 enforcing vendoring-gate + regression invariants (Subtasks 17/25)
- `agents/cleaner.md` §Schema-Validation rules for lessons files (Subtask 20)
- `agents/learner.md` §"On Release" checklist (Subtask 19)
- `docs/DESIGN.md` §Agent Registration section (Subtask 15)
- 3 retrospective lessons in `.athanor/lessons/` citing contract-ids (Subtask 27) _(local-only; `.athanor/` is gitignored)_
- Contract ledger with 11 contracts at `.athanor/sessions/2026-04-17-001/contract-ledger.md` (Subtask 10) _(local-only; `.athanor/` is gitignored)_
- Regression RCA for v0.6.2/v0.6.3/v0.6.4 at `.athanor/sessions/2026-04-17-001/regression-rca.md` (Subtask 8) _(local-only; `.athanor/` is gitignored)_

### Changed
- `skills/work/SKILL.md` documents `thin-leader-rejection:bullet-1` exception for reading `athanor.json` (Subtask 16)
- `skills/scope-drift/SKILL.md` adds provenance line + upstream-drift-note (freeze-and-document) (Subtask 18)

### Fixed
- (none new beyond v0.6.4)

## [0.6.4] — 2026-04-17
### Fixed
- CI harden: `validate-plugin` gate strengthened, duplicate-hooks path check added, live-load evidence enforced via standardized template (#2)

## [0.6.3] — 2026-04-17
### Fixed
- Remove duplicate `hooks` reference from `plugin.json` manifest — resolves "Duplicate hooks file detected" load failure (#1)

## [0.6.2] — 2026-04-16
### Fixed
- Deconflict agent descriptions to prevent Codex dispatch collision in `/athanor:deep-plan`

## [0.6.1] — 2026-04-16
### Fixed
- Correct `hooks.json` prompt-type field
- Clean up marketplace manifest

## [0.6.0] — 2026-04-15
### Added
- `scope-drift` skill
- `/athanor:setup` auditor
- Dependency tier policy (T0/T1/T2)

## [0.5.0] — 2026-04-14
### Added
- `verification-before-completion` Stop hook (Pilot PR1a)
- `ultrathink` keyword propagation to all opus worker prompts
- `debug` skill and 3-tier plan structure (deep / standard / lite)
- Real Codex CLI integration

### Changed
- Move `task-splitter` from `/athanor:plan` to `/athanor:work` Step 0.5
- Rename skills to drop `athanor-` prefix; update `CONVENTIONS.md` and README accordingly

> Note: no v0.5.x patch releases shipped; an interim `v0.4.6` version bump (commit `72a6347`) was rolled into v0.5.0 without a separate tag — v0.5.0 → v0.6.0 direct.

## [0.4.3] — 2026-04-09
### Changed
- `/athanor:plan` output now shows full plan plus detailed subtasks

## [0.4.2] — 2026-04-09
### Fixed
- Prefix skill names with `athanor-` for clearer slash-command autocomplete

## [0.4.1] — 2026-04-09
### Changed
- Upgrade executor agent to Opus, cleaner agent to Sonnet

## [0.4.0] — 2026-04-09
### Fixed
- Rename skills to avoid built-in command conflicts

## [0.3.1] — 2026-04-08
### Removed
- Drop redundant `athanor.json.template`

## [0.3.0] — 2026-04-08
### Added
- `marketplace.json` for plugin marketplace registration

### Changed
- README rewrite — value-first structure derived from reference analysis
- Document correct in-session `/plugin marketplace add` install flow

### Fixed
- Deconflict skill triggers — remove bare English words
- Correct README install instructions, researcher role description, and session-file paths

## [0.2.0] — 2026-04-08
### Fixed
- 2nd audit: 10 issues resolved (3 critical, 7 medium)
- 3rd audit: 9 remaining issues resolved (6 medium, 3 low)

## [0.1.1] — 2026-04-08
### Fixed
- Comprehensive 1st audit: 24 issues resolved across all files

## [0.1.0] — 2026-04-08
### Added
- Initial release with Thin Leader pattern
- Phase 1: `/athanor:setup` with thin-leader dispatch
- Phase 2: dispatch conventions and smoke test
- Phase 3: `/athanor:discuss` with parallel research + critic synthesis
- Phase 4: `/athanor:analyze` with parallel workers + leader merge
- Phase 5: `/athanor:plan` cross-model adversarial planning
- Phase 6: `/athanor:work --solo` execution engine
- Phase 7: `/athanor:work --team` with wave-based parallel execution
- Phase 8: learning & memory decay system
- Phase 9: learner agent and state tracking; plugin manifest under `.claude-plugin/`
