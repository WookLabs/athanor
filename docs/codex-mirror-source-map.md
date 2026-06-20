# Codex Mirror Source Map

Last reviewed: 2026-06-20.

This file is the source of truth for Athanor's manual Claude-to-Codex mirror
surface. It does not generate skills. It lets a read-only gate prove that the
Codex companion still mirrors the intended Claude skills or explicitly records
why a surface is Codex-only or Claude-only.

Run the verifier:

```text
python scripts/gates/codex_mirror_parity.py --json
```

## Mirror Map

| Claude surface | Claude source | Codex surface | Codex source | Status | Description anchor |
|---|---|---|---|---|---|
| analyze | `skills/analyze/SKILL.md` | athanor-analyze | `plugins/athanor-codex/skills/athanor-analyze/SKILL.md` | mirror | analyze |
| assess | `skills/assess/SKILL.md` | athanor-assess | `plugins/athanor-codex/skills/athanor-assess/SKILL.md` | mirror | 100 |
| debug | `skills/debug/SKILL.md` | athanor-debug | `plugins/athanor-codex/skills/athanor-debug/SKILL.md` | mirror | debug |
| deep-plan | `skills/deep-plan/SKILL.md` | athanor-deep-plan | `plugins/athanor-codex/skills/athanor-deep-plan/SKILL.md` | mirror | deep |
| discuss | `skills/discuss/SKILL.md` | athanor-discuss | `plugins/athanor-codex/skills/athanor-discuss/SKILL.md` | mirror | discuss |
| lfg | `skills/lfg/SKILL.md` | athanor-lfg | `plugins/athanor-codex/skills/athanor-lfg/SKILL.md` | mirror | lfg |
| lfg-goal | `skills/lfg-goal/SKILL.md` | athanor-lfg-goal | `plugins/athanor-codex/skills/athanor-lfg-goal/SKILL.md` | mirror | goal |
| lite-plan | `skills/lite-plan/SKILL.md` | athanor-lite-plan | `plugins/athanor-codex/skills/athanor-lite-plan/SKILL.md` | mirror | lite |
| plan | `skills/plan/SKILL.md` | athanor-plan | `plugins/athanor-codex/skills/athanor-plan/SKILL.md` | mirror | plan |
| prompt-gen | `skills/prompt-gen/SKILL.md` | athanor-prompt-gen | `plugins/athanor-codex/skills/athanor-prompt-gen/SKILL.md` | mirror | prompt |
| review | `skills/review/SKILL.md` | athanor-review | `plugins/athanor-codex/skills/athanor-review/SKILL.md` | mirror | review |
| scope-drift | `skills/scope-drift/SKILL.md` | athanor-scope-drift | `plugins/athanor-codex/skills/athanor-scope-drift/SKILL.md` | mirror | scope |
| setup | `skills/setup/SKILL.md` | athanor-setup | `plugins/athanor-codex/skills/athanor-setup/SKILL.md` | mirror | setup |
| verification-before-completion | `skills/verification-before-completion/SKILL.md` | athanor-verify | `plugins/athanor-codex/skills/athanor-verify/SKILL.md` | mirror | verification |
| work | `skills/work/SKILL.md` | athanor-work | `plugins/athanor-codex/skills/athanor-work/SKILL.md` | mirror | work |
| ce-test-browser | `skills/ce-test-browser/SKILL.md` | none | none | Claude-only | browser |
| releaser | `agents/releaser.md` | athanor-release | `plugins/athanor-codex/skills/athanor-release/SKILL.md` | codex-agent-mirror | release |
| ci-watcher | `agents/ci-watcher.md` | athanor-ci-watch | `plugins/athanor-codex/skills/athanor-ci-watch/SKILL.md` | codex-agent-mirror | ci |

## Runtime Boundary

Unsupported Claude-only runtime surfaces in Codex:

- Claude Stop hook.
- Claude PreToolUse Kernel Guard.
- Freeze enforcement.
- Claude Task worker dispatch.

Codex mirror skills must state these limits instead of claiming hook-backed
enforcement. New Codex skills require either a mirror row, a Codex-only row
with a Claude agent/source reference, or an explicit rejection in this file.
