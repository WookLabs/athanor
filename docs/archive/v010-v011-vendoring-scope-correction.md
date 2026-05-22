---
title: "v0.10–v0.11 Vendoring Scope Correction — Honesty Ledger"
type: archive
status: ledger
date: 2026-05-22
release_window: v0.10.0 → v0.11.7 (seven release cycles, 2026-05-19 → 2026-05-22)
pivot_release: v0.12.0 (Concept Absorption Pivot)
authority: `.athanor/sessions/2026-05-22-001/decisions.md` (D1, D7, D10, D11)
plan_of_record: `.athanor/sessions/2026-05-22-001/plan.md`
---

# v0.10–v0.11 Vendoring Scope Correction — Honesty Ledger

## Purpose

This document is the Phase 0 ledger required by the v0.12.0 Concept
Absorption Pivot plan (`.athanor/sessions/2026-05-22-001/plan.md`).
Per decision D1 it is written **before any code or surface deletion**.
Per decision D7 it uses explicit attribution voice; per decisions D10
and D11 it records what survives the pivot intact.

The framing is single-sentence and recurs throughout the ledger:

> **The work was real; the product surface was wrong.**

The work — Stop hook hardening, drift scanner, sentinel binding, plugin
deployment fix, doc invariants — solved real bugs. The product surface
on which that work shipped — 32 `ce-*` skills, 13 `sp-*` skills, and 49
vendored sub-agents all promoted to user-invocable `/athanor:ce-*` and
`/athanor:sp-*` commands — was wrong relative to the user's
concept-absorption intent.

## The v0.10.0 misread

**v0.10.0 plan-of-record misread the user's concept-absorption intent
as wholesale plugin vendoring.**

The user's original v0.10.0 ask was concept absorption: lift the
multi-persona reviewer pattern from compound-engineering, lift the
debugging discipline (Iron Law, Four Phases) from CE, formalize the
requirements-capture R/A/F/AE-IDs template (already partially absorbed
at v0.9.0), and adopt the skill-discovery preamble pattern from
superpowers. Four concepts. The target was athanor's 10 native Thin
Leader skills.

The v0.10.0 plan-of-record instead vendored:

- 32 `ce-*` skills exposed as user-invocable `/athanor:ce-<name>` commands
- 13 `sp-*` skills exposed as user-invocable `/athanor:sp-<name>` commands
- 49 vendored CE sub-agents under `agents/vendored/ce/*.agent.md`
- A "Vendored Surface — Identity Guard Layer" section in `CLAUDE.md`
  defending four athanor identity commitments against the inflated surface

Aggregate vendored surface: **94 items**.

The user never asked for `/athanor:ce-test-xcode`,
`/athanor:ce-dhh-rails-style`, `/athanor:ce-figma-design-sync`,
`/athanor:ce-gemini-imagegen`, `/athanor:ce-frontend-design`,
`/athanor:ce-strategy`, `/athanor:ce-proof`, `/athanor:ce-slack-research`,
`/athanor:ce-riffrec-feedback-analysis`, or `/athanor:ce-product-pulse`
as athanor commands. The wholesale vendoring was a plan-of-record
misread of "concept absorption" as "namespace absorption."

Attribution is to the v0.10.0 plan-of-record misread itself — not to
ambient process, not to a scope debate, not to evolving requirements.
Seven release cycles (v0.10.0 → v0.11.7) shipped on the wrong premise.

## v0.10.0 → v0.10.3 — vendoring fold and Stop hook hardening

### v0.10.0 (2026-05-19) — the over-scope shipment

Vendored absorption of compound-engineering 3.8.3 + superpowers 5.1.0
under the athanor namespace. 267 vendored files across a 6-phase
delivery. Every vendored markdown file carries a T2 provenance block
recording upstream version, source-commit reference, license, and
modifications. Body content byte-identical to upstream.

Identity guard layer added to `CLAUDE.md`: Thin Leader contract +
cross-model adversarial planning + Spec-then-TDD discipline + Stop hook
runtime gate scope, defended by guard prose against the inflated
surface. NOTICE.md expanded with full MIT attribution.

