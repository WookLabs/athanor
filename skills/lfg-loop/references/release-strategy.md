# LFG Loop Release Strategy

Default policy is per-cycle persistence: each delivery cycle keeps its own PR,
CI evidence, residual notes, and receipt. Consolidated release is opt-in through
`lfgLoop.consolidateCycles`.

The loop leader may run git/gh plumbing only where `/athanor:lfg` already
authorizes it. Version bump, changelog, release tagging, and state rotation stay
owned by the releaser ceremony.

Terminal loop artifacts must point to the actual PRs, commits, CI runs, and
residual files used as evidence.
