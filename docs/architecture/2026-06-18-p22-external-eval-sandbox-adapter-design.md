# P22 External Eval Sandbox Adapter Design

Date: 2026-06-18
Branch: `feat/p22-external-eval-sandbox-adapter`

## Context

P15 made Athanor workflow scenarios portable as local eval episodes. The
remaining external benchmark/sandbox gap is not that Athanor lacks local evals;
it is that external harnesses cannot inspect a task/scorer/sandbox contract
without understanding Athanor's internal `episode.json` format.

OpenAI's 2026 Agents SDK direction emphasizes native sandbox execution with
manifests, while Harbor and Terminal-Bench emphasize benchmark tasks with
explicit task, scorer, and sandbox metadata. Athanor should align with that
shape without making Docker, Inspect, Harbor, or network execution mandatory.

## Design

`scripts/evals/export_external_eval_adapter.py` reads an already packaged
episode and writes an external-harness metadata directory:

```text
external-eval.json
tasks/workflow-evals.json
scorers/deterministic-workflow.json
sandbox/manifest.json
README.md
```

The adapter reuses `scripts.evals.workflow_episode.load_episode`, so unsafe
episodes that require network access or exceed declared limits are rejected
before export. The exported JSON is descriptive metadata, not an execution
launcher.

## Safety Properties

- no default external execution;
- no package installation;
- no setup commands;
- no network access;
- no external telemetry;
- no Docker/Harbor/Inspect dependency;
- existing deterministic runner remains the only supported local execution
  path.

## Score Impact

P22 is expected to move external benchmark/sandbox interop from 9.3 to 9.6.
It does not attempt to solve native runtime escalation or reactive event
channels; those remain P23 and P24.

## Verification

```text
python -m pytest tests/test_regression_external_eval_adapter.py tests/test_regression_workflow_eval_episode.py tests/test_regression_v019_release_story.py -q
python scripts/evals/package_workflow_episode.py --scenario-root tests/fixtures/workflow_evals --output-dir .athanor/episodes/workflow-evals --json
python scripts/evals/export_external_eval_adapter.py --episode-root .athanor/episodes/workflow-evals --output-dir .athanor/external-evals/workflow-evals --json
python scripts/gates/harness_decision_ledger.py --json
```

## Follow-Up

A future bridge can translate the exported JSON into exact Inspect or Harbor
task files after operator approval. That bridge should stay optional until a
real external benchmark run proves value.
