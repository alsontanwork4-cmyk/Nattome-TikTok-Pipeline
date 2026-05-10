from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from ..shell import authenticated_user_or_redirect, template_context


router = APIRouter()


@router.get("/artifacts/{artifact_id:path}", response_class=HTMLResponse)
def artifact_download(request: Request, artifact_id: str) -> Response:
    user = authenticated_user_or_redirect(request)
    if isinstance(user, RedirectResponse):
        return user
    settings = request.app.state.settings
    templates = request.app.state.templates
    dashboard_client = request.app.state.dashboard_client

    metadata = dashboard_client.get_artifact_metadata(artifact_id)
    if not metadata:
        return templates.TemplateResponse(
            request,
            "artifact_status.html",
            {
                **template_context(settings, page_title="Artifact not found", active_path="/runs"),
                "current_user": user,
                "status_title": "Artifact not found",
                "status_message": "No Supabase artifact metadata exists for this route.",
            },
            status_code=404,
        )
    signed_url = dashboard_client.create_signed_artifact_url(metadata, expires_in=900)
    if not signed_url:
        return templates.TemplateResponse(
            request,
            "artifact_status.html",
            {
                **template_context(settings, page_title="Artifact unavailable", active_path="/runs"),
                "current_user": user,
                "status_title": "Artifact unavailable",
                "status_message": "Supabase Storage did not return a signed download URL.",
            },
            status_code=502,
        )
    return RedirectResponse(signed_url, status_code=303)
