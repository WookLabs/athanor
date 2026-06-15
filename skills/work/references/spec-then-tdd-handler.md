# Spec-then-TDD Execution Reference

Detailed reference for `/athanor:work` Spec-then-TDD execution discipline.
Cross-linked from `skills/work/SKILL.md` Step 2 (Solo dispatch packet) and
Step 2b (result handler).

## ATHANOR_RESULT schema

Worker MUST return:

```
ATHANOR_RESULT
status: {done|failure|done_with_concerns|needs_context|blocked}
subtask_id: {id}
summary: {what was done}
files_changed:
  - {file}: {change description}
decisions:
  - {decisions made}
discoveries:
  {tagged with importance}
lessons_read: [{list of lesson filenames you read, or empty}]
verification: {what was run} → {pass|fail}
execution_note: {spec-then-tdd|test-aware|direct}   # v0.8.0
execution_note_source: {plan|grandfathered}          # v0.8.0
red_evidence:                                         # v0.8.0 — only when spec-then-tdd
  - criterion: "MUST <text>"
    command: "pytest tests/..."
    test_node_id: "tests/...::test_..."
    exit_code: <int>
    output_tail: "..."
red_status: {red|partial_never_red|never_red}        # v0.8.0 — only when spec-then-tdd
tests_modified: {true|false}                          # v0.8.0 — ALWAYS emit when execution_note in {spec-then-tdd, test-aware}, so Phase 2 downgrade can route a spec-then-tdd subtask through the Phase 3 gate without false-positive failure
test_paths_touched: [{paths}]                         # v0.8.0 — ALWAYS emit when execution_note in {spec-then-tdd, test-aware}
full_suite_passed: {true|false}                       # v0.8.0 — ALWAYS emit; result of `pytest tests/` (full suite); Phase 3 gate trusts this self-report combined with test_paths_touched
concerns: [{string}, ...]                             # v0.16.0 — REQUIRED when status == done_with_concerns; non-empty list
context_needed: "{description}"                       # v0.16.0 — REQUIRED when status == needs_context
blocker: "{external blocker description}"             # v0.16.0 — REQUIRED when status == blocked
END_RESULT
```

## Execution Instructions (v0.8.0 — branches on execution_note)

The leader MUST inject ONE of the three blocks below based on the subtask's
`execution_note` value. If the `execution_note` field is absent (grandfathered
plan from before v0.8.0), the leader treats the subtask as `direct` and
includes the Direct block. The worker should be told which block applies and
report `execution_note_source: grandfathered` in ATHANOR_RESULT when the
fallback fires.

### Direct (execution_note: direct OR field absent — grandfathered)

Standard Ralph-Loop unchanged from earlier athanor releases:

1. Read the relevant files first (targeted, not full files)
2. Implement the change
3. Run verification:
   - command: run the command via Bash, exit code 0 = pass
   - check: verify the condition (file exists, content matches, etc.)
   - review: self-review your changes for correctness
   - none: just implement once, no retry
4. If verification fails: analyze why, adjust, retry
5. If all retries exhausted: return failure brief

### Spec-then-TDD Instructions (execution_note: spec-then-tdd)

You have a list of `acceptance_criteria` (passed as the subtask's
acceptance_criteria field). Process each criterion in order:

For each criterion (e.g., "MUST exit 2 when material claim detected"):

1. **WRITE**: Write a failing test for this criterion in the test file listed
   under Files. Do NOT touch implementation code in this step.
2. **RUN**: Execute `pytest <test_file>::<new_test_function> -v` via Bash.
   Capture full output.
3. **VERIFY RED**: Confirm the test FAILED (exit code non-zero). Record
   per-criterion `red_evidence` with these required fields:
   - `command`: the exact pytest command you ran
   - `test_node_id`: the parametrized test node id
     (e.g., `tests/test_foo.py::test_bar[case-1]`)
   - `exit_code`: integer exit code from pytest
   - `output_tail`: last ~10 lines of pytest output proving the failure mode
   If the test PASSES on first run (exit_code == 0), set
   `red_status: never_red` for this criterion in your ATHANOR_RESULT (still
   record the GREEN-on-first-run command and exit_code as red_evidence) and
   SKIP to the next criterion. The auto-downgrade is handled by the leader,
   not by you.
