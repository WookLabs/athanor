"""Regression test for the canonical stop-phrase whitelist (Phase 6 / P10).

P10 finding: the leader-side worker-output stop-phrase whitelist (5 ko/en
phrases) was duplicated VERBATIM across ~7 skill/reference files and partially
embedded in agents/reviewer.md. The copies had begun to drift. Phase 6 creates
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


# The bare slug that fingerprints a stop-phrase-whitelist pointer line. It is a
# substring of the full canonical pointer path (POINTER_TARGET below), so any
# file that legitimately points at the doc contains BOTH.
WHITELIST_SLUG = "stop-phrase-whitelist"
# The full canonical pointer reference every member of the derived set must
# carry. Discovery is by the bare slug; the per-member assertion is the full
# path — a wider-discovery / narrower-assertion split so that corrupting a
# pointer's PATH (e.g. dropping the `docs/` prefix) while leaving the slug keeps
# the file in the derived set yet fails the assertion (a genuine RED), instead
# of silently dropping the file out of scope.
POINTER_TARGET = "docs/stop-phrase-whitelist.md"


def test_every_skill_pointer_member_carries_canonical_pointer() -> None:
    """Assertion 5 (M4 per-skill pointer-presence): the set of skill files
    that point at the canonical stop-phrase whitelist is DERIVED dynamically
    by rglobbing skills/ for *.md files containing the literal
    ``stop-phrase-whitelist`` slug — it is NOT a hardcoded path list.

    Why the derived set is canonical: the pointer pattern (a 1-line "see
    docs/stop-phrase-whitelist.md" reference replacing the formerly-embedded
    enumeration) is added/removed per skill as skills are authored or retired.
    A hardcoded membership list would silently go stale the moment a skill is
    added or removed — passing vacuously while the real tree diverged. Letting
    the live tree define the set at test time is the whole point: the assertion
    set is exactly "whatever in skills/ claims to carry the pointer right now."

    Two invariants are pinned:
      a. NON-EMPTY: the rglob must discover at least one member. An empty set
         (e.g. after a skills/ directory rename or a glob typo) must FAIL loud,
         not pass vacuously — a vacuous "every member is fine" over zero
         members would hide a total loss of coverage.
      b. COMPLETENESS: every discovered member must contain the FULL canonical
         pointer reference ``docs/stop-phrase-whitelist.md``. Because the slug
         is a substring of that path, a well-formed pointer satisfies both the
         discovery predicate and this assertion; a member that keeps the slug
         but corrupts/truncates the path (a half-broken pointer) stays in the
         derived set and fails here — the RED this guard exists to catch.
    """
    members = [
        md
        for md in sorted(SKILLS_DIR.rglob("*.md"))
        if WHITELIST_SLUG in md.read_text(encoding="utf-8")
    ]

    # Invariant (a): the derived set must be non-empty.
    assert members, (
        "No skills/*.md file contains the "
        f"{WHITELIST_SLUG!r} slug. The pointer set is derived dynamically by "
        "rglobbing skills/ — an empty result means the pointers vanished or "
        "skills/ moved/renamed. This must fail loud rather than pass "
        "vacuously over zero members."
    )

    # Invariant (b): every derived member carries the full canonical pointer.
    missing = [
        str(md.relative_to(REPO_ROOT))
        for md in members
        if POINTER_TARGET not in md.read_text(encoding="utf-8")
    ]
    assert not missing, (
        f"These skill files contain the {WHITELIST_SLUG!r} slug but not the "
        f"full canonical pointer {POINTER_TARGET!r} (a corrupted/truncated "
        f"pointer): {missing}"
    )
