<!-- Relocated from CLAUDE.md at v0.16.0.
     Canonical runtime reference remains in CLAUDE.md §Defense Mechanisms status table (1-paragraph summary per mechanism).
     This file contains verbose internals (detection pipeline, NFKC folds, residual lists) moved here to reduce per-session token load. -->

# Defense Mechanisms — Implementation Detail (Historical)

## Stop Hook Detection Pipeline

### Runtime contract (command-based, enforced)

On every `Stop` event, Claude Code invokes `scripts/hooks/stop_verify_claims.py`
(registered as `type: command` in `hooks/hooks.json`) with the Stop event
JSON on stdin. The script:

1. Reads the payload; extracts `last_assistant_message`. Fail-open on
   missing/unparseable stdin.
2. Reads `hooks.profile` from `athanor.json`. If `"off"`, exits 0 silently
   — the user has opted out of the runtime gate.
3. Checks whether the response begins with the emission sentinel
   `<!-- athanor:verification-emission v=2 nonce=<32-hex> -->` (anchored at
   the first non-whitespace line). If yes, exits 0 silently to prevent
   re-entry on the verification skill's own output.
4. Greps the response body for material-claim phrases (English + Korean,
   whitelist ported verbatim from the v0.7.7 prompt). On no match, exits 0.
5. On match, exits 2 with stderr directing the model to invoke the
   `verification-before-completion` skill. Claude Code feeds the stderr
   back to the model as continuation context; the model must produce
   fresh evidence before Stop succeeds.

**Spike evidence:** the 2026-05-18 dry-run confirmed Claude Code honors
`exit 2` from `type: command` Stop hooks (the user's intended next message
never reached the model; instead the model received the stderr as system
feedback). Full result in `docs/STATE.md` §"Command-hook Stop blocking
spike (2026-05-18)".

### Detection layers (chronological)

| Version | Layer added |
|---------|-------------|
| v0.7.7  | English + Korean phrase whitelist (initial baseline ported verbatim from the v0.7.7 prompt nudge) |
| v0.7.9  | Emission sentinel + nonce binding (`<!-- athanor:verification-emission v=2 nonce=<32-hex> -->`) + `hook_state` circuit breaker against re-entry |
| v0.10.2 | NFKC unicode normalization; Cyrillic confusables fold; 6 verb-anchored paraphrase regex patterns; vendor-aware whitelist extension (CE / superpowers idioms; 18 idioms) |
| v0.10.3 | Greek + Armenian confusables fold extension; conditional / speculative clause-prefix suppression; attribution / paired-quote / attributed-verb suppression (sentence-level historical-attribution skip) |
| v0.11.3 | Input-layer fix — `_read_last_assistant_message()` + `_content_to_text()` handling both legacy payload shape (test-lock) and real `transcript_path` JSONL shape (production-correct) |
| v0.11.4 | Plugin-root deployment path fix — `${CLAUDE_PLUGIN_ROOT}` env-var expansion so the script resolves in every project, not just athanor's source repo |
| v0.11.5 | Doc drift fix (status-table honesty re-alignment) |
| v0.11.6 | Sentinel body-hash binding (anti-replay against copied-sentinel forgery) |
| v0.11.7 | Scanner extension + B1 minimal whitelist additions |

### Re-entry prevention (sentinel mechanics)

The `verification-before-completion` skill is contractually required to
prefix every response with the v=2 nonce-bound sentinel
(`<!-- athanor:verification-emission v=2 nonce=<32-hex> -->`; see
`skills/verification-before-completion/SKILL.md` §"Emission Sentinel").
The hook script matches the sentinel anchored at response-start (line 1,
optional leading whitespace). Sentinels on line 2 or later do NOT count —
that's the brittleness trade-off documented in the skill.

### Per-project opt-out

Set `"hooks": {"profile": "off"}` in `athanor.json` to disable the gate.
The script exits 0 unconditionally; no claim detection runs. `"standard"`
(default) is the only other supported value; `lenient` / `strict` are
deferred to a future release.

### Detection scope

