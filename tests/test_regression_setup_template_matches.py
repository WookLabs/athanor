"""Regression: templates/athanor.json must mirror athanor.json's shape
at every nesting level. Top-level _doc text differs intentionally
(per §10.3 resolved decision); everything else must match exactly.

Closes plan §4 C4. The v0.7.6 drift surfaced specifically at
``models.debugger`` — nested, not top-level — so this test walks
recursively, not just top-level keys.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ROOT_CONFIG = REPO_ROOT / "athanor.json"
TEMPLATE_CONFIG = REPO_ROOT / "templates" / "athanor.json"


def _load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def collect_keypaths(obj, prefix: str = "") -> set[str]:
    """Return the set of dotted keypaths for every key in every nested object.

    Lists are walked positionally with ``[i]`` segments — drift in array
    *length* surfaces as keypath drift. Scalar values terminate the walk
    (we only care about keysets, not values).
    """
    paths: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            here = f"{prefix}.{k}" if prefix else k
            paths.add(here)
            paths |= collect_keypaths(v, here)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            here = f"{prefix}[{i}]"
            paths |= collect_keypaths(v, here)
    return paths


def test_top_level_keyset_matches():
    """Top-level keys must be identical between root and template."""
    root = _load_json(ROOT_CONFIG)
    template = _load_json(TEMPLATE_CONFIG)
    assert set(root.keys()) == set(template.keys()), (
        f"top-level key drift — root only: {set(root) - set(template)}, "
        f"template only: {set(template) - set(root)}"
    )


def test_recursive_keyset_matches():
    """Nested keys must be identical at every level — this is the test
    that would have caught the v0.7.6 models.debugger drift."""
    root = _load_json(ROOT_CONFIG)
    template = _load_json(TEMPLATE_CONFIG)
    root_paths = collect_keypaths(root)
    template_paths = collect_keypaths(template)
    only_in_root = root_paths - template_paths
    only_in_template = template_paths - root_paths
    assert root_paths == template_paths, (
        f"recursive keypath drift between athanor.json and templates/athanor.json — "
        f"root only: {sorted(only_in_root)}; template only: {sorted(only_in_template)}"
    )


def test_top_level_doc_intentionally_differs():
    """Positive assertion that the top-level _doc strings DIFFER.

    Per §10.3 resolved decision, the root says 'runtime configuration'
    and the template says 'template — copied verbatim by /athanor:setup'.
    This test pins that the divergence is deliberate, not a copy/paste lapse.
    If a future edit accidentally re-syncs them (e.g. someone overwrites
    template with root contents), this test catches it.
    """
    root = _load_json(ROOT_CONFIG)
    template = _load_json(TEMPLATE_CONFIG)
    root_doc = root.get("_doc", "")
    template_doc = template.get("_doc", "")
    assert root_doc and template_doc, "both files must carry a top-level _doc"
    assert root_doc != template_doc, (
        "top-level _doc strings should differ (root = 'runtime configuration', "
        "template = 'template'). Identical _doc indicates a copy/paste regression."
    )
    # Sanity tags so the test fails loudly if intent shifts:
    assert "template" in template_doc.lower(), (
        "template _doc should self-identify with the word 'template'"
    )
