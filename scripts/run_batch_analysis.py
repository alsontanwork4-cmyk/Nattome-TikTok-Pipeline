#!/usr/bin/env python3
"""Command-line adapter for Nattome TikTok Batch Analysis Runs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from batch_analysis.config import MODE_DEFAULT_BATCH_SIZE
from batch_analysis.env import load_dotenv_files
from batch_analysis.run import create_run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a runnable Nattome TikTok Batch Analysis Run skeleton."
    )
    parser.add_argument(
        "--mode",
        choices=sorted(MODE_DEFAULT_BATCH_SIZE),
        default="default",
        help="Run mode. Use daily for the daily top-video handoff; defaults to the 10-video Default Batch.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        help="Requested batch size. Defaults to the selected mode's standard size.",
    )
    parser.add_argument(
        "--runs-dir",
        type=Path,
        default=Path("runs") / "batch-analysis",
        help="Directory where timestamped Run Folders are created.",
    )
    parser.add_argument(
        "--outputs-dir",
        type=Path,
        default=Path("outputs"),
        help="Directory where final dated marketer-facing outputs are written.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Optional JSON config file to merge into the recorded run configuration.",
    )
    parser.add_argument(
        "--candidates",
        type=Path,
        help="Apify output, daily handoff, or local fixture JSON containing TikTok candidate metadata.",
    )
    parser.add_argument(
        "--timestamp",
        help="UTC timestamp for deterministic runs or tests, for example 2026-05-06T13:45:30Z.",
    )
    return parser.parse_args()


def main() -> int:
    load_dotenv_files([Path.cwd(), WORKSPACE_ROOT])
    args = parse_args()
    try:
        run_folder = create_run(args)
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"created Batch Analysis Run: {run_folder}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
