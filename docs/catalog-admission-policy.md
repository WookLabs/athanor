# Catalog Admission Policy

Date: 2026-06-20

This policy governs how Athanor absorbs ideas from local `ref/` repositories.
The goal is selective learning, not surface growth. Athanor keeps **11 commands**
and **4 registered agents** unless a separate topology decision and gate prove
that replacing the surface is better than extending it.

## Admission States

Every reference receives one of these states:

- `adopt`: principle or contract can be copied into Athanor policy with little
  runtime surface risk.
- `adapt`: idea is useful, but must enter through an existing skill, local
  read-only gate, schema, fixture, or documentation path.
- `observe`: keep as radar; do not build from it yet.
- `reject`: do not use the design for Athanor core.
- `sunset`: remove from the active radar unless a current Athanor artifact
  still cites it.

## Fail-Cap Rubric

The gate uses a fail-cap rubric: the weakest scored dimension caps the final
recommendation.

Dimensions:

- `local_first`: no external telemetry, hosted dashboard, proxy, or API-key
  dependency by default.
- `surface_discipline`: no broad command, registered-agent, hook, MCP, or skill
  explosion.
- `evidence_strength`: concrete docs, tests, schemas, or fixtures.
- `license_clarity`: license or principle-only status is visible.
- `athanor_fit`: fits Thin Leader, local gates, and small live surface.

Runtime surface growth is capped below direct `adopt`. A reference with many
skills, agents, commands, hooks, manifests, or MCP tools may still be `adapt`,
but only through bounded local artifacts.

## Default Rejections

Reject or keep in `observe` unless explicitly proven otherwise:

- daemon or server control planes;
- cloud telemetry or hosted dashboards;
- default external memory or remote retrieval;
- broad MCP tool bundles;
- automatic agent or command generation;
- full-auto, auto-merge, or unattended irreversible actions;
- mutating hook installers outside the explicit existing apply path.

## Operator Flow

Run:

```text
python scripts/gates/catalog_admission.py --json
```

The gate is read-only. It reports all local refs, scores each entry, and emits
the fields validated by `schemas/catalog-entry.schema.json`. It has no external
telemetry and reports `irreversible_actions: 0`.

Use the result before importing any new skill, command, agent, hook, MCP server,
or dependency from `ref/`.
