from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .runtime import sanitize_error_summary
from .supabase_client import ArtifactMetadata


@dataclass(frozen=True)
class ArtifactUpload:
    source_path: Path
    metadata: ArtifactMetadata


def build_run_record(
    run_id: str,
    *,
    manifest: dict[str, Any],
    selected_batch: dict[str, Any],
    metadata: dict[str, Any],
    manual_run: dict | None = None,
    status: str | None = None,
    error_summary: str | None = None,
) -> dict[str, Any]:
    resolved_status = status or run_status(manifest)
    resolved_error = error_summary if error_summary is not None else run_error_summary(manifest)
    return _manual_run_record(
        run_id,
        manifest=manifest,
        selected_batch=selected_batch,
        metadata=metadata,
        manual_run=manual_run or {},
        status=resolved_status,
        error_summary=resolved_error,
    )


def artifact_uploads(
    run_folder: Path,
    *,
    run_id: str,
    storage_bucket: str,
) -> list[ArtifactUpload]:
    return [
        ArtifactUpload(
            source_path=source_path,
            metadata=artifact_metadata(
                source_path,
                run_folder=run_folder,
                run_id=run_id,
                bucket=storage_bucket,
            ),
        )
        for source_path in sorted(path for path in run_folder.rglob("*") if path.is_file())
    ]


def artifact_metadata(
    source_path: Path,
    *,
    run_folder: Path,
    run_id: str,
    bucket: str,
) -> ArtifactMetadata:
    relative_path = source_path.relative_to(run_folder).as_posix()
    object_path = f"runs/{run_id}/{relative_path}"
    return ArtifactMetadata(
        run_id=run_id,
        artifact_type=artifact_type(relative_path),
        bucket=bucket,
        object_path=object_path,
        filename=source_path.name,
        content_type=content_type(source_path),
        size_bytes=source_path.stat().st_size,
        checksum=f"sha256:{sha256(source_path)}",
        created_at=mtime_iso(source_path),
    )


def raw_video_records(run_id: str, selected_batch: dict[str, Any]) -> list[dict[str, Any]]:
    records = []
    seen: set[str] = set()
    for candidate in candidate_records(selected_batch):
        video_id = str(candidate.get("video_id") or candidate.get("id") or "").strip()
        if not video_id or video_id in seen:
            continue
        seen.add(video_id)
        records.append(
            {
                "video_id": video_id,
                "run_id": run_id,
                "tiktok_url": str(candidate.get("tiktok_url") or candidate.get("url") or ""),
                "author_handle": str(candidate.get("author_handle") or ""),
                "caption": str(candidate.get("caption") or ""),
                "hashtags": list_value(candidate.get("hashtags")),
                "source_input": str(
                    candidate.get("source_input")
                    or candidate.get("search_input")
                    or selected_batch.get("candidate_source")
                    or ""
                ),
                "play_count": int_value(candidate.get("play_count")),
                "like_count": int_value(candidate.get("like_count")),
                "comment_count": int_value(candidate.get("comment_count")),
                "share_count": int_value(candidate.get("share_count")),
                "created_at": str(candidate.get("created_at") or ""),
                "updated_at": iso_now(),
            }
        )
    return records


def selected_video_records(
    run_id: str,
    selected_batch: dict[str, Any],
    *,
    default_selection_reason: str,
    default_evidence_status: str,
) -> list[dict[str, Any]]:
    selected = selected_batch.get("selected_candidates")
    if not isinstance(selected, list):
        return []
    selected_at = str(selected_batch.get("selected_at") or "")
    records = []
    for index, candidate in enumerate(selected, start=1):
        if not isinstance(candidate, dict):
            continue
        video_id = str(candidate.get("video_id") or candidate.get("id") or "").strip()
        if not video_id:
            continue
        records.append(
            {
                "run_id": run_id,
                "video_id": video_id,
                "selection_rank": int_value(candidate.get("rank"), fallback=index),
                "selection_reason": str(candidate.get("selection_reason") or default_selection_reason),
                "evidence_status": str(candidate.get("evidence_status") or default_evidence_status),
                "created_at": selected_at,
                "updated_at": iso_now(),
            }
        )
    return records


