# Plan (fixture: multi-doc files, mixed extensions)

## Subtasks

- [ ] **Subtask 1: Release ceremony prose**
  - task: Update migration doc and changelog atomically.
  - files: [docs/migration.md, CHANGELOG.md]
  - verify: {type: check, value: docs build}
  - depends_on: []
  - execution_note: direct
  - classification_reason: prose-only doc edits
