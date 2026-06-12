# Freeze Allowlist Contract (v0.18.0 — Phase 1)

`/athanor:work` Step 0.6 builds a **per-session Plan-Scoped Freeze
Manifest** (the *freeze allowlist*) from the Subtasks block's `files:`
declarations. This document is the load-bearing prose contract referenced
by SKILL.md Step 0.6 and consumed by the v0.18.0 PreToolUse dispatcher +
freeze guard.

## Concept

**The problem.** Worker dispatch is a clean-context handoff. Executors
sometimes touch files outside the plan's declared scope — sometimes
legitimately (downstream discovery), more often by mistake (path typo,
wrong-file edit, scope creep). Pre-v0.18.0 the only defenses were
*advisory* prose (scope-drift skill, splitter `files:` declarations as
loose intent) and the leader-side multi-status review at result time.
Neither stops a bad write **before** it lands.

**The mechanism.** v0.18.0 introduces a Claude-tool-level allowlist. Per
session, the Splitter's per-subtask `files:` declarations are unioned
with a set of session-local defaults to produce
`.athanor/sessions/<id>/freeze-allowlist.json`. When
`athanor.json` `hooks.freeze.mode != "off"`, the PreToolUse dispatcher
reads this allowlist and rejects Claude-issued `Edit` / `Write` /
`MultiEdit` / `NotebookEdit` / scoped `Bash` writes whose destination
paths fall outside it.

**Posture.** Opt-in. The allowlist is **always built** (no config gate
on the builder — cheap stdlib step, no measurable cost), so a user
flipping `hooks.freeze.mode` from `"off"` to `"session"` later in the
session simply starts enforcing the allowlist that's already on disk.

## Builder: `scripts/work/build_freeze_allowlist.py`

Stdlib-only (same constraint as `scripts/hooks/*.py`). Exposes three
entry points:

- `parse_subtasks_files(plan_md_text: str) -> list[dict]` — parses the
  `## Subtasks` block of `plan.md`; extracts each subtask's `files:`
  declaration. Returns `[{subtask_id, files: list[str]}, ...]`. Handles
  both bullet-list shape (`- files: [a.py, b.py]`) and table-row shape.
  Missing `files:` for a subtask is **not an error** — it becomes an
  empty list and the allowlist falls back to defaults only.
- `build_allowlist(parsed: list[dict], session_id: str, extras: list[str]) -> dict`
  — composes the full allowlist as a dict with these keys:
  - `allowed_paths`: union of (a) all subtask `files:` entries (deduped,
    normalized to project-relative POSIX paths), (b) session defaults
    (see below), (c) user extras from
    `athanor.json` `hooks.freeze.allowedPaths`.
  - `session_id`: the session identifier (used by the guard for
    cross-checks against `transcript_path` ancestor).
  - `built_at`: ISO-8601 UTC timestamp.
  - `source`: dict noting which plan generated the allowlist
    (`plan_md_sha256`, subtask count).
- `write_allowlist(allowlist: dict, output_path: str) -> None` —
  atomic write via tempfile + rename (write to a sibling temp file,
  then `os.replace` into place). Target path is
  `.athanor/sessions/<id>/freeze-allowlist.json`.

### Default-included paths

Even with empty `files:` declarations, the allowlist always contains
these session-default entries (so the leader and workers can always
write session artifacts):

- `.athanor/sessions/<id>/...` — the active session directory
  (work-log.md, discoveries/, sub-plan artifacts).
- `.athanor/sessions/<id>/discoveries/**` — discovery briefs.
- `.athanor/lessons/**` — lessons system (`learner-cleaner.md` writes).
- `docs/v0.18.0-migration.md` — the v0.18.0 migration guide is a
  session-spanning legitimate-edit target.

### User extension

`athanor.json` `hooks.freeze.allowedPaths: list[str]` is unioned
into `allowed_paths` at build time. **Extras extend, never replace,**
the dynamic allowlist. This is the supported mechanism for users to
allow project-wide tooling paths (e.g., `CHANGELOG.md`, `STATE.md`)
without amending plan.md.

## Subtask `files:` parser contract (load-bearing for Freeze)

v0.18.0 makes the Splitter `files:` field **load-bearing**. The
following invariants are pinned by `tests/test_regression_v018_splitter_files_contract.py`
(ST-1.4, separate subtask):

