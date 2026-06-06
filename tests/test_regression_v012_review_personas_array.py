"""Regression: v0.12.0 — review skill personas + doc-review mode lifted from
compound-engineering 3.8.3 + schema gains review.personas enum.

Subtask 8 of the v0.12.0 concept-kernel cutover plan (RED-first per
spec-then-tdd execution_note). Locks three properties:

1. `skills/review/SKILL.md` declares a §Personas subsection enumerating
   exactly 6 athanor-native reviewer personas (vocabulary-compressed
   subset of CE's 18) AND an Attribution subsection naming CE +
   Kieran Klaassen.
2. The same SKILL.md adds a §"Doc review mode" subsection enumerating
   the 7 doc-mode personas inherited from CE's `ce-doc-review`.
3. `schemas/athanor-config.schema.json`'s `review` object accepts an
   optional `personas` array whose items enum to those 6 names; unknown
   values (e.g. `"foo"`) are rejected by the schema.

The 6 code personas: correctness, security, performance, testing,
maintainability, adversarial.
The 7 doc personas: coherence, feasibility, scope-guardian, product-lens,
security-lens, design-lens, adversarial-document.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

REPO_ROOT = Path(__file__).resolve().parent.parent
REVIEW_SKILL = REPO_ROOT / "skills" / "review" / "SKILL.md"
REVIEW_SECTIONS = REPO_ROOT / "skills" / "review" / "references" / "review-sections.md"
SCHEMA_PATH = REPO_ROOT / "schemas" / "athanor-config.schema.json"

CODE_PERSONAS = [
    "correctness",
    "security",
    "performance",
    "testing",
    "maintainability",
    "adversarial",
]

DOC_PERSONAS = [
    "coherence",
    "feasibility",
    "scope-guardian",
    "product-lens",
    "security-lens",
    "design-lens",
    "adversarial-document",
]


def _read_skill() -> str:
    # v0.18.3: §Personas + §Doc review mode were carved to
    # references/review-sections.md (gstack-style STOP-Read). The persona
    # contract is preserved across the skill router + carved section, so this
    # regression reads both as the logical review surface.
    body = REVIEW_SKILL.read_text(encoding="utf-8")
    if REVIEW_SECTIONS.is_file():
        body += "\n" + REVIEW_SECTIONS.read_text(encoding="utf-8")
    return body


def _read_schema() -> dict:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_personas_section_present_with_6_personas():
    """MUST 1 — skills/review/SKILL.md declares §Personas + 6 names + CE attribution."""
    body = _read_skill()

    # §Personas heading present (allow ## or ### level).
    assert re.search(r"^#{2,3}\s+Personas\s*$", body, flags=re.MULTILINE), (
        "skills/review/SKILL.md must contain a 'Personas' section heading"
    )

    # Each of the 6 code personas must appear as a `### Persona: <name>` subsection.
    for name in CODE_PERSONAS:
        pattern = rf"^#{{3,4}}\s+Persona:\s+{re.escape(name)}\s*$"
        assert re.search(pattern, body, flags=re.MULTILINE), (
            f"Personas section must include '### Persona: {name}' subsection"
        )

    # Attribution must mention CE + Kieran Klaassen explicitly.
    assert "compound-engineering" in body, (
        "Attribution must cite 'compound-engineering'"
    )
    assert "Kieran Klaassen" in body, (
        "Attribution must cite 'Kieran Klaassen' (CE copyright holder)"
    )

    # Articulate vocabulary-compressed subset claim — the 6 personas are not
    # a verbatim copy of CE's 18 but a deliberate compression.
    assert "vocabulary-compressed" in body or "compressed subset" in body, (
        "Attribution must articulate that the 6 personas are a "
        "vocabulary-compressed subset of CE's 18 reviewer personas"
    )


def test_doc_review_mode_subsection_lists_7_personas():
    """MUST 2 — skills/review/SKILL.md adds §Doc review mode + 7 doc personas."""
    body = _read_skill()

    assert re.search(r"^#{2,3}\s+Doc review mode\s*$", body, flags=re.MULTILINE), (
        "skills/review/SKILL.md must contain a 'Doc review mode' section heading"
    )

    for name in DOC_PERSONAS:
        assert name in body, (
            f"Doc review mode section must enumerate doc persona '{name}'"
        )

    # CLI invocation contract documented.
    assert "--target docs" in body, (
        "Doc review mode must document the '--target docs' CLI invocation"
    )
    assert "--target code" in body, (
        "Doc review mode must document the default '--target code' invocation"
    )


def test_schema_accepts_6_persona_enum_rejects_unknown():
    """MUST 3 — schema gains review.personas array enum; rejects unknown values."""
    schema = _read_schema()

    review_props = schema["properties"]["review"]["properties"]
    assert "personas" in review_props, (
        "review object must declare a 'personas' property"
    )

    personas_schema = review_props["personas"]
    assert personas_schema["type"] == "array"
    assert personas_schema.get("uniqueItems") is True, (
        "review.personas must enforce uniqueItems: true"
    )
    assert personas_schema.get("minItems", 0) == 0, (
        "review.personas minItems should be 0 (optional set)"
    )
    enum = personas_schema["items"]["enum"]
    assert sorted(enum) == sorted(CODE_PERSONAS), (
        f"review.personas enum must equal {sorted(CODE_PERSONAS)}, got {sorted(enum)}"
    )

    # Positive case — full 6-persona array validates.
    good_instance = {
        "version": "1.0",
        "review": {"personas": CODE_PERSONAS},
    }
    jsonschema.validate(instance=good_instance, schema=schema)

    # Negative case — unknown enum value rejected.
    bad_instance = {
        "version": "1.0",
        "review": {"personas": ["foo"]},
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=bad_instance, schema=schema)

    # Backwards compat — existing review.lenses still validates alongside personas.
    coexist_instance = {
        "version": "1.0",
        "review": {
            "lenses": ["security", "architecture"],
            "personas": ["security", "adversarial"],
            "minConfidence": 25,
        },
    }
    jsonschema.validate(instance=coexist_instance, schema=schema)
