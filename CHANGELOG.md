# Changelog

All notable changes to Athanor are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

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
