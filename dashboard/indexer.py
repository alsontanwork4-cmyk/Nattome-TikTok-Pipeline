from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from sqlite3 import Connection
import sqlite3
from typing import Any, Iterable

from .store import connect_dashboard_store, dump_json


DERIVED_TABLES = (
    "artifact_sources",
    "raw_videos",
    "selected_batches",
    "batch_runs",
    "run_outputs",
)


@dataclass(frozen=True)
class IndexSummary:
    raw_videos: int
    selected_batches: int
    batch_runs: int
    run_outputs: int


def index_pipeline_artifacts(workspace: Path | str = ".") -> IndexSummary:
    workspace_path = Path(workspace)
    connection = connect_dashboard_store(workspace_path)
    try:
        _clear_derived_records(connection)
        _index_raw_scrapes(connection, workspace_path)
        _index_batch_runs(connection, workspace_path)
        connection.commit()
        return _build_summary(connection)
    finally:
        connection.close()


def _clear_derived_records(connection: Connection) -> None:
    for table_name in DERIVED_TABLES:
        connection.execute(f"DELETE FROM {table_name}")


def _index_raw_scrapes(connection: Connection, workspace: Path) -> None:
    raw_paths = [
        *(workspace / "data" / "raw_scrapes").glob("*.json"),
        *(workspace / "runs" / "batch-analysis").glob("*/data/raw_scrape_all.json"),
        *(workspace / "runs" / "batch-analysis").glob("*/data/raw_scrape_top30.json"),
    ]
    for raw_path in sorted(set(raw_paths)):
        data = _read_json(raw_path)
        if data is None:
            continue
        relative_path = _relative_path(workspace, raw_path)
        videos = _video_items(data)
        connection.execute(
            """
            INSERT INTO artifact_sources (
                path,
                artifact_type,
                generated_at,
                metadata_json
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                relative_path,
                "raw_scrape",
                data.get("generated_at") if isinstance(data, dict) else None,
                _json_dumps(_artifact_metadata(data)),
            ),
        )
        for video in videos:
            video_id = _video_id(video)
            if not video_id:
                continue
            connection.execute(
                """
                INSERT INTO raw_videos (
                    video_id,
                    source_artifact_path,
                    tiktok_url,
                    author_handle,
                    caption,
                    hashtags_json,
                    source_input,
                    play_count,
                    like_count,
                    comment_count,
                    share_count,
                    created_at,
                    is_downloadable,
                    run_id,
                    config_version,
                    selection_status,
                    raw_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(video_id) DO UPDATE SET
                    source_artifact_path = excluded.source_artifact_path,
                    tiktok_url = excluded.tiktok_url,
                    author_handle = excluded.author_handle,
                    caption = excluded.caption,
                    hashtags_json = excluded.hashtags_json,
                    source_input = excluded.source_input,
                    play_count = excluded.play_count,
                    like_count = excluded.like_count,
                    comment_count = excluded.comment_count,
                    share_count = excluded.share_count,
                    created_at = excluded.created_at,
                    is_downloadable = excluded.is_downloadable,
                    raw_json = excluded.raw_json,
                    indexed_at = CURRENT_TIMESTAMP
                """,
                (
                    video_id,
                    relative_path,
                    video.get("url") or video.get("webVideoUrl"),
                    video.get("author_handle") or video.get("authorHandle"),
                    video.get("caption") or video.get("text"),
                    _json_dumps(video.get("hashtags") or []),
                    video.get("source_input") or video.get("sourceInput"),
                    _int_or_none(video.get("play_count") or video.get("playCount")),
                    _int_or_none(video.get("like_count") or video.get("likeCount")),
                    _int_or_none(video.get("comment_count") or video.get("commentCount")),
                    _int_or_none(video.get("share_count") or video.get("shareCount")),
                    video.get("created_at") or video.get("createdAt"),
                    1 if video.get("video_download_url") or video.get("videoDownloadUrl") else 0,
                    None,
                    None,
                    _initial_selection_status(video),
                    _json_dumps(video),
                ),
            )


def _index_batch_runs(connection: Connection, workspace: Path) -> None:
    runs_root = workspace / "runs" / "batch-analysis"
    for manifest_path in sorted(runs_root.glob("*/run_manifest.json")):
        run_folder = manifest_path.parent
        run_id = run_folder.name
        manifest = _read_json(manifest_path)
        if not isinstance(manifest, dict):
            continue
        metadata_path = run_folder / "run_metadata.json"
        connection.execute(
            """
            INSERT INTO batch_runs (
                run_id,
                run_folder,
                run_timestamp,
                mode,
                requested_batch_size,
                manifest_path,
                metadata_path,
                raw_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                _relative_path(workspace, run_folder),
                manifest.get("run_timestamp"),
                manifest.get("mode"),
                _int_or_none(manifest.get("requested_batch_size")),
                _relative_path(workspace, manifest_path),
                _relative_path(workspace, metadata_path) if metadata_path.exists() else None,
                _json_dumps(manifest),
            ),
        )
        _index_selected_batch(connection, workspace, run_id, run_folder)
        _index_analyzed_source_metadata(connection, workspace, run_id, run_folder)
        _index_run_outputs(connection, workspace, run_id, run_folder, manifest)


def _index_selected_batch(
    connection: Connection,
    workspace: Path,
    run_id: str,
    run_folder: Path,
) -> None:
    selected_path = run_folder / "data" / "selected_batch.json"
    selected_batch = _read_json(selected_path)
    if not isinstance(selected_batch, dict):
        return
    selected_candidates = selected_batch.get("selected_candidates") or []
    selected_ids = {_video_id(candidate) for candidate in selected_candidates}
    selected_ids.discard("")
    connection.execute(
        """
        INSERT INTO selected_batches (
            path,
            run_id,
            selected_at,
            candidate_source,
            selected_candidate_count,
            raw_json
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            _relative_path(workspace, selected_path),
            run_id,
            selected_batch.get("selected_at"),
            _normalize_path_text(selected_batch.get("candidate_source")),
            _int_or_none(selected_batch.get("selected_candidate_count")) or len(selected_ids),
            _json_dumps(selected_batch),
        ),
    )
    for video_id in selected_ids:
        connection.execute(
            """
            UPDATE raw_videos
            SET selection_status = CASE
                    WHEN selection_status = 'analyzed' THEN 'analyzed'
                    ELSE 'selected'
                END,
                run_id = ?
            WHERE video_id = ?
            """,
            (run_id, video_id),
        )


def _index_analyzed_source_metadata(
    connection: Connection,
    workspace: Path,
    run_id: str,
    run_folder: Path,
) -> None:
    for metadata_path in sorted((run_folder / "data").glob("*_source_metadata.json")):
        metadata = _read_json(metadata_path)
        if not isinstance(metadata, dict):
            continue
        video_id = _video_id(metadata)
        if not video_id:
            continue
        updated = connection.execute(
            """
            UPDATE raw_videos
            SET selection_status = 'analyzed',
                run_id = ?,
                raw_json = CASE
                    WHEN raw_json = '{}' THEN ?
                    ELSE raw_json
                END
            WHERE video_id = ?
            """,
            (run_id, _json_dumps(metadata), video_id),
        )
        if updated.rowcount == 0:
            connection.execute(
                """
                INSERT INTO raw_videos (
                    video_id,
                    source_artifact_path,
                    tiktok_url,
                    author_handle,
                    caption,
                    hashtags_json,
                    play_count,
                    like_count,
                    comment_count,
                    share_count,
                    created_at,
                    is_downloadable,
                    run_id,
                    selection_status,
                    raw_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    video_id,
                    _relative_path(workspace, metadata_path),
                    metadata.get("url"),
                    metadata.get("author_handle"),
                    metadata.get("caption"),
                    _json_dumps(metadata.get("hashtags") or []),
                    _int_or_none(metadata.get("play_count")),
                    _int_or_none(metadata.get("like_count")),
                    _int_or_none(metadata.get("comment_count")),
                    _int_or_none(metadata.get("share_count")),
                    metadata.get("created_at"),
                    1 if metadata.get("video_download_url") else 0,
                    run_id,
                    "analyzed",
                    _json_dumps(metadata),
                ),
            )


def _index_run_outputs(
    connection: Connection,
    workspace: Path,
    run_id: str,
    run_folder: Path,
    manifest: dict[str, Any],
) -> None:
    manifest_path = run_folder / "run_manifest.json"
    metadata_path = run_folder / "run_metadata.json"
    selected_path = run_folder / "data" / "selected_batch.json"
    for artifact_type, label, path in [
        ("manifest", "Run manifest", manifest_path),
        ("metadata", "Run metadata", metadata_path),
        ("selected_batch", "Selected batch", selected_path),
    ]:
        if path.exists():
            _insert_run_output(connection, workspace, run_id, path, artifact_type, label)

    outputs = manifest.get("outputs") if isinstance(manifest, dict) else {}
    if isinstance(outputs, dict):
        for label, raw_path in outputs.items():
            output_path = run_folder / str(raw_path)
            if output_path.exists():
                _insert_run_output(
                    connection,
                    workspace,
                    run_id,
                    output_path,
                    str(label),
                    str(label).replace("_", " ").title(),
                )

    for log_path in sorted((run_folder / "logs").glob("*")):
        if log_path.is_file():
            _insert_run_output(connection, workspace, run_id, log_path, "log", log_path.name)

def _insert_run_output(
    connection: Connection,
    workspace: Path,
    run_id: str,
    path: Path,
    artifact_type: str,
    label: str,
) -> None:
    connection.execute(
        """
        INSERT INTO run_outputs (
            run_id,
            artifact_path,
            artifact_type,
            label,
            exists_on_disk
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            run_id,
            _relative_path(workspace, path),
            artifact_type,
            label,
            1 if path.exists() else 0,
        ),
    )


def _build_summary(connection: Connection) -> IndexSummary:
    return IndexSummary(
        raw_videos=_count(connection, "raw_videos"),
        selected_batches=_count(connection, "selected_batches"),
        batch_runs=_count(connection, "batch_runs"),
        run_outputs=_count(connection, "run_outputs"),
    )


def _count(connection: Connection, table_name: str) -> int:
    return int(connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])


def _video_items(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if not isinstance(data, dict):
        return []
    for key in ("top", "items", "videos", "candidates"):
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _video_id(video: dict[str, Any]) -> str:
    return str(video.get("id") or video.get("video_id") or video.get("videoId") or "")


def _initial_selection_status(video: dict[str, Any]) -> str:
    status = str(video.get("selection_status") or video.get("selectionStatus") or "").lower()
    if status in {"eligible", "selected", "analyzed"}:
        return status
    eligibility = video.get("is_eligible")
    if eligibility is None:
        eligibility = video.get("eligible")
    if eligibility is True or str(eligibility).lower() in {"true", "eligible", "yes"}:
        return "eligible"
    return "raw"


def _artifact_metadata(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {}
    return {
        key: value
        for key, value in data.items()
        if key not in {"top", "items", "videos", "candidates", "raw_items"}
    }


def _read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _relative_path(workspace: Path, path: Path) -> str:
    try:
        return _normalize_path_text(path.relative_to(workspace))
    except ValueError:
        return _normalize_path_text(path)


def _normalize_path_text(path: object) -> str:
    return str(path).replace("\\", "/")


def _json_dumps(value: Any) -> str:
    return dump_json(value)


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
