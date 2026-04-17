# Contributing to Athanor

## Structure

- `skills/` — SKILL.md files define leader protocols (the actual implementation)
- `agents/` — Agent reference docs (keep in sync with SKILL.md dispatch prompts)
- `docs/` — Design, conventions, roadmap, state tracking
- `.claude-plugin/plugin.json` — Plugin manifest

## Adding a Skill

1. Create `skills/{name}/SKILL.md` with frontmatter (name, description)
2. Follow the Thin Leader pattern — leader dispatches, workers execute
3. Use ATHANOR_RESULT format for worker responses
4. Update CLAUDE.md commands table

## Conventions

See `docs/CONVENTIONS.md` for dispatch packet format, session file I/O,
discovery file naming, and lesson file conventions.

## Testing

Test with: `claude --plugin-dir /path/to/athanor -p "/athanor:{skill} {test input}"`

## Vendoring vs. Installing (Contribution Gate)

When proposing a PR that adds a vendored file under `skills/`, the PR description MUST answer:

> Why not require an installable companion plugin instead of vendoring this skill?

This gate exists because vendoring accumulates drift debt (NOTICE.md maintenance, license re-attribution on upstream changes, manual sync). Installable companions decouple athanor from upstream cadence.

### Tier ordering (T0 highest preference, T2 lowest)

| Tier | Mechanism | When appropriate |
|------|-----------|------------------|
| T0   | Install — declare prerequisite via `/athanor:setup` audit + README mention | Source is published as a Claude Code plugin via a marketplace |
| T1   | Require-and-wire — declare via `requires` field if/when Claude Code plugin spec adds support | (Reserved for future) |
| T2   | Vendor — copy in, add NOTICE attribution, add provenance metadata | Source has no marketplace presence (T3 in the dedup ledger), or upstream is unmaintained |

A PR that vendors must demonstrate that T0 and T1 are infeasible. See `docs/DEPENDENCIES.md` for current vendored exceptions and the rationale recorded for each.

## Pre-release Validation

Before creating a release tag, run:

```
claude plugin validate .claude-plugin/plugin.json
claude plugin validate .claude-plugin/marketplace.json
```

Both MUST exit 0. Note: `.claude-plugin/plugin.json` is the path that traverses hook schemas (verified empirically in v0.6.1 Phase 0 discovery). A repo-root invocation (`claude plugin validate .`) targets `marketplace.json` only and will NOT surface hook schema errors.

Additionally, before tagging, run one fresh Claude Code session with `--plugin-dir <repo>` and confirm the plugin loads without errors in `claude plugin list`. Save a transcript snippet to the release session folder as `live-session-evidence.md`. This evidence is a blocking prerequisite for push.

### `live-session-evidence.md` template

The file MUST contain all three sections below. Missing any section = not valid evidence.

```markdown
# Live session evidence — vX.Y.Z

## 1. Plugin loads clean
Paste the output of `claude plugin list` or the `/plugin` TUI showing
the athanor plugin with Status: Enabled and **zero** "Failed to load"
or "Duplicate" errors.

## 2. Stop hook fires
Paste a turn where the active model made a completion claim and the
`verification-before-completion` skill was invoked on Stop. Include
the skill invocation line and at least one verification step output.

## 3. Skill dispatch sanity
Paste the result of one `/athanor:<skill>` command completing end-to-end
with no "Hook load failed" or manifest-schema errors.
```

Rationale: the Duplicate-hooks regression (v0.6.2) shipped because neither
CI nor a human checker ever observed the plugin actually loading. Static
schema validation is necessary but not sufficient; runtime-load evidence
closes that gap.
