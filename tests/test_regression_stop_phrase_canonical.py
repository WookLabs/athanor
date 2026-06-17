"""Regression test for the canonical stop-phrase whitelist (Phase 6 / P10).

P10 finding: the leader-side worker-output stop-phrase whitelist (5 ko/en
phrases) was duplicated VERBATIM across ~7 skill/reference files and partially
embedded in docs/agent-roles/reviewer.md. The copies had begun to drift. Phase 6 creates
one canonical doc (docs/stop-phrase-whitelist.md) and replaces every skill-side
embedding with a 1-line pointer.

Four invariants pinned here:
  1. docs/stop-phrase-whitelist.md exists and contains all 5 canonical phrases
     in BOTH Korean and English forms.
  2. No single skill file under skills/ re-embeds the list: a file containing
     >= 3 of the 5 canonical phrases indicates a re-embedded enumeration
     (rather than a legitimate illustrative/contextual mention of 1-2 phrases).
  3. agents/ is EXEMPT from assertion 2 — agent docs MAY carry short
     illustrative excerpts (per docs/stop-phrase-whitelist.md §"Agent-doc
     exemption policy"). The exemption is documented here so a future refactor
     does not silently fold agents/ back into the skills/ scope.
  4. The CLAUDE.md stop-phrase pointer resolves to docs/stop-phrase-whitelist.md
     (the pointer target must actually exist on disk).

Plan reference: Phase 6 Steps 6.1-6.5 (P10 stop-phrase de-duplication).
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WHITELIST_DOC = REPO_ROOT / "docs" / "stop-phrase-whitelist.md"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
SKILLS_DIR = REPO_ROOT / "skills"

# The 5 canonical phrases, each as (Korean, English).
CANONICAL_PHRASES = [
    ("이 정도면 멈춰도 될 것 같습니다", "I think we can stop here"),
    ("계속할까요?", "Should I continue?"),
    ("기존 이슈입니다", "This is a pre-existing issue"),
    ("새 세션에서 계속", "Let's continue in a new session"),
    ("좋은 체크포인트", "Good checkpoint"),
]

# Flattened ko-only forms, used to count re-embedding in skill files.
# Korean forms are the strongest fingerprint of a verbatim re-embedding.
KOREAN_PHRASES = [ko for ko, _en in CANONICAL_PHRASES]


def test_whitelist_doc_has_all_five_ko_en_phrases() -> None:
    """Assertion 1: docs/stop-phrase-whitelist.md exists and lists all 5
    canonical phrases in BOTH Korean and English."""
    assert WHITELIST_DOC.exists(), (
        f"Canonical whitelist doc must exist at "
        f"docs/stop-phrase-whitelist.md (Phase 6 Step 6.1)"
    )
    body = WHITELIST_DOC.read_text(encoding="utf-8")
    for ko, en in CANONICAL_PHRASES:
        assert ko in body, (
            f"docs/stop-phrase-whitelist.md missing Korean form: {ko!r}"
        )
        assert en in body, (
            f"docs/stop-phrase-whitelist.md missing English form: {en!r}"
        )


def test_no_skill_file_reembeds_the_whitelist() -> None:
    """Assertion 2: no skill file under skills/ contains >= 3 of the 5
    canonical phrases (>= 3 indicates a re-embedded enumeration rather than
    an illustrative mention). Each embedding must instead point at
    docs/stop-phrase-whitelist.md."""
    offenders = []
    for md in sorted(SKILLS_DIR.rglob("*.md")):
        body = md.read_text(encoding="utf-8")
        hits = [ko for ko in KOREAN_PHRASES if ko in body]
        if len(hits) >= 3:
            rel = md.relative_to(REPO_ROOT)
            offenders.append((str(rel), hits))
    assert not offenders, (
        "These skill files still re-embed >= 3 canonical stop-phrases "
        "instead of pointing at docs/stop-phrase-whitelist.md: "
        f"{offenders}"
    )


def test_agents_are_carved_out_of_the_reembed_scope() -> None:
    """Assertion 3: the re-embed scope (assertion 2) is explicitly limited to
    skills/. agents/*.md are EXEMPT — they may carry short illustrative
    excerpts (1-2 phrases) plus a pointer. This test documents and locks that
    carve-out: the canonical doc must spell out the agent-doc exemption, and
    the exemption is asserted to apply to the agents/ tree (not skills/)."""
    body = WHITELIST_DOC.read_text(encoding="utf-8")
    body_lower = body.lower()
    # The canonical doc must document the agent-doc exemption explicitly.
    assert "agent-doc exemption" in body_lower or "agents/*.md" in body, (
        "docs/stop-phrase-whitelist.md must document the agent-doc "
        "exemption policy (agents/*.md may carry short illustrative excerpts)."
    )
    # Sanity: the carve-out is about agents/, and the enforced scope is skills/.
    assert "agents/" in body, (
        "Exemption policy must name the agents/ tree it exempts."
    )
    assert SKILLS_DIR.is_dir(), "skills/ is the enforced re-embed scope."


def test_claude_md_pointer_resolves_to_whitelist_doc() -> None:
    """Assertion 4: the CLAUDE.md stop-phrase pointer references
    docs/stop-phrase-whitelist.md, and that target actually exists on disk."""
    body = CLAUDE_MD.read_text(encoding="utf-8")
    assert "docs/stop-phrase-whitelist.md" in body, (
        "CLAUDE.md must point the stop-phrase whitelist at "
        "docs/stop-phrase-whitelist.md (Phase 6 Step 6.2)."
    )
    assert WHITELIST_DOC.exists(), (
        "CLAUDE.md pointer target docs/stop-phrase-whitelist.md does not "
        "resolve to an existing file."
    )
