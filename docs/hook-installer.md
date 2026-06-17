# Hook Installer

P8 extends the original read-only hook install planner into a reversible,
trust-aware settings installer. The command name remains
`scripts/gates/hook_install_dry_run.py` for compatibility, but the report shape
now supports `dry-run`, `apply`, and `remove` modes.

## Boundary

The installer reads:

- `hooks/catalog.json`;
- `hooks/hooks.json`;
- an optional Claude settings file;
- an optional hook trust-state file.

It never enables `capture-only` or `disabled` catalog entries through apply
mode. It never removes arbitrary user hooks. Remove mode only deletes exact
Athanor catalog command entries.

## Dry Run

Dry-run is the default and remains read-only:

```bash
python scripts/gates/hook_install_dry_run.py --json
```

The explicit equivalent is:

```bash
python scripts/gates/hook_install_dry_run.py --mode dry-run --json
```

The schema v2 report includes:

- `mode`;
- `summary`;
- `actions`;
- `writes`;
- `command_hash`;
- `source_hashes`;
- `missing_sources`;
- `trust_status`;
- `trust_reason`.

Dry-run always emits `writes: []`.

## Trust Review

Apply mode requires a trust-state file. The default path is:

```bash
.athanor/hook-installer-trust.json
```

The trust state follows `schemas/hook-installer-trust.schema.json`:

```json
{
  "schema_version": 1,
  "trusted_hooks": {
    "stop-verify-claims": {
      "status": "trusted",
      "command_hash": "sha256:...",
      "source_hashes": [
        {
          "path": "scripts/hooks/stop_verify_claims.py",
          "sha256": "sha256:..."
        }
      ],
      "reviewed_at": "2026-06-17T00:00:00Z",
      "reviewer": "local-operator"
    }
  }
}
```

Review flow:

1. Run dry-run and inspect the hook command and source paths.
2. Review the referenced local files.
3. Copy the current `command_hash` and `source_hashes` into trust state.
4. Run apply with `--trust-state`.

If the command or source hash changes later, apply mode blocks the action with
a trust mismatch instead of silently installing it.

## Apply

Apply writes only trusted, installable `would-add` actions:

```bash
python scripts/gates/hook_install_dry_run.py \
  --mode apply \
  --settings ~/.claude/settings.json \
  --trust-state .athanor/hook-installer-trust.json \
  --json
```

Apply behavior:

- preserves unrelated settings keys;
- creates the settings parent directory when needed;
- refuses to clobber existing non-matching hooks for the same event;
- blocks untrusted hooks;
- blocks capture-only and disabled hooks;
- writes a timestamped backup before replacing an existing settings file;
- writes a temp file and atomically replaces the target settings file.

## Remove

Remove deletes only exact Athanor catalog command entries:

```bash
python scripts/gates/hook_install_dry_run.py \
  --mode remove \
  --settings ~/.claude/settings.json \
  --json
```

Remove behavior:

- preserves unrelated hooks in the same event;
- removes empty event arrays;
- preserves unrelated settings keys;
- writes a timestamped backup when settings changed;
- reports `already-absent` and writes nothing when no exact entry is present;
- exits without rewriting when settings JSON is invalid.

## Rollback

When apply or remove changes an existing settings file, the report includes a
backup entry:

```json
{
  "kind": "backup",
  "path": "/path/to/settings.json.bak-20260617T000000000000Z"
}
```

Rollback is a file restore:

```bash
cp /path/to/settings.json.bak-20260617T000000000000Z ~/.claude/settings.json
```

On Windows PowerShell:

```powershell
Copy-Item -LiteralPath C:\path\settings.json.bak-20260617T000000000000Z `
  -Destination $HOME\.claude\settings.json
```

Use the exact backup path from the report.
