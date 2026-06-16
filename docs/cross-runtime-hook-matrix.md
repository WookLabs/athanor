# Cross-Runtime Hook Matrix

Date: 2026-06-17
Branch: `feat/hook-payload-replay`
Purpose: freeze the P3 boundary between Athanor's hook catalog and the current
Claude Code / Codex hook surfaces before adding any generator or installer.

## Sources

Primary sources reviewed for this matrix:

- Claude Code hooks reference: https://code.claude.com/docs/en/hooks
- Claude Code plugins reference: https://code.claude.com/docs/en/plugins-reference
- Codex hooks reference: https://developers.openai.com/codex/hooks
- Codex implementation reference: https://github.com/openai/codex

Local refs used as comparative architecture references:

- `ref/alexei-led-cc-thingz`
- `ref/anthropics-claude-code`
- `ref/anthropics-claude-plugins-official`
- `ref/anthropics-knowledge-work-plugins`
- `ref/ElliotJLT-hooksmith`
- `ref/obra-superpowers`

## Read

Athanor should keep Stop, PreToolUse, and PostToolUse as the only enabled
default hooks until additional lifecycle events have live-redacted fixtures and
replayable handlers. Claude Code has the broadest documented event surface.
Codex now has enough lifecycle hook parity and a stronger trust/managed-hook
model to justify a cross-runtime matrix before any generator.

The matrix is documentation plus regression tests only. It is not a generator,
installer, or settings writer.

## Athanor Catalog Mapping

| Event | Athanor default | Claude Code | Codex | Next action |
| --- | --- | --- | --- | --- |
| FileChanged | capture-only | not documented | not documented | Collect live-redacted fixture; no settings mutation. |
| PermissionRequest | capture-only | supported | supported | Collect live-redacted fixture; no settings mutation. |
| PostToolUse | enabled | supported | supported | Keep replay-gated; no settings mutation. |
| PostToolUseFailure | capture-only | supported | not documented | Collect live-redacted fixture; no settings mutation. |
| PreCompact | capture-only | supported | supported | Collect live-redacted fixture; no settings mutation. |
| PreToolUse | enabled | supported | supported | Keep replay-gated; safety corpus remains disabled/observe unless explicitly enabled; no settings mutation. |
| SessionStart | capture-only | supported | supported | Collect live-redacted fixture; no settings mutation. |
| Stop | enabled | supported | supported | Keep replay-gated; no settings mutation. |
| SubagentStop | capture-only | supported | supported | Collect live-redacted fixture; no settings mutation. |
| UserPromptSubmit | capture-only | supported | supported | Promote spike to live-redacted fixture before replay support; no settings mutation. |

## Event Support Matrix

| Event | Claude Code status | Codex status | Athanor policy |
| --- | --- | --- | --- |
| UserPromptSubmit | documented hook event | documented hook event | capture-only spike |
| PreToolUse | documented hook event | documented hook event | enabled runtime guard |
| PermissionRequest | documented approval surface | documented hook event | capture-only candidate |
| PostToolUse | documented hook event | documented hook event | enabled evidence sniffer |
| PostToolUseFailure | documented hook event | not documented in Codex hook page | capture-only candidate |
| PostToolBatch | documented hook event | not documented in Codex hook page | not cataloged |
| PermissionDenied | documented hook event | not documented in Codex hook page | not cataloged |
| Notification | documented hook event | not documented in Codex hook page | not cataloged |
| SubagentStart | documented hook event | documented hook event | not cataloged |
| SubagentStop | documented hook event | documented hook event | capture-only candidate |
| Stop | documented hook event | documented hook event | enabled claim verifier |
| PreCompact | documented hook event | documented hook event | capture-only candidate |
| PostCompact | not documented in Claude Code hook page | documented hook event | not cataloged |
| SessionStart | documented hook event | documented hook event | capture-only candidate |
| ConfigChange | documented hook event | not documented in Codex hook page | not cataloged |

## Trust And Install Policy Matrix

| Runtime | Hook trust model | Installer boundary |
| --- | --- | --- |
| Claude Code | plugin validation through `claude plugin validate` or `/plugin validate`; plugin hooks live at plugin-root `hooks/hooks.json` or manifest-declared hook config. | Marketplace/plugin install may expose hooks, but Athanor still requires catalog evidence before recommending runtime enablement. |
| Codex | trust before execution for non-managed hooks; managed hooks are trusted by policy and can be forced through requirements; plugin-bundled hooks still require review. | Respect project trust and managed hooks; do not bypass the hook browser or managed policy. |
| Athanor | catalog-first evidence policy; enabled hooks must be replay-gated or live-redacted; capture-only hooks are evidence collection only. | dry-run first; no generator writes settings until the matrix, catalog, and live fixtures prove the change. |

## Generator Boundary

P3 does not generate manifests, and P4 only adds a read-only install dry-run
planner. `scripts/gates/hook_install_dry_run.py` can preview settings actions,
but it does not write settings, manifests, trust state, or hook files. The
generator is deferred until:

1. every Athanor catalog event has an explicit Claude Code and Codex support
   status;
2. unsupported or undocumented events have a no-op or capture-only policy;
3. plugin-local hook support is versioned per runtime;
4. trust and managed-hook behavior are represented before any installer UX;
5. dry-run output can show exactly what would change without mutating user
   settings.

Until those conditions are satisfied, Athanor should keep `hooks/hooks.json` as
the only runtime registration surface and keep `hooks/catalog.json` as metadata.
