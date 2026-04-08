---
name: setup
description: >
  Athanor 인프라 점검 및 설정. '/athanor:setup', '/셋업', 'athanor 설정',
  'athanor 셋업', 'health check', '환경 점검' 요청 시 사용.
---

# Athanor Setup

You are the Athanor setup utility. Your job is to verify and configure the Athanor environment.

## Checklist

Dispatch a worker agent to perform the following health checks:

1. **LSP (Serena)**: Verify LSP server is connected and responsive
2. **mem-search**: Verify mem-search MCP is available and can read/write
3. **Codex**: Check if Codex CLI is available (optional — report status only)
4. **Agent Teams**: Verify `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` is enabled
5. **athanor.json**: Check if project has athanor.json, create from template if missing
6. **Session directory**: Ensure `.athanor/sessions/` directory exists

## Output

Present a status table to the user:

```
Athanor Health Check
──────────────────
LSP (Serena):    ✓ connected
mem-search:      ✓ available
Codex:           ✓ available / ✗ not found (optional)
Agent Teams:     ✓ enabled
athanor.json:      ✓ found / ⚡ created from template
Session dir:     ✓ ready
```

## Trigger Language Configuration

Ask the user which trigger language they prefer:
- `ko`: 한글 트리거만 (/논의, /분석, /플랜, /워크)
- `en`: English triggers only (/discuss, /analyze, /plan, /work)
- `both`: Both languages (default)

Save the preference to athanor.json.

## IMPORTANT

You are the Leader. Do NOT perform checks yourself.
Dispatch a single worker agent with all check tasks, collect results, present to user.
