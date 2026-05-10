from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .supabase_client import ArtifactMetadata


@dataclass(frozen=True)
class LegacyImportSummary:
    runs: int
    artifacts: int
    curation_records: int = 0


def import_legacy_artifacts(
    workspace: Path | str,
    dashboard_client: object,
    *,
    storage_bucket: str,
    legacy_sqlite_path: Path | str | None = None,
) -> LegacyImportSummary:
    workspace_path = Path(workspace)
    runs = 0
    artifacts = 0
    for run_folder in _legacy_run_folders(workspace_path):
        manifest = _read_json(run_folder / "run_manifest.json")
        if not isinstance(manifest, dict):
            continue
        selected_batch = _read_json(run_folder / "data" / "selected_batch.json")
        metadata = _read_json(run_folder / "run_metadata.json")
        run_record = _run_record(
            run_folder,
            manifest=manifest,
            selected_batch=selected_batch if isinstance(selected_batch, dict) else {},
            metadata=metadata if isinstance(metadata, dict) else {},
        )
        _call_required(dashboard_client, "upsert_run")(run_record)
        runs += 1
        for source_path in _artifact_files(run_folder):
            artifact = _artifact_metadata(
                source_path,
                run_folder=run_folder,
                run_id=run_record["run_id"],
                bucket=storage_bucket,
            )
            _call_required(dashboard_client, "upload_artifact_file")(source_path, artifact)
            _call_required(dashboard_client, "upsert_artifact_metadata")(artifact)
            artifacts += 1

    curation_records = (
        _import_legacy_sqlite_curation(dashboard_client, Path(legacy_sqlite_path))
        if legacy_sqlite_path
        else 0
    )
    return LegacyImportSummary(
        runs=runs,
        artifacts=artifacts,
        curation_records=curation_records,
    )


def _legacy_run_folders(workspace: Path) -> list[Path]:
    root = workspace / "runs" / "batch-analysis"
    if not root.is_dir():
        return []
    return sorted(path for path in root.iterdir() if (path / "run_manifest.json").is_file())


def _artifact_files(run_folder: Path) -> list[Path]:
    return sorted(path for path in run_folder.rglob("*") if path.is_file())