This is the release the v0.12.0 pivot corrects.

### v0.10.1 (2026-05-19) — vendor hygiene

Vendored-surface inventory tooling and post-vendor cleanup. Plan:
`docs/plans/2026-05-19-004-feat-v0.10.1-vendor-hygiene-plan.md`. The
hygiene work itself was honest — the surface it cleaned was the wrong
surface.

### v0.10.2 (2026-05-19) — Stop hook paraphrase + NFKC + Cyrillic + vendor-aware whitelist (A2 closure)

Stop hook detection extended to close the A2 vendor-aware bypass:

- **Paraphrase regex layer** — six verb-anchored patterns covering
  "CI is green / build is healthy / 테스트가 다 통과 / etc." paraphrase
  forms of the v0.7.7 whitelist phrases.
- **NFKC normalization + Cyrillic confusables fold** — 17-character
  Latin↔Cyrillic homoglyph table normalized before whitelist match.
- **Vendor-aware whitelist extension** — 18 idioms emitted by vendored
  CE and superpowers skills added to the trigger set (`review complete`,
  `<promise>DONE</promise>`, `all checks passing`, `branch merged`,
  `리뷰 완료`, etc.).

Per decision D11 the v0.10.2 detection layers are preserved into
v0.12.0. The original motivation (vendored skill output coverage) no
longer applies post-v0.12.0 atomic cut, but the detection utility
persists as general defensive coverage — paraphrase forms, Cyrillic
homoglyphs, and the 18 idioms are not exclusive to vendored prose
origin.

### v0.10.3 (2026-05-19) — Stop hook residual closure (Greek/Armenian + conditional + attribution)

Three residual-closure layers:

- **Greek + Armenian confusables fold** extending the v0.10.2 Cyrillic
  table to two additional script families.
- **Conditional / speculative clause-prefix suppression** — "If all
  tests are green, merge" no longer triggers.
- **Attribution / paired-quote / attributed-verb suppression** —
  historical quotes such as `the v0.7.6 docs said "tests pass"` no
  longer trigger; sentence-level attributed-history detection
  originally promised in v0.8.0+ ships here in v0.10.3 R3.

Preserved into v0.12.0 per D11.

## v0.11.0 → v0.11.2 — boundary advisory and first hygiene cut

### v0.11.0 (2026-05-19) — `/athanor:lfg` athanor-native wrapper

Standalone end-to-end pipeline command. Wraps the LFG flow through
athanor-native commands at identity-bearing steps: Step 1 invokes
`/athanor:plan` (cross-model adversarial) instead of CE's single-agent
flow; Step 2 invokes `/athanor:work` (Spec-then-TDD); Step 3 invokes
`/athanor:review` (6-lens). The rest of the step shape is reused from
vendored `ce-lfg`. Coexists with `/athanor:ce-lfg`.

The `/athanor:lfg` wrapper survives the v0.12.0 cut as athanor identity
#3-adjacent. The vendored `/athanor:ce-lfg` is full DROP per decision D9
after the v0.11.8 deprecation warning cycle.

### v0.11.1 (2026-05-20) — using-superpowers boundary advisory

The vendored `superpowers:using-superpowers` skill body declares
"ABSOLUTELY MUST invoke before response" / "1% chance → MUST use it"
voice. Inside athanor-native skill context (the 10 Thin Leader skills:
analyze, debug, deep-plan, discuss, lfg, lite-plan, plan, review, setup,
work), discovery is resolved by leader dispatch — pre-response
invocation check is advisory only. The boundary is declared verbatim
in each of the 10 skill §Identity sections and regression-locked in
`tests/test_regression_v011_1_using_superpowers_boundary.py`.

The boundary advisory itself is a concept-absorption pattern — formalize
into the v0.12.0 `concepts/` inventory rather than carrying both the
guard prose and the vendored skill body forward.