- Field name is exactly `files:` (not `paths:` or `targets:`).
- Value is a YAML/markdown list of strings — bullet list under the
  field name, or inline `[a, b, c]`, or table cell.
- Each entry is a project-relative POSIX path or glob (`**/*.py` is
  allowed; the builder normalizes but does not expand globs — the
  guard does the glob match at evaluation time).
- Absent / empty `files:` is treated as "no declared scope for this
  subtask" — allowlist falls back to defaults only for that subtask's
  contribution. Builder MUST NOT crash.
- Splitter changes that rename the field or change the list shape
  break Freeze; the contract test enforces this so future Splitter
  edits surface the dependency.

## Output: `.athanor/sessions/<id>/freeze-allowlist.json`

Example shape (truncated):

```json
{
  "session_id": "2026-05-28-005",
  "built_at": "2026-05-28T22:58:01Z",
  "allowed_paths": [
    "skills/work/SKILL.md",
    "skills/work/references/freeze.md",
    "tests/test_regression_v018_freeze_step_06.py",
    ".athanor/sessions/2026-05-28-005/**",
    ".athanor/lessons/**",
    "docs/v0.18.0-migration.md"
  ],
  "source": {
    "plan_md_sha256": "ab12...",
    "subtask_count": 7
  }
}
```

The guard reads this JSON only; it does not re-build the allowlist at
evaluation time. This separates build-time semantics (subject to plan
revision) from evaluation-time semantics (must be deterministic per
PreToolUse call).

## Dispatcher integration: `pretool_dispatcher.py` → `freeze_guard`

The v0.18.0 PreToolUse dispatcher is a single outer entry point.
Sequencing matters (locked by Phase 2 dispatcher contract test):

1. Read PreToolUse payload from stdin.
2. Try to load `athanor.json`. Result is `None | dict`.
3. **Invoke `kernel_guard.evaluate(payload, config=None or loaded)` FIRST.**
   Kernel guard runs unconditionally (even on missing config — defaults
   to `profile=standard` per v0.16.0 behavior). If exit 2, propagate
   immediately — freeze never runs after a kernel reject.
4. After kernel guard returns 0, the dispatcher consults config for
   freeze.
5. If config is `None` → exit 0 silently. Freeze cannot run without
   config; safe fail-open since freeze is opt-in.
6. If `config.hooks.freeze.mode == "off"` (default) → exit 0 silently.
7. Otherwise, resolve `session_id` (from `transcript_path` ancestor or
   `.athanor/sessions/active` cursor) and call
   `read_freeze_allowlist(session_id) -> dict | None`. None → exit 0
   silently (no allowlist on disk; nothing to enforce against).
8. Invoke `freeze_guard.evaluate(payload, config, allowlist)`. On
   violation, exit 2 with stderr explaining which path fell outside
   the allowlist and pointing the user at the legitimate-edit
   workflow.

This sequencing — **kernel guard FIRST, freeze SECOND, fail-closed on
missing config only for kernel, fail-open on missing config for freeze**
— is the v0.18.0 dispatcher invariant (Codex review of Plan A win).

## Bash write-pattern gating (conservative)

Freeze gates the Claude `Edit` / `Write` / `MultiEdit` / `NotebookEdit`
tools fully (the destination path is the gated path — `file_path` for
Edit/Write/MultiEdit, `notebook_path` for NotebookEdit). For `Bash`, freeze applies
a **conservative pattern match** against the command string. Gated
patterns:

- `> file` — redirect overwrite. Match: `>\s*(\S+)`.
- `>> file` — redirect append. Match: `>>\s*(\S+)`.
- `tee file` — `tee` write target. Match: `tee\s+(\S+)`.
- `sed -i FILE` — in-place sed. Match: `sed\s+-i(?:\s+\S+)?\s+(\S+)`.
- `mv X Y` — move (destination `Y` gated). Match: `mv\s+\S+\s+(\S+)`.
- `cp X Y` — copy (destination `Y` gated). Match: `cp\s+\S+\s+(\S+)`.

If the extracted destination path resolves outside the allowlist, the
guard rejects with exit 2 + stderr. Conservative patterns mean
quoted-path or heavily-piped Bash may slip through (false negative);
this is the documented honesty residual.

### D2 residual — subprocess writes NOT gated

**Subprocess writes are explicitly NOT gated by Freeze.** Examples:

- `python -c "open('out.txt', 'w').write('x')"` — writes via subprocess
  Python.
