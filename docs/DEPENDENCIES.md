# Athanor Dependencies & Companion Policy

This document records athanor's dependency posture: vendored exceptions, recommended companions, version-tested matrix, intent-source contract, and the installer-first contribution gate.

## Vendored Skills (Frozen Exceptions)

Athanor's general policy is to **prefer installable companions over vendoring** (see Installer-first Contribution Gate below). The following vendored skills are **permanent exceptions** for documented reasons:

| Skill | Source | Rationale | Long-term posture |
|-------|--------|-----------|-------------------|
| `verification-before-completion` | superpowers v5.0.7 | Stop hook must have a guaranteed local target. Skill is small (~140 lines); drift cost minimal. (Decision #5, plan synthesis 2026-04-14) | **Permanent** |
| `scope-drift` | claude-octopus (SHA `3c260845...`) | Source repo (claude-octopus) is T3 — no marketplace presence. Vendor is the only path. (Pilot PR1b 2026-04-14) | **Permanent** |

## Recommended Companion Plugins

| Plugin | Source | Tested version | Required? |
|--------|--------|----------------|-----------|
| superpowers | `claude-plugins-official` marketplace | 5.0.7 | No (recommended) |

Install via `/plugin install superpowers@claude-plugins-official`. Run `/athanor:setup` to audit.

## Intent-Source Contract (scope-drift skill)

The `scope-drift` skill compares working-tree changes against the canonical plan-of-record. The plan-of-record is determined by:

1. **Latest session selection**: lexicographic-descending sort of `.athanor/sessions/{YYYY-MM-DD}-{NNN}/` directories; pick first.
2. **File precedence**: within selected session, try `plan.md > deep-plan.md > lite-plan.md`; first match wins.
3. **Plan-revision rule**: latest mtime of the chosen file wins. Override: `canonical: true` YAML frontmatter pins a specific revision.
4. **Self-reference exclusion** (excluded from drift scan):
   - `.athanor/sessions/**/*`
   - `.athanor/lessons/**/*`
   - `.athanor/discoveries/**/*`

Full contract: see session 2026-04-14-001 `pr1b-discovery.md` section (e).

## Installer-first Contribution Gate

When proposing a new vendored skill via PR, the contribution MUST justify why an installable companion is not used instead.

Tier ordering (T0 highest, T2 lowest preference):
- **T0**: Install available — declare prerequisite via `/athanor:setup` audit + README mention
- **T1**: Require-and-wire — declare via `requires` field if/when Claude Code plugin spec adds support
- **T2**: Vendor — copy file in, add NOTICE attribution, add provenance metadata

Vendoring (T2) requires explicit answer to "Why not T0/T1?" in the PR description. See `CONTRIBUTING.md` "Vendoring vs. Installing" section.

## Version Compatibility Matrix

| Companion | Min tested | Max tested | Notes |
|-----------|-----------|-----------|-------|
| superpowers | 5.0.7 | 5.0.7 | Pinned at v0.5.0/v0.6.0 release time. Newer versions likely work but not validated. |

## Provenance Metadata Convention

Every vendored skill file under `skills/` MUST carry a `<!-- Provenance: ... -->` block at the top with:
- `upstream`: source repo path
- `source-commit`: pinned SHA
- `license`: SPDX-style license string with copyright
- `modifications`: list of local changes

See `skills/scope-drift/SKILL.md` for the canonical format.
