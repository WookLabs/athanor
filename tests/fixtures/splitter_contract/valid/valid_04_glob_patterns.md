# Plan (fixture: glob patterns preserved verbatim)

## Subtasks

- [ ] **Subtask 1: Apply codemod across two trees**
  - task: Run a sweeping codemod over src/ and tests/.
  - files: [src/**, tests/**]
  - verify: {type: command, value: pytest tests/}
  - depends_on: []
  - execution_note: spec-then-tdd
  - classification_reason: new behavior introduced across glob-matched trees
  - acceptance_criteria:
    - MUST every file under src/** retains parseable AST
    - MUST tests/ suite green post-codemod
