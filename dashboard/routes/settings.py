from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from ..runtime import sanitize_error_summary
from ..scrape_settings import validate_scrape_settings
from ..settings_views import (
    form_settings_from_payload,
    form_value,
    settings_form_payload,
    settings_template_context,
)
from ..shell import authenticated_user_or_redirect, call_client_list


router = APIRouter()


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request) -> Response:
    user = authenticated_user_or_redirect(request)
    if isinstance(user, RedirectResponse):
        return user
    settings = request.app.state.settings
    templates = request.app.state.templates
    dashboard_client = request.app.state.dashboard_client

    error = ""
    try:
        versions = call_client_list(dashboard_client, "list_settings_versions")
    except Exception as exc:
        versions = []
        error = sanitize_error_summary(exc) or "Scrape settings data is unavailable."
    return templates.TemplateResponse(
        request,
        "settings.html",
        settings_template_context(settings, user=user, versions=versions, error=error),
        status_code=503 if error else 200,
    )


@router.post("/settings", response_class=HTMLResponse)
async def save_settings(request: Request) -> Response:
    user = authenticated_user_or_redirect(request)
    if isinstance(user, RedirectResponse):
        return user
    settings = request.app.state.settings
    templates = request.app.state.templates
    dashboard_client = request.app.state.dashboard_client

    form = await request.form()
    try:
        payload = settings_form_payload(form)
        reason = form_value(form, "reason").strip()
        if not reason:
            raise ValueError("saving production scrape settings requires a reason")
        validated = validate_scrape_settings(payload)
        dashboard_client.save_settings_version(
            validated,
            reason=reason,
            user=user.audit_identity,
        )
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "settings.html",
            settings_template_context(
                settings,
                user=user,
                versions=call_client_list(dashboard_client, "list_settings_versions"),
                error=str(exc),
                form_settings=form_settings_from_payload(settings_form_payload(form)),
            ),
            status_code=400,
        )
    return RedirectResponse("/settings", status_code=303)


@router.post("/settings/{version}/rollback", response_class=HTMLResponse)
async def rollback_settings(request: Request, version: int) -> Response:
    user = authenticated_user_or_redirect(request)
    if isinstance(user, RedirectResponse):
        return user
    settings = request.app.state.settings
    templates = request.app.state.templates
    dashboard_client = request.app.state.dashboard_client

    form = await request.form()
    try:
        reason = form_value(form, "reason").strip()
        if not reason:
            raise ValueError("rolling back production scrape settings requires a reason")
        dashboard_client.rollback_settings_version(
            target_version=version,
            reason=reason,
            user=user.audit_identity,
        )
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "settings.html",
            settings_template_context(
                settings,
                user=user,
                versions=call_client_list(dashboard_client, "list_settings_versions"),
                error=str(exc),
            ),
            status_code=400,
        )
    return RedirectResponse("/settings", status_code=303)
