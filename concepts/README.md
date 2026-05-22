# concepts/ — Inventory-Only Provenance Directory

## Purpose

This directory is an **inventory-only** record of which conceptual elements from vendored upstream skills survived the v0.12.0 concept-kernel cutover into athanor-native skills. Each non-README file in this directory documents one lifted concept: where it came from, where it now lives in athanor, what was kept, and what was deliberately discarded. The directory serves traceability and license-attribution needs; it does not participate in runtime behavior.

## What's here

Per-concept `.md` files, each following a fixed shape (Source / Target / License / Author / commit-hash placeholder, plus "Why this concept survives v0.12.0", "What was lifted", "What was NOT lifted", "Verification"). Files map 1:1 onto distinct concepts that crossed from upstream (`compound-engineering@3.8.3`, `superpowers@5.1.0`) into athanor-native skill bodies during the v0.12.0 cutover. The TBD commit-hash placeholders in each file will be backfilled post-merge once the v0.12.0 ship commit hash is known. Cross-reference: `docs/architecture/v012-concept-absorption.md` carries the architectural rationale and decision log; this directory is the per-concept ledger.

## What's NOT here

This is **not** a templating engine. The files here are not consumed at runtime by any skill, hook, or script. There is no JSON manifest, no schema validator, no auto-generator that produces athanor-native skill prose from these inventory files. Concept ownership lives in the target skill body (e.g., `skills/review/SKILL.md` §"Personas"); this directory only records the lineage. If a concept changes in a target skill body, the corresponding `concepts/*.md` file is updated by hand to reflect the new shape — drift is acceptable and is closed by routine maintenance, not by a generator. Sub-agent files, language-specific personas, and procedural walkthroughs from upstream are explicitly out of scope and listed under each file's "What was NOT lifted" section.
