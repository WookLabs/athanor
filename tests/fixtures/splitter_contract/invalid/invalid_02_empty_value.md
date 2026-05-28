# Plan (fixture: empty value after colon)

## Subtasks

- [ ] **Subtask 1: Empty files value (no array, no path)**
  - task: Demonstrate handling of an empty value with no list shape.
  - files:
  - verify: {type: none}
  - depends_on: []
  - execution_note: direct
  - classification_reason: empty-value fixture for parser resilience
