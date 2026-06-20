#!/usr/bin/env python3
"""Read-only verifier for Athanor's Claude-to-Codex mirror source map."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACT = Path("docs/runtime-surface-contract.json")
DEFAULT_SOURCE_MAP = Path("docs/codex-mirror-source-map.md")
NONE_VALUES = {"", "-", "none", "n/a"}
VALID_STATUSES = {"mirror", "claude-only", "codex-agent-mirror"}
BOUNDARY_TOKENS = (
    "Claude Stop hook",
    "Claude PreToolUse",
    "Freeze enforcement",
    "Claude Task",
)
VERSION_RE = re.compile(r"\bv\d+\.\d+(?:\.\d+)?\b")


class MirrorInputError(Exception):
    """Raised when a mirror parity input is missing or malformed."""


def _iso_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _read_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise MirrorInputError(f"{label} not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise MirrorInputError(f"{label} must be a JSON object")
    return data


def _clean_cell(value: str) -> str:
    cleaned = value.strip()
    if cleaned.startswith("`") and cleaned.endswith("`"):
        cleaned = cleaned[1:-1].strip()
    return cleaned


def _optional(value: str) -> str | None:
    cleaned = _clean_cell(value)
    return None if cleaned.lower() in NONE_VALUES else cleaned


def _norm_status(value: str) -> str:
    return _clean_cell(value).lower()


def _parse_table(markdown: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    in_table = False
    headers: list[str] = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            if in_table and rows:
                break
            continue
        cells = [_clean_cell(cell) for cell in stripped.strip("|").split("|")]
        if not in_table:
            lowered = [cell.lower() for cell in cells]
            if lowered[:6] == [
                "claude surface",
                "claude source",
                "codex surface",
                "codex source",
                "status",
                "description anchor",
            ]:
                headers = lowered
                in_table = True
            continue
        if all(set(cell) <= {"-", ":"} for cell in cells):
            continue
        if len(cells) < len(headers):
            continue
        rows.append(
            {
                "claude_surface": _optional(cells[0]),
                "claude_source": _optional(cells[1]),
                "codex_surface": _optional(cells[2]),
                "codex_source": _optional(cells[3]),
                "status": _norm_status(cells[4]),
                "description_anchor": _clean_cell(cells[5]),
            }
        )
    return rows


def _list_dirs(path: Path) -> list[str]:
    if not path.is_dir():
        return []
    return sorted(
        item.name
        for item in path.iterdir()
        if item.is_dir() and not item.name.startswith(".")
    )


def _read_lower(repo_root: Path, rel: str | None) -> str:
    if not rel:
        return ""
    path = repo_root / rel
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8").lower()


def _anchor_mismatches(repo_root: Path, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mismatches: list[dict[str, Any]] = []
    for row in rows:
        anchor = str(row.get("description_anchor") or "").strip().lower()
        if not anchor:
            mismatches.append({"row": row, "missing": ["<empty>"]})
            continue
        terms = [term.strip().lower() for term in re.split(r"[,/]", anchor) if term.strip()]
        source_texts = [
            _read_lower(repo_root, row.get("claude_source")),
            _read_lower(repo_root, row.get("codex_source")),
        ]
        active_texts = [text for text in source_texts if text]
        missing = [
            term
            for term in terms
            if any(term not in text for text in active_texts)
        ]
        if missing:
            mismatches.append({"row": row, "missing": missing})
    return mismatches


def _path_errors(repo_root: Path, rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    for row in rows:
        for key in ("claude_source", "codex_source"):
            rel = row.get(key)
            if not rel:
                continue
            path = repo_root / str(rel)
            if not path.is_file():
                errors.append({"row": str(row.get("claude_surface") or row.get("codex_surface")), "path": str(rel)})
    return errors


def _check(
    checks: list[dict[str, Any]],
    check_id: str,
    status: str,
    message: str,
    *,
    expected: Any = None,
    actual: Any = None,
    missing: list[str] | None = None,
    unexpected: list[str] | None = None,
) -> None:
    item: dict[str, Any] = {"id": check_id, "status": status, "message": message}
    if expected is not None:
        item["expected"] = expected
    if actual is not None:
        item["actual"] = actual
    if missing is not None:
        item["missing"] = missing
    if unexpected is not None:
        item["unexpected"] = unexpected
    checks.append(item)


def _status(checks: list[dict[str, Any]]) -> str:
    return "fail" if any(check["status"] == "fail" for check in checks) else "pass"


def build_report(
    *,
    repo_root: Path,
    contract_path: Path,
    source_map_path: Path,
) -> tuple[dict[str, Any], int]:
    contract = _read_json(contract_path, "runtime surface contract")
    source_map_text = source_map_path.read_text(encoding="utf-8")
    rows = _parse_table(source_map_text)

    claude_contract = contract.get("claude_plugin")
    codex_contract = contract.get("codex_companion")
    if not isinstance(claude_contract, dict):
        raise MirrorInputError("contract claude_plugin must be an object")
    if not isinstance(codex_contract, dict):
        raise MirrorInputError("contract codex_companion must be an object")

    expected_claude = sorted(
        str(item)
        for item in (
            list(claude_contract.get("native_skills", []))
            + list(claude_contract.get("vendored_claude_only_skills", []))
        )
    )
    expected_codex = sorted(str(item) for item in codex_contract.get("skills", []))
    row_claude = sorted(
        str(row["claude_surface"])
        for row in rows
        if row.get("claude_surface")
        and row.get("status") in {"mirror", "claude-only"}
    )
    row_codex = sorted(
        str(row["codex_surface"])
        for row in rows
        if row.get("codex_surface")
        and row.get("status") in {"mirror", "codex-agent-mirror"}
    )
    actual_claude_dirs = sorted(
        item
        for item in _list_dirs(repo_root / "skills")
        if item in expected_claude
    )
    actual_codex_dirs = _list_dirs(repo_root / "plugins" / "athanor-codex" / "skills")

    missing_claude = [item for item in expected_claude if item not in row_claude]
    unexpected_claude = [item for item in row_claude if item not in expected_claude]
    missing_codex = [item for item in expected_codex if item not in row_codex]
    unexpected_codex = [item for item in row_codex if item not in expected_codex]
    missing_claude_dirs = [item for item in expected_claude if item not in actual_claude_dirs]
    missing_codex_dirs = [item for item in expected_codex if item not in actual_codex_dirs]
    invalid_statuses = sorted(
        {
            str(row.get("status"))
            for row in rows
            if row.get("status") not in VALID_STATUSES
        }
    )
    path_errors = _path_errors(repo_root, rows)
    anchor_mismatches = _anchor_mismatches(repo_root, rows)
    stale_version_refs = VERSION_RE.findall(source_map_text)
    boundary_hits = [token for token in BOUNDARY_TOKENS if token in source_map_text]

    checks: list[dict[str, Any]] = []
    _check(
        checks,
        "mirror.source_map_exists",
        "pass" if source_map_path.is_file() else "fail",
        "Codex mirror source map exists",
        expected=str(source_map_path),
        actual=str(source_map_path) if source_map_path.is_file() else None,
    )
    _check(
        checks,
        "mirror.expected_claude_surfaces",
        "pass" if not missing_claude and not unexpected_claude else "fail",
        "source map lists expected Claude skill surfaces",
        expected=expected_claude,
        actual=row_claude,
        missing=missing_claude,
        unexpected=unexpected_claude,
    )
    _check(
        checks,
        "mirror.expected_codex_surfaces",
        "pass" if not missing_codex and not unexpected_codex else "fail",
        "source map lists expected Codex companion skills",
        expected=expected_codex,
        actual=row_codex,
        missing=missing_codex,
        unexpected=unexpected_codex,
    )
    _check(
        checks,
        "mirror.runtime_directories",
        "pass" if not missing_claude_dirs and not missing_codex_dirs else "fail",
        "mapped runtime skill directories exist",
        missing=missing_claude_dirs + missing_codex_dirs,
        unexpected=[],
    )
    _check(
        checks,
        "mirror.source_paths",
        "pass" if not path_errors else "fail",
        "source map paths resolve inside the repository",
        actual=path_errors,
    )
    _check(
        checks,
        "mirror.status_values",
        "pass" if not invalid_statuses else "fail",
        "source map statuses are recognized",
        expected=sorted(VALID_STATUSES),
        actual=invalid_statuses,
    )
    _check(
        checks,
        "mirror.description_anchors",
        "pass" if not anchor_mismatches else "fail",
        "description anchors appear in mapped source files",
        actual=anchor_mismatches,
    )
    _check(
        checks,
        "mirror.stale_version_refs",
        "pass" if not stale_version_refs else "fail",
        "source map avoids pinning stale version references",
        expected=[],
        actual=stale_version_refs,
    )
    _check(
        checks,
        "mirror.unsupported_claude_only_surfaces",
        "pass" if len(boundary_hits) == len(BOUNDARY_TOKENS) else "fail",
        "unsupported Claude-only runtime surfaces are documented",
        expected=list(BOUNDARY_TOKENS),
        actual=boundary_hits,
        missing=[token for token in BOUNDARY_TOKENS if token not in boundary_hits],
        unexpected=[],
    )

    status = _status(checks)
    checks_by_id = {str(check["id"]): check for check in checks}
    report = {
        "schema_version": 1,
        "generated_at": _iso_now(),
        "status": status,
        "profile": {
            "id": "codex-mirror-parity",
            "description": "Read-only verifier for the Claude-to-Codex mirror source map.",
            "mutates_files_by_default": False,
            "external_telemetry": False,
            "irreversible_actions": 0,
        },
        "summary": {
            "rows": len(rows),
            "missing_mirror_rows": len(missing_claude) + len(missing_codex),
            "unexpected_mirror_rows": len(unexpected_claude) + len(unexpected_codex),
            "path_errors": len(path_errors),
            "stale_version_refs": len(stale_version_refs),
            "description_anchor_mismatches": len(anchor_mismatches),
            "unsupported_claude_only_surfaces": len(boundary_hits),
            "failures": sum(1 for check in checks if check["status"] == "fail"),
            "irreversible_actions": 0,
        },
        "rows": rows,
        "checks": checks,
        "checks_by_id": checks_by_id,
    }
    return report, 0 if status == "pass" else 1


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Athanor Codex mirror parity.")
    parser.add_argument("--repo-root", default=".", help="Repository root. Defaults to cwd.")
    parser.add_argument(
        "--contract",
        default=str(DEFAULT_CONTRACT),
        help="Runtime surface contract JSON path.",
    )
    parser.add_argument(
        "--source-map",
        default=str(DEFAULT_SOURCE_MAP),
        help="Codex mirror source-map Markdown path.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON report.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    repo_root = Path(args.repo_root).resolve()
    contract_path = Path(args.contract)
    source_map_path = Path(args.source_map)
    if not contract_path.is_absolute():
        contract_path = repo_root / contract_path
    if not source_map_path.is_absolute():
        source_map_path = repo_root / source_map_path

    try:
        report, exit_code = build_report(
            repo_root=repo_root,
            contract_path=contract_path,
            source_map_path=source_map_path,
        )
    except (MirrorInputError, OSError, json.JSONDecodeError) as exc:
        report = {
            "schema_version": 1,
            "generated_at": _iso_now(),
            "status": "fail",
            "profile": {
                "id": "codex-mirror-parity",
                "description": "Read-only verifier for the Claude-to-Codex mirror source map.",
                "mutates_files_by_default": False,
                "external_telemetry": False,
                "irreversible_actions": 0,
            },
            "summary": {
                "rows": 0,
                "missing_mirror_rows": 0,
                "unexpected_mirror_rows": 0,
                "path_errors": 0,
                "stale_version_refs": 0,
                "description_anchor_mismatches": 0,
                "unsupported_claude_only_surfaces": 0,
                "failures": 1,
                "irreversible_actions": 0,
            },
            "rows": [],
            "checks": [{"id": "input", "status": "fail", "message": str(exc)}],
            "checks_by_id": {"input": {"id": "input", "status": "fail", "message": str(exc)}},
        }
        exit_code = 1

    if args.json:
        sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(
            f"Athanor Codex mirror parity\nstatus: {report['status']}\n"
            f"rows: {report['summary']['rows']}\n"
            f"failures: {report['summary']['failures']}\n"
        )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
