# Plan (fixture: multi-file bracketed list)

## Subtasks

- [ ] **Subtask 1: Refactor hook runtime helpers**
  - task: Extract shared helpers from the hook runtime module.
  - files: [scripts/hooks/_athanor_hook_runtime.py, scripts/hooks/hook_state.py]
  - verify: {type: command, value: pytest tests/test_regression_hook_state_helpers.py}
  - depends_on: []
  - execution_note: test-aware
  - classification_reason: refactor across two files, behavior preserved
