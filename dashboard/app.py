from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import DashboardSettings
from .web_constants import NAV_GROUPS


def create_app(settings: DashboardSettings | None = None) -> FastAPI:
    resolved_settings = settings or DashboardSettings.from_env()
    app = FastAPI(title="Nattome TikTok Scraper")
    templates = Jinja2Templates(directory=str(resolved_settings.templates_path))

    app.state.settings = resolved_settings
    app.state.templates = templates

    app.mount(
        "/static",
        StaticFiles(directory=str(resolved_settings.assets_path)),
        name="static",
    )

    @app.get("/", response_class=HTMLResponse)
    def dashboard_shell(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "base.html",
            {
                "settings": resolved_settings,
                "page_title": "Overview",
                "active_path": "/",
                "nav_groups": NAV_GROUPS,
            },
        )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
