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
LSP (Serena):    ✓ connected      (or ✗ not found)
Codex:           ✓ available      (or ○ not found — optional)
Agent Teams:     ✓ enabled        (or ✗ disabled)
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