### v0.11.2 (2026-05-20) — first hygiene cut (4 CE-plugin-lifecycle skills)

Removed 4 vendored CE skills whose function was specific to CE's own
plugin lifecycle, not portable to athanor's plugin context:

- `ce-update` — CE plugin self-update workflow
- `ce-report-bug` — CE bug-report routing
- `ce-release-notes` — CE release-notes generation tied to CE repo
- `ce-setup` — CE plugin initial setup

Pre-cut surface was 36 CE skills; post-cut is 32 CE skills (Plan A's
later claim of 33 was stale by one cycle). This is the precedent for
the v0.12.0 atomic cut — the same posture, broader scope.

## v0.11.3 → v0.11.7 — companion-fix arc (5 layers)

Five consecutive releases each closed one bug in the same latent arc:
the Stop hook + the documentation surfaces describing it. Each layer
is named below per decision D10 — the companion-fix arc preserves
intact across the v0.12.0 pivot, and the regression tests survive.

The shared meta-cause across all 5 layers: documentation surfaces grow
drift faster than tests cover them; manual verification only inside
athanor's own source repo masked deployment-path bugs and
input-shape bugs simultaneously.

### v0.11.3 (2026-05-21) — Stop hook input-layer fix (transcript_path parser)

For 5 release cycles (v0.7.8 → v0.11.2 inclusive) the Stop hook
script's stdin parser assumed `last_assistant_message: <string>` in the
event payload. Claude Code actually sends `transcript_path: <jsonl-path>`
and the message lives inside that file. Every Stop event silently
fail-opened with `exit 0` and stderr `"last_assistant_message missing
or non-string"`. The 35+ existing regression tests used the same
incorrect assumed payload shape, so they passed while production
fail-opened.

v0.11.3 introduces `_read_last_assistant_message()` and
`_content_to_text()`. The parser accepts BOTH the legacy shape
(preserves the 35+ existing tests as backwards-compat lock) AND the
real Claude Code shape (`transcript_path` → JSONL → reverse-scan to
the first main-session `entry.type == "assistant"` with `isSidechain
!= true` → join `text` blocks). Sub-agent assistant turns skipped so
only the main-session model response gates.

`tests/test_regression_v011_3_stop_hook_input_layer.py` adds 25
mandatory + 1 xfail-tolerant tests against the real Claude Code
payload shape.

**Bug class:** script wrong.

### v0.11.4 (2026-05-21) — Stop hook plugin-root path fix (${CLAUDE_PLUGIN_ROOT})

The v0.11.3 input-layer fix was correct in code but only reachable when
Claude Code resolved the hook command relative to athanor's own source
repo. The hook command in `hooks/hooks.json` was registered with a
bare relative path (`python3 scripts/hooks/stop_verify_claims.py`)
which Claude Code resolves relative to the user's PROJECT cwd, not the
plugin install dir. For any user with athanor installed user-scope but
working in another project, Claude Code failed to find the script and
treated the missing-script stderr as "hook script missing" —
non-blocking. The gate was silently absent in every project except
athanor's source repo from v0.7.8 through v0.11.3 inclusive.

v0.11.4 closes the deployment-path arc with
`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/hooks/stop_verify_claims.py"`.
The env var `${CLAUDE_PLUGIN_ROOT}` is set by Claude Code for plugin
hooks and expands to the plugin install path. Matches the industry
pattern used by `superpowers`, `claude-mem`, and `openai-codex` plugin
hook registrations.

`tests/test_regression_stop_command_hook.py::test_stop_hook_command_uses_plugin_root_or_absolute_path`
locks the invariant — bare relative paths in the Stop hook command
string fail this test post-v0.11.4.

**Bug class:** path wrong. Companion-fix to v0.11.3 (same latent bug
arc; manual testing only inside athanor's source repo hid both bugs
simultaneously).

### v0.11.5 (2026-05-21) — CLAUDE.md doc-drift hardening (10 Thin Leader update + invariant tests)

`CLAUDE.md` is the authoritative project description and the source the
leader and worker dispatches reference. v0.11.5 ships drift-class
invariants:

