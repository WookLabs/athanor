#!/usr/bin/env python3
r"""
check_release_ready.py — cross-platform release gate for Athanor.

Runs four assertions and, on full success, writes a fresh
`live-session-evidence.md` into the latest `.athanor/sessions/<id>/`
directory. Exit 0 if all pass (and evidence written unless
--skip-evidence); non-zero otherwise.

Checks:
  (a) Session work-log.md contains a structured `## v<version>` section
      header matching the current plugin.json version. Binds the
      evidence to THIS release: pure-prose mentions of the version
      (e.g. "candidate for v0.7.1") no longer satisfy the gate. Regex
      `^##\s*v?{VERSION}\b` is word-boundary-terminated so `0.7.1` does
      NOT match `10.7.1` or `0.7.10`. On success, a fresh
      `live-session-evidence.md` is written below.
  (b) CHANGELOG.md has an entry for the current plugin.json version.
  (c) No duplicate hook declaration in .claude-plugin/plugin.json
      (delegated to scripts.gates.manifest_checks.duplicate_hooks_path_check).
  (d) Latest session's contract-ledger.md exists and is >= 500 bytes.
  (e) v0.12.0 — exactly 1 vendored skill survives on disk
      (`ce-test-browser` per D8). Counts depth-1 `skills/ce-*` and
      `skills/sp-*` directories.
  (f) v0.12.0 — marketplace.json parses and its declared plugins shape
      is reported alongside the on-disk skill-directory count.
  (g) v0.12.0 — `concepts/` directory exists with >= 7 inventory files
      (1 README + 6 numbered concept files).

Modes:
  default                  run all seven checks (local pre-tag use)
  --ci                     run (b)+(c)+(e)+(f)+(g); skip (a)+(d) which
                           need .athanor/ session artifacts gitignored
                           and absent in CI fresh checkouts. No evidence.
  --skip-evidence          run all checks but don't write evidence.
  --session <YYYY-MM-DD-NNN>
                           override latest-session auto-detection. Use
                           to point check_a at an older session whose
                           work-log carries the expected `## v<version>`
                           anchor. Missing session dir → clean exit 2,
                           no traceback.

Stdlib only, Python 3.10+. All file I/O uses encoding='utf-8' to
avoid the Windows cp949 default.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Resolve repo root relative to this script's location so invocation
# from any working directory still works.
REPO_ROOT = Path(__file__).resolve().parent.parent
# Ensure `from scripts.gates...` imports work when run as a top-level script.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
PLUGIN_JSON = REPO_ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE_JSON = REPO_ROOT / ".claude-plugin" / "marketplace.json"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
SESSIONS_DIR = REPO_ROOT / ".athanor" / "sessions"
SKILLS_DIR = REPO_ROOT / "skills"
CONCEPTS_DIR = REPO_ROOT / "concepts"

# v0.12.0 post-cutover invariant: exactly one vendored skill survives
# (`ce-test-browser` per D8 — no athanor-native equivalent for browser
# automation). All other ce-* / sp-* directories were removed in the
# atomic cut.
VENDORED_SKILL_KEEP = "ce-test-browser"
EXPECTED_VENDORED_SKILL_COUNT = 1

# v0.12.0 Phase 3 lifted 5 numbered concept files + a README. The release
# gate uses `>= 7` rather than `== 7` so adding new reference material does
# not bump the gate; the lower bound is what matters.
CONCEPTS_MIN_FILE_COUNT = 7

SESSION_NAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{3}$")


def read_text(path: Path) -> str:
    with path.open(encoding="utf-8") as f:
        return f.read()


def read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _work_log_has_version_anchor(work_log_path: Path, version: str) -> bool:
    """Returns True if work_log_path contains a line matching
    ^##\\s*v?{VERSION}\\b (MULTILINE). False if file missing or no match.
    Word-boundary prevents 0.7.1 from matching 10.7.1 or 0.7.10."""
    if not work_log_path.is_file():
        return False
    try:
        text = work_log_path.read_text(encoding="utf-8")
    except OSError:
        return False
    pattern = re.compile(rf"^##\s*v?{re.escape(version)}\b", re.MULTILINE)
    return bool(pattern.search(text))


def latest_session_dir() -> Path | None:
    if not SESSIONS_DIR.is_dir():
        return None
    candidates = [
        p for p in SESSIONS_DIR.iterdir()
        if p.is_dir() and SESSION_NAME_RE.match(p.name)
    ]
    if not candidates:
        return None
    # Lexicographic sort works because YYYY-MM-DD-NNN is zero-padded.
    return max(candidates, key=lambda p: p.name)


def get_version() -> str | None:
    try:
        return read_json(PLUGIN_JSON).get("version")
    except (OSError, json.JSONDecodeError):
        return None


# ---------- checks ----------

def check_a_evidence(session: Path | None, version: str | None) -> tuple[bool, str]:
    """(a) Evidence is written by a successful run, so during the
    check phase we only verify the session directory is writable
    and that work-log.md contains a structured '## v<version>' anchor.
    The actual evidence file is produced at the end on success."""
    # v0.18.6 (bug hunt R4): fail-loud on an unreadable version instead of
    # coercing to "" below — an empty version turns the anchor regex into
    # `^##\s*v?\b`, which any `## ` header satisfies, masking the real cause.
    if version is None:
        return False, "could not read version from plugin.json (version is None)"
    if session is None:
        return False, "no session directory found under .athanor/sessions/"
    if not session.is_dir():
        return False, f"latest session path is not a directory: {session}"
    work_log = session / "work-log.md"
    if not work_log.is_file():
        return False, (
            f"session work-log.md missing; create it with a '## v{version}' section "
            f"OR pass --session <id> pointing at an older session with the expected anchor"
        )
    if not _work_log_has_version_anchor(work_log, version or ""):
        return False, (
            f"session work-log.md does not contain a '## v{version}' section header; "
            f"add the header OR pass --session <id>"
        )
    # Writable check — try touching a tempfile name. Don't actually create
    # it; trust that a directory that exists is writable unless we hit
    # permission errors at write time.
    return True, f"session dir ready: {session.name} (evidence will be written on success)"


def check_b_changelog(version: str | None) -> tuple[bool, str]:
    if version is None:
        return False, "could not read version from plugin.json"
    if not CHANGELOG.is_file():
        return False, "CHANGELOG.md not found"
    text = read_text(CHANGELOG)
    # Match either a released entry "## [0.7.0]" or an unreleased entry
    # "## [Unreleased — v0.7.0]" style. Either counts as an entry for
    # the current version.
    released = re.compile(rf"^##\s*\[\s*{re.escape(version)}\s*\]", re.MULTILINE)
    # v0.18.6 (bug hunt R3): `(?![0-9.])` right-boundary so v0.18.5 does not
    # match an Unreleased entry for v0.18.50 (the trailing `[^\]]*` previously
    # swallowed the extra digit). Mirrors the released matcher's `\s*\]` tightness.
    unreleased = re.compile(
        rf"^##\s*\[\s*Unreleased[^\]]*v?{re.escape(version)}(?![0-9.])[^\]]*\]",
        re.MULTILINE,
    )
    if released.search(text) or unreleased.search(text):
        return True, f"CHANGELOG.md has an entry for v{version}"
    return False, f"CHANGELOG.md has no entry for v{version}"


def check_c_duplicate_hooks() -> tuple[bool, str]:
    from scripts.gates.manifest_checks import duplicate_hooks_path_check
    return duplicate_hooks_path_check(PLUGIN_JSON, REPO_ROOT)


def check_e_vendored_skill_count() -> tuple[bool, str]:
    """(e) v0.12.0 atomic-cut invariant — exactly one vendored skill
    survives on disk: `ce-test-browser` (D8 KEEP).

    Counts depth-1 `skills/ce-*` and `skills/sp-*` directories. Any other
    survivor signals a partial-removal regression."""
    if not SKILLS_DIR.is_dir():
        return False, f"{SKILLS_DIR.relative_to(REPO_ROOT)} missing"
    survivors = sorted(
        p.name for p in SKILLS_DIR.iterdir()
        if p.is_dir() and (
            p.name.startswith("ce-") or p.name.startswith("sp-")
        )
    )
    count = len(survivors)
    if count != EXPECTED_VENDORED_SKILL_COUNT:
        return False, (
            f"expected exactly {EXPECTED_VENDORED_SKILL_COUNT} vendored "
            f"skill ({VENDORED_SKILL_KEEP!r}); found {count}: {survivors!r}"
        )
    if survivors != [VENDORED_SKILL_KEEP]:
        return False, (
            f"expected {[VENDORED_SKILL_KEEP]!r}; found {survivors!r}"
        )
    return True, f"vendored skills: count={count} survivor={survivors[0]!r}"


def check_f_marketplace_skill_count() -> tuple[bool, str]:
    """(f) marketplace.json parses cleanly, declares the athanor plugin,
    and the on-disk skill surface is reported for honesty.

    marketplace.json currently lists a single 'plugins' entry (athanor
    itself, not per-skill rows). The gate's job is to (1) prove the file
    parses, (2) assert plugins[0].name == 'athanor' (the marketplace points
    at THIS plugin — a real structural invariant), and (3) report the
    on-disk product surface count (10 native + 2 internal + 1 vendored KEEP
    = 13). The count is reported, not hard-pinned, so adding/removing a
    skill does not require touching a brittle magic number here; a future
    per-skill expansion of marketplace.json will be cross-checked against it.
    """
    if not MARKETPLACE_JSON.is_file():
        return False, f"{MARKETPLACE_JSON.relative_to(REPO_ROOT)} missing"
    try:
        data = read_json(MARKETPLACE_JSON)
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"marketplace.json parse error: {exc}"
    plugins = data.get("plugins") if isinstance(data, dict) else None
    if not isinstance(plugins, list) or not plugins:
        return False, "marketplace.json 'plugins' array missing or empty"

    # Disk-side expectation: 10 native + 2 internal + 1 vendored KEEP = 13.
    if not SKILLS_DIR.is_dir():
        return False, f"{SKILLS_DIR.relative_to(REPO_ROOT)} missing"
    on_disk_skill_dirs = [
        p.name for p in SKILLS_DIR.iterdir()
        if p.is_dir() and (p / "SKILL.md").is_file()
    ]
    on_disk_count = len(on_disk_skill_dirs)
    # Real structural assertion: the marketplace's first plugin must be
    # athanor itself. A no-op gate that always returned True (pre-v0.18.8)
    # could not catch a misnamed/empty marketplace entry.
    mkt_name = plugins[0].get("name") if isinstance(plugins[0], dict) else None
    if mkt_name != "athanor":
        return False, (
            f"marketplace.json plugins[0].name must be 'athanor'; got {mkt_name!r}"
        )
    # The marketplace surface is computed from disk; if the JSON ever grows
    # a per-skill listing, that listing must match this count.
    return True, (
        f"marketplace-skill-count: plugins[0].name={mkt_name!r} "
        f"disk-skill-dirs={on_disk_count}"
    )


def check_g_concepts_present() -> tuple[bool, str]:
    """(g) v0.12.0 Phase 3 invariant — concepts/ directory exists and
    holds at least 7 inventory files (1 README + 6 numbered concepts)."""
    if not CONCEPTS_DIR.is_dir():
        return False, (
            f"{CONCEPTS_DIR.relative_to(REPO_ROOT)} missing — Phase 3 "
            f"LIFT inventory absent"
        )
    files = [p for p in CONCEPTS_DIR.iterdir() if p.is_file()]
    count = len(files)
    if count < CONCEPTS_MIN_FILE_COUNT:
        return False, (
            f"concepts/ holds {count} files; expected >= "
            f"{CONCEPTS_MIN_FILE_COUNT}"
        )
    return True, f"concepts-present: file_count={count}"


def check_d_contract_ledger(session: Path | None) -> tuple[bool, str]:
    if session is None:
        return False, "no session directory found"
    ledger = session / "contract-ledger.md"
    if not ledger.is_file():
        return False, f"{ledger.relative_to(REPO_ROOT)} does not exist"
    size = ledger.stat().st_size
    if size < 500:
        return False, f"{ledger.relative_to(REPO_ROOT)} is only {size} bytes (< 500)"
    return True, f"{ledger.relative_to(REPO_ROOT)} present ({size} bytes)"


# ---------- evidence writer ----------

def write_evidence(
    session: Path,
    version: str | None,
    source_cmd: str,
    results: list[tuple[str, bool, str]],
) -> Path:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    path = session / "live-session-evidence.md"
    lines: list[str] = []
    lines.append("# Live Session Evidence")
    lines.append("")
    lines.append(f"- Generated: {timestamp}")
    lines.append(f"- Plugin version: {version or 'unknown'}")
    lines.append(f"- Source command: `{source_cmd}`")
    lines.append(f"- Session: {session.name}")
    lines.append("")
    lines.append("## Release-gate checks")
    lines.append("")
    lines.append("| Check | Result | Detail |")
    lines.append("|-------|--------|--------|")
    for key, ok, detail in results:
        status = "pass" if ok else "fail"
        safe_detail = detail.replace("|", "\\|")
        lines.append(f"| {key} | {status} | {safe_detail} |")
    lines.append("")
    lines.append("_Produced by `scripts/check_release_ready.py`._")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# ---------- entry point ----------

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="check_release_ready.py",
        description="Athanor release-ready gate.",
        add_help=True,
    )
    parser.add_argument("--skip-evidence", action="store_true",
                        help="run checks but do not write live-session-evidence.md")
    parser.add_argument("--ci", action="store_true",
                        help="CI mode: run only changelog+manifest checks; skip session-dependent checks")
    parser.add_argument("--session", metavar="SESSION_ID", default=None,
                        help="explicit session id under .athanor/sessions/ (default: latest)")
    args = parser.parse_args(argv[1:])

    ci_mode = args.ci
    skip_evidence = args.skip_evidence or ci_mode

    source_cmd = " ".join(argv)
    version = get_version()
    if args.session is not None:
        session = SESSIONS_DIR / args.session
        if not session.is_dir():
            print(f"session directory not found: {args.session}", file=sys.stderr)
            return 2
    else:
        session = latest_session_dir()

    checks: list[tuple[str, bool, str]] = []
    if ci_mode:
        # CI fresh checkout has no .athanor/ (gitignored), so (a) and (d)
        # are structurally inapplicable. Run only the contract-independent
        # checks so CI can still catch CHANGELOG and manifest regressions.
        b_ok, b_msg = check_b_changelog(version)
        checks.append(("(b) changelog-entry", b_ok, b_msg))
        c_ok, c_msg = check_c_duplicate_hooks()
        checks.append(("(c) no-duplicate-hooks", c_ok, c_msg))
        # v0.12.0 Phase 6 surface gates.
        e_ok, e_msg = check_e_vendored_skill_count()
        checks.append(("(e) vendored-skill-count", e_ok, e_msg))
        f_ok, f_msg = check_f_marketplace_skill_count()
        checks.append(("(f) marketplace-skill-count", f_ok, f_msg))
        g_ok, g_msg = check_g_concepts_present()
        checks.append(("(g) concepts-present", g_ok, g_msg))
    else:
        a_ok, a_msg = check_a_evidence(session, version)
        checks.append(("(a) evidence-ready", a_ok, a_msg))
        b_ok, b_msg = check_b_changelog(version)
        checks.append(("(b) changelog-entry", b_ok, b_msg))
        c_ok, c_msg = check_c_duplicate_hooks()
        checks.append(("(c) no-duplicate-hooks", c_ok, c_msg))
        d_ok, d_msg = check_d_contract_ledger(session)
        checks.append(("(d) contract-ledger", d_ok, d_msg))
        # v0.12.0 Phase 6 surface gates — also run in default (local) mode
        # so pre-tag validation catches the same regressions as CI.
        e_ok, e_msg = check_e_vendored_skill_count()
        checks.append(("(e) vendored-skill-count", e_ok, e_msg))
        f_ok, f_msg = check_f_marketplace_skill_count()
        checks.append(("(f) marketplace-skill-count", f_ok, f_msg))
        g_ok, g_msg = check_g_concepts_present()
        checks.append(("(g) concepts-present", g_ok, g_msg))

    all_ok = all(ok for _, ok, _ in checks)

    print("Athanor release-ready gate" + (" (ci mode)" if ci_mode else ""))
    print(f"  repo: {REPO_ROOT}")
    print(f"  version: {version or '<unknown>'}")
    if not ci_mode:
        session_label = "session" if args.session is not None else "latest session"
        print(f"  {session_label}: {session.name if session else '<none>'}")
    print()
    for key, ok, detail in checks:
        tag = "PASS" if ok else "FAIL"
        print(f"  [{tag}] {key}: {detail}")
    print()

    if all_ok and not skip_evidence:
        if session is None:
            print("internal error: all checks passed but no session to write evidence", file=sys.stderr)
            return 1
        evidence_path = write_evidence(session, version, source_cmd, checks)
        rel = evidence_path.relative_to(REPO_ROOT)
        print(f"evidence written: {rel}")
        return 0

    if all_ok:
        tag = "(--ci: evidence skipped)" if ci_mode else "(--skip-evidence: no file written)"
        print(f"all checks passed {tag}")
        return 0

    print("release gate: FAIL", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