Material claims: edits applied / files created-removed-renamed / tests
passing-failing / lint-typecheck clean / builds succeeding / bug fixed /
requirements met / releases shipped / migrations completed / deployments
succeeded / agent task completed / verification output — English + Korean
phrase whitelist. Explicitly skipped (no exit 2): pure analysis, planning,
design, opinions, research Q&A, tool-output summaries that don't assert
work status.

### v0.11.3 input-layer fix (post-mortem)

For 5 release cycles (v0.7.8 → v0.11.2), the script's stdin parser assumed
the Stop event payload contained `last_assistant_message: <string>`. Claude
Code actually sends `transcript_path: <jsonl-path>` and the message lives
inside that file. Every Stop event silently fail-opened (`exit 0` with
stderr `"last_assistant_message missing or non-string"`). The 35+ existing
tests in `tests/test_regression_stop_hook_script.py` used the same incorrect
assumed payload shape, so they passed while production fail-opened.

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
in the status table is now honest.

`tests/test_regression_v011_3_stop_hook_input_layer.py` adds 25 mandatory +
1 xfail-tolerant tests against the real Claude Code payload shape. The
2026-05-18 dry-run spike documented in `docs/STATE.md` confirmed `exit 2`
behavior but did not validate the stdin parsing path (it tested the gate
by manually piping JSON, which masked the production gap).

### v0.11.4 plugin-root deployment fix (post-mortem)

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

### Related references

- **Skill source:** `skills/verification-before-completion/SKILL.md` (MIT, vendored)
- **Hook config:** `hooks/hooks.json` → Stop event, type `command` → `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/hooks/stop_verify_claims.py"` (plugin-root expansion since v0.11.4; bare relative path in v0.7.8 → v0.11.3 was the deployment-path bug)

---

## Spec-then-TDD Discipline (Splitter Internals)

Subtask 단위로 Spec-then-TDD를 자동 적용. 메커니즘 분기:

### Splitter classification (heuristic)

`/athanor:work` Task Splitter가 각 subtask를
`spec-then-tdd | test-aware | direct` 중 하나로 분류 (heuristic in
`skills/work/SKILL.md` Step 0.5 Rules block):

- source code modification + 새 동작/계약 → `spec-then-tdd`
- source code modification + 기존 동작 보존 (refactor) → `test-aware`
- prose-only (`.md`, `_doc`, CHANGELOG) → `direct`

### Branch semantics

**spec-then-tdd**: red-first 5단계 (test write → run RED → implement → run
GREEN → next criterion). Worker가 per-criterion `red_evidence` (command,
test_node_id, exit_code, output_tail) 보고 + `tests_modified` /
`test_paths_touched` / `full_suite_passed` 자가보고. Leader가 evidence
shape 검증 후 RED 안 갔으면 `test-aware`로 **pending-downgrade** —
Phase 3 게이트 (conjunction of three signals)를 다시 통과해야 success.

**test-aware**: 종료 게이트 — 세 조건의 conjunction:
1. `git diff --name-only` 결과에 `tests/**` path가 1개 이상 포함
   (test_*.py, conftest.py, fixtures/, snapshot 모두 허용)
2. worker가 `full_suite_passed: true`로 자가보고 (즉 `pytest tests/`를
   실행해 exit 0을 봤다고 주장)
3. `verification:` 자유형 prose가 (2)와 일관

셋 중 하나라도 빠지면 게이트 fail.

**direct**: 현재 athanor 동작 그대로 (doc/config-only edits).

### Evidence shape spec (spec-then-tdd worker contract)

Worker는 spec-then-tdd 분류 시 다음 필드를 결과 메시지에 자가보고해야 함:

- `red_evidence` (per criterion):
  - `command`: 실제 실행한 pytest 명령 (e.g., `pytest tests/test_foo.py::test_bar -x`)
  - `test_node_id`: 어떤 노드를 RED로 봤는지
  - `exit_code`: 정수 (RED 단계는 non-zero 기대; GREEN 단계는 0)
  - `output_tail`: pytest output 마지막 줄들 (RED일 경우 실패 라인을 포함해야 함)
- `tests_modified`: boolean — 이 subtask에서 test 파일을 만들거나 수정했는지
- `test_paths_touched`: 변경한 test 파일 경로 list
- `full_suite_passed`: boolean — `pytest tests/` 전체를 돌려 exit 0을 봤는지

