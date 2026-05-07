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


def durable_outputs_exist(run_folder: Path) -> bool:
    manifest_path = run_folder / "run_manifest.json"
    if not manifest_path.exists():
        return False

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False

    outputs = manifest.get("outputs") if isinstance(manifest, dict) else None
    if not isinstance(outputs, dict):
        return False

    output_root_value = outputs.get("output_root")
    final_outputs = outputs.get("final_outputs")
    if not output_root_value or not isinstance(final_outputs, list) or not final_outputs:
        return False

    output_root = Path(str(output_root_value))
    final_output_paths = []
    for output in final_outputs:
        if not isinstance(output, dict) or not output.get("path"):
            return False
        output_path = output_root / str(output["path"])
        if not resolved_inside(output_root, output_path):
            return False
        final_output_paths.append(output_path)

    return all(path.exists() for path in final_output_paths)


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
        removed: list[dict[str, Any]] = []
        if cleanup_config.get("remove_source_videos", True):
            source_video = bundle.get("artifacts", {}).get("source_video", {})
            if not isinstance(source_video, dict):
                source_video = bundle.get("source_video", {})
            if isinstance(source_video, dict) and source_video.get("path"):
                remove_artifact(run_folder / str(source_video["path"]), run_folder, removed)
        bundle_logs.append(
            {
                "candidate_id": bundle.get("candidate_id"),
                "removed_artifacts": removed,
                "preserved_outputs": durable_outputs_exist(run_folder),
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

