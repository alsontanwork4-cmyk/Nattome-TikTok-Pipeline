from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

def resolved_inside(parent: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True

def remove_artifact(path: Path, run_folder: Path, removed: list[dict[str, Any]]) -> None:
    if not path.exists() or not resolved_inside(run_folder, path):
        return
    if path.is_dir():
        shutil.rmtree(path)
        artifact_type = "directory"
    else:
        path.unlink()
        artifact_type = "file"
    removed.append(
        {
            "path": str(path.relative_to(run_folder)),
            "type": artifact_type,
        }
    )

def durable_outputs_exist(run_folder: Path, bundle_folder: Path) -> bool:
    flat_required = [
        run_folder / "reports" / "cross_video_pattern_summary.md",
        run_folder / "data" / "structured_batch_analysis.json",
        run_folder / "data" / "spreadsheet_summary.csv",
    ]
    legacy_required = [
        bundle_folder / "video_evidence_report.md",
        run_folder / "batch_outputs" / "markdown" / "cross_video_pattern_summary.md",
        run_folder / "batch_outputs" / "json" / "structured_batch_analysis.json",
        run_folder / "batch_outputs" / "spreadsheets" / "spreadsheet_summary.csv",
    ]
    return all(path.exists() for path in flat_required) or all(
        path.exists() for path in legacy_required
    )

def cleanup_evidence_artifacts(
    run_folder: Path,
    evidence_index: dict[str, Any],
    cleanup_config: dict[str, Any],
) -> dict[str, Any]:
    log_path = run_folder / "logs" / "evidence_artifact_cleanup.json"
    if cleanup_config.get("enabled", False) is not True:
        status = {
            "status": "skipped",
            "reason": "cleanup disabled in runtime configuration",
            "removed_artifact_count": 0,
            "bundles": [],
        }
        log_path.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return status

    if cleanup_config.get("requires_report_approval", True) and not cleanup_config.get(
        "report_approved", False
    ):
        status = {
            "status": "skipped",
            "reason": "report approval not confirmed",
            "removed_artifact_count": 0,
            "bundles": [],
        }
        log_path.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return status

    bundle_logs = []
    for bundle in evidence_index.get("bundles", []):
        if not isinstance(bundle, dict):
            continue
        bundle_folder = run_folder / str(bundle.get("bundle_folder"))
        removed: list[dict[str, Any]] = []
        if cleanup_config.get("remove_source_videos", True):
            source_video = bundle.get("artifacts", {}).get("source_video", {})
            if not isinstance(source_video, dict):
                source_video = bundle.get("source_video", {})
            if isinstance(source_video, dict) and source_video.get("path"):
                remove_artifact(run_folder / str(source_video["path"]), run_folder, removed)
        if cleanup_config.get("remove_frames", True):
            remove_artifact(bundle_folder / "artifacts" / "frames", run_folder, removed)
        bundle_logs.append(
            {
                "candidate_id": bundle.get("candidate_id"),
                "removed_artifacts": removed,
                "preserved_outputs": durable_outputs_exist(run_folder, bundle_folder),
            }
        )

    removed_count = sum(len(bundle["removed_artifacts"]) for bundle in bundle_logs)
    status = {
        "status": "completed",
        "removed_artifact_count": removed_count,
        "bundles": bundle_logs,
    }
    log_path.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return status

