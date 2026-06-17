# External Eval Adapter

P22 exports packaged Athanor workflow eval episodes into an external-harness
metadata layout without enabling external execution by default.

The adapter is intentionally dependency-free. It does not install Inspect,
Harbor, Docker, or any sandbox runtime. It writes JSON files that those systems
or a future bridge can inspect and translate.

## Export

First package the local workflow episode:

```bash
python scripts/evals/package_workflow_episode.py \
  --scenario-root tests/fixtures/workflow_evals \
  --output-dir .athanor/episodes/workflow-evals \
  --json
```

Then export the external adapter:

```bash
python scripts/evals/export_external_eval_adapter.py \
  --episode-root .athanor/episodes/workflow-evals \
  --output-dir .athanor/external-evals/workflow-evals \
  --json
```

## Directory Layout

```text
.athanor/external-evals/workflow-evals/
  external-eval.json
  README.md
  tasks/
    workflow-evals.json
  scorers/
    deterministic-workflow.json
  sandbox/
    manifest.json
```

## Compatibility Profiles

`external-eval.json` declares two descriptive compatibility profiles:

- `inspect-like`;
- `harbor-like`.

These are not claims that Athanor invokes Inspect or Harbor. They define the
portable parts those ecosystems normally need: task metadata, dataset path,
scorer metadata, runner command, sandbox policy, and limits.

## Sandbox Policy

`sandbox/manifest.json` records the policy external harnesses must preserve:

- `network_access: false`;
- `setup_commands: []`;
- `external_telemetry: false`;
- read-only access to the packaged episode;
- stdout as the only declared write path.

The adapter keeps `external_execution.default_enabled: false` and
`dependencies: []`. A future bridge may translate the exported JSON into a
native Inspect or Harbor task, but this plugin does not install or run those
systems by default.

## CI Gate

CI runs the adapter after the workflow episode package gate. The gate proves
that committed workflow scenarios can be packaged, exported, and represented
with explicit local-only sandbox metadata before broad pytest runs.
