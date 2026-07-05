"""Regression — migration guides carry staleness frontmatter + aging rule.

Context
-------
The lfg/lfg-loop doc-lifecycle audit found docs/ had NO staleness signal:
migration guides (v0.12.0 … v0.18.0) accumulate with no marker of which
are superseded, and nothing flags them for archival. Only CLAUDE.md had a
line-count guard.

Wave 3 introduces a lightweight, test-enforced aging mechanism:
1. Every `docs/v*-migration.md` carries `status: historical | current`
   frontmatter (and `superseded-by:` when historical).
2. Any guide for a minor older than the current plugin minor MUST be
   `historical` — this test is the automatic "ager": CI fails if an old
   guide is left marked current, prompting archival to docs/archive/.
3. `docs/CONVENTIONS.md` documents the rule.

Archival itself is a non-destructive move done at release time — this
test only flags; it never deletes.

Static text reads only — no subprocess, no file mutation.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"
PLUGIN = REPO_ROOT / ".claude-plugin" / "plugin.json"
CONVENTIONS = DOCS / "CONVENTIONS.md"


def _current_minor() -> int:
    version = json.loads(PLUGIN.read_text(encoding="utf-8"))["version"]
    return int(version.split(".")[1])


def _frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return ""
    parts = text.split("---", 2)
    return parts[1] if len(parts) >= 3 else ""


def _guides() -> list[Path]:
    return sorted(DOCS.glob("v*-migration.md"))


def test_migration_guides_have_status_frontmatter() -> None:
    """MUST — each migration guide declares status: historical|current."""
    guides = _guides()
    assert guides, "expected at least one docs/v*-migration.md guide"
    for g in guides:
        fm = _frontmatter(g.read_text(encoding="utf-8"))
        assert re.search(r"^\s*status:\s*(historical|current)\s*$", fm, re.M), (
            f"{g.name} must carry frontmatter 'status: historical|current' "
            f"— migration guides need an explicit staleness marker."
        )


def test_old_migration_guides_are_historical() -> None:
    """MUST — guides older than the current minor are historical + superseded.

    This is the automatic ager: a stale guide left as 'current' fails CI.
    """
    cur = _current_minor()
    for g in _guides():
        vm = re.search(r"v\d+\.(\d+)\.\d+-migration", g.name)
        assert vm, f"{g.name} does not match the vMAJOR.MINOR.PATCH-migration pattern"
        minor = int(vm.group(1))
        fm = _frontmatter(g.read_text(encoding="utf-8"))
        status_m = re.search(r"status:\s*(\w+)", fm)
        status = status_m.group(1) if status_m else None
        if minor < cur:
            assert status == "historical", (
                f"{g.name} (minor {minor}) is older than the current plugin "
                f"minor {cur} but status='{status}'. Stale migration guides "
                f"must be marked 'historical' (archive candidate)."
            )
            assert "superseded-by" in fm, (
                f"{g.name} is historical and must name a 'superseded-by:' "
                f"target so readers find the current guidance."
            )


def test_conventions_documents_migration_staleness() -> None:
    """MUST — CONVENTIONS.md documents the migration-guide staleness rule."""
    low = CONVENTIONS.read_text(encoding="utf-8").lower()
    assert "migration guide" in low and ("staleness" in low or "historical" in low), (
        "docs/CONVENTIONS.md must document the migration-guide staleness "
        "rule (status frontmatter + archive-candidate aging at release time)."
    )
