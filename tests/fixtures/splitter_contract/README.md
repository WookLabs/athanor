# Splitter `files:` Field Parser Contract Fixtures (v0.18.0 R-B4)

Lock fixtures for the Splitter `files:` field parser contract. Consumed by
`tests/test_regression_v018_splitter_files_contract.py`.

## Why this exists

v0.18.0 introduces `scripts/work/build_freeze_allowlist.py` (S1.2), which
parses `## Subtasks` blocks of `.athanor/sessions/<id>/plan.md` and extracts
each subtask's `files:` declaration to build the dynamic Freeze allowlist
JSON consumed by `scripts/hooks/freeze_guard.py`.

This makes the Splitter `files:` declaration **load-bearing** — silent
format drift breaks Freeze. R-B4 of the v0.18.0 plan mandates a contract
test to lock the field shape.

## Contract (Splitter output shape)

Canonical bullet-list form (per `skills/work/references/splitter.md`
Output Format):

```
- [ ] **Subtask N: {title}**
  - task: {what to do}
  - files: [{file paths}]
  - verify: {type: command|check|review|none, value: ...}
  - depends_on: []
  - execution_note: {spec-then-tdd|test-aware|direct}
  - classification_reason: {one-line descriptive reason}
```

### `files:` field — accepted forms (parser MUST handle)

1. **Bracketed list, single entry**: `files: [single/path.py]`
2. **Bracketed list, multi-entry**: `files: [path1.py, path2.py]`
3. **Bracketed list, empty**: `files: []`
4. **Bracketed list, glob entries**: `files: [src/**, tests/**]`
5. **Bare path** (single, no brackets): `files: path/to/file.py`
6. **Field omitted entirely** (subtask has no `files:` line at all)
7. **Long paths with hyphens/underscores/dots** preserved verbatim
8. **Mixed file types** (e.g., `.py`, `.md`) in one list

### `files:` field — rejected forms (parser MUST handle gracefully)

Graceful handling = return empty `files: []` for that subtask (or skip
the subtask cleanly) + emit a warning. Parser MUST NOT raise / crash.

1. **Bare unquoted string that looks like neither a path nor a list**:
   `files: not_a_path_or_list` — treat as bare path (Splitter shouldn't
   emit this, but the parser shouldn't crash).
2. **Empty value with no array**: `files:` (no value after colon).
3. **Missing colon** (malformed YAML-ish): `files [a, b]` — not a valid
   field declaration; parser must NOT match this as a files entry.
4. **Mixed indentation** breaking the parent subtask block — parser
   either skips the subtask or returns empty for it.

## Layout

```
tests/fixtures/splitter_contract/
  README.md                  ← this file (contract documentation)
  valid/
    valid_01_single_file.md
    valid_02_multi_file.md
    valid_03_bare_path.md
    valid_04_glob_patterns.md
    valid_05_empty_array.md
    valid_06_no_files_field.md
    valid_07_multi_doc.md
    valid_08_long_path.md
  invalid/
    invalid_01_unquoted_string.md
    invalid_02_empty_value.md
    invalid_03_missing_colon.md
    invalid_04_broken_indent.md
```

Each fixture is a single `plan.md` snippet with one or two subtask blocks
exercising the named shape. Header preamble is intentionally minimal so
the fixture focuses on the subtask-block parsing surface.

## Pin-stable invariant

If the Splitter output format ever changes such that any of the
`valid_*.md` fixtures no longer parse — or any of the `invalid_*.md`
fixtures suddenly do parse — `test_regression_v018_splitter_files_contract.py`
WILL fail. This is the desired behavior: any format drift requires an
explicit, reviewed update to both the fixtures AND the parser.
