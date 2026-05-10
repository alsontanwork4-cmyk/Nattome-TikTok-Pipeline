from __future__ import annotations

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .auth import (
    DASHBOARD_ACCESS_TOKEN_COOKIE,
    DASHBOARD_REFRESH_TOKEN_COOKIE,
    AuthenticationError,
    SupabaseAuthClient,
    get_current_user,
)
from .config import DashboardSettings
from .web_constants import NAV_GROUPS


def create_app(
    settings: DashboardSettings | None = None,
    *,
    auth_client: object | None = None,
) -> FastAPI:
    resolved_settings = settings or DashboardSettings.from_env()
    app = FastAPI(title="Nattome TikTok Scraper")
    templates = Jinja2Templates(directory=str(resolved_settings.templates_path))

    app.state.settings = resolved_settings
    app.state.templates = templates
    app.state.auth_client = auth_client or SupabaseAuthClient(resolved_settings)

    app.mount(
        "/static",
        StaticFiles(directory=str(resolved_settings.assets_path)),
        name="static",
    )

    @app.get("/", response_class=HTMLResponse)
    def dashboard_shell(request: Request) -> Response:
        try:
            user = get_current_user(request)
        except AuthenticationError:
            return RedirectResponse("/login", status_code=303)
        return templates.TemplateResponse(
            request,
            "base.html",
            {
                "settings": resolved_settings,
                "page_title": "Overview",
                "active_path": "/",
                "nav_groups": NAV_GROUPS,
                "current_user": user,
            },
        )

    @app.get("/login", response_class=HTMLResponse)
    def login_page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "login.html",
            _template_context(resolved_settings, page_title="Login", active_path="/login"),
        )

    @app.post("/login", response_class=HTMLResponse)
    def login(
        request: Request,
        email: str = Form(...),
        password: str = Form(...),
    ) -> Response:
        try:
            session = app.state.auth_client.sign_in_with_password(email, password)
        except AuthenticationError:
            return templates.TemplateResponse(
                request,
                "login.html",
                {
                    **_template_context(
                        resolved_settings,
                        page_title="Login",
                        active_path="/login",
                    ),
                    "error": "Invalid email or password",
                },
                status_code=401,
            )

        response = RedirectResponse("/", status_code=303)
        response.set_cookie(
            DASHBOARD_ACCESS_TOKEN_COOKIE,
            session.access_token,
            httponly=True,
            secure=resolved_settings.runtime_mode == "production",
            samesite="lax",
            max_age=session.expires_in,
        )
        if session.refresh_token:
            response.set_cookie(
                DASHBOARD_REFRESH_TOKEN_COOKIE,
                session.refresh_token,
                httponly=True,
                secure=resolved_settings.runtime_mode == "production",
                samesite="lax",
                max_age=60 * 60 * 24 * 30,
            )
        return response

    @app.post("/logout")
    def logout() -> RedirectResponse:
        response = RedirectResponse("/login", status_code=303)
        response.delete_cookie(DASHBOARD_ACCESS_TOKEN_COOKIE)
        response.delete_cookie(DASHBOARD_REFRESH_TOKEN_COOKIE)
        return response

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


def _template_context(
    settings: DashboardSettings,
    *,
    page_title: str,
    active_path: str,
) -> dict:
    return {
        "settings": settings,
        "page_title": page_title,
        "active_path": active_path,
        "nav_groups": NAV_GROUPS,
        "current_user": None,
        "error": "",
    }


app = create_app()
