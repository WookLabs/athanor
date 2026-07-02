# Changelog

All notable changes to Athanor are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [0.24.2] — 2026-07-01

Headline: a small **hardening patch** — fail-loud git plumbing for the
autonomous `/athanor:lfg` pipeline. One merged PR since v0.24.1; all hardening,
no new features and no surface change.

### Hardened

- **Fail-loud git plumbing in unattended `/athanor:lfg` + `ci-watcher`.** Every
  autonomous `git push` / `git commit` in `/athanor:lfg` (Steps 4/7/8) and
  `agents/ci-watcher.md` (Step 4) now runs with `GIT_TERMINAL_PROMPT=0`, stdin
  redirected from `/dev/null`, and a finite `timeout`. This guard was absent
  repo-wide: an interactive credential / 2FA / LFS prompt would block on stdin
  and silently hang the unattended pipeline indefinitely. Git now fails fast
  with a non-zero exit that flows into the existing push-failure diagnosis
  path. Pure hardening of existing plumbing — no new surface;
  `/athanor:lfg-goal` is unchanged (pure wrapper). +7 regression tests
  (`tests/test_regression_lfg_git_hardening.py`).

A companion "Codex CLAUDE.md preamble" candidate was **refuted and not shipped**
(AGENTS.md already mirrors CLAUDE.md for Codex — the guard would have been
redundant). Honest impact: a minor correctness/robustness improvement to lfg
plumbing; no score re-baseline claimed. The plugin surface stays frozen: 4
registered agents and the existing native command set are untouched.

## [0.24.1] — 2026-06-30

Headline: a patch release of **16 adversarially-confirmed fixes** (10 correctness
+ 6 documentation) hardening load-bearing hook/gate code and stale docs. They came
from an `ultracode` quality hunt — 11 finders → adversarial verification → 18
findings confirmed and **5 phantom findings rejected** (verify-before-cut) → two
`/athanor:lfg` fix cycles. All fixes, no new features; this release ships 16 of the
confirmed findings (the two PRs below) plus **+23 regression tests**. The plugin
surface stays frozen: 4 registered agents and the existing native command set are
untouched. Honest re-assessment after the hunt: correctness 88→90 (newly meets its
floor), documentation 86→89, test_coverage 83→84, overall 89→~90.

### Fixed

