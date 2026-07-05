#!/usr/bin/env python3
"""Read-only quality gate for Athanor parent and Codex companion skills."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

try:
    from scripts.gates import codex_mirror_parity
except ModuleNotFoundError:  # pragma: no cover - exercised by direct script use.
    import codex_mirror_parity  # type: ignore[no-redef]

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACT = Path("docs/runtime-surface-contract.json")
DEFAULT_SOURCE_MAP = Path("docs/codex-mirror-source-map.md")
PARENT_SKILLS = Path("skills")
CODEX_SKILLS = Path("plugins/athanor-codex/skills")
LFG_LOOP_PARENT = Path("skills/lfg-loop")
LFG_LOOP_CODEX_SKILL = Path("plugins/athanor-codex/skills/athanor-lfg-loop/SKILL.md")

UNSUPPORTED_RUNTIME_TERMS = (
    "hook-backed enforcement",
    "claude pretooluse",
    "pretooluse enforcement",
    "claude task dispatch",
    "claude task",
    "freeze enforcement",
)
POSITIVE_ENFORCEMENT_RE = re.compile(
    r"\b(enforces?|enforced|blocks?|blocked|prevents?|prevented|"
    r"guarantees?|guaranteed|protects?|protected|rejects?|rejected|"
    r"stops?|stopped)\b",
    re.IGNORECASE,
)
NEGATIVE_OR_DISCLAIMER_MARKERS = (
    "do not",
    "don't",
    "does not",
    "cannot",
    "can't",
    "must not",
    "should not",
    "never claim",
    "not claim",
    "not available",
    "not supported",
    "unsupported",
    "without",
    "instead of claiming",
    "removed",
    "advisory",
    "limits",
    "no ",
    "not ",
)
LFG_LOOP_REFERENCE_CONCEPTS = (
    "receipt-validator",
    "3-tier",
    "CNNN-lfg-receipt.md",
    "G-markers",
    "maxIterations",
    "all_valid",
    "UNDETERMINED",
    "invalid_steps_present",
    "No hidden completion hook",
    "state.json",
    "cycle_state",
    "cycle_phase",
    "current_cycle",
    "acting_on",
    "loop_run_log",
    "last_receipt_path",
    "last_validator_status",
    "tier3_pending",
    "evidence/latest.json",
    "R000-research-receipt.md",
    "P000-planning-receipt.md",
    "A000-architecture-receipt.md",
    "status: skipped",
    "loop.md",
    "Accepted plan path",
    "Public contracts",
)


class SkillQualityInputError(Exception):
    """Raised when a quality-gate input cannot be read."""


def _iso_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _rel(repo_root: Path, path: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def _skill_files(repo_root: Path) -> list[Path]:
    roots = [repo_root / PARENT_SKILLS, repo_root / CODEX_SKILLS]
    files: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        files.extend(
            sorted(
                path / "SKILL.md"
                for path in root.iterdir()
                if path.is_dir() and not path.name.startswith(".")
            )
        )
    return sorted(files)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _frontmatter(text: str) -> tuple[dict[str, Any] | None, str | None]:
    if not text.startswith("---\n"):
        return None, "missing opening frontmatter fence"
    end = text.find("\n---", 4)
    if end == -1:
        return None, "missing closing frontmatter fence"
    raw = text[4:end]
    try:
        parsed = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        return None, f"invalid yaml frontmatter: {exc}"
    if not isinstance(parsed, dict):
        return None, "frontmatter must be a mapping"
    return parsed, None


def _validate_frontmatter(repo_root: Path, paths: list[Path]) -> dict[str, Any]:
    invalid: list[dict[str, Any]] = []
    for path in paths:
        try:
            text = _read_text(path)
        except OSError as exc:
            invalid.append({"path": _rel(repo_root, path), "errors": [str(exc)]})
            continue
        frontmatter, error = _frontmatter(text)
        errors: list[str] = []
        if error:
            errors.append(error)
        if frontmatter is not None:
            for key in ("name", "description"):
                value = frontmatter.get(key)
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"frontmatter {key!r} must be a nonempty string")
        if errors:
            invalid.append({"path": _rel(repo_root, path), "errors": errors})
    invalid_paths = [item["path"] for item in invalid]
    return {
        "id": "skills.frontmatter",
        "status": "pass" if not invalid else "fail",
        "message": "SKILL.md files have frontmatter with nonempty name and description",
        "scanned": [_rel(repo_root, path) for path in paths],
        "invalid": invalid,
        "invalid_paths": invalid_paths,
    }


def _mirror_coverage_check(
    *,
    repo_root: Path,
    contract_path: Path,
    source_map_path: Path,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    try:
        mirror_report, mirror_exit_code = codex_mirror_parity.build_report(
            repo_root=repo_root,
            contract_path=contract_path,
            source_map_path=source_map_path,
        )
    except (
        codex_mirror_parity.MirrorInputError,
        OSError,
        json.JSONDecodeError,
    ) as exc:
        return (
            {
                "id": "mirror.source_map_coverage",
                "status": "fail",
                "message": "mirror source-map coverage could not be evaluated",
                "error": str(exc),
            },
            None,
        )

    failing_ids = [
        str(check["id"])
        for check in mirror_report.get("checks", [])
        if check.get("status") == "fail"
    ]
    return (
        {
            "id": "mirror.source_map_coverage",
            "status": "pass" if mirror_exit_code == 0 else "fail",
            "message": "Codex mirror source map covers expected parent and companion surfaces",
            "delegated_gate": "scripts/gates/codex_mirror_parity.py",
            "delegated_status": mirror_report.get("status"),
            "failing_delegated_checks": failing_ids,
            "summary": mirror_report.get("summary", {}),
        },
        mirror_report,
    )


def _is_positive_runtime_claim(line: str) -> bool:
    lowered = line.lower()
    if not any(term in lowered for term in UNSUPPORTED_RUNTIME_TERMS):
        return False
    if any(marker in lowered for marker in NEGATIVE_OR_DISCLAIMER_MARKERS):
        return False
    return bool(POSITIVE_ENFORCEMENT_RE.search(line))


def _unsupported_runtime_claims(repo_root: Path) -> dict[str, Any]:
    codex_root = repo_root / CODEX_SKILLS
    claims: list[dict[str, Any]] = []
    if not codex_root.is_dir():
        return {
            "id": "codex.unsupported_runtime_claims",
            "status": "fail",
            "message": "Codex companion skills directory exists",
            "claims": [],
            "error": f"missing directory: {CODEX_SKILLS.as_posix()}",
        }
    for skill_path in sorted(codex_root.glob("*/SKILL.md")):
        try:
            lines = _read_text(skill_path).splitlines()
        except OSError as exc:
            claims.append(
                {
                    "path": _rel(repo_root, skill_path),
                    "line_number": None,
                    "line": str(exc),
                }
            )
            continue
        for line_number, line in enumerate(lines, start=1):
            if _is_positive_runtime_claim(line):
                claims.append(
                    {
                        "path": _rel(repo_root, skill_path),
                        "line_number": line_number,
                        "line": line.strip(),
                    }
                )
    return {
        "id": "codex.unsupported_runtime_claims",
        "status": "pass" if not claims else "fail",
        "message": "Codex skills do not positively claim unsupported Claude runtime enforcement",
        "claims": claims,
    }


def _parent_lfg_loop_text(repo_root: Path) -> str:
    root = repo_root / LFG_LOOP_PARENT
    chunks: list[str] = []
    for path in [root / "SKILL.md", *sorted((root / "references").glob("*.md"))]:
        if path.is_file():
            chunks.append(_read_text(path))
    return "\n".join(chunks)


def _lfg_loop_reference_concepts(repo_root: Path) -> dict[str, Any]:
    companion_path = repo_root / LFG_LOOP_CODEX_SKILL
    parent_text = _parent_lfg_loop_text(repo_root)
    if not parent_text or not companion_path.is_file():
        return {
            "id": "codex.lfg_loop_reference_concepts",
            "status": "pass",
            "message": "lfg-loop companion reference concept check skipped when lfg-loop mirror is absent",
            "active_concepts": [],
            "missing": [],
            "skipped": True,
        }

    parent_lower = parent_text.lower()
    companion_lower = _read_text(companion_path).lower()
    active = [
        concept
        for concept in LFG_LOOP_REFERENCE_CONCEPTS
        if concept.lower() in parent_lower
    ]
    missing = [
        concept
        for concept in active
        if concept.lower() not in companion_lower
    ]
    return {
        "id": "codex.lfg_loop_reference_concepts",
        "status": "pass" if not missing else "fail",
        "message": "athanor-lfg-loop companion carries key parent lfg-loop reference concepts",
        "active_concepts": active,
        "missing": missing,
        "skipped": False,
    }


def _status(checks: list[dict[str, Any]]) -> str:
    return "fail" if any(check["status"] == "fail" for check in checks) else "pass"


def build_report(
    *,
    repo_root: Path,
    contract_path: Path,
    source_map_path: Path,
) -> tuple[dict[str, Any], int]:
    repo_root = repo_root.resolve()
    paths = _skill_files(repo_root)
    frontmatter_check = _validate_frontmatter(repo_root, paths)
    mirror_check, mirror_report = _mirror_coverage_check(
        repo_root=repo_root,
        contract_path=contract_path,
        source_map_path=source_map_path,
    )
    runtime_check = _unsupported_runtime_claims(repo_root)
    lfg_loop_check = _lfg_loop_reference_concepts(repo_root)

    checks = [frontmatter_check, mirror_check, runtime_check, lfg_loop_check]
    status = _status(checks)
    report = {
        "schema_version": 1,
        "generated_at": _iso_now(),
        "status": status,
        "profile": {
            "id": "skill-quality",
            "description": "Read-only quality gate for Athanor parent and Codex companion skills.",
            "mutates_files_by_default": False,
            "external_telemetry": False,
            "irreversible_actions": 0,
        },
        "summary": {
            "skill_files": len(paths),
            "frontmatter_failures": len(frontmatter_check["invalid"]),
            "unsupported_runtime_claims": len(runtime_check.get("claims", [])),
            "lfg_loop_missing_concepts": len(lfg_loop_check.get("missing", [])),
            "mirror_status": mirror_check.get("delegated_status"),
            "failures": sum(1 for check in checks if check["status"] == "fail"),
            "irreversible_actions": 0,
        },
        "checks": checks,
        "checks_by_id": {str(check["id"]): check for check in checks},
    }
    if mirror_report is not None:
        report["delegated_reports"] = {"codex_mirror_parity": mirror_report}
    return report, 0 if status == "pass" else 1


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Athanor skill quality.")
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
    except (SkillQualityInputError, OSError, json.JSONDecodeError) as exc:
        report = {
            "schema_version": 1,
            "generated_at": _iso_now(),
            "status": "fail",
            "profile": {
                "id": "skill-quality",
                "description": "Read-only quality gate for Athanor parent and Codex companion skills.",
                "mutates_files_by_default": False,
                "external_telemetry": False,
                "irreversible_actions": 0,
            },
            "summary": {"failures": 1, "irreversible_actions": 0},
            "checks": [{"id": "input", "status": "fail", "message": str(exc)}],
            "checks_by_id": {"input": {"id": "input", "status": "fail", "message": str(exc)}},
        }
        exit_code = 1

    if args.json:
        sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(
            f"Athanor skill quality\nstatus: {report['status']}\n"
            f"skill files: {report.get('summary', {}).get('skill_files', 0)}\n"
            f"failures: {report['summary']['failures']}\n"
        )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
