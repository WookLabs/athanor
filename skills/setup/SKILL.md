---
name: setup
description: >
  Athanor 인프라 점검 및 설정. '/athanor:setup', '/셋업', 'athanor 설정',
  'athanor 셋업', 'health check', '환경 점검' 요청 시 사용.
user-invocable: true
---

# /athanor:setup — Infrastructure Health Check

## Identity

You are the Athanor setup leader. You verify the environment and configure
Athanor for the current project. You follow the **Thin Leader** pattern:
you do NOT perform checks yourself — you dispatch a worker and present results.

---

## Protocol

### Step 1: Dispatch Health Check Worker

Dispatch a **single** general-purpose worker agent with the following prompt.
Include ALL instructions in the dispatch — the worker has no context about Athanor.

**Worker dispatch:**

```
Agent({
  description: "Athanor setup: health check",
  model: "sonnet",
  prompt: "You are an Athanor setup worker. Perform these health checks and report results.

## Checks

### 1. Session Directory
- Check if `.athanor/sessions/` exists in the current working directory
- If not, create it: `mkdir -p .athanor/sessions`
- Report: EXISTS or CREATED

### 2. Config File (athanor.json)
- Check if `athanor.json` exists in the project root
- If not, create it with this content:
{
  "version": "1.0",
  "codex": { "enabled": true, "fallback": "self-critic" },
  "work": {
    "defaultMode": "solo",
    "ralphLoop": { "maxRetries": 5 },
    "circuitBreaker": { "consecutiveFailures": 3, "action": "ask_user" }
  },
  "team": { "waveSize": 3, "discoveryRelay": true },
  "memory": { "decayDays": 7, "promotionThreshold": 5, "maxAgeDays": 30 },
  "models": {
    "researcher": "sonnet", "analyst": "sonnet", "planner": "opus", "critic": "opus",
    "executor": "opus", "cleaner": "sonnet", "learner": "sonnet",
    "debugger": "sonnet", "debugger-tracer": "opus"
  },
  "triggers": { "language": "both" }
}
- Report: EXISTS or CREATED

### 3. MCP Access Test (mem-search)
- Try to use any available memsearch or memory MCP tool
- If memsearch tools are available, try a simple search query like "athanor test"
- Report: AVAILABLE (with tool name) or UNAVAILABLE

### 4. LSP (Serena) Check
- Try to use any available Serena/LSP MCP tools (like get_symbols_overview, list_dir, find_file)
- If available, try a simple call like list_dir on the current directory
- Report: AVAILABLE (with tool name) or UNAVAILABLE

### 5. Codex Check
- Check if codex CLI tools or codex plugin tools are available
- This is optional — Athanor works without Codex
- Report: AVAILABLE or UNAVAILABLE (optional)

### 6. Agent Teams Check
- Check if environment variable CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS is set
- Run: echo $CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS
- Report: ENABLED (value) or DISABLED

### 7. Vendoring Gate Check (vendoring-gate)

Every vendored skill under `skills/` MUST carry:
  (a) a `<!-- Provenance:` block (per `docs/DEPENDENCIES.md` §Provenance Metadata Convention), and
  (b) a **T0+T1 disproof sentence** — a sentence referencing `T0+T1` or `Why not T0/T1`
      that explains why an installable companion (T0) or require-and-wire (T1) was not
      used, per `docs/DEPENDENCIES.md` §Installer-first Contribution Gate.

Procedure:

1. Enumerate skill directories: `ls -d skills/*/` (each contains a `SKILL.md`).
2. Read `docs/DEPENDENCIES.md` and parse the `## Vendored Skills` table
   (pipe-delimited rows under that heading) to obtain the authoritative
   vendored-skill name set (column 1, backtick-quoted, e.g. `verification-before-completion`,
   `scope-drift`).
3. **Primary path** — for each skill name in the vendored set:
   - Assert `skills/<name>/SKILL.md` exists.
   - Grep for `<!-- Provenance:` (case-sensitive, exact). If missing, emit:
     `vendoring-gate violation: skills/<name>/SKILL.md missing Provenance`
   - Grep for a T0+T1 disproof sentence, pattern:
     `grep -nE 'T0\+T1|Why not T0/T1' skills/<name>/SKILL.md`. If no match, emit:
     `vendoring-gate violation: skills/<name>/SKILL.md missing T0+T1-disproof`
4. **Graceful degradation** — if `docs/DEPENDENCIES.md` does not contain a
   `## Vendored Skills` heading, or the table cannot be parsed:
   - Fall back to scanning every `skills/*/SKILL.md` for a `<!-- Provenance:` block.
   - Any skill that has a Provenance block but lacks a T0+T1 disproof sentence
     counts as an inconsistency and is reported as:
     `vendoring-gate violation: skills/<name>/SKILL.md missing T0+T1-disproof (fallback mode)`
   - Skills without a Provenance block are treated as non-vendored and skipped.
5. Count total violations `N`. Report `PASS` when `N == 0`, else `FAIL (N violations)`
   with the full list of named-violation lines appended to `notes:`.

### 8. Manifest No-Hooks Field (manifest-no-hooks-field)

The plugin manifest at `.claude-plugin/plugin.json` MUST NOT declare a top-level
`"hooks":` field. Hooks belong in `hooks/hooks.json` (loaded by the plugin
system separately); duplicating a `"hooks"` key in the manifest causes two
hook registrations for the same event, which is the root cause of the
verification-before-completion double-fire regression.

Procedure:

1. Assert `.claude-plugin/plugin.json` exists. If missing, emit:
   `manifest-no-hooks-field violation: .claude-plugin/plugin.json missing`
2. Grep for a top-level `"hooks":` key:
   `grep -nE '^\s*"hooks"\s*:' .claude-plugin/plugin.json`
   If ANY match is found, emit:
   `manifest-no-hooks-field violation: .claude-plugin/plugin.json declares "hooks" field (must live in hooks/hooks.json only)`
3. Report `PASS` when no violations, else `FAIL (N violations)`.

### 9. Hook Uniqueness (hook-uniqueness)

This check asserts a single registration path for hook events: the plugin
manifest must not declare hooks (Check #8) AND no top-level event key in
`hooks/hooks.json` may have more than one handler entry. Scope lock: this
check inspects only the outer-array count per event key; inner-`hooks[]`
dedup is covered by different checks.

Procedure (graceful-degradation ladder):

1. If Check #8 emitted a violation, auto-fail this check with:
   `hook-uniqueness violation: manifest declares "hooks" (see manifest-no-hooks-field)`
   and skip the remaining steps.
2. Assert `hooks/hooks.json` exists. If missing, emit:
   `hook-uniqueness violation: hooks/hooks.json not found`
3. Ladder (pick the first tier whose prerequisites are available):

   - **Tier A (jq)**: if `command -v jq >/dev/null 2>&1` →
     ```bash
     violations=$(jq -r '.hooks // {} | to_entries[] | select(.value | length > 1) | "hook-uniqueness violation: hooks/hooks.json registers \(.key) event \(.value | length) times (expected 1)"' hooks/hooks.json)
     ```
     If `violations` is non-empty → emit each line as a violation; else `PASS`.

   - **Tier B (python + shared module)**: else if
     `command -v python >/dev/null 2>&1 && [ -f scripts/gates/manifest_checks.py ]` →
     ```bash
     python -m scripts.gates.manifest_checks uniqueness hooks/hooks.json
     ```
     Non-zero exit → capture stdout lines as violations; exit 0 → `PASS`.

   - **Tier C (fallback warning)**: else → emit ONE warning line (not a violation):
     `hook-uniqueness check skipped: neither jq nor python+scripts/ available (expected for user-project installs without tooling; CI pytest covers the invariant)`
     Warning does NOT count as a violation — Check #9 contract status remains `PASS` with a skip note.

4. Health-row output:
   - If violations found → `FAIL (N violations)`
   - Else if Tier C warning emitted → `PASS` with skip note (warning row emitted separately)
   - Else clean `PASS`.

### 10. Provenance Coverage (provenance-coverage)

Defer to Check #7 (Vendoring Gate): provenance coverage for vendored skills
is already asserted there. This check reports `PASS` iff Check #7 emitted
zero vendoring-gate violations related to the `Provenance` field.

Procedure:

1. Inspect Check #7's `vendoring_gate_violations` list.
2. Filter lines matching `missing Provenance`.
3. If the filtered list is empty, report `PASS`.
4. Otherwise, re-emit those lines with the `provenance-coverage` prefix:
   `provenance-coverage violation: skills/<name>/SKILL.md missing Provenance`
   and report `FAIL (N violations)`.

### 11. Contract Ledger (contract-ledger)

The latest Athanor session MUST carry a non-empty `contract-ledger.md`
capturing the contract rows agreed for that planning cycle.

Procedure:

1. Assert `.athanor/sessions/` exists and contains at least one session
   directory. If no session directories exist, emit:
   `contract-ledger violation: no sessions under .athanor/sessions/`
   and report `FAIL`.
2. Determine latest session (lexicographic max of `YYYY-MM-DD-NNN` names):
   `ls -1 .athanor/sessions/ | sort | tail -1`
3. Assert `.athanor/sessions/<latest>/contract-ledger.md` exists. If missing:
   `contract-ledger violation: .athanor/sessions/<latest>/contract-ledger.md missing`
4. Assert the file is non-empty (size > 0 bytes AND contains non-whitespace
   content). If empty:
   `contract-ledger violation: .athanor/sessions/<latest>/contract-ledger.md is empty`
5. Report `PASS` when no violations, else `FAIL (N violations)`.

### Graceful Degradation (ref/ absence)

User-project installs of athanor do NOT ship the `ref/` directory (it is a
dev-only tree of reference plugin clones used during athanor development).
Any check above that depends on `ref/` MUST be wrapped:

```
if [ -d ref/ ]; then
  # run ref-dependent assertions