10 adversarially-confirmed correctness bugs in load-bearing hook/gate code
(PR #81, `a3b9527`; +23 regression tests), led by the two HIGH safety fixes:

- **(HIGH) `/athanor:lfg` merge-gate G2 was fail-open.** The unresolved-review-
  residual clause keyed only on the `blocker` severity token, but `/athanor:review`
  emits critical/high/medium/low — so an unresolved **CRITICAL** residual could
  reach a MERGE verdict. The clause now matches `(blocker|critical|high)` and is
  fail-safe.
- **(HIGH) PreToolUse kernel-guard destructive-shell check was bypassable.** The
  destructive-shell matcher was whole-command unanchored: a chained checkout-dot
  form slipped past the block while a quoted mention was false-blocked. The matcher
  is now segment-anchored.
- **(MED) Force-push matcher missed the `+refspec` form.**
- **(MED) The `test_` credential exemption was a path substring** — it exposed a
  real `.env` living under a `test_`-prefixed directory; tightened.
- **(MED) Merge-gate crashed (uncaught exit 1) on a non-UTF-8 findings file** — it
  now fails loud as exit 2.
- **(MED) Stop-hook attribution verbs over-suppressed first-person claims.**
- **(MED) Evidence-gate matched a generic `node_id` as a bare command substring.**
- **(LOW) PostToolUse sniffer recorded value-option args as targets** and inferred
  green-as-red on the bare word `error`.
- **(LOW) Goal-controller parsed an inert `completion_gates_required` flag** (removed).

### Documentation

6 adversarially-confirmed staleness fixes (PR #82, `d0d7405`):

- `DESIGN.md` agent-partition verify command globbed the wrong directory (exited 1
  on the correct state); corrected.
- `STATE.md` cited a deleted test as the active enforcer; re-pointed to the live one.
- `freeze.md` + `/athanor:setup` omitted the live `warn` freeze mode; documented.
- `freeze.md` cited a non-existent test filename; corrected.
- `DESIGN.md` documented a ghost `models` config key; removed.
- `package-knowledge-index` review stamp was stale; refreshed.

## [0.24.0] — 2026-06-30

Headline: **removed the P26–P30 self-validating governance subsystem**
(−8,599 LOC across 42 files) and shipped an **executable fail-loud
merge-readiness gate** for `/athanor:lfg` Step 8.5. Six merged PRs land since
v0.23.0; net diff 63 files, +2,129 / −8,626. Two fail-loud-over-silent-fallback
bugs are fixed, dead config and hot-path overlay prose are removed, and the
analyze + debug skills gain their first behavioral regression tests.

### Added

- **Executable merge-readiness gate for `/athanor:lfg` Step 8.5 (PR #74).** New
  `scripts/gates/lfg_merge_gate.py` replaces hand-interpreted bash for the
  pipeline's most-irreversible action (the auto-merge). It reads `gh pr view`
  JSON on stdin and emits a `merge | block | skip` verdict plus the deciding
  clause (exit `0`/`2`/`3`/`4`); an unknown `mergeStateStatus` enum maps to
  exit `2` (fail-loud — never a silent merge), and merge is authorized only for
  a `CLEAN` state. The gate is verdict-only: it structurally cannot `--admin`
  or bypass branch protection. +19 executable tests. **Honesty label: advisory**
  — it is an executable verdict, but no runtime hook forces the leader to honor
  it (same enforcement class as the Step 3/8 fix-round counter).

### Fixed

- **Two fail-loud-over-silent-fallback bugs (PR #75).** (1) The
  `${CLAUDE_PLUGIN_ROOT}` sentinel anchor was restored in
  `verification-before-completion` SKILL.md and `receipt-validator.md` — a bare
  path had silently degraded Stop-hook invariant #4 in user projects. (2) A
  `*)` default arm was added to both `codex.fallback` case blocks in
  `codex-availability.md`, so an unrecognized fallback value surfaces instead
  of falling through silently. +6 regression tests.

### Removed

- **P26–P30 self-validating governance subsystem removed (PR #79, headline) —
  −8,599 LOC across 42 files.** The subsystem scored itself (the
  `organization_score.py` self-scorer) and gated CI on its own existence, with
  zero external / marketplace / `plugin.json` consumer. Removed: 5 gate scripts,
  5 org tests, 6 schemas, 5 docs, ~12 artifacts, and 5 decision JSONs, across 4
  CI-green phases. `work_item_stage.py` and `harness_decision_ledger.py`
  (separate, live) were KEPT. This is the bulk of the release's −8,626
  deletions.
- **Dead `lfgGoal.userConfirmAfter` config removed (PR #77).** The schema
  falsely advertised a knob with no consumer. `consolidateCycles`,
  `review.personas`, and `doc-review` were verified live and kept.

### Changed

- **Hot-path overlay prose relocated to docs (PR #76).** ~24 lines of P26
  overlay prose moved out of the `lfg` / `lfg-goal` hot-path skills into docs.
  Investigation found the suspected "~2000 LOC over-build" was actually
  live/tested code, so the live scripts were kept — only the prose moved. (An
  honesty win: the over-claim was rejected rather than acted on.)

### Tests

- analyze and debug skills gained their first behavioral regression tests
  (PR #78), plus 4 `freeze.md` function-name fact-corrections. Net new tests
  across the release: **+25** (+19 executable merge-gate, +6 fail-loud
  regression), net of the 5 self-validating org tests removed with the
  governance subsystem.

## [0.23.0] — 2026-06-25

### Added

- 한글 완료 요약 step added to `/athanor:lfg` (Step 9.5) and `/athanor:lfg-goal`
  (terminal, all exits) — advisory, follows `output.language`, machine tokens
  stay English, hook-safe factual phrasing.

## [0.22.1] — 2026-06-25

### Added

- **Worker context packet convention (slim, advisory).** Adds
  `docs/worker-context-packets.md` — a lightweight dispatch-hygiene convention
  that names what a clean-context worker should receive in its dispatch packet
  and return in its result. It is **convention-only and not runtime-enforced**:
  rather than re-encoding the contracts, it references the existing canonical
  sources — the executor dispatch packet in `skills/work/references/splitter.md`,
  the `ATHANOR_RESULT` result schema in
  `skills/work/references/spec-then-tdd-handler.md`, and the runtime write-scope
  in `skills/work/references/freeze.md`. A single doc-pin regression test locks
  the convention's cross-references. The plugin surface stays frozen: 4
  registered agents and the existing native command set are unchanged.

## [0.22.0] — 2026-06-24

### Added

- **`/athanor:lfg-goal` durable loop controller strengthened (PR #65).** The
  goal-loop controller gains an **adaptive score-target router**: it validates
  assessment evidence with fail-loud parsing, runs a two-way `target_met`
  cross-check against the computed scores (so a claimed pass is rejected when
  the numbers disagree, and vice versa), and routes baseline/delta assessment
  results into the next lfg-cycle carrying the lowest-scoring dimensions as the
  focus. Review-hardening lands alongside it: **persistent block/escalate
  states are now bounded** — a stuck `eval_status=fail` / invalid-receipt loop
  terminates via `stop_no_progress` → `aborted` instead of spinning — and the
  **CLI exit-code contract** now returns non-zero for every stop/block action
  (`exit 0` ⟺ the controller authorized a forward action). New fixture-gate
  scenarios plus a re-drive regression test lock the behavior.

### Changed

- **`/athanor:lfg` Step 8.5 auto-merge flipped to opt-out (default ON).** The
  `lfg.autoMerge` default in `athanor.json` / `templates/athanor.json` is now
  `true`, so a green PR is merged by default once the unchanged conjunctive
  merge-readiness gate (G0–G5) passes. Disabling is now a one-flag opt-out:
  the old `--no-merge` flag is **renamed to `--unmerge`** (hard-disables even
  when config enables it; fail-safe direction wins ties), and `--merge` is kept
  as the explicit-enable counterpart for a `false` config. The disabled-skip
  result state `skipped-not-opted-in` is renamed to `skipped-merge-disabled`.
  The gate logic, disposition table, re-poll, merge command, never-`--admin`
  rule, and releaser boundary are unchanged.

## [0.21.0] — 2026-06-24

### Added

- **Opt-in `/athanor:lfg` auto-merge + merge-readiness gate (Step 8.5).** After
  CI goes green, `/athanor:lfg` can now optionally merge a green PR to its base
  branch (`gh pr merge --rebase --delete-branch`). It is **off by default** and
  opt-in via the `--merge`/`--no-merge` flag or `athanor.json` `lfg.autoMerge`
  (`--no-merge` wins ties). Merge proceeds only when a fail-loud conjunctive
  readiness gate passes — re-entry/draft state, dual-source residual review
  blockers, unresolved-CI section, an exhaustive 8-value GitHub
  `mergeStateStatus` disposition, and merge-queue detection. On any failed
  clause the leader leaves the PR open, reports which clause failed, and still
  finishes the pipeline; it never `--admin`-bypasses branch protection. The step
  **merges only** — it never version-bumps, tags, or edits CHANGELOG/STATE.md
  (that stays the `athanor-releaser` ceremony). The gate is advisory
  (leader-prose-enforced); no runtime hook blocks the merge.

## [0.20.1] — 2026-06-23

### Added

- **User-facing output language preference (`output.language`).** best-effort advisory, default en — 본 레포 ko; 9개 native 스킬에 leader-side 해석 + 조건부 per-language directive 주입; 영어권 default 동작 불변.

## [0.20.0] — 2026-06-23

This minor release rolls up the never-published `0.19.3` ref-optimization work
plus the score-95 tooling migration, a Stop-hook opt-in deadlock fix, and the
`catalog_admission` CI fixes into a single shipped version. The plugin surface
stays frozen: 4 registered agents (`ci-watcher`, `codex-dispatcher`, `learner`,
`releaser`) and the existing native command set are unchanged. Identity
invariants intact (4): Thin Leader / cross-model adversarial / Spec-then-TDD /
Stop hook gate.

### Added

- **346-ref optimization bundle.** Ships the local-first, read-only gate bundle
  from the 346-ref optimization pass — `scripts/gates/memory_index.py`,
  `scripts/gates/catalog_admission.py`, `scripts/gates/codex_mirror_parity.py`,
  `scripts/gates/work_item_stage.py`, the durable-loop controller,
  `scripts/evals/workflow_trace_query.py`, the hook-safety corpus, and
  package-footprint reduction. All gates are read-only evidence; historical
  `ref/` material stays repo-local and out of default packaged context, and the
  4-agent / native-command surface is frozen.

### Changed

- **uv/pyproject tooling migration (score-95).** CI now uses
  `astral-sh/setup-uv` with `uv sync --locked --dev` and `uv run`, backed by new
  `pyproject.toml`, `.python-version` (3.14), and `uv.lock` files. The ship
  profile classifies the new tooling files as dev-only so they stay out of the
  packaged plugin surface.
- **Installed-hook project-root resolution.** The installed-hook
  `resolve_project_root()` now honors `$CLAUDE_PROJECT_DIR` before falling back
  to the cwd walk-up, so hooks resolve the correct repo root under Claude Code.
- **PostToolUse evidence scope.** The evidence sniffer scope is promoted from
  `unspecified` to `full_suite`.
- **prompt-gen output-only hardening (Prompt generation skill).** The
  `/athanor:prompt-gen` Prompt generation skill (native + Codex mirror
  `athanor-prompt-gen`) drops `Skill` from its allowed-tools and treats any
  execution-language request as raw prompt material rather than a directive, so
  it stays output-only: it turns vague requests into structured prompts and can
  recommend the next Athanor skill (e.g. `/athanor:plan`) without ever starting
  implementation.

### Fixed

- **Stop-hook opt-in deadlock.** `scripts/hooks/stop_verify_claims.py` now exits
  `0` when no `athanor.json` is present — previously the gate was unsatisfiable
  without opt-in because its emission-sentinel path is also opt-in-gated. The
  sentinel body is now hashed with surrogate-safe `surrogatepass` handling on
  both the emit and validate sides.
- **catalog_admission CI fixes.** The `catalog_admission` gate treats an absent
  `ref/` corpus (gitignored) as vacuously clean, and its three real-corpus
  integration tests skip when `ref/` is absent, so fresh CI checkouts pass.

## [0.19.2] — 2026-06-19

### Added

- **Prompt generation skill.** Ships `/athanor:prompt-gen` and Codex
  companion `athanor-prompt-gen` as a request-framing surface that recommends
  the next Athanor skill before implementation starts.
- **lfg-goal score-target optimization loop.** Publishes the opt-in
  score-target goal loop across Claude and Codex skill surfaces, config
  defaults, schema, templates, rubrics, and regression tests.
- **Agent topology gate.** Adds the topology contract, documentation, CI gate,
  and regression coverage that lock the 4 registered agents, 7 reference roles,
  skill routes, and `prompt-gen` intake-framing status.

### Changed

- **Claude plugin release metadata.** Bumps the Claude plugin release surface to
  `0.19.2` so user-scope plugin updates detect and install this package.

## [0.19.1] — 2026-06-18

### Fixed

- **CI dependency install order.** The validation workflow now installs
  `pytest`, `jsonschema`, and `pyyaml` immediately after Python setup so the
  hook-installer regression gate can run before the broad pytest step on fresh
  GitHub Actions runners.

## [0.19.0] — 2026-06-18

### Added

- **Assessment skill.** Adds `skills/assess/SKILL.md` and
  `plugins/athanor-codex/skills/athanor-assess/SKILL.md` so Athanor can
  evaluate a target against a user goal with 100-point weighted dimensions,
  confidence, overbuilt and underbuilt findings, add/remove guidance, and a
  Priority Plan before implementation starts.
- **Agent topology gate.** Adds `docs/agent-topology.md`,
  `docs/agent-topology-contract.json`, and
  `scripts/gates/agent_topology.py` to lock the 4 registered agents,
  7 reference roles, every skill route, and `prompt-gen` intake-framing
  status before broad regression tests.
- **346-ref optimization gate bundle.** Adds the local-first optimization
  bundle from the 346-ref analysis without growing the 4 registered agents or
  11 native commands: `scripts/gates/catalog_admission.py`,
  `scripts/gates/memory_index.py`, `scripts/gates/memory_retrieval_eval.py`,
  `scripts/evals/workflow_trace_query.py`,
  `scripts/gates/codex_mirror_parity.py`,
  `scripts/gates/work_item_stage.py`, and package
  `ship_profile_decisions` keep ref absorption, memory, trace replay, Codex
  mirror parity, work-item stages, and ship-profile reduction gated by
  read-only evidence.
- **v0.19 evidence branch candidate.** Adds the PostToolUse test-evidence
  path, Freeze D2 evidence follow-up, hook payload corpus replay gate, and
  log-only UserPromptSubmit spike harness while keeping runtime blocking
  behavior opt-in or evidence-only where live payload certainty is still
  empirical.
- **Generic hook payload capture harness.** `scripts/hooks/hook_payload_capture.py`
  prints an opt-in settings snippet for live Stop, PreToolUse, PostToolUse,
  and FileChanged payload review, writes raw local captures plus redacted shape
  summaries under `.athanor/spikes/hook-payloads`, and remains unregistered in
  repo `hooks/hooks.json`.
- **Shared hook capture utilities.** `scripts/hooks/hook_capture_utils.py`
  centralizes raw capture, redacted shape summaries, and settings-snippet
  generation so the generic capture harness and UserPromptSubmit spike harness
  cannot silently drift.
- **Evidence enforcement ladder.** `hooks.evidence.mode` now supports
  `observe`, `warn`, and `strict` for the work evidence gates. `warn` preserves
  the hybrid default; `observe` records observations without changing subtask
  status; `strict` promotes evidence concerns to failures.
- **Live hook fixture importer.** `scripts/gates/import_hook_fixture.py` imports
  manually reviewed hook payload captures into the replay corpus as
  `source_level: live-redacted`, recursively redacting home paths, obvious API
  tokens, private GitHub image URLs, and private-key blocks before appending to
  `tests/fixtures/hooks/index.json`.
- **Claude Code 2.1.177 live hook fixtures.** The replay corpus now includes
  reviewed live-redacted Stop, PreToolUse, and PostToolUse captures generated
  through `scripts/hooks/hook_payload_capture.py`, with capture provenance
  recorded on each fixture.
- **Claude Code 2.1.178 live pytest PostToolUse fixture.** The replay corpus
  now includes a reviewed live-redacted targeted pytest run captured from a
  real Claude Code PostToolUse event. It locks the current empirical fact that
  this payload shape exposes stdout/stderr but no direct exit-code field; the
  sniffer now infers clear pytest pass/fail summaries and records
  `exit_code_source`.
- **Hook corpus safety gate.** `scripts/gates/replay_hook_fixtures.py` now
  rejects fixtures containing obvious secrets/local paths, Claude project slugs,
  and requires `live-redacted` fixtures to carry redaction metadata with
  manual-review provenance.
- **CI hook replay gate.** The validation workflow now runs
  `scripts/gates/replay_hook_fixtures.py` as a named CI step, so hook fixture
  replay failures are visible independently from the pytest suite.
- **PostToolUse health diagnostics.** Fail-open infrastructure issues such as a
  missing session directory now write `.athanor/hook-health.jsonl` breadcrumbs
  while preserving hook exit 0 behavior.
- **Durable loop controller foundation.** Adds versioned lfg-goal loop state
  and evidence schemas, a deterministic decision engine, controller CLI,
  committed fixture gate, P6 `loop.decision` workflow scenario coverage, and
  operator docs while keeping live Claude Code invocation out of scope.
- **Trust-aware hook installer apply/remove path.**
  `scripts/gates/hook_install_dry_run.py` now emits schema v2 reports with
  hook hash fingerprints and trust status, supports `--mode apply` for
  trusted no-clobber settings writes with backups, and supports
  `--mode remove` for exact Athanor hook removal while keeping capture-only
  hooks blocked by policy.
- **Cross-runtime conformance gate.** Adds a read-only runtime-surface contract
  and `scripts/gates/runtime_conformance.py` so Claude Code plugin
  metadata, Codex companion skills, and `hooks/catalog.json` enabled runtime
  hooks fail CI on drift before any generator or settings writer expands the
  surface.
- **Observability trend snapshots.** Adds
  `scripts/observability/collect_trend_snapshot.py`,
  `scripts/observability/report_trends.py`, and trace-to-scenario promotion so
  workflow eval scores, hook latency ratios, durable loop actions, and
  escalations can be tracked in local `.athanor/observability/trends.jsonl`
  history without enabling new hooks or external telemetry.
- **Entropy cleanup report gate.** Adds read-only
  `scripts/gates/entropy_cleanup.py` plus
  `schemas/entropy-cleanup-report.schema.json` to surface stale plans,
  capture-only hook candidates, ref freshness, and runtime
  mirror/conformance drift as structured cleanup actions before P12 expands
  live orchestration.
- **Runtime execution adapter.** Adds read-only
  `scripts/gates/runtime_execution_adapter.py` plus fixture coverage to
  recommend `solo`, `subagent-wave`, `dynamic-workflow`, `agent-team`, or
  `manual-worktree` backends before future live orchestration work launches
  dynamic workflow, agent team, or worktree surfaces.
- **Live command trace emitter.** Adds local-first
  `scripts/evals/emit_workflow_trace.py` and command skill anchors so
  Athanor command leaders can write `.athanor/traces` JSONL records for
  `workflow.started`, worker/evidence events, escalations, and
  `workflow.finished` without enabling new default hooks or external telemetry.
- **OTel-style trace export adapter.** Adds privacy-safe local JSON export via
  `scripts/evals/export_otel_trace.py` and
  `schemas/otel-trace-export.schema.json`, mapping Athanor workflow traces to
  GenAI-style attributes such as `gen_ai.operation.name` without adding an
  OpenTelemetry SDK dependency, hooks, collector export, or raw
  message/evidence/reference content by default.
- **Workflow eval episode packaging.** Adds
  `scripts/evals/package_workflow_episode.py`,
  `schemas/workflow-eval-episode.schema.json`, and `--episode-root` runner
  support so deterministic workflow scenarios can be packaged as portable local
  episodes with `deterministic_grader_kinds`, limits, privacy metadata, and
  `network_access` sandbox policy before broad pytest.
- **External eval adapter.** Adds
  `scripts/evals/export_external_eval_adapter.py` and
  `schemas/external-eval-adapter.schema.json` to export packaged workflow
  episodes into inspect-like and harbor-like task, scorer, and
  `sandbox/manifest.json` metadata while keeping no default external execution,
  no dependency installation, no network access, and no external telemetry.
- **Native runtime playbook.** Adds
  `scripts/gates/native_runtime_playbook.py` and
  `schemas/native-runtime-playbook-report.schema.json` to turn native runtime
  probe dry-runs into operator-approved recipes for `manual-worktree`,
  `dynamic-workflow`, and `agent-team` lifecycles while keeping
  `auto_execute: false`, explicit cleanup, and zero irreversible actions by
  default.
- **Reactive channel fixture gate.** Adds local-only
  `scripts/gates/reactive_channel_fixture.py` plus
  `schemas/reactive-channel-fixture-report.schema.json` to normalize fake
  pushed CI and review payloads into `dispatch-ci-watcher`,
  `record-ci-pass`, and `plan-review-response` action templates while keeping
  every listener unregistered, `auto_execute: false`, no default network
  execution, and zero irreversible actions.
- **Package knowledge index.** Adds `docs/package-knowledge-index.md` and
  read-only `scripts/gates/package_knowledge_index.py` so package-facing
  workers can start from README.md or CLAUDE.md, find current operator gates
  and safety contracts, and avoid repo-local development history while the
  broader ship profile remains explicit.
- **Organization operating model.** Adds
  `docs/organization-operating-model.md` and read-only
  `scripts/gates/organization_operating_model.py` so `/athanor:lfg` and
  `/athanor:lfg-goal` route work through a company-like office/stage graph
  with owner roles, receipt requirements, learning governance, no default live listener, and no registered-agent expansion.
- **Organization work-item registry.** Adds
  `docs/organization-work-item-registry.md` and read-only
  `scripts/gates/organization_work_item_registry.py` so 9.8-score work can
  carry durable work-item state, ordered stage history, `receipt_ref`
  handoffs, owners, artifacts, and safety metadata before broad tests.
- **Organization stage receipts.** Adds
  `docs/organization-stage-receipts.md` and
  `scripts/gates/organization_stage_receipt.py` so lfg-goal evidence can
  become a schema-backed stage receipt; the adapter writes only with `--emit`
  and advances work-items only with `--apply-work-item-update`.
- **Policy promotion ledger.** Adds `docs/policy-promotion-ledger.md` and
  read-only `scripts/gates/policy_promotion_ledger.py` so lessons move through
  `incident -> lesson -> candidate_policy -> policy -> gate_candidate -> gate -> retired`
  with owners, evidence, acceptance criteria, rollback, schema-backed tests,
  and explicit retirement instead of accumulating prose policy.
- **Organization score gate.** Adds `docs/organization-score.md` and read-only
  `scripts/gates/organization_score.py` so the 9.8 maturity claim is computed
  from organization evidence inputs, weighted dimensions, CI coverage,
  package-boundary warnings, and explicit residual gaps instead of scorecard prose.
- **Distribution smoke gate.** Adds
  `scripts/gates/distribution_smoke.py` and a named CI gate that runs
  `claude plugin details` when available, verifies the live 4-agent loader
  surface, enforces the always-on token budget, checks manifest/marketplace
  pins, and keeps inline-only pipeline role docs out of plugin-root `agents/`.
- **Trace-memory quality gate.** Adds
  `scripts/gates/trace_memory_quality.py`,
  `schemas/trace-memory-quality-report.schema.json`, and committed fixtures so
  lesson promotion, stale decay, quarantine, and with/without lesson
  comparisons are evidence-backed before memory can be treated as
  self-improving.
- **Harness decision ledger.** Adds committed `docs/harness-decisions/*.json`
  records plus `scripts/gates/harness_decision_ledger.py` so harness changes
  declare expected metrics, verification commands, observed results, and
  rollback/follow-up decisions before the harness can claim self-improvement.
- **Native runtime probe.** Adds read-only
  `scripts/gates/native_runtime_probe.py` fixture coverage for Claude `/goal`,
  `/loop`, worktree, dynamic workflow, and agent team readiness. The probe
  emits dry-run launch plans only, keeps `auto_launch_allowed: false`, and
  fails profiles that try to make native runtime surfaces executable by default.
- **Maintenance profile gate.** Adds read-only
  `scripts/gates/maintenance_profile.py` as a CI and `/loop` profile that
  packages entropy cleanup, distribution smoke, observability snapshots,
  native runtime probe, and harness decision ledger checks into one operator
  report with zero irreversible actions by default.
- **Package footprint policy gate.** Adds read-only
  `scripts/gates/package_footprint_policy.py` plus
  `schemas/package-footprint-policy-report.schema.json` to classify the
  default ship profile, report package budgets and largest files, surface
  dev-only candidates such as tests, plans, archives, architecture research,
  and CI metadata, and recommend `exclude-from-ship-profile` without deleting
  or moving files.

### Changed

- **Memory honesty cleanup.** README, DESIGN, and ROADMAP now describe the
  shipped learning surface as local `.athanor/lessons/` files plus
  Learner/Cleaner prompt-level decay. mem-search permanent persistence remains
  explicitly unimplemented instead of being implied by the historical Phase 8
  checklist.
- **XHigh progress audit refresh.** The saved xhigh report now separates the
  original 7.3/10 score from the current post-remediation evidence score,
  records all eight original recommendations as done, and records the
  live-redacted core hook fixture evidence that satisfies the approximate
  9.5/10 target plus the final live pytest evidence hardening.
- **Strict default migration policy.** ROADMAP now states the release policy
  needed before changing `hooks.evidence.mode` from `warn` to `strict`: new
  installs may move stricter after live pytest evidence is present, while
  existing installs keep explicit/generated `warn` unless users opt in.

### Release Notes

- Ships the v0.19.0 evidence, loop, harness, organization-model, and assessment
  branch. The release bumps manifests, schema URLs, README, STATE, and release
  tests in the same pass so the marketplace surface and runtime evidence stay
  aligned.

## [0.18.8] — 2026-06-12

### Added

- **athanor-codex companion plugin** (`plugins/athanor-codex/`). A second-runtime mirror of the athanor native skill set for the Codex CLI — 13 skills (`athanor-analyze`, `athanor-debug`, `athanor-discuss`, `athanor-lfg`, `athanor-lfg-goal`, `athanor-plan`, `athanor-ci-watch`, `athanor-release`, `athanor-review`, `athanor-scope-drift`, `athanor-setup`, `athanor-verify`, `athanor-work`). Prefix-safe, no Claude hooks, repo-local marketplace entry. See `plugins/athanor-codex/README.md`. (P8: top-level ledger entries — CHANGELOG, README, STATE.md, DEPENDENCIES.md — now document the companion.)
- **P9 — athanor-lfg-goal companion parity.** The companion's `athanor-lfg-goal` skill now matches the parent's UNDETERMINED non-blocking rule (`8 VALID + 1 UNDETERMINED` → passes); a two-way derived test pins both sides so either drifting breaks the suite.

### Fixed

- **CI — pyyaml added to pip install in `validate-plugin.yml`.** The codex-companion regression test (`test_regression_codex_companion.py`) imports `yaml` at module level; CI's fresh Python env had no PyYAML, causing collection failure on both ubuntu and windows runners.
- **P14 — Stop-gate carve-out removed (security).** Dead `DEPRECATION_SENTINEL` path in `scripts/hooks/stop_verify_claims.py` provided a permanent Stop-gate bypass that could never be triggered legitimately; removed entirely. The bypass was a dead code path, not a runtime opt-out — its removal closes the hole with no functional regression.
- **P2 — Freeze allowlist dead-on-arrival fix.** `scripts/work/build_freeze_allowlist.py` failed silently for absolute paths (the v0.18.0 freeze allowlist was DOA for absolute-path entries). Adds absolute-path relativization and unifies `allowedPaths`/`extraAllowedPaths` key naming.
- **P13 — Force-push guard segment-scoped.** `scripts/hooks/pretool_kernel_guard.py` force-push matcher now uses a `(?![\w-])` word-boundary so `feature/main-update` and similar branches are no longer false-positived; exact `main`/`master` slash-segments stay blocked. Force-push guard now also strips `sudo`/`env` wrapper prefixes before segment matching, re-blocking `sudo git push --force origin main`; remaining wrapper class (`xargs`/`time`/`nice`/option-argument forms) is documented as accepted scope.
- **P16 — NotebookEdit/MultiEdit added to Kernel Guard coverage.** Both tool names added to the PreToolUse guard so notebook and multi-edit destructive patterns are subject to the same checks as Bash/Edit.
- **P15 — Hook-state opt-in lifecycle.** Hooks no longer create `.athanor/sessions/<id>/.hook-state/` as a side effect in repos that have never opted in. The directory is now created only after `athanor.json` is detected (opt-in gate), preventing filesystem debris in non-athanor repos.
- **P19 — STATE.md stale ledger rows corrected.** Contract-ledger and agent-frontmatter rows updated to reflect current enforcement status; refuted known-gaps (frontmatter tests "absent", transcript-parser contingency) deleted.
- **`extract_target_path` return annotation corrected to `str | None`.** Test coverage added for hook-state opt-in `.git`-boundary and `tests/_version.py` fail-loud raises.

### Changed

- **Fable 5 audit rounds 1–2.** Round 1 (043244c): Tier 1+2+3 corrections — athanor-codex install docs, guard fixes, test pins. Round 2 (65d0136–b35965c, 8 commits, P2/P5–P11/P13–P20): doc-contract parity P5/P6/P7/P17; stop-phrase whitelist canonicalized with pointers P10; plugin version literal centralized via `tests/_version.py` P18; setup dead `models` config block deleted and triggers de-scoped P11; English triggers added to analyze/work/discuss skills P11; ROADMAP deferred headings re-keyed to stable codenames P20.
- **P20 — ROADMAP deferred headings re-keyed.** Headings previously keyed as `v0.18.1`/`v0.18.2` (colliding with shipped versions) replaced with stable codenames (`git-worktree isolation` / `UserPromptSubmit injection`); release-evidence test re-pointed to codename anchors.

## [0.18.7] — 2026-06-07

### Changed — plugin diet (de-register 7 reference-only agents; honesty cleanup)

An evidence-based plugin-diet audit (3 parallel Explore agents + direct verification). Honest finding: athanor is **already lean** (v0.12.0 atomic cut + v0.18.3 cleanup), so the genuine wins are modest and several audit "candidates" were refuted on verification — `ROADMAP.md` is test-locked, `DESIGN.md` is cross-referenced, `scope-change-critic.md` is an active worker, the dead one-shot scripts are inert + test-entangled. One audit "orphan" finding (lfg-goal `judge-rubric`/`goal-md-template`) was refuted by the existing v0.13.0 contract tests and **dropped** — the test net working as intended.

- **Agents: 11 → 4 registered.** The 7 inline-only pipeline roles (`analyst`, `cleaner`, `critic`, `executor`, `planner`, `researcher`, `reviewer`) are **de-registered to pure reference docs** — frontmatter `name:`/`tools:`/`model:` removed, `description:` kept. They had 0 standalone `@-mention` adoption and the registered type contradicted the collision guard (skills dispatch them INLINE with session-specific paths). Only `learner`, `releaser`, `ci-watcher`, `codex-dispatcher` stay registered (the leader / release ceremony / lfg dispatch them as types). Verified `claude plugin validate` clean, no new load warnings. CLAUDE.md §Native Agent Inventory + §Effort Level + COLLISION GUARD prose simplified.
- **DESIGN.md stale-command fix.** `docs/DESIGN.md` diagrams + tier table dropped the v0.17.0-removed `/athanor:deep-plan` / `/athanor:lite-plan` for the `/athanor:plan --depth=` form. Locked by an extended `test_regression_stale_command_refs.py`.
- **Config honesty labels.** `schemas/athanor-config.schema.json` now flags the genuinely-unimplemented surface — `memory.promotionThreshold` (permanent→mem-search promotion not wired) and `triggers.language` (advisory; not enforced at dispatch) — so the schema no longer over-claims behavior it doesn't ship.

5 new/updated regression tests (DESIGN stale-refs, 2 schema honesty labels, agent reference-doc partition, effort-level registered-only). Full suite **970 passed, 0 failed**; `claude plugin validate` + `lint_checks agent-descriptions` green. No identity-invariant change; STATE rotation/trim (v0.18.1 → `docs/archive/STATE-history.md`, Previous cap 5) applied.

## [0.18.6] — 2026-06-07

### Fixed — 11 bugs from a deep bug-hunt (Kernel Guard security hardening)

A deep adversarial bug-hunt Workflow (4 specialized lenses → refute-default reproduce-to-confirm) found **11 real bugs** in athanor's own executable code — all reproduced, all fixed RED→GREEN. Headline: athanor's PreToolUse **Kernel Guard** (the safety gate that blocks catastrophic commands) was bypassable by the most common real-world forms. Honest scope: 5 are pre-existing v0.16.0 regex flaws; only **1 (D1)** is a v0.18.5 regression.

**Critical — Kernel Guard root-wipe bypasses (`scripts/hooks/pretool_kernel_guard.py`):**
- **G1** `rm -rf /*` (shell-glob root wipe) and `rm -rf ~/*` slipped the guard — only literal `/` was blocked.
- **G2** `rm -rf --no-preserve-root /` (the GNU-canonical root wipe; bare `rm -rf /` is refused by GNU rm) slipped via the intervening option.

The `rm` family is now detected by a flag-detection + target-detection split: flag-order independent, intervening options allowed, shell-glob root/home forms matched — while keeping false-positives out (`rm -rf /tmp/build`, `./build/`, `~/projects/old`, `rm -f file.txt`).

**High — more destructive-command bypasses (same file):**
- **G3** `rm -fr /` (flag order f-before-r; POSIX bundled flags are order-independent).
- **G4** `git clean --force` (long form) — only `-f` short bundles were blocked.
- **R1** `head -n 5 .env` — a value-taking option's separate-token value (`5`) shadowed the path, so the credential-read guard inspected `5` instead of `.env`. Reader path extraction is now token-based with value-option skipping.

**Medium:**
- **D1** *(v0.18.5 regression)* `scripts/work/build_freeze_allowlist.py` — the DF1 drift WARN was silently suppressed by any stray `#### Subtask N` heading in prose; suppression now keys off a recognized subtask BLOCK (header + fields), not a lenient regex hit.
- **F1** `scripts/hooks/freeze_guard.py` — `..` was not collapsed, so a path-traversal candidate matched a session allowlist glob (fnmatch `*` crosses `/`) and an out-of-scope edit slipped the freeze. Candidates are now `posixpath.normpath`-canonicalized before matching (fail-closed on escape).
- **R3** `scripts/check_release_ready.py` — the Unreleased-changelog regex matched a substring-prefix version (`0.18.5` matched `0.18.50`); added a right boundary.

**Low:**
- **F3** `build_freeze_allowlist.py` — a non-bracketed inline backtick list of files kept only the first path; now comma-split like the bracketed branch.
- **R2** `scripts/gates/manifest_checks.py` — crashed with an uncaught TypeError on a non-string plugin.json `hooks` field; now fails-loud with a clean `(False, reason)`.
- **R4** `check_release_ready.py` — coerced a `None` version to `""`, making any `## ` header satisfy the evidence anchor and masking the real cause; now fails-loud.

19 new regression tests (each security fix pairs bypass-blocked + legitimate-allowed guards), RED→GREEN; full suite **965 passed, 0 failed**. No identity-invariant change; STATE rotation/trim (v0.18.0 → `docs/archive/STATE-history.md`, Previous cap 5) applied.

## [0.18.5] — 2026-06-06

### Fixed — self-dogfood fail-loud fixes (adversarial enforcement audit)

An adversarial enforcement audit (4-lens Workflow, refute-default verify) of athanor's **own** complexity + no-silent-fallback discipline found and fixed 4 athanor-own-code defects. Honest framing: **user code = advisory** (Critic/review are leader-dispatched, not merge gates); **athanor's own code = gate**. This audit **refutes the prior "zero risky-silent fallback patterns" self-assessment** — the runtime gate scripts were clean, but two v0.17/v0.18 surfaces had drifted.

- **DF1 — `scripts/work/build_freeze_allowlist.py` silent mis-scope → fail-loud.** When a `## Subtasks` section was present but no subtask header matched either Splitter shape (heading drift / future format), the parser returned `[]` with no breadcrumb, silently mis-scoping the freeze allowlist to defaults-only and over-blocking downstream with no signal at the real cause. Now emits a stderr WARN on that drift path — false-positive-guarded: a matched header with no `files:` (a legitimate doc-only subtask) stays silent.
- **DF2 — `scripts/hooks/capability_probe.py` catch-all swallow → fail-loud.** A catch-all `except Exception: pass` around the runtime project-root resolver masked *all* errors (including a programming-error class a future refactor could introduce) behind the walk-up fallback. Narrowed to `except (OSError, FileNotFoundError)` so unexpected errors propagate, matching the module's existing narrow-except discipline.
- **CG2 — review/SKILL.md complexity-gate gap.** `skills/review/SKILL.md` (311 lines) had drifted past the thin-router budget while `work/SKILL.md` (≤250) and `plan/SKILL.md` (≤300) were line-capped. Added a ≤320 line-cap regression to lock against re-bloat (ratchets toward 300 as prose carves to `references/review-sections.md`).
- **HL1 — `/athanor:review` honesty under-label.** The review surface emitted "must fix before merge" severity prose with no advisory label, while the paired Critic surface carries "This rubric is advisory." Added a mirroring "advisory — not a merge gate" banner so a reader cannot mistake review for a CI gate (a false enforcement impression is itself a fail-loud honesty violation).

7 new regression tests (RED→GREEN); full suite **946 passed, 0 failed**. No identity-invariant change; release ceremony version-parity + STATE rotation/trim (v0.17.0 → `docs/archive/STATE-history.md`, Previous cap 5) applied.

## [0.18.4] — 2026-06-06

### Added — engineering-quality principle (low complexity + fail-loud)

- **CLAUDE.md §Core Principle** codifies "Engineering quality": works is the floor — keep complexity low + maintainable; **no indiscriminate fallback (fail-loud over silent fallback)** — surface errors, don't swallow them into a fallback that makes them hard to find. User code = advisory (Critic/review); athanor's own code = gate. (band 175→178.)
- **plan Critic axis (D) "Simplicity & fail-loud readiness"** (advisory) — flags unjustified complexity/scope + fallback designs that swallow should-be-fixed errors. Synced across `critic-rubric.md`, all `critic-variants.md` injections, and the `plan/SKILL.md` dispatch enumeration (three → four axes).
- **review maintainability lens** — silent-failure heuristic strengthened to name fail-loud + indiscriminate fallbacks explicitly.
- **athanor self fail-loud** — `scripts/hooks/pretool_dispatcher.py` now emits a stderr breadcrumb on the unparseable-stdin fail-open path (was silent — a guard that no-ops invisibly is the exact anti-pattern the principle warns against).

### Verification

- 4 new regression tests (engineering principle, critic axis (D) incl. SKILL.md sync, dispatcher fail-loud); full suite **939 passed, 0 failed**.
- An adversarial multi-lens Workflow review (4 lenses → refute-default verify) caught a self-consistency miss — `plan/SKILL.md` left at "three axes" while rubric/variants moved to four — fixed before release and the regression extended to lock SKILL.md.

## [0.18.3] — 2026-06-06

### Fixed — plugin hygiene cleanup (ref-update audit)

- README `/athanor:deep-plan` / `/athanor:lite-plan` → `/athanor:plan --depth=` (v0.17.0 folded them; README lagged).
- discuss dropped the `--new-session` flag broken-promise (reclassified v0.11.7) from the stale-session announcement.
- agent model drift: CLAUDE.md §Effort Level now maps all 11 agents to their actual frontmatter tier (executor=opus etc.); a regression locks frontmatter ↔ §Effort + the v0.6.2 frontmatter-consistency class.
- STATE.md bloat: trimmed 28→5 Previous Phase sections; v0.15.0…v0.7.9 moved verbatim to `docs/archive/STATE-history.md` (first application of the v0.18.2 bounded-history trim rule); 1362→~360 lines.
- Memory 2-tier honesty: §Rules 5 labels mem-search permanent persistence as unimplemented (scripts make zero mem-search calls; STATE.md Known gaps).

### Added — ref-pattern adoption

- **Approach-altitude gate** (from compound-engineering v3.11.1): `/athanor:plan` Step 1 recognizes "plan the approach / 방법부터 계획" requests before deliverable planning; detail + proactive gating in `skills/plan/references/approach-altitude.md`.
- **Review section carving** (from gstack v1.56 STOP-Read): `/athanor:review` lens personas + doc-review mode carved to `skills/review/references/review-sections.md`, loaded on demand after lens selection; SKILL 418→311 lines, decision-brief format preserved.

### Notes

- 16 new regression tests; full suite 932 passed, 0 failed. B-6 (concepts orphan) and B-8 (defense label) were verified **false positives** — no change. autoresearch dangerous-cmd / privacy-block found **already covered** by the existing PreToolUse kernel guard. A-4 (kernel-guard extension) + B-7/B-9 deferred to ROADMAP.

## [0.18.2] — 2026-06-04

### Fixed — lfg/lfg-goal doc-lifecycle audit (read→exec / exec→doc / cleanup)

- **D13 broken cross-reference (High):** `agents/cleaner.md` gains a "Clean Old Goals" step — `skills/lfg-goal/SKILL.md` claimed the cleaner ages out stale `.athanor/goals/` per D13, but no such step existed (Step 4 cleaned only sessions). It now ages out non-completing (`aborted`/`abandoned`) goals past `goalRetentionDays`; `complete` goals are excluded (deleting their live tree stays a user action). Dispatch prompt in `learner-cleaner.md` synced.
- **Cleaner model drift:** dispatch tier `sonnet` → `haiku` to match `agents/cleaner.md` frontmatter + CLAUDE.md "Cleaner: minimal effort".
- **Completion archival:** completed-goal `receipts/` now archived to `docs/goals-completed/<id>/` alongside `goal.md` + `goal-completion.md` (the externally-verifiable evidence trail survives).
- **learner-on-release:** wired into the release ceremony (`agents/releaser.md` Step 6, leader-follow-up dispatch) — previously a dormant, never-triggered contract.

### Added — documentation lifecycle

- **Migration-guide staleness:** `status: historical|current` + `superseded-by:` frontmatter on `docs/v*-migration.md`; `docs/CONVENTIONS.md §7` rule; a regression test is the automatic ager (a guide older than the current plugin minor left `current` fails CI). v0.12.0 / v0.17.0 marked historical.
- **STATE.md bounded-history trim:** `agents/releaser.md` Step 3 caps retained `## Previous Phase` sections (5), moving surplus non-destructively to `docs/archive/STATE-history.md` — progressive, not retroactive.
- **lfg PR-body persistence:** Step 7 PR template carries work-log + review summary slots so the work record survives in git after the gitignored session tree is cleaned.

### Notes

- 16 new regression tests (7 files); every defect implemented RED→GREEN. Cleanup/trigger layers are advisory (prose-driven), matching athanor's defense-mechanism honesty labels. The pre-existing STATE.md 28-section backlog is trimmed progressively, not in this release.

## [0.18.1] — 2026-05-31

### Changed — Agent inventory audit + concept absorption (Goal 36470e54)

- ref agent evaluation (ECC 259/68, CE 43, autoresearch 1, gstack/superpowers 0): **0 wholesale adoptions** — all subsumed by reviewer 6-lens/critic/researcher/learner, out of scope, or Thin-Leader-incompatible. Consistent with v0.12.0 concept-absorption policy. See docs/agent-evaluation-matrix.md.
- Concept absorption (prose, not new agents): reviewer quality lens gains silent-failure (swallowed-error/empty-catch, ex-ECC) + project-standards (repo CLAUDE.md audit, ex-CE) heuristics.
- Agent inventory clarified: dual-nature (inline-dispatch reference docs + @-mention registered types) + COLLISION GUARD rationale documented (CLAUDE.md + docs/archive/agent-dual-nature.md). All 11 agents KEPT, 0 removed.

## [0.18.0] — 2026-05-29

### Added — Freeze-First (Plan B base)

**Freeze infrastructure (Phase 1-2):**
- `scripts/work/build_freeze_allowlist.py` — per-session allowlist builder from Splitter `files:` declarations
- `scripts/hooks/pretool_dispatcher.py` — single-outer-entry PreToolUse dispatcher
- `scripts/hooks/freeze_guard.py` — Claude file-tool allowlist (Edit/Write/MultiEdit + conservative Bash patterns)
- `hooks.freeze` config block in athanor.json + schema (default `mode = "off"`, opt-in)

**Architecture decisions (per Critic synthesis):**
- Kernel guard runs FIRST in dispatcher (v0.16.0 catastrophic class never over-ruled)
- Kernel guard fail-CLOSED on missing config preserved (v0.16.0 default unchanged)
- Freeze guard fail-open on missing allowlist (opt-in semantics)

### Honesty Residuals (intentional scope limits)

- **D2: Codex stage uneven enforcement** — `/athanor:lfg` Codex subprocess writes are NOT gated by Freeze. Freeze is documented as "Claude file-tool allowlist", not a comprehensive editing envelope.
- **Bash subprocess writes ungated** — `python -c "open('foo', 'w')..."`, `make build`, `codex exec`, etc. NOT detected. Documented in `skills/work/references/freeze.md`.

### Deferred (per Critic synthesis, both reviewers converged)

- **v0.18.1 — git-worktree isolation** — admission criteria: (a) freeze-violations.jsonl >= 10 across >= 5 sessions, OR (b) 1 user-reported issue with repro, OR (c) `/athanor:work --team` same-file collision documented
- **v0.18.2 — UserPromptSubmit injection** — design precondition: live spike capturing real payload shape (v0.17.0 capability_probe shows UPS supported=false passively)

### Tests
- 692 -> 872 (+180 new)
- 11 new regression tests: builder, schema, splitter contract, kernel evaluate_payload, dispatcher, freeze_guard, Phase 2 integration, static dedup preservation

### Planning
- Deep-tier adversarial plan: Planner A (Claude) + Planner B (Codex) + cross-review + Critic synthesis
- Plan B base (Freeze-First) + Plan A Phase 2 architecture (corrected per Codex review) + reviewer convergence on stage shipping

## [0.17.0] — 2026-05-28

### Changed — Surface Cut + Capability Spikes

**Big skill splits (S01 + S02):**
- `skills/work/SKILL.md`: 1153 → 250 lines (router) + 5 references files (multi-status, spec-then-tdd-handler, splitter, team-mode, learner-cleaner)
- `skills/plan/SKILL.md`: 1255 → 300 lines (router) + 7 references files (planner-dispatch, reviewer-dispatch, critic-variants, codex-availability, critic-rubric, presentation, depth-flag-dispatch)

**Command surface simplification (S07):**
- `/athanor:deep-plan` and `/athanor:lite-plan` collapsed into `/athanor:plan --depth={standard|deep|lite}` and `/athanor:plan --no-review`
- Trigger keywords preserved on `/athanor:plan` for muscle memory
- Migration guide: `docs/v0.17.0-migration.md`

**Documentation hoisting (S04 + S05):**
- using-superpowers boundary: 11× verbatim → CLAUDE.md canonical + 9 pointer refs
- Spec-then-TDD discipline: 4-location dedup → CLAUDE.md canonical + brief pointers in plan/work/executor
- NOTICE.md LIFT entries compressed to 1-line attributions

**Vendoring cleanup (S03):**
- `agents/vendored/ce/*.agent.md` removed (dead vendoring, zero live dispatch)

**Infrastructure (S06 + S08):**
- NEW: `scripts/hooks/_athanor_hook_runtime.py` shared runtime helpers (read_stdin_payload, read_athanor_config, is_hook_profile_off, resolve_project_root)
- NEW: `scripts/hooks/capability_probe.py` passive hook capability probe → emits `.athanor/hook-capability.json`
- stop_verify_claims.py + pretool_kernel_guard.py refactored to use shared runtime (behavior preserved)

**Config diet (S09):**
- All `_doc` inline documentation fields removed from `athanor.json` and `templates/athanor.json` (athanor.json 4897 → 1153 bytes)
- Schema description fields remain canonical inline docs

### Tests
- 644 → 692+ passed (S04 689, S08 692, S09 682 with deletion)
- NEW: test_regression_v017_work_skill_split, test_regression_s02_plan_skill_split, test_regression_v017_hook_runtime, test_regression_v017_capability_probe, test_regression_s07_depth_flag_collapse
- REMOVED: tests/test_regression_doc_string_honesty.py (S09)

### Planning
- Deep-tier adversarial plan: Planner A (Claude) + Planner B (Codex) + cross-review + Critic synthesis
- REMOVE-first ordering per Plan B + Plan A's test-cascade rigor
- 3-release roadmap: v0.17.0 (this) → v0.18.0 (hook additions) → v0.19.0 (evidence-bound discipline)

### Identity invariants (unchanged)

Thin Leader / cross-model adversarial planning / Spec-then-TDD discipline / Stop hook runtime gate. Companion-fix arc 5-layer (v0.11.3 → v0.11.8) untouched.

## [0.16.0] — 2026-05-28

### Added — Multi-Status Executor

- `/athanor:work` now distinguishes four worker completion statuses:
  - `done` — subtask complete, evidence shape valid
  - `done_with_concerns` — subtask complete but worker flagged residuals worth surfacing
  - `needs_context` — worker requires additional inputs before it can proceed
  - `blocked` — external dependency or unresolved decision halts progress
- New `blocked_queue` lets the leader route partial completions without flattening to binary success/failure. The Phase 3 gate (conjunction of three signals) still applies to `done` and `done_with_concerns`; `needs_context` / `blocked` defer through the queue instead of marking the subtask success or failure.

### Added — PreToolUse Kernel Guard (3-class safety)

- New PreToolUse hook intercepts tool invocations before they reach the runtime and blocks three classes of operation:
  1. **Destructive shell** — `rm -rf` against tracked paths, `find -delete` on broad globs, `dd of=`, and equivalent patterns.
  2. **Force-push** — `git push --force` / `git push -f` against protected branches (main/master + remote tracking).
  3. **Credentials** — reads / writes that traverse `.env*`, `~/.aws/credentials`, `~/.ssh/`, `*.pem`, and similar.
- Sits alongside the existing Stop hook gate; both are command-based and honour `athanor.json` `hooks.profile: "off"` for per-project opt-out.

### Changed — CLAUDE.md Token Diet

- CLAUDE.md slimmed from ~534 → ~175 lines. The file is now a contract index (Session Lookup Convention, Defense Mechanisms Status table, 4 identity invariants enumeration, Concept Absorption Surface anchor) — not a prose source-of-truth dump.
- Heavyweight prose moved to `docs/archive/`:
  - `stop-hook-postmortem.md` — companion-fix arc v0.11.3 → v0.11.8 detail
  - `concept-absorption-surface.md` — full v0.12.0 cutover ledger
  - `defense-mechanisms-detail.md` — Stop hook detection pipeline + Spec-then-TDD operational detail + scope-drift trigger glob
- Pinned by new `tests/test_regression_v016_claude_md_contract.py`:
  - line count band [145, 175]
  - §"Session Lookup Convention" anchor
  - §"Defense Mechanisms" + §"Status table" subsection
  - 4 identity invariants by literal name
  - 3 archive companion files exist

### Tests

- Total: 639 → 644 (+5 ST16). Additional coverage shipped alongside the executor and kernel-guard work landed earlier in the cycle.
- New file: `tests/test_regression_v016_claude_md_contract.py` (5 tests).
- Version-pinned tests updated: `test_regression_v014_release_smoke.py` (`TARGET_VERSION = "0.16.0"`), `test_regression_v013_release_smoke.py` (plugin.json version assert), `test_regression_v013_1_codex_hang.py` (`test_schema_id_v0160_bump`), `test_regression_v012_honesty_voice.py` (whitelist now accepts 0.16.x in `## Current Phase`).

### Identity invariants (unchanged)

Thin Leader / cross-model adversarial planning / Spec-then-TDD discipline / Stop hook runtime gate. Companion-fix arc 5-layer (v0.11.3 → v0.11.8) untouched.

## [0.15.1] — 2026-05-28

### Changed
- `/athanor:lfg` Step 2 now invokes `/athanor:work --team` by default (wave-parallel execution). Users may override with `--solo`. Global `work.defaultMode` remains `"solo"` — only the LFG pipeline defaults to team mode.

### Fixed — Stale Reference Sweep
- 5 stale `§"Vendored Surface — Identity Guard Layer"` cross-references updated to `§"Concept Absorption Surface"` across `stop_verify_claims.py`, `plan/SKILL.md`, `work/SKILL.md`, `discuss/references/requirements-capture.md`, `discuss/references/clarify-gap-probes.md`
- `.claude-plugin/plugin.json` keywords: removed stale `vendored-ce`, `vendored-superpowers`; added `team-mode`, `wave-parallel`
- `codex._doc` deferral text: `"deferred to v0.15+"` → `"deferred to v0.16+"` across `athanor.json`, `templates/athanor.json`, `schemas/athanor-config.schema.json`

### Added
- `tests/test_regression_v015_1_lfg_team_default.py` — 5 regression tests (team flag, solo default lock, keyword cleanup, deferral text)
- Extended H1 stale-reference test scope from 2 → 7 files

### Planning
- Standard tier: Planner A (Claude) + Codex review + Critic refinement
- Codex review scoped down Phase 1 from global default change to LFG-only flag

## [0.15.0] — 2026-05-28

### Fixed — LFG Pipeline Contract Reconciliation (22-bug eradication)

**CRITICAL (3):**
- **C1:** No-progress circuit breaker moved inside `for cycle` loop (was dead code outside loop) — `skills/lfg-goal/SKILL.md`
- **C2:** Aggregate status enum unified to `all_valid | completed_with_residuals | invalid_steps_present` across SKILL.md, receipt-validator.md, state-shape.md, and test fixtures
- **C3:** `cycle_phase` 7-value enum added to `state-shape.md` with Tier 3 goal_complete fix, 4-value last_validator_status, and cycle_phase-aware resume semantics

**HIGH (5):**
- **H1:** Stale "Vendored Surface — Identity Guard Layer" → "Concept Absorption Surface" in both LFG skills
- **H2:** Thin Leader violation in `/athanor:lfg` Step 3 → worker dispatch via `/athanor:work`
- **H3:** Thin Leader violation in `/athanor:lfg` Step 8 → `athanor-ci-watcher` agent dispatch
- **H4:** Stale `/athanor:ce-lfg` comparison → historical note (post-v0.12.0) + test updated
- **H5:** Stale `docs/plans/` in Step 1 GATE → `.athanor/sessions/<id>/plan.md` only

**MEDIUM (8):**
- **M1:** Resume rules completed for all 7 `cycle_phase` values (receipt_validated added, tier1→Tier 2 fixed)
- **M2:** Pseudocode handles 3-value aggregate branch (was 1-value only)
- **M3:** Schema `archiveOnComplete` path aligned to `docs/goals-completed/<id>/`
- **M4:** STATE.md config key `lfg-goal.maxIterations` → `lfgGoal.maxIterations`
- **M5:** `gh pr checks --watch` wrapped with `timeout 600s` (no native --timeout flag)
- **M6:** Korean raw-message position mapping bug in `stop_verify_claims.py` — re-derive position in normalized text for suppression context check (v0.14.2 EN fix extended to KO path)
- **M7:** `Write` added to `/athanor:lfg` allowed-tools frontmatter
- **M8:** CLAUDE.md Commands table updated: sole pipeline post-v0.12.0, stale ce-plan/ce-work refs removed

**LOW (6):**
- **L1:** Nonce TTL documentation aligned to 120s across 3 files
- **L2:** Zero-remote fallback added to Step 4
- **L3:** Push-failure handling added to Step 7
- **L4:** Prose-only enforcement transparency notes on 3-iteration clauses
- **L5:** Explicit `gh run list` run-id extraction in Step 8 (replaces bare placeholder)
- **L6:** LFG dispatcher back-references added to ci-watcher.md and releaser.md

### Added
- `tests/test_regression_v015_lfg_bug_eradication.py` — 21 regression tests locking all 22 bug fixes
- Updated `tests/test_regression_v013_lfg_goal_receipt_contract.py` (+1 test: 3-value aggregate)
- Updated `tests/test_regression_v013_lfg_goal_skill.py` (+1 test: 7-value cycle_phase resume)

### Planning
- Deep-tier adversarial plan: Planner A (Claude) + Planner B (Codex) + cross-review + Critic synthesis
- Contract-kernel-first execution: xfail tests (Phase 0) → schemas (Phase 1) → SKILL.md (Phase 2) → Python (Phase 3) → docs (Phase 4) → sweep (Phase 5)
- 5-lens parallel review (security 8/10, architecture 8/10, testing 8/10, quality 8/10, documentation 7/10)

## [0.14.3] — 2026-05-26

### Fixed
- **G4: Version manifest drift** — 5 manifest files (`plugin.json`,
  `marketplace.json`, `athanor.json` `$schema`, `templates/athanor.json`
  `$schema`, `schemas/athanor-config.schema.json` `$id`) were stuck at
  0.14.0 through v0.14.2; bumped atomically to 0.14.3.
- **G5: CHANGELOG test count correction** — v0.14.0 entry claimed
  "20 tests" for `test_regression_v014_agent_definitions.py` (actual: 9)
  and "7 tests" for `test_regression_v014_release_smoke.py` (actual: 3);
  corrected in place.
- **G6: Agent definition honesty framing** — v0.14.0 Honesty note now
  distinguishes `codex-dispatcher.md` (reference for existing inline
  implementation in `skills/plan/SKILL.md`) from `releaser.md` +
  `ci-watcher.md` (dispatch-contract reference documents with no inline
  implementation yet).

### Changed
- Test pins bumped: `test_schema_id` → 0.14.3, `test_v013_release_surface`
  version pin → 0.14.3, `test_v014_version_consistent` TARGET_VERSION →
  0.14.3.
- `docs/STATE.md` Current Phase → v0.14.3; v0.14.2 as Previous.

### Honesty note
- Documentation/version hygiene patch — 4 identity invariants intact,
  companion-fix arc untouched.

## [0.14.2] — 2026-05-26

### Fixed
- **G1: `check_release_ready.py` version source** — script read version
  from `athanor.json` top-level `version` field (config schema version
  "1.0"), not the plugin version; switched to `.claude-plugin/plugin.json`.
- **G2: `check_release_ready.py` CHANGELOG heading format** — parser
  expected `## v0.X.Y` but CHANGELOG uses `## [0.X.Y]`; regex updated to
  match both bracket and bare formats.
- **G3: `test_regression_v010_namespace_layout.py` `check_release_ready`
  import** — test imported the script as a module but the script lacked
  `if __name__` guard and function entry points; added `main()` function
  and `__main__` guard.

### Honesty note
- Infrastructure bug fix patch — 4 identity invariants intact,
  companion-fix arc untouched.

## [0.14.0] — 2026-05-24

### Added
- 3 new native agent definitions:
  - `agents/releaser.md` — Release ceremony automation (5-file version bump,
    CHANGELOG, STATE.md rotation, test pin updates, release-ready verification)
  - `agents/codex-dispatcher.md` — Codex CLI dispatch wrapper with timeout
    clamping (1-600s), stdin redirect (`< /dev/null`), and structured exit-code
    handling. Enforces "Worker prompts must not depend on Leader shell variables"
    convention discovered in v0.13.2.
  - `agents/ci-watcher.md` — CI watch + autofix loop (gh pr checks, failure log
    analysis, fix dispatch, residual escalation)
- Cross-reference notes in `skills/plan/SKILL.md` (codex-dispatcher) and
  `skills/lfg/SKILL.md` (releaser + ci-watcher)
- `tests/test_regression_v014_agent_definitions.py` (9 tests)
- `tests/test_regression_v014_release_smoke.py` (3 tests)

### Changed
- `CLAUDE.md` updated with native agent inventory (11 agents total: 8 existing + 3 new)
- `fallbackAfterMs` deferral re-targeted from v0.14+ to v0.15+ (codex-dispatcher agent
  is an agent definition, not the async-join implementation that fallbackAfterMs requires)
- Codex dispatcher extraction (v0.13.2 Plan B) is realized as an agent REFERENCE
  DEFINITION — the inline codex invocation in `skills/plan/SKILL.md` remains the
  canonical implementation. Full extraction deferred to v0.15+.

### Honesty note
- Agent definition files describe the agent's PURPOSE, TOOLS, and DISPATCH CONTRACT.
  Implementation status differs per agent:
  - `codex-dispatcher.md` — reference document for the inline implementation already
    present in `skills/plan/SKILL.md` (Planner B + Reviewer B codex dispatch blocks);
    full extraction into a standalone dispatcher deferred to v0.15+.
  - `releaser.md` + `ci-watcher.md` — dispatch-contract reference documents only;
    no inline implementation exists yet in any skill file. These define the agent
    shape for future Leader dispatch.
- 4 identity invariants intact. Companion-fix arc untouched.

## [0.13.2] — 2026-05-24

### Fixed
- `${CODEX_TIMEOUT_S}` phantom variable in Worker bash blocks — Worker's
  clean-context Agent() dispatch has no access to Leader's Step 0 shell
  variables. Fix: each Worker bash block now computes timeout inline via
  `jq` with value clamping (1-600s, default 300s fallback).
- Korean paraphrase regex suffix mismatch in Stop hook — `(?:했|함|됨)`
  was mandatory, missing particle-inserted base forms like "테스트가 모두
  통과". Fix: suffix group made optional with `?` (2-char edit).
- `codex.timeoutMs` schema lacked upper bound — added `"maximum": 600000`
  (10 min ceiling matching Bash tool's own limit).

### Added
- `tests/test_regression_v013_2_korean_regex.py` (5 tests locking Korean
  base-form + suffixed-form + full-pipeline detection).
- 4 new tests in `tests/test_regression_v013_1_codex_hang.py`: inline-jq
  self-containment + clamping bounds + schema maximum + clamping consistency.

### Changed
- CHANGELOG v0.13.1 entry: removed internal "ST15 scope" planning identifier.
- `skills/discuss/SKILL.md` Step 0: "kept in sync" comment corrected to "subset".
- `test_no_deprecated_full_auto_flag` prose assertion relaxed to flexible regex.

### Honesty note
- Bug fix patch — 4 identity invariants intact, companion-fix arc untouched.
- Discovered convention: **Worker prompts must not depend on Leader shell
  variables** — `Agent()` dispatch creates clean context. Codex dispatcher
  extraction deferred to v0.15+ (Plan B architectural insight captured).

## [0.13.1] — 2026-05-23

### Fixed
- Codex CLI stdin EOF deadlock (GitHub Issue #20919) — added `< /dev/null`
  redirect to all `codex exec` invocations (`skills/plan/SKILL.md` Planner B
  + Reviewer B blocks) and `codex --version` probes (`skills/plan/SKILL.md`
  Step 0 + `skills/discuss/SKILL.md` line 397). Prevents `readFileSync(0)`
  hang in non-TTY environments where Bash tool dispatches inherit stdin.
- Migrated deprecated `--full-auto` flag (removed in codex CLI 0.133.0) to
  top-level `codex -a never -s workspace-write exec …` form per empirical
  byte-capture of `codex --help` and `codex exec --help` output.
- Replaced prose-only "(timeout 300000ms)" comment with shell-level
  `timeout 300s` prefix as PRIMARY hard wall-clock fence; Bash-tool
  `timeout: 300000` parameter remains as belt-and-suspenders secondary.

### Added
- `codex.timeoutMs` config key in `athanor.json` (default 300000) wired
  through Step 0 probe with seconds conversion (`CODEX_TIMEOUT_S`) and
  schema validation (minimum 1000ms).
- New regression test file `tests/test_regression_v013_1_codex_hang.py`
  (11 tests, ~470 LOC): prose-grep redirect/flag/timeout audits +
  schema/probe contract locks + deterministic static text-level redirect
  verification.

### Changed
- Schema `$id` v0.13.0 → v0.13.1 (`schemas/athanor-config.schema.json`).
- `tests/test_regression_plan_reads_requirements_md.py:182` regex anchor
  made flag-agnostic to survive future codex CLI flag tweaks.
- `tests/test_regression_v013_release_smoke.py:34` version pin bumped
  to 0.13.1.
- Stale doc references in `docs/CONVENTIONS.md`, `docs/DESIGN.md`,
  `docs/ROADMAP.md` updated to v0.13.1 canonical codex command form
.

### Honesty note
- This is an operational hardening patch — 4 athanor identity invariants
  intact (Thin Leader / cross-model adversarial / Spec-then-TDD / Stop
  hook gate), companion-fix arc 5 layer (v0.11.3 → v0.11.8) untouched.
- **v0.13.1 intentionally ships `timeoutMs` only.** `fallbackAfterMs`
  (leader-side soft deadline) requires async join infrastructure absent
  in current synchronous Bash-dispatch model; deferred to v0.15+.
- **Minimum codex CLI version required: 0.133.0+.** The
  `-a never -s workspace-write` top-level flag form requires codex CLI
  0.133.0 or later. Users with older CLI versions will see dispatch
  failures attributed to "codex unavailable" — the actual cause is
  version mismatch. Step 0 probe currently does NOT version-gate (only
  checks CLI presence); explicit version detection deferred to v0.15+.
- Pre-edit byte-capture artifact (`/tmp/codex-{top,exec}-help.txt` from
  CLI 0.133.0) was used to empirically verify flag positions before
  migration — locked in `.athanor/sessions/2026-05-23-001/discoveries/
  worker-3-codex-cli-shape.md` for future PR audit trail.

## [0.13.0] — 2026-05-23

**Goal-driven Validated Ralph Loop.** New athanor-native skill `/athanor:lfg-goal` combines (a) a user-stated goal + (b) macro Ralph loop + (c) existing /athanor:lfg pipeline. Runs lfg cycles until the goal is met or guards trip.

The skill is an **orchestration layer** over the existing 4 identity invariants — no new invariant added (D11). Receipt-arithmetic + dispatched receipt-validator + 3-tier adversarial goal-check close the leader-discretion loophole exposed during v0.12.0 ship: a cycle that skipped /athanor:lfg Step 3 (review) cannot produce a valid receipt, and the validator dispatches Bash verification commands the leader cannot fabricate.

### Added
- `skills/lfg-goal/SKILL.md` (657 lines) — full skill spec covering Validated Receipt-Ledger Loop architecture, 9-step receipt format, 3-tier goal-completion check, scope-change protocol, resume/abort semantics, 4-identity-invariant survival check, honesty note on physical enforcement scope.
- `skills/lfg-goal/references/` — 5 worker dispatch prompt templates:
  - `receipt-validator.md` (9-step Bash verification command table; dispatched after each cycle)
  - `judge-rubric.md` (Tier 2 cross-model judge-A Claude + judge-B Codex)
  - `scope-change-critic.md` (accept/reject/escalate on mid-flight goal edits)
  - `state-shape.md` (state.json format for resume/abort)
  - `goal-md-template.md` (canonical goal.md structure with mandatory Verify command + Test-count command)
- `lfgGoal.*` config block in `athanor.json` + `templates/athanor.json` with 11 fields (maxIterations=5 per D8 / consolidateCycles=false per D9 / both invocation forms per D10 / scopeDriftAutoCheck=true per D12 / tier3UserRatification=true per D6)
- Schema `lfgGoal` sub-schema in `schemas/athanor-config.schema.json` (11 fields with descriptions)
- 3 new regression test files (`tests/test_regression_v013_lfg_goal_*.py`) covering skill surface, receipt contract, config validation — 22 tests total
- 3 receipt fixtures (`tests/fixtures/lfg_goal/receipt_{valid,invalid_missing_step3,partial_with_residuals}.md`)

### Changed
- `CLAUDE.md`: Commands table +/athanor:lfg-goal row (11 user-invocable skills now); "10 Thin Leader skill" → "11 Thin Leader skill" prose update with lfg-goal added to enumerated lists
- `NOTICE.md`: new §"Native syntheses (not lifted)" section with /athanor:lfg-goal entry (internal synthesis, no upstream attribution)
- `tests/test_regression_v011_1_using_superpowers_boundary.py`: NATIVE_THIN_LEADER_SKILLS tuple extended 10 → 11 (lfg-goal added)

### Voice (what v0.13.0 deliberately does NOT do)
- Does NOT add a 5th identity invariant — lfg-goal is orchestration over the existing 4 (Thin Leader / cross-model adversarial planning / Spec-then-TDD / Stop hook runtime gate). D11 makes this explicit in the skill body.
- Does NOT modify `/athanor:lfg` — lfg-goal calls lfg verbatim then dispatches the validator + judges (Plan B Phase 4 dropped per D2).
- Does NOT auto-bypass user ratification — Tier 3 user-confirm is BLOCKING by default (D6); only an explicit flag disables it.
- Does NOT introduce a JSON-to-prompt templating engine — all worker prompts are .md references embedded in Agent() dispatches by the leader (D3 inventory-only principle preserved from v0.12.0).
- Does NOT touch `skills/scope-drift/SKILL.md` — scope-drift is consumed read-only by lfg-goal Phase 6 integration (D12).
- Does NOT silently mutate the v0.12.0 frozen-snapshot test (`tests/test_regression_v012_native_identity_surface.py`); v0.13.0 adds its own dedicated test files instead.

### Honesty note
The 3-layer architecture (goal ledger + dispatched receipt-validator + 3-tier check) is **advisory orchestration**, not runtime enforcement. The Stop hook fires per cycle as before; cycle validity is leader-discretion bounded by receipt-evidence Bash commands that are externally verifiable but not runtime-gated. Adversarial forgery of receipt evidence remains a residual; full hard-enforcement of receipt authenticity deferred to v0.13.x+.

### Deferred to v0.13.x+
- Stop hook runtime gate for receipt presence (currently advisory)
- Multi-goal parallel execution (lfg-goal is single-goal per session)
- Cleaner agent integration for `goalRetentionDays` aging (config field declared but cleaner not yet extended)
- Goal templates library (`goals/templates/`) for common goal shapes

### Migration
No breaking changes. Existing /athanor:lfg invocations continue to work identically. /athanor:lfg-goal is opt-in via explicit invocation.

### Session
Plan: `.athanor/sessions/2026-05-22-002/plan.md` (deep-tier: Claude Planner A + Codex Planner B + cross-review + Critic; 15 subtasks via Splitter)
Decisions: D1-D14 audit trail in decisions.md

## [0.12.0] — 2026-05-22

### Honesty Framing

v0.10.0 plan-of-record misread the user's concept-absorption intent as wholesale plugin vendoring. v0.12.0 is the scope correction.

7 release cycles (v0.10.0 ~ v0.11.7) shipped 33 compound-engineering skills + 13 superpowers skills + 49 vendored sub-agents on a plan-of-record that converted a concept-absorption ask into a 95-item plugin marketplace. The companion-fix arc (v0.11.3 ~ v0.11.7) closed real Stop hook bugs on top of that over-scoped surface; the work was real, the product surface was wrong. v0.11.8 staged the deprecation warnings. v0.12.0 atomically removes the wrong surface and lifts the genuinely valuable concepts into athanor-native skills as prose subsections, with `concepts/` as the inventory ledger.

97% vendored surface reduction: from 95 items (33 ce-* + 13 sp-* + 49 sub-agents) down to 3 (1 KEEP skill + 2 KEEP sub-agents).

### Added

- 5 LIFTs into athanor-native skills:
  - `skills/review/SKILL.md` §"Personas" — 6-persona vocabulary (correctness/security/performance/testing/maintainability/adversarial), lifted from `ce-code-review@3.8.3`
  - `skills/review/SKILL.md` §"Doc review mode" — 7-lens doc persona array + `--target docs` CLI, lifted from `ce-doc-review@3.8.3`
  - `skills/debug/SKILL.md` §"Systematic Debugging Discipline" — Iron Law + Four Phases + "3+ fixes = architectural question" rule, lifted from `sp-systematic-debugging@5.1.0`
  - `skills/discuss/references/requirements-capture.md` — R-ID / A-ID / F-ID / AE-ID structure (v0.9.0 concept absorption; v0.12.0 attribution formalized) from `ce-brainstorm@3.8.3`
  - CLAUDE.md §"using-superpowers boundary (v0.11.1)" — concept formalization + attribution to `sp-using-superpowers@5.1.0`
- `concepts/` inventory directory (7 files: README + 6 concept-attribution docs) — pure traceability ledger; NOT a runtime data layer
- `docs/archive/v010-v011-vendoring-scope-correction.md` — Honesty Ledger retrospective (Subtask 1)
- `docs/architecture/v012-concept-absorption.md` — forward-looking architecture doc (Subtask 2)
- `scripts/v012_remove_vendored.py` — atomic removal script (Subtask 14)
- `tests/test_regression_v012_*.py` — 7+ new regression test files covering: no-vendored-surface assertions, native-identity-surface assertions, LIFT concept presence, concepts/ inventory shape, review.personas schema enum, removal-script smoke, release-ready gates, NOTICE attribution survival, honesty-voice presence
- `scripts/check_release_ready.py` extended with 3 new v0.12.0 surface gates (vendored skill count = 1, marketplace count match, concepts/ present)

### Changed

- `athanor.json` schema: added `review.personas` array (enum of 6 values)
- `scripts/hooks/stop_verify_claims.py`: added v0.11.8 deprecation sentinel carve-out (Subtask 6); preserved v0.11.3 transcript_path parser, v0.11.6 body-hash normalization, v0.11.7 B1 mutation detection — all intact
- `scripts/check_vendor_drift.py`: scope shrunk to 1-KEEP (`ce-test-browser`) — preserved per Subtask 15 alignment; v0.11.8 deprecation block strip added (Subtask 6)
- `NOTICE.md`: added §"Concepts adopted from upstream (post-v0.12.0)" enumerating 5 LIFT entries with MIT attribution preserved
- `.claude-plugin/marketplace.json`: description refreshed to v0.12.0 scope-correction reality (NOT "33 ce-* + 13 sp-*")

### Removed

- 45 vendored skill directories (`skills/ce-*` + `skills/sp-*`) — 5 LIFT-source + 40 DROP. Preserve: `skills/ce-test-browser/` per D8.
- 47 vendored sub-agent files under `agents/vendored/ce/`. Preserve: `ce-git-history-analyzer.agent.md` + `ce-repo-research-analyst.agent.md`.
- Per D9: `ce-plan`, `ce-work`, `ce-lfg` are FULL DROP (no THIN-ADAPTER stubs).
- `tests/test_regression_v010_vendor_provenance.py` + `tests/test_regression_v010_1_vendor_provenance_sha.py` (scope shrunk too far post-removal)

### Migration

Users who invoke `/athanor:ce-*` or `/athanor:sp-*` (any except `/athanor:ce-test-browser`): the skill is no longer present. See `docs/v0.12.0-migration.md` (Subtask 19) for the migration target table.

Common migrations:

- `/athanor:ce-plan` / `/athanor:ce-work` / `/athanor:ce-lfg` → use `/athanor:plan` / `/athanor:work` / `/athanor:lfg` (athanor-native equivalents with cross-model adversarial planning + Spec-then-TDD discipline)
- `/athanor:ce-code-review` → use `/athanor:review` (now includes `review.personas[]` array for explicit persona dispatch)
- `/athanor:sp-systematic-debugging` → use `/athanor:debug` (now includes "Systematic Debugging Discipline" subsection with Iron Law + Four Phases)
- Other removed skills: install `compound-engineering` or `superpowers` plugins directly if you need them — athanor v0.12.0 stands alone as a Thin Leader orchestrator

### Voice (what v0.12.0 deliberately does NOT do)

- Does NOT invalidate the v0.11.3 ~ v0.11.7 companion-fix arc; those Stop hook bugs were real and their fixes survive intact (`scripts/hooks/stop_verify_claims.py` + all v0.11.3-v0.11.7 regression tests preserved)
- Does NOT erase the over-scope from history; `docs/archive/v010-v011-vendoring-scope-correction.md` is the durable retrospective
- Does NOT touch the 1 KEEP-class skill `/athanor:ce-test-browser` (per D8 — user opt-in browser automation outside athanor identity)
- Does NOT introduce a JSON-to-prompt templating engine; `concepts/` is .md inventory only (D3)
- Does NOT lower the four identity invariants (Thin Leader + cross-model adversarial planning + Spec-then-TDD + Stop hook runtime gate) — they are reinforced by the smaller surface

### Self-violation acknowledgment

This is the scope-correction release. The v0.10.0 plan-of-record misread the user's request, and 7 release cycles shipped on that misread before the user re-stated the intent. v0.12.0 is the honest correction. The companion-fix arc work (v0.11.3 ~ v0.11.7) closed real Stop hook gaps on the over-scoped surface; it survives the pivot.

## [0.11.8] — 2026-05-22

**Deprecation warning cycle for v0.12.0 atomic scope-correction cut.** No functional changes. 45 vendored skills marked with a deprecation preamble — users invoking these skills now see an in-skill ⚠ DEPRECATION notice pointing at the migration target (or "no athanor-native migration" for DROP-class).

### Added

- `scripts/v011_8_deprecation_preamble.py` — idempotent injection of deprecation sentinel + 4-line preamble into 45 SKILL.md files (5 LIFT + 40 DROP). KEEP-class `ce-test-browser` (per D8) is the carve-out.
- `tests/test_regression_v011_8_deprecation_preamble.py` — 12-test regression suite covering preamble shape + idempotency + Stop hook carve-out + vendor drift carve-out.
- `docs/archive/v010-v011-vendoring-scope-correction.md` — Honesty Ledger archive (v0.10.0 plan-of-record misread retrospective + companion-fix arc preservation).
- `docs/architecture/v012-concept-absorption.md` — forward-looking architecture doc for the v0.12.0 pivot (4 identity invariants + concepts/ inventory role + 3-item post-pivot surface).
- `.athanor/sessions/2026-05-22-001/disk-inventory.txt` — disk-derived count audit (33 ce-* / 13 sp-* / 49 sub-agents / 46 tests at HEAD b3abc1f).

### Changed

- `scripts/hooks/stop_verify_claims.py` — added `<!-- athanor:deprecated v=1 since=0.11.8 removal=0.12.0 -->` early-return carve-out (placed after v=2 sentinel check, before material-claim detection; counter reset on hit). Does NOT alter v=2 sentinel handling, v0.11.3 transcript_path parser, v0.11.6 body-hash normalization, or v0.11.7 B1 mutation detection.
- `scripts/check_vendor_drift.py` — added `_strip_deprecation_block` (mirrors `_strip_provenance_block`). Wired into `_diff_skill` so the 4-line preamble does not register as upstream drift.

### Voice (what v0.11.8 deliberately does NOT do)

- Does NOT remove any vendored skill — atomic removal is v0.12.0
- Does NOT touch the 1 KEEP-class skill `ce-test-browser` (per D8 user decision)
- Does NOT lift any concepts into athanor-native skills — concept LIFT is v0.12.0 Phase 3
- Does NOT change the marketplace.json description shape — v0.12.0 will redo that
- Does NOT supersede v0.11.3 ~ v0.11.7 companion-fix arc

### Self-violation acknowledgment

This is the **honest correction cycle**. The v0.10.0 plan-of-record misread the user's concept-absorption intent as wholesale plugin vendoring, and 7 releases (v0.10.0 ~ v0.11.7) shipped on that misread. v0.11.8 is the deprecation-warning release that precedes the v0.12.0 atomic cut. The companion-fix arc (v0.11.3 ~ v0.11.7) closed real bugs on the over-scoped surface; that work survives the pivot (Stop hook script + all regression tests + Spec-then-TDD discipline + cross-model `/athanor:plan` intact).

### Migration

No user action required for v0.11.8. Users who currently invoke `/athanor:ce-*` or `/athanor:sp-*` will see a deprecation preamble in those skill files. v0.12.0 removes the skill directories — users should migrate to the listed `/athanor:` native equivalents (or install compound-engineering / superpowers plugins directly for tools without an athanor-native target).

### Deferred to v0.12.0

- Concept LIFT into athanor-native skills (review personas, debug discipline, requirements-capture, skill-discovery preamble)
- Vendored directory + sub-agent removal (40 DROP + 5 LIFT directories)
- NOTICE.md restructure
- `marketplace.json` description refresh
- 5-file version bump 0.11.8 → 0.12.0

## [0.11.7] — 2026-05-22

**Doc-drift scanner extension + Residual reclassification + minimal B1
inclusion — companion-fix arc 5th layer.** v0.11.5 shipped CLAUDE.md
drift-class invariants but the scanner was scoped only to Markdown
narrative; Python docstrings (notably `scripts/hooks/stop_verify_claims.py`)
and `docs/STATE.md` carried the same prose-vs-code drift pattern outside
the v0.11.5 net. v0.11.7 extends the scanner to Python docstrings via
`ast.get_docstring` + per-file extractors, audits `docs/STATE.md` and the
hook docstring for stale version pins, closes B2 (`stop_verify_claims.py:145`
"v0.11.0+" stale) and B5 (`CLAUDE.md:229` "v0.8.0+ work" stale), and
applies the v0.11.6 reclassification pattern to a documented broken
promise (B6: `CLAUDE.md:87` carry phrasing). Per Codex Reviewer push,
v0.11.7 also includes a minimal B1 detection layer — mid-session profile
mutation now produces a stderr warning without altering exit semantics —
so the 8-cycle "documented but not guarded" honesty residual gets a first
layer of closure now rather than deferring to v0.11.8+ architectural work.

### Honesty arc

The bugs were carried for 6 to 11+ release cycles each in a generic
"Residual known limitations" block in `scripts/hooks/stop_verify_claims.py`
and in `CLAUDE.md` §Known residuals — same anti-pattern v0.11.6 surfaced
("documented bug masked as enhancement candidate"). v0.11.7 reclassifies
each carried item with explicit Severity / Target / Acceptance labels —
no more anonymous "candidate" carry slots. B1 specifically: the docstring
said "not guarded" for 8+ cycles; v0.11.7 ships minimal detection (one
layer of closure) rather than another release of pure documentation.

### Companion-fix arc — 5 layers closed

| Layer | Release | Bug |
|---|---|---|
| Runtime stdin parser shape | v0.11.3 | script wrong |
| Hook command path resolution | v0.11.4 | path wrong |
| CLAUDE.md doc drift class | v0.11.5 | Markdown untestable claims |
| Sentinel body-hash binding | v0.11.6 | trailing-whitespace round-trip mismatch |
| **Scanner extension + Residual reclassification + B1 minimal** | **v0.11.7** | **Python docstrings + STATE.md outside scanner; documented bugs carried as anonymous "candidates"; profile mutation undetected** |

Shared meta-cause continues: documentation surfaces grow drift faster
than tests cover them; "Residual known limitations" was a hold-everything
bin where the v0.11.6 reclassification pattern needed to apply more
broadly. v0.11.7 trims the bin by labeling each entry with shippable
intent.

### Fixed

- **B2** — `scripts/hooks/stop_verify_claims.py:145` carried the stale
  pin "Known residual (v0.11.0+)" 11+ release cycles after the matching
  detection layers shipped through v0.10.2 / v0.10.3 / v0.11.3. Pin
  refreshed to reference current Residual table semantics; carry text
  removed in favour of the explicit Severity / Target / Acceptance
  Residual block below.
- **B5** — `CLAUDE.md:229` carried "v0.8.0+ work" phrasing on
  sentence-level attributed-history detection. That label has been stale
  since v0.10.3's attribution-context suppression shipped. Phrasing
  refreshed to the v0.11.7 reclassified label.
- **B6** — `CLAUDE.md:87` carried a "v0.11.0+ candidate" phrasing on a
  documented broken promise (LLM-class semantic similarity in detection
  whitelist). Reclassified with explicit "promised in v0.8.0 release
  notes but never implemented" honesty wording, matching the v0.11.6
  reclassification pattern. The work itself remains deferred but the
  classification drift is closed.

### Added

- **Phase 1 doc-drift scanner extension** — per-file extractors for
  Python docstrings via `ast.get_docstring` covering `scripts/hooks/*.py`
  + `docs/STATE.md` Markdown body. The v0.11.5 2-layer scanner pattern
  (narrow current-state matcher + claim-verb broad scan +
  `HISTORICAL_MARKERS` left-context filter) preserved verbatim; only the
  input set widens.
- **`tests/test_regression_v011_7_import_path_invariants.py`** — Subtask 4
  ships 6 tests locking the `scripts/hooks/__init__.py` import path
  invariant from v0.11.5. The package marker existence test +
  `from scripts.hooks import stop_verify_claims, sentinel_helper, hook_state`
  importability + module-attribute pins prevent silent regression.
- **`tests/test_regression_v011_7_profile_mutation_detection.py`** —
  Subtask 6 ships 5 tests covering the minimal B1 detection layer:
  initial snapshot taken on first invocation, second invocation
  observing a changed `hooks.profile` value emits a stderr warning, exit
  code preserved (detection-only contract), snapshot expiry matches
  hook_state TTL semantics, and prose voice safety on the warning text.
- **`scripts/hooks/hook_state.py`** gains `read_profile_snapshot()` +
  `write_profile_snapshot()` helpers — first-invocation cache + diff
  surface for the minimal B1 detection. Helpers are scoped narrowly so
  v0.11.8+ architectural enforcement can replace them without
  cross-cutting refactor.

### Changed

- **Subtask 5 xfail marker cleanup** — `strict=False` xfail markers on
  `tests/test_regression_v011_5_claude_md_invariants.py` tests 1.1 / 1.2 /
  1.3 removed. The tests have XPASSed since v0.11.5 corrective fixes
  landed; silent XPASS is now loud PASS. Carried by v0.11.5 Voice
  section as "optional polish carried to v0.11.6"; v0.11.7 closes it.
- **Subtask 5 `_clean_hook_state` autouse fixture** added to
  `tests/test_regression_v011_6_sentinel_body_normalization.py`. The
  v0.11.6 sentinel tests previously leaked `hook_state.json` artifacts
  across test runs in some local configs; the autouse fixture isolates
  each test in a fresh state directory. Fragility patch — no behavior
  change.
- **Subtask 5 B3 minimal "ce-setup is not available" honest message** —
  the 4 vendored skill references to `/ce-setup` (dangling since v0.11.2
  scope-clarification cut) now show a one-line honest message
  ("`/ce-setup` is not available in athanor; see `/athanor:setup` for
  the athanor-native equivalent") via the v0.11.7 T2 modifications field
  on `ce-test-browser`, `ce-frontend-design`, and the `ce-demo-reel` ×
  2 occurrences. Full T2 navigation (clickable reference repair across
  the vendored corpus) deferred to v0.11.8+.
- **`docs/STATE.md` prose drift** at lines 19 and 478 — stale version
  pin references cleaned per Phase 1 scanner output. Historical context
  markers preserved.
- **`README.md` line 19** — drift residual from the v0.11.5 A2 closure
  cleaned by Phase 1 scanner.
- **Version bump** 0.11.6 → 0.11.7 across `.claude-plugin/plugin.json`
  and `.claude-plugin/marketplace.json` (`"version"` field +
  `"description"` refresh). URL pins (`"$schema"` / `"$id"` strings
  containing `v0.11.x`) bumped v0.11.6 → v0.11.7 in `athanor.json`,
  `templates/athanor.json`, `schemas/athanor-config.schema.json`.

### Voice (what v0.11.7 deliberately does NOT do)

- v0.11.7 does NOT block the Stop hook gate on mid-session profile
  mutation. B1 ships as detection-only — a stderr warning is emitted
  on observed mutation, exit code is preserved. Full architectural
  enforcement (snapshot / cache / lock + legitimate cross-session edit
  handling) is v0.11.8+ work and named as such, not carried as an
  anonymous candidate.
- v0.11.7 does NOT lower forgery cost. The v0.11.6 sentinel
  body-hash binding (v=2 nonce-bound contract) is unchanged; B1 adds a
  separate detection layer above the existing protocol.
- v0.11.7 does NOT touch detection layers — v0.7.7 whitelist +
  v0.10.2 paraphrase regex + NFKC + Cyrillic + vendor-aware + v0.10.3
  Greek / Armenian + conditional + attribution suppression are all
  unchanged and reachable post-v0.11.3 / v0.11.4 / v0.11.5 / v0.11.6 /
  v0.11.7.
- v0.11.7 does NOT supersede v0.11.3 / v0.11.4 / v0.11.5 / v0.11.6.
  The companion-fix arc continues to 5 layers; each release closes one
  layer and exposes the next.

### Self-violation acknowledgment

The v0.11.6 reclassification pattern ("documented bug masked as
enhancement candidate" is a honesty-arc violation) applies more broadly
than the single Residual entry v0.11.6 fixed. 4 documented bugs that
have been carrying as anonymous "candidate" items for 6 to 11+ release
cycles — B1 (profile mutation), B2 (stale version pin), B5 (stale
"v0.8.0+ work" label), B6 (broken-promise wording) — now have explicit
Severity / Target / Acceptance labels in the v0.11.7 Residual block. B1
in particular: the docstring said "not guarded" for 8+ release cycles
while no detection layer existed; v0.11.7 ships minimal detection as a
first layer of closure rather than another pure-documentation release.

### Migration

- No user action required. Users pick up via
  `/plugin marketplace update athanor` on next refresh. The B1
  detection layer surfaces a stderr warning when `athanor.json`
  `hooks.profile` changes between invocations within a single session;
  no exit-code or gate-semantics change. Existing snapshots from
  pre-v0.11.7 sessions self-expire via the hook_state TTL.

### Deferred (v0.11.8+)

- **B1 full architectural treatment** — snapshot / cache / lock +
  legitimate cross-session edit handling. v0.11.7 ships minimal
  detection only.
- **B3 full T2 navigation pattern** — clickable reference repair across
  the vendored corpus. v0.11.7 ships only the minimal honest message
  on the 4 known dangling references.
- **B4 `_content_to_text` no-separator empirical investigation** — the
  v0.11.3 helper joins text blocks without a separator; the behavior is
  documented but no empirical attacker / fuzzer test exists.
- **LOW-7 tag gap v0.7.7 → v0.11.1 backfill** (release archaeology).
- **LOW-8 detection coverage via `transcript_path`** (35+ legacy tests
  parameterization).
- **Bolder**: CLAUDE.md generate-from-manifests (Codex Reviewer
  suggestion from v0.11.5 / v0.11.6 sessions).

---

## [0.11.6] — 2026-05-21

**Sentinel body-hash binding fix — companion to v0.11.3/4/5 arc.**
The 4th and (for now) last layer of the latent-bug arc — v=2 sentinel
protocol's hash-binding round-trip was broken since v0.7.9 introduction.
`scripts/hooks/sentinel_helper.py emit` hashes the body it reads from
stdin (typically with a trailing `\n` from heredoc input);
`scripts/hooks/stop_verify_claims.py validate_emission_sentinel()`
extracts the body from the model's response in transcript JSONL and
hashes that. Claude Code transcript capture **strips trailing whitespace**
on response storage — so helper hashes N+1 bytes while script hashes N
bytes for the same logical body. Empirically diagnosed in this release
session: piped body 1744 bytes vs transcript-captured body 1743 bytes,
exact 1-byte trailing-newline diff. The mismatch caused the
verification skill to ALWAYS body-hash-mismatch in the
v0.11.3-introduced production path, despite documented v=2 nonce-bound
forgery protection.

### Honesty arc

The bug was documented as `Residual known limitation` since v0.7.9 and
carried forward through v0.11.5 as "v0.11.0+ candidate". That
classification itself was an honesty-arc violation — a documented bug
that doesn't behave per its documented contract is a *bug*, not an
*enhancement candidate*. v0.11.6 closes both the technical bug and the
classification drift.

### Companion-fix arc — 4 layers closed

| Layer | Release | Bug |
|---|---|---|
| Runtime stdin parser shape | v0.11.3 | script wrong |
| Hook command path resolution | v0.11.4 | path wrong |
| CLAUDE.md doc drift class | v0.11.5 | doc untestable claims |
| **Sentinel body-hash binding** | **v0.11.6** | **trailing-whitespace round-trip mismatch** |

Shared meta-cause: source-repo-only manual testing hid bugs at each
layer simultaneously. v0.11.6 also exposes the meta-bug — that
"documented known limitation" can be a category that hides honest
bugs from accountability. Future "documented but unfixed" entries
should be either reclassified as bugs or have explicit fix-priority
labels.

### Fixed

- `scripts/hooks/sentinel_helper.py emit()` — body normalized via
  `.strip()` before SHA-256 hashing (1-line change at line 64). Helper
  now hashes trailing/leading-whitespace-stripped body so heredoc
  trailing newlines no longer cause mismatch.
- `scripts/hooks/stop_verify_claims.py validate_emission_sentinel()` —
  `body_canonical = body_after.strip()` replaces the old
  `body_after.lstrip("\n")` (line 861). Symmetric with helper change.
  Content-forgery rejection still works (verified by
  test_content_difference_still_rejected).

### Added

- `tests/test_regression_v011_6_sentinel_body_normalization.py` — 5
  tests: RED-first repro of the v0.7.9-introduced bug
  (trailing-newline + leading-newline mismatch), byte-identical
  baseline preservation, content-forgery rejection (security boundary),
  helper-script normalization consistency unit test. All 5 PASS
  after the v0.11.6 fix.

### Changed

- 5-file version bump 0.11.5 → 0.11.6
  (`.claude-plugin/{plugin,marketplace}.json` version + 3 URL pins in
  `athanor.json`, `templates/athanor.json`,
  `schemas/athanor-config.schema.json`).
- `docs/STATE.md` Current Phase → v0.11.6.

### Voice (what v0.11.6 deliberately does NOT do)

- Does NOT change SENTINEL_PATTERN regex shape or nonce protocol.
  v=2 nonce-bound contract is unchanged; only the body canonicalization
  step is normalized for whitespace tolerance.
- Does NOT lower forgery cost. Content differences in the body still
  produce hash mismatch and the gate fires as designed. Whitespace was
  never a security boundary — the v=2 design's forgery-cost argument
  is about content hash, not whitespace preservation.
- Does NOT touch detection layers (v0.7.7 whitelist + v0.10.2
  paraphrase regex + NFKC + Cyrillic + vendor-aware + v0.10.3 Greek/
  Armenian + conditional + attribution suppression). All unchanged
  and now finally exercise reliably through the v=2 sentinel gate.
- Does NOT supersede v0.11.3/4/5. The 4-layer companion-fix arc is
  complete with this release.

### Self-violation acknowledgment

For 11+ release cycles (v0.7.9 → v0.11.5), `Residual known
limitations` block in `scripts/hooks/stop_verify_claims.py` docstring
listed sentinel-binding brittleness as a "v0.11.0+ candidate". That
phrasing carried the honesty-arc violation: a documented bug masked
as enhancement-pending. v0.11.6 fixes both the bug and the
classification drift. Future hook-affecting releases should run
sentinel round-trip tests in a real session before claiming the
binding works.

### Migration

- No user action required. Users with athanor installed pick up the
  fix on next `/plugin marketplace update athanor`. The fix is
  backwards-compatible: existing nonce.json state from pre-v0.11.6
  sessions with mismatched hashes will simply expire via the
  60-second TTL or get overwritten on next sentinel emit.

### Deferred (v0.11.7+)

- LOW-7 tag gap v0.7.7 → v0.11.1 backfill (release archaeology)
- LOW-8 detection coverage via transcript_path (35+ legacy tests
  parameterization)
- MEDIUM-4 dangling `/ce-setup` references in 3 vendored skills
  (T2 navigation)
- Bolder: CLAUDE.md generate-from-manifests (Codex Reviewer
  suggestion from v0.11.5 session)
- Audit `Residual known limitations` block for other
  documented-but-unfixed entries (apply v0.11.6 reclassification
  pattern: bug vs enhancement, honest fix-priority labels)

---

## [0.11.5] — 2026-05-21

**Documentation honesty hardening — companion to v0.11.3+v0.11.4 runtime
closure.** v0.11.3 fixed the Stop hook script behavior (input-layer
parser); v0.11.4 fixed the deployment path (`${CLAUDE_PLUGIN_ROOT}`
expansion); v0.11.5 closes the *documentation drift class* that hid the
runtime bug for 5 release cycles. CLAUDE.md was making truth claims that
no test enforced — "37 CE skills" (actually 33 post-v0.11.2
scope-clarification cut), "SessionStart 자동 로드" (athanor's
`hooks/hooks.json` registers only the Stop event; SessionStart skill
loading is a Claude Code platform mechanism, not a plugin hook),
"v=1 sentinel" (production has used v=2 nonce-bound since v0.7.9).
v0.11.5 ships drift-class regression test infrastructure with 2-layer
scanner + historical-context exemption — so the next 8 release cycles
cannot accumulate the same prose-vs-code gap unnoticed.

### Fixed

- **`CLAUDE.md` CE-count drift** — 3 stale "37 CE skills" references
  corrected to "33" (lines 35, 113, 319). Historical and attributed
  references (e.g., "absorbed compound-engineering v3.8.3 (37 skills)"
  as a chronological artifact) preserved.
- **`README.md` CE-count drift** — 2 stale "37" references corrected to
  "33" (lines 8, 12), plus 1 dependent arithmetic adjustment "50 vendored
  skills" → "46" (33 ce-* + 13 sp-*).
- **`CLAUDE.md` SessionStart fiction** (line 113) — "SessionStart에 자동
  로드" replaced with accurate description: athanor's `hooks/hooks.json`
  registers only the Stop event; SessionStart skill loading is a Claude
  Code platform-level mechanism (additional-context system-reminder
  channel), not an athanor plugin hook.
- **`CLAUDE.md` v=1 sentinel doc lag** (lines 144, 161) — v=1 references
  describing the current protocol replaced with v=2 nonce-bound (matching
  `SENTINEL_PATTERN` in `scripts/hooks/stop_verify_claims.py` since
  v0.7.9). Historical mentions of v=1 as the original protocol shape
  remain intact.

### Added

- **`tests/test_regression_v011_5_claude_md_invariants.py`** — 4
  invariant tests with 2-layer scanner (Layer A narrow current-state
  matcher + Layer B claim-verb broad scan) and `HISTORICAL_MARKERS`
  left-context filter for historical-attribution exemption: (1.1) CE-count
  claim matches actual `skills/ce-*` directory count; (1.2) hook event
  claims match `hooks/hooks.json` registrations; (1.3) sentinel version
  claim matches `SENTINEL_PATTERN` in the hook script; (1.4)
  exemption-filter regression self-test. Locks the drift class going
  forward.
- **`scripts/hooks/__init__.py`** — empty package marker closing the
  latent import-path trap surfaced in the 2026-05-21 analyze session
  (LOW-6).

### Changed

- **`tests/test_regression_v011_1_using_superpowers_boundary.py`**
  `NATIVE_THIN_LEADER_SKILLS` tuple grows 9 → 10 with `lfg` added at
  the alphabetical position. Closes the MEDIUM-5 lfg ghost (the LFG
  skill was silently outside the boundary roster).
- **`skills/lfg/SKILL.md`** — `### v0.11.1 using-superpowers boundary`
  preamble subsection added (canonical text copied verbatim from
  `skills/plan/SKILL.md`).
- **`CLAUDE.md`** `using-superpowers boundary` row enumeration —
  "9 Thin Leader skill" updated to "10" + `lfg` inserted into the
  alphabetical listing.
- **Version bump** 0.11.4 → 0.11.5 across `.claude-plugin/plugin.json`
  and `.claude-plugin/marketplace.json` (`"version"` field +
  `"description"` refresh). URL pins (`"$schema"` / `"$id"` strings
  containing `v0.11.x`) bumped v0.11.4 → v0.11.5 in `athanor.json`,
  `templates/athanor.json`, `schemas/athanor-config.schema.json`.

### Voice (what v0.11.5 deliberately does NOT do)

- v0.11.5 does NOT supersede or retract v0.11.3 or v0.11.4. The
  companion-fix arc continues: runtime gate restored (v0.11.3 input
  layer + v0.11.4 deployment path) + drift class closed (v0.11.5
  prose level).
- v0.11.5 does NOT add new behavior to any skill. The release ships
  drift-class tests + prose corrections + 1 empty package marker; no
  detection-layer changes.
- v0.11.5 does NOT modify `scripts/hooks/stop_verify_claims.py`
  runtime logic or `scripts/hooks/hook_state.py` /
  `scripts/hooks/sentinel_helper.py`. Detection layers and circuit
  breaker untouched.
- v0.11.5 does NOT remove the xfail markers on Subtask 1's tests
  1.1/1.2/1.3 — they XPASS after the corrective fixes landed but the
  `strict=False` markers stay so any future regression makes them fail
  loud. Optional polish carried to v0.11.6.
- v0.11.5 does NOT generate CLAUDE.md from machine-checkable manifests
  — the Codex Reviewer's bolder architectural suggestion is deferred
  to a v0.12.x design note.
- v0.11.5 does NOT touch the 35+ legacy stop_hook_script tests'
  payload shape (transcript_path detection coverage carried as LOW-8).

### Self-violation acknowledgment (honesty arc)

For 5+ release cycles (v0.10.0 cuts onward), CLAUDE.md accumulated
truth-claim drift that no test enforced. The v0.11.3 + v0.11.4
input-layer + deployment-path bug arc hid for the same number of cycles
because manual testing happened only inside athanor's own source repo.
v0.11.5 ships the drift-class regression test infrastructure that would
have caught the same class of bug AT THE PROSE LEVEL — converting prose
drift into testable invariants. Same arc, different layer.

### Migration

- No user action required. Users pick up the fix on next
  `/plugin marketplace update athanor`. v0.11.5's behavior surface
  change is zero — only docs and tests changed.

### Deferred (v0.11.6+)

- MEDIUM-4: dangling `/ce-setup` references in 3 vendored skills
  (T2 navigation).
- LOW-7: tag gap v0.7.7 → v0.11.1 backfill (archaeology).
- LOW-8: detection coverage via `transcript_path` path (35+ legacy
  tests parameterization).
- Bolder: CLAUDE.md generate-from-manifests architecture (Codex
  Reviewer suggestion).
- A5 / sec-001 / sec-003 / profile-mutation guard — earlier carries.
- xfail marker cleanup on `test_regression_v011_5_claude_md_invariants.py`
  tests 1.1/1.2/1.3 (optional polish).

## [0.11.4] — 2026-05-21

**Stop hook plugin-root deployment fix — companion to v0.11.3 input-layer
fix.** v0.7.8 → v0.11.3 the hook command in `hooks/hooks.json` used a
bare relative path (`python3 scripts/hooks/stop_verify_claims.py`) which
Claude Code resolves relative to the user's PROJECT cwd, not the plugin
install dir. The script was therefore reachable only inside athanor's
own source repo; in every other project CC treated the hook as missing
(non-blocking exit). v0.11.4 switches to `${CLAUDE_PLUGIN_ROOT}` env var
expansion — the industry pattern used by superpowers, claude-mem, and
openai-codex plugin hooks. v0.11.3's input-layer fix and v0.11.4's
deployment-path fix are companion-fixes of one latent bug arc: script
wrong (closed v0.11.3) + path wrong (closed v0.11.4).

### Fixed

- **`hooks/hooks.json`** — Stop hook command changed from
  `python3 scripts/hooks/stop_verify_claims.py` to
  `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/hooks/stop_verify_claims.py"`.
  The `${CLAUDE_PLUGIN_ROOT}` env var is set by Claude Code for plugin
  hooks and expands to the plugin install directory regardless of the
  project cwd.

### Added

- **`tests/test_regression_stop_command_hook.py::test_stop_hook_command_uses_plugin_root_or_absolute_path`**
  — new regression test locking the invariant. Asserts the Stop hook
  command contains `${CLAUDE_PLUGIN_ROOT}` OR (after stripping leading
  quote) starts with `/` (absolute path). Bare relative paths fail the
  test. Reviewer revision 1: the `cmd.lstrip("\"'")` strip step is
  explicit because the JSON-quoted command starts with `"` — a naive
  `cmd.startswith("/")` check would break.

### Changed

- **`CLAUDE.md`** §"Defense Mechanisms" status-table row — v0.11.4
  plugin-root audit pointer appended.
- **`CLAUDE.md`** §"Completion-Claim Verification (Stop hook — enforced,
  command-based)" detail subsection — new §"Stop hook v0.11.4 plugin-root
  deployment fix (post-mortem)" subsection chronologically after the
  v0.11.3 post-mortem. The v0.11.3 post-mortem block is retroactively
  annotated with a "scope: source-repo only until v0.11.4 plugin-root
  fix" footnote.
- **`CLAUDE.md`** Hook config reference line updated to mention
  `${CLAUDE_PLUGIN_ROOT}`.
- **`scripts/hooks/stop_verify_claims.py`** docstring — new v0.11.4
  plugin-root deployment fix post-mortem section in chronological order
  between the v0.11.3 post-mortem and the Residual known limitations
  block. The v0.11.3 post-mortem block is retroactively annotated with
  the source-repo-only scope footnote.
- **`docs/STATE.md`** — Current Phase shifted v0.11.3 → v0.11.4; v0.11.3
  promoted to Previous Phase.
- **Version bump** 0.11.3 → 0.11.4 across `.claude-plugin/plugin.json`
  and `.claude-plugin/marketplace.json` (`"version"` field). URL pins
  (`"$schema"` / `"$id"` strings containing `v0.11.x`) bumped v0.11.3
  → v0.11.4 in `athanor.json`, `templates/athanor.json`,
  `schemas/athanor-config.schema.json`.

### Voice (what v0.11.4 deliberately does NOT do)

- v0.11.4 does NOT supersede or retract v0.11.3. v0.11.3's input-layer
  fix remains correct and necessary; v0.11.4 is the companion
  deployment-path fix. The v0.11.3 post-mortem is retroactively
  annotated (scope footnote added), NOT replaced.
- v0.11.4 does NOT change `scripts/hooks/stop_verify_claims.py` code
  logic — only adds a new docstring section. The `hooks/hooks.json`
  edit and the new regression test are the only behavior changes.
- v0.11.4 does NOT modify `scripts/hooks/hook_state.py` or
  `scripts/hooks/sentinel_helper.py`. Circuit breaker + v=2 nonce
  protocol continue unchanged.
- v0.11.4 does NOT touch the detection layers (whitelist / paraphrase
  regex / NFKC / cyrillic-greek-armenian fold / conditional-attribution
  suppression). Those are v0.7.9 / v0.10.2 / v0.10.3 work, code-correct
  and now reachable.
- v0.11.4 does NOT add a new hook event (still Stop only). The existing
  CLAUDE.md claim about "SessionStart auto-load" of using-superpowers is
  a separate issue carried in v0.11.5 deferred (analyze.md HIGH-2).

### Self-violation acknowledgment (honesty arc)

For 6 release cycles (v0.7.8 → v0.11.3), the Stop hook documented as
`**enforced (command-based)**` was reachable only inside athanor's own
source repo because of a bare relative path in `hooks/hooks.json`.
v0.11.3 fixed the script behavior but not the deployment path; v0.11.4
closes the second half. The shared meta-cause for the v0.11.3 + v0.11.4
bug arc: manual testing happened only inside athanor's source repo,
where both the wrong stdin shape AND the wrong path resolution happened
to be invisible. Future hook-affecting releases must run a smoke test
in a different project before claiming the hook is reachable.

### Migration

- No user action required. Users already running athanor will pick up
  the fix on next `/plugin marketplace update athanor` — the new
  hooks.json command uses an env var that CC sets automatically.

## [0.11.3] — 2026-05-21

**Stop hook input-layer fix — honesty arc restoration.** v0.7.8 (script
introduction) through v0.11.2 — the runtime Stop hook documented as
`**enforced (command-based)**` silently fail-opened on every Stop event
because its stdin parser assumed a payload shape Claude Code never sent.
The script expected `{"last_assistant_message": "<string>"}` on stdin and
treated any other shape as empty input. Claude Code actually sends
`{"session_id", "transcript_path", "stop_hook_active", "hook_event_name"}`
— the assistant turn lives at the tail of the JSONL file referenced by
`transcript_path`, not on stdin. v0.11.3 fixes the input layer; the
detection logic shipped over v0.7.9 / v0.10.2 / v0.10.3 is unchanged but
now actually runs in production. Self-violation acknowledged and
corrected.

Plan: `docs/plans/2026-05-21-001-feat-v0.11.3-stop-hook-input-layer-fix-plan.md`

### Fixed

- **`scripts/hooks/stop_verify_claims.py`** — stdin parser now reads the
  real Claude Code Stop event shape. New helpers
  `_read_last_assistant_message()` + `_content_to_text()` accept BOTH the
  legacy `last_assistant_message: <string>` shape (preserved for tests
  and any direct caller) and the real transcript-path shape (production).
  Transcript resolution walks the JSONL referenced by `transcript_path`,
  selects the most-recent entry whose `entry.type == "assistant"` with
  `isSidechain != true` (so only the main-session model's turn gates;
  sub-agent assistant turns are filtered out), and joins the
  `text`-typed content blocks. Tool-use-only turns produce empty text and
  exit 0 cleanly. Partial-JSONL race tolerance is preserved — malformed
  trailing lines are skipped without aborting parse.

### Added

- **`tests/test_regression_v011_3_stop_hook_input_layer.py`** — 25
  mandatory tests + 1 xfail-tolerant test locking the real-Claude-Code-
  shape behavior. Coverage spans: tool_use-only turn (exit 0), mixed
  text + tool_use turn (exit 2 on text claim), partial-JSONL race
  tolerance, sentinel-in-transcript validation, sub-agent
  (`isSidechain: true`) skipping, `stop_hook_active: true` pass-through
  (no special-case short-circuit), stale-counter post-upgrade scenario,
  and the full
  `{session_id, transcript_path, stop_hook_active, hook_event_name}`
  payload contract. The existing 35+ tests in
  `tests/test_regression_stop_hook_script.py` are retained as a
  backwards-compat lock on the legacy `last_assistant_message` shape.

### Changed

- **`CLAUDE.md`** §"Defense Mechanisms" status-table row — a one-sentence
  v0.11.3 audit pointer added; the `**enforced (command-based)**` label
  stays in place. The label is now honest as of v0.11.3.
- **`CLAUDE.md`** §"Completion-Claim Verification (Stop hook — enforced,
  command-based)" detail section — new §"Stop hook v0.11.3 input-layer
  fix (post-mortem)" subsection documenting the assumed-vs-actual
  payload shape divergence and the corrective rewrite of the stdin
  parser.
- **`scripts/hooks/stop_verify_claims.py`** docstring — a new v0.11.3
  input-layer fix (post-mortem) section inserted in chronological order
  between the v0.10.3 entry and the Residual known limitations block.
- **`docs/STATE.md`** — Current Phase v0.11.3; v0.11.2 promoted to
  Previous Phase.
- **Version bump** 0.11.2 → 0.11.3 across `.claude-plugin/plugin.json`
  and `.claude-plugin/marketplace.json` (`"version"` field). URL pins
  (`"$schema"` / `"$id"` strings containing `v0.11.x`) bumped v0.11.2
  → v0.11.3 in `athanor.json`, `templates/athanor.json`,
  `schemas/athanor-config.schema.json`.

### Voice (what v0.11.3 deliberately does NOT do)

- v0.11.3 does NOT remove or change the v0.7.9 / v0.10.2 / v0.10.3
  detection logic. Those layers were code-correct; they were unreachable,
  not broken. The fix is at the stdin parser, not at the claim-matcher.
- v0.11.3 does NOT supersede any prior release. v0.7.8 through v0.11.2
  documentation remains in `CHANGELOG.md` and `docs/plans/`; the v0.11.3
  audit note clarifies, it does not erase.
- v0.11.3 does NOT change the `**enforced (command-based)**` label. The
  label is now honest as of v0.11.3.
- v0.11.3 does NOT modify `hooks/hooks.json`. Hook registration was
  correct; only the script's stdin parsing was wrong.
- v0.11.3 does NOT modify `scripts/hooks/hook_state.py` or
  `scripts/hooks/sentinel_helper.py`. The circuit breaker and v=2 nonce
  protocol continue unchanged.
- v0.11.3 does NOT special-case `stop_hook_active` to short-circuit the
  gate. The flag is pass-through; re-entry semantics remain governed by
  the existing `hook_state` circuit breaker per v0.7.9 design.
- v0.11.3 does NOT rephrase or expand `FORBIDDEN_PHRASES`,
  `V011_FORBIDDEN_PHRASES`, or `V011_1_BOUNDARY_FORBIDDEN_PHRASES`.
  Voice constraints from v0.10.0 / v0.11.0 / v0.11.1 carry forward
  verbatim.

### Self-violation acknowledgment (honesty arc)

For 5 release cycles (v0.7.8 → v0.11.2), athanor labeled its own Stop
hook `**enforced (command-based)**` while production fail-opened on
every Stop event. The 35+ existing tests in
`tests/test_regression_stop_hook_script.py` used the same incorrect
assumed payload shape, so they passed while production was dead.
v0.11.3 adds 25 mandatory + 1 xfail-tolerant tests against the real
Claude Code payload shape and retains the legacy tests as a
backwards-compat lock. The mistake originated in v0.7.8 when the script
was authored before the actual Stop event payload had been observed
end-to-end. This release is a correction, not a quiet patch — the
v0.11.3 entry, the CLAUDE.md post-mortem subsection, and the script
docstring all carry the acknowledgment.

### Migration

- No user action required. Projects with `"hooks": {"profile": "off"}`
  continue to opt out. Projects with `"hooks": {"profile": "standard"}`
  (default) now get the gate they were already paying for in `CLAUDE.md`
  documentation.

## [0.11.2] — 2026-05-20

**Hygiene cut — scope clarification.** athanor stands alone (v0.11.0
commitment), so tooling that manages the compound-engineering plugin
itself belongs to CE, not athanor's vendored surface. v0.11.2 removes
four CE-plugin-lifecycle skills + finally cuts a config block that
self-declared as "DEPRECATED in v0.7.7, slated for removal in v0.7.9"
yet kept shipping through v0.11.1.

Analysis source: cross-model cutting-preparation deep analysis
(`.athanor/sessions/2026-05-20-002/discuss.md` — Researcher A Claude
+ Devil's Advocate Codex + Critic synthesis). v0.11.2 cuts are the
**high-agreement intersection** — items both voices judged safe. Larger
mid-cuts and architectural vendor-prune defer to v0.12.0 / v0.13.0.

Plan: `docs/plans/2026-05-20-002-feat-v0.11.2-hygiene-plan.md`

### Removed

- **`models` config block** from `athanor.json`, `templates/athanor.json`,
  and `schemas/athanor-config.schema.json`. The block was declared
  unread at v0.7.7 (no skill or agent dispatches via this config) and
  marked for v0.7.9 removal in its own `_doc`. v0.11.2 closes that
  4-minor-overdue deprecation arc. Model assignment continues to live
  inline in each `skills/<name>/SKILL.md` and `agents/*.md` file (the
  actual runtime contract since v0.6.x).
- **4 CE-plugin-lifecycle vendored skills:**
  - `skills/ce-update/` — manages `compound-engineering` plugin updates
  - `skills/ce-report-bug/` — reports bugs to the CE repository
  - `skills/ce-release-notes/` — summarizes CE plugin releases
  - `skills/ce-setup/` — configures CE environment (overlaps athanor's
    own `/athanor:setup` at 562 lines)

  Each carried `disable-model-invocation: true` upstream (already hidden
  from auto-trigger). Their domain is CE-plugin maintenance; athanor's
  domain is workflow orchestration.

### Changed

- **`tests/test_regression_v010_namespace_layout.py`** —
  `test_vendor_skill_count_meets_expectation` count assertion relaxed
  from `>= 37` to `>= 33` for ce-* (post-cut floor). Docstring updated
  to note v0.11.2 closure. Future cuts will lower further; raise back
  only when a release adds skills.
- **`tests/test_regression_doc_string_honesty.py`** — inverted the
  `models._doc` pins per the v0.10.3 §D6 pattern. The v0.7.x~v0.10.x
  tests pinned "doc must lead with 'DEPRECATED in v0.7.7'"; v0.11.2
  flips to "block must NOT exist." Same closure-locking shape used
  for v0.10.3 Greek/conditional/attribution residual closure.
- **`NOTICE.md`** — vendored CE skill list trimmed by 4 entries plus
  an explanatory paragraph documenting the v0.11.2 scope-clarification
  intent.
- **Version bump** across `.claude-plugin/{plugin,marketplace}.json`,
  `athanor.json`, `templates/athanor.json`,
  `schemas/athanor-config.schema.json` (0.11.1 → 0.11.2).
- **`docs/STATE.md`** — Current Phase v0.11.2 with full cut accounting
  and v0.12.0+ deferred list.

### Voice (what v0.11.2 deliberately does NOT do)

- v0.11.2 does NOT remove or rewrite `docs/plans/2026-05-19-003-*` (the
  v0.10.0 absorption plan that originally enumerated the cut skills).
  Plan archives are immutable release evidence — Devil's Advocate's
  defense holds.
- v0.11.2 does NOT modify `scripts/check_vendor_drift.py`. The script
  walks `skills/ce-*/` dynamically; after the cut it iterates 33
  instead of 37. No maintained allow-missing list — "every present
  ce-*/sp-* skill matches upstream" remains the governing invariant.
- v0.11.2 does NOT touch `ce-lfg`, `sp-using-superpowers`, beta
  variants, domain-specialized CE skills, `deep-plan`/`lite-plan`, or
  any honesty-arc test (`v010_2_paraphrase_closure`,
  `v010_3_residual_closure`, etc.). Those defer to v0.12.0 / v0.13.0
  per cross-model analysis.
- v0.11.2 does NOT frame cuts as supersession or replacement of
  compound-engineering. The framing is **scope clarification**:
  CE-plugin lifecycle tools belong to the CE plugin; athanor is an
  orchestrator.

### Migration

- Projects that hand-edited `athanor.json` to override the `models`
  block (none expected — the block was unread) should remove the
  override. The block was inert prior to removal.
- Users who invoked `/athanor:ce-update`, `/athanor:ce-report-bug`,
  `/athanor:ce-release-notes`, or `/athanor:ce-setup` should invoke
  the corresponding `/compound-engineering:` namespace command
  directly if they have the CE plugin installed. The skills were
  CE-plugin maintenance tooling, not athanor capability.

### Deferred (carried forward — v0.12.0+)

- **v0.12.0 mid-cut:** domain-specialized CE skills (`ce-dhh-rails-style`,
  `ce-gemini-imagegen`, `ce-test-xcode`, `ce-riffrec-feedback-analysis`,
  `ce-product-pulse`, `ce-slack-research`, `ce-frontend-design`); beta
  variants (`ce-work-beta`, `ce-polish-beta`); orphan sub-agent sweep;
  honesty-test helper extraction; `docs/plans/` archive directory.
- **v0.13.0 big cut:** drift-script invariant redefinition (`"approved
  subset, athanor-relevance justified"`); CE narrow to ~13-15 skills;
  sp-* narrow to 4; CLAUDE.md advisory-section consolidation. Requires
  prior CHANGELOG voice-framing decision so cuts honor v0.11.0 / v0.11.1
  positive-commitment gates.
- **A5** native-vs-vendored deprecation candidates.
- **sec-001** transcript-event introspection.
- **sec-003** LLM-class semantic similarity for stop_verify_claims.py.
- Mid-session `hooks.profile` mutation guard.

---

## [0.11.1] — 2026-05-20

**`using-superpowers` boundary clarification (advisory, preamble-declared).**
v0.10.0에서 흡수된 `superpowers:using-superpowers` skill은 SessionStart에
auto-load 되어 "ABSOLUTELY MUST invoke before response" 톤을 강제한다.
v0.11.1은 그 톤이 athanor-native 9개 Thin Leader skill (analyze, debug,
deep-plan, discuss, lite-plan, plan, review, setup, work) 호출 context에서
**advisory**라는 경계를 문서화한다 — runtime gate 추가 없음, vendored
content 편집 없음. 산문 + lock-in test 중심 작은 release.

Plan: `docs/plans/2026-05-20-001-feat-v0.11.1-using-superpowers-boundary-plan.md`
Origin: `docs/brainstorms/2026-05-20-001-athanor-using-superpowers-boundary-requirements.md`

### Added

- **CLAUDE.md §Defense Mechanisms** new row + detail —
  `using-superpowers boundary (v0.11.1)`. 라벨: `advisory
  (preamble-declared)`. 4 signal phrase (using-superpowers / SessionStart /
  advisory / leader dispatch) 포함. carve-out 명시: scope-drift +
  verification-before-completion는 unprefixed slot이나 Thin Leader 패턴
  아닌 vendored-content이라 제외.
- **9 native Thin Leader SKILL.md** 각각에 `### v0.11.1 using-superpowers
  boundary` subsection 추가. 동일 canonical 단락 — "Athanor's Thin Leader
  + planner-classified discipline applies in this skill context.
  `superpowers:using-superpowers` is loaded at SessionStart and its 'MUST
  invoke before response' pressure is **advisory here** — discovery in
  athanor-native skills resolves through leader dispatch, not pre-response
  invocation check. See CLAUDE.md §Defense Mechanisms."
- **9 new regression tests** in
  `tests/test_regression_v011_1_using_superpowers_boundary.py`:
  CLAUDE.md row presence + 4 signal phrase + advisory label + 9 skill
  preamble heading exactness + 7 canonical signal phrase coverage +
  carve-out enforcement (scope-drift / verification-before-completion
  must NOT carry preamble) + vendored sp-using-superpowers presence +
  CLAUDE.md / CHANGELOG forbidden phrase guard.

### Changed

- **Version bump** across `.claude-plugin/{plugin,marketplace}.json`,
  `athanor.json`, `templates/athanor.json`,
  `schemas/athanor-config.schema.json` (0.11.0 → 0.11.1).
- **STATE.md** Current Phase: v0.11.1.

### Voice (what v0.11.1 deliberately does NOT do)

- v0.11.1 does NOT remove, sunset, or hide the vendored
  `sp-using-superpowers` skill. The skill stays loaded at SessionStart;
  its discipline remains in force when sp-* / ce-* / explicitly-superpowers
  context applies.
- v0.11.1 does NOT add a runtime gate enforcing the boundary. Honesty
  arc requires not labelling a mechanism `enforced` without a Stop hook
  or equivalent code-level gate. The boundary stays explicitly
  `advisory (preamble-declared)`.
- v0.11.1 does NOT modify the vendored `skills/sp-using-superpowers/
  SKILL.md` body (T2 provenance lock; drift script enforces).
- v0.11.1 does NOT carry sunset framing or supersession claims of any
  kind toward `superpowers:using-superpowers`. Forbidden-phrase tests
  lock this for both CLAUDE.md and CHANGELOG.

### Migration

- None required. Existing project `athanor.json` keeps working unchanged
  — no new config keys.

### Deferred (carried forward — separate brainstorm/release)

- **A5** — `sp-*` 13 skill deprecation candidates (v0.12.x+).
- **sec-001** — transcript-event introspection.
- **sec-003** — LLM-class semantic similarity for `stop_verify_claims.py`.
- Mid-session `hooks.profile` mutation guard.
- CE 37 skill cross-cutting decisions (separate brainstorm).

---

## [0.11.0] — 2026-05-19

**Standalone LFG: `/athanor:lfg` wrapper skill ships.** Closes the v0.10.0
absorption arc's standalone narrative. The full end-to-end pipeline
(plan → work → review → autofix persist → residual handoff → browser test
→ commit-push-PR → CI watch → DONE) now runs through athanor-native
commands at the identity-bearing steps, with athanor's cross-model
adversarial planning and Spec-then-TDD discipline as the default.
Vendored `/athanor:ce-lfg` (from compound-engineering 3.8.3) preserved
unchanged — both skills coexist; users choose by namespace.

Plan: `docs/plans/2026-05-19-007-feat-v0.11.0-athanor-lfg-wrapper-plan.md`
Origin: `docs/brainstorms/2026-05-19-003-athanor-standalone-lfg-wrapper-requirements.md`

### Added

- **`/athanor:lfg` wrapper skill** at `skills/lfg/SKILL.md` (depth-1
  Claude Code auto-discovery):
  - Step 1 invokes `/athanor:plan` (cross-model adversarial — Planner A
    Claude + Planner B Codex + Critic when codex available).
  - Step 2 invokes `/athanor:work` (Splitter `execution_note` +
    conjunction-of-three Phase 3 gate per v0.8.0 Spec-then-TDD).
  - Step 3 invokes `/athanor:review` (parallel 6-lens, no autofix —
    athanor identity choice).
  - Steps 4-8 reuse vendored ce-lfg's step shape (autofix persist,
    residual handoff, ce-test-browser, commit-push-PR, CI watch + 3
    fix iterations).
  - Step 9 emits `<promise>DONE</promise>` sentinel.
  - §"Difference from /athanor:ce-lfg" table makes the choice explicit
    for users — `/athanor:lfg` is athanor-first; `/athanor:ce-lfg` is
    CE single-agent + autofix-aware.
- **10 new regression tests** in
  `tests/test_regression_v011_athanor_lfg_wrapper.py`: file structure +
  frontmatter validity + identity-bearing steps invoke athanor-native
  commands + all 8 pipeline anchors present + voice forbidden-phrase
  check + difference-from-ce-lfg disclosure + T2 commitment (vendored
  ce-lfg body unchanged) + coexistence regression.

### Changed

- **CLAUDE.md Commands table** — new `/athanor:lfg` row added alongside
  other athanor-native skills. (Vendored `/athanor:ce-lfg` row already
  exists from v0.10.0.)
- **Version bump** across `.claude-plugin/{plugin,marketplace}.json`,
  `athanor.json`, `templates/athanor.json`,
  `schemas/athanor-config.schema.json` (0.10.3 → 0.11.0).
- **Version-pin tests** generalized from "0.10.x series" to "0.10.x or
  0.11.x series" — `tests/test_regression_v010_namespace_layout.py`
  and `tests/test_regression_v010_honesty_arc.py` updated.

### Voice (what v0.11.0 deliberately does NOT do)

- v0.11.0 does NOT remove or sunset the vendored `/athanor:ce-lfg`
  skill. Both `/athanor:lfg` and `/athanor:ce-lfg` coexist; users
  select by namespace based on whether they want athanor-first or
  CE single-agent + autofix-aware flow.
- v0.11.0 does NOT introduce supersession or sunset framing in
  release prose for the vendored CE flow. The v0.10.0 voice
  discipline ("upstream stays first-class") is preserved verbatim.
- v0.11.0 does NOT modify vendored `skills/ce-lfg/SKILL.md` body —
  T2 provenance commitment from v0.10.0 preserved. Regression test
  asserts body bytes unchanged.
- v0.11.0 does NOT extend Stop hook coverage further (v0.10.3
  boundary preserved).
- v0.11.0 is NOT a "replacement" — it is an **addition**. The user's
  muscle memory `/athanor:lfg` is what changes; the underlying
  capability set grows by one skill.

### Migration (from v0.10.3)

- No breaking changes. 374 baseline tests stay green; 10 new tests
  (384 total passing).
- Users who invoke `/athanor:lfg` (new) get the athanor-first flow.
- Users who invoke `/athanor:ce-lfg` (unchanged) continue to get the
  vendored CE single-agent + autofix flow.
- Users who invoke `/compound-engineering:lfg` directly (the external
  CE plugin) continue to work if the CE plugin is installed; v0.11.0
  does not interfere.

### Deferred (carried forward)

- **v0.11.1+**: A4 superpowers `using-superpowers` cross-cutting
  integration with athanor-native skills (separate brainstorm).
- **v0.11.2+**: A5 native-vs-vendored deprecation candidates (e.g.,
  `/athanor:discuss` synthesis vs `/athanor:ce-brainstorm`). Depends
  on A4 outcome.
- **v0.11.x**: LLM-class semantic similarity (sec-003 last carry);
  transcript-event introspection (sec-001 residual); mid-session
  profile mutation guard.

## [0.10.3] — 2026-05-19

**Stop hook residual closure: Greek/Armenian fold + conditional
suppression + attribution skip (R1+R2+R3).** Closes the three Stop-hook
accuracy residuals that v0.10.2 documented honestly rather than hand-wave
away. All heuristic-based; pure stdlib (`re`, `unicodedata`).

Plan: `docs/plans/2026-05-19-006-feat-v0.10.3-stop-hook-residual-closure-plan.md`

### Added

- **Multi-script confusables fold** (U1, R1 closure): `_CYRILLIC_TO_LATIN_TABLE`
  renamed `_CONFUSABLES_TO_LATIN_TABLE` (backwards-compat alias retained).
  Now covers 3 scripts: Cyrillic (17 chars, v0.10.2) + Greek (13 chars:
  `α ε ι ν ο ρ υ Α Ε Ι Ο Ρ Τ Υ`) + Armenian (`ո`). Greek `ο→o` /
  `ρ→p` / `α→a` substitutions are the high-frequency attack vectors;
  Armenian `ո` is the lone clean Latin-`o` homoglyph in that script.
- **Conditional / speculative tense suppression** (U2, R2 closure): new
  `_is_conditional_or_speculative_context(text, match_start)` inspects
  the clause containing the match (from the most recent `.`,`,`,`;`,`?`,
  `!`,`\n` boundary to `match_start`). If the clause's first token is in
  `_CONDITIONAL_MARKERS_EN` (`if / once / when / whenever / should /
  could / would / unless`) or starts with a Korean prefix marker
  (`만약 / 만일`), the match is suppressed. Closes v0.10.2's
  `test_known_false_positives_documented` cases — "If all tests are
  green, merge" / "Once the build is healthy, ship it" no longer trigger
  the gate. Pre-existing v0.7.7 substring-in-prose case "When tests pass
  through this filter" is also suppressed as collateral coverage ("When"
  is a conditional marker).
- **Attribution / quoted-context skip** (U3, R3 closure): new
  `_is_attributed_quote_context(text, match_start, match_end)` two-pronged
  check:
  - Paired-quote: same-line odd count of any of (`"`, `'`, `` ` ``)
    before `match_start` AND at least one matching quote after `match_end`
    → match is inside an unclosed quote → suppressed.
  - Attribution verb (EN, precedes quote): within 40 chars before
    `match_start` on the same line, scan for `said / claimed / wrote /
    noted / commented / mentioned / stated / reported` → suppressed.
  - Attribution verb (KO, follows quote): within 40 chars AFTER
    `match_end` on the same line, scan for `라고 했 / 라고 적 / 라고 말`
    → suppressed (Korean attribution grammar places marker after quote).
- **22 new regression tests** in
  `tests/test_regression_v010_3_residual_closure.py`: Greek/Armenian fold
  positives (5), conditional suppression positives + negatives (6),
  attribution suppression positives + negatives (6), v0.10.2 regression
  pins (5).

### Changed

- **`is_material_claim()` refactored** to track match positions for both
  literal and regex layers and apply `_match_is_suppressed()` (R2+R3
  combined check) at a single call site per candidate match. Loop
  semantics: find match → check suppressions → continue scanning the
  same phrase/pattern if suppressed, return True otherwise.
- **`_normalize_for_match()` docstring** enumerates all three scripts
  (Cyrillic v0.10.2 + Greek/Armenian v0.10.3).
- **v0.10.2 known-residual tests inverted per plan §D6** — these were
  current-behavior pins with explicit "if these flip, residual closed"
  comments. v0.10.3 closes them; assertions now flip:
  - `test_known_false_positives_documented` →
    `test_v010_3_conditional_suppression_closed` (asserts NOT caught).
  - `test_normalize_non_confused_greek_omicron_documented_residual` →
    `test_v010_3_greek_omicron_now_folded` (asserts Greek ο now folds).
  - New `test_v010_3_pre_v077_substring_still_catches_prose` pins the
    "When tests pass through..." suppression as a collateral R2 closure.

### Voice (what v0.10.3 deliberately does NOT close)

- v0.10.3 does NOT add semantic similarity (LLM-class paraphrase). The
  regex layer is verb-anchored; subtler clause embedding ("we verified
  the test suite ran clean") is still uncaught.
- v0.10.3 does NOT detect speculative tense WITHOUT prefix marker
  ("Probably CI is green"). Documented v0.11.0+ candidate.
- v0.10.3 does NOT cover multi-paragraph quote spans or code-block
  context for attribution. Same-line constraint preserved.
- v0.10.3 does NOT extend the confusables table beyond Greek + Armenian.
  Cherokee, full-width Latin (not handled by NFKC), other scripts
  remain unfolded.
- v0.10.3 does NOT close sentinel forgery via filesystem nonce state
  (sec-001 residual) — transcript-event introspection is v0.11.0+.
- v0.10.3 does NOT introduce mid-session profile mutation protection.

### Migration (from v0.10.2)

- No breaking changes. 352 baseline tests stay green; 22 new + 4 inverted
  pins = 374 total passing.
- `is_material_claim()` is MORE strict in some places (Greek/Armenian
  bypass vectors closed) and MORE lenient in others (conditional /
  attributed quotes now suppressed). Sessions previously over-triggering
  the gate on doc-review or planning prose should see reduced
  false-positive rate.
- If a v0.10.3 suppression hides a real claim (false negative), the
  `profile: "off"` athanor.json escape hatch is unchanged.

### Deferred (carried forward)

- **v0.11.0+**: LLM-class semantic similarity layer; speculative tense
  without prefix marker; multi-paragraph quote spans; transcript-event
  introspection (sec-001); mid-session profile mutation guard; A3 LFG
  pipeline reconciliation; A4 superpowers cross-cutting; A5 deprecation
  candidates.

## [0.10.2] — 2026-05-19

**Stop hook paraphrase + NFKC + cyrillic + vendor-aware closure (B2 / ADV-006 / A2).**
v0.7.9 docstring originally claimed `is_material_claim()` shipped regex
verb-anchor patterns + NFKC unicode normalization + confusables fold.
v0.10.1 U6 audit caught the overclaim and corrected the docstring honestly.
v0.10.2 *actually ships* what was originally promised — pure-Python stdlib
(`re`, `unicodedata`); no new dependencies.

Plan: `docs/plans/2026-05-19-005-feat-v0.10.2-paraphrase-bypass-closure-plan.md`

### Added

- **`_normalize_for_match()` helper** (U1, ADV-006 closure): NFKC Unicode
  normalization + 17-character Cyrillic→Latin confusables fold + lowercase.
  Idempotent. Closes cyrillic homoglyph attacks ("tеsts pass" with Cyrillic
  'е' folds to "tests pass" before substring match) and fullwidth-character
  attacks ("ｔｅｓｔｓ ｐａｓｓ" → "tests pass" via NFKC). Cyrillic fold
  table covers `а е о р с у х` (lowercase) and 10 uppercase counterparts.
- **`MATERIAL_CLAIM_PATTERNS` regex layer** (U2, B2 / sec-003 closure): 6
  conservative verb-anchored regex patterns. Catches paraphrased state
  assertions ("CI is green", "all tests are passing", "the build is
  healthy", "deployed to prod", Korean "테스트가 다 통과", "빌드 성공").
  Each pattern is verb-anchored to limit false positives on prose
  discussing tests without asserting state. Compiled at module load
  (fail-loud on bad regex). Module-load assertion prevents empty list
  from silently disabling the layer.
- **Vendor-aware whitelist extension** (U3, A2 closure): 14 English idioms
  + 4 Korean idioms added to `MATERIAL_CLAIMS_EN`/`MATERIAL_CLAIMS_KO`.
  Coverage of vendored CE/superpowers skill completion phrases (review
  complete, `<promise>DONE</promise>`, all checks passing, branch
  merged, 리뷰 완료, etc.).
- **38 new regression tests** in
  `tests/test_regression_v010_2_paraphrase_closure.py`: 9 normalization
  cases / 9 paraphrase positives / 3 paraphrase negatives / 3
  known-residual cases (current-behavior pin) / 2 cyrillic + fullwidth
  end-to-end / 5 vendor-aware positives / 3 v0.7.7 EN+KO regression /
  1 skip-categories regression / 4 module-load invariants.

### Changed

- **`is_material_claim()` pipeline refactored** to normalize → literal
  EN whitelist → literal KO whitelist → regex patterns, early return on
  first match. KO match runs against both raw and normalized text so
  homoglyph-attacked Korean is also caught.
- **`scripts/hooks/stop_verify_claims.py` top-level docstring** updated:
  - New "v0.10.2 paraphrase + NFKC + vendor-aware closure" subsection
    explicitly framed by the honesty arc — "v0.7.9 originally claimed →
    v0.10.1 honestly corrected → v0.10.2 actually ships".
  - "Residual known limitations" section rewritten with v0.10.2 reality:
    paraphrase + cyrillic items moved out of "deferred" (now shipped);
    new residuals listed (LLM-class paraphrase, conditional-tense
    false-positives, quoted historical references, Greek/Armenian/other-
    script homoglyphs).
  - v0.10.0 vendored-surface scope paragraph trimmed (vendor-aware
    whitelist extension is now active; no longer "deferred to v0.10.1+").

### Voice (what v0.10.2 deliberately does NOT claim)

- v0.10.2 does NOT close conditional-tense paraphrase ("If tests are
  green, merge"). The regex layer catches these because verb anchor
  matches; documented as known residual with v0.10.3+ closure candidate.
- v0.10.2 cyrillic fold covers Cyrillic homoglyphs ONLY. Greek `ο`,
  Armenian `ո`, and other-script confusables remain unfolded. Expand
  the table deliberately, not greedily.
- v0.10.2 does NOT add semantic similarity detection (LLM-class
  paraphrase). Surface-level regex + Unicode normalization only.
- v0.10.2 does NOT extend the gate to skip attributed historical
  references ("the v0.7.6 docs said 'tests pass'"). Attribution
  detection is v0.10.3+ candidate.
- v0.10.2 does NOT introduce mid-session profile-mutation protection
  (model writes `athanor.json` mid-turn).
- Honesty-arc framing matters: v0.10.2 is the closure of an OVERCLAIM in
  v0.7.9, exposed by v0.10.1 audit. The release narrative is
  "promised → exposed → delivered", not "ship now and overclaim later".

### Migration (from v0.10.1)

- No breaking changes. Existing test suite (314 tests) stays green; 38
  new tests added (352 total passing).
- `is_material_claim()` is more strict than v0.10.1 (catches additional
  paraphrases + homoglyphs + vendor idioms). Sessions that previously
  passed Stop without hitting the gate may now trigger it; this is the
  intended behavior (closes the bypass vectors).
- If a session legitimately produces output that the v0.10.2 regex
  layer flags as a false-positive, set `"hooks": {"profile": "off"}`
  in `athanor.json` for per-project opt-out (unchanged escape hatch).

### Deferred (carried forward to v0.10.3+ / v0.11.0+)

- **v0.10.3**: attribution / speculative-tense detection (conditional
  paraphrase false-positives, quoted historical references); Greek
  homoglyph fold expansion if attack surface justifies.
- **v0.11.0+**: A3 LFG pipeline reconciliation; A4 `using-superpowers`
  cross-cutting integration; A5 native-vs-vendored deprecation
  candidates; transcript-event introspection (sec-001 residual);
  mid-session profile-mutation guard.

## [0.10.1] — 2026-05-19

**Vendor hygiene + Splitter audit field + B2 honesty closure.** A small
follow-up to v0.10.0 that ties up three deferred items (A1 vendor-drift
script, B3 v0.9.0 reference provenance correction, B1 Splitter
`classification_reason`) and surfaces an overclaim that v0.7.9 had left
in `stop_verify_claims.py` docstring (U6 honesty-arc closure). No
identity decisions; no architectural shifts.

Plan: `docs/plans/2026-05-19-004-feat-v0.10.1-vendor-hygiene-plan.md`

### Added

- **`scripts/check_vendor_drift.py`** (U1): single-command drift check
  across all `skills/ce-*/` and `skills/sp-*/` directories against their
  upstream plugin caches. Stdlib only. Strips provenance block + normalizes
  frontmatter `name:` rewrite + collapses blank-line runs before
  comparing. Modes: default verbose / `--ci` summary-only / `--skill NAME`
  filter / `--cache-root PATH` override. Exit codes 0/1/2 for
  no-drift/drift/unreachable. Verified: against the merged v0.10.0
  vendored tree, all 50 vendored skills match upstream (`total=50
  unchanged=50 drifted=0 unreachable=0`).
- **`tests/fixtures/splitter_cases/`** (U4): 3 ambiguous-case fixture
  YAMLs documenting Splitter heuristic edges — spec-then-tdd vs direct
  (case_01); refactor → test-aware (case_02); contract-prose → direct
  (case_03). Each fixture carries case_id / subtask_brief /
  expected_classification / expected_reason_keywords / rationale.
- **Splitter output schema `classification_reason` field** (U3, B1 closure):
  every subtask emitted by `/athanor:work` Step 0.5 Splitter must now
  include a one-line `classification_reason` audit field, regardless of
  `execution_note` value. The heuristic itself is unchanged — v0.10.1
  only adds the audit field so misclassifications are diagnosable from
  the work log. Length contract: ≤ 200 chars, no embedded newlines.
- 3 new regression test files (18 new assertions):
  - `test_regression_v010_1_vendor_drift_script.py` (5 tests)
  - `test_regression_v010_1_vendor_provenance_sha.py` (4 tests)
  - `test_regression_splitter_classification_reason.py` (9 tests)

### Changed

- **`scripts/hooks/stop_verify_claims.py` docstring v0.7.9 hardening
  subsection** (U6, B2 honesty closure): rewrote the docstring to remove
  the v0.7.9-attributed paraphrase regex / NFKC unicode / cyrillic
  homoglyph items that NEVER landed in the v0.7.9 release. The actual
  function (`is_material_claim()`) is still pure literal substring
  matching — its own internal docstring openly says so, but the
  top-level docstring incorrectly claimed those mitigations were shipped.
  v0.10.1 corrects the overclaim and re-files paraphrase/cyrillic items
  under "Residual known limitations (deferred)" with v0.10.2 candidate
  annotation. No runtime change — pure honesty-arc correction.
- **`skills/discuss/references/clarify-gap-probes.md`** and
  **`skills/discuss/references/requirements-capture.md`** (U2, B3
  closure): provenance block `source-commit` line replaced the v0.9.0
  placeholder (`"vendored at athanor v0.9.0 release time"`) with a
  proper `compound-engineering@3.8.2 <upstream-relative-path>` pin +
  v0.10.0 verification note. SHA pin not available from plugin-cache
  distribution; version-tag fallback per CLAUDE.md §"Vendored Surface"
  drift policy. Body content unchanged (regression test pins body
  intact).
- **`skills/work/SKILL.md`** Step 0.5 Splitter prompt + Output Format +
  Post-split Validation extended for the new `classification_reason`
  field. Validation step #9 added.
- **Test generalization** (`test_regression_v010_namespace_layout.py`):
  hard-coded "0.10.0" version assertions replaced with `0.10.x` series
  check + plugin.json↔marketplace.json version-agreement check. v0.11.0+
  will need an explicit update; v0.10.x patch releases pass through.

### Voice (what v0.10.1 deliberately does NOT claim)

- B2 paraphrase bypass closure is **STILL DEFERRED**. v0.10.1 did NOT
  ship paraphrase regex, NFKC normalization, or cyrillic homoglyph
  protection. It only corrected the docstring overclaim. Actual closure
  is a v0.10.2 candidate.
- ADV-006 cyrillic homoglyph closure is also **STILL DEFERRED**.
- Vendor-drift script does NOT auto-fix drift. It reports; the operator
  decides whether to re-vendor.
- `classification_reason` is descriptive (records why Splitter chose a
  classification) not prescriptive (does not change the heuristic).
  Misclassifications are still possible; the field makes them
  diagnosable.

### Migration (from v0.10.0)

- Plan documents authored against v0.10.0 are unaffected. New Splitter
  output emits one extra line per subtask (`classification_reason: ...`);
  existing parsers that ignore unknown lines are forward-compatible.
- The Stop hook continues to behave exactly as in v0.7.9~v0.10.0. v0.10.1
  changed only the docstring, not the runtime.
- Existing `athanor.json` files in user projects continue to validate
  against the v0.10.0 schema. The schema URL pin moved to v0.10.1; the
  schema itself is unchanged.

### Deferred (carried forward)

- **v0.10.2**: vendor-aware Stop hook whitelist (A2); paraphrase bypass
  closure (B2 — paraphrase regex + NFKC + confusables fold); cyrillic
  homoglyph (ADV-006); transcript-event introspection for sentinel
  forgery (sec-001 residual).
- **v0.11.0+**: A3 LFG pipeline reconciliation; A4 `using-superpowers`
  cross-cutting integration; A5 native-vs-vendored deprecation
  candidates.

## [0.10.0] — 2026-05-19

**Vendored absorption of compound-engineering 3.8.3 + superpowers 5.1.0
under athanor namespace.** v0.10.0 brings the user-confirmed "full merge
with athanor identity preserved" scope to ground. 37 CE skills + 49 CE
sub-agents + 13 superpowers skills land at `skills/ce-<name>/`,
`agents/vendored/ce/*.agent.md`, and `skills/sp-<name>/` respectively
(flat skill layout chosen so Claude Code's depth-1 SKILL.md auto-discovery
resolves them). Every vendored markdown file carries a T2 provenance block
inserted after the YAML frontmatter, recording upstream version,
source-commit reference, license, and any modifications (the only allowed
modification is renaming the YAML `name:` field to match the namespace-
prefixed directory, recorded per-file). Body content is byte-identical to
upstream.

Plan: `docs/plans/2026-05-19-003-feat-v0.10.0-absorb-ce-superpowers-plan.md`
Inventory: `docs/plans/2026-05-19-003-feat-v0.10.0-absorb-ce-superpowers-plan-INVENTORY.md`

### Added (vendored superset)

- **37 CE skills** at `skills/ce-<name>/` exposed as `/athanor:ce-<name>`
  commands. Includes the full CE 3.8.3 catalog: ce-brainstorm, ce-plan,
  ce-work, ce-code-review (with 18 reviewer personas reachable via the
  vendored sub-agents below), ce-debug, ce-doc-review, ce-lfg (renamed
  from upstream `lfg`), ce-test-browser, ce-test-xcode, ce-strategy,
  ce-ideate, ce-compound, ce-proof (HITL), ce-sessions, ce-worktree,
  ce-commit, ce-commit-push-pr, ce-resolve-pr-feedback,
  ce-frontend-design, ce-figma-design-sync, ce-demo-reel,
  ce-gemini-imagegen, ce-pulse, ce-product-pulse, ce-setup,
  ce-release-notes, ce-report-bug, ce-update, ce-simplify-code,
  ce-optimize, ce-polish-beta, ce-clean-gone-branches, ce-slack-research,
  ce-riffrec-feedback-analysis, ce-dhh-rails-style,
  ce-agent-native-architecture, ce-agent-native-audit, ce-compound-refresh,
  ce-work-beta.
- **49 CE sub-agents** at `agents/vendored/ce/*.agent.md` (not user-
  invocable as commands; dispatched by the vendored skills above).
- **13 superpowers skills** at `skills/sp-<name>/` exposed as
  `/athanor:sp-<name>` commands. Includes sp-brainstorming, sp-writing-
  plans, sp-writing-skills, sp-executing-plans, sp-systematic-debugging,
  sp-test-driven-development, sp-subagent-driven-development, sp-dispatching-
  parallel-agents, sp-using-git-worktrees, sp-using-superpowers,
  sp-finishing-a-development-branch, sp-requesting-code-review,
  sp-receiving-code-review. (Superpowers' `verification-before-completion`
  intentionally NOT re-vendored — already at `skills/verification-before-
  completion/` from v0.7.8.)
- **CLAUDE.md §"Vendored Surface — Identity Guard Layer"** enumerating
  the four athanor identity commitments preserved under absorption:
  Thin Leader contract / cross-model adversarial planning /
  Spec-then-TDD discipline / Stop hook runtime gate scope.
- **NOTICE.md** expanded with full MIT attribution for CE (Kieran
  Klaassen / Every Inc) and superpowers (Jesse Vincent), enumerating
  every vendored file.
- **`scripts/oneshot/v010_vendor.py`** — reusable vendor script committed
  in-tree so future drift refreshes can re-run it (deviation from plan
  U2 note that originally suggested gitignoring it; documentation value
  outweighs scratch-script convention).

### Changed (athanor-native, preserved with vendored-surface awareness)

- **CLAUDE.md Commands table** split into Athanor-native + Vendored
  subsections. `/athanor:plan` and `/athanor:work` rows annotated with
  the identity commitment each preserves (cross-model adversarial;
  Spec-then-TDD).
- **CLAUDE.md Defense Mechanisms** Stop-hook row extended with v0.10.0
  scope disclosure (gate triggers on every Stop; whitelist may false-
  negative on vendored prose voice; vendor-aware whitelist deferred to
  v0.10.1+). Spec-then-TDD row extended with scope clarification that
  vendored `/athanor:ce-work` and `/athanor:sp-test-driven-development`
  are OUTSIDE the discipline.
- **skills/plan/SKILL.md** Identity section gains v0.10.0 vendored-
  surface relationship note: `/athanor:plan` stays the cross-model dual-
  planner default. DO NOT silently downgrade to `/athanor:ce-plan`.
- **skills/work/SKILL.md** Identity section gains v0.10.0 vendored-
  surface relationship note: `/athanor:work` stays the Spec-then-TDD
  flow. `/athanor:ce-work` and `/athanor:sp-test-driven-development`
  are OUTSIDE.
- **scripts/hooks/stop_verify_claims.py** docstring extended with
  v0.10.0 vendored-surface honesty note (gate scope unchanged at
  runtime; whitelist coverage tuned to athanor voice).
- **Version bumps** across `.claude-plugin/plugin.json`,
  `.claude-plugin/marketplace.json`, schema `$id` URL pinned to
  `v0.10.0` tag (in `schemas/athanor-config.schema.json`, `athanor.json`,
  `templates/athanor.json`).
- **plugin description + keywords** expanded with `vendored-ce` and
  `vendored-superpowers` keywords.

### Voice (what v0.10.0 deliberately does NOT claim)

- NOT a feature-parity claim. v0.10.0 vendors upstream content with
  provenance; it does not promise that every vendored skill is fully
  validated under athanor's runtime semantics (Thin Leader, Stop hook
  gate, etc.). Users invoking vendored skills are running
  surface-discovered upstream content via athanor's worker dispatch.
- NOT a Stop-hook scope extension. The runtime gate stays athanor-voice-
  tuned at v0.10.0; vendored skill outputs may bypass the whitelist
  through prose-voice differences. Vendor-aware whitelist is v0.10.1+
  work.
- NOT a re-license or upstream substitute. athanor stays MIT; CE and
  superpowers stay MIT under their copyright holders. T2 vendoring
  preserves all upstream license text in NOTICE.md.
- NOT an upstream deprecation. Users may still install CE and
  superpowers as separate plugins; athanor v0.10.0 just doesn't require
  them to be installed.
- NOT a synonym for "athanor supersedes CE". The two plugins have
  different identities. athanor v0.10.0 absorbs CE's skill surface;
  CE's release cadence, sub-agent evolution, and design direction remain
  with Every Inc.

### Migration (from v0.9.0)

- No breaking changes to athanor-native skills. Existing `/athanor:plan`,
  `/athanor:work`, `/athanor:discuss`, etc. behave identically to v0.9.0.
- New `/athanor:ce-*` and `/athanor:sp-*` commands become reachable
  automatically after plugin reload.
- If you have custom hooks or scripts that grep `skills/<n>/SKILL.md`,
  they now match ~50 additional entries at depth 1. Filter by directory
  prefix (`ce-`, `sp-`) if you only want athanor-native skills.
- Schema URL pin moved from `v0.9.0` to `v0.10.0`. Existing athanor.json
  files in user projects continue to validate against the v0.9.0 schema
  until they're regenerated; the schema is backwards-compatible at this
  release.

### Deferred (explicitly NOT in v0.10.0)

- **v0.10.1 vendor-drift check** — `scripts/check_vendor_drift.py` to
  diff vendored content against upstream plugin caches; manual diff
  process documented in `docs/STATE.md` §Vendor Manifest until then.
- **v0.10.1+ vendor-aware Stop-hook whitelist** — expand phrase set to
  cover vendored skill output idioms.
- **v0.10.2 LFG pipeline reconciliation** — both athanor LFG (implicit;
  user-chained) and vendored `/athanor:ce-lfg` (CE's end-to-end pipeline)
  now exist. A unified flow is its own brainstorm.
- **v0.10.3 superpowers `using-superpowers` cross-cutting integration**
   — vendoring the SKILL.md verbatim is the v0.10.0 deliverable; running
  superpowers' "skill-invocation BEFORE any response" rule across
  athanor-native skills is its own scope (would impact every skill).
- **v0.11.0+ deprecation candidates** — `/athanor:discuss` synthesis
  mode partially overlaps with `/athanor:ce-brainstorm` (athanor v0.9.0
  already absorbed clarify-mode equivalent); deprecating one in favour
  of the other is its own scope.

### Regression test surface

- 10 new regression test files (M6) pin identity guards, provenance
  invariants, namespace policy, and honesty arc voice. Total test count
  ~255 baseline + ~25 new ≥ 280 passing on Python 3.x with `jsonschema`.

## [0.9.0] — 2026-05-19

**`/athanor:discuss` dual-mode expansion — clarify (intent명확화) +
synthesis (옵션 A/B 합성).** v0.9.0 closes the gap identified during the
v0.8.0 session: `/athanor:discuss` previously demanded a pre-defined
A vs B dilemma in Step 1, so users with ambiguous intent had no athanor-
native path to clarify what they actually wanted. v0.9.0 absorbs an
intent-clarification mode into the existing skill (no new command),
modeled after `compound-engineering/ce-brainstorm` Phase 1.2–1.3: at
Step 1 the leader asks one mode-selection question; in **clarify mode**
the leader runs a single-Claude gap-probe dialog over the four lenses
(evidence / specificity / counterfactual / attachment) and writes
`.athanor/sessions/{id}/requirements.md` using the vendored ce-brainstorm
requirements-capture template; in **synthesis mode** the existing v0.7.x
Researcher / Devil's Advocate / Critic flow runs unchanged. `/athanor:plan`
Step 1 now auto-loads `requirements.md` (when present) and the Critic
Rubric gains axis (C) R-ID traceback coverage. Mechanism stays **advisory
dialog mode / planner-classified gap probes** — same honesty arc as
v0.7.7~v0.8.0.

Plan: `docs/plans/2026-05-19-002-feat-v0.9.0-discuss-clarify-mode-plan.md`
Origin: `docs/brainstorms/2026-05-19-002-discuss-clarify-mode-requirements.md`

### Added (advisory dialog — single-Claude clarify mode)

- **Step 1 mode dispatch in `/athanor:discuss`** (U1): three-option menu —
  (A) options A/B already clear → synthesis; (B) clarify intent first →
  clarify; (C) "먼저 의도를 정리하고 싶다" → default-to-clarify (chain to
  synthesis via Phase 4 menu later if options emerge). AskUserQuestion
  preferred, numbered-list fallback. R7 synthesis preservation regression
  added so existing Researcher / Devil's Advocate / Step 2.5 / Critic /
  Step 4 / Codex dispatch matrix cannot silently drift.
- **Step 2-clarify single-Claude dialog protocol** (U2): four-gap internal
  scan (evidence / specificity / counterfactual / attachment) + one-
  question-per-turn + AskUserQuestion-for-narrowing + open-ended-for-
  introspective-probes + integration check + Phase 2.5 scoping synthesis
  before write. **Leader-side stop-phrase guard** prevents the leader from
  emitting "계속할까요?" / "Should I continue?" to short-circuit the
  dialog (Codex review P1 #6 closure).
- **`skills/discuss/references/clarify-gap-probes.md`** vendored (MIT, T2
  pattern from ce-brainstorm). Full lens definitions, probe examples,
  probe-form rules (rigor → open-ended; narrowing → blocking menu),
  one-question rule, integration check, exit condition.
- **Step 3-clarify-finalization** writes
  `.athanor/sessions/{id}/requirements.md` using the vendored
  requirements-capture template (U3). 11-section structure (Summary /
  Problem Frame / Actors / Key Flows / Requirements / Acceptance
  Examples / Success Criteria / Scope Boundaries / Key Decisions /
  Dependencies / Outstanding Questions) with stable IDs (A-IDs / F-IDs /
  R-IDs / AE-IDs).
- **`skills/discuss/references/requirements-capture.md`** vendored (MIT,
  T2 pattern). Section matrix + ID conventions + frontmatter format +
  layout rules + finalization checklist.
- **Step 3-clarify-handoff Phase 4 menu** (U4): 4-option menu after
  requirements.md is saved — [1] /athanor:plan with auto-inject; [2]
  synthesis chain via same session **with explicit Option A/B dilemma
  confirm step** (Codex review P1 #3 closure — existing Step 2 assumes
  a parsed dilemma); [3] /athanor:analyze auto-invoke; [4] save-and-stop
  (no auto-dispatch). AskUserQuestion preferred, numbered-list fallback.
- **`/athanor:plan` Step 1 auto-loads `requirements.md`** (U5) when
  present in the session, injecting its full body as the "Origin
  requirements" context block for Planner A. Ordering when all three
  inputs present: analyze.md → requirements.md → discuss.md. Backwards
  compat preserved (absent → pre-v0.9.0 behavior).
- **v0.8.0 Critic Rubric extended to three axes** (U5 + Codex review P1
  #5 closure): axis (C) R-ID traceback coverage added — gated on
  requirements.md presence; flags behavior-bearing phases that fail to
  cite-back origin R-IDs / A-IDs / F-IDs / AE-IDs in Verify MUST/SHOULD
  bullets. All three Critic Agent prompt blocks (deep 4-input, deep
  2-input review-skipped, standard 2-input refinement) extended with
  axis (C) inline so the dispatched Critic actually sees the rubric.
- **CLAUDE.md Commands table `/athanor:discuss` row updated** (U6) —
  "Decision brainstorming + intent clarification (dual mode: clarify ↔
  synthesis)". skill frontmatter description trigger keywords extended
  with **qualified** clarify-direction phrases (Codex review P1 #4
  closure): 의도 명확화 / 요구사항이 헷갈려 / 무엇을 만들지 헷갈려 /
  뭘 해야할지 모르겠어 / 명확히 정리해줘. Bare 헷갈려 explicitly
  NOT a trigger (would overlap with /athanor:debug).
- **7 new regression-test files**: discuss mode question + R7 synthesis
  preservation (11 tests), clarify dialog protocol (11), clarify
  requirements template (9), clarify handoff menu (7), plan reads
  requirements.md + Critic axis (C) (7), claude_md_honesty extension
  (+2), discuss trigger keywords (5). Total ≥48 new + 207 prior = 255
  passing.

### Changed

- Plan / plugin version: v0.8.0 → v0.9.0 (minor bump — new feature
  surface in `/athanor:discuss`).
- JSON Schema `$id` URL release-tag pin: v0.8.0 → v0.9.0.
- `skills/discuss/SKILL.md` Step 1 reshaped (single-pass dilemma confirm
  → 4 sub-steps: restate → mode question → branch → synthesis-only
  dilemma confirm).
- `skills/plan/SKILL.md` Step 1 expanded with requirements.md input
  + ordering rules + R-ID cite-back instruction.
- `skills/plan/SKILL.md` Critic Rubric (v0.8.0) extended to three axes
  (A, B, C); each Critic Agent prompt block inline-rubric updated to
  reference axis (C).

### Voice / honesty

- Mechanism is **advisory dialog mode / planner-classified gap probes** —
  no runtime hook enforces clarify-mode discipline. Stay consistent with
  v0.7.7~v0.8.0 advisory/enforced labeling arc.
- "intent-clarification enforced" / "ce-brainstorm equivalent" / "clarify
  enforced" overclaim phrases intentionally avoided. Regression test
  asserts absence (`tests/test_regression_claude_md_honesty.py`,
  `tests/test_regression_discuss_trigger_keywords.py`).
- Trigger keyword expansion uses **qualified** phrases. Bare "헷갈려"
  rejected (overlaps with `/athanor:debug` domain).
- Codex involvement deliberately NOT introduced into clarify mode —
  single-Claude dialog is the symmetric choice (ce-brainstorm itself is
  single-agent). Synthesis mode preserves the existing Worker B Codex
  dispatch.
- R-ID cite-back is **advisory** in plan-side Critic axis (C). Critic
  flags missing cite-backs but the plan can still ship with gaps (the
  Critic comment surfaces the gap to the user; no hard-block).

### Migration

- No user-facing migration required. Existing `/athanor:discuss` callers
  see the new Step 1 mode question but their synthesis-mode flow is
  byte-identical to v0.7.x once they select option [A].
- Existing 5 grandfathered plan docs continue to run cleanly through
  `/athanor:plan` (requirements.md absent → pre-v0.9.0 behavior).
- `requirements.md` artifact is per-session; old sessions without it
  remain valid; new sessions in clarify mode produce it.

### Deferred (post v0.9.0)

- **v0.9.0.1 fast-follow**: optional second-pass Codex review of the
  clarify-mode prose may surface refinements; if so, ship under a
  follow-up PR (no implementation-side changes anticipated).
- **v0.9.1**: Deep-product tier durability gap probe added to clarify
  mode (currently Standard tier only — 4 lenses). Auto-chain opt-in
  flag for clarify → synthesis transitions.
- **v0.9.x**: clarify dialog cross-model option (Codex contrarian
  variant). Auto-classification heuristic re-examined based on
  operational mode-distribution data.
- **v0.9.x**: `/athanor:work` Splitter direct read of `requirements.md`
  (currently routes via /plan).
- **v0.10.0+**: Operational data may justify auto-mode-detection
  heuristic to replace the Step 1 question (current default: always
  ask).

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
  Total test count after main implementation + Codex-review autofix +
  dual-review (Opus + Codex) autofix: 197 passing (154 baseline + 39 new
  across U1-U7 + 4 from initial Codex autofix; further dual-review fixes
  land in the same PR with additional test coverage).

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

- **v0.8.0.1 (fast-follow)**: Splitter classification heuristic refinement —
  add `classification_reason` field per subtask + ambiguous-case fixtures
  (Codex implementation-review Medium #3). Current 3-bullet heuristic is
  sufficient for the obvious source / prose / config splits but leaves edge
  cases (build scripts, infrastructure-as-code, mixed-purpose JSON outside
  the security-adjacent enumeration) under-specified. The deferred fix
  surfaces the planner's reasoning so Splitter mistakes are auditable.
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
