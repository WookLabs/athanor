# Stop-Phrase Whitelist (canonical)

Single source of truth for the **leader-side worker-output stop-phrase whitelist**.
Previously this 5-phrase list was duplicated verbatim across 8 files (7 skill/reference
files + `docs/agent-roles/reviewer.md`); the copies began to drift
(P10 finding). All embeddings now point here instead of restating the list.

## Where this applies

This is **leader-side Worker Output Defense** (advisory; not a code-level gate —
see `CLAUDE.md` §"Defense Mechanisms / Stop-Phrase Detection"). After a dispatched
worker (Researcher, Devil's Advocate, Critic, Planner, Reviewer, analyst, executor,
…) returns, the leader scans the worker's output for these phrases. A match signals
the worker stopped early; the leader **re-dispatches** that worker with the same
prompt prefixed by a "complete the task fully, do not stop early" instruction
(the exact prefix wording is skill-specific). In `/athanor:discuss` clarify mode the
same whitelist guards the *leader's own* dialog turns (the leader must NEVER emit
these phrases mid-dialog).

## The 5 canonical phrases (Korean / English)

| # | Korean | English |
|---|--------|---------|
| 1 | `이 정도면 멈춰도 될 것 같습니다` | `I think we can stop here` |
| 2 | `계속할까요?` | `Should I continue?` |
| 3 | `기존 이슈입니다` | `This is a pre-existing issue` |
| 4 | `새 세션에서 계속` | `Let's continue in a new session` |
| 5 | `좋은 체크포인트` | `Good checkpoint` |

Either the Korean or the English form (or any close paraphrase) counts as a match.
`debug` is especially sensitive to phrase #3 — a "기존 이슈입니다 / pre-existing issue"
claim must be paired with a `git blame` line + the session id where the issue was
first observed, or the finding is rejected.

## Agent-doc exemption policy

Files under `agents/*.md` are **exempt** from carrying the full verbatim list. They
MAY include a short ILLUSTRATIVE excerpt (one or two phrases, e.g.
`'좋은 체크포인트' / 'I think we can stop here'`) immediately followed by a pointer
to this file for the full set. They MUST NOT re-embed the complete 5-phrase block.
Regression coverage (`tests/test_regression_stop_phrase_canonical.py`) scopes the
"no verbatim re-embedding" assertion to `skills/` and explicitly carves out `agents/`.