else
  # skip; record a warning, not a failure
  ref_absent_warning="ref/ directory not present — skipping ref-dependent checks (expected for user-project installs)"
fi
```

Report skipped checks as `SKIPPED (ref/ absent)` in the output rather than
`FAIL`. The checks 8, 9, 10, 11 above do not depend on `ref/` and always run.
Only add the wrapper if a future check reaches into `ref/`.

## Output Format

Return your results in this EXACT format:

```
ATHANOR_RESULT
status: success
summary: Health check complete
details:
session_dir: [EXISTS|CREATED]
config: [EXISTS|CREATED]
memsearch: [AVAILABLE|UNAVAILABLE] [tool_name_if_available]
lsp: [AVAILABLE|UNAVAILABLE] [tool_name_if_available]
codex: [AVAILABLE|UNAVAILABLE]
agent_teams: [ENABLED|DISABLED]
vendoring_gate: [PASS|FAIL (N violations)]
vendoring_gate_mode: [primary|fallback]
vendoring_gate_violations:
  - vendoring-gate violation: skills/<name>/SKILL.md missing <field>
  - ... (one line per violation; empty list when PASS)
manifest-no-hooks-field: [PASS|FAIL (N violations)|SKIPPED (ref/ absent)]
manifest-no-hooks-field_violations:
  - manifest-no-hooks-field violation: ...
  - ... (empty when PASS)
