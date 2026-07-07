# Runtime Conformance

The Cross-runtime conformance gate keeps Athanor's Claude Code plugin,
Codex companion, and hook catalog aligned without expanding runtime behavior.
It is a read-only verifier, not a generator.

The gate reads `docs/runtime-surface-contract.json`,
`hooks/catalog.json`, `hooks/hooks.json`, `.claude-plugin/plugin.json`, and
`plugins/athanor-codex/.codex-plugin/plugin.json`. It reports drift between
the machine-readable contract and the files shipped in this repository.

## Boundaries

- `hooks/catalog.json` remains the hook metadata source of truth.
- `hooks/hooks.json` remains the only runtime hook registration file.
- Enabled hook identity includes both the POSIX `command` and any Windows
  `command_windows` override, so cross-platform launch fixes cannot drift
  between the catalog and runtime manifest.
- `docs/runtime-surface-contract.json` defines expected distribution surfaces.
- The Codex companion at `plugins/athanor-codex` must stay hook-free,
  MCP-free, and app-free.
- `ce-test-browser` is a vendored Claude-only skill and must not be mirrored as
  `athanor-ce-test-browser`.
- The verifier never writes settings, manifests, hook files, or generated
  mirrors.

## CI

The validation workflow runs the Cross-runtime conformance gate before the
broad pytest suite. Failures mean a runtime surface changed without updating
the contract or the corresponding runtime artifact.
