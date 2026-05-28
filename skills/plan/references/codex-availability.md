# Codex Availability State Machine (Step 0 Detail)

This reference holds the full Codex availability matrix that resolves
`codex_available` (boolean) AND `review_strategy` (one of `codex` /
`claude-self-review` / `none`). Both variables are consumed by dispatch
sites in Steps 2, 3, and 4 of `skills/plan/SKILL.md`.

The SKILL.md router carries a brief pointer to this file; the full
state machine lives here so the router stays under the 300-line cap.

## Resolve State

> **Exception:** The Leader MAY run Bash commands to read `athanor.json`
> and probe Codex CLI availability.

```bash
# Read config (with graceful jq-absence fallback)
if command -v jq >/dev/null 2>&1; then
  CODEX_CONFIG_ENABLED=$(jq -r '.codex.enabled // true' athanor.json 2>/dev/null)
  CODEX_FALLBACK=$(jq -r '.codex.fallback // "self-critic"' athanor.json 2>/dev/null)
  CODEX_TIMEOUT_MS=$(jq -r '.codex.timeoutMs // 300000' athanor.json 2>/dev/null)
  CODEX_TIMEOUT_S=$((CODEX_TIMEOUT_MS / 1000))
  [ "$CODEX_TIMEOUT_S" -lt 1 ] && CODEX_TIMEOUT_S=300
  [ "$CODEX_TIMEOUT_S" -gt 600 ] && CODEX_TIMEOUT_S=600
else
  # jq not installed — assume defaults from shipped config
  CODEX_CONFIG_ENABLED=true
  CODEX_FALLBACK=self-critic
  CODEX_TIMEOUT_MS=300000
  CODEX_TIMEOUT_S=300
fi

# Probe CLI
if codex --version </dev/null >/dev/null 2>&1; then CODEX_CLI=true; else CODEX_CLI=false; fi

# State machine
if [ "$CODEX_CONFIG_ENABLED" = "true" ] && [ "$CODEX_CLI" = "true" ]; then
  codex_available=true
  review_strategy=codex
elif [ "$CODEX_CONFIG_ENABLED" = "false" ]; then
  codex_available=false
  case "$CODEX_FALLBACK" in
    self-critic) review_strategy=claude-self-review ;;
    skip)        review_strategy=none ;;
    fail)        echo "ERROR: codex.enabled=false but codex.fallback=fail — aborting" >&2; exit 1 ;;
  esac
else
  # CLI absent, config true — same fallback matrix
  codex_available=false
  case "$CODEX_FALLBACK" in
    self-critic) review_strategy=claude-self-review ;;
    skip)        review_strategy=none ;;
    fail)        echo "ERROR: codex --version failed and codex.fallback=fail — aborting" >&2; exit 1 ;;
  esac
fi
```

## Announcement

Announce exactly one of the following based on resolved state:

- `Codex available` (when `codex_available=true`)
- `Codex disabled by config (review_strategy=<value>)` (when `CODEX_CONFIG_ENABLED=false`)
- `Codex CLI not installed (review_strategy=<value>)` (when config true but CLI absent)

## Variable contract

`codex_available` and `review_strategy` MUST be threaded through to:

- Step 2 dispatch decision (Planner B path)
- Step 3 dispatch decision (Reviewer B path)
- Step 4 dispatch decision (Critic variant selection)

The Gate Checkpoint announcements at each step (see SKILL.md) re-print
the resolved variables for transcript traceability.
