# P25 Package-Facing Knowledge Index Design

## Problem

P21-P24 split Athanor into clearer surfaces: runtime plugin, repo-local
development history, evaluation adapters, native runtime playbooks, and
reactive event fixtures. The remaining weak point is discoverability. A worker
or operator still has to infer the current runtime contract by scanning
README, CLAUDE.md, multiple docs, and historical plans.

That is too much surface for a package-facing entry point.

## Design

Add `docs/package-knowledge-index.md` as a short current index. It is not a
new source of truth for behavior. It is a map to the existing current source
docs and gates:

- runtime surface and root entry points;
- operator gate map;
- safety contracts;
- ship-profile boundary;
- freshness rule.

Add `scripts/gates/package_knowledge_index.py` to keep that map honest. The
gate is read-only and validates:

- required sections are present;
- current docs and gate scripts are linked;
- README.md and CLAUDE.md point back to the index;
- local links resolve inside the repository;
- development-history paths are not linked from the package-facing index;
- the index stays short;
- telemetry, mutation, and irreversible action counts stay zero.

## Boundary

The index must not link to:

- `docs/plans/**`;
- `docs/archive/**`;
- `docs/architecture/**`;
- `tests/**`;
- `ref/**`;
- `.github/**`;
- `.athanor/**`.

Those files remain useful repo-local engineering memory, but they are not the
first package-facing knowledge surface.

## Scoring Impact

This addresses the remaining `Knowledge surface freshness` gap:

- before P25: `9.25`, because current docs exist but are scattered;
- after P25: target `9.55`, because current runtime/operator knowledge has a
  gated, short, package-facing entry point.

## Non-Goals

- No deletion of historical docs.
- No packaging exclusions beyond the existing P21 recommendation.
- No runtime listener, telemetry, command execution, or mutation.
- No replacement of detailed operator docs.
