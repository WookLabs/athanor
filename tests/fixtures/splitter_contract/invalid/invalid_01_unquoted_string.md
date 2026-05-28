# Plan (fixture: bare unquoted-string value — NOT a path/list)

## Subtasks

- [ ] **Subtask 1: Garbage value in files field**
  - task: Demonstrate that a bare non-path value is tolerated, not crashing.
  - files: not_a_path_or_list
  - verify: {type: none}
  - depends_on: []
  - execution_note: direct
  - classification_reason: malformed-value fixture for parser resilience
