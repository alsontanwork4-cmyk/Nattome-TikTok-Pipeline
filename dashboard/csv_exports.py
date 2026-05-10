from __future__ import annotations

import csv
from io import StringIO

from fastapi.responses import Response

from .view_models import cell, list_value, safe_error_summary


def raw_video_export_rows(
    *,
    raw_videos: list[dict],
    selected_videos: list[dict],
) -> list[dict[str, object]]:
    selected_by_video = {str(row.get("video_id") or ""): row for row in selected_videos}
    rows = []
    for video in raw_videos:
        video_id = str(video.get("video_id") or "")
        selected = selected_by_video.get(video_id, {})
        rows.append(
            {
                "video_id": video_id,
                "tiktok_url": str(video.get("tiktok_url") or ""),
                "author_handle": str(video.get("author_handle") or ""),
                "caption": str(video.get("caption") or ""),
                "hashtags": "; ".join(str(item) for item in list_value(video.get("hashtags"))),
                "source_input": str(video.get("source_input") or ""),
                "play_count": cell(video.get("play_count")),
                "like_count": cell(video.get("like_count")),
                "comment_count": cell(video.get("comment_count")),
                "share_count": cell(video.get("share_count")),
                "created_at": str(video.get("created_at") or ""),
                "is_downloadable": "yes" if video.get("is_downloadable") else "no",
                "run_id": str(video.get("run_id") or selected.get("run_id") or ""),
                "config_version": str(video.get("config_version") or ""),
                "selection_status": str(selected.get("evidence_status") or "raw"),
                "source_artifact_path": str(video.get("source_artifact_path") or ""),
            }
        )
    return rows


def run_summary_export_row(run: dict, outputs: list[dict]) -> dict[str, object]:
    return {
        "run_id": str(run.get("run_id") or ""),
        "timestamp": str(run.get("started_at") or run.get("created_at") or ""),
        "run_type": str(run.get("run_type") or run.get("mode") or ""),
        "source_type": str(run.get("source_type") or ""),
        "triggered_by": str(run.get("triggered_by") or run.get("created_by") or ""),
        "config_version": str(run.get("config_version") or ""),
        "raw_candidates": cell(run.get("raw_candidate_count")),
        "eligible_candidates": cell(run.get("eligible_candidate_count")),
        "selected_count": cell(run.get("selected_count")),
        "top_issue": safe_error_summary(run.get("error_summary")),
        "output_types": "; ".join(str(output.get("artifact_type") or "") for output in outputs),
        "output_links": "; ".join(str(output.get("object_path") or "") for output in outputs),
    }


def csv_text(columns: list[str], rows: list[dict[str, object]]) -> str:
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def csv_download_response(body: str, *, filename: str) -> Response:
    return Response(
        body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
