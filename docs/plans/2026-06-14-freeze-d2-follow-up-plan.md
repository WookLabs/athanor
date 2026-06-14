# Freeze D2 Follow-up Implementation Plan

Date: 2026-06-14

## Goal

Add an evidence-only follow-up for the Freeze D2 residual. The change observes
file-change evidence after tools finish, but it does not add new blocking
behavior.

## Decisions

- Use the existing `PostToolUse` hook only.
- Do not register `FileChanged` in this stage.
- Treat observed out-of-allowlist paths as `concern`, not `failure`.
- Treat missing file-change evidence as normal and non-concerning.

## Implementation

- Extend `scripts/hooks/posttool_evidence_sniffer.py` to write
  `.athanor/sessions/<id>/.hook-state/freeze-change-evidence.jsonl` when a
  PostToolUse payload exposes file-change candidates.
- Reuse `scripts/hooks/freeze_guard.py` allowlist behavior through public
  wrappers for Bash write-target extraction and path classification.
- Add `scripts/work/freeze_evidence_gate.py` to summarize freeze-change
  evidence as `pass` or `concern`.
- Update `/athanor:work` docs so the result handler runs the new concern gate
  after the test-evidence gate.

## Test Plan

- Add PostToolUse regression tests for `tool_response.files_changed`,
  direct file-tool `tool_input.file_path`, Bash syntactic write targets,
  missing allowlist, and no-op non-pytest Bash commands.
- Add gate tests for missing evidence, in-allowlist pass,
  out-of-allowlist concern, unknown-allowlist concern, and malformed JSONL.
- Verify targeted v0.19 tests, v0.18 freeze integration tests, the full test
  suite, release readiness, and `git diff --check`.

