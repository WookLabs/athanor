#!/usr/bin/env python3
"""Read-only quality gate for trace-backed Athanor lesson memory."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LESSON_ROOT = REPO_ROOT / ".athanor" / "lessons"
DEFAULT_CONFIG = REPO_ROOT / "athanor.json"
EVIDENCE_FIELDS = ("trace_refs", "eval_refs", "evidence_refs")
DEGRADED_OUTCOMES = {"harmful", "degraded", "regressed", "negative"}


class TraceMemoryInputError(Exception):
    """Raised when trace-memory gate inputs are malformed."""


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    lower = value.lower()
    if lower in {"true", "false"}:
        return lower == "true"
    try:
        return int(value)
    except ValueError:
        return value.strip('"').strip("'")


def parse_frontmatter(text: str) -> dict[str, Any]:
    """Parse the small YAML-frontmatter subset used by lesson files."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    metadata: dict[str, Any] = {}
    current_key: str | None = None
    for raw in lines[1:]:
        stripped = raw.strip()
        if stripped == "---":
            break
        if stripped.startswith("- ") and current_key:
            existing = metadata.setdefault(current_key, [])
            if not isinstance(existing, list):
                existing = [existing]
                metadata[current_key] = existing
            existing.append(_parse_scalar(stripped[2:]))
            continue
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        current_key = key.strip()
        value = value.strip()
        metadata[current_key] = [] if value == "" else _parse_scalar(value)
    return metadata


def load_config(path: Path) -> dict[str, int]:
    if not path.is_file():
        return {"decay_days": 7, "promotion_threshold": 5, "max_age_days": 30}
    data = json.loads(path.read_text(encoding="utf-8"))
    memory = data.get("memory", {}) if isinstance(data, dict) else {}
    return {
        "decay_days": int(memory.get("decayDays", 7)),
        "promotion_threshold": int(memory.get("promotionThreshold", 5)),
        "max_age_days": int(memory.get("maxAgeDays", 30)),
    }


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _age_days(meta: dict[str, Any], today: date) -> int | None:
    raw = meta.get("date") or meta.get("created")
    if not isinstance(raw, str) or not raw:
        return None
    try:
        lesson_date = datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None
    return max((today - lesson_date).days, 0)


def _lesson_id(path: Path, meta: dict[str, Any]) -> str:
    for key in ("lesson_id", "lesson-id", "id"):
        value = meta.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return path.stem


def _evidence_refs(meta: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for field in EVIDENCE_FIELDS:
        refs.extend(_as_list(meta.get(field)))
    return refs


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def classify_lesson(
    path: Path,
    root: Path,
    meta: dict[str, Any],
    config: dict[str, int],
    today: date,
) -> dict[str, Any]:
    lesson_id = _lesson_id(path, meta)
    importance = str(meta.get("importance", "working")).strip().lower()
    access_count = int(meta.get("access_count", 0) or 0)
    age = _age_days(meta, today)
    refs = _evidence_refs(meta)
    outcome = str(meta.get("memory_outcome", "")).strip().lower()
    quarantined = importance == "quarantine" or meta.get("quarantine") is True
    status = "pass"
    action = "keep"
    reason = "lesson is within trace-memory policy"

    if outcome in DEGRADED_OUTCOMES and not quarantined:
        status = "fail"
        action = "violation"
        reason = "degraded memory must be quarantined"
    elif quarantined:
        action = "quarantine"
        reason = "degraded or explicitly quarantined memory is isolated"
    elif importance == "permanent" and not refs:
        status = "fail"
        action = "violation"
        reason = "permanent lessons require trace/eval/evidence refs"
    elif importance == "working" and access_count >= config["promotion_threshold"]:
        if refs:
            action = "promote_candidate"
            reason = "working lesson reached promotion threshold with evidence"
        else:
            status = "fail"
            action = "violation"
            reason = "promotion candidate requires trace/eval/evidence refs"
    elif importance == "working" and age is not None and age > config["decay_days"]:
        status = "warn"
        action = "decay"
        reason = "stale low-access working lesson should decay"

    return {
        "lesson_id": lesson_id,
        "path": _relative_path(path, root),
        "importance": importance,
        "access_count": access_count,
        "age_days": age,
        "evidence_refs": refs,
        "action": action,
        "status": status,
        "reason": reason,
    }


def load_lessons(root: Path, config: dict[str, int], today: date) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    if not root.is_dir():
        raise TraceMemoryInputError(f"lesson root is not a directory: {root}")

    lessons: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.md")):
        meta = parse_frontmatter(path.read_text(encoding="utf-8"))
        lessons.append(classify_lesson(path, root, meta, config, today))
    return lessons


def load_comparisons(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    if not path.is_file():
        raise TraceMemoryInputError(f"comparison file not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise TraceMemoryInputError("comparison file schema_version must be 1")
    raw = data.get("comparisons")
    if not isinstance(raw, list):
        raise TraceMemoryInputError("comparison file must contain comparisons[]")

    comparisons: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise TraceMemoryInputError("comparison entries must be objects")
        baseline = float(item["baseline_score"])
        injected = float(item["injected_score"])
        status = "pass" if injected >= baseline else "fail"
        reason = (
            "injected memory did not degrade scenario score"
            if status == "pass"
            else "injected memory degraded scenario score"
        )
        comparisons.append(
            {
                "id": str(item["id"]),
                "lesson_id": str(item["lesson_id"]),
                "scenario_id": str(item["scenario_id"]),
                "baseline_score": baseline,
                "injected_score": injected,
                "status": status,
                "reason": reason,
                "trace_refs": _as_list(item.get("trace_refs")),
            }
        )
    return comparisons


def build_report(
    lesson_root: Path,
    comparison_file: Path | None,
    config_path: Path,
    today: date,
) -> dict[str, Any]:
    config = load_config(config_path)
    lessons = load_lessons(lesson_root, config, today)
    comparisons = load_comparisons(comparison_file)
    violations = sum(1 for lesson in lessons if lesson["status"] == "fail") + sum(
        1 for comparison in comparisons if comparison["status"] == "fail"
    )
    warnings = sum(1 for lesson in lessons if lesson["status"] == "warn")
    return {
        "schema_version": 1,
        "status": "fail" if violations else "pass",
        "config": config,
        "summary": {
            "lessons": len(lessons),
            "comparisons": len(comparisons),
            "violations": violations,
            "warnings": warnings,
        },
        "lesson_root": str(lesson_root),
        "comparison_file": str(comparison_file) if comparison_file else None,
        "lessons": lessons,
        "comparisons": comparisons,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Athanor trace-memory quality gate.")
    parser.add_argument("--lesson-root", type=Path, default=DEFAULT_LESSON_ROOT)
    parser.add_argument("--comparison-file", type=Path, default=None)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--today", default=date.today().isoformat())
    parser.add_argument("--json", action="store_true", help="Emit JSON report.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    try:
        today = datetime.strptime(args.today, "%Y-%m-%d").date()
        report = build_report(args.lesson_root, args.comparison_file, args.config, today)
    except (
        OSError,
        KeyError,
        ValueError,
        json.JSONDecodeError,
        TraceMemoryInputError,
    ) as exc:
        print(f"trace-memory quality: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            f"{report['status']}: lessons={report['summary']['lessons']} "
            f"violations={report['summary']['violations']}"
        )
        for lesson in report["lessons"]:
            if lesson["status"] != "pass":
                print(f"  - {lesson['lesson_id']}: {lesson['action']} - {lesson['reason']}")
        for comparison in report["comparisons"]:
            if comparison["status"] != "pass":
                print(f"  - {comparison['id']}: {comparison['reason']}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
