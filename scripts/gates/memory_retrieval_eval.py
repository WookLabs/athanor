#!/usr/bin/env python3
"""Read-only retrieval quality eval for the local Athanor memory index."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.gates.memory_index import load_records, search_records

DEFAULT_FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "memory_index"
DEFAULT_QUERIES = REPO_ROOT / "tests" / "fixtures" / "memory_retrieval_eval" / "queries.json"


class RetrievalEvalInputError(Exception):
    """Raised when retrieval eval inputs are malformed."""


def _profile() -> dict[str, Any]:
    return {
        "id": "memory-retrieval-eval",
        "description": "Read-only query/gold-id quality eval for Athanor's local memory index.",
        "mutates_files_by_default": False,
        "external_telemetry": False,
        "irreversible_actions": 0,
    }


def _load_queries(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise RetrievalEvalInputError(f"query file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise RetrievalEvalInputError("query file schema_version must be 1")
    queries = data.get("queries")
    if not isinstance(queries, list) or not queries:
        raise RetrievalEvalInputError("query file must contain non-empty queries[]")
    normalized: list[dict[str, Any]] = []
    for item in queries:
        if not isinstance(item, dict):
            raise RetrievalEvalInputError("query entries must be objects")
        query_id = item.get("id")
        query = item.get("query")
        gold_ids = item.get("gold_ids")
        top_k = item.get("top_k", 5)
        if not isinstance(query_id, str) or not query_id:
            raise RetrievalEvalInputError("query id must be a non-empty string")
        if not isinstance(query, str) or not query:
            raise RetrievalEvalInputError(f"query {query_id}: query must be non-empty")
        if not isinstance(gold_ids, list) or not gold_ids or not all(isinstance(gold, str) for gold in gold_ids):
            raise RetrievalEvalInputError(f"query {query_id}: gold_ids must be a non-empty string list")
        if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
            raise RetrievalEvalInputError(f"query {query_id}: top_k must be a positive integer")
        normalized.append(
            {
                "id": query_id,
                "query": query,
                "gold_ids": gold_ids,
                "top_k": top_k,
            }
        )
    return normalized


def _round(value: float) -> float:
    return round(value, 3)


def _evaluate_query(records: list[Any], item: dict[str, Any]) -> dict[str, Any]:
    search = search_records(records, item["query"], item["top_k"])
    retrieved_ids = [str(result["id"]) for result in search["results"]]
    gold_ids = [str(gold) for gold in item["gold_ids"]]
    hits = [gold for gold in gold_ids if gold in retrieved_ids]
    missing = [gold for gold in gold_ids if gold not in retrieved_ids]
    precision = len(hits) / max(len(retrieved_ids), 1)
    recall = len(hits) / len(gold_ids)
    status = "pass" if not missing else "fail"
    return {
        "id": item["id"],
        "query": item["query"],
        "top_k": item["top_k"],
        "gold_ids": gold_ids,
        "retrieved_ids": retrieved_ids,
        "hit": bool(hits),
        "precision_at_k": _round(precision),
        "recall_at_k": _round(recall),
        "missing_gold_ids": missing,
        "status": status,
    }


def build_report(
    *,
    fixture_root: Path,
    query_file: Path,
    min_hit_rate: float,
    min_average_recall: float,
) -> dict[str, Any]:
    records, source_records = load_records(fixture_root, REPO_ROOT)
    queries = [_evaluate_query(records, item) for item in _load_queries(query_file)]
    failures = sum(1 for item in queries if item["status"] == "fail")
    hit_rate = sum(1 for item in queries if item["hit"]) / len(queries)
    average_precision = sum(float(item["precision_at_k"]) for item in queries) / len(queries)
    average_recall = sum(float(item["recall_at_k"]) for item in queries) / len(queries)
    threshold_failures = int(hit_rate < min_hit_rate) + int(average_recall < min_average_recall)
    status = "pass" if failures == 0 and threshold_failures == 0 else "fail"
    return {
        "schema_version": 1,
        "status": status,
        "profile": _profile(),
        "source": {
            "fixture_root": str(fixture_root),
            "query_file": str(query_file),
            "source_records": source_records,
            "records": len(records),
        },
        "thresholds": {
            "min_hit_rate": min_hit_rate,
            "min_average_recall_at_k": min_average_recall,
        },
        "summary": {
            "queries": len(queries),
            "failures": failures,
            "hit_rate": _round(hit_rate),
            "average_precision_at_k": _round(average_precision),
            "average_recall_at_k": _round(average_recall),
            "irreversible_actions": 0,
        },
        "queries": queries,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local memory retrieval quality eval.")
    parser.add_argument("--fixture-root", type=Path, default=DEFAULT_FIXTURE_ROOT)
    parser.add_argument("--queries", type=Path, default=DEFAULT_QUERIES)
    parser.add_argument("--min-hit-rate", type=float, default=1.0)
    parser.add_argument("--min-average-recall", type=float, default=1.0)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        report = build_report(
            fixture_root=args.fixture_root,
            query_file=args.queries,
            min_hit_rate=args.min_hit_rate,
            min_average_recall=args.min_average_recall,
        )
    except (OSError, ValueError, json.JSONDecodeError, RetrievalEvalInputError) as exc:
        print(f"memory retrieval eval: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            f"{report['status']}: queries={report['summary']['queries']} "
            f"hit_rate={report['summary']['hit_rate']}"
        )
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
