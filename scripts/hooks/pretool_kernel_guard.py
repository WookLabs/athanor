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
     - `git push origin +main` (git-native `+refspec` force form, incl.
       `+HEAD:main` / `+refs/heads/x:main` dst-ref spellings)
  3. **Sensitive credential file access** (Bash, Read, Write, Edit, MultiEdit, NotebookEdit):
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

Cross-platform note: reached from hooks/hooks.json via `sh
"${CLAUDE_PLUGIN_ROOT}/scripts/hooks/run_hook.sh"
"${CLAUDE_PLUGIN_ROOT}/scripts/hooks/pretool_dispatcher.py"` (the
dispatcher invokes this guard in-process; run_hook.sh resolves a
portable Python interpreter). The plugin-root expansion follows the
v0.11.4 lesson (bare relative paths broke deployment in
non-source-repo projects).
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
    # Reason per command segment (P13 shared splitter) so a later command's
    # tokens don't bleed into this rm's analysis; within a segment, take the
    # text after the `rm` token as its argument span.
    for segment in _command_segments(command):
        m = re.search(r"\brm\b(.*)", segment)
        if m is None:
            continue
        args = m.group(1)
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
# The `(main|master)` token must appear as a standalone word on the same
# `git push` invocation as a force flag. The trailing boundary is
# `(?![\w-])` rather than a bare `\b`: a plain `\b` fires at the `n`→`-`
# transition inside `feature/main-update`, so `\bmain\b` false-positived on
# any branch whose name merely STARTS with `main`/`master` (e.g.
# `feature/main-update`, `release/master-rework`). `(?![\w-])` requires the
# token to be followed by neither a word char nor a hyphen, so those branch
# names are correctly ALLOWED while `origin main` / `origin master` (token
# followed by space or end-of-string) stay BLOCKED.
# Residual conservative case: a slash-segment that is EXACTLY `main`/`master`
# (e.g. `feature/main`) is still blocked — the leading `\b` fires at `/`→`m`
# and the trailing boundary passes at end-of-arg. Rare; rename to work around.
# This is a best-effort textual gate, not a parser — see module docstring.
#
# Pattern 4 covers the git-native `+refspec` force form (`git push origin
# +main`), which carries no `--force`/`-f` flag yet force-pushes. The
# `(?:[^\s:]*:)?` optional group lets the dst-ref spellings `+HEAD:main` /
# `+refs/heads/x:main` match; the required literal `+` keeps a normal
# `git push origin main` untouched, and the `(?![\w-])` boundary keeps
# `+main-fix` (a branch merely prefixed with `main`) allowed.
FORCE_PUSH_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bgit\s+push\b(?=.*--force\b)(?=.*\b(?:main|master)(?![\w-]))"),
    re.compile(r"\bgit\s+push\b(?=.*(?:^|\s)-f\b)(?=.*\b(?:main|master)(?![\w-]))"),
    re.compile(r"\bgit\s+push\b(?=.*--force-with-lease\b)(?=.*\b(?:main|master)(?![\w-]))"),
    re.compile(r"\bgit\s+push\b(?=.*(?:^|\s)\+(?:[^\s:]*:)?(?:main|master)(?![\w-]))"),
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
)
# A `test_`-prefixed BASENAME (e.g. `test_credentials.json`, `test_foo.env`) is
# a fixture filename and allowed — but this is checked on the basename ONLY (in
# `_path_is_sensitive`), NOT as a path substring. The old `/test_` substring
# exception fell OPEN on a real `.env` secret living under a `test_`-prefixed
# DIRECTORY segment (e.g. `config/test_env/.env`), which must stay blocked.
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


