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


class EmptyDashboardDataClient:
    def list_runs(self, *, limit: int = 50) -> list[dict]:
        return []

    def get_run(self, run_id: str) -> dict | None:
        return None

    def list_run_outputs(self, run_id: str) -> list[dict]:
        return []


def create_app(
    settings: DashboardSettings | None = None,
    *,
    auth_client: object | None = None,
    dashboard_client: object | None = None,
) -> FastAPI:
    resolved_settings = settings or DashboardSettings.from_env()
    app = FastAPI(title="Nattome TikTok Scraper")
    templates = Jinja2Templates(directory=str(resolved_settings.templates_path))

    app.state.settings = resolved_settings
    app.state.templates = templates
    app.state.auth_client = auth_client or SupabaseAuthClient(resolved_settings)
    app.state.dashboard_client = dashboard_client or EmptyDashboardDataClient()

    app.mount(
        "/static",
        StaticFiles(directory=str(resolved_settings.assets_path)),
        name="static",
    )

    @app.get("/", response_class=HTMLResponse)
    def dashboard_shell(request: Request) -> Response:
        user = _authenticated_user_or_redirect(request)
        if isinstance(user, RedirectResponse):
            return user
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

    @app.get("/runs", response_class=HTMLResponse)
    def runs_page(request: Request) -> Response:
        user = _authenticated_user_or_redirect(request)
        if isinstance(user, RedirectResponse):
            return user
        runs = [_run_view(row) for row in app.state.dashboard_client.list_runs(limit=50)]
        return templates.TemplateResponse(
            request,
            "runs.html",
            {
                **_template_context(resolved_settings, page_title="Runs", active_path="/runs"),
                "current_user": user,
                "runs": runs,
            },
        )

    @app.get("/runs/{run_id}", response_class=HTMLResponse)
    def run_detail_page(request: Request, run_id: str) -> Response:
        user = _authenticated_user_or_redirect(request)
        if isinstance(user, RedirectResponse):
            return user
        run = app.state.dashboard_client.get_run(run_id)
        if not run:
            return templates.TemplateResponse(
                request,
                "run_detail.html",
                {
                    **_template_context(
                        resolved_settings,
                        page_title="Run not found",
                        active_path="/runs",
                    ),
                    "current_user": user,
                    "run": None,
                    "outputs": [],
                },
                status_code=404,
            )
        outputs = [_output_view(row) for row in app.state.dashboard_client.list_run_outputs(run_id)]
        return templates.TemplateResponse(
            request,
            "run_detail.html",
            {
                **_template_context(
                    resolved_settings,
                    page_title=str(run.get("run_id") or run_id),
                    active_path="/runs",
                ),
                "current_user": user,
                "run": _run_view(run),
                "outputs": outputs,
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


def _authenticated_user_or_redirect(request: Request) -> object:
    try:
        return get_current_user(request)
    except AuthenticationError:
        return RedirectResponse("/login", status_code=303)


def _run_view(row: dict) -> dict:
    status = str(row.get("status") or "unknown").lower()
    return {
        "run_id": str(row.get("run_id") or ""),
        "status": status,
        "status_label": _status_label(status),
        "status_tone": _status_tone(status),
        "run_type": str(row.get("run_type") or row.get("mode") or ""),
        "started_at": str(row.get("started_at") or ""),
        "finished_at": str(row.get("finished_at") or ""),
        "duration": _format_duration(row.get("duration_seconds")),
        "triggered_by": str(row.get("triggered_by") or row.get("created_by") or ""),
        "raw_candidate_count": row.get("raw_candidate_count") or 0,
        "eligible_candidate_count": row.get("eligible_candidate_count") or 0,
        "selected_count": row.get("selected_count") or 0,
        "error_summary": _safe_error_summary(row.get("error_summary")),
    }


def _output_view(row: dict) -> dict:
    return {
        "artifact_type": str(row.get("artifact_type") or ""),
        "bucket": str(row.get("bucket") or ""),
        "object_path": str(row.get("object_path") or ""),
        "filename": str(row.get("filename") or row.get("object_path") or ""),
        "content_type": str(row.get("content_type") or ""),
        "size": _format_bytes(row.get("size_bytes")),
        "checksum": str(row.get("checksum") or ""),
        "created_at": str(row.get("created_at") or ""),
    }


def _status_label(status: str) -> str:
    return {
        "queued": "Queued",
        "running": "Running",
        "succeeded": "Succeeded",
        "failed": "Failed",
        "canceled": "Canceled",
        "cancelled": "Canceled",
    }.get(status, status.title() or "Unknown")


def _status_tone(status: str) -> str:
    if status == "succeeded":
        return "ok"
    if status in {"queued", "running"}:
        return "accent"
    if status in {"failed", "error"}:
        return "err"
    if status in {"canceled", "cancelled"}:
        return "warn"
    return "warn"


def _format_duration(value: object) -> str:
    try:
        seconds = int(value)
    except (TypeError, ValueError):
        return "--"
    minutes, remaining_seconds = divmod(seconds, 60)
    hours, remaining_minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {remaining_minutes}m {remaining_seconds}s"
    if minutes:
        return f"{minutes}m {remaining_seconds}s"
    return f"{remaining_seconds}s"


def _format_bytes(value: object) -> str:
    try:
        size = int(value)
    except (TypeError, ValueError):
        return "--"
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size} B"


def _safe_error_summary(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    sanitized_lines = []
    for line in text.splitlines()[:4]:
        lowered = line.lower()
        if any(marker in lowered for marker in ("secret", "token", "password", "key=")):
            sanitized_lines.append("[redacted secret]")
        else:
            sanitized_lines.append(line[:240])
    return "\n".join(sanitized_lines)


app = create_app()