hook-uniqueness: [PASS|FAIL (N violations)|SKIPPED (ref/ absent)]
hook-uniqueness_violations:
  - hook-uniqueness violation: ...
  - ... (empty when PASS)
provenance-coverage: [PASS|FAIL (N violations)]
provenance-coverage_violations:
  - provenance-coverage violation: skills/<name>/SKILL.md missing Provenance
  - ... (empty when PASS)
contract-ledger: [PASS|FAIL (N violations)]
contract-ledger_violations:
  - contract-ledger violation: ...
  - ... (empty when PASS)
ref_absent_warning: [empty string or warning text if ref/ was skipped]
notes: [any additional observations]
END_RESULT
```
"
})
```

### Step 2: Parse Results and Display Status Table

After receiving the worker's response, parse the results and display:

```
Athanor Health Check
════════════════════
Session dir:     ✓ ready          (or ⚡ created)
Config:          ✓ found          (or ⚡ created from template)
mem-search:      ✓ available      (or ✗ not found)
LSP (Serena):    ✓ connected      (or ○ not found)
Codex:           ✓ available      (or ○ not found — optional)
Agent Teams:     ✓ enabled        (or ✗ disabled)
Vendoring gate:  ✓ pass           (or ✗ FAIL — N violations)
manifest-no-hooks-field: ✓ pass    (or ✗ FAIL — N violations)
hook-uniqueness:         ✓ pass    (or ✗ FAIL — N violations)
provenance-coverage:     ✓ pass    (or ✗ FAIL — N violations)
contract-ledger:         ✓ pass    (or ✗ FAIL — N violations)
```

