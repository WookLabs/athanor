---
name: skill-without-provenance
description: Vendored skill body that intentionally omits the `<!-- Provenance:` HTML comment. Lint check vendored_skill_provenance_check should flag this.
allowed-tools: Bash, Read
---

# /athanor:skill-without-provenance

This is a fixture body simulating a vendored skill whose attribution
comment block was accidentally deleted during a refactor. The lint
check should detect that no upstream-citation HTML comment is present
within the first 60 lines of body and report a violation.

## Workflow

(intentionally minimal — fixture only)
