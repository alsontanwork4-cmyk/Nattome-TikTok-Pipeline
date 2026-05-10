from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from ..run_workbench import run_detail_workbench, run_history_rows
from ..runtime import ActiveManualRunError, enqueue_manual_run, sanitize_error_summary
from ..shell import authenticated_user_or_redirect, call_client_list, template_context
from ..view_models import run_view


router = APIRouter()


@router.get("/runs", response_class=HTMLResponse)
def runs_page(request: Request, q: str = "") -> Response:
    user = authenticated_user_or_redirect(request)
    if isinstance(user, RedirectResponse):
        return user
    settings = request.app.state.settings
    templates = request.app.state.templates
    dashboard_client = request.app.state.dashboard_client

    run_error = ""
    try:
        run_records = dashboard_client.list_runs(limit=50)
        outputs_by_run = _outputs_by_run(dashboard_client, run_records)
        raw_videos_by_run = _raw_videos_by_run(
            call_client_list(dashboard_client, "list_raw_videos")
        )
        rendered_runs = run_history_rows(
            run_records,
            outputs_by_run,
            raw_videos_by_run=raw_videos_by_run,
            query=q,
        )
    except Exception as exc:
        rendered_runs = []
        run_error = sanitize_error_summary(exc) or "Dashboard run data is unavailable."
    return templates.TemplateResponse(
        request,
        "runs.html",
        {
            **template_context(settings, page_title="Runs", active_path="/runs"),
            "current_user": user,
            "runs": rendered_runs,
            "run_error": run_error,
            "query": q,
            "run_count": len(rendered_runs),
        },
        status_code=503 if run_error else 200,
    )


@router.post("/runs", response_class=HTMLResponse)
def request_manual_run(request: Request) -> Response:
    user = authenticated_user_or_redirect(request)
    if isinstance(user, RedirectResponse):
        return user
    settings = request.app.state.settings
    templates = request.app.state.templates
    dashboard_client = request.app.state.dashboard_client

    try:
        enqueue_manual_run(dashboard_client, triggered_by=user.audit_identity)
    except ActiveManualRunError as exc:
        run_records = dashboard_client.list_runs(limit=50)
        rendered_runs = run_history_rows(
            run_records,
            _outputs_by_run(dashboard_client, run_records),
            raw_videos_by_run=_raw_videos_by_run(
                call_client_list(dashboard_client, "list_raw_videos")
            ),
        )
        return templates.TemplateResponse(
            request,
            "runs.html",
            {
                **template_context(settings, page_title="Runs", active_path="/runs"),
                "current_user": user,
                "runs": rendered_runs,
                "run_error": str(exc),
                "query": "",
                "run_count": len(rendered_runs),
            },
            status_code=409,
        )
    return RedirectResponse("/runs", status_code=303)


@router.get("/runs/{run_id}", response_class=HTMLResponse)
def run_detail_page(request: Request, run_id: str, tab: str = "overview") -> Response:
    user = authenticated_user_or_redirect(request)
    if isinstance(user, RedirectResponse):
        return user
    settings = request.app.state.settings
    templates = request.app.state.templates
    dashboard_client = request.app.state.dashboard_client

    run = dashboard_client.get_run(run_id)
    if not run:
        return templates.TemplateResponse(
            request,
            "run_detail.html",
            {
                **template_context(settings, page_title="Run not found", active_path="/runs"),
                "current_user": user,
                "run": None,
                "outputs": [],
                "workbench": None,
            },
            status_code=404,
        )
    outputs = dashboard_client.list_run_outputs(run_id)
    raw_videos = call_client_list(dashboard_client, "list_raw_videos")
    workbench = run_detail_workbench(
        dashboard_client,
        run=run,
        outputs=outputs,
        raw_videos=raw_videos,
        tab=tab,
    )
    return templates.TemplateResponse(
        request,
        "run_detail.html",
        {
            **template_context(
                settings,
                page_title=str(run.get("run_id") or run_id),
                active_path="/runs",
            ),
            "current_user": user,
            "run": run_view(run),
            "outputs": workbench["outputs"],
            "workbench": workbench,
        },
    )


def _outputs_by_run(dashboard_client: object, run_records: list[dict]) -> dict[str, list[dict]]:
    outputs_by_run = {}
    for row in run_records:
        run_id = str(row.get("run_id") or "")
        try:
            outputs_by_run[run_id] = dashboard_client.list_run_outputs(run_id)
        except Exception:
            outputs_by_run[run_id] = []
    return outputs_by_run


def _raw_videos_by_run(raw_videos: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for video in raw_videos:
        run_id = str(video.get("run_id") or "")
        if not run_id:
            continue
        grouped.setdefault(run_id, []).append(video)
    return grouped