Leader는 evidence의 **shape** (필드 존재 + 타입 일관성)만 검증. **truthfulness**
(worker가 실제로 그 명령을 돌렸는지)는 검증 불가 — `tests/test_…`에 새 노드가
git diff로 나타났는지 같은 간접 신호로 sanity-check만 가능.

### Pending-downgrade flow narrative

`/athanor:work` Step 2b 결과 핸들러가 worker 응답을 받고:

1. `execution_note: spec-then-tdd` 으로 분류되어 dispatch된 subtask가
   `red_evidence`를 빠뜨리거나 모든 criterion에서 `exit_code == 0`
   (즉 RED 단계 자체가 없음)으로 보고했다면 → `test-aware`로 다운그레이드.
2. 다운그레이드된 subtask는 `success` 표시 대신 **pending** 상태로 들어감.
3. Phase 3 (test-aware) 게이트 — 위의 conjunction-of-three —를 다시 통과해야
   `success`로 마감. 통과 못 하면 `failed` 또는 `requires-revision`.
4. Splitter heuristic 자체는 advisory; 사용자가 plan.md에서 `execution_note`
   를 수동 override 가능 (`<!-- athanor:subtasks:manual -->` 마커로 전체
   Splitter 우회도 가능).

### What it catches

새 동작 도입하는 subtask에서 "tests are afterthought" 패턴. RED 단계 자체를
건너뛰는 worker는 evidence shape 누락으로 잡힘.

### What it does NOT catch

- Splitter의 오분류 (false-positive: prose-only을 spec-then-tdd로 분류;
  false-negative: behavior 변경을 direct로 분류).
- Worker가 evidence를 fabricate (실제 RED를 본 적 없으면서 만들어낸
  command / exit_code 보고)하면 잡히지 않음. Leader는 evidence의 *shape*만
  검증하며 *진실성*은 검증 불가. adversarial forgery 차단 (runtime 강제,
  transcript-event introspection)은 v0.8.1+ 후보
  (verification-before-completion skill 확장).

### Per-project opt-out

본 메커니즘은 advisory이므로 별도 `athanor.json` 플래그 없음. plan.md를
수동 편집해 `execution_note: direct`로 강제하거나
`<!-- athanor:subtasks:manual -->` 마커로 Splitter를 우회 가능.

### Related references

- **Splitter prompt:** `skills/work/SKILL.md` Step 0.5 (Rules per subtask + Output Format)
- **Dispatch packet:** `skills/work/SKILL.md` Step 2a §"Execution Instructions"
  (3-branch conditional on execution_note)
- **Result handler:** `skills/work/SKILL.md` Step 2b §"v0.8.0 Spec-then-TDD result handler"
- **Critic rubric:** `skills/plan/SKILL.md` Step 4 §"v0.8.0 Critic Rubric"
- **Honesty arc:** v0.7.7~v0.7.9의 advisory/enforced 라벨 정직성 약속 유지.
  본 작업은 "advisory (planner-classified)" — runtime 강제 없음 명시.

### v0.10.0 scope clarification

Discipline applies to athanor-native `/athanor:work` only. Vendored
`/athanor:ce-work` and `/athanor:sp-test-driven-development` are OUTSIDE
the discipline — users opt in by explicit invocation; CE / superpowers
carry their own execution semantics. (Post-v0.12.0 the vendored work
skills are gone; native `/athanor:work` is the sole on-by-default
execution path.)

---

## Known Residuals

### Stop Hook — coverage gaps (post-v0.11.4)

v0.10.3 coverage achievements (all detected): paraphrase ("CI is green"),
Cyrillic / Greek / Armenian homoglyph, fullwidth, vendored CE / superpowers
idioms. v0.10.3 suppression achievements (false-positive avoidance):
conditional / speculative tense ("If all tests are green, merge"),
attributed historical quotes (`the v0.7.6 docs said "tests pass"`).

**Residual gaps (v0.11.0+, still not closed):**

- **LLM-class semantic similarity.** A worker rephrasing a material
  claim in genuinely novel prose ("the suite is now in working order")
  that no whitelist phrase or paraphrase regex catches. Lexical layer
  has reached diminishing returns; closing this requires LLM-classifier
  judgment.
