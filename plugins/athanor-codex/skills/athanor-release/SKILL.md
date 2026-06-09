---
name: athanor-release
description: "Run Athanor's release ceremony in Codex: version bump, changelog, state rotation, test pin updates, and release-ready verification."
---

# Athanor Release

Use this when the user asks to prepare or ship an Athanor release. This is a
Codex-native release ceremony, not a Claude `Task` worker dispatch.

## Protocol

1. Read the requested target version, ship date, and CHANGELOG entry. If any
   of these are missing, ask before editing release files.
2. Inspect the repository release surface before editing. Do not assume files
   exist because older Athanor release contracts named them.
3. Perform the 5-file version bump when the release surface contains the full
   original Athanor contract:
   - `plugin.json`: top-level `version`.
   - `marketplace.json`: top-level `version`.
   - `athanor.json`: `$schema` URL version segment.
   - `templates/athanor.json`: `$schema` URL version segment.
   - `schemas/athanor-config.schema.json`: `$id` URL version segment.
4. If the current tree has a repo-local Codex marketplace instead of a root
   `marketplace.json`, update the actual marketplace file only when it carries
   a release version field. Do not invent a missing marketplace version.
5. Prepend the release section to `CHANGELOG.md`.
6. Rotate `docs/STATE.md`: move the previous `## Current Phase` content into
   previous/history context and create a new current phase for the target
   version.
7. Find and update test pins by searching for the previous version in schema,
   release smoke, manifest, and readiness tests. Treat "test pins" as release
   contract data, not optional cleanup.
8. Run:

```bash
python3 scripts/check_release_ready.py --ci
```

9. Report every changed file and the readiness result. If the gate fails, stop
   with the failing checks instead of calling the release ready.

## Editing Rules

- Read every target file before editing it.
- Make surgical edits. Do not reformat JSON or markdown outside the release
  fields and sections being changed.
- If a named 5-file version bump target is absent, report the exact missing
  file and whether the current release surface has an equivalent file.
- Do not change `.github/workflows/` unless the release request explicitly
  includes workflow changes.
- Do not tag, push, or publish unless the user asked for those actions or an
  accepted LFG pipeline reached the release step.

## Codex Constraints

- Do not claim Claude Task dispatch, Claude Stop hook verification, Claude
  PreToolUse enforcement, or Freeze enforcement.
- Do not claim a release is ready without the concrete
  `python3 scripts/check_release_ready.py --ci` result.
- Do not fabricate tags, GitHub releases, PR status, or marketplace status.
