from __future__ import annotations

from .web_constants import CURATION_LABELS, NAV_GROUPS, NAV_ITEMS
from .web_layout import render_page
from .web_server import DashboardServer, create_handler, main, resolve_dashboard_workspace, serve

__all__ = [
    "CURATION_LABELS",
    "DashboardServer",
    "NAV_GROUPS",
    "NAV_ITEMS",
    "create_handler",
    "main",
    "render_page",
    "resolve_dashboard_workspace",
    "serve",
]


if __name__ == "__main__":
    main()