4. **IMPLEMENT**: Add the minimum implementation to satisfy this criterion.
5. **VERIFY GREEN**: Execute the same pytest command. Confirm the test PASSES
   (exit code 0). Also run the full test suite (`pytest tests/`) — all
   existing tests must still pass.

After all criteria processed:
- Optional refactor pass (improve naming, dedupe — no behavior change)
- Final pytest run — all tests green
- Report ATHANOR_RESULT with per-criterion `red_evidence` list AND aggregate
  `red_status`:
  - `red` if all criteria recorded a RED exit_code != 0 in their red_evidence
  - `partial_never_red` if some criteria had RED but others were never_red
  - `never_red` if all criteria's first-run exit_code was 0 (i.e. tests
    didn't actually go RED)
- ALSO report `tests_modified: true` and the list of test artifact paths
  touched (`test_paths_touched: [...]`) using `git diff --name-only` filtered
  to `tests/**`. These fields look redundant with `red_evidence` but Phase 2
  downgrade can route a spec-then-tdd subtask through the Phase 3 test-aware
  gate, and the gate validates the same fields a true test-aware subtask
  would emit. Omitting them causes Phase 3 to false-positive fail any
  downgraded subtask even when tests were written.
- ALSO report `full_suite_passed: true` ONLY after running `pytest tests/`
  end-to-end and observing exit code 0. This is the worker's self-report
  that the broader regression suite stayed green — the leader's Phase 3
  gate treats `full_suite_passed: false` (or missing) as a gate violation.

The leader will validate that every criterion in your acceptance_criteria
list has a matching red_evidence entry. Missing or malformed red_evidence
for any criterion is treated as `never_red` for that criterion (defensive —
workers cannot silently skip the RED check by omitting evidence).

### Test-Aware End Gate (execution_note: test-aware)

You may write tests and implementation in any order. Before reporting success,
the end gate enforces test artifact changes:

1. Run `git diff --name-only` and confirm at least one path is under
   `tests/` (i.e. matches `^tests/.*` regex — this includes any file under
   `tests/`: `test_*.py` files, `conftest.py`, fixture modules under
   `tests/fixtures/`, snapshot files, golden files, etc. — a broader test
   artifact pattern than just `test_*.py`).
   If no path under `tests/` has changes, REPORT failure — test-aware
   subtasks require test artifact changes.
2. Run `pytest tests/` end-to-end — full suite must pass with exit code 0.
3. Report all three fields in your ATHANOR_RESULT:
   - `tests_modified: true`
   - `test_paths_touched: [...]` (list of paths from step 1)
   - `full_suite_passed: true` (only if step 2 actually returned exit code 0)

## v0.8.0+ Spec-then-TDD result handler (runs BEFORE the success/failure branch)

This handler starts with the original **advisory self-report shape** check:
the leader validates the shape of the worker's `red_evidence` (command,
test_node_id, exit_code, output_tail) before applying the downgrade rule.
v0.19.0 adds a **hybrid evidence gate** after the test-aware clauses: when
PostToolUse evidence exists, `scripts/work/evidence_gate.py` cross-checks
worker self-report against `.hook-state/test-evidence.jsonl`. Evidence
mismatch is a gate failure. Missing evidence is a concern, not a hard failure,
so early PostToolUse payload/environment gaps do not brick work completion.

### Phase 1 — validate red_evidence shape (only when subtask.execution_note == "spec-then-tdd")

For each criterion in `subtask.acceptance_criteria`:
- Find the matching entry in `ATHANOR_RESULT.red_evidence`.
- If absent OR missing any of {command, test_node_id, exit_code, output_tail},
  mark this criterion as `never_red` (defensive default).
- If `exit_code == 0` (RED check did not actually fail), mark this criterion
  as `never_red`.

Compute `red_status_resolved`:
- All criteria `never_red` → `red_status_resolved = "never_red"`
- Some `never_red` but not all → `red_status_resolved = "partial_never_red"`
- All criteria had non-zero RED exit_code → `red_status_resolved = "red"`

