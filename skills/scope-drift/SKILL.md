---
name: scope-drift
description: Use on demand to detect scope drift between current branch changes and the canonical plan-of-record in the latest athanor session. Triggers on user-invoked phrases "check scope drift", "scope check", "did I drift", "drifted from plan", "still on track", "off-track", "anything off-track", "스코프 드리프트 체크", "스코프 체크", "드리프트 확인", "계획 벗어났나", and equivalents. Does NOT auto-fire on completion claims or Stop events — on-demand pilot.
---

<!--
Provenance:
  upstream: ref/claude-octopus/skills/skill-scope-drift/SKILL.md
  source-commit: 3c260845f136cc6e3398a1d87ca5fb053a52b1d0
  license: MIT (Copyright (c) 2026 nyldn)
  modifications:
    - Removed upstream activation banners and plugin branding from skill body
    - Genericized host-command references to athanor equivalents (on-demand only)
    - Rewrote upstream namespaced path references to athanor intent-source glob
    - Added SELF_REFERENCE_EXCLUDES constant for athanor session/lesson/discovery artifacts
    - Dropped Dev/Knowledge context taxonomy (no athanor equivalent); replaced with "no diff" skip condition
    - Set description frontmatter triggers to on-demand only (per pilot wiring decision)
-->

# Scope Drift Detection

Compares the actual branch diff against stated intent (canonical plan + PR body + commit messages) to surface scope creep and missing requirements.

**Informational only — never blocks.** Some drift is intentional ("I saw a bug while working on the feature"). The goal is awareness, not enforcement.

## When to Run

- On-demand only. Invoked by user phrases: `"check scope drift"`, `"scope check"`, `"did I drift?"`, or direct Skill-tool invocation.
- Skipped when no diff exists against the base branch (nothing to compare).
- Skipped when no intent source can be resolved (see abort behavior below).

This skill does **not** auto-fire on Stop events or completion claims — that is `verification-before-completion`'s job.

## Intent-Source Contract

The canonical intent source is the latest athanor session plan. Full contract in `.athanor/sessions/2026-04-14-001/pr1b-discovery.md` § (e); the essentials are embedded here.

### INTENT_SOURCE_GLOB

```
.athanor/sessions/<LATEST>/plan.md
.athanor/sessions/<LATEST>/deep-plan.md
.athanor/sessions/<LATEST>/lite-plan.md
```

### Resolution rules

1. **Latest-session selection.** Let `S` be the immediate child directories of `.athanor/sessions/` whose names match `^\d{4}-\d{2}-\d{2}-\d{3}$`. Sort `S` lexicographically descending; take the first element as `<LATEST>`. Names that do not match are ignored. Directory mtime and git-tracked status do not influence selection.
2. **Precedence (existence-based).** Within `<LATEST>`, try the three filenames in strict order: `plan.md` > `deep-plan.md` > `lite-plan.md`. The first that exists wins. No mtime comparison, no content merging, no fallback to older sessions.
3. **Plan-revision rule.** Read the winning file as it exists on disk at invocation time (mtime is the tie-breaker only across revisions of the same file). If the file begins with a YAML frontmatter block containing `canonical: true`, honor that as pinned-canonical regardless of mtime. Absence, `canonical: false`, or malformed frontmatter all resolve to "latest mtime wins".
4. **Abort behavior.** If `.athanor/sessions/` does not exist, OR no directory in `S` matches the id pattern, OR `<LATEST>` contains none of the three filenames — abort with an error naming the missing path(s). Do NOT fall back to an older session, an untracked plan file elsewhere, or `decisions.md`.

`decisions.md` is intentionally out of scope for this contract: it is a locked-choice ledger, not a scope statement.

### SELF_REFERENCE_EXCLUDES

Athanor's own session/lesson/discovery artifacts must be stripped from the changed-files list before drift classification — otherwise every run flags its own plan edits as drift:

```
.athanor/sessions/**/*
.athanor/lessons/**/*
.athanor/discoveries/**/*
```

Apply these exclusions to `git diff --name-only` output. Any other path (including `.athanor/CLAUDE.md`, `.athanor/plugin.json`, `athanor/skills/**`) remains in scope.

## How It Works

### Step 1: Gather Stated Intent

Collect intent signals from multiple sources (any that exist):

