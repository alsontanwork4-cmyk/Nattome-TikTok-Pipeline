from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from ..auth import (
    DASHBOARD_ACCESS_TOKEN_COOKIE,
    DASHBOARD_REFRESH_TOKEN_COOKIE,
    AuthenticationError,
)
from ..shell import template_context


router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> HTMLResponse:
    return request.app.state.templates.TemplateResponse(
        request,
        "login.html",
        template_context(
            request.app.state.settings,
            page_title="Login",
            active_path="/login",
        ),
    )


@router.post("/login", response_class=HTMLResponse)
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
) -> Response:
    settings = request.app.state.settings
    templates = request.app.state.templates
    try:
        session = request.app.state.auth_client.sign_in_with_password(email, password)
    except AuthenticationError:
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                **template_context(settings, page_title="Login", active_path="/login"),
                "error": "Invalid email or password",
            },
            status_code=401,
        )

    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        DASHBOARD_ACCESS_TOKEN_COOKIE,
        session.access_token,
        httponly=True,
        secure=settings.runtime_mode == "production",
        samesite="lax",
        max_age=session.expires_in,
    )
    if session.refresh_token:
        response.set_cookie(
            DASHBOARD_REFRESH_TOKEN_COOKIE,
            session.refresh_token,
            httponly=True,
            secure=settings.runtime_mode == "production",
            samesite="lax",
            max_age=60 * 60 * 24 * 30,
        )
    return response


@router.post("/logout")
def logout() -> RedirectResponse:
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(DASHBOARD_ACCESS_TOKEN_COOKIE)
    response.delete_cookie(DASHBOARD_REFRESH_TOKEN_COOKIE)
    return response