### Phase 2 — apply downgrade rule

If `red_status_resolved in {"never_red", "partial_never_red"}`:
- Mark the subtask as a downgrade-pending candidate. The actual completion
  decision is deferred to Phase 3 below — a downgraded subtask must STILL
  pass the test-aware gate (test files touched + pytest green) before being
  marked complete. Without this rule, a worker that fabricates `red_evidence`
  failures (or simply never writes any tests) could be silently marked
  successful via downgrade. Phase 3 enforcement closes that loophole.
- Append to work-log.md:
  ```
  ## Subtask {id}: pending [auto-downgraded: spec-then-tdd → test-aware, awaiting gate]
  - Reason: red_status_resolved={value} (one or more criteria did not produce RED evidence)
  - Detected by: leader validation of worker's red_evidence shape
    (criteria with missing/malformed evidence were defaulted to never_red)
  - Remediation: leader auto-downgraded the completion criteria to test-aware;
    Phase 3 below now applies and the subtask completes ONLY if the
    test-aware gate (tests/** paths modified + pytest green) passes
  - Original execution_note: spec-then-tdd
  - effective_execution_note: test-aware (downgrade applied)
  - never_red criteria: [list of criterion text]
  ```
- No user escalation. The downgrade and subsequent gate check are silent
  except for the work-log entries.

### Phase 3 — test-aware gate enforcement (applies when subtask.execution_note == "test-aware" OR Phase 2 downgraded a spec-then-tdd subtask to test-aware)

The gate is a **conjunction** of three signals — all three MUST hold for
the subtask to pass:

1. `ATHANOR_RESULT.tests_modified == true` AND `test_paths_touched` is
   non-empty (the worker actually touched `tests/**`).
2. `ATHANOR_RESULT.full_suite_passed == true` (the worker self-reports that
   it ran `pytest tests/` and saw exit code 0). Missing field is treated as
   `false` (defensive default — worker that forgot to run the full suite
   does not pass the gate).
3. The `verification:` line in ATHANOR_RESULT (free-form prose set by the
   existing Ralph-Loop instruction) shows a pass/green signal consistent
   with full_suite_passed.
4. **Hybrid PostToolUse evidence gate**: normalize the worker's
   `ATHANOR_RESULT` fields into JSON and run:
   ```
   python3 scripts/work/evidence_gate.py \
     --evidence .athanor/sessions/<id>/.hook-state/test-evidence.jsonl \
     --result-json -
   ```
   Pass this JSON object on stdin:
   ```
   {
     "execution_note": "<effective execution_note>",
     "red_evidence": [...],
     "full_suite_passed": true|false,
     "verification": "<verification line>"
   }
   ```

If any hard gate clause fails:
- This is a worker-side gate violation — test-aware (or downgraded
  spec-then-tdd) subtask completed without proper test discipline.
- Mark subtask as failed (NOT success), increment `consecutiveFailures`.
- work-log message names the specific gate clause that failed:
  - `test-aware gate violation: no tests/** paths modified (test_paths_touched empty)`
  - `test-aware gate violation: full_suite_passed=false or missing (worker did not run pytest tests/)`
  - `test-aware gate violation: verification line contradicts full_suite_passed`
  - `test-evidence gate violation: evidence mismatch between ATHANOR_RESULT and PostToolUse test-evidence.jsonl`
- If this subtask was a Phase 2 downgrade, the work-log entry is updated
  from `pending` to `✗ failed [downgraded then gate-rejected]` so the audit
  trail captures both steps.

If `evidence_gate.py` returns JSON status `"concern"`:
- Do NOT treat it as a gate failure. Missing evidence is expected on some
  early PostToolUse payload variants or sessions where pytest ran outside the
  hook surface.
- Append the concern to work-log.md:
  `test-evidence gate concern: missing evidence for <red_evidence|full_suite>`.
- If the worker otherwise passed all gate clauses, prefer
  `done_with_concerns` when reporting the final subtask status; otherwise keep
  the normal failure handling for the failing non-evidence clause.

