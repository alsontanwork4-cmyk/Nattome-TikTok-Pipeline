#!/usr/bin/env python3
"""Command-line adapter for Nattome TikTok Batch Analysis Runs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from batch_analysis.cloud_publication import (
    CloudPublicationConfigurationError,
    CloudPublicationError,
)
from batch_analysis.env import load_dotenv_files
from batch_analysis.run import create_run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Nattome Daily Evidence analysis pipeline."
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
        help="Daily Top-3 Selection JSON containing TikTok candidate metadata.",
    )
    parser.add_argument(
        "--backfill-candidates",
        type=Path,
        help="Optional daily backfill candidate JSON. Up to two candidates are analyzed only when Top-3 candidates do not qualify.",
    )
    parser.add_argument(
        "--timestamp",
        help="UTC timestamp for deterministic runs or tests, for example 2026-05-06T13:45:30Z.",
    )
    parser.add_argument(
        "--publish-cloud",
        action="store_true",
        dest="cloud_publication_enabled",
        help="Publish completed Daily Evidence Run metadata and artifact records to Supabase.",
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
    except CloudPublicationConfigurationError as exc:
        print(f"cloud publication configuration error: {exc}", file=sys.stderr)
        return 3
    except CloudPublicationError as exc:
        if exc.run_folder is not None:
            print(f"created Batch Analysis Run: {exc.run_folder}")
        print(f"cloud publication error: {exc}", file=sys.stderr)
        return 3

    print(f"created Batch Analysis Run: {run_folder}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
