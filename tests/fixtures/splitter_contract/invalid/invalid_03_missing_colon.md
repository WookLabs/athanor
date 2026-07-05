# Plan (fixture: missing colon — malformed field declaration)

## Subtasks

- [ ] **Subtask 1: Files without colon (not a field declaration)**
  - task: Demonstrate that a line shape without the field colon is ignored.
  - files [scripts/hooks/pretool_dispatcher.py]
  - verify: {type: none}
  - depends_on: []
  - execution_note: direct
  - classification_reason: malformed-shape fixture for parser resilience
