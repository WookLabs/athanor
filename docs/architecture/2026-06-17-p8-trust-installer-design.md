# P8 Trust-Aware Installer Apply Design

Date: 2026-06-17

## Goal

Extend the P4 read-only hook install planner into a reversible, trust-aware
installer for Claude settings. P8 should let users apply or remove Athanor hook
settings only when the catalog entry is installable, source hashes have been
reviewed, and the target settings file can be changed without clobbering user
hooks.

## Current State

`scripts/gates/hook_install_dry_run.py` already reads:

- `hooks/catalog.json`
- `hooks/hooks.json`
- optional Claude settings JSON

It reports:

- enabled runtime hooks that are already present;
- installable hooks that would be added;
- capture-only or disabled hooks that are blocked;
- settings conflicts that would clobber existing user hooks.

It intentionally never writes settings. This is the correct P4 boundary but it
leaves Trust/install UX below the 9.5 target.

## Requirements

P8 must add:

- apply and remove operations;
- hash/source trust state;
- no-clobber conflict handling;
- capture-only hooks blocked from default apply;
- atomic settings writes;
- rollback-capable backups;
- dry-run and apply/remove reports that share one schema.

## Non-Goals

P8 does not:

- enable any capture-only hook by default;
- promote lifecycle candidates without live-redacted evidence;
- write plugin manifests;
- bypass Claude or Codex trust policy;
- infer user trust from the current repository alone.

## Trust Model

The installer uses a local trust state file:

```bash
.athanor/hook-installer-trust.json
```

Tests and operators can override it with `--trust-state`.

Trust state shape:

- `schema_version`: `1`
- `trusted_hooks`: object keyed by hook id
- each trusted hook records:
  - `status`: `trusted`
  - `command_hash`: hash of the catalog command string
  - `source_hashes`: hashes of resolved local source files referenced by the
    command
  - `reviewed_at`: operator-supplied or generated timestamp
  - `reviewer`: free-form local reviewer id

An apply operation is allowed only when the current catalog command hash and
resolved source hashes match trust state. A mismatch returns
`status=blocked` with `reason=trust hash mismatch`.

## Hash Inputs

For each catalog entry:

1. Hash the exact command string as `sha256:<hex>`.
2. Resolve `${CLAUDE_PLUGIN_ROOT}/...` paths in the command against
   `repo_root`.
3. Hash each resolved existing local file as `sha256:<hex>`.
4. Record missing source files as a trust failure.

This keeps trust scoped to actual local executable content, not only catalog
metadata.

## Operations

### Dry Run

Default behavior remains read-only:

```bash
python scripts/gates/hook_install_dry_run.py --json
```

Dry-run output gains trust fields but still writes nothing.

### Apply

Apply writes only `would-add` actions whose trust state is valid:

```bash
python scripts/gates/hook_install_dry_run.py \
  --mode apply \
  --trust-state .athanor/hook-installer-trust.json \
  --settings ~/.claude/settings.json \
  --json
```

Apply behavior:

- create settings parent directory if missing;
- preserve unrelated settings keys;
- add exact catalog hook entries;
- refuse event-level clobber if non-matching hooks already exist;
- write a timestamped backup before replacement when settings exists;
- write temp file then atomic replace;
- report backup and settings paths in `writes`.

### Remove

Remove deletes only exact Athanor catalog hook entries:

```bash
python scripts/gates/hook_install_dry_run.py \
  --mode remove \
  --settings ~/.claude/settings.json \
  --json
```

Remove behavior:

- remove exact `(event, matcher, command)` matches;
- preserve unrelated hooks in the same event;
- remove empty event arrays;
- preserve unrelated settings keys;
- write a backup before replacement when settings changes;
- report `already-absent` for hooks not found.

## Report Schema

All modes return:

- `schema_version`: `2`
- `status`: `ok` or `error`
- `mode`: `dry-run`, `apply`, or `remove`
- `summary`: status counts
- `actions`: per-hook actions with trust fields
- `writes`: files changed or backup paths
- `error`: only for fatal errors

Dry-run can remain schema v1 until the implementation lands, but P8 completion
requires schema v2 for shared apply/remove reports.

## Safety Rules

- Capture-only entries never apply.
- Disabled entries never apply.
- Missing command never applies.
- Missing or mismatched trust state blocks apply.
- Existing non-matching hooks for the same event block apply.
- Remove only deletes exact Athanor catalog entries.
- Invalid JSON never rewrites the target file.

## Acceptance Criteria

P8 is complete when:

- trust state schema and hash builder are tested;
- apply writes trusted installable hooks atomically;
- apply creates backups and never clobbers unrelated settings;
- apply blocks capture-only and untrusted hooks;
- remove deletes only exact Athanor hook entries;
- dry-run/apply/remove share one report shape;
- docs explain trust review, apply, remove, backup, and rollback behavior;
- CI or release story locks the installer regression tests.
