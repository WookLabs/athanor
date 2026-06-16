# Hook Safety Pattern Corpus

The safety corpus is an opt-in PreToolUse diagnostic layer. It classifies risky
tool payloads and writes structured findings, but it does not block in this
release.

## Modes

- `off`: default, no classifier work and no diagnostics.
- `observe`: write `.athanor/hook-safety.jsonl`, no stderr, exit 0.
- `warn`: write `.athanor/hook-safety.jsonl`, emit one stderr summary, exit 0.

## Initial Patterns

| Pattern ID | Severity | Meaning |
| --- | --- | --- |
| `bash-curl-pipe-shell` | high | `curl` output is piped directly into `sh` or `bash`. |
| `bash-wget-pipe-shell` | high | `wget` output is piped directly into `sh` or `bash`. |
| `git-direct-commit-protected-branch` | medium | `git commit` is running while the current branch is `main` or `master`. |
| `write-private-key-material` | high | A write payload contains private-key material. |
| `write-token-shaped-secret` | medium | A write payload contains a token-shaped secret. |

## Promotion Boundary

These findings are not default blockers. A future blocking mode requires live
diagnostic evidence, false-positive review, catalog update, replay coverage, and
release-policy documentation.