def _run_record(
    run_folder: Path,
    *,
    manifest: dict[str, Any],
    selected_batch: dict[str, Any],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    status = _run_status(manifest)
    run_timestamp = str(manifest.get("run_timestamp") or metadata.get("run_timestamp") or "")
    return {
        "run_id": run_folder.name,
        "status": status,
        "run_type": str(manifest.get("mode") or metadata.get("mode") or "legacy"),
        "mode": str(manifest.get("mode") or metadata.get("mode") or ""),
        "started_at": run_timestamp,
        "finished_at": run_timestamp if status in {"succeeded", "failed"} else "",
        "duration_seconds": metadata.get("duration_seconds"),
        "triggered_by": str(metadata.get("triggered_by") or "legacy-import"),
        "created_by": str(metadata.get("triggered_by") or "legacy-import"),
        "error_summary": _error_summary(manifest),
        "raw_candidate_count": _int_value(selected_batch.get("input_candidate_count")),
        "eligible_candidate_count": _int_value(selected_batch.get("eligible_candidate_count")),
        "selected_count": _int_value(
            selected_batch.get("selected_candidate_count"),
            fallback=len(selected_batch.get("selected_candidates") or []),
        ),
        "report_date": metadata.get("report_date"),
        "summary": metadata.get("summary") or "",
        "created_at": run_timestamp,
        "updated_at": _iso_now(),
    }


def _artifact_metadata(
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
        artifact_type=_artifact_type(relative_path),
        bucket=bucket,
        object_path=object_path,
        filename=source_path.name,
        content_type=_content_type(source_path),
        size_bytes=source_path.stat().st_size,
        checksum=f"sha256:{_sha256(source_path)}",
        created_at=_mtime_iso(source_path),
    )


def _import_legacy_sqlite_curation(dashboard_client: object, sqlite_path: Path) -> int:
    if not sqlite_path.is_file():
        return 0
    connection = sqlite3.dbapi2.connect(sqlite_path)
    connection.row_factory = sqlite3.Row
    try:
        if not _has_table(connection, "video_curation"):
            return 0
        rows = list(connection.execute("SELECT * FROM video_curation"))
    finally:
        connection.close()

    upsert_curation = _call_optional(dashboard_client, "upsert_video_curation")
    if not callable(upsert_curation):
        return 0
    count = 0
    for row in rows:
        video_id = str(_row_value(row, "tiktok_video_id") or _row_value(row, "video_id") or "")
        if not video_id:
            continue
        labels = _list_json(_row_value(row, "labels") or "[]")
        upsert_curation(
            video_id,
            labels=[str(label) for label in labels],
            note=str(_row_value(row, "note") or ""),
            exclude_similar_reason=str(
                _row_value(row, "exclude_similar_reason") or ""
            ),
            user=str(_row_value(row, "updated_by") or "legacy-import"),
        )
        count += 1
    return count


def _has_table(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _row_value(row: sqlite3.Row, key: str) -> object:
    return row[key] if key in row.keys() else None


def _run_status(manifest: dict[str, Any]) -> str:
    phases = manifest.get("phases")
    if isinstance(phases, list):
        statuses = {str(phase.get("status") or "").lower() for phase in phases if isinstance(phase, dict)}
        if statuses & {"failed", "error", "blocked"}:
            return "failed"
    return "succeeded"


def _error_summary(manifest: dict[str, Any]) -> str:
    phases = manifest.get("phases")
    if not isinstance(phases, list):
        return ""
    for phase in phases:
        if not isinstance(phase, dict):
            continue
        if str(phase.get("status") or "").lower() not in {"failed", "error", "blocked"}:
            continue
        return str(
            phase.get("error")
            or phase.get("exception")
            or phase.get("exception_text")
            or phase.get("reason")
            or ""
        )[:240]
    return ""


def _artifact_type(relative_path: str) -> str:
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


def _content_type(path: Path) -> str:
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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _mtime_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).replace(
        microsecond=0
    ).isoformat()


def _read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _list_json(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    try:
        loaded = json.loads(str(value or "[]"))
    except json.JSONDecodeError:
        return []
    return loaded if isinstance(loaded, list) else []


def _int_value(value: object, *, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _call_required(target: object, method_name: str):
    method = getattr(target, method_name, None)
    if not callable(method):
        raise RuntimeError(f"dashboard client does not support {method_name}")
    return method


def _call_optional(target: object, method_name: str):
    method = getattr(target, method_name, None)
    return method if callable(method) else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Import legacy dashboard run artifacts.")
    parser.add_argument("--workspace", default=".", help="Workspace containing runs/batch-analysis.")
    parser.add_argument("--legacy-sqlite", default="", help="Optional one-time legacy SQLite source.")
    parser.add_argument("--storage-bucket", default="dashboard-artifacts")
    args = parser.parse_args()
    try:
        from supabase import create_client
    except ImportError as exc:  # pragma: no cover - deployment-only convenience
        raise SystemExit("Install the Supabase Python client before running the import.") from exc

    from .config import DashboardSettings
    from .supabase_client import DashboardSupabaseClient

    settings = DashboardSettings.from_env()
    key = settings.supabase_service_role_key or settings.supabase_anon_key
    if not settings.supabase_url or not key:
        raise SystemExit("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.")
    dashboard_client = DashboardSupabaseClient(
        create_client(settings.supabase_url, key),
        storage_bucket=args.storage_bucket or settings.supabase_storage_bucket,
    )
    summary = import_legacy_artifacts(
        Path(args.workspace),
        dashboard_client,
        storage_bucket=args.storage_bucket or settings.supabase_storage_bucket,
        legacy_sqlite_path=Path(args.legacy_sqlite) if args.legacy_sqlite else None,
    )
    print(summary)
    return 0


if __name__ == "__main__":
    main()
