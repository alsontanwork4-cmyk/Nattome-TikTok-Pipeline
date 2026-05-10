from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from ..markdown import render_markdown
from ..reports import get_report_artifact, report_list_view
from ..runtime import sanitize_error_summary
from ..shell import authenticated_user_or_redirect, template_context
from ..view_models import run_view


router = APIRouter()


@router.get("/reports", response_class=HTMLResponse)
def reports_page(request: Request) -> Response:
    user = authenticated_user_or_redirect(request)
    if isinstance(user, RedirectResponse):
        return user
    settings = request.app.state.settings
    templates = request.app.state.templates
    dashboard_client = request.app.state.dashboard_client

    report_error = ""
    reports = []
    try:
        reports = [
            report_list_view(
                run,
                dashboard_client.list_run_outputs(str(run.get("run_id") or "")),
            )
            for run in dashboard_client.list_runs(limit=50)
        ]
    except Exception as exc:
        report_error = sanitize_error_summary(exc) or "Dashboard report data is unavailable."
    return templates.TemplateResponse(
        request,
        "reports.html",
        {
            **template_context(settings, page_title="Reports", active_path="/reports"),
            "current_user": user,
            "report_error": report_error,
            "reports": reports,
        },
        status_code=503 if report_error else 200,
    )


@router.get("/reports/{run_id}", response_class=HTMLResponse)
def report_detail_page(request: Request, run_id: str) -> Response:
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
            "report_detail.html",
            {
                **template_context(
                    settings,
                    page_title="Report not found",
                    active_path="/reports",
                ),
                "current_user": user,
                "run": None,
                "report_html": "",
            },
            status_code=404,
        )
    metadata = get_report_artifact(dashboard_client, run_id)
    markdown = dashboard_client.download_artifact_text(metadata) if metadata is not None else None
    return templates.TemplateResponse(
        request,
        "report_detail.html",
        {
            **template_context(
                settings,
                page_title=str(run.get("run_id") or run_id),
                active_path="/reports",
            ),
            "current_user": user,
            "run": run_view(run),
            "report_html": render_markdown(markdown) if markdown else "",
        },
    )