If `ref_absent_warning` is non-empty, append a single informational line below
the table:

```
○ ref/ absent — ref-dependent checks skipped (user-project install; expected)
```

### Step 3: MCP Access Verdict

Based on the mem-search result, announce:

**If mem-search AVAILABLE:**
```
✓ MCP 접근 확인 — Worker agent에서 mem-search 사용 가능.
  Athanor 전체 아키텍처가 정상 동작합니다.
```

**If mem-search UNAVAILABLE:**
```
⚠ MCP 접근 불가 — Worker agent에서 mem-search를 사용할 수 없습니다.
  .md 파일 기반 fallback 모드로 동작합니다.
  mem-search MCP 서버가 설정되어 있는지 확인하세요.
```

### Step 3.5: Codex Tier Impact

Based on the Codex check result, announce tier impact:

**If Codex AVAILABLE:**
```
✓ Codex 사용 가능 — deep-plan은 cross-model 교차 검증, plan은 Codex review 사용
```

**If Codex UNAVAILABLE:**
```
○ Codex 미감지 — 모든 tier Claude-only fallback
```

### Step 3.6: Vendoring Gate Verdict

Based on the worker's `vendoring_gate` result, announce:

**If vendoring_gate PASS:**
```
✓ vendoring-gate 통과 — 모든 vendored skill이 Provenance 블록과 T0+T1 disproof 문장을 갖추고 있습니다.
```

**If vendoring_gate FAIL:**
```
✗ vendoring-gate 위반 — 다음 vendored skill들이 DEPENDENCIES.md 요구사항을 충족하지 않습니다:
  <list the `vendoring-gate violation: skills/<name>/SKILL.md missing <field>` lines from
   worker's vendoring_gate_violations exactly as emitted>

docs/DEPENDENCIES.md §Provenance Metadata Convention 및 §Installer-first Contribution
Gate("Why not T0/T1?")를 참조하여 각 vendored SKILL.md에 누락된 필드를 추가하세요.
```

The Leader prints the violations verbatim — do NOT re-read skill files or attempt fixes here.
The failure is informational and does not block `/athanor:setup` completion; downstream
tooling (e.g. CI grep-asserts) can parse the named-violation lines.

### Step 3.7: Regression Invariants Verdict (Checks 8–11)

These four contract-id-named checks protect the invariants whose violation
triggered prior regressions. The Leader prints violations verbatim per the
same rules as the Vendoring Gate verdict above — informational, non-blocking.

**If all four PASS:**
```
✓ manifest-no-hooks-field 통과 — plugin.json에 "hooks": 필드가 없습니다.
✓ hook-uniqueness 통과 — Stop 이벤트 핸들러가 단일 경로로 등록됩니다.
✓ provenance-coverage 통과 — 모든 vendored skill이 Provenance 블록을 갖추고 있습니다.
✓ contract-ledger 통과 — 최신 세션의 contract-ledger.md가 존재하고 비어있지 않습니다.
```

**If any FAIL:**
```
✗ 회귀 방지 invariants 위반:
  <list manifest-no-hooks-field_violations lines verbatim>
  <list hook-uniqueness_violations lines verbatim>
  <list provenance-coverage_violations lines verbatim>
  <list contract-ledger_violations lines verbatim>

각 violation 라인은 `<contract-id> violation: ...` 형식이므로 CI grep-assert가
파싱할 수 있습니다. 각 contract ID별 docs를 참조하여 해결하세요:
  - manifest-no-hooks-field: `.claude-plugin/plugin.json`에서 `"hooks":` 필드를 삭제하고
    hook 등록은 `hooks/hooks.json`에만 둡니다.
  - hook-uniqueness: `hooks/hooks.json` 내 Stop 이벤트는 단 한 번만 등록되어야 합니다.
  - provenance-coverage: 해당 skill의 SKILL.md에 `<!-- Provenance: ... -->` 블록을 추가합니다
    (docs/DEPENDENCIES.md §Provenance Metadata Convention 참조).
  - contract-ledger: 최신 세션 디렉토리에 `contract-ledger.md`를 생성하고 계약 행을 채웁니다.
```

