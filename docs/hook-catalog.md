# Hook Catalog

`hooks/catalog.json` is the source of truth for Athanor's runtime hook surface
and near-term hook expansion candidates. It does not install hooks or mutate
Claude settings. Runtime registration still comes only from `hooks/hooks.json`.

The catalog exists so future hook expansion starts from explicit policy,
evidence, risk, and performance metadata instead of README-only intent.

Cross-runtime support and generator boundaries are tracked in
[docs/cross-runtime-hook-matrix.md](cross-runtime-hook-matrix.md).

Installer previews are read-only. Use
`python scripts/gates/hook_install_dry_run.py --json` to compare the catalog,
`hooks/hooks.json`, and an optional Claude settings file. The planner reports
what would be added, blocked, or conflicted, includes hook fingerprint and
trust-state fields in a schema v2 report, and always emits `writes: []`.

## Runtime Defaults

- `enabled`: registered in `hooks/hooks.json` now.
- `capture-only`: has a manual capture harness or spike path, but is not
  registered by Athanor.
- `disabled`: documented candidate with no runtime handler.

## Evidence Levels

- `none`: no Athanor payload fixture or handler exists.
- `synthetic`: tested or documented locally, but not live-proven.
- `live-redacted`: captured from live Claude Code and manually reduced.
- `replay-gated`: live or synthetic fixtures replay through Athanor gate code.

## Current Entries

| ID | Event | Default | Policy | Evidence | Budget | Notes |
| --- | --- | --- | --- | --- | ---: | --- |
| `stop-verify-claims` | Stop | enabled | block | replay-gated | 500 ms | Verifies completion claims at turn end. |
| `pretool-dispatcher` | PreToolUse | enabled | block | replay-gated | 500 ms | Routes tool calls through kernel and freeze guards. |
| `pretool-safety-pattern-corpus` | PreToolUse | disabled | observe | synthetic | 100 ms | Opt-in diagnostics for risky shell and secret-shaped write patterns. |
| `posttool-evidence-sniffer` | PostToolUse | enabled | warn | replay-gated | 500 ms | Records evidence and diagnostics without changing default policy. |
| `generic-payload-capture` | FileChanged | capture-only | observe | synthetic | 250 ms | Manual capture path for future FileChanged evidence. |
| `userpromptsubmit-spike` | UserPromptSubmit | capture-only | observe | synthetic | 250 ms | Manual prompt payload spike; not a runtime policy hook. |
| `sessionstart-context-candidate` | SessionStart | capture-only | observe | synthetic | 100 ms | Capture-first context injection candidate after live evidence. |
| `precompact-summary-candidate` | PreCompact | capture-only | observe | synthetic | 100 ms | Capture-first compaction summary candidate after payload evidence. |
| `permissionrequest-capture-candidate` | PermissionRequest | capture-only | observe | synthetic | 100 ms | Capture-first approval-surface candidate before policy hooks. |
| `posttoolusefailure-capture-candidate` | PostToolUseFailure | capture-only | observe | synthetic | 100 ms | Capture-first failure diagnostics candidate before enforcement. |
| `subagentstop-capture-candidate` | SubagentStop | capture-only | observe | synthetic | 100 ms | Capture-first worker completion metadata candidate before runtime policy. |

## Promotion Rules

An entry can move from `disabled` to `capture-only` only after a capture harness
exists and its command can be reviewed without installing it by default.

An entry can move from `capture-only` to `enabled` only after:

1. live-redacted payload evidence exists where the event depends on Claude Code
   runtime shape;
2. the handler has targeted tests;
3. replay or an equivalent gate proves the committed fixture still exercises
   the handler;
4. the hook declares a performance budget and skip/fail-open behavior;
5. `hooks/hooks.json`, `hooks/catalog.json`, and this document are updated in
   the same change.

## Performance Policy

Default hooks must stay narrow. The current target is a sub-500 ms budget per
registered hook invocation on typical local repositories. Heavier hooks, such
as focused test runners or broad linting, must start as opt-in catalog entries
with explicit skip paths before any runtime registration.

`performance_budget_ms` is executable metadata, not a documentation-only
promise. `scripts/gates/check_hook_performance_budget.py` reads
`hooks/catalog.json`, selects `enabled` hooks, reuses safe payload fixtures, and
fails CI when an enabled hook is missing a sample or exceeds its declared
budget. Capture-only and disabled entries keep budgets for design review, but
they are not measured by the default CI gate until promoted to `enabled`.
