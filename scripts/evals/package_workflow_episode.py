#!/usr/bin/env python3
"""Package Athanor workflow eval scenarios as a portable local episode."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evals.workflow_episode import EpisodeSuiteFailed, create_episode


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Package workflow eval scenarios.")
    parser.add_argument("--scenario-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--episode-id", type=str, default=None)
    parser.add_argument("--json", action="store_true", help="Emit JSON report.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    try:
        report = create_episode(
            args.scenario_root,
            args.output_dir,
            episode_id=args.episode_id,
        )
    except EpisodeSuiteFailed as exc:
        if args.json:
            print(json.dumps(exc.report, indent=2, sort_keys=True))
        else:
            print("workflow episode package: source scenarios did not pass", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"workflow episode package: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            "packaged workflow episode: "
            f"path={report['episode_root']} scenarios={report['scenario_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