- `make build` — Makefile-driven writes to `build/`, `dist/`, etc.
- `codex exec ...` — Codex CLI dispatches that produce files.
- `git apply patch` — `git`-mediated file writes.
- `npm run ...`, `cargo build`, etc. — toolchain-driven writes.

These bypass the freeze guard because the destination path is not
syntactically visible in the Bash command string. v0.18.0 CHANGELOG
explicitly labels this surface as **"Claude file-tool allowlist"** —
NOT "editing envelope" — to set honest expectations. Users running
`/athanor:lfg` should be aware that the LFG pipeline includes Bash
subprocess dispatches (Codex worker, test runners) whose writes are
outside the freeze envelope.

A future v0.19.0 PostToolUse sniffer pass may close part of this gap
by inspecting `tool_response.files_changed` style fields after Bash
returns. This is the same forward-compat anchor as the Spec-then-TDD
v0.19.0 evidence-bound enforcement work (see
`references/spec-then-tdd-handler.md` §"v0.19.0 — Evidence-Bound
Enforcement (planned)"). Not promised in v0.18.0.

## Opt-in: `athanor.json` `hooks.freeze`

```json
{
  "hooks": {
    "freeze": {
      "mode": "off",
      "allowedPaths": []
    }
  }
}
```

- `mode`: one of `"off"` (default — gate is silent, freeze evaluator
  never runs) or `"session"` (freeze evaluator runs on every
  PreToolUse for Claude `Edit` / `Write` / `MultiEdit` / `NotebookEdit` /
  scoped `Bash`). Future modes (`"strict"`, `"per-subtask"`) deferred to
  v0.18.x and v0.19.0.
- `allowedPaths`: list of project-relative paths or globs to
  union into every session's allowlist. Useful for project-wide
  artifacts the plan doesn't always re-declare (`CHANGELOG.md`,
  `docs/STATE.md`).

**Default is `"off"`.** A user who never edits `athanor.json` sees
no freeze behavior — the v0.18.0 surface is invisible to them. The
allowlist is still built (cheap, no side effect) so the user can flip
the mode on mid-session and start enforcing immediately.

## Legitimate-edit workflow

When a worker legitimately needs to write outside the declared
allowlist (downstream discovery, scope expansion), three paths exist:

1. **Edit `freeze-allowlist.json` directly.** Quick, session-local,
   no plan amendment. Trade-off: bypasses the plan-as-source-of-truth
   contract.
2. **Amend `plan.md` and re-run Splitter.** The proper path —
   Splitter re-validates, builder re-runs, allowlist regenerates.
   This keeps plan.md as the source of truth.
3. **Flip `hooks.freeze.mode` to `"off"`.** Disables enforcement for
   the rest of the session. Heavy-handed but always available as the
   escape hatch.

The leader does NOT auto-resolve allowlist violations. Per Thin
Leader contract, the worker reports the violation as a `blocked`
multi-status (see `references/multi-status.md`); the user picks
which legitimate-edit path to take.

## What Freeze does NOT do

- Does NOT gate subprocess writes (D2 — explicit).
- Does NOT gate the leader's own session-directory writes
  (`.athanor/sessions/<id>/...` is in defaults; leader operates as a
  privileged actor within the session dir per Thin Leader exceptions
  in CLAUDE.md §"Core Principle").
- Does NOT change `/athanor:plan` or `/athanor:work` semantics on its
  own — Freeze is a *runtime gate*, not a planner classifier.
- Does NOT auto-extend the allowlist on worker-reported "need to
  touch X" — the user must take one of the three legitimate-edit
  paths above.
- Does NOT replace scope-drift detection. Scope drift is plan-vs-
  reality at result time; Freeze is request-vs-allowlist at PreToolUse
  time. They cover different windows.

## Forward references

- Phase 2 dispatcher contract test:
  `tests/test_regression_v018_pretool_dispatcher_sequencing.py`
  (separate subtask) — pins kernel-FIRST / freeze-SECOND ordering.
- Phase 3 freeze guard evaluator:
  `scripts/hooks/freeze_guard.py` (separate subtask) — implements the
  per-tool gating logic described above.
- v0.18.1 staged worktree: contains the worktree contamination work
  (admission criteria in `docs/STATE.md` §v0.18.x roadmap).
- v0.19.0 evidence-bound enforcement: PostToolUse sniffer may close
  part of the subprocess-write residual.