# Command-chain separators: `&&`, `||`, single `|`, `;`, and newline. Kept as
# one shared splitter (P13) so the force-push and destructive-rm checks agree
# on what "a single command segment" means. This is deliberately NOT a shell
# tokenizer — it does not honor quoting, here-docs, `$(...)`, or backslash
# continuations. The bias is false-NEGATIVE: when the split is ambiguous we
# would rather UNDER-block than over-block, because this guard is a fat-finger
# guardrail, not a security boundary (see module docstring).
_SEGMENT_SPLIT = re.compile(r"&&|\|\||\||;|\n")
# A trailing `#` comment is stripped only when the `#` sits at a token boundary
# (start-of-segment or after whitespace). Mid-token `#` (e.g. `url#frag`,
# `issue-#5`) is left intact so we never silently drop a real argument.
_TRAILING_COMMENT = re.compile(r"(?:^|\s)#.*$")


def _command_segments(command: str) -> list[str]:
    """Split a shell command string into best-effort command segments.

    Splits on `&&`, `||`, `|`, `;`, and newline, then conservatively strips a
    trailing `#`-comment from each segment (only when the `#` is at a token
    boundary). Empty/whitespace-only segments are dropped. Shared by the
    force-push and destructive-rm checks so both reason over the SAME notion of
    a single command (P13).

    Intentionally not a shell parser: quoting/here-docs/`$(...)` are not
    honored. False-NEGATIVE bias — an ambiguous case under-blocks rather than
    over-blocks (fat-finger guardrail, not a security boundary).
    """
    segments: list[str] = []
    for raw in _SEGMENT_SPLIT.split(command):
        seg = _TRAILING_COMMENT.sub("", raw).strip()
        if seg:
            segments.append(seg)
    return segments


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
    """Return matched description if the command is destructive, else None.

    Segment-scoped + anchored (P13), mirroring `_check_force_push`: each
    DESTRUCTIVE_PATTERN is applied with `pattern.match` (anchored at position 0)
    to the wrapper-stripped head of every command SEGMENT, so the segment must
    BEGIN with the destructive subcommand. This one change fixes both directions
    of the old whole-command unanchored `.search`:

      * false-NEGATIVE — `git checkout . && echo done` (and the `;`/`||`/`|`
        variants) is now segmented, so the isolated `git checkout .` segment is
        matched and BLOCKED; the chain operator no longer hides it past the
        terminator.
      * false-POSITIVE — `echo "git reset --hard"` / `git commit -m '...git
        clean -fd...'` now have a non-git segment head, so the anchored match
        fails and they are ALLOWED (the destructive spelling is only quoted
        data passed to another command, not the segment's command word).

    Preserved blocks: bare `git reset --hard`, `cd x && git reset --hard` (via
    segment split), `sudo git reset --hard` (via wrapper strip). Accepted
    false-NEGATIVE (unchanged, by design): `git -C x reset --hard` — the same
    best-effort textual idiom and accepted residual as the force-push checks
    (see module docstring).
    """
    if _is_destructive_rm(command):
        return "rm -rf targeting filesystem root or home"
    # Reuse the force-push wrapper stripper (sudo/env prefixes) so a
    # `sudo git reset --hard` still anchors to the `git …` head.
    for segment in _command_segments(command):
        stripped = _strip_force_push_wrappers(segment)
        for pattern, description in DESTRUCTIVE_PATTERNS:
            if pattern.match(stripped):
                return description
    return None


# A force-push segment's command word is `git push`, optionally behind a small
# safe wrapper-prefix set (`sudo [-flags]`, `env [VAR=val] [-flags]`) stripped
# by `_strip_force_push_wrappers` before this anchor is applied. Anchoring to
# the segment's (post-strip) leading command keeps the force-push literal
# appearing only as QUOTED DATA to another command (e.g.
# `echo 'git push --force origin main'`) from tripping the gate: there the
# segment's command is `echo`, not git push.
#
# Accepted false-negative CLASS (still slips, by design — this is a fat-finger
# guardrail, NOT a security boundary, see module docstring): any segment whose
# effective head after stripping the sudo/env wrapper set is not literally
# `git` — e.g. `xargs`/`time`/`nice` wrappers, `sudo -u <user>` option-argument
# forms (the non-flag `<user>` token stops the strip), and shell aliases.
_SEGMENT_IS_GIT_PUSH = re.compile(r"^git\s+push\b")