def publish_run_records(
    dashboard_client: object,
    run_folder: Path,
    *,
    run_id: str,
    manual_run: dict | None = None,
) -> tuple[str, str]:
    manifest = read_json(run_folder / "run_manifest.json")
    selected_batch = read_json(run_folder / "data" / "selected_batch.json")
    metadata = read_json(run_folder / "run_metadata.json")
    manifest_data = manifest if isinstance(manifest, dict) else {}
    selected_data = selected_batch if isinstance(selected_batch, dict) else {}
    metadata_data = metadata if isinstance(metadata, dict) else {}
    status = run_status(manifest_data)
    error_summary = run_error_summary(manifest_data)

    upsert_run = call_optional(dashboard_client, "upsert_run")
    if callable(upsert_run):
        upsert_run(
            build_run_record(
                run_id,
                manifest=manifest_data,
                selected_batch=selected_data,
                metadata=metadata_data,
                manual_run=manual_run,
                status=status,
                error_summary=error_summary,
            )
        )

    raw_records = raw_video_records(run_id, selected_data)
    upsert_raw_videos = call_optional(dashboard_client, "upsert_raw_videos")
    if callable(upsert_raw_videos) and raw_records:
        upsert_raw_videos(raw_records)

    selected_records = selected_video_records(
        run_id,
        selected_data,
        default_selection_reason="dashboard worker",
        default_evidence_status="published",
    )
    upsert_selected_videos = call_optional(dashboard_client, "upsert_selected_videos")
    if callable(upsert_selected_videos) and selected_records:
        upsert_selected_videos(selected_records)

    return status, error_summary


def run_status(manifest: dict[str, Any]) -> str:
    phases = manifest.get("phases")
    if isinstance(phases, list):
        statuses = {str(phase.get("status") or "").lower() for phase in phases if isinstance(phase, dict)}
        if statuses & {"failed", "error", "blocked"}:
            return "failed"
    return "succeeded"


def run_error_summary(manifest: dict[str, Any]) -> str:
    phases = manifest.get("phases")
    if not isinstance(phases, list):
        return ""
    for phase in phases:
        if not isinstance(phase, dict):
            continue
        if str(phase.get("status") or "").lower() not in {"failed", "error", "blocked"}:
            continue
        return sanitize_error_summary(
            phase.get("error")
            or phase.get("exception")
            or phase.get("exception_text")
            or phase.get("reason")
            or ""
        )
    return ""


def read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def call_optional(target: object, method_name: str):
    method = getattr(target, method_name, None)
    return method if callable(method) else None


def artifact_type(relative_path: str) -> str:
    name = Path(relative_path).name
    if name == "run_manifest.json":
        return "manifest"
    if name == "run_metadata.json":
        return "metadata"
    if name == "selected_batch.json":
        return "selected_batch"
    if name.startswith("raw_scrape"):
        return "raw_scrape"
    if relative_path.startswith("reports/"):
        return "report"
    if relative_path.startswith("logs/"):
        return "log"
    if relative_path.startswith("evidence/"):
        return "evidence"
    return "artifact"


def content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return "application/json"
    if suffix == ".md":
        return "text/markdown"
    if suffix == ".csv":
        return "text/csv"
    if suffix == ".xlsx":
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if suffix in {".mp4", ".mov", ".webm"}:
        return f"video/{suffix[1:]}"
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".png":
        return "image/png"
    return "application/octet-stream"


def candidate_records(selected_batch: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = []
    for key in ("selected_candidates", "excluded_candidates"):
        values = selected_batch.get(key)
        if not isinstance(values, list):
            continue
        candidates.extend(candidate for candidate in values if isinstance(candidate, dict))
    return candidates


def list_value(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if not value:
        return []
    return [str(value)]


def int_value(value: object, *, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def mtime_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).replace(
        microsecond=0
    ).isoformat()


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _manual_run_record(
    run_id: str,
    *,
    manifest: dict[str, Any],
    selected_batch: dict[str, Any],
    metadata: dict[str, Any],
    manual_run: dict,
    status: str,
    error_summary: str,
) -> dict[str, Any]:
    started_at = str(
        manifest.get("run_timestamp")
        or metadata.get("run_timestamp")
        or manual_run.get("claimed_at")
        or manual_run.get("requested_at")
        or ""
    )
    now = iso_now()
    return {
        "run_id": run_id,
        "status": status,
        "run_type": str(manual_run.get("run_type") or manifest.get("mode") or "full_pipeline"),
        "mode": "manual",
        "started_at": started_at,
        "finished_at": now if status in {"succeeded", "failed", "canceled"} else "",
        "duration_seconds": metadata.get("duration_seconds"),
        "triggered_by": str(manual_run.get("triggered_by") or metadata.get("triggered_by") or "dashboard-worker"),
        "created_by": str(manual_run.get("triggered_by") or metadata.get("triggered_by") or "dashboard-worker"),
        "error_summary": error_summary,
        "raw_candidate_count": int_value(selected_batch.get("input_candidate_count")),
        "eligible_candidate_count": int_value(selected_batch.get("eligible_candidate_count")),
        "selected_count": int_value(
            selected_batch.get("selected_candidate_count"),
            fallback=len(selected_batch.get("selected_candidates") or []),
        ),
        "report_date": metadata.get("report_date"),
        "summary": metadata.get("summary") or "",
        "created_at": str(manual_run.get("requested_at") or started_at or now),
        "updated_at": now,
    }
