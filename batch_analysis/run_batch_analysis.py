#!/usr/bin/env python3
"""Run the stripped Nattome source-video snapshot pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from batch_analysis.env import load_dotenv_files
from batch_analysis.run import create_run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a Nattome run folder, select candidates, and download source videos."
    )
    parser.add_argument(
        "--runs-dir",
        type=Path,
        default=Path("runs") / "batch-analysis",
        help="Directory where timestamped run folders are created.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Optional JSON config file to merge into the recorded run configuration.",
    )
    parser.add_argument(
        "--candidates",
        type=Path,
        help="Candidate JSON containing TikTok metadata and video_download_url fields.",
    )
    parser.add_argument(
        "--timestamp",
        help="UTC timestamp for deterministic runs or tests, for example 2026-05-06T13:45:30Z.",
    )
    return parser.parse_args()


def main() -> int:
    load_dotenv_files([Path.cwd(), WORKSPACE_ROOT], override=True)
    args = parse_args()
    try:
        run_folder = create_run(args)
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"created Nattome source-video run: {run_folder}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
