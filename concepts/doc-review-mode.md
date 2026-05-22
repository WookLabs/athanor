# Concept: Doc Review Mode

**Source:** ce-doc-review@3.8.3 (https://github.com/EveryInc/compound-engineering-plugin)
**Target:** skills/review/SKILL.md §"Doc review mode"
**License:** MIT
**Author:** Kieran Klaassen / Every Inc
**Commit SHA:** TBD — filled after v0.12.0 ship merge

## Why this concept survives v0.12.0

`/athanor:review` was originally code-only — its 6 personas all assume a code diff as input. `ce-doc-review` introduces a complementary mode that examines documentation artifacts (plan.md, requirements.md, CHANGELOG entries, architecture docs) through a different lens set tuned for prose concerns: coherence, feasibility, scope-guard, product framing, security framing, design framing, and an adversarial document-reviewer. Subtask 8 lifted this mode into `skills/review/SKILL.md` as a `--target docs` flag that switches the persona array from the 6-code lenses to the 7-doc lenses.

The concept survives because documentation review and code review share enough structural shape (parallel personas → merged report) to live in one skill, but diverge enough in vocabulary that they need distinct lens sets. The athanor-native compression also collapses CE's separate document-personas registry into one section of `skills/review/SKILL.md` rather than maintaining standalone sub-agent files.

## What was lifted

- The 7-doc-persona lens set (coherence, feasibility, scope-guardian, product-lens, security-lens, design-lens, adversarial-document)
- The `--target docs` CLI flag that toggles persona arrays (Subtask 8)
- The "doc artifact is the input, not a code diff" mode-switch concept
- The doc-mode output-shape (merged review report scoped to prose concerns)

## What was NOT lifted

- ce-doc-review's separate document-personas registry as standalone sub-agent files
- The upstream split-skill structure (`ce-code-review` + `ce-doc-review` as two skills)
- Per-persona doc-mode system-prompt templates (athanor uses a single unified bilingual voice across all personas)
- CE's doc-mode-specific report templates (athanor reuses the existing review report shape with the persona array swapped)

## Verification

`skills/review/SKILL.md` §"Doc review mode" carries the persona array and the `--target docs` flag. Subtask 8's verification line locks the doc-mode persona array length and contents.
