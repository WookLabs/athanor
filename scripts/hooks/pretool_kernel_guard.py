#!/usr/bin/env python3
"""
Athanor v0.16.0 PreToolUse kernel guard.

Registered as `type: command` in hooks/hooks.json. On every PreToolUse event,
Claude Code invokes this script with the event payload on stdin. The script
inspects the proposed tool invocation and blocks 3 catastrophic worker-hazard
classes:

  1. **Destructive shell commands** (Bash):
     - `rm -rf` targeting filesystem root or home
     - `git reset --hard`
     - `git clean -f`
     - `git checkout .` (restore all)
  2. **Force-push to protected branches** (Bash):
     - `git push --force` / `-f` / `--force-with-lease` to main/master
  3. **Sensitive credential file access** (Bash, Read, Write, Edit):
     - `.env`, `.env.local`, `.env.production`, `.env.secret`
     - `credentials.json`, `credentials.yaml`, `private_key`, `.ssh/`,
       `.aws/credentials`
     - EXCEPTIONS: `.env.example`, `.env.template`, `.env.test`, `.env.sample`,
       paths under `fixtures/` or starting with `test_`

Decision flow:
  1. Parse stdin (PreToolUse event JSON). Fail-open on missing/unparseable.
  2. Read `hooks.profile` from athanor.json. If `"off"`, exit 0 silently.
     **NOTE (v0.18.0 invariant):** missing athanor.json keeps the default
     ``profile="standard"`` — kernel guard is fail-CLOSED on missing config.
     ``rm -rf /`` is still blocked even when no athanor.json exists.
  3. Dispatch by `tool_name`. If a rule matches, exit 2 with stderr explaining
     the block (Claude Code feeds stderr back to the model as continuation
     context so it can choose a safer alternative).

Stdlib-only — same pattern as `stop_verify_claims.py`. As of v0.17.0
(S06) the input/config helpers below are sourced from the shared
``_athanor_hook_runtime`` sibling module; the in-script wrappers
``_read_stdin_payload`` / ``_find_athanor_config`` / ``_read_profile``
remain as thin delegations so the existing test surface (which
subprocess-invokes this script) is unchanged.

v0.18.0 (S?): the rule-evaluation core is extracted into
``evaluate_payload(payload, project_root=None) -> (exit_code, stderr_message)``
so the upcoming PreToolUse dispatcher can invoke kernel-guard logic
in-process without re-shelling. ``main()`` remains the CLI entry point
and now delegates to ``evaluate_payload`` after reading stdin/profile;
all v0.16.0 behavior (including fail-closed on missing config) is
preserved bit-for-bit. The 23 existing subprocess-driven regression
tests continue to pass unchanged.

Cross-platform note: invoked via `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/
hooks/pretool_kernel_guard.py"` in hooks/hooks.json. The plugin-root
expansion follows the v0.11.4 lesson (bare relative paths broke
deployment in non-source-repo projects).
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Optional

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import _athanor_hook_runtime as _runtime  # noqa: E402

ATHANOR_CONFIG_NAME = _runtime.ATHANOR_CONFIG_NAME
SUPPORTED_PROFILES = {"off", "standard"}

# ---------------------------------------------------------------------------
# Rule 1: Destructive shell commands
# ---------------------------------------------------------------------------
# `rm -rf` targeting filesystem root or home. v0.18.6 (deep bug hunt G1-G3)
# replaced a single rigid regex with a flag-detection + target-detection split
# so equally-destructive variants no longer slip through:
#   - flag order independent (`-rf` AND `-fr`)
#   - intervening options allowed (`rm -rf --no-preserve-root /`)
#   - shell-glob root/home forms (`/*`, `~/*`)
# while keeping false-positives out (`rm -rf /tmp/build`, `./build/`,
# `~/projects/old`, `rm -f file.txt`). A catastrophic target is an argument
# that is filesystem root or home with NOTHING after the first separator
# except glob/dot wildcards — `/tmp` has a path component, so it is NOT one.
_RM_ROOT_OR_HOME_TARGET = re.compile(
    r"""(?:^|\s)            # arg boundary
        ['"]?               # optional opening quote
        (?:
            /(?:\*|\.\*?)?         # / , /* , /. , /.*
          | ~(?:/(?:\*|\.\*?)?)?   # ~ , ~/ , ~/* , ~/. , ~/.*
        )
        ['"]?               # optional closing quote
        (?=\s|$|;|&|\|)     # arg end
    """,
    re.VERBOSE,
)


def _is_destructive_rm(command: str) -> bool:
    """True if `command` has an `rm` invocation that is recursive AND force AND
    targets filesystem root or home — any flag order, with optional intervening
    options, including shell-glob forms (`/*`, `~/*`)."""
    for m in re.finditer(r"\brm\b([^\n;]*)", command):
        # Bound the arg span at a command-chain separator so a later command's
        # tokens don't bleed into this rm's analysis.
        args = re.split(r"&&|\|\||\|", m.group(1))[0]
        has_recursive = (
            "--recursive" in args
            or re.search(r"(?:^|\s)-[a-zA-Z]*r[a-zA-Z]*(?=\s|$)", args) is not None
        )
        has_force = (
            "--force" in args
            or re.search(r"(?:^|\s)-[a-zA-Z]*f[a-zA-Z]*(?=\s|$)", args) is not None
        )
        if has_recursive and has_force and _RM_ROOT_OR_HOME_TARGET.search(args):
            return True
    return False


GIT_RESET_HARD_PATTERN = re.compile(r"\bgit\s+reset\s+--hard\b")
# `git clean` with force — short bundle (`-f`/`-fd`/`-xdf`) OR long `--force`
# (v0.18.6 bug hunt G4: the long form previously slipped through).
GIT_CLEAN_F_PATTERN = re.compile(
    r"\bgit\s+clean\b(?=.*?(?:\s-[a-zA-Z]*f|\s--force\b))"
)
# `git checkout .` — restore all. Trailing $ or whitespace so we don't match
# `git checkout ./path` or `git checkout .foo`.
GIT_CHECKOUT_DOT_PATTERN = re.compile(r"\bgit\s+checkout\s+\.(?:\s*$|\s+--?)")

# Regex-driven destructive patterns (the rm family is handled by
# _is_destructive_rm above; included in _check_destructive_shell).
DESTRUCTIVE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (GIT_RESET_HARD_PATTERN, "git reset --hard"),
    (GIT_CLEAN_F_PATTERN, "git clean -f / --force"),
    (GIT_CHECKOUT_DOT_PATTERN, "git checkout . (restore all)"),
]

# ---------------------------------------------------------------------------
# Rule 2: Force-push to protected branches
# ---------------------------------------------------------------------------
# The `(main|master)` token must appear as a standalone word (\b boundary)
# anywhere on the same `git push` invocation as a force flag. Feature
# branches like `feature/x` or `release/main-fix` must NOT match
# (`release/main-fix` would match `\bmain\b` — but the leading slash + dash
# inside the branch name means `\b` does fire at the `main` boundary).
# Trade-off: branch names that literally end in `main` as a slash-segment
# (e.g. `feature/main`) are conservatively blocked. Acceptable for v0.16.0;
# users push `feature/main` via `--force-with-lease` to a non-main remote
# rarely, and the block is easily worked around (rename branch).
FORCE_PUSH_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bgit\s+push\b(?=.*--force\b)(?=.*\b(?:main|master)\b)"),
    re.compile(r"\bgit\s+push\b(?=.*(?:^|\s)-f\b)(?=.*\b(?:main|master)\b)"),
    re.compile(r"\bgit\s+push\b(?=.*--force-with-lease\b)(?=.*\b(?:main|master)\b)"),
]

# ---------------------------------------------------------------------------
# Rule 3: Sensitive credential file access
# ---------------------------------------------------------------------------
# Dotenv variants — extension-anchored. The exception check (below) carves
# out `.env.example`, `.env.template`, etc.
SENSITIVE_DOTENV_PATTERN = re.compile(
    r"(?:^|[/\\])\.env(?:\.local|\.production|\.secret)?(?:$|\s|['\"])"
)
# Substring markers — match anywhere in the path.
SENSITIVE_SUBSTRINGS = (
    "credentials.json",
    "credentials.yaml",
    "credentials.yml",
    "private_key",
    ".ssh/",
    ".aws/credentials",
)
# Exception markers — if the path contains any of these, allow access even
# if a sensitive pattern matches. Order: example/template/test/sample first,
# then directory-based exemptions for fixtures and test files.
SENSITIVE_EXCEPTIONS = (
    ".env.example",
    ".env.template",
    ".env.test",
    ".env.sample",
    "fixtures/",
    "/test_",
    # `test_` at the start of a basename (e.g. `tests/test_foo.py` is also
    # caught by `tests/` segment, but standalone `test_foo.env` should be
    # allowed because it's a fixture name).
)
# `cat`/`less`/`head`/`tail`/`more`/`bat` credential-read detection for Bash.
_BASH_READER_KEYWORDS = ("cat", "less", "more", "head", "tail", "bat")
# Options that consume a SEPARATE-token value (`head -n 5 file`). Their value
# must be skipped so the path candidate isn't mistaken for the value itself
# (v0.18.6 bug hunt R1: `head -n 5 .env` previously captured `5`, not `.env`).
_BASH_READER_VALUE_OPTS = frozenset({"-n", "-c", "--lines", "--bytes"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stderr(msg: str) -> None:
    """Emit one line of stderr; stderr is fed back to the model on exit 2
    and visible in CI logs on exit 0. Both are useful — keep messages terse."""
    print(f"athanor (pretool guard): {msg}", file=sys.stderr)


def _read_stdin_payload() -> dict | None:
    """Read the PreToolUse event payload from stdin.

    v0.17.0: thin delegation to ``_athanor_hook_runtime.read_stdin_payload``.
    Behavior preserved exactly — returns parsed dict, or None on TTY,
    read error, empty body, JSON parse failure, or non-dict.
    """
    return _runtime.read_stdin_payload()


def _find_athanor_config() -> Path | None:
    """Locate athanor.json via priority chain (v0.7.9 pattern).

    v0.17.0: thin delegation to
    ``_athanor_hook_runtime._find_athanor_config_path`` (internal helper,
    re-exported by name for the pretool guard's exit-2 reporting surface
    so existing call sites continue to receive a Path or None).
    """
    return _runtime._find_athanor_config_path()


def _read_profile() -> str:
    """Read `hooks.profile` from athanor.json. Defaults to "standard"."""
    config = _runtime.read_athanor_config()
    if _runtime.is_hook_profile_off(config):
        return "off"
    # Defensive on unknown values — the runtime helper treats anything but
    # "off" as non-off; the v0.16.0 contract additionally rejects unknown
    # explicit values back to "standard". Re-derive here to preserve that.
    hooks_section = config.get("hooks", {}) if isinstance(config, dict) else {}
    if not isinstance(hooks_section, dict):
        return "standard"
    profile = hooks_section.get("profile", "standard")
    if not isinstance(profile, str) or profile not in SUPPORTED_PROFILES:
        return "standard"
    return profile


# ---------------------------------------------------------------------------
# Rule dispatchers
# ---------------------------------------------------------------------------

def _check_destructive_shell(command: str) -> str | None:
    """Return matched description if the command is destructive, else None."""
    if _is_destructive_rm(command):
        return "rm -rf targeting filesystem root or home"
    for pattern, description in DESTRUCTIVE_PATTERNS:
        if pattern.search(command):
            return description
    return None


def _check_force_push(command: str) -> bool:
    """Return True if the command is a force-push to a protected branch."""
    return any(pattern.search(command) for pattern in FORCE_PUSH_PATTERNS)


def _path_is_sensitive(path: str) -> bool:
    """Return True if the path targets a sensitive credential file AND is
    not covered by an exception."""
    if not path:
        return False
    # Normalize a bit — strip surrounding quotes the model may have included.
    p = path.strip().strip("'\"")
    if not p:
        return False
    lowered = p.lower()
    # Exceptions first — example/template/test/sample files are allowed even
    # if they share the .env prefix.
    for ex in SENSITIVE_EXCEPTIONS:
        if ex in lowered:
            return False
    # Substring markers — credentials.json, .ssh/, etc.
    for marker in SENSITIVE_SUBSTRINGS:
        if marker in lowered:
            return True
    # Dotenv regex — anchored on path separator or start, with optional
    # known suffix (.local, .production, .secret).
    if SENSITIVE_DOTENV_PATTERN.search(p) or SENSITIVE_DOTENV_PATTERN.search(p + " "):
        return True
    # Bare basename (e.g. `.env`) — the regex above requires a leading
    # separator OR start-of-string; the `p + " "` pad covers trailing
    # boundary. Double-check basename for the bare-`.env` case.
    base = os.path.basename(p)
    if base in {".env", ".env.local", ".env.production", ".env.secret"}:
        return True
    return False


def _bash_extract_read_paths(command: str) -> list[str]:
    """Extract candidate file paths from `cat`/`less`/`head`/`tail`/`more`/
    `bat` commands. Returns the first positional path per pipeline/chain
    segment so `cat .env | grep PASS` is still inspected, and value-taking
    options (`head -n 5 .env`) don't shadow the real path (v0.18.6 R1)."""
    paths: list[str] = []
    for segment in re.split(r"[|;&\n]", command):
        tokens = segment.split()
        reader_idx = next(
            (i for i, t in enumerate(tokens) if t in _BASH_READER_KEYWORDS), None
        )
        if reader_idx is None:
            continue
        j = reader_idx + 1
        while j < len(tokens):
            tok = tokens[j]
            if tok.startswith("-"):
                # Skip the option; for separate-value options skip its value too.
                j += 2 if tok in _BASH_READER_VALUE_OPTS else 1
                continue
            paths.append(tok)
            break
    return paths


# ---------------------------------------------------------------------------
# Public dispatcher entry point
# ---------------------------------------------------------------------------

def evaluate_payload(
    payload: dict,
    project_root: Optional[Path] = None,
) -> tuple[int, str]:
    """Evaluate a PreToolUse payload against the kernel-guard rules.

    Pure function — no global state, no stdin/stdout I/O. Designed to be
    called both from this script's ``main()`` (CLI entry) and from the
    v0.18.0 in-process PreToolUse dispatcher.

    Parameters
    ----------
    payload : dict
        The parsed PreToolUse event JSON. Must already be a dict (callers
        handle the stdin-parse fail-open path themselves; passing a
        malformed shape here yields a fail-open ``(0, "")``).
    project_root : Optional[Path]
        Reserved for the dispatcher: when supplied, callers may use it to
        scope config lookup. The current implementation reads the profile
        via the shared runtime helper (which honors ``$CLAUDE_PROJECT_DIR``
        and walk-up from cwd); ``project_root`` is accepted to lock the
        signature for the dispatcher but does NOT override the runtime
        resolution path — that path already covers the dispatcher's
        in-process case. Reserved for future per-call overrides.

    Returns
    -------
    (exit_code, stderr_message) : tuple[int, str]
        ``exit_code`` is 0 (allow) or 2 (block). ``stderr_message`` is the
        single-line block reason (without the ``athanor (pretool guard):``
        prefix — the caller is responsible for prefixing if writing to
        stderr). On allow, ``stderr_message`` is an empty string.

    Behavior invariants (v0.16.0, preserved by v0.18.0 refactor)
    -----------------------------------------------------------
    1. Missing athanor.json yields ``profile="standard"`` (fail-CLOSED).
       ``rm -rf /`` is still blocked even when no athanor.json exists.
    2. ``hooks.profile == "off"`` yields exit 0 (opt-out), same semantics
       as the Stop hook.
    3. Unknown/malformed ``tool_name`` or ``tool_input`` shape yields
       fail-open ``(0, "")`` — matches the v0.16.0 CLI behavior.
    """
    # project_root reserved for future use — currently the runtime helper
    # owns config resolution (env var + walk-up).
    del project_root

    profile = _read_profile()
    if profile == "off":
        return (0, "")  # opt-out; same semantics as Stop hook

    if not isinstance(payload, dict):
        return (0, "")

    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    if not isinstance(tool_name, str) or not isinstance(tool_input, dict):
        # Unknown/malformed shape — fail-open.
        return (0, "")

    # ---- Bash tool ----
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        if not isinstance(command, str) or not command:
            return (0, "")

        # Rule 1: destructive shell
        destructive = _check_destructive_shell(command)
        if destructive is not None:
            return (
                2,
                f"BLOCKED: destructive command detected ({destructive}). "
                f"Narrow the scope or use a safer alternative.",
            )

        # Rule 2: force-push to protected branches
        if _check_force_push(command):
            return (
                2,
                "BLOCKED: force-push to main/master. Use a feature branch.",
            )

        # Rule 3: sensitive credential file access via cat/less/head/tail
        for path in _bash_extract_read_paths(command):
            if _path_is_sensitive(path):
                return (
                    2,
                    f"BLOCKED: accessing sensitive credential file "
                    f"({path}). Use environment variables instead.",
                )

        return (0, "")

    # ---- Read / Write / Edit tools ----
    if tool_name in ("Read", "Write", "Edit"):
        # All three tools use `file_path` as the canonical input key
        # (per Claude Code tool schemas).
        path = tool_input.get("file_path", "")
        if not isinstance(path, str) or not path:
            return (0, "")
        if _path_is_sensitive(path):
            return (
                2,
                f"BLOCKED: accessing sensitive credential file ({path}). "
                f"Use environment variables instead.",
            )
        return (0, "")

    # Other tools — pass through.
    return (0, "")


# ---------------------------------------------------------------------------
# CLI entry point (subprocess-invoked by Claude Code PreToolUse hook)
# ---------------------------------------------------------------------------

def main() -> int:
    """CLI entry: read stdin, evaluate, emit stderr on block, return exit code.

    v0.18.0: delegates the rule evaluation to :func:`evaluate_payload`. The
    stdin-parse fail-open path stays here because it requires direct stdin
    I/O (and a distinct stderr message); the rest of the decision flow is
    pure-function and tested via both CLI subprocess and direct call.
    """
    payload = _read_stdin_payload()
    if payload is None:
        _stderr("stdin missing or unparseable; passing (fail-open)")
        return 0

    exit_code, stderr_message = evaluate_payload(payload)
    if exit_code == 2 and stderr_message:
        _stderr(stderr_message)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
