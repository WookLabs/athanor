#!/usr/bin/env python3
"""Export a packaged Athanor workflow episode for external eval harnesses."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evals.external_eval_adapter import export_adapter


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export external eval adapter files.")
    parser.add_argument("--episode-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--json", action="store_true", help="Emit JSON report.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    try:
        report = export_adapter(args.episode_root, args.output_dir)
    except ValueError as exc:
        print(f"external eval adapter: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"exported external eval adapter: path={report['adapter_root']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
