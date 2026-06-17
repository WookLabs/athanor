# Workflow Eval Episodes

P15 packages Athanor workflow scenario fixtures as portable local eval episodes.
An episode is a directory with a manifest, copied scenario files, and a
documented runner command. It is designed for local CI and external harnesses
that want to inspect the task, scorer, sandbox, and limits before running it.

## Package

```bash
python scripts/evals/package_workflow_episode.py \
  --scenario-root tests/fixtures/workflow_evals \
  --output-dir .athanor/episodes/workflow-evals \
  --json
```

The packager validates the source scenarios with the deterministic workflow
runner before writing the manifest. Invalid scenario files exit `2`; scenario
suites that evaluate but miss their declared `min_score` thresholds exit `1`.

## Run

```bash
python scripts/evals/run_workflow_scenarios.py --episode-root .athanor/episodes/workflow-evals --json
```

`--episode-root` reads `episode.json`, validates the local-only sandbox policy,
resolves `artifacts.scenario_root`, and then delegates to the same deterministic
runner used by `--scenario-root`.

## Directory Layout

```text
.athanor/episodes/workflow-evals/
  episode.json
  README.md
  scenarios/
    scenarios.json
```

The manifest is described by
`schemas/workflow-eval-episode.schema.json`. The packaged scenario files still
use `schemas/workflow-eval-scenario.schema.json`, and their inline trace records
still use `schemas/workflow-trace.schema.json`.

## Manifest Fields

`episode.json` records:

- `episode_id`, `title`, `description`, and `created_by`;
- source scenario files and scenario ids;
- runtime command and Python requirement;
- artifact paths for scenario, scenario schema, and trace schema;
- scorer metadata, including `deterministic_grader_kinds`;
- sandbox metadata, including `network_access: false`;
- limits for timeout, retries, parallelism, scenario count, and trace records;
- privacy metadata stating that committed fixtures use synthetic trace content
  and do not perform external upload.

## Sandbox Policy

Episode execution is intentionally conservative:

- no network access;
- no setup command execution;
- no OpenAI Evals, Inspect AI, LangSmith, or DSPy dependency;
- no LLM-as-judge release gate;
- stdout report output only.

The manifest records intended runtime behavior for external harnesses, but the
Athanor runner does not execute arbitrary setup commands from the manifest.

## CI Gate

The validation workflow runs a named `Workflow episode package gate` before the
broad pytest suite. It packages `tests/fixtures/workflow_evals` into
`.athanor/episodes/workflow-evals` and then executes the packaged episode with
`scripts/evals/run_workflow_scenarios.py --episode-root`.

