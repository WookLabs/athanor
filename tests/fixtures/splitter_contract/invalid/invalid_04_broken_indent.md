# Plan (fixture: broken indentation in subtask block)

## Subtasks

- [ ] **Subtask 1: Mixed indentation that breaks the bullet block**
  - task: Demonstrate that bad indentation degrades gracefully.
- files: [scripts/hooks/stop_verify_claims.py]
  - verify: {type: none}
  - depends_on: []
  - execution_note: direct
  - classification_reason: indent-break fixture for parser resilience
