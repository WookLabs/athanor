"""Regression: templates/athanor.json must mirror athanor.json's shape
at every nesting level. Everything must match exactly.

Closes plan §4 C4. The v0.7.6 drift surfaced specifically at
``models.debugger`` — nested, not top-level — so this test walks
recursively, not just top-level keys.

History: pre-S09 the top-level ``_doc`` text intentionally diverged
between root and template (root = 'runtime configuration', template =
'template — copied verbatim'). S09 hard-removed all ``_doc`` inline
documentation fields per user decision U3; the divergence-pin test
``test_top_level_doc_intentionally_differs`` no longer applies and was
removed in S09.
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


def test_no_underscore_doc_fields_present():
    """S09 invariant: ``_doc`` inline documentation fields must NOT appear
    in athanor.json or templates/athanor.json.

    Per user decision U3 (2026-05-28), all ``_doc`` inline documentation
    fields were hard-removed. Documentation lives in:
    - ``schemas/athanor-config.schema.json`` ``description`` fields
      (per-key, machine-readable)
    - ``CLAUDE.md`` (architectural rationale)
    - ``docs/STATE.md`` (release-line operational notes)

    If a future edit re-introduces ``_doc`` at any level (top-level or
    nested) in either file, this test catches it.
    """
    root = _load_json(ROOT_CONFIG)
    template = _load_json(TEMPLATE_CONFIG)
    root_paths = collect_keypaths(root)
    template_paths = collect_keypaths(template)
    root_doc_paths = sorted(p for p in root_paths if p == "_doc" or p.endswith("._doc"))
    template_doc_paths = sorted(
        p for p in template_paths if p == "_doc" or p.endswith("._doc")
    )
    assert not root_doc_paths, (
        f"athanor.json must not contain `_doc` fields (S09 hard-removal). "
        f"Found: {root_doc_paths}"
    )
    assert not template_doc_paths, (
        f"templates/athanor.json must not contain `_doc` fields (S09 hard-removal). "
        f"Found: {template_doc_paths}"
    )
