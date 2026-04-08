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

**Worker dispatch prompt:**

```
You are an Athanor setup worker. Perform these health checks and report results.

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
  "language": "ko",
  "codex": { "enabled": true, "fallback": "self-critic" },
  "work": {
    "defaultMode": "solo",
    "ralphLoop": { "maxRetries": 5 },
    "circuitBreaker": { "consecutiveFailures": 3, "action": "ask_user" }
  },
  "team": { "waveSize": 3, "discoveryRelay": true },
  "memory": { "decayDays": 7, "promotionThreshold": 5, "maxAgeDays": 30 },
  "models": {
    "analyst": "sonnet", "planner": "opus", "critic": "opus",
    "executor": "sonnet", "cleaner": "haiku", "learner": "sonnet"
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
ATHANOR_HEALTH_CHECK_RESULTS
session_dir: [EXISTS|CREATED]
config: [EXISTS|CREATED]
memsearch: [AVAILABLE|UNAVAILABLE] [tool_name_if_available]
lsp: [AVAILABLE|UNAVAILABLE] [tool_name_if_available]
codex: [AVAILABLE|UNAVAILABLE]
agent_teams: [ENABLED|DISABLED]
notes: [any additional observations]
END_RESULTS
```
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
