from __future__ import annotations

import json

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from ..agent_settings import validate_agent_settings
from ..agent_views import agents_form_payload, agents_template_context, form_value
from ..runtime import sanitize_error_summary
from ..shell import authenticated_user_or_redirect, call_client_list


router = APIRouter()


@router.get("/agents", response_class=HTMLResponse)
def agents_page(request: Request) -> Response:
    user = authenticated_user_or_redirect(request)
    if isinstance(user, RedirectResponse):
        return user
    settings = request.app.state.settings
    templates = request.app.state.templates
    dashboard_client = request.app.state.dashboard_client

    error = ""
    try:
        versions = call_client_list(dashboard_client, "list_agent_settings_versions")
    except Exception as exc:
        versions = []
        error = sanitize_error_summary(exc) or "Agent settings data is unavailable."
    return templates.TemplateResponse(
        request,
        "agents.html",
        agents_template_context(settings, user=user, versions=versions, error=error),
        status_code=503 if error else 200,
    )


@router.post("/agents", response_class=HTMLResponse)
async def save_agents(request: Request) -> Response:
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
            raise ValueError("saving agent settings requires a reason")
        payload = agents_form_payload(form)
        validated = validate_agent_settings(payload)
        dashboard_client.save_agent_settings_version(
            validated,
            reason=reason,
            user=user.audit_identity,
        )
    except (ValueError, json.JSONDecodeError) as exc:
        error = str(exc) if isinstance(exc, ValueError) else "advanced JSON must be a valid object"
        return templates.TemplateResponse(
            request,
            "agents.html",
            agents_template_context(
                settings,
                user=user,
                versions=call_client_list(dashboard_client, "list_agent_settings_versions"),
                error=error,
            ),
            status_code=400,
        )
    return RedirectResponse("/agents", status_code=303)


@router.post("/agents/{version}/rollback", response_class=HTMLResponse)
async def rollback_agents(request: Request, version: int) -> Response:
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
            raise ValueError("rolling back agent settings requires a reason")
        dashboard_client.rollback_agent_settings_version(
            target_version=version,
            reason=reason,
            user=user.audit_identity,
        )
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "agents.html",
            agents_template_context(
                settings,
                user=user,
                versions=call_client_list(dashboard_client, "list_agent_settings_versions"),
                error=str(exc),
            ),
            status_code=400,
        )
    return RedirectResponse("/agents", status_code=303)
