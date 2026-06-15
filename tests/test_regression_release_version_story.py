"""Regression tests for release/version ownership.

Feature, fix, and docs branches may mention future release names, but version
pins are owned by an explicit release ceremony. This prevents ordinary
implementation work from silently becoming a partial release pass.
"""
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CONVENTIONS = REPO_ROOT / "docs" / "CONVENTIONS.md"
RELEASER = REPO_ROOT / "agents" / "releaser.md"
CODEX_RELEASE = (
    REPO_ROOT
    / "plugins"
    / "athanor-codex"
    / "skills"
    / "athanor-release"
    / "SKILL.md"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalize_ws(text: str) -> str:
    return " ".join(text.split())


def test_conventions_define_release_specific_version_ownership() -> None:
    """The repo conventions must say version pins belong to release passes."""
    text = _normalize_ws(_read(CONVENTIONS))
    required = [
        "Release/version ownership",
        "feature/fix/docs",
        "release-specific pass",
        ".claude-plugin/plugin.json",
        ".claude-plugin/marketplace.json",
        "athanor.json",
        "templates/athanor.json",
        "schemas/athanor-config.schema.json",
        "CHANGELOG.md",
        "docs/STATE.md",
        "v0.19.0",
    ]
    missing = [token for token in required if token not in text]
    assert not missing, (
        "docs/CONVENTIONS.md must lock release-version ownership; "
        f"missing tokens: {missing}"
    )


def test_releaser_requires_explicit_release_request_before_bump() -> None:
    """The Claude release worker must not turn ordinary work into a bump."""
    text = _normalize_ws(_read(RELEASER))
    required = [
        "explicit release request",
        "target version",
        "ship date",
        "CHANGELOG entry",
        "ordinary feature/fix/docs work",
        "Do NOT run Step 1",
    ]
    missing = [token for token in required if token not in text]
    assert not missing, (
        "agents/releaser.md must gate version bumps behind an explicit "
        f"release request; missing tokens: {missing}"
    )


def test_releaser_documents_nested_marketplace_version_field() -> None:
    """The Claude release worker must describe the actual marketplace shape."""
    text = _read(RELEASER)
    normalized = _normalize_ws(text)
    assert ".claude-plugin/marketplace.json" in normalized
    assert "plugins[0].version" in normalized
    forbidden = [
        "**`marketplace.json`** — top-level",
        "`marketplace.json`: top-level",
    ]
    hits = [token for token in forbidden if token in text]
    assert not hits, (
        "agents/releaser.md must not describe marketplace version as a "
        f"top-level field: {hits}"
    )


def test_codex_release_skill_mirrors_version_ownership_policy() -> None:
    """The Codex release mirror must preserve the same bump boundaries."""
    raw = _read(CODEX_RELEASE)
    text = _normalize_ws(raw)
    required = [
        "explicit release request",
        "ordinary feature/fix/docs work",
        "Do NOT perform the 5-file version bump",
        "plugins[0].version",
        "release-specific pass",
    ]
    missing = [token for token in required if token not in text]
    assert not missing, (
        "Codex release skill must mirror release-version ownership policy; "
        f"missing tokens: {missing}"
    )
    assert "`marketplace.json`: top-level" not in raw, (
        "Codex release skill must not describe marketplace version as top-level"
    )
