# Plan (fixture: empty array — subtask declares no files)

## Subtasks

- [ ] **Subtask 1: Run a tool, no file edits**
  - task: Invoke a read-only diagnostic; no project files touched.
  - files: []
  - verify: {type: command, value: scripts/check_release_ready.py --dry-run}
  - depends_on: []
  - execution_note: direct
  - classification_reason: read-only diagnostic, no files modified