- 10 Thin Leader skill list refresh covering the post-v0.11.0
  `/athanor:lfg` addition.
- `tests/test_regression_v011_5_*` invariant tests locking
  CLAUDE.md§-section claims against runtime configuration (the
  Stop hook command string, the `hooks.profile` opt-out value, the
  10-skill enumeration, the `${CLAUDE_PLUGIN_ROOT}` reference shape).

`scripts/hooks/__init__.py` package marker ships in this release so the
hooks directory is importable; the import-path invariant is regression-
locked.

**Bug class:** Markdown narrative claims untestable against runtime
state. v0.11.5 widens the testable surface.

### v0.11.6 (2026-05-21) — Sentinel body-hash binding fix (trailing-whitespace normalization)

The verification-before-completion skill prefixes its responses with
a sentinel `<!-- athanor:verification-emission v=2 nonce=<32-hex> -->`
to prevent Stop hook re-entry on the skill's own evidence emission.
v0.11.6 binds the sentinel to a body hash so a stripped-or-replayed
sentinel cannot bypass detection on subsequent turns.

The trailing-whitespace round-trip mismatch — when Claude Code's
transcript log normalizes trailing whitespace differently than the
emission path computed — caused legitimate verification emissions to
fail the body-hash check. Fix: normalize trailing whitespace
consistently in both hash-compute and hash-verify paths.

The v0.11.6 release introduced a reclassification pattern for previously
anonymous "Residual known limitations" entries: each carry slot gets
explicit Severity / Target / Acceptance labels rather than open-ended
candidacy.

**Bug class:** trailing-whitespace round-trip mismatch in sentinel
binding.

### v0.11.7 (2026-05-22) — Scanner extension + Residual reclassification + B1 detection

Three companion fixes in one release:

- **Doc-drift scanner extension** — v0.11.5 shipped CLAUDE.md
  drift-class invariants but the scanner was scoped only to Markdown
  narrative. Python docstrings (notably
  `scripts/hooks/stop_verify_claims.py`) and `docs/STATE.md` carried
  the same prose-vs-code drift pattern outside the v0.11.5 net.
  v0.11.7 extends the scanner via `ast.get_docstring` + per-file
  extractors.
- **Residual reclassification** — applies the v0.11.6 reclassification
  pattern more broadly. B2 (`stop_verify_claims.py:145` stale "v0.11.0+"
  pin) and B5 (`CLAUDE.md:229` stale "v0.8.0+ work" phrasing) carry
  text removed. B6 (`CLAUDE.md:87` carried as anonymous candidate)
  reclassified as documented broken promise with explicit "promised in
  v0.8.0 release notes but never implemented" honesty wording.
- **B1 minimal detection layer** — per Codex Reviewer push,
  mid-session profile mutation now produces a stderr warning without
  altering exit semantics. The 8+ cycle "documented but not guarded"
  honesty residual gets a first layer of closure now rather than
  deferring to v0.11.8+ architectural work.

**Bug class:** Python docstrings + STATE.md outside scanner; documented
bugs carried as anonymous candidates; profile mutation undetected.

### Companion-fix arc summary

| Layer | Release | Bug class |
|---|---|---|
| Runtime stdin parser shape | v0.11.3 | script wrong |
| Hook command path resolution | v0.11.4 | path wrong |
| CLAUDE.md doc drift class | v0.11.5 | Markdown untestable claims |
| Sentinel body-hash binding | v0.11.6 | trailing-whitespace round-trip mismatch |
| Scanner extension + Residual reclassification + B1 minimal | v0.11.7 | docstrings + STATE.md + anonymous-candidate carry + profile mutation |

The arc shipped real fixes for real bugs in real code paths — the Stop
hook script, the hook command registration, the doc-drift scanner, the
sentinel binding, the residual classification system. None of it
depended on the vendored CE/superpowers surface to be valuable.

## What survives the v0.12.0 pivot intact

Per decisions D10 and D11:

