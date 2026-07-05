# Plan (fixture: single-file bracketed list)

## Subtasks

- [ ] **Subtask 1: Single file edit**
  - task: Touch one source file with a trivial change.
  - files: [scripts/hooks/pretool_dispatcher.py]
  - verify: {type: command, value: pytest tests/test_regression_stop_hook_script.py}
  - depends_on: []
  - execution_note: test-aware
  - classification_reason: existing-behavior preserved, single source file
