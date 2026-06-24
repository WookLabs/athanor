# Athanor — Implementation State

> 이 파일은 현재 구현 진행 상태를 추적합니다.
> 각 Phase / 릴리스 완료 시 업데이트합니다.
> 자세한 변경 내역은 `CHANGELOG.md` 를 정본(source of truth)으로 봅니다.

## Current Phase: v0.22.1 — Worker Context Packet Convention (slim)

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

## Previous Phase: v0.20.0 — Ref Optimization + uv Tooling Release

**v0.20.0** (released 2026-06-23) — Minor release that ships the never-published
`0.19.3` ref-optimization work as a single shipped version, folded together with
the score-95 uv/pyproject tooling migration, a Stop-hook opt-in deadlock fix, and
the `catalog_admission` CI fixes. The plugin surface stays frozen: 4 registered
agents and the existing native command set are unchanged, and the 346-ref
optimization gate bundle (catalog admission, memory index, Codex mirror parity,
work-item stage transition, durable-loop controller, workflow-trace eval,
hook-safety corpus, and package-footprint reduction) remains local-first and
read-only with `ref/` kept repo-local rather than default packaged context.

The score-95 increment migrates CI to `astral-sh/setup-uv` + `uv sync
--locked --dev` + `uv run` (new `pyproject.toml`, `.python-version` = 3.14, and
`uv.lock`, all dev-only in the ship profile), makes the installed-hook
`resolve_project_root()` honor `$CLAUDE_PROJECT_DIR` before the cwd walk-up,
promotes the PostToolUse evidence scope from `unspecified` to `full_suite`, and
hardens `/athanor:prompt-gen` (native + Codex mirror) to be output-only. The
Stop-hook fix makes `stop_verify_claims.py` exit 0 when no `athanor.json` is
present (the gate was unsatisfiable without opt-in because the sentinel path is
also opt-in-gated) and adds surrogate-safe (`surrogatepass`) sentinel-body
hashing on both emit and validate sides. `catalog_admission` now treats an
absent gitignored `ref/` corpus as vacuously clean.

Release verification closed with Claude/Codex manifest validation, distribution
smoke, topology/package/mirror gates, and the full pytest suite under `uv run`.

Identity invariants intact (4): Thin Leader / cross-model adversarial /
Spec-then-TDD / Stop hook gate.

## Previous Phase: v0.19.3 — Ref Optimization Release

**v0.19.3** (committed 2026-06-20, never published to the marketplace; folded
into v0.20.0) — Patch release for the 346-ref optimization pass. The plugin
surface stays conservative: 4 registered agents, 13 native commands, and no new
default live execution. The release packages the local-first gate bundle for
catalog admission, memory index, memory retrieval eval, workflow trace query,
Codex mirror parity, work-item stage transition, and ship-profile reduction
while keeping `ref/` plus historical planning, architecture, and test evidence
repo-local rather than default packaged context.

Release verification closed with Claude/Codex manifest validation, distribution
smoke, topology/package/mirror gates, and focused regression coverage.

Identity invariants intact (4): Thin Leader / cross-model adversarial /
Spec-then-TDD / Stop hook gate.

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
| `_doc-honesty` (v0.7.7+v0.7.8) | ✅ enforced | `tests/test_regression_doc_string_honesty.py` (models deprecated; hooks working contract) |
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

**Cross-platform note:** Hook command was `python3 /home/wook/work/06_athanor/scripts/hooks/stop_verify_claims.py`. On Windows, `python3` may not be on PATH (`py -3` or `python` instead). v0.7.8 must use a portable invocation — proposal: shebang-less script + explicit `python` resolver in `hooks/hooks.json` per-platform OR a launcher shim.

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
