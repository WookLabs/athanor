# P15 Eval Episode Packaging Design

Date: 2026-06-17
Status: implementation design
Depends on: P6 workflow scenario runner, P13 live traces, P14 OTel-style trace export

## Research Basis

P15 targets the remaining "portable eval episode packaging" gap from
`docs/architecture/2026-06-17-p14-deep-research-refresh.md`.

The current external baseline points away from a SaaS-specific package format:

- OpenAI's Evals API docs now describe a transition window, with the existing
  Evals platform becoming read-only on 2026-10-31 and scheduled to shut down on
  2026-11-30. P15 should not bind Athanor's local eval story to that API.
- Inspect AI emphasizes reusable eval building blocks, eval sets, retryable
  runs, scoped log directories, external agents, and sandboxed task execution.
- LangSmith and AgentEvals emphasize trajectory evaluation, including
  deterministic trajectory matching when expected tool paths are known.
- DSPy keeps the portable core simple: dataset plus metric/scorer function.

The common denominator is a portable local episode with dataset/scenario files,
runner command, scorer metadata, sandbox hints, limits, and a manifest that can
be inspected before execution.

## Problem

Athanor already has deterministic workflow scenario fixtures in
`tests/fixtures/workflow_evals/` and an executable runner in
`scripts/evals/run_workflow_scenarios.py`. Those fixtures are strong local CI
checks, but they are not yet packaged as portable benchmark episodes:

- no episode manifest;
- no setup/runtime command metadata;
- no scorer metadata separate from inline graders;
- no sandbox/network/write policy;
- no time/retry/parallelism limits;
- no runner path that executes an episode directory directly.

This keeps the local eval harness near 9.45/10 instead of comfortably above
9.5/10 because the eval artifacts are hard to move, review, or run outside the
repo's current fixture layout.

## Goals

1. Package one or more workflow scenario JSON files into a portable episode
   directory.
2. Make the package self-describing through `episode.json`.
3. Preserve the existing deterministic scenario and grader format.
4. Let the existing runner execute an episode directory with `--episode-root`.
5. Keep the implementation stdlib-only and local-first.
6. Record sandbox, network, filesystem, scorer, and limit metadata explicitly.
7. Add a CI gate that packages the committed scenarios and runs the packaged
   episode before broad pytest.

## Non-Goals

- No OpenAI Evals API upload.
- No Inspect AI dependency.
- No LangSmith, DSPy, or other cloud integration.
- No LLM-as-judge release gate.
- No automatic execution of arbitrary setup commands.
- No network access.
- No generated zip archive in git.

## Architecture

P15 adds a thin packaging layer:

```text
tests/fixtures/workflow_evals/*.json
        |
        v
scripts/evals/package_workflow_episode.py
        |
        v
<episode-root>/
  episode.json
  README.md
  scenarios/*.json
        |
        v
scripts/evals/run_workflow_scenarios.py --episode-root <episode-root> --json
```

The core module is `scripts/evals/workflow_episode.py`. It owns:

- scenario file discovery and copying;
- scenario id/grader summary extraction;
- episode manifest creation;
- manifest loading and validation;
- resolving the packaged scenario root for the runner.

The packager CLI uses the module and existing scenario runner validation. The
runner keeps its current `--scenario-root` behavior and adds mutually exclusive
`--episode-root` support.

## Episode Directory Contract

An episode directory contains:

- `episode.json`: manifest validated by
  `schemas/workflow-eval-episode.schema.json`;
- `README.md`: human-readable local run instructions;
- `scenarios/*.json`: copied scenario files that still conform to
  `schemas/workflow-eval-scenario.schema.json`.

The manifest uses schema version 1 and includes:

- `episode_id`: stable package id;
- `title` and `description`;
- `created_by`: `athanor-workflow-episode-packager`;
- `source`: original scenario root path and scenario ids;
- `runtime`: runner path, command argv, Python requirement, dependency list;
- `artifacts`: scenario root, scenario schema, trace schema;
- `scorers`: deterministic scorer kinds present in the episode;
- `sandbox`: network disabled, read-only scenario inputs, local output policy;
- `limits`: timeout seconds, retries, max parallelism, scenario/record caps;
- `privacy`: synthetic/local fixture statement and raw trace content status.

## Data Flow

1. The packager loads and evaluates the source scenarios through
   `evaluate_root()`. Packaging fails if parsing fails or the source suite does
   not reach its declared `min_score` thresholds.
2. Scenario JSON files are copied into `<episode-root>/scenarios/`.
3. The manifest is generated from the copied files, not from stale in-memory
   assumptions.
4. The runner reads `episode.json`, validates that network is disabled and that
   the declared scenario root exists under the episode directory, then delegates
   to `evaluate_root()`.

## Error Handling

- Invalid source scenario: exit 2 with `workflow episode package: ...`.
- Failing source scenario suite: exit 1 with the JSON report when `--json` is
  requested, otherwise a short error.
- Invalid episode manifest: exit 2 with `workflow scenario eval: ...`.
- Missing packaged scenario files: exit 2.
- Ambiguous CLI use of both `--scenario-root` and `--episode-root`: argparse
  rejects it via a mutually exclusive group.

## Security And Privacy

The episode runner never executes setup commands. The manifest records intended
commands and setup notes for external harnesses to inspect. The default
committed episodes use synthetic trace fixtures and no network. Raw trace
messages remain inside the copied scenario fixtures because those are already
committed test data; the manifest states this explicitly so external consumers
can classify the package before running it.

## Architecture Review

Rejected alternatives:

1. Generate Inspect AI tasks directly. This would add dependency and version
   churn for a local harness problem.
2. Export OpenAI Evals payloads. The documented deprecation window makes that a
   poor long-term anchor.
3. Invent a separate grader format. Existing graders are deterministic, tested,
   and CI-backed; duplicating them would create drift.

The selected design keeps Athanor's evidence model local and deterministic
while making it portable enough for future benchmark adapters.