- `scripts/hooks/stop_verify_claims.py` — preserved intact. The v0.7.9
  nonce sentinel + v0.10.2 paraphrase regex + NFKC + Cyrillic fold +
  vendor-aware whitelist + v0.10.3 Greek/Armenian fold + conditional/
  attribution suppression + v0.11.3 transcript_path parser + v0.11.6
  sentinel body-hash binding + v0.11.7 B1 profile-mutation warning all
  remain.
- `hooks/hooks.json` — preserved with `${CLAUDE_PLUGIN_ROOT}` expansion.
- The companion-fix arc tests:
  `tests/test_regression_v011_3_stop_hook_input_layer.py`,
  `tests/test_regression_stop_command_hook.py` (plugin-root invariant),
  `tests/test_regression_v011_5_*` (CLAUDE.md drift invariants),
  v0.11.6 sentinel body-hash tests, v0.11.7 profile-mutation detection
  tests, v0.11.7 import-path invariants. Cross-verified preservation
  requirement.
- The v0.10.2 vendor-aware whitelist rationale is re-framed in
  CLAUDE.md from "vendored skill output coverage" to "general defensive
  coverage." Utility persists beyond the original motivation —
  paraphrase, Cyrillic/Greek/Armenian homoglyphs, and the 18 idioms
  are not exclusive to vendored prose origin.
- Spec-then-TDD discipline in `/athanor:work` (athanor identity #3).
- Cross-model adversarial planning in `/athanor:plan` (athanor
  identity #2).
- `/athanor:lfg` athanor-native pipeline (v0.11.0 wrapper).

## What v0.12.0 corrects

- The 32 `ce-*` skills surface — atomic cut after one v0.11.8
  deprecation warning cycle. `ce-test-browser` is the single KEEP-class
  CE skill (user opt-in browser automation, no athanor-native
  equivalent, decision D8). The other 31 are DROP or LIFT.
- The 13 `sp-*` skills surface — same atomic-cut posture.
- The 49 vendored CE sub-agents — cut to 2 retained generic discovery
  dispatch targets per decision D12.
- The `/athanor:ce-plan`, `/athanor:ce-work`, `/athanor:ce-lfg` slash
  commands — full DROP per decision D9 (no THIN-ADAPTER stubs). Users
  migrate to `/athanor:plan`, `/athanor:work`, `/athanor:lfg`.
- The "Vendored Surface — Identity Guard Layer" section of CLAUDE.md —
  obsoleted by the atomic cut. The guard prose existed to defend
  athanor identity against the inflated surface; fewer vendored
  surfaces means fewer places where the four identity commitments must
  be defended.

Aggregate surface reduction post-v0.12.0: **97%** (3 retained items: 1
ce-test-browser KEEP skill + 2 KEEP sub-agents — per decision D13).

## Framing

The work was real; the product surface was wrong.

The Stop hook hardening, the doc-drift scanner, the sentinel binding,
the plugin deployment fix, the import-path invariants, the residual
reclassification — these closed real bugs that affected real users.
The companion-fix arc is part of athanor's permanent record.

The 32 `/athanor:ce-*` and 13 `/athanor:sp-*` command surface was a
plan-of-record misread of the user's concept-absorption intent. v0.12.0
corrects the surface without destroying the work shipped on top of it.

## Cross-references

- Pivot plan: `.athanor/sessions/2026-05-22-001/plan.md`
- Decisions log: `.athanor/sessions/2026-05-22-001/decisions.md`
- Durable plan inventory (Phase 1.4 target):
  `docs/plans/2026-05-22-001-feat-v0.12.0-concept-absorption-pivot-plan-INVENTORY.md`
- Architecture doc (Phase 0.2 target):
  `docs/architecture/v012-concept-absorption.md`
- CHANGELOG entries: `CHANGELOG.md` §§ [0.10.0] – [0.11.7]
- Identity guard layer (to be removed in v0.12.0): `CLAUDE.md`
  §"Vendored Surface — Identity Guard Layer"
