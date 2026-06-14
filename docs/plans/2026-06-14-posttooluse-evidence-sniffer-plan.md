# PostToolUse Evidence Sniffer Plan

Date: 2026-06-14
Selected audit item: 1
Mode: evidence-only v1

## Goal

Register a PostToolUse hook that records pytest-family Bash command results to
session state. The hook must collect useful evidence without blocking Claude
Code sessions.

## Non-Goals

- No UserPromptSubmit registration.
- No enforcement against worker-reported evidence yet.
- No freeze policy change.
- No assumption that every Claude Code version exposes identical PostToolUse
  payload fields.

## Runtime Contract

1. Hook event: `PostToolUse`.
2. Command:
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/hooks/posttool_evidence_sniffer.py"`.
3. Input: Claude Code hook JSON from stdin.
4. Matching scope: Bash commands that invoke `pytest`, `py.test`, or
   `python -m pytest`.
5. Output path:
   `.athanor/sessions/<latest>/.hook-state/test-evidence.jsonl`.
6. Record shape:
   - `schema_version`
   - `timestamp`
   - `hook_event_name`
   - `tool_name`
   - `command`
   - `test_targets`
   - `primary_target`
   - `scope`
   - `exit_code`
   - `output_tail`
   - `session_id`
7. Failure behavior: fail-open with exit code 0.

## Acceptance Criteria

1. A new regression suite proves the sniffer is importable and always
   evidence-only.
2. Non-Bash or non-pytest payloads are ignored.
3. Representative pytest payloads append JSONL evidence rows.
4. Missing or malformed payloads return exit 0.
5. `hooks/hooks.json` registers exactly one PostToolUse entry using
   `${CLAUDE_PLUGIN_ROOT}`.
6. `capability_probe.py` reports PostToolUse as registered/supported in the
   evidence-only sense while keeping empirical `tool_response` certainty
   nullable.
7. The v0.18 static-dedup lock continues to forbid UserPromptSubmit, while
   allowing the deliberate PostToolUse addition.
8. CI installs every dependency needed for test collection.

## Implementation Steps

1. Add failing regression tests for the hook script, hook manifest, capability
   probe, and static-dedup inventory update.
2. Implement `scripts/hooks/posttool_evidence_sniffer.py`.
3. Register PostToolUse in `hooks/hooks.json`.
4. Update `capability_probe.py` and `spec-then-tdd-handler.md`.
5. Correct CI dependency installation for `pyyaml`.
6. Run targeted tests, collection, release readiness checks, and the full test
   suite.

## Enforcement Upgrade Later

The next step after v1 evidence collection is to make the work result handler
cross-check `ATHANOR_RESULT.red_evidence` and `full_suite_passed` against
`test-evidence.jsonl`. That should be a separate change because it affects
completion semantics and can block sessions.
