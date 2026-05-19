<!-- Provenance:
  upstream: ce@3.8.3 assets/resolution-template.md
  source-commit: vendored at athanor v0.10.0 release time from ce@3.8.3
  upstream-url: https://github.com/EveryInc/compound-engineering-plugin
  license: MIT (Copyright (c) 2025 Kieran Klaassen / Every Inc)
  modifications: none — verbatim copy under T2 vendoring pattern; provenance block inserted after frontmatter only
  t0-t1-disproof:
    Why not T0/T1? ce is shipped as a Claude Code plugin (T3 marketplace
    listing). T0 (install companion) is unavailable for per-skill reference files.
    T1 (require dependency) is reserved pending Claude Code plugin-spec `requires`
    field support. T2 (vendor) is the only feasible tier today.
-->

# Resolution Templates

Choose the template matching the problem_type track (see `references/schema.yaml`).

---

## Bug Track Template

Use for: `build_error`, `test_failure`, `runtime_error`, `performance_issue`, `database_issue`, `security_issue`, `ui_bug`, `integration_issue`, `logic_error`

<!-- YAML safety: array items (symptoms, applies_when, tags, related_components) starting with ` [ * & ! | > % @ ? or containing ": " must be wrapped in double quotes. See references/yaml-schema.md > "YAML Safety Rules". -->

```markdown
---
title: [Clear problem title]
date: [YYYY-MM-DD]
category: [docs/solutions subdirectory]
module: [Module or area]
problem_type: [schema enum]
component: [schema enum]
symptoms:
  - [Observable symptom 1]
root_cause: [schema enum]
resolution_type: [schema enum]
severity: [schema enum]
tags: [keyword-one, keyword-two]
---

# [Clear problem title]

## Problem
[1-2 sentence description of the issue and user-visible impact]

## Symptoms
- [Observable symptom or error]

## What Didn't Work
- [Attempted fix and why it failed]

## Solution
[The fix that worked, including code snippets when useful]

## Why This Works
[Root cause explanation and why the fix addresses it]

## Prevention
- [Concrete practice, test, or guardrail]

## Related Issues
- [Related docs or issues, if any]
```

---

## Knowledge Track Template

Use for: `best_practice`, `documentation_gap`, `workflow_issue`, `developer_experience`

<!-- YAML safety: array items (symptoms, applies_when, tags, related_components) starting with ` [ * & ! | > % @ ? or containing ": " must be wrapped in double quotes. See references/yaml-schema.md > "YAML Safety Rules". -->

```markdown
---
title: [Clear, descriptive title]
date: [YYYY-MM-DD]
category: [docs/solutions subdirectory]
module: [Module or area]
problem_type: [schema enum]
component: [schema enum]
severity: [schema enum]
applies_when:
  - [Condition where this applies]
tags: [keyword-one, keyword-two]
---

# [Clear, descriptive title]

## Context
[What situation, gap, or friction prompted this guidance]

## Guidance
[The practice, pattern, or recommendation with code examples when useful]

## Why This Matters
[Rationale and impact of following or not following this guidance]

## When to Apply
- [Conditions or situations where this applies]

## Examples
[Concrete before/after or usage examples showing the practice in action]

## Related
- [Related docs or issues, if any]
```
