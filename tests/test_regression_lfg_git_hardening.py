"""Regression — /athanor:lfg autonomous git plumbing is fail-loud hardened.

Gap under lock
--------------
`/athanor:lfg` runs `git push` / `git commit` UNATTENDED: Step 4 review-fix
push, Step 7 push + push-failure handler, Step 8 CI-autofix commit+push. The
Step 7 push-failure handler only catches a NON-ZERO exit — but an interactive
credential / 2FA / LFS-smudge prompt BLOCKS on stdin and never exits, so it
escapes that handler and silently HANGS the unattended pipeline.
`GIT_TERMINAL_PROMPT` appeared NOWHERE in the repo before this fix.

The fix extends `agents/codex-dispatcher.md`'s existing stdin-redirect +
`timeout` fail-loud discipline to lfg's git plumbing: every autonomous git
command is run with `GIT_TERMINAL_PROMPT=0`, stdin from `/dev/null`, and a
finite `timeout`, so a credential/2FA prompt **fails fast** (non-zero exit →
the existing push-failure diagnosis path) instead of hanging.

Scope notes locked here:
- `skills/lfg-loop/SKILL.md` wraps `/athanor:lfg` VERBATIM (D2) with no own
  git push/commit prose, so it needs no change — this file locks that it
  stays a pure wrapper (read-only `git show/log/diff` in the receipt table is
  not autonomous plumbing).
- `agents/ci-watcher.md` Step 4 independently runs `git commit`/`git push`
  in its watch-fix loop, so it carries the same hardening.

Static text reads only — no subprocess, no git invocation.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LFG = REPO_ROOT / "skills" / "lfg" / "SKILL.md"
LFG_GOAL = REPO_ROOT / "skills" / "lfg-loop" / "SKILL.md"
CI_WATCHER = REPO_ROOT / "agents" / "ci-watcher.md"

HARDEN = "GIT_TERMINAL_PROMPT=0"
RATIONALE_TOKENS = ("fail fast", "fails fast", "hang", "credential")

# `GIT_TERMINAL_PROMPT=0 ... git push` on the SAME command line — the token
# sits adjacent to the push it protects. This is the non-vacuous locality
# check: a `GIT_TERMINAL_PROMPT=0` floating elsewhere in the doc would not
# actually harden the push.
_HARDENED_PUSH_RE = re.compile(r"GIT_TERMINAL_PROMPT=0[^\n]*\bgit push\b")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_lfg_git_plumbing_declares_git_terminal_prompt() -> None:
    """MUST — lfg SKILL.md hardens autonomous git with GIT_TERMINAL_PROMPT=0."""
    body = _read(LFG)
    assert body.count(HARDEN) >= 1, (
        "skills/lfg/SKILL.md git plumbing must set GIT_TERMINAL_PROMPT=0 so an "
        "unattended credential / 2FA prompt fails fast instead of hanging the "
        "pipeline. GIT_TERMINAL_PROMPT was absent repo-wide before this fix."
    )


def test_lfg_hardening_is_adjacent_to_push() -> None:
    """MUST (non-vacuous) — the hardening token sits on the same command line
    as `git push`, not just floating somewhere in the doc."""
    body = _read(LFG)
    assert _HARDENED_PUSH_RE.search(body), (
        "GIT_TERMINAL_PROMPT=0 must appear on the same command line as "
        "`git push` in skills/lfg/SKILL.md (e.g. "
        "`GIT_TERMINAL_PROMPT=0 timeout 120s git push </dev/null`) — otherwise "
        "the hardening is decorative and the push is still promptable/hangable."
    )


def test_lfg_hardening_has_failfast_rationale() -> None:
    """MUST — the 'Git plumbing hardening' note explains WHY (fail fast / no
    hang / credential) so the intent survives future edits, AND carries the
    GIT_TERMINAL_PROMPT=0 token in the same block."""
    body = _read(LFG)
    idx = body.find("Git plumbing hardening")
    assert idx >= 0, (
        "skills/lfg/SKILL.md must carry a 'Git plumbing hardening' note "
        "documenting the autonomous-git fail-loud discipline."
    )
    window = body[idx : idx + 900]
    assert HARDEN in window, (
        "the 'Git plumbing hardening' note must show GIT_TERMINAL_PROMPT=0 "
        "(the concrete hardened form), not just mention hardening abstractly."
    )
    assert any(tok in window.lower() for tok in RATIONALE_TOKENS), (
        "the hardening note must state the fail-fast / no-hang / credential "
        f"rationale (one of {RATIONALE_TOKENS}) so a future editor cannot strip "
        "the token without also removing the stated reason."
    )


def test_lfg_stdin_redirect_and_timeout_accompany_hardening() -> None:
    """MUST — belt-and-suspenders: stdin redirect from /dev/null + a finite
    timeout fence accompany GIT_TERMINAL_PROMPT=0, and the note cites the
    codex-dispatcher mirror.

    v0.24.3 (N2) strengthened: the timeout fence must be the PORTABLE
    resolved form `"$TIMEOUT_CMD" NNNs git …` (stock macOS/BSD has no GNU
    `timeout`; a bare wrapper exits 127 before git runs), and the resolver
    preamble (`command -v timeout || command -v gtimeout` + coreutils
    fail-loud hint) must be present in the doc."""
    body = _read(LFG)
    assert "</dev/null" in body, (
        "hardened autonomous git commands must redirect stdin from /dev/null "
        "so a prompt cannot block on inherited stdin."
    )
    assert re.search(r'"\$TIMEOUT_CMD"\s+\d+s\s+git\s+(?:push|commit)', body), (
        "hardened autonomous git commands must carry a finite portable "
        '`"$TIMEOUT_CMD" NNNs` fence (the hard wall-clock stop if the prompt '
        "path still stalls) — bare `timeout NNNs` is GNU-coreutils-only and "
        "exits 127 before git runs on stock macOS/BSD."
    )
    assert "command -v timeout || command -v gtimeout" in body, (
        "the portable timeout resolver preamble must be present so "
        '`"$TIMEOUT_CMD"` actually resolves (timeout → gtimeout → fail loud).'
    )
    assert "coreutils" in body, (
        "the resolver's fail-loud path must name GNU coreutils as the "
        "actionable install hint."
    )
    assert "codex-dispatcher" in body, (
        "the hardening should reference agents/codex-dispatcher.md's existing "
        "stdin-redirect + timeout hardening as the mirror it extends."
    )


def test_lfg_cifix_autopush_hardened() -> None:
    """MUST — the Step 8 CI-autofix push (the unattended retry-loop site the
    gap explicitly named, ~L302) is hardened, not just the Step 4 review push."""
    body = _read(LFG)
    step8_start = body.find("### Step 8")
    step85_start = body.find("### Step 8.5")
    assert step8_start >= 0 and step85_start >= 0, (
        "lfg SKILL.md must retain a Step 8 (CI watch/autofix) section bounded "
        "by Step 8.5."
    )
    step8 = body[step8_start:step85_start]
    assert _HARDENED_PUSH_RE.search(step8), (
        "the Step 8 CI-autofix `git push` must be hardened with "
        "GIT_TERMINAL_PROMPT=0 — it runs inside the unattended retry loop where "
        "a credential/2FA prompt would silently hang the pipeline."
    )


def test_ci_watcher_autonomous_push_hardened() -> None:
    """MUST — agents/ci-watcher.md independently runs git commit/push in its
    watch-fix loop; that push carries the same fail-loud hardening."""
    body = _read(CI_WATCHER)
    assert HARDEN in body and _HARDENED_PUSH_RE.search(body), (
        "agents/ci-watcher.md Step 4 `git push` must be hardened with "
        "GIT_TERMINAL_PROMPT=0 (+ </dev/null + finite timeout) — it pushes "
        "UNATTENDED inside the CI retry loop, the same hang risk as lfg."
    )


def test_lfg_loop_is_pure_wrapper_no_own_git_push() -> None:
    """lfg-loop wraps /athanor:lfg VERBATIM and owns NO git push/commit prose,
    so it needs no hardening. Lock that it stays a pure wrapper — if it ever
    grows its own autonomous push/commit, this fails and flags that the
    §'Git plumbing hardening' discipline must be added there too."""
    body = _read(LFG_GOAL)
    assert "verbatim" in body.lower() and "/athanor:lfg" in body, (
        "lfg-loop must document that it invokes /athanor:lfg verbatim (the "
        "reason it carries no git plumbing of its own)."
    )
    # Read-only git (git show / log / diff in the receipt-validation table) is
    # fine; a `git push` / `git commit` COMMAND would be its OWN autonomous
    # plumbing that would need the same GIT_TERMINAL_PROMPT=0 hardening.
    assert "git push" not in body, (
        "lfg-loop grew a 'git push' — it is no longer a pure lfg wrapper; add "
        "the §'Git plumbing hardening' GIT_TERMINAL_PROMPT=0 discipline there too."
    )
    assert "git commit" not in body, (
        "lfg-loop grew a 'git commit' — add the git-plumbing hardening there too."
    )
