# Hook Safety Pattern Corpus

The safety corpus is an opt-in PreToolUse diagnostic layer. It classifies risky
tool payloads and writes structured findings, but it does not block in this
release.

## Modes

- `off`: default, no classifier work and no diagnostics.
- `observe`: write `.athanor/hook-safety.jsonl`, no stderr, exit 0.
- `warn`: write `.athanor/hook-safety.jsonl`, emit one stderr summary, exit 0.

## Pattern Metadata

Every finding records `stage`, `source_ref`, `risk`, and
`promotion_condition`. The default `stage` is `observe`; promotion requires
live diagnostic evidence, false-positive review, replay coverage, catalog
update, and release-policy documentation.

## Initial Patterns

| Pattern ID | Stage | Risk | Source ref | Meaning |
| --- | --- | --- | --- | --- |
| `bash-curl-pipe-shell` | observe | high | `ref/karanb192-claude-code-hooks/README.md` | `curl` output is piped directly into `sh` or `bash`. |
| `bash-wget-pipe-shell` | observe | high | `ref/disler-claude-code-hooks-mastery/README.md` | `wget` output is piped directly into `sh` or `bash`. |
| `shell-rm-rf-broad-delete` | observe | high | `ref/karanb192-claude-code-hooks/README.md` | `rm -rf` targets a broad local path or wildcard. |
| `git-clean-force-delete` | observe | high | `ref/disler-claude-code-hooks-mastery/README.md` | `git clean` is running with force-delete flags. |
| `git-direct-commit-protected-branch` | observe | medium | `ref/karanb192-claude-code-hooks/README.md` | `git commit` is running while the current branch is `main` or `master`. |
| `read-env-secret-path` | observe | high | `ref/karanb192-claude-code-hooks/README.md` | `Read` targets a dotenv secret path. |
| `read-ssh-private-key-path` | observe | high | `ref/ElliotJLT-hooksmith/README.md` | `Read` targets an SSH private-key path. |
| `write-private-key-material` | observe | high | `ref/karanb192-claude-code-hooks/README.md` | A write payload contains private-key material. |
| `write-token-shaped-secret` | observe | medium | `ref/karanb192-claude-code-hooks/README.md` | A write payload contains a token-shaped secret. |

`promotion_condition` is intentionally repeated in emitted JSONL findings so a
single observation remains understandable outside this document.

## Promotion Boundary

These findings are not default blockers. A future blocking mode requires live
diagnostic evidence, false-positive review, catalog update, replay coverage, and
release-policy documentation.
