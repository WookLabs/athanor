#!/usr/bin/env python3
"""Read-only local memory index gate for Athanor."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = REPO_ROOT / ".athanor"
WORD_RE = re.compile(r"[A-Za-z0-9_가-힣]+")


@dataclass(frozen=True)
class MemoryRecord:
    id: str
    kind: str
    source_path: str
    content_hash: str
    title: str
    summary: str
    tokens_estimate: int
    full_content: str

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "source_path": self.source_path,
            "content_hash": self.content_hash,
            "title": self.title,
            "summary": self.summary,
            "tokens_estimate": self.tokens_estimate,
        }

    def detail(self) -> dict[str, Any]:
        data = self.public()
        data["full_content"] = self.full_content
        return data


def _iso_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _repo_rel(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in WORD_RE.finditer(text)]


def _token_count(text: str) -> int:
    return len(_tokenize(text))


def _strip_frontmatter(text: str) -> tuple[dict[str, str], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text.strip()
    meta: dict[str, str] = {}
    body_start = 0
    for idx, raw in enumerate(lines[1:], start=1):
        if raw.strip() == "---":
            body_start = idx + 1
            break
        if ":" in raw and not raw.lstrip().startswith("- "):
            key, value = raw.split(":", 1)
            meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta, "\n".join(lines[body_start:]).strip()


def _first_heading(text: str, fallback: str) -> str:
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("#"):
            return line.lstrip("#").strip() or fallback
    return fallback


def _summarize(text: str, *, max_words: int = 28) -> str:
    words = text.split()
    if not words:
        return ""
    summary = " ".join(words[:max_words])
    if len(words) > max_words:
        summary += "..."
    return summary


def _record_hash(content: str) -> str:
    normalized = "\n".join(line.rstrip() for line in content.strip().splitlines())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _md_record(path: Path, root: Path, kind: str, id_prefix: str) -> MemoryRecord:
    text = path.read_text(encoding="utf-8")
    meta, body = _strip_frontmatter(text)
    title = meta.get("title") or _first_heading(body, path.stem.replace("-", " ").title())
    record_id = meta.get("id") or f"{id_prefix}:{path.stem}"
    summary = _summarize(body)
    content_for_hash = body or text
    return MemoryRecord(
        id=record_id,
        kind=meta.get("kind") or kind,
        source_path=_repo_rel(path, root),
        content_hash=_record_hash(content_for_hash),
        title=title,
        summary=summary,
        tokens_estimate=_token_count(body or text),
        full_content=body or text,
    )


def _trace_records(path: Path, root: Path) -> list[MemoryRecord]:
    records: list[MemoryRecord] = []
    for index, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"message": raw.strip()}
        event_type = str(payload.get("event_type") or payload.get("type") or "trace")
        message = str(payload.get("message") or payload.get("status") or event_type)
        record_id = str(payload.get("id") or f"trace:{path.stem}:{index}")
        full_content = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        title = event_type
        summary = _summarize(f"{event_type} {message}")
        records.append(
            MemoryRecord(
                id=record_id,
                kind="trace",
                source_path=_repo_rel(path, root),
                content_hash=_record_hash(full_content),
                title=title,
                summary=summary,
                tokens_estimate=_token_count(full_content),
                full_content=full_content,
            )
        )
    return records


def _source_root(args: argparse.Namespace, repo_root: Path) -> Path:
    if args.fixture_root is not None:
        return args.fixture_root
    if args.source is not None:
        return args.source
    return repo_root / DEFAULT_SOURCE.relative_to(REPO_ROOT)


def _dedupe_rank(record: MemoryRecord) -> tuple[int, str]:
    stem = Path(record.source_path).stem.lower()
    return (1 if "copy" in stem or "duplicate" in stem else 0, record.source_path)


def load_records(source_root: Path, repo_root: Path) -> tuple[list[MemoryRecord], int]:
    if not source_root.exists():
        return [], 0
    if not source_root.is_dir():
        raise ValueError(f"memory source is not a directory: {source_root}")

    source_records: list[MemoryRecord] = []
    for path in sorted(source_root.glob("lessons/*.md"), key=lambda item: item.as_posix()):
        source_records.append(_md_record(path, repo_root, "lesson", "lesson"))
    for path in sorted(source_root.glob("traces/*.jsonl"), key=lambda item: item.as_posix()):
        source_records.extend(_trace_records(path, repo_root))
    for path in sorted(source_root.glob("goals/*.md"), key=lambda item: item.as_posix()):
        source_records.append(_md_record(path, repo_root, "goal", "goal"))
    for path in sorted(source_root.glob("loops-completed/*.md"), key=lambda item: item.as_posix()):
        source_records.append(_md_record(path, repo_root, "completed_goal", "completed_goal"))

    by_hash: dict[str, MemoryRecord] = {}
    for record in sorted(source_records, key=_dedupe_rank):
        by_hash.setdefault(record.content_hash, record)
    return sorted(by_hash.values(), key=lambda item: item.id), len(source_records)


def _score_record(record: MemoryRecord, query: str) -> int:
    terms = _tokenize(query)
    if not terms:
        return 0
    kind_boost = {"lesson": 20, "trace": 5, "goal": 0, "completed_goal": 0}
    title = f" {record.title.lower()} "
    summary = f" {record.summary.lower()} "
    full = f" {record.full_content.lower()} "
    score = kind_boost.get(record.kind, 0)
    for term in terms:
        score += title.count(term) * 4
        score += summary.count(term) * 3
        score += full.count(term)
    return score


def search_records(records: list[MemoryRecord], query: str, limit: int) -> dict[str, Any]:
    kind_order = {"lesson": 0, "trace": 1, "goal": 2, "completed_goal": 3}
    scored = [
        (score, record)
        for record in records
        if (score := _score_record(record, query)) > 0
    ]
    scored.sort(key=lambda item: (-item[0], kind_order.get(item[1].kind, 9), item[1].id))
    return {
        "query": query,
        "limit": limit,
        "results": [
            {
                **record.public(),
                "score": score,
            }
            for score, record in scored[:limit]
        ],
    }


def _context_block(search: dict[str, Any], budget: int) -> dict[str, Any]:
    lines: list[str] = []
    record_ids: list[str] = []
    tokens = 0
    for item in search.get("results", []):
        line = f"- {item['id']}: {item['summary']}"
        line_tokens = _token_count(line)
        if tokens + line_tokens > budget:
            remaining = budget - tokens
            if remaining <= 0:
                break
            words = line.split()
            line = " ".join(words[:remaining])
            line_tokens = _token_count(line)
        lines.append(line)
        record_ids.append(str(item["id"]))
        tokens += line_tokens
        if tokens >= budget:
            break
    return {
        "budget_tokens": budget,
        "tokens_estimate": tokens,
        "record_ids": record_ids,
        "text": "\n".join(lines),
    }


def build_report(args: argparse.Namespace, repo_root: Path) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    source_root = _source_root(args, repo_root)
    try:
        records, source_count = load_records(source_root, repo_root)
    except ValueError as exc:
        records = []
        source_count = 0
        errors.append({"id": "invalid-source", "message": str(exc)})

    detail = None
    if args.detail:
        match = next((record for record in records if record.id == args.detail), None)
        if match is None:
            errors.append(
                {
                    "id": "missing-detail",
                    "message": f"memory detail id not found: {args.detail}",
                }
            )
        else:
            detail = match.detail()

    search = None
    context = None
    if args.query:
        search = search_records(records, args.query, args.limit)
        if args.context_budget is not None:
            context = _context_block(search, args.context_budget)

    duplicates = max(source_count - len(records), 0)
    status = "fail" if errors else "pass"
    return {
        "schema_version": 1,
        "status": status,
        "generated_at": _iso_now(),
        "profile": {
            "id": "local-memory-index",
            "description": "Read-only local memory index for lessons, traces, goals, and completed loops.",
            "mutates_files_by_default": False,
            "external_telemetry": False,
            "irreversible_actions": 0,
        },
        "summary": {
            "source_records": source_count,
            "records": len(records),
            "duplicates": duplicates,
            "errors": len(errors),
            "irreversible_actions": 0,
        },
        "source_root": str(source_root),
        "records": [record.public() for record in records],
        "search": search,
        "detail": detail,
        "context": context,
        "errors": errors,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the Athanor local memory index.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--fixture-root", type=Path, default=None)
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--query", default="")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--detail", default="")
    parser.add_argument("--context-budget", type=int, default=None)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    repo_root = args.repo_root.resolve()
    report = build_report(args, repo_root)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"memory-index {report['status']}: {report['summary']}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
