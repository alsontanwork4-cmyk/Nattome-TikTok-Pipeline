#!/usr/bin/env python3
"""Create a local archive before cloud migration work changes project workflow."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from batch_analysis.local_backup import create_local_evidence_backup


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a timestamped local backup of evidence data and credentials."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=WORKSPACE_ROOT,
        help="Project root containing data, outputs, runs, and .env.",
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        help="Directory where the local backup archive should be written.",
    )
    parser.add_argument(
        "--timestamp",
        help="UTC timestamp for deterministic backup names, for example 2026-05-09T02:03:04Z.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = create_local_evidence_backup(
            project_root=args.project_root,
            backup_root=args.backup_dir,
            timestamp=args.timestamp,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"created local evidence backup: {result.archive_path}")
    print(f"created backup receipt: {result.receipt_path}")
    print(f"created at: {result.created_at}")
    print("protected inputs: " + ", ".join(result.protected_inputs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