After the test-evidence gate, run the Freeze D2 evidence concern check:
```
python3 scripts/work/freeze_evidence_gate.py \
  --evidence .athanor/sessions/<id>/.hook-state/freeze-change-evidence.jsonl
```
If it returns JSON status `"concern"`, do NOT treat it as a gate failure.
Append each concern to work-log.md as
`freeze-evidence gate concern: <concern>`, and prefer `done_with_concerns`
when the worker otherwise passed all hard gate clauses. Missing
`freeze-change-evidence.jsonl` returns `"pass"` and should not create a
concern; many legitimate tool runs expose no file-change payload.

If all hard gate clauses pass and the evidence gate has no failure:
- Subtask is marked complete and the work-log `pending` entry (if any) is
  updated to `✓ {title} [auto-downgraded: spec-then-tdd → test-aware]`.

**Honesty note on the gate**: the leader still does not independently
re-execute `pytest tests/`. The hybrid evidence gate only cross-checks
PostToolUse records that actually exist. A fabricated `full_suite_passed:
true` claim with conflicting full-suite evidence fails; the same claim with
no full-suite evidence becomes a concern. Strict hard-fail on missing evidence
is deferred until live PostToolUse payload coverage is proven.

### Phase 4 — grandfathered fallback breadcrumb (only when execution_note absent in plan)

If `ATHANOR_RESULT.execution_note_source == "grandfathered"`:
- Append `[grandfathered: execution_note field absent in plan; treated as direct]`
  to the work-log entry for traceability. This applies to BOTH branches:
  - On success (the "If success" block below), append the breadcrumb to the
    `✓ {title}` line so the success entry reads
    `✓ {title} [grandfathered: execution_note field absent in plan; treated as direct]`.
  - On failure (the "If failure" block below), append the breadcrumb to the
    failure work-log entry so the failure record also captures the
    grandfathered status. If the failure path normally writes no work-log
    entry (current pre-v0.8.0 behavior), write a minimal one anchored on
    grandfathered status: `## Subtask {id}: ✗ {title} [grandfathered, failed]`.

## v0.19.0 — Evidence-Bound Enforcement (hybrid stage)

<!-- forward-compat anchor for PostToolUse test-evidence sniffer — fulfilled by evidence-only v1 and evidence_gate.py hybrid cross-check -->

The PostToolUse hook records pytest evidence, and the `/athanor:work` result
handler now cross-checks that evidence through `scripts/work/evidence_gate.py`:

- Hook fires after Bash tool runs a pytest-family command (`pytest`,
  `py.test`, or `python -m pytest`).
- Hook appends JSONL evidence to
  `.athanor/sessions/<latest>/.hook-state/test-evidence.jsonl`.
- Each record includes the command, normalized test targets, scope
  (`targeted`, `full_suite`, or `unspecified`), exit code, output tail,
  timestamp, and session id.
- The hook always fails open. It never exits 2 and never blocks a session.
- The handler treats evidence mismatches as `test-evidence gate violation`
  failures.
- The handler treats missing evidence as a concern in hybrid mode.
- The same hook also records evidence-only Freeze D2 file-change observations
  to `.hook-state/freeze-change-evidence.jsonl` when PostToolUse exposes
  tool input write targets or structured `tool_response.files_changed`-style
  fields. `scripts/work/freeze_evidence_gate.py` reports observed
  out-of-allowlist or unknown-allowlist paths as concerns only.

What this stage does **not** enforce:

- Missing evidence is not a hard failure yet.
- File-change observations are not hard failures yet.
- `tool_response_available` remains empirical. The sniffer tolerates several
  likely payload field names, but live Claude Code payload evidence should
  still be reviewed before strict enforcement. The capability probe therefore
  labels PostToolUse payload keys as `expected` and reports only redacted
  `evidence_streams` metadata from existing JSONL files.

Next enforcement upgrade:

- Promote missing PostToolUse evidence from concern to failure once live
  payload coverage is stable.
- Add a separate `FileChanged` spike only after a live payload capture proves
  that event is needed beyond the current PostToolUse evidence stream.
