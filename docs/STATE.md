# Athanor — Implementation State

> 이 파일은 현재 구현 진행 상태를 추적합니다.
> 각 Phase / 릴리스 완료 시 업데이트합니다.
> 자세한 변경 내역은 `CHANGELOG.md` 를 정본(source of truth)으로 봅니다.

## Current Phase: v0.24.4 — skill prompt diet (refactor patch on v0.24.3)

**v0.24.4** (released 2026-07-04) — Refactor patch landing one merged PR since
v0.24.3 (#88, `9f82019`), from a cross-model deep-plan (Planner A + contrarian
B + 2 cross-reviews + Critic): a **skill prompt diet**. Four advisory /
explanatory sections (zero test refs, zero gate/load-bearing logic) were
relocated out of the hot-path `lfg` / `lfg-goal` skills into four NEW reference
files (`skills/lfg/references/freeze-residual.md`;
`skills/lfg-goal/references/{enforcement-scope,release-strategy,lfg-vs-lfg-goal}.md`).
Char delta: `skills/lfg/SKILL.md` 40,220 → 39,489 (-731); `skills/lfg-goal/SKILL.md`
49,610 → 45,480 (-4,130). Inline pointers preserve the decision-relevant
summaries (advisory label, D2 loose-coupling, default-value docs) — behavior
unchanged. Two new lint checks land in `scripts/gates/lint_checks.py`
(+192 lines): `skill_size_cap_check` (regrowth ratchet, cap =
round(post-diet length × 1.05) per skill across 8 skills — prevents the next
lfg-goal size regression but does NOT enforce further shrink) and
`skill_line_number_ref_check` (bans new bare `line NNN` deep-prose refs in
`skills/**/*.md`, `\d{2,5}` threshold + fenced/file:line allowlists). Four
rotted line-anchor cross-refs were fixed to `(§heading)` form (one cross-file);
a narrow de-fossil pass touched only the relocated sections with locked-window
tags preserved. +12 regression tests; full suite 1677 passed; adversarial
review APPROVE_WITH_NITS. Honest scope: ZERO behavior change and ZERO existing
tests modified — this is pure relocation + additive lint guardrails. Deferred
to a future release (lock-retarget cost): `/athanor:lfg` Step 8.5 (~15.6k chars,
~30 locality assertions) and `/athanor:lfg-goal` Score-Target Loop / Goal
Storage / Resume-Loop remain inline. The plugin surface stays frozen: 4
registered agents (`ci-watcher`, `codex-dispatcher`, `learner`, `releaser`) and
the existing native command set are untouched. This patch updates the v0.24.3
Current Phase in place (no Current→Previous rotation); the v0.24.3
portable-invocation narrative follows.

### v0.24.3 — portable external invocation (hardening patch on v0.24.2)

