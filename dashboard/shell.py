from __future__ import annotations

from fastapi import Request
from fastapi.responses import RedirectResponse

from .auth import AuthenticationError, get_current_user
from .config import DashboardSettings

NAV_GROUPS = (
    (
        "Discovery",
        (
            ("Overview", "/", "overview"),
            ("Reports", "/reports", "report"),
            ("Run History", "/runs", "history"),
        ),
    ),
    (
        "Controls",
        (
            ("Scrape Settings", "/settings", "settings"),
        ),
    ),
)


def template_context(
    settings: DashboardSettings,
    *,
    page_title: str,
    active_path: str,
) -> dict:
    return {
        "settings": settings,
        "page_title": page_title,
        "active_path": active_path,
        "nav_groups": fastapi_nav_groups(),
        "current_user": None,
        "error": "",
    }


def fastapi_nav_groups() -> tuple[tuple[str, tuple[tuple[str, str, str], ...]], ...]:
    return NAV_GROUPS


def authenticated_user_or_redirect(request: Request) -> object:
    try:
        return get_current_user(request)
    except AuthenticationError:
        return RedirectResponse("/login", status_code=303)


def current_user_or_none(request: Request) -> object | None:
    try:
        return get_current_user(request)
    except Exception:
        return None


def active_path_for_request(request: Request) -> str:
    path = request.url.path
    if path.startswith("/reports"):
        return "/reports"
    if path.startswith("/runs") or path.startswith("/artifacts"):
        return "/runs"
    if path.startswith("/settings") or path.startswith("/videos"):
        return "/settings"
    return "/"


def call_client_list(dashboard_client: object, method_name: str) -> list[dict]:
    method = getattr(dashboard_client, method_name, None)
    if not callable(method):
        return []
    try:
        return list(method() or [])
    except Exception:
        return []