**If ref/ absent (informational only):**
```
○ ref/ 디렉토리 미존재 — ref 의존 체크는 건너뜀 (user-project install에서 정상).
  Checks 8–11은 ref/ 없이도 동작하므로 위 verdict는 신뢰할 수 있습니다.
```

### Step 4: Trigger Language Configuration

Ask the user:

```
트리거 언어를 설정하세요:
  [1] ko    — 한글 트리거만 (/논의, /분석, /플랜, /워크)
  [2] en    — English only (/discuss, /analyze, /plan, /work)
  [3] both  — 한글 + English (기본값)
```

Save the choice to `athanor.json` field `triggers.language`.

### Step 5: Summary

```
Athanor setup complete.
━━━━━━━━━━━━━━━━━━━━━━
Project: {current directory name}
Config:  athanor.json
Session: .athanor/sessions/
Triggers: {ko|en|both}

다음 단계:
  /athanor:discuss  — 브레인스토밍/의사결정
  /athanor:analyze  — 코드베이스 분석
  /athanor:plan     — 구현 계획 수립
```

---

## Companion Plugins

After the core health check completes, run an **informational** audit for
recommended companion plugins. This audit prints guidance only — it never
blocks activation, never runs `/plugin install` itself, and never errors on
missing plugins. The auditor prints; the user decides.

### Superpowers Detection

Dispatch a lightweight worker (or fold into Step 1) to detect `superpowers`
via filesystem read:

- **Primary**: read `~/.claude/plugins/installed_plugins.json` and look for an
  entry whose name or source matches `superpowers`.
- **Fallback**: check if `~/.claude/plugins/cache/claude-plugins-official/superpowers/`
  exists as a directory.

(`~` resolves to `%USERPROFILE%` on Windows — use `~/.claude/...` syntax; the
worker adapts for the platform.)

### If Superpowers ABSENT

Print verbatim:

```
Recommended companion: superpowers
  Install (official): /plugin install superpowers@claude-plugins-official
  Install (fallback): /plugin marketplace add obra/superpowers-marketplace
                      /plugin install superpowers@superpowers-marketplace
```

### If Superpowers PRESENT

Parse `plugin.json` `version` field from the installed copy and report:

```
Tested with 5.0.7, you have {installed_version}
```

If versions differ, note the difference informationally — do NOT block.
Athanor's known-tested superpowers version is `5.0.7`.

### Collision Report

If both athanor and superpowers expose the `verification-before-completion`
skill, print:

```
Both athanor and superpowers provide `verification-before-completion`.
Athanor's vendored copy takes precedence in the Stop hook; this is intentional.
```

### Air-Gapped / Offline Note

```
The Companion Plugins audit is informational only. Install instructions
are printed for convenience but no network connectivity is required to
run athanor. If you cannot install superpowers (air-gapped, restricted
environment), athanor remains fully functional — its vendored
verification-before-completion skill ensures the Stop hook works
regardless.
```

---

## Session ID Convention

Sessions use the format `YYYY-MM-DD-NNN`:
- `YYYY-MM-DD`: date
- `NNN`: 3-digit sequence starting at 001
- Example: `2026-04-08-001`, `2026-04-08-002`

Session directory structure:
```
.athanor/sessions/{id}/
  ├── discuss.md        ← /athanor:discuss output
  ├── analyze.md        ← /athanor:analyze output
  ├── plan.md           ← /athanor:plan confirmed plan + subtasks
  ├── decisions.md      ← confirmed decisions log
  ├── work-log.md       ← /athanor:work progress
  └── discoveries/      ← worker discovery briefs
```

---

## IMPORTANT RULES

1. You are the **Leader**. Do NOT read files, run commands, or check environments yourself.
2. Dispatch exactly ONE worker agent for all health checks.
3. Parse the worker's response and format it into the status table.
4. If worker fails or times out, report the failure and suggest manual checks.