```bash
# 1. Canonical plan from latest athanor session (per INTENT_SOURCE_GLOB)
PLAN_FILE=""
if [[ -d ".athanor/sessions" ]]; then
  LATEST=$(ls -1 .athanor/sessions 2>/dev/null \
    | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{3}$' \
    | sort -r | head -n1)
  if [[ -n "$LATEST" ]]; then
    for candidate in plan.md deep-plan.md lite-plan.md; do
      [[ -f ".athanor/sessions/$LATEST/$candidate" ]] \
        && PLAN_FILE=".athanor/sessions/$LATEST/$candidate" && break
    done
  fi
fi

# Enforce Resolution rule 4: abort when no intent source resolved in latest session.
# Per Mandatory Compliance, must NOT fall back to commit messages alone.
if [[ -z "$PLAN_FILE" ]]; then
  echo "ABORT: no intent source in latest session (${LATEST:-<none>})"
  echo "Looked for: .athanor/sessions/${LATEST:-<none>}/{plan.md,deep-plan.md,lite-plan.md}"
  echo "Remediation: run /athanor:plan to create a plan, or verify .athanor/sessions/ contains a session dir matching YYYY-MM-DD-NNN with a plan file."
  exit 1
fi

# 2. PR description (if on a branch with an open PR)
PR_BODY=""
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
if [[ -n "$CURRENT_BRANCH" && "$CURRENT_BRANCH" != "main" && "$CURRENT_BRANCH" != "master" ]]; then
  if command -v gh &>/dev/null; then
    PR_BODY=$(gh pr view "$CURRENT_BRANCH" --json body --jq '.body' 2>/dev/null || echo "")
  fi
fi

# 3. Commit messages on this branch (since divergence from base)
BASE_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")
COMMIT_MESSAGES=$(git log --oneline "${BASE_BRANCH}..HEAD" 2>/dev/null || echo "")
```

If `PLAN_FILE` is empty AND `PR_BODY` is empty AND `COMMIT_MESSAGES` is empty, abort with a message naming what was searched. Do not produce a vacuous report.

Because athanor's `plan.md` is a structured doc (Goals / Subtasks / Decisions / Verifications), extract intent from its Goals/Overview section and Subtasks table. Do not expect flat checkbox lines; derive the stated intent by reading the plan's own structure.

### Step 2: Gather Actual Diff

```bash
DIFF_STAT=$(git diff --stat "${BASE_BRANCH}..HEAD" 2>/dev/null || git diff --stat HEAD~1 2>/dev/null || echo "")
DIFF_FILES=$(git diff --name-only "${BASE_BRANCH}..HEAD" 2>/dev/null || git diff --name-only HEAD~1 2>/dev/null || echo "")
DIFF_SUMMARY=$(git diff --shortstat "${BASE_BRANCH}..HEAD" 2>/dev/null || git diff --shortstat HEAD~1 2>/dev/null || echo "")
```

If `DIFF_FILES` is empty, skip the rest — there is no diff to classify.

Apply `SELF_REFERENCE_EXCLUDES` to `DIFF_FILES` before continuing. A file whose path matches any of the three exclude globs is dropped from the classification input.

### Step 3: Analyse for Drift

Compare intent signals against the filtered diff. Two categories:

**Scope Creep** — files or changes not aligned with any stated intent:
- Unrelated directories not mentioned in the plan or commit messages
- New capabilities, APIs, or UI elements not described in intent
- "While I was in there" formatting/refactor/dependency changes mixed with feature work
- Build config, CI, or dependency changes bundled with feature code

**Missing Requirements** — items from stated intent not reflected in the diff:
- Subtasks/goals in the plan not addressed by any changed file
- Features described in PR body or commit messages with no corresponding code changes
- Features implemented but no corresponding test files changed
- API or behaviour changes with no documentation updates

### Step 4: Output Structured Report

```markdown
## Scope Drift Check

**Status:** `CLEAN` | `DRIFT DETECTED` | `REQUIREMENTS MISSING` | `DRIFT + MISSING`

### Intent Summary
Sources checked: plan.md ✓ | PR description ✗ | Commit messages (N commits) ✓
- [Summarise the stated intent in 2-3 bullet points]

### Delivered Summary
- N files changed across M directories (after self-reference exclusion)
- [Summarise what the diff actually does in 2-3 bullet points]

### Scope Creep (if any)
| File/Directory | Why it looks unrelated | Severity |
|----------------|------------------------|----------|
| `path/to/file` | Not mentioned in any intent source | Low/Medium/High |

### Missing Requirements (if any)
| Requirement | Source | Evidence |
|-------------|--------|----------|
| [Requirement text] | plan.md Subtask N | No matching file changes found |

### Recommendation
- [One-line: "Clean — proceed" or "N items drifted, M requirements missing — review with awareness"]
```

Report the exact `PLAN_FILE` path used (e.g. `.athanor/sessions/2026-04-14-001/plan.md`) so the user can verify which session grounded the check.

## Mandatory Compliance

When invoked, you MUST execute the pipeline. You are PROHIBITED from:
- Guessing whether drift occurred without running `git diff` and reading the plan
- Reporting "no drift" without having resolved an intent source
- Blocking or gating any downstream action — this skill is informational only

If the contract aborts (no intent source, no diff), say so explicitly. A vacuous "CLEAN" report is worse than an honest abort.

## Configuration

No configuration needed. The skill auto-detects available intent sources and adapts:

- No latest session matching the id pattern → abort per (e.3)
- No PR → skip PR body
- No git history → skip commit messages
- No diff → skip gracefully (nothing to compare)

# Attribution

Adapted under MIT license. See Provenance block at top of this file for upstream path, source commit, and modification list.
Copyright (c) 2026 nyldn
