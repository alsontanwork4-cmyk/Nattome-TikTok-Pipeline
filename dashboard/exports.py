from __future__ import annotations

import csv
import json
import sqlite3
from io import StringIO
from pathlib import Path
from typing import Any

from .run_history import load_run_history
from .store import connect_dashboard_store


RAW_VIDEO_CSV_COLUMNS = [
    "video_id",
    "tiktok_url",
    "author_handle",
    "caption",
    "hashtags",
    "source_input",
    "play_count",
    "like_count",
    "comment_count",
    "share_count",
    "created_at",
    "is_downloadable",
    "run_id",
    "config_version",
    "selection_status",
    "curation_labels",
    "exclude_similar_reason",
    "curation_note",
    "source_artifact_path",
]

RUN_SUMMARY_CSV_COLUMNS = [
    "run_id",
    "timestamp",
    "run_type",
    "source_type",
    "triggered_by",
    "config_version",
    "scrape_quality_score",
    "raw_candidates",
    "eligible_candidates",
    "selected_count",
    "average_nattome_relevance",
    "average_engagement",
    "freshness_score",
    "duplicate_noise_score",
    "pipeline_health",
    "top_issue",
    "output_types",
    "output_links",
]


def export_raw_videos_csv(
    workspace: Path | str = ".",
    *,
    filters: dict[str, str] | None = None,
) -> str:
    workspace_path = Path(workspace)
    connection = connect_dashboard_store(workspace_path)
    try:
        run_config_versions = _run_config_versions(connection)
        rows = [
            _raw_video_export_row(row, run_config_versions)
            for row in _raw_video_rows(connection)
        ]
    finally:
        connection.close()
    return _csv_text(
        RAW_VIDEO_CSV_COLUMNS,
        [row for row in rows if _raw_video_matches(row, filters or {})],
    )


def export_run_summaries_csv(workspace: Path | str = ".") -> str:
    history = load_run_history(workspace)
    rows = [_run_summary_export_row(row) for row in history.rows]
    return _csv_text(RUN_SUMMARY_CSV_COLUMNS, rows)


