# Plan (fixture: long path with hyphens/underscores/dots)

## Subtasks

- [ ] **Subtask 1: Extend runtime helper with new entry point**
  - task: Add a new helper exposed via the hook runtime module.
  - files: [scripts/hooks/_athanor_hook_runtime.py]
  - verify: {type: command, value: pytest tests/test_regression_v017_hook_runtime.py}
  - depends_on: []
  - execution_note: spec-then-tdd
  - classification_reason: new helper contract on security-adjacent runtime
  - acceptance_criteria:
    - MUST helper accepts session_id and returns dict-or-None
    - MUST existing v0.17.0 callers unbroken
