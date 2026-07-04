# v0.18.0 Freeze residual — Codex stage NOT freeze-gated

Relocated from `skills/lfg/SKILL.md` (session 2026-07-03-004 Phase 2.1,
pure-relocation diet). The 2-line pointer left inline in the SKILL.md
body keeps the residual visible at the dispatch site; this file holds
the full reasoning for operators tracing the D2 residual.

If the user has enabled `athanor.json` `hooks.freeze.mode = "session"`,
the Freeze guard gates Claude file-tool writes (Edit / Write /
MultiEdit + conservative Bash patterns) against the per-session
allowlist. **Codex subprocess writes invoked during this LFG run
(`/athanor:plan` Step 1 Codex dispatches, any `codex exec ...` worker
calls) are NOT gated by Freeze** — those writes happen inside a
subprocess whose destination paths are not visible to the PreToolUse
dispatcher. This is the documented D2 residual; see
`skills/work/references/freeze.md` §"D2 residual — subprocess writes
NOT gated" and `docs/v0.18.0-migration.md` §"D2 Honesty Residual".

The leader does not warn the user about this on every invocation
(noise); the residual is documented in CHANGELOG, ROADMAP, and the
migration guide. LFG users with strong scope-lock requirements should
be aware that Codex stage writes are on the honour system within this
release line.
