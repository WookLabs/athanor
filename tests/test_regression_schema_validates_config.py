"""Regression: athanor.json and templates/athanor.json must validate against
the shipped JSON Schema at schemas/athanor-config.schema.json.

Closes plan §4 C3 — "Author real schema NOW". Prevents shape drift between
the schema authoring and the two runtime configs (root + template).

Requires the `jsonschema` package (not stdlib). When absent the tests are
skipped via ``pytest.importorskip`` so the suite degrades gracefully on
minimal CI images; the lint/CI matrix is expected to install it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schemas" / "athanor-config.schema.json"
ROOT_CONFIG = REPO_ROOT / "athanor.json"
TEMPLATE_CONFIG = REPO_ROOT / "templates" / "athanor.json"
INVALID_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "fixture_athanor_invalid.json"


def _load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _validate(instance_path: Path) -> None:
    """Raise jsonschema.ValidationError if instance does not satisfy schema."""
    schema = _load_json(SCHEMA_PATH)
    instance = _load_json(instance_path)
    jsonschema.validate(instance=instance, schema=schema)


def test_root_config_validates():
    """athanor.json must validate against the shipped schema."""
    _validate(ROOT_CONFIG)


def test_template_validates():
    """templates/athanor.json must validate against the same schema."""
    _validate(TEMPLATE_CONFIG)


def test_broken_fixture_fails():
    """Deliberately-broken fixture (codex.enabled='yes' string) must fail."""
    with pytest.raises(jsonschema.ValidationError) as excinfo:
        _validate(INVALID_FIXTURE)
    # Sanity check: the violation must mention the wrong-typed field, not
    # some unrelated coincidence. Word-stem flexible — different jsonschema
    # versions phrase this slightly differently.
    msg = str(excinfo.value).lower()
    assert "boolean" in msg or "enabled" in msg, (
        f"validation error should reference the boolean / enabled field, got: {msg}"
    )


def test_schema_accepts_safety_corpus_mode():
    schema = _load_json(SCHEMA_PATH)
    instance = _load_json(ROOT_CONFIG)
    instance["hooks"]["safetyCorpus"] = {"mode": "observe"}
    jsonschema.validate(instance=instance, schema=schema)
