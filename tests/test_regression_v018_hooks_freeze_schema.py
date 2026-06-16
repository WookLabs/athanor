"""Regression tests for v0.18.0 hooks.freeze schema + config parity.

Covers:
  - schemas/athanor-config.schema.json accepts hooks.freeze
  - schemas/athanor-config.schema.json accepts hooks.freeze with mode absent (default "off")
  - schemas/athanor-config.schema.json rejects invalid mode value
  - athanor.json + templates/athanor.json parity for freeze section
  - Default mode is "off" (D1)
  - hooks.evidence.mode defaults to "warn" and validates observe/warn/strict
"""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schemas" / "athanor-config.schema.json"
ATHANOR_JSON = REPO_ROOT / "athanor.json"
TEMPLATE_JSON = REPO_ROOT / "templates" / "athanor.json"


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def athanor_config() -> dict:
    return json.loads(ATHANOR_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def template_config() -> dict:
    return json.loads(TEMPLATE_JSON.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Schema: hooks.freeze property exists and validates correctly
# ---------------------------------------------------------------------------


def test_schema_accepts_hooks_freeze_full(schema):
    """Schema accepts a config with a fully-specified hooks.freeze block."""
    config = {
        "version": "1.0",
        "hooks": {
            "profile": "standard",
            "freeze": {
                "mode": "off",
                "allowedPaths": [],
            },
        },
    }
    jsonschema.validate(instance=config, schema=schema)


def test_schema_accepts_hooks_freeze_session_mode(schema):
    """Schema accepts hooks.freeze.mode = 'session'."""
    config = {
        "version": "1.0",
        "hooks": {
            "profile": "standard",
            "freeze": {
                "mode": "session",
                "allowedPaths": ["src/"],
            },
        },
    }
    jsonschema.validate(instance=config, schema=schema)


def test_schema_accepts_hooks_freeze_warn_mode(schema):
    """Schema accepts hooks.freeze.mode = 'warn'."""
    config = {
        "version": "1.0",
        "hooks": {
            "profile": "standard",
            "freeze": {
                "mode": "warn",
                "allowedPaths": [],
            },
        },
    }
    jsonschema.validate(instance=config, schema=schema)


def test_schema_accepts_hooks_freeze_mode_absent(schema):
    """Schema accepts hooks.freeze with mode absent (additionalProperties: false
    means we can't add unknown keys, but mode is optional per schema)."""
    config = {
        "version": "1.0",
        "hooks": {
            "profile": "standard",
            "freeze": {},
        },
    }
    jsonschema.validate(instance=config, schema=schema)


def test_schema_accepts_hooks_freeze_absent(schema):
    """Schema accepts a hooks block without freeze (freeze is optional)."""
    config = {
        "version": "1.0",
        "hooks": {
            "profile": "standard",
        },
    }
    jsonschema.validate(instance=config, schema=schema)


def test_schema_accepts_hooks_evidence_modes(schema):
    """Schema accepts hooks.evidence.mode = observe|warn|strict."""
    for mode in ("observe", "warn", "strict"):
        config = {
            "version": "1.0",
            "hooks": {
                "profile": "standard",
                "evidence": {
                    "mode": mode,
                },
            },
        }
        jsonschema.validate(instance=config, schema=schema)


def test_schema_rejects_invalid_evidence_mode(schema):
    """Schema rejects invalid hooks.evidence.mode values."""
    config = {
        "version": "1.0",
        "hooks": {
            "profile": "standard",
            "evidence": {
                "mode": "loud",
            },
        },
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=config, schema=schema)


def test_schema_rejects_invalid_mode_value(schema):
    """Schema rejects hooks.freeze.mode with an invalid enum value."""
    config = {
        "version": "1.0",
        "hooks": {
            "profile": "standard",
            "freeze": {
                "mode": "strict",  # not in enum [off, session, warn]
                "allowedPaths": [],
            },
        },
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=config, schema=schema)


def test_schema_rejects_unknown_freeze_property(schema):
    """additionalProperties: false on freeze object rejects unknown keys."""
    config = {
        "version": "1.0",
        "hooks": {
            "profile": "standard",
            "freeze": {
                "mode": "off",
                "unknownKey": "bad",
            },
        },
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=config, schema=schema)


def test_schema_rejects_non_array_allowed_paths(schema):
    """allowedPaths must be an array; a string should be rejected."""
    config = {
        "version": "1.0",
        "hooks": {
            "profile": "standard",
            "freeze": {
                "mode": "off",
                "allowedPaths": "src/",  # wrong type
            },
        },
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=config, schema=schema)


# ---------------------------------------------------------------------------
# Schema structure: freeze property is declared inside hooks
# ---------------------------------------------------------------------------


def test_schema_freeze_property_declared(schema):
    """hooks.freeze property is declared in the schema."""
    hooks_props = schema["properties"]["hooks"]["properties"]
    assert "freeze" in hooks_props, (
        "hooks.freeze property missing from schema — subtask 1.3 not implemented"
    )


def test_schema_evidence_property_declared(schema):
    """hooks.evidence property is declared in the schema."""
    hooks_props = schema["properties"]["hooks"]["properties"]
    assert "evidence" in hooks_props


def test_schema_evidence_mode_enum_contains_observe_warn_strict(schema):
    """hooks.evidence.mode enum is exactly observe/warn/strict."""
    evidence_props = schema["properties"]["hooks"]["properties"]["evidence"]["properties"]
    assert evidence_props["mode"]["enum"] == ["observe", "warn", "strict"]


def test_schema_evidence_additional_properties_false(schema):
    """evidence object has additionalProperties: false."""
    evidence_def = schema["properties"]["hooks"]["properties"]["evidence"]
    assert evidence_def.get("additionalProperties") is False


def test_schema_freeze_mode_enum_contains_off(schema):
    """hooks.freeze.mode enum contains 'off'."""
    freeze_props = schema["properties"]["hooks"]["properties"]["freeze"]["properties"]
    mode_enum = freeze_props["mode"]["enum"]
    assert "off" in mode_enum


def test_schema_freeze_mode_enum_contains_session(schema):
    """hooks.freeze.mode enum contains 'session'."""
    freeze_props = schema["properties"]["hooks"]["properties"]["freeze"]["properties"]
    mode_enum = freeze_props["mode"]["enum"]
    assert "session" in mode_enum


def test_schema_freeze_mode_enum_contains_warn(schema):
    """hooks.freeze.mode enum contains 'warn'."""
    freeze_props = schema["properties"]["hooks"]["properties"]["freeze"]["properties"]
    mode_enum = freeze_props["mode"]["enum"]
    assert "warn" in mode_enum


def test_schema_freeze_additional_properties_false(schema):
    """freeze object has additionalProperties: false."""
    freeze_def = schema["properties"]["hooks"]["properties"]["freeze"]
    assert freeze_def.get("additionalProperties") is False, (
        "hooks.freeze should have additionalProperties: false"
    )


# ---------------------------------------------------------------------------
# athanor.json: freeze block present with correct defaults
# ---------------------------------------------------------------------------


def test_athanor_json_has_hooks_freeze(athanor_config):
    """athanor.json has hooks.freeze block."""
    assert "hooks" in athanor_config
    assert "freeze" in athanor_config["hooks"], (
        "athanor.json missing hooks.freeze — subtask 1.3 not implemented"
    )


def test_athanor_json_freeze_mode_is_off(athanor_config):
    """athanor.json hooks.freeze.mode defaults to 'off' (D1)."""
    freeze = athanor_config["hooks"]["freeze"]
    assert freeze.get("mode") == "off", (
        f"Expected mode='off', got {freeze.get('mode')!r}"
    )


def test_athanor_json_freeze_allowed_paths_is_empty_list(athanor_config):
    """athanor.json hooks.freeze.allowedPaths defaults to []."""
    freeze = athanor_config["hooks"]["freeze"]
    assert freeze.get("allowedPaths") == [], (
        f"Expected allowedPaths=[], got {freeze.get('allowedPaths')!r}"
    )


def test_athanor_json_evidence_mode_is_warn(athanor_config):
    """athanor.json hooks.evidence.mode defaults to warn."""
    evidence = athanor_config["hooks"]["evidence"]
    assert evidence.get("mode") == "warn"


def test_athanor_json_validates_against_schema(schema, athanor_config):
    """athanor.json validates against the updated schema."""
    jsonschema.validate(instance=athanor_config, schema=schema)


# ---------------------------------------------------------------------------
# templates/athanor.json: parity with athanor.json for freeze section
# ---------------------------------------------------------------------------


def test_template_json_has_hooks_freeze(template_config):
    """templates/athanor.json has hooks.freeze block."""
    assert "hooks" in template_config
    assert "freeze" in template_config["hooks"], (
        "templates/athanor.json missing hooks.freeze — parity broken"
    )


def test_template_json_freeze_mode_is_off(template_config):
    """templates/athanor.json hooks.freeze.mode is 'off'."""
    freeze = template_config["hooks"]["freeze"]
    assert freeze.get("mode") == "off", (
        f"Expected mode='off', got {freeze.get('mode')!r}"
    )


def test_template_json_freeze_allowed_paths_is_empty_list(template_config):
    """templates/athanor.json hooks.freeze.allowedPaths is []."""
    freeze = template_config["hooks"]["freeze"]
    assert freeze.get("allowedPaths") == []


def test_template_json_evidence_mode_is_warn(template_config):
    """templates/athanor.json hooks.evidence.mode defaults to warn."""
    evidence = template_config["hooks"]["evidence"]
    assert evidence.get("mode") == "warn"


def test_template_json_validates_against_schema(schema, template_config):
    """templates/athanor.json validates against the updated schema."""
    jsonschema.validate(instance=template_config, schema=schema)


def test_athanor_json_template_freeze_parity(athanor_config, template_config):
    """athanor.json and templates/athanor.json have identical hooks.freeze blocks."""
    assert athanor_config["hooks"]["freeze"] == template_config["hooks"]["freeze"], (
        "hooks.freeze parity broken between athanor.json and templates/athanor.json"
    )


def test_athanor_json_template_evidence_parity(athanor_config, template_config):
    """athanor.json and templates/athanor.json have identical hooks.evidence blocks."""
    assert athanor_config["hooks"]["evidence"] == template_config["hooks"]["evidence"], (
        "hooks.evidence parity broken between athanor.json and templates/athanor.json"
    )