def _strip_force_push_wrappers(segment: str) -> str:
    """Strip a small, safe wrapper-prefix set from a command segment's head so
    `sudo git push …` / `env VAR=v git push …` are recognised as git-push
    invocations by the `^git\\s+push` anchor.

    Stripped (simple whitespace tokenization — deliberately NOT shlex/a real
    shell parser, to stay consistent with this file's best-effort textual
    idiom):
      * leading `sudo` token(s), plus any immediately following BARE option
        tokens (tokens starting with `-`, e.g. `sudo -E`),
      * leading `env` token, plus any following `VAR=value` assignment tokens
        and bare option tokens (e.g. `env GIT_DIR=/tmp/x`).

    Known honest residual (ACCEPTED): an option-with-argument form like
    `sudo -u alice git push …` stops at the non-flag `alice` token — the strip
    leaves `-u alice git push …`, which the anchor rejects, so it slips. We do
    NOT build argument-aware option parsing (see module docstring).
    """
    tokens = segment.split()
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok == "sudo":
            i += 1
            # Consume immediately-following bare option flags (e.g. `-E`).
            while i < len(tokens) and tokens[i].startswith("-"):
                i += 1
            continue
        if tok == "env":
            i += 1
            # Consume following `VAR=value` assignments and bare option flags.
            while i < len(tokens) and (
                tokens[i].startswith("-") or "=" in tokens[i]
            ):
                i += 1
            continue
        break
    return " ".join(tokens[i:])


def _check_force_push(command: str) -> bool:
    """Return True if the command force-pushes to a protected branch.

    Segment-scoped (P13): the `git push`, a force flag, and the `main`/`master`
    token must all co-occur within a SINGLE command segment (split on `&&`,
    `||`, `|`, `;`, newline). Before the leading-command anchor is applied, a
    small safe wrapper-prefix set (`sudo [-flags]`, `env [VAR=val] [-flags]`)
    is stripped from the segment head (`_strip_force_push_wrappers`) so a
    privileged/env-wrapped push is still recognised; the force-push checks then
    run against the STRIPPED segment. Two false-positives are thereby avoided:

      * cross-segment — `git push --force origin feat && git switch main`: the
        force flag and `main` live in different segments, so no single segment
        satisfies all three tokens.
      * quoted data — `echo 'git push --force origin main' >> notes.txt`: the
        force-push spelling is only an argument to `echo`; the segment's
        command word (after stripping) is not `git push`, so it is ignored.

    Accepted false-NEGATIVE class: any segment whose effective head after
    stripping the sudo/env wrapper set is not literally `git` slips — e.g.
    `xargs`/`time`/`nice` wrappers, `sudo -u <user>` option-argument forms,
    shell aliases. Acceptable for a fat-finger guardrail (see module docstring).
    """
    for segment in _command_segments(command):
        stripped = _strip_force_push_wrappers(segment)
        if not _SEGMENT_IS_GIT_PUSH.match(stripped):
            continue
        if any(pattern.search(stripped) for pattern in FORCE_PUSH_PATTERNS):
            return True
    return False


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
    # A `test_`-prefixed BASENAME is a fixture filename (allowed) — scoped to
    # the basename so a real `.env` under a `test_`-prefixed DIRECTORY segment
    # (e.g. `config/test_env/.env`) is NOT exempted (the old `/test_` substring
    # exception fell open on exactly that path).
    if os.path.basename(lowered).startswith("test_"):
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

    # ---- Read + write-class file tools ----
    # `Read` is kept as an EXPLICIT, separate reference rather than folded
    # into WRITE_TOOLS (it is not a write tool — see _athanor_hook_runtime).
    # The write-class tools (Write/Edit/MultiEdit/NotebookEdit) come from the
    # shared WRITE_TOOLS tuple so the credential gate covers all of them; the
    # target path is resolved via `extract_target_path` so NotebookEdit's
    # `notebook_path` key is honored (every other tool uses `file_path`).
    if tool_name in ({"Read"} | set(_runtime.WRITE_TOOLS)):
        path = _runtime.extract_target_path(tool_name, tool_input)
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