**v0.24.3** (released 2026-07-03) — Hardening patch landing one merged PR since
v0.24.2 (#86, `9f5146b`): portable external invocation for athanor's own
enforcement/plumbing, closing two verified cross-platform holes surfaced by the
7/3 delta ref-analysis and designed via cross-model deep-plan. **(N1)** The 3
ENFORCED hooks were invoked as bare `python3` in `hooks/hooks.json`; on Windows
the App-Execution-Alias Store stub shadows `python3`, so in a live incident
(2026-07-01) the **Stop gate fail-opened silently** — identity invariant #4
(completion-claim verification) never fired. New `scripts/hooks/run_hook.sh`
launcher resolves the interpreter by functionality probe (`import sys` + py≥3.10,
stdin `</dev/null`) over `python3` → `python` → `py -3`, then `exec`s the winner
(exit-2 blocking + stdin propagate preserved); no working interpreter → exit 1
**loud pass** with `INACTIVE` stderr (no silent fail-open); no caching.
`hooks.json`/`catalog.json` kept in lockstep, perf-budget gate regex fails loud
on drift, `.gitattributes` pins `*.sh` LF. This closes the dropped v0.7.8
portable-invocation promise (see the CLOSED ledger entry below). PreToolUse
python-less fail-open is an honest-labeled residual. **(N2)** Portable `timeout`
resolver (companion-fix to v0.24.2, which assumed GNU coreutils — stock
macOS/BSD had no `timeout` and exited 127 before git/gh/codex ran): all lfg /
ci-watcher / codex-dispatcher sites now use
`TIMEOUT_CMD=$(command -v timeout || command -v gtimeout)` + fail-loud exit-127
FATAL; the codex-dispatcher exit table gains the 127 row. +18 regression tests
(11 portable-hook incl. the 2026-07-01 live-incident replay, 7 portable-timeout);
v0.24.2 locks strengthened; full suite 1665 passed; adversarial review
APPROVE_WITH_NITS (nits applied). Honest impact: a cross-platform
correctness/robustness fix to athanor's own enforcement + plumbing; no score
re-baseline claimed. The plugin surface stays frozen: 4 registered agents
(`ci-watcher`, `codex-dispatcher`, `learner`, `releaser`) and the existing native
command set are untouched. User-facing: the hook-command change triggers a
one-time hook re-approve prompt on plugin update (command hash mismatch). This
patch updates the v0.24.2 Current Phase in place (no Current→Previous rotation);
the v0.24.2 lfg-git-plumbing narrative follows.

### v0.24.2 — lfg git fail-loud plumbing (hardening patch on v0.24.1)

**v0.24.2** (released 2026-07-01) — Hardening patch landing one merged PR since
v0.24.1: fail-loud git plumbing for the autonomous `/athanor:lfg` pipeline.
Every unattended `git push` / `git commit` in `/athanor:lfg` (Steps 4/7/8) and
`agents/ci-watcher.md` (Step 4) now runs with `GIT_TERMINAL_PROMPT=0`, stdin
redirected from `/dev/null`, and a finite `timeout` — a guard that was absent
repo-wide, so an interactive credential / 2FA / LFS prompt would block on stdin
and silently hang the unattended pipeline indefinitely. Git now fails fast with
a non-zero exit into the existing push-failure diagnosis path. Pure hardening of
existing plumbing (no new surface); `/athanor:lfg-goal` is unchanged (pure
wrapper); +7 regression tests (`tests/test_regression_lfg_git_hardening.py`). A
companion "Codex CLAUDE.md preamble" candidate was refuted (AGENTS.md already
mirrors CLAUDE.md for Codex) and not shipped. Honest impact: a minor
correctness/robustness improvement to lfg plumbing; no score re-baseline
claimed. The plugin surface stays frozen: 4 registered agents (`ci-watcher`,
`codex-dispatcher`, `learner`, `releaser`) and the existing native command set
are untouched. This patch updates the v0.24.1 Current Phase in place (no
Current→Previous rotation); the v0.24.1 adversarial-quality-hunt narrative
follows.

### v0.24.1 — Adversarial Quality Hunt (correctness + docs patch on v0.24.0)

**v0.24.1** (released 2026-06-30) — Patch release landing two merged PRs since
v0.24.0 from an `ultracode` quality hunt (11 finders → adversarial verification →
18 confirmed / 5 phantom findings rejected, verify-before-cut → two `/athanor:lfg`
fix cycles; all fixes, no new features). PR #81 (`a3b9527`) fixes 10
adversarially-confirmed correctness bugs in load-bearing hook/gate code (+23
regression tests), led by two HIGH safety fixes: (1) the `/athanor:lfg` merge-gate
G2 unresolved-review-residual clause was fail-open — it keyed only on the `blocker`
severity token while `/athanor:review` emits critical/high/medium/low, so an
unresolved CRITICAL residual could reach a MERGE verdict; broadened to
`(blocker|critical|high)`, fail-safe. (2) the PreToolUse kernel-guard
destructive-shell matcher was whole-command unanchored, so a chained checkout-dot
form bypassed the block while a quoted mention was false-blocked; now
segment-anchored. The remaining 8 (5 MED / 3 LOW) cover the force-push `+refspec`
form, a `test_` credential-exemption path-substring that exposed a real `.env`, a
merge-gate crash on a non-UTF-8 findings file (now exit 2), stop-hook attribution
over-suppression, an evidence-gate bare-substring match, and three
sniffer/controller LOW fixes. PR #82 (`d0d7405`) fixes 6 adversarially-confirmed
doc-staleness items (DESIGN.md agent-partition verify command + ghost `models`
config key, STATE.md deleted-test citation, freeze.md `warn`-mode omission + wrong
test filename, `/athanor:setup` freeze-mode omission, stale
package-knowledge-index review stamp). Honest re-assessment after the hunt:
correctness 88→90 (newly meets its floor), documentation 86→89, test_coverage
83→84, overall 89→~90; net new tests +23. The plugin surface stays frozen: 4
registered agents (`ci-watcher`, `codex-dispatcher`, `learner`, `releaser`) and
the existing native command set are untouched. This patch updates the v0.24.0
Current Phase in place (no Current→Previous rotation); the v0.24.0 base-release
narrative follows.

### v0.24.0 base — Governance Subsystem Removal + Executable lfg Merge Gate

**v0.24.0** (released 2026-06-30) — Minor release landing six merged PRs since
v0.23.0; net diff 63 files, +2,129 / −8,626. The headline is the **removal of
the P26–P30 self-validating governance subsystem** (PR #79, −8,599 LOC across
42 files): a subsystem that scored itself (the `organization_score.py`
self-scorer) and gated CI on its own existence, with zero external /
marketplace / `plugin.json` consumer. Removed were 5 gate scripts, 5 org tests,
6 schemas, 5 docs, ~12 artifacts, and 5 decision JSONs, across 4 CI-green
phases; `work_item_stage.py` and `harness_decision_ledger.py` (separate, live)
were kept. Alongside it ships an **executable fail-loud merge-readiness gate**
for `/athanor:lfg` Step 8.5 (PR #74, `scripts/gates/lfg_merge_gate.py`): stdin
`gh pr view` JSON → `merge | block | skip` verdict + deciding clause (exit
`0`/`2`/`3`/`4`), unknown `mergeStateStatus` enum → exit `2` (fail-loud),
`CLEAN`-only merge, structurally verdict-only (cannot `--admin` / bypass branch
protection); +19 exec tests. The gate's honesty label stays **advisory** (an
executable verdict, but no runtime hook forces the leader to honor it — same
class as the fix-round counter).

Two **fail-loud-over-silent-fallback** bugs were fixed (PR #75): the
`${CLAUDE_PLUGIN_ROOT}` sentinel anchor restored in
`verification-before-completion` SKILL.md + `receipt-validator.md` (a bare path
had silently degraded Stop-hook invariant #4 in user projects), and a `*)`
default arm added to both `codex.fallback` case blocks in
`codex-availability.md`; +6 regression tests. Dead `lfgGoal.userConfirmAfter`
config (schema-advertised but unconsumed) was removed (PR #77), and ~24 lines
of P26 overlay prose were relocated from the `lfg` / `lfg-goal` hot-path skills
to docs (PR #76) — the suspected "~2000 LOC over-build" was found to be
live/tested code and kept, so only the prose moved (over-claim rejected as an
honesty win). The analyze + debug skills gained their first behavioral
regression tests (PR #78) plus 4 `freeze.md` function-name fact-corrections;
net new tests across the release: +25. The plugin surface stays frozen: 4
registered agents (`ci-watcher`, `codex-dispatcher`, `learner`, `releaser`) and
the existing native command set are untouched.

Identity invariants intact (4): Thin Leader / cross-model adversarial /
Spec-then-TDD / Stop hook gate.

## Previous Phase: v0.23.0 — 한글 완료 요약 Step for /athanor:lfg + /athanor:lfg-goal

**v0.23.0** (released 2026-06-25) — Minor release shipping a single
`/athanor:lfg` / `/athanor:lfg-goal` user-experience addition landed on main
since v0.22.1 (merged as `6f6301e`). A **한글 완료 요약 step** — a Korean
completion summary the leader presents when the pipeline finishes
(`/athanor:lfg` new Step 9.5) and when the macro loop finishes (`/athanor:lfg-goal`
terminal subroutine on all 6 exit points: goal-met, abort, the three
durable-residual exits, and the Tier-2-split break, each reporting which state
ended the loop). It is **advisory leader-prose** (Present-to-User; no new
runtime gate, no new file) and follows the canonical `output.language` resolver
(`ko`→한글, `en`→English, default `en`) without i18n duplication — the English
path is preserved. Machine tokens (the `merge:` 8-state value, `G1..G5`,
`<promise>DONE</promise>`, `validation_status`, `goal_met`) stay English and are
emitted before the summary in the same terminal turn, and the prose is hook-safe:
every Stop-hook-whitelisted Korean literal is backtick-wrapped on a 회피-marked
line and example output uses factual/passive phrasing. The regression lock
extends `tests/test_regression_output_language_directive.py` (widened
`MATERIAL_CLAIMS_KO` as a strict subset of the hook set + 8 new tests covering
step presence, ordering, all-terminal coverage, machine-token-English,
canonical-pointer, advisory label, and section-scoped hook-safety). The plugin
surface stays frozen: 4 registered agents (`ci-watcher`, `codex-dispatcher`,
`learner`, `releaser`) and the existing native command set are untouched.

Identity invariants intact (4): Thin Leader / cross-model adversarial /
Spec-then-TDD / Stop hook gate.

## Previous Phase: v0.22.1 — Worker Context Packet Convention (slim)

**v0.22.1** (released 2026-06-25) — Patch release shipping a single
documentation-only convention landed on main since v0.22.0 (PR #69, merged as
`5a42bdc`). New `docs/worker-context-packets.md` (~61 lines) is a lightweight,
**advisory** dispatch-hygiene convention: it names what a clean-context worker
should be handed in its dispatch packet and what it must return, but instead of
re-encoding any contract it references the existing canonical sources — the
executor dispatch packet in `skills/work/references/splitter.md`, the
`ATHANOR_RESULT` result schema in `skills/work/references/spec-then-tdd-handler.md`,
and the runtime write-scope in `skills/work/references/freeze.md`. It is
**convention-only and not runtime-enforced**; a single doc-pin regression test
locks the cross-references. (It supersedes an initially over-built schema+gate
build-out that cross-model review shrank to a small net doc addition.) The
plugin surface stays frozen: 4 registered agents (`ci-watcher`,
`codex-dispatcher`, `learner`, `releaser`) and the existing native command set
are untouched.

Identity invariants intact (4): Thin Leader / cross-model adversarial /
Spec-then-TDD / Stop hook gate.

## Previous Phase: v0.22.0 — Default-On lfg Auto-Merge + Strengthened lfg-goal Loop

**v0.22.0** (released 2026-06-24) — Minor release shipping two
`/athanor:lfg` / `/athanor:lfg-goal` improvements landed on main since
v0.21.0. First, **`/athanor:lfg` Step 8.5 auto-merge flips to opt-out
(default ON)**: the `lfg.autoMerge` default is now `true`, so a green PR is
merged once the unchanged conjunctive merge-readiness gate (G0–G5) passes;
disabling collapses to a one-flag opt-out (`--no-merge` renamed to
`--unmerge`, fail-safe direction wins ties), `--merge` stays the
explicit-enable counterpart, and the disabled-skip state is renamed
`skipped-merge-disabled` (gate logic, disposition table, re-poll, merge
command, never-`--admin` rule, and releaser boundary all unchanged).
Second, the **`/athanor:lfg-goal` durable loop controller is strengthened
(PR #65)** with an adaptive score-target router — assessment-evidence
validation with fail-loud parsing, a two-way `target_met` cross-check
against computed scores, and baseline/delta assessment → lfg-cycle routing
carrying the lowest-scoring dimensions — plus review-hardening that bounds
persistent block/escalate states (a stuck `eval_status=fail` /
invalid-receipt loop terminates via `stop_no_progress` → `aborted` instead
of spinning) and a CLI exit-code contract that returns non-zero for all
stop/block actions (`exit 0` ⟺ a forward action was authorized). New
fixture-gate scenarios + a re-drive regression test lock the loop behavior.
The plugin surface stays frozen: 4 registered agents (`ci-watcher`,
`codex-dispatcher`, `learner`, `releaser`) and the existing native command
set are untouched.

Identity invariants intact (4): Thin Leader / cross-model adversarial /
Spec-then-TDD / Stop hook gate.

## Previous Phase: v0.21.0 — Opt-in /athanor:lfg Auto-Merge + Step 8.5 Gate

**v0.21.0** (released 2026-06-24) — Minor release that publishes the opt-in
`/athanor:lfg` auto-merge surface: after CI goes green, `/athanor:lfg` Step 8.5
can optionally merge a green PR to its base branch (`gh pr merge --rebase
--delete-branch`), gated by a fail-loud conjunctive merge-readiness check
(re-entry/draft state, dual-source residual review blockers, unresolved-CI
section, an exhaustive 8-value GitHub `mergeStateStatus` disposition, and
merge-queue detection). It is off by default and opt-in via the
`--merge`/`--no-merge` flag or `athanor.json` `lfg.autoMerge` (`--no-merge` wins
ties); on any failed clause the leader leaves the PR open, reports which clause
failed, and still finishes the pipeline, never `--admin`-bypassing branch
protection. The step merges only — version-bump/tag/CHANGELOG/STATE.md stays the
`athanor-releaser` ceremony — and the gate is advisory (leader-prose-enforced;
no runtime hook blocks the merge). The plugin surface stays frozen: 4 registered
agents (`ci-watcher`, `codex-dispatcher`, `learner`, `releaser`) and the existing
native command set are untouched.

Identity invariants intact (4): Thin Leader / cross-model adversarial /
Spec-then-TDD / Stop hook gate.

## Previous Phase: v0.20.1 — output.language Presentation Preference

**v0.20.1** (released 2026-06-23) — Patch release that ships the never-published
`output.language` presentation preference (merged to main after v0.20.0 in commit
`cdf76e5`, but never released). `output.language` is a best-effort advisory
user-facing language preference (enum `ko|en`, default `en`; this repo runs `ko`):
the leader interprets it at present-time across the 9 native Thin Leader skills,
injecting a conditional per-language directive so prose surfaces can render in the
chosen language while machine-parse surfaces (result schemas, JSON, gate output)
stay English. The English-default behavior is unchanged, and the plugin surface
stays frozen: 4 registered agents (`ci-watcher`, `codex-dispatcher`, `learner`,
`releaser`) and the existing native command set are untouched.

Identity invariants intact (4): Thin Leader / cross-model adversarial /
Spec-then-TDD / Stop hook gate.

## Ref-driven optimization surface (current status)

Standing summary carried forward when the v0.20.0 phase block was archived
(`docs/archive/STATE-history.md`) under the bounded-history trim — this status
is current, not phase history, so it lives outside the dated phase blocks. The
**346-ref optimization** gate bundle stays local-first and read-only:
catalog admission, memory index, memory retrieval eval, workflow trace query,
Codex mirror parity, work-item stage transition, and ship-profile reduction,
with `ref/` kept repo-local rather than default-packaged context. The plugin surface
stays frozen — 4 registered agents (`ci-watcher`, `codex-dispatcher`,
`learner`, `releaser`) and 13 native commands are unchanged.

## History (시계열 요약 — 자세한 항목은 CHANGELOG.md 참조)

### Foundation — v0.1.0 ~ v0.5.x (2026-04-08 ~ 2026-04-14)

- **Phase 0–9 (v0.1.0)**: 초기 scaffold → /athanor:setup → CONVENTIONS.md → /athanor:discuss → /athanor:analyze → /athanor:plan (cross-model adversarial pipeline) → /athanor:work solo → /athanor:work --team (wave grouping, discovery relay) → Lessons system (learner + cleaner) → README & defense mechanisms 문서화.
- **v0.2.x ~ v0.5.x**: tier 분리 (lite/standard/deep plan), `/athanor:debug` triage, 파일명 중립화 (plan-claude/plan-codex → plan-a/plan-b), Codex CLI fallback 정비.

### Hook hardening cycle — v0.6.x (2026-04-15 ~ 2026-04-17)

- **v0.6.0**: `scope-drift` skill 추가.
- **v0.6.1**: `hooks.json` prompt-type 필드 수정, marketplace manifest 정리.
- **v0.6.2**: agent description 충돌 해소 (Codex dispatch collision in `/athanor:deep-plan`).
- **v0.6.3**: plugin.json `hooks` 필드 잔존 → `Duplicate hooks file detected` 회귀 fix.
- **v0.6.4**: validate-plugin gate 강화, duplicate-hooks path check 추가, live-load evidence enforce.

### Contract-first defense — v0.7.x (2026-04-17 ~ 2026-04-24)

- **v0.7.0**: 28-subtask `/athanor:work --team` 세션 (`2026-04-17-001`)으로 11개 contract 종결. CHANGELOG.md bootstrap (15개 historical tag), `scripts/check_release_ready.py`, 3개 regression fixture + pytest 도입, `/athanor:setup` self-audit Check #7–11 (vendoring-gate + regression invariants), `agents/cleaner.md` §Schema-Validation, `agents/learner.md` §On Release, `docs/DESIGN.md` §Agent Registration.
- **v0.7.1**: PR #3 adversarial-review follow-up. `check_a_evidence`를 `## v<version>` anchor 기반 word-boundary regex로 강화, `scripts/gates/manifest_checks.py` 모듈로 hook 게이트 일원화 (3-way duplicate path 통합), `Path.resolve()`로 cross-platform 통일.
- **v0.7.2**: Stop hook을 material-claim 트리거로 narrow. analysis/planning/research Q&A turn에서의 user-fatigue 제거. `fixture_narrowed_stop_prompt.json` + `test_current_hooks_contains_narrowed_gating_markers` 회귀 추가.
- **v0.7.6 (2026-05-02)**: 5-agent ref deep-dive + Codex cross-validation. 최우선 contract-default `athanor.json` 파일 신설. `agents/reviewer.md` confidence-anchored review findings (CE persona reviewer pattern).
- **v0.7.7 (2026-05-18)**: Truth-in-documentation release. Stop hook 라벨을 `enforced` → `advisory (prompt-based)`로 정직하게 demote, schema/template/config `_doc` 거짓 claim 시정, `schemas/athanor-config.schema.json` (draft-07) 신설 + `$schema` URL을 release tag pin, `templates/athanor.json` 추출 + setup이 읽도록 변경, 6개 session-touching skill을 CLAUDE.md §Session Lookup Convention canonical rule로 정렬, `plan/SKILL.md` Step 3/4 intro tier-aware 재작성, `plan/discuss` skill에 `codex.enabled` + `codex.fallback` matrix 도입. 41 regression test 추가. PR #10 dual review (Opus + Codex)로 `_doc` 거짓 claim 잔존 catch + commit 6fdbd05로 시정.
- **v0.7.8 (2026-05-18)**: 스파이크-약속 enforcement upgrade. Stop hook이 `type: prompt` → `type: command`로 전환, `scripts/hooks/stop_verify_claims.py`가 stdin payload를 읽어 material-claim detection 수행 (English + Korean whitelist v0.7.7 prompt에서 verbatim 포팅) + exit 2로 Stop 차단, stderr가 모델 컨텍스트로 피드백. `verification-before-completion` skill에 §Emission Sentinel 추가 (`<!-- athanor:verification-emission v=1 -->` 응답 prefix로 hook이 re-entry 방지). `hooks.profile`의 `off`/`standard` 값만 honoured (`lenient`/`strict`는 deferred), `hooks.disabled[]` orphan 키 삭제. CLAUDE.md 라벨 `advisory (prompt-based)` → `enforced (command-based)`로 재승급. PR #10 dual-review에서 catch한 Major 4건 (Step 2 tier prose, Deep-tier 2-input Critic, /work review-skipped marker, analyze:301 today residual) 함께 처리.

### Concept absorption → atomic cut — v0.10.x ~ v0.12.0 (2026-05-19 ~ 2026-05-22)

- **v0.10.0 → v0.12.0**: v0.10.0 absorbed compound-engineering + superpowers as vendored skills; the v0.12.0 **atomic cut** corrected the scope (95 vendored items → 1 KEEP `ce-test-browser` + 5 concepts absorbed as prose). The 4 identity invariants survived the cutover. Detail: `docs/archive/concept-absorption-surface.md`.

## Live invariants (현 시점 contract status)

| Contract | 상태 | 보호 위치 |
|---|---|---|
| `stop-hook-command-contract` | ✅ enforced (v0.7.8 — runtime gate via `type: command` + exit 2) | `tests/test_regression_stop_command_hook.py` (registration) + `tests/test_regression_stop_hook_script.py` (decision flow) |
| `hook-uniqueness` | ✅ enforced | `tests/test_regression_hook_uniqueness.py`, `scripts/gates/manifest_checks.py::hook_uniqueness_check` |
| `manifest-no-hooks-field` | ✅ enforced | `tests/test_regression_manifest_hooks.py`, `scripts/gates/manifest_checks.py::duplicate_hooks_path_check` |
| `check_a_evidence` (release-time) | ✅ enforced | `scripts/check_release_ready.py::check_a_evidence` (word-boundary regex) |
| `schema-validates-config` (v0.7.7) | ✅ enforced | `tests/test_regression_schema_validates_config.py` |
| `schema-url-version-pin` (v0.7.7) | ✅ enforced | `tests/test_regression_schema_url_version_pin.py` |
| `session-lookup-convention` (v0.7.7) | ✅ enforced | `tests/test_regression_session_lookup_convention.py` |
| `vendoring-gate` (T0+T1 disproof) | ⚠️ LLM-driven only | `/athanor:setup` Check #7. CI 자동 실행 안 됨 (개선 후보) |
| `contract-ledger` presence | ✅ fixed (v0.18.x) | `/athanor:setup` Check #11 — fresh-checkout fast-path implemented: no sessions → PASS (info), not a hard FAIL. See `skills/setup/SKILL.md` §11 fast-path. |
| `learner-on-release` | ✅ ceremony 단계 (advisory) | `agents/releaser.md` Step 6 — release tag 후 leader가 Learner dispatch (`learner_on_release: pending-leader-dispatch` 신호). `agents/learner.md` §On Release |
| `agent-frontmatter-consistency` | ✅ enforced | `tests/test_regression_agent_effort_level.py` (registered-agent model tier + 7/4 partition lock), `tests/test_regression_v014_agent_definitions.py`, `tests/test_regression_codex_companion.py` |
| `stop-phrase-detection` | ❌ prose-only, enforce 없음 | CLAUDE.md §Defense Mechanisms (개선 후보) |
| `read-before-edit` | ❌ prose-only, enforce 없음 | CLAUDE.md §Defense Mechanisms (개선 후보) |

## Known gaps (다음 작업 후보)

- Memory 2-tier (`permanent → mem-search`) still has no mem-search MCP writer. Current implemented boundary is local `.athanor/lessons` frontmatter plus the read-only memory index (`docs/memory-index.md`) and compact handoff contract (`docs/handoff-artifact.md`).

## Command-hook Stop blocking spike (2026-05-18)

**Goal:** v0.7.8 plan(`.athanor/sessions/2026-05-18-001/plan.md` §SPIKE) prerequisite — empirically verify whether Claude Code runtime honors `type: "command"` Stop hooks with `exit 2` to block stop and feed stderr back to the model.

**Method:**
- Script: `scripts/hooks/stop_verify_claims.py` — no-op stub with one-shot exit 2 via `/tmp/athanor-spike-block.flag` + `/tmp/athanor-spike-done.flag` safety guard.
- Registered as parallel Stop hook in `~/.claude/settings.json` (NOT athanor plugin's hooks.json — current Claude Code session does not have athanor installed; user-global settings exercises the same runtime path).
- Logged every invocation to `/tmp/athanor-spike.log`.

**Result: PASS** — all four spike questions answered empirically:

| Q | Result | Evidence |
|---|---|---|
| Q1: Does `type: command` Stop hook execute? | ✅ YES | Log: `invoked event=Stop payload_bytes=554 argv=[...]` |
| Q2: Does exit 0 produce normal Stop? | ✅ YES | Phase A turn ended cleanly after PASSING entry |
| Q3: Does exit 2 block Stop? | ✅ YES | Phase B: user's intended message never reached model; instead Claude received system-formatted "Stop hook feedback" |
| Q4: Is stderr fed back as continuation context? | ✅ YES | Stderr appeared verbatim as `Stop hook feedback: [<command>]: <stderr text>` in model input |

**Empirical raw observation (Phase B):**

The next message after `exit 2` arrived at the model as:
```
Stop hook feedback:
[python3 /home/wook/work/06_athanor/scripts/hooks/stop_verify_claims.py]: athanor spike: blocking Stop to test command-hook gating semantics. This stderr message demonstrates whether type=command Stop hooks feed exit-2 stderr back to the model as continuation context.
```

The model recognized this as system feedback (not a user message) and continued processing in the same turn context. The user-facing UI showed no error.

**Timing observation (worth designing around):**

The log shows TWO Stop events that should have triggered exit 2 — first `14:26:31 PASSING` and then `14:27:04 BLOCKING`. The block flag was created via `touch` before the 14:26:31 Stop, yet only the 14:27:04 event detected it. Possible explanations:
1. The 14:26:31 event was M3's natural turn-end Stop fired before the next user message; the 14:27:04 event fired as a separate hook invocation (possibly pre-next-turn evaluation).
2. Filesystem sync race between `touch` from Bash tool's environment and the hook's `os.path.exists` from a possibly different working directory.

**Implication for v0.7.8 design:**
- Do NOT rely on `os.path.exists`-style transient state for gating decisions. Use the script's own evaluation of stdin payload (the hook event JSON), which is guaranteed-present.
- The v0.7.8 production script (`scripts/hooks/stop_verify_claims.py` v1) should parse `last_assistant_message` from stdin and decide entirely from message content + the M2 sentinel marker — NO filesystem flags.

**Cross-platform note:** Hook command was `python3 /home/wook/work/06_athanor/scripts/hooks/stop_verify_claims.py`. On Windows, `python3` may not be on PATH (`py -3` or `python` instead). v0.7.8 must use a portable invocation — proposal: shebang-less script + explicit `python` resolver in `hooks/hooks.json` per-platform OR a launcher shim. *(Dropped-promise closure: this portable invocation never shipped in v0.7.8 — reclassified as a known dropped promise — until the 2026-07-01 Windows Store-stub fail-open incident forced it; **shipped in v0.24.3 via `scripts/hooks/run_hook.sh` (portable launcher shim)** — functionality-probed `python3` → `python` → `py -3`, ≥3.10, exit-1 loud-pass when none work; locked by `tests/test_regression_portable_hook_interpreter.py`. This ledger entry is CLOSED.)*

**Decision:** v0.7.8 plan §SPIKE branch = **PASS path** (command hook with exit 2 enforcement, single-marker sentinel for re-entry, off/standard profiles only). M1 relabel in v0.7.7 references this spike with forward note: "v0.7.8 upgrades to enforced (command-based)."

**Cleanup performed:** hook removed from `~/.claude/settings.json`; `/tmp/athanor-spike*` files deleted. `scripts/hooks/stop_verify_claims.py` remains in repo as the v0.7.8 starting point (current state = no-op stub; will be extended in v0.7.8 PR with claim-classification + sentinel-detection logic).

## Phase 1 Checklist (historical, archived)

### 1.1 플러그인 로딩 검증 ✅
- [x] Claude Code에서 `--plugin-dir` 로 로딩 테스트
- [x] 5개 스킬이 `/athanor:` prefix로 표시 확인 (setup, discuss, analyze, plan, work)
- [x] plugin.json → .claude-plugin/plugin.json 이동 (Claude Code 규약)

### 1.2 Session 디렉토리 관리 ✅
- [x] `.athanor/sessions/` 자동 생성 로직 (setup SKILL.md에 구현)
- [x] 세션 ID 규칙: `YYYY-MM-DD-NNN`
- [x] 세션 디렉토리 템플릿 (discuss.md, analyze.md, plan.md, decisions.md, work-log.md, discoveries/)

### 1.3 Config 관리 ✅
- [x] athanor.json 로딩 로직 (setup worker가 처리)
- [x] 기본값 fallback (template에서 복사)

### 1.4 /athanor:setup 구현 ✅
- [x] Health check worker dispatch (thin leader 패턴)
- [x] 상태 테이블 출력 (6개 항목)
- [x] 트리거 언어 설정 (ko/en/both)

### 1.5 테스트 ✅
- [x] `/athanor:setup` 실행 → 동작 확인
- [x] Status table 정상 출력 확인
- [x] Agent Teams: ✓ enabled
- [x] LSP: ✓ available (built-in)
- [x] mem-search: 사용자 세션에서 검증 (MCP가 로드되어 있을 때)

### MCP 접근성 결론
- `-p` (non-interactive) 모드에서는 MCP 서버가 로드되지 않아 mem-search 미감지 가능
- 이는 테스트 환경 한계. 실제 사용자 세션에서는 MCP가 로드되어 있을 것
- fallback (.md 파일 통신)은 이미 설계에 포함되어 있음
