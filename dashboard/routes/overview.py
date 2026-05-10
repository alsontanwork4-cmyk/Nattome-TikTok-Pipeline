from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from ..runtime import sanitize_error_summary
from ..shell import authenticated_user_or_redirect, template_context
from ..view_models import output_count_label, output_view, run_view


router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def dashboard_shell(request: Request) -> Response:
    user = authenticated_user_or_redirect(request)
    if isinstance(user, RedirectResponse):
        return user
    settings = request.app.state.settings
    templates = request.app.state.templates
    dashboard_client = request.app.state.dashboard_client

    data_error = ""
    try:
        latest_runs = dashboard_client.list_runs(limit=1)
    except Exception as exc:
        latest_runs = []
        data_error = sanitize_error_summary(exc) or "Dashboard data is unavailable."
    latest_run = run_view(latest_runs[0]) if latest_runs else None
    outputs = []
    if latest_run and not data_error:
        try:
            outputs = [
                output_view(row)
                for row in dashboard_client.list_run_outputs(latest_run["run_id"])
            ]
        except Exception as exc:
            data_error = sanitize_error_summary(exc) or "Run output metadata is unavailable."
    return templates.TemplateResponse(
        request,
        "overview.html",
        {
            **template_context(settings, page_title="Overview", active_path="/"),
            "current_user": user,
            "data_error": data_error,
            "latest_run": latest_run,
            "outputs": outputs,
            "report_href": f"/reports/{latest_run['run_id']}" if latest_run else "",
            "output_count_label": output_count_label(outputs),
            "top_operational_issue": (
                latest_run["error_summary"]
                if latest_run and latest_run["error_summary"]
                else "No operational issue reported."
            ),
        },
        status_code=503 if data_error and not latest_run else 200,
    )
