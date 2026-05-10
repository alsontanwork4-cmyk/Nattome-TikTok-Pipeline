from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, Response

from ..csv_exports import csv_download_response, csv_text, raw_video_export_rows, run_summary_export_row
from ..shell import authenticated_user_or_redirect, call_client_list


router = APIRouter()


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
    "source_artifact_path",
]

RUN_SUMMARY_CSV_COLUMNS = [
    "run_id",
    "timestamp",
    "run_type",
    "source_type",
    "triggered_by",
    "config_version",
    "raw_candidates",
    "eligible_candidates",
    "selected_count",
    "top_issue",
    "output_types",
    "output_links",
]


@router.get("/exports/raw-videos.csv")
def raw_videos_export(request: Request) -> Response:
    user = authenticated_user_or_redirect(request)
    if isinstance(user, RedirectResponse):
        return user
    dashboard_client = request.app.state.dashboard_client
    return csv_download_response(
        csv_text(
            RAW_VIDEO_CSV_COLUMNS,
            raw_video_export_rows(
                raw_videos=call_client_list(dashboard_client, "list_raw_videos"),
                selected_videos=call_client_list(dashboard_client, "list_selected_videos"),
            ),
        ),
        filename="nattome-raw-videos.csv",
    )


@router.get("/exports/run-summaries.csv")
def run_summaries_export(request: Request) -> Response:
    user = authenticated_user_or_redirect(request)
    if isinstance(user, RedirectResponse):
        return user
    dashboard_client = request.app.state.dashboard_client
    runs = dashboard_client.list_runs(limit=50)
    return csv_download_response(
        csv_text(
            RUN_SUMMARY_CSV_COLUMNS,
            [
                run_summary_export_row(
                    run,
                    dashboard_client.list_run_outputs(str(run.get("run_id") or "")),
                )
                for run in runs
            ],
        ),
        filename="nattome-run-summaries.csv",
    )
