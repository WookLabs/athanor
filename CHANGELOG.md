# Changelog

All notable changes to Athanor are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

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
