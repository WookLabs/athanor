# Athanor Final Optimization Plan

Date: 2026-06-16
Branch: `feat/hook-payload-replay`

## Goal

Review every remaining improvement candidate from the xhigh audit follow-up,
implement the candidates that materially improve the plugin, and verify the
plugin is optimized beyond the 9.5 evidence target without leaving known
actionable gaps undocumented.

## Scope Decisions

1. **Live pytest PostToolUse fixture** — implement. The corpus already proves
   live PostToolUse payload shape with a Bash `echo`, but a live pytest fixture
   gives stronger evidence for the actual test-evidence path.
2. **UserPromptSubmit replay/import boundary** — implement. The importer
   currently accepts `UserPromptSubmit` while replay supports only core events;
   this must be made explicit instead of latent.
3. **Strict default policy** — implement as policy documentation plus tests.
   Do not silently change existing defaults without migration framing.
4. **Capture harness duplication** — implement a small shared helper module so
   core hook capture and UPS capture do not drift.
5. **Fail-open health diagnostics** — implement. Evidence hooks should still
   fail open, but infrastructure failures should be written to a diagnostic
   JSONL stream for audit.
6. **FileChanged spike** — implement an opt-in capture path and documentation;
   do not register enforcement without live payload evidence.
7. **mem-search permanent persistence** — review and leave explicitly scoped as
   a separate subsystem unless current code reveals a small, safe integration
   point. The current branch already corrected overclaims.
8. **PostToolUse exit-code provenance** — implement. The live pytest payload
   proves direct exit-code is absent, so the sniffer should keep that boundary
   honest while inferring only clear pytest output summaries and recording the
   source.
9. **CI replay visibility** — implement. Hook fixture replay already runs
   through pytest, but a named CI step makes replay failures easier to diagnose.

## Execution Plan

1. Add tests first for each behavioral change:
   - importer/replay boundary for unsupported replay-only events,
   - shared capture helper parity,
   - PostToolUse health diagnostics on fail-open paths,
   - FileChanged capture snippet coverage,
   - strict default migration policy text.
2. Run targeted tests and confirm they fail for the expected missing behavior.
3. Implement minimal changes:
   - shared capture helper under `scripts/hooks/`,
   - update capture scripts to reuse it,
   - update replay/import handling,
   - add health diagnostic writes in `posttool_evidence_sniffer.py`,
   - extend generic capture to include `FileChanged`,
   - update docs and audit score.
   - add pytest-output exit-code inference with explicit provenance,
   - run hook fixture replay as a named CI workflow step.
4. Capture or import a live pytest PostToolUse fixture if Claude Code is
   available in the current environment; otherwise keep the plan active and do
   not claim that specific candidate is complete.
5. Verify with:
   - targeted regression tests,
   - full `python -m pytest tests\ -q`,
   - `python scripts\check_release_ready.py --ci`,
   - `python scripts\gates\replay_hook_fixtures.py --fixture-root tests\fixtures\hooks --json`,
   - `git diff --check`,
   - fixture/doc secret scan.

## Completion Standard

The work is complete only when every implemented candidate has direct tests,
the corpus replay passes, the full suite passes, release checks pass, and the
audit document explains any remaining non-actionable release or external
dependency decisions.
