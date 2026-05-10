from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .auth import SupabaseAuthClient
from .config import DashboardSettings
from .composition import build_dashboard_data_client
from .routes import agents, artifacts, auth, exports, overview, reports, runs
from .routes import settings as settings_routes
from .runtime import sanitize_error_summary
from .shell import active_path_for_request, current_user_or_none, template_context


def create_app(
    dashboard_settings: DashboardSettings | None = None,
    *,
    auth_client: object | None = None,
    dashboard_client: object | None = None,
) -> FastAPI:
    resolved_settings = dashboard_settings or DashboardSettings.from_env()
    app = FastAPI(title="Nattome TikTok Scraper")
    templates = Jinja2Templates(directory=str(resolved_settings.templates_path))

    app.state.settings = resolved_settings
    app.state.templates = templates
    app.state.auth_client = auth_client or SupabaseAuthClient(resolved_settings)
    app.state.dashboard_client = (
        dashboard_client
        if dashboard_client is not None
        else _default_dashboard_client(resolved_settings)
    )

    app.mount(
        "/static",
        StaticFiles(directory=str(resolved_settings.assets_path)),
        name="static",
    )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.exception_handler(Exception)
    async def dashboard_exception_handler(request: Request, exc: Exception) -> Response:
        return templates.TemplateResponse(
            request,
            "artifact_status.html",
            {
                **template_context(
                    resolved_settings,
                    page_title="Dashboard error",
                    active_path=active_path_for_request(request),
                ),
                "current_user": current_user_or_none(request),
                "status_title": "Dashboard data unavailable",
                "status_message": sanitize_error_summary(exc)
                or "A dashboard data request failed.",
            },
            status_code=500,
        )

    app.include_router(overview.router)
    app.include_router(runs.router)
    app.include_router(agents.router)
    app.include_router(settings_routes.router)
    app.include_router(reports.router)
    app.include_router(exports.router)
    app.include_router(artifacts.router)
    app.include_router(auth.router)
    return app


def _default_dashboard_client(settings: DashboardSettings) -> object:
    return build_dashboard_data_client(settings)


app = create_app()
