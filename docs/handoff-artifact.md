# Handoff Artifact Contract

This document defines the compact handoff artifact used when Athanor work
crosses a session boundary, a context compaction, or an operator transfer. The
artifact is a small markdown record, not a new command surface.

## Location

Use the narrowest durable location that matches the work:

- Goal loop: `.athanor/loops/<loop-id>/handoff.md`
- Work session: `.athanor/sessions/<session-id>/handoff.md`
- Completed public archive: `docs/loops-completed/<loop-id>/handoff.md`

## Required Fields

Every handoff artifact must contain these fields:

- current goal: verbatim or ledger-linked goal statement.
- recent decisions: only decisions that affect the next action.
- active plan or work item: the exact plan item, work item id, or cycle target.
- latest run-log reference: path or id for the newest run log or receipt.
- relevant memory ids: stable Learner memory ids plus short source paths.
- resume command: the command or skill invocation that resumes the work.
- open risks: unresolved blockers, assumptions, or verification gaps.

## Format

```markdown
# Handoff: <goal-or-session-id>

## current goal
<one paragraph or link to loop.md>

## recent decisions
- <decision id/path>: <short effect>

## active plan or work item
<plan path and item number, work item id, or cycle target>

## latest run-log reference
<path or receipt id>

## relevant memory ids
- <stable_id> (<source_artifact_path>): <safe_to_inject_summary>

## resume command
<single command or skill invocation>

## open risks
- <risk, missing evidence, or blocked dependency>
```

## Rules

- Keep the artifact reference-first and compact; prefer links over pasted logs.
- Include only safe-to-inject summaries from Learner records.
- Do not introduce another registered agent for handoff writing.
- Do not treat this artifact as proof of completion; receipts and tests remain
  the evidence source.
