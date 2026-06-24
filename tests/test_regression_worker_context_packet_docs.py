"""Regression doc-pin for the slim Worker Context Packet convention.

After the PR #69 shrink this is the ONLY worker-context-packet test. It locks
honesty (no overclaims), reference integrity (the doc points at the real,
singly-sourced contracts), and that the restored CONVENTIONS/DESIGN dispatch
examples are present and discoverable. It deliberately does NOT pin a brittle
token whitelist — the convention doc's worth-keeping behavior is honesty +
cross-reference integrity, not a fixture-shaped field list.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs" / "worker-context-packets.md"

OVERCLAIM_FORBIDDEN = [
    "runtime-enforced registered agent",
    "registered agents validate before invoking",
    "Claude Task enforcement",
]


def test_slim_doc_has_no_overclaims() -> None:
    text = DOC.read_text(encoding="utf-8")
    for phrase in OVERCLAIM_FORBIDDEN:
        assert phrase not in text, f"slim doc must not overclaim: {phrase!r}"


def test_slim_doc_references_real_contracts() -> None:
    text = DOC.read_text(encoding="utf-8")
    for ref in ["splitter.md", "spec-then-tdd-handler.md", "freeze.md"]:
        assert ref in text, f"slim doc must reference {ref!r}"


def test_restored_examples_present_and_discoverable() -> None:
    conventions = (REPO_ROOT / "docs" / "CONVENTIONS.md").read_text(encoding="utf-8")
    design = (REPO_ROOT / "docs" / "DESIGN.md").read_text(encoding="utf-8")
    assert "You are an Athanor executor worker" in conventions
    assert 'subtask: "OTP' in design
    # Both restored examples keep a pointer back to the slim convention doc.
    for rel, text in (("docs/CONVENTIONS.md", conventions), ("docs/DESIGN.md", design)):
        assert "worker-context-packets.md" in text, rel
