# P12 Runtime Execution Adapter Design

Date: 2026-06-17
Branch: `feat/p12-runtime-execution-adapter`
Status: design for implementation

## Goal

Add a deterministic runtime execution adapter that classifies Athanor work into
an execution backend and isolation policy before future live orchestration work
starts launching larger Claude Code surfaces.

P12 is a decision contract, not a launcher. It does not spawn dynamic workflows,
agent teams, subagents, worktrees, or background sessions. It emits structured
recommendations that later command flows can consume and that CI can verify
against committed fixtures.

## Why This Is Next

The current deep-research scorecard identifies runtime backend selection,
agent-team/dynamic-workflow readiness, and worktree isolation as the largest
post-P11 gaps. Claude Code now exposes several distinct execution surfaces:
single-session work, subagents, dynamic workflows, experimental agent teams, and
worktrees. Athanor's existing `/work --team` language treats parallel work too
generically for that environment.

P12 closes that gap by making the routing decision explicit and testable:

- when to stay in the current checkout;
- when to use subagent waves;
- when a dynamic workflow is worth the fanout;
- when an agent team is worth the coordination cost;
- when same-file or high-risk work must use worktree isolation;
- how to fall back when a capability is unavailable or experimental.

## Design Choices

### Approach A: Launch Native Claude Surfaces Directly

This would teach Athanor to start dynamic workflows, agent teams, or worktrees
immediately.

Rejected for P12. Agent teams remain experimental, dynamic workflow and
worktree availability depends on local Claude Code version/configuration, and
launching live backends without first having command-level trace emitters would
increase autonomy before observability.

### Approach B: Document A Decision Matrix Only

This would add prose guidance explaining when to use each backend.

Rejected. Athanor improves when guidance is executable. A prose-only matrix
would not raise the runtime-readiness score enough because it cannot be
regressed in CI.

### Approach C: Read-Only Recommendation Engine With Fixtures

Selected. Add a CLI and schema that take normalized task-shape input and emit a
backend recommendation. Committed fixtures assert the decision matrix. Future
command flows can call the same code before live dispatch.

## Architecture

Add one gate-style script:

- `scripts/gates/runtime_execution_adapter.py`

Add one report schema:

- `schemas/runtime-execution-adapter-report.schema.json`

Add deterministic fixtures:

- `tests/fixtures/runtime_execution/*.json`

Add regression tests:

- `tests/test_regression_runtime_execution_adapter.py`

Add operator docs:

- `docs/runtime-execution-adapter.md`

Wire release story:

- `.github/workflows/validate-plugin.yml`
- `CHANGELOG.md`
- `tests/test_regression_v019_release_story.py`

The script follows existing Athanor gate conventions:

- Python stdlib only;
- read-only;
- `--json` for machine output;
- fixture mode for CI;
- direct request mode for local inspection;
- exit `0` for pass;
- exit `1` for fixture mismatches;
- exit `2` for invalid input.

## Input Model

A request is a JSON object with these fields:

- `id`: optional stable id for fixture/report readability.
- `task`: short human task summary.
- `risk`: `low`, `medium`, or `high`.
- `estimated_files`: non-negative integer.
- `parallel_workers`: non-negative integer.
- `same_file_risk`: `low`, `medium`, or `high`.
- `long_running`: boolean.
- `requires_isolation`: boolean.
- `requires_peer_coordination`: boolean.
- `requires_rerunnable_script`: boolean.
- `requires_human_review`: boolean.
- `capabilities`: optional object describing local backend availability:
  - `subagent_wave`: `available`, `unavailable`, or `unknown`;
  - `dynamic_workflow`: `available`, `unavailable`, or `unknown`;
  - `agent_team`: `available`, `unavailable`, or `unknown`;
  - `worktree`: `available`, `unavailable`, `manual`, or `unknown`.

Missing capability values default to conservative assumptions:

- `subagent_wave`: `available`;
- `dynamic_workflow`: `unknown`;
- `agent_team`: `unknown`;
- `worktree`: `manual`.

## Output Model

A direct recommendation has:

- `schema_version`: `1`;
- `request_id`;
- `recommended_backend`: one of `solo`, `subagent-wave`,
  `dynamic-workflow`, `agent-team`, `manual-worktree`;
- `fallback_backend`: optional backend;
- `isolation`: one of `current-checkout`, `worktree-recommended`,
  `worktree-required`;
- `risk_level`: `low`, `medium`, or `high`;
- `confidence`: `low`, `medium`, or `high`;
- `reasons`: stable reason objects;
- `warnings`: stable warning objects;
- `required_capabilities`;
- `blocked_capabilities`;
- `notes`.

A fixture report wraps several recommendations:

```json
{
  "schema_version": 1,
  "status": "pass",
  "summary": {
    "fixtures": 5,
    "passed": 5,
    "failed": 0
  },
  "generated_at": "2026-06-17T00:00:00Z",
  "fixtures": []
}
```

## Decision Rules

Rules are intentionally simple and deterministic.

### Solo

Choose `solo` when:

- `parallel_workers <= 1`;
- `estimated_files <= 2`;
- `risk` is `low` or `medium`;
- no isolation or peer coordination is required.

Isolation: `current-checkout`.

### Subagent Wave

Choose `subagent-wave` when:

- parallel workers are useful but bounded;
- workers can report back to one lead context;
- same-file risk is not high;
- peer-to-peer communication is not required.

Typical shape:

- `parallel_workers` from 2 to 3;
- `estimated_files` from 2 to 10;
- `long_running` is false;
- `requires_rerunnable_script` is false.

Isolation is `worktree-recommended` for medium same-file risk, high risk, or
explicit isolation, otherwise `current-checkout`.

### Dynamic Workflow

Choose `dynamic-workflow` when:

- fanout is large;
- the run should be reusable as a script;
- the work is long-running or codebase-wide;
- peer-to-peer communication is not the primary need;
- the capability is available.

Typical shape:

- `parallel_workers >= 4`, or
- `estimated_files >= 20`, or
- `long_running`, or
- `requires_rerunnable_script`.

If dynamic workflow is unavailable or unknown, recommend the best fallback:

- `subagent-wave` if conflict risk is manageable;
- `manual-worktree` if isolation dominates.

### Agent Team

Choose `agent-team` when:

- independent contexts must coordinate directly;
- peer review, competing hypotheses, or cross-layer negotiation is central;
- the capability is available;
- same-file risk is not high.

If agent teams are unavailable or unknown, fall back to `subagent-wave` with a
warning. If same-file risk is high, prefer `manual-worktree` because the
coordination surface does not itself isolate writes.

### Manual Worktree

Choose `manual-worktree` when:

- `requires_isolation` is true and worktree is not natively available;
- `same_file_risk` is high;
- high-risk changes are expected to touch many files;
- the user needs independent branch/workspace review before merge.

Isolation: `worktree-required`.

## Capability Semantics

The adapter treats capability availability as input, not as a live probe. This
keeps P12 deterministic and CI-friendly. A later P13/P14 path can add a
capability probe that fills these values from Claude Code version/configuration.

`unknown` is not a failure. It produces warnings and a conservative fallback.
This matches the current repository's stance: do not silently rely on
experimental or version-specific runtime surfaces.

## Fixture Coverage

Committed fixtures must cover at least:

1. small low-risk change -> `solo`, `current-checkout`;
2. independent bounded parallel work -> `subagent-wave`;
3. large rerunnable fanout with dynamic workflow available ->
   `dynamic-workflow`;
4. same-file conflict/high isolation -> `manual-worktree`;
5. peer coordination with agent team available -> `agent-team`;
6. peer coordination with agent team unknown -> fallback `subagent-wave` and
   warning.

## CI Integration

Add a named gate before broad pytest:

```yaml
- name: Runtime execution adapter fixture gate
  shell: bash
  run: python scripts/gates/runtime_execution_adapter.py --fixture-root tests/fixtures/runtime_execution --json
```

The CI gate does not start runtime backends. It only verifies the routing
contract.

## Error Handling

- Invalid fixture JSON: exit `2`.
- Missing `request` or `expect` in a fixture: exit `2`.
- Unsupported enum value: exit `2`.
- Fixture mismatch: report `fail`, exit `1`.
- Direct recommendation mode with invalid flags: exit `2`.

## Non-Goals

- No dynamic workflow launching.
- No agent team spawning.
- No `git worktree` creation.
- No Claude Code version probing.
- No settings mutation.
- No external telemetry.
- No replacement for P13 live trace emitters.

## Architecture Review

The selected design is deliberately a contract-first adapter. It raises the
runtime-readiness score because it turns backend choice into a stable,
testable artifact, while avoiding the risk of introducing live fanout before
trace coverage exists. It also gives future command flows a single importable
decision function instead of scattering ad hoc backend rules across skills.

The main risk is false precision: a deterministic adapter can recommend the
wrong backend if callers provide poor task-shape inputs. The mitigation is to
keep reasons and warnings explicit, default unknown capabilities to
conservative fallbacks, and make future live traces compare selected backend
against actual outcomes.

## Self-Review

- Placeholder scan: no unresolved placeholders.
- Scope check: one read-only adapter, schema, fixtures, docs, CI wiring.
- Runtime safety check: no launchers, no settings changes, no network access.
- Testability check: every decision rule is represented by fixture tests.