- **Speculative tense without prefix marker.** "Tests should be green
  shortly" — no "if" / "when" / "once" prefix to anchor the conditional
  suppression rule, but the verb form is still non-assertive.
- **Multi-paragraph quote spans.** Attribution skip is sentence-level
  (paired-quote within single sentence). Multi-paragraph quote blocks
  with attribution in paragraph 1 and trigger phrase in paragraph 2
  still fire false-positive.
- **Cherokee + full-width-Latin confusables.** v0.10.2 / v0.10.3 added
  Cyrillic + Greek + Armenian folds; Cherokee and full-width-Latin
  scripts contain additional Latin lookalikes that bypass the current
  fold table.
- **Material claims outside the whitelist (deliberate false-negative).**
  The whitelist mirrors v0.7.7's well-tuned set; expanded deliberately,
  not greedily. New material-claim phrasings (e.g., new release-ceremony
  vocabulary) require an explicit whitelist update before they gate.

**Escape hatch for false positives.** Users encountering false positives
can set `"hooks": {"profile": "off"}` in `athanor.json` to disable the
gate entirely. The script exits 0 unconditionally with no claim detection.

### Spec-then-TDD — coverage gaps

- **Splitter misclassification.** False-positive (prose-only marked
  `spec-then-tdd` → forces unnecessary test scaffolding) and false-negative
  (behavior change marked `direct` → bypasses TDD discipline) both
  possible; heuristic uses path globs + skill-name keywords and cannot
  read true semantic intent.
- **Evidence fabrication.** Worker can synthesize `red_evidence` fields
  (command string, exit_code, output_tail) without actually running the
  command. Leader validates evidence **shape** but cannot validate
  **truthfulness**. Closing this requires transcript-event introspection
  (i.e., reading the tool-call log to verify the Bash invocation actually
  occurred) — originally floated as v0.8.1+ candidate work on the
  `verification-before-completion` skill; never landed and reclassified
  as open residual.
- **`full_suite_passed` self-report.** test-aware gate condition (2)
  depends on worker's truthful self-report of running `pytest tests/`.
  Same fabrication risk as `red_evidence`.

### Future candidate work (v0.11.8+)

- Semantic-similarity LLM classifier layer on top of the lexical
  whitelist (Stop hook).
- Speculative-tense detection without prefix-marker dependency
  (Stop hook).
- Multi-paragraph quote-span attribution skip (Stop hook).
- Cherokee + full-width-Latin homoglyph fold extension (Stop hook).
- Transcript-event introspection for evidence truthfulness verification
  (Spec-then-TDD).
- Adversarial-forgery runtime gate within `verification-before-completion`
  skill extension (Spec-then-TDD).

## PreToolUse Kernel Guard (Pattern Targets and Honest Scope)

Relocated from the CLAUDE.md §Defense Mechanisms status-table row at
v0.18.8 (the 1-line summary row remains canonical in CLAUDE.md; this is
the verbose internals). The guard is registered on the `hooks/hooks.json`
`PreToolUse` event (since v0.16.0; v0.18.0 routes it through the
single-outer-entry `pretool_dispatcher.py`, kernel guard running FIRST
and never over-ruled by the freeze layer). The hook genuinely fires and
exits 2 to block.

### Pattern targets (3 accident classes)

1. **Destructive shell** — `rm -rf /` and family, `git reset --hard`.
2. **Force-push to `main`/`master`** — the matcher uses a `(?![\w-])`
   right boundary so `main`/`master`-prefixed branches (e.g.
   `feature/main-update`) are allowed while exact `main`/`master`
   segments stay blocked.
3. **Credential file access** — `.env`, private keys. `.env.example` /
   `.env.test` are allowed.

`athanor.json` `hooks.profile: "off"` opt-out disables the guard (exits 0
even for `rm -rf /`).

### Honest scope (what it is NOT)

This is a **textual regex guard, NOT a command parser or security
boundary**. It catches obvious literal forms but is bypassable by
obfuscation: command substitution `$(...)`, variable indirection,
base64/`eval`, reordered flags. Treat it as a guardrail against
fat-finger accidents, not containment against an adversary.