def _raw_video_rows(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(
        connection.execute(
            """
            SELECT
                raw_videos.*,
                video_curation.labels AS curation_labels,
                video_curation.exclude_similar_reason,
                video_curation.note AS curation_note
            FROM raw_videos
            LEFT JOIN video_curation
                ON video_curation.tiktok_video_id = raw_videos.video_id
            ORDER BY COALESCE(raw_videos.play_count, 0) DESC, raw_videos.video_id
            """
        )
    )


def _raw_video_export_row(
    row: sqlite3.Row,
    run_config_versions: dict[str, str],
) -> dict[str, object]:
    run_id = str(row["run_id"] or "")
    return {
        "video_id": str(row["video_id"] or ""),
        "tiktok_url": str(row["tiktok_url"] or ""),
        "author_handle": str(row["author_handle"] or ""),
        "caption": str(row["caption"] or ""),
        "hashtags": "; ".join(str(item) for item in _json_list(row["hashtags_json"])),
        "source_input": str(row["source_input"] or ""),
        "play_count": _cell(row["play_count"]),
        "like_count": _cell(row["like_count"]),
        "comment_count": _cell(row["comment_count"]),
        "share_count": _cell(row["share_count"]),
        "created_at": str(row["created_at"] or ""),
        "is_downloadable": "yes" if int(row["is_downloadable"] or 0) else "no",
        "run_id": run_id,
        "config_version": str(row["config_version"] or run_config_versions.get(run_id, "")),
        "selection_status": str(row["selection_status"] or "raw"),
        "curation_labels": "; ".join(str(item) for item in _json_list(row["curation_labels"])),
        "exclude_similar_reason": str(row["exclude_similar_reason"] or ""),
        "curation_note": str(row["curation_note"] or ""),
        "source_artifact_path": str(row["source_artifact_path"] or ""),
    }


def _run_config_versions(connection: sqlite3.Connection) -> dict[str, str]:
    versions: dict[str, str] = {}
    selected_by_run = {
        str(row["run_id"]): _json_dict(row["raw_json"])
        for row in connection.execute("SELECT run_id, raw_json FROM selected_batches")
    }
    for row in connection.execute("SELECT run_id, raw_json FROM batch_runs"):
        run_id = str(row["run_id"])
        manifest = _json_dict(row["raw_json"])
        selected = selected_by_run.get(run_id, {})
        version = _config_version(manifest, selected)
        if version:
            versions[run_id] = version
    return versions


def _config_version(manifest: dict[str, Any], selected_json: dict[str, Any]) -> str:
    configuration = manifest.get("configuration")
    if not isinstance(configuration, dict):
        configuration = {}
    return str(
        configuration.get("version")
        or configuration.get("config_version")
        or selected_json.get("config_version")
        or selected_json.get("settings_version")
        or ""
    )


def _raw_video_matches(row: dict[str, object], filters: dict[str, str]) -> bool:
    for key, value in filters.items():
        wanted = str(value or "").strip()
        if not wanted:
            continue
        if key == "label":
            labels = {label.strip() for label in str(row["curation_labels"]).split(";") if label.strip()}
            if wanted not in labels:
                return False
            continue
        if key == "q":
            haystack = " ".join(str(row[column]) for column in RAW_VIDEO_CSV_COLUMNS).lower()
            if wanted.lower() not in haystack:
                return False
            continue
        if str(row.get(key) or "") != wanted:
            return False
    return True


def _run_summary_export_row(row: object) -> dict[str, object]:
    output_links = list(getattr(row, "output_links"))
    return {
        "run_id": getattr(row, "run_id"),
        "timestamp": getattr(row, "timestamp"),
        "run_type": getattr(row, "run_type"),
        "source_type": getattr(row, "source_type"),
        "triggered_by": getattr(row, "triggered_by"),
        "config_version": getattr(row, "config_version"),
        "scrape_quality_score": _cell(getattr(row, "scrape_quality_score")),
        "raw_candidates": getattr(row, "raw_candidates"),
        "eligible_candidates": getattr(row, "eligible_candidates"),
        "selected_count": getattr(row, "selected_count"),
        "average_nattome_relevance": f"{float(getattr(row, 'average_nattome_relevance')):.4f}",
        "average_engagement": f"{float(getattr(row, 'average_engagement')):.4f}",
        "freshness_score": _cell(getattr(row, "freshness_score")),
        "duplicate_noise_score": _cell(getattr(row, "duplicate_noise_score")),
        "pipeline_health": getattr(row, "pipeline_health"),
        "top_issue": getattr(row, "top_issue"),
        "output_types": "; ".join(str(getattr(link, "artifact_type")) for link in output_links),
        "output_links": "; ".join(str(getattr(link, "path")) for link in output_links),
    }


def _dict_markdown_lines(label: str, value: object) -> list[str]:
    if not isinstance(value, dict) or not value:
        return [f"- {label}: None"]
    return [f"- {label} {key.title()}: {item}" for key, item in value.items() if item]


def _source_video_markdown_lines(source_videos: object) -> list[str]:
    if not isinstance(source_videos, list) or not source_videos:
        return ["", "### Source Videos", "No source videos recorded."]
    lines = ["", "### Source Videos"]
    for video in source_videos:
        if not isinstance(video, dict):
            continue
        video_id = str(video.get("video_id") or "unknown")
        url = str(video.get("tiktok_url") or "No TikTok URL")
        run_id = str(video.get("run_id") or "")
        suffix = f" ({run_id})" if run_id else ""
        lines.append(f"- {video_id}: {url}{suffix}")
    return lines


def _csv_text(columns: list[str], rows: list[dict[str, object]]) -> str:
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def _json_list(value: object) -> list[object]:
    data = _json_loads(value)
    return data if isinstance(data, list) else []


def _json_dict(value: object) -> dict[str, Any]:
    data = _json_loads(value)
    return data if isinstance(data, dict) else {}


def _json_loads(value: object) -> object:
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str) or not value:
        return {}
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {}


def _cell(value: object) -> object:
    return "" if value is None else value
