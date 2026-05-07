from __future__ import annotations

import argparse
import html
import json
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urlencode, urlparse

from .architecture import load_pipeline_architecture
from .exports import (
    export_approved_patterns_markdown,
    export_nattome_povs_markdown,
    export_raw_videos_csv,
    export_run_summaries_csv,
)
from .health import compute_pipeline_health
from .indexer import index_pipeline_artifacts
from .manual_runs import trigger_manual_run
from .nattome_pov_library import (
    NATTOME_POV_STATUSES,
    archive_nattome_pov,
    create_nattome_pov,
    list_nattome_pov_versions,
    list_nattome_povs,
    update_nattome_pov,
)
from .pattern_library import (
    APPROVED_PATTERN_STATUSES,
    approve_candidate_pattern,
    archive_approved_pattern,
    create_approved_pattern,
    generate_candidate_patterns,
    list_approved_patterns,
    list_pattern_versions,
    update_approved_pattern,
)
from .quality import compute_scrape_quality_scores
from .recommendations import (
    VALID_RECOMMENDATION_STATUSES,
    generate_recommendations,
    update_recommendation_status,
)
from .run_history import load_run_history, load_run_history_detail
from .search import SearchResponse, search_dashboard_records
from .settings import (
    READ_ONLY_SETTINGS,
    get_active_settings_version,
    list_settings_versions,
    rollback_settings_version,
    save_settings_version,
)
from .store import DASHBOARD_DB_PATH, initialize_dashboard_store


NAV_ITEMS = (
    ("Overview", "/"),
    ("Global Search", "/search"),
    ("Scraped Content", "/scraped-content"),
    ("Run History", "/run-history"),
    ("Scrape Settings", "/scrape-settings"),
    ("Recommendations", "/recommendations"),
    ("Pattern Library", "/pattern-library"),
    ("Nattome POV Library", "/nattome-pov-library"),
    ("Pipeline Architecture", "/pipeline-architecture"),
)

CURATION_LABELS = (
    "Relevant",
    "Irrelevant",
    "Wrong Market",
    "Great Hook",
    "Good Nattome Fit",
    "Competitor Inspiration",
    "Save for Later",
    "Exclude Similar",
)


class DashboardServer(ThreadingHTTPServer):
    daemon_threads = True


def create_handler(
    workspace: Path | str = ".",
    *,
    manual_run_executor: Callable[..., object] | None = None,
) -> type[BaseHTTPRequestHandler]:
    workspace_path = Path(workspace)

    class DashboardRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed_path = urlparse(self.path).path
            if parsed_path == "/healthz":
                self._send_text("ok\n")
                return
            if parsed_path == "/exports/raw-videos.csv":
                initialize_dashboard_store(workspace_path)
                query = parse_qs(urlparse(self.path).query)
                self._send_export(
                    export_raw_videos_csv(workspace_path, filters=_first_query_values(query)),
                    content_type="text/csv; charset=utf-8",
                    filename="nattome-raw-videos.csv",
                )
                return
            if parsed_path == "/exports/run-summaries.csv":
                initialize_dashboard_store(workspace_path)
                self._send_export(
                    export_run_summaries_csv(workspace_path),
                    content_type="text/csv; charset=utf-8",
                    filename="nattome-run-summaries.csv",
                )
                return
            if parsed_path == "/exports/approved-patterns.md":
                initialize_dashboard_store(workspace_path)
                self._send_export(
                    export_approved_patterns_markdown(workspace_path),
                    content_type="text/markdown; charset=utf-8",
                    filename="nattome-approved-patterns.md",
                )
                return
            if parsed_path == "/exports/nattome-povs.md":
                initialize_dashboard_store(workspace_path)
                self._send_export(
                    export_nattome_povs_markdown(workspace_path),
                    content_type="text/markdown; charset=utf-8",
                    filename="nattome-povs.md",
                )
                return
            if parsed_path in {route for _, route in NAV_ITEMS}:
                initialize_dashboard_store(workspace_path)
                query = parse_qs(urlparse(self.path).query)
                self._send_html(
                    render_page(
                        parsed_path,
                        workspace_path,
                        query_params=query,
                        run_history_run_id=_first_form_value(query, "run_id") if parsed_path == "/run-history" else "",
                    )
                )
                return
            self.send_error(404, "Dashboard route not found")

        def do_POST(self) -> None:
            parsed_path = urlparse(self.path).path
            if parsed_path == "/scraped-content/curation":
                initialize_dashboard_store(workspace_path)
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length).decode("utf-8")
                _save_video_curation(workspace_path, parse_qs(body))
                self._redirect("/scraped-content")
                return
            if parsed_path == "/scrape-settings/save":
                initialize_dashboard_store(workspace_path)
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length).decode("utf-8")
                try:
                    _save_scrape_settings(workspace_path, parse_qs(body))
                except ValueError as exc:
                    self._send_error_page(400, str(exc))
                    return
                self._redirect("/scrape-settings")
                return
            if parsed_path == "/scrape-settings/rollback":
                initialize_dashboard_store(workspace_path)
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length).decode("utf-8")
                try:
                    _rollback_scrape_settings(workspace_path, parse_qs(body))
                except ValueError as exc:
                    self._send_error_page(400, str(exc))
                    return
                self._redirect("/scrape-settings")
                return
            if parsed_path == "/manual-runs/trigger":
                initialize_dashboard_store(workspace_path)
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length).decode("utf-8")
                form = parse_qs(body)
                try:
                    trigger_manual_run(
                        workspace_path,
                        _first_form_value(form, "run_type") or "scrape_only",
                        triggered_by=_first_form_value(form, "user") or "local",
                        executor=manual_run_executor,
                    )
                except ValueError as exc:
                    self._send_error_page(400, str(exc))
                    return
                self._redirect("/run-history")
                return
            if parsed_path == "/recommendations/status":
                initialize_dashboard_store(workspace_path)
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length).decode("utf-8")
                try:
                    _update_recommendation_status(workspace_path, parse_qs(body))
                except ValueError as exc:
                    self._send_error_page(400, str(exc))
                    return
                self._redirect("/recommendations")
                return
            if parsed_path == "/pattern-library/approve":
                initialize_dashboard_store(workspace_path)
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length).decode("utf-8")
                try:
                    _approve_pattern_candidate(workspace_path, parse_qs(body))
                except ValueError as exc:
                    self._send_error_page(400, str(exc))
                    return
                self._redirect("/pattern-library")
                return
            if parsed_path == "/pattern-library/create":
                initialize_dashboard_store(workspace_path)
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length).decode("utf-8")
                try:
                    _create_pattern(workspace_path, parse_qs(body))
                except ValueError as exc:
                    self._send_error_page(400, str(exc))
                    return
                self._redirect("/pattern-library")
                return
            if parsed_path == "/pattern-library/edit":
                initialize_dashboard_store(workspace_path)
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length).decode("utf-8")
                try:
                    _edit_pattern(workspace_path, parse_qs(body))
                except ValueError as exc:
                    self._send_error_page(400, str(exc))
                    return
                self._redirect("/pattern-library")
                return
            if parsed_path == "/pattern-library/archive":
                initialize_dashboard_store(workspace_path)
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length).decode("utf-8")
                try:
                    _archive_pattern(workspace_path, parse_qs(body))
                except ValueError as exc:
                    self._send_error_page(400, str(exc))
                    return
                self._redirect("/pattern-library")
                return
            if parsed_path == "/nattome-pov-library/create":
                initialize_dashboard_store(workspace_path)
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length).decode("utf-8")
                try:
                    _create_nattome_pov(workspace_path, parse_qs(body))
                except ValueError as exc:
                    self._send_error_page(400, str(exc))
                    return
                self._redirect("/nattome-pov-library")
                return
            if parsed_path == "/nattome-pov-library/edit":
                initialize_dashboard_store(workspace_path)
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length).decode("utf-8")
                try:
                    _edit_nattome_pov(workspace_path, parse_qs(body))
                except ValueError as exc:
                    self._send_error_page(400, str(exc))
                    return
                self._redirect("/nattome-pov-library")
                return
            if parsed_path == "/nattome-pov-library/archive":
                initialize_dashboard_store(workspace_path)
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length).decode("utf-8")
                try:
                    _archive_nattome_pov(workspace_path, parse_qs(body))
                except ValueError as exc:
                    self._send_error_page(400, str(exc))
                    return
                self._redirect("/nattome-pov-library")
                return
            self.send_error(404, "Dashboard route not found")

        def log_message(self, format: str, *args: object) -> None:
            return

        def _send_html(self, body: str) -> None:
            encoded = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def _redirect(self, location: str) -> None:
            self.send_response(303)
            self.send_header("Location", location)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _send_text(self, body: str) -> None:
            encoded = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def _send_export(self, body: str, *, content_type: str, filename: str) -> None:
            encoded = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def _send_error_page(self, status: int, message: str) -> None:
            body = f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Dashboard error</title></head>
<body><h1>Dashboard error</h1><p>{html.escape(message)}</p></body>
</html>
"""
            encoded = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    return DashboardRequestHandler


def render_page(
    active_path: str,
    workspace: Path,
    *,
    query_params: dict[str, list[str]] | None = None,
    run_history_run_id: str = "",
) -> str:
    title = _title_for_path(active_path)
    query_params = query_params or {}
    nav = "\n".join(
        _render_nav_item(label, route, active_path)
        for label, route in NAV_ITEMS
    )
    if active_path == "/":
        overview = _render_overview(workspace)
    elif active_path == "/search":
        overview = _render_search(workspace, query_params)
    elif active_path == "/scraped-content":
        overview = _render_scraped_content(workspace)
    elif active_path == "/scrape-settings":
        overview = _render_scrape_settings(workspace)
    elif active_path == "/run-history":
        overview = _render_run_history(workspace, run_history_run_id=run_history_run_id)
    elif active_path == "/recommendations":
        overview = _render_recommendations(workspace)
    elif active_path == "/pattern-library":
        overview = _render_pattern_library(workspace)
    elif active_path == "/nattome-pov-library":
        overview = _render_nattome_pov_library(workspace)
    elif active_path == "/pipeline-architecture":
        overview = _render_pipeline_architecture(workspace)
    else:
        overview = _render_placeholder(title)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Nattome Scrape Quality Dashboard</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f7f4;
      --panel: #ffffff;
      --ink: #1f2722;
      --muted: #657166;
      --line: #dce2da;
      --accent: #2f6f5e;
      --accent-soft: #dceee7;
      --warn-soft: #fff0ce;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Arial, Helvetica, sans-serif;
      letter-spacing: 0;
    }}
    .layout {{
      min-height: 100vh;
      display: grid;
      grid-template-columns: 248px minmax(0, 1fr);
    }}
    nav {{
      border-right: 1px solid var(--line);
      background: var(--panel);
      padding: 24px 16px;
    }}
    .brand {{
      font-size: 18px;
      font-weight: 700;
      line-height: 1.25;
      margin: 0 0 24px;
    }}
    .nav-link {{
      display: block;
      border-radius: 6px;
      color: var(--ink);
      padding: 10px 12px;
      text-decoration: none;
      font-size: 14px;
      line-height: 1.3;
    }}
    .nav-link + .nav-link {{ margin-top: 4px; }}
    .nav-link[aria-current="page"] {{
      background: var(--accent-soft);
      color: var(--accent);
      font-weight: 700;
    }}
    main {{
      padding: 32px;
      max-width: 1120px;
      width: 100%;
    }}
    h1 {{
      font-size: 30px;
      line-height: 1.15;
      margin: 0 0 8px;
    }}
    .lede {{
      color: var(--muted);
      font-size: 15px;
      margin: 0 0 28px;
      max-width: 760px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 16px;
    }}
    .actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 0 0 20px;
    }}
    .action-link,
    .action-form button {{
      background: var(--accent);
      border: 0;
      border-radius: 6px;
      color: #ffffff;
      cursor: pointer;
      font-size: 14px;
      font-weight: 700;
      line-height: 1.2;
      padding: 10px 12px;
      text-decoration: none;
    }}
    .action-form {{
      margin: 0;
    }}
    .run-controls {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
      margin-bottom: 16px;
    }}
    .run-control-form {{
      display: grid;
      gap: 10px;
    }}
    .run-control-form button {{
      background: var(--accent);
      border: 0;
      border-radius: 6px;
      color: #ffffff;
      cursor: pointer;
      font: inherit;
      font-weight: 700;
      justify-self: start;
      padding: 10px 12px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      min-height: 132px;
    }}
    .panel h2 {{
      font-size: 16px;
      margin: 0 0 10px;
    }}
    .metric {{
      font-size: 28px;
      font-weight: 700;
      margin: 0 0 6px;
    }}
    .muted {{ color: var(--muted); }}
    .notice {{
      background: var(--warn-soft);
      border-color: #f0d28f;
    }}
    .wide-panel {{
      margin-top: 16px;
    }}
    .compact-list,
    .video-list {{
      margin: 0;
      padding-left: 18px;
    }}
    .compact-list li + li {{
      margin-top: 8px;
    }}
    .video-list {{
      list-style: none;
      padding-left: 0;
    }}
    .video-row {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 16px;
      align-items: center;
      border-top: 1px solid var(--line);
      padding: 12px 0;
    }}
    .video-caption {{
      font-weight: 700;
      margin: 0 0 4px;
    }}
    .video-row a {{
      color: var(--accent);
      font-weight: 700;
    }}
    .content-list {{
      display: grid;
      gap: 16px;
    }}
    .scraped-card-header {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 16px;
      align-items: start;
    }}
    .scraped-card-header h2 {{
      margin: 0 0 4px;
    }}
    .metadata-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin: 16px 0;
    }}
    .metadata-grid dt {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      margin: 0 0 3px;
      text-transform: uppercase;
    }}
    .metadata-grid dd {{
      margin: 0;
      overflow-wrap: anywhere;
    }}
    .table-scroll {{
      overflow-x: auto;
      width: 100%;
    }}
    .data-table {{
      border-collapse: collapse;
      min-width: 1180px;
      width: 100%;
    }}
    .data-table th,
    .data-table td {{
      border-top: 1px solid var(--line);
      font-size: 13px;
      line-height: 1.35;
      padding: 10px 8px;
      text-align: left;
      vertical-align: top;
    }}
    .data-table th {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
    }}
    .data-table a {{
      color: var(--accent);
      font-weight: 700;
    }}
    h3 {{
      font-size: 14px;
      margin: 14px 0 8px;
    }}
    .output-links {{
      min-width: 180px;
    }}
    .curation-form {{
      border-top: 1px solid var(--line);
      display: grid;
      gap: 12px;
      padding-top: 14px;
    }}
    .curation-form fieldset {{
      border: 0;
      margin: 0;
      padding: 0;
    }}
    .curation-form legend,
    .field-label {{
      color: var(--muted);
      display: grid;
      font-size: 13px;
      font-weight: 700;
      gap: 6px;
    }}
    .label-grid {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px 14px;
      margin-top: 8px;
    }}
    .check-label {{
      align-items: center;
      display: inline-flex;
      gap: 6px;
      font-size: 13px;
      font-weight: 400;
    }}
    .field-label input,
    .field-label textarea {{
      border: 1px solid var(--line);
      border-radius: 6px;
      color: var(--ink);
      font: inherit;
      padding: 9px 10px;
      width: 100%;
    }}
    .field-label textarea {{
      min-height: 70px;
      resize: vertical;
    }}
    .curation-form button {{
      background: var(--accent);
      border: 0;
      border-radius: 6px;
      color: #ffffff;
      font: inherit;
      font-weight: 700;
      justify-self: start;
      padding: 10px 12px;
    }}
    .settings-form {{
      display: grid;
      gap: 14px;
    }}
    .settings-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }}
    .settings-form select {{
      border: 1px solid var(--line);
      border-radius: 6px;
      color: var(--ink);
      font: inherit;
      padding: 9px 10px;
      width: 100%;
    }}
    .settings-form button,
    .rollback-form button {{
      background: var(--accent);
      border: 0;
      border-radius: 6px;
      color: #ffffff;
      font: inherit;
      font-weight: 700;
      justify-self: start;
      padding: 10px 12px;
    }}
    .history-list {{
      display: grid;
      gap: 12px;
      list-style: none;
      margin: 0;
      padding: 0;
    }}
    .history-item {{
      border-top: 1px solid var(--line);
      padding-top: 12px;
    }}
    .rollback-form {{
      display: grid;
      gap: 8px;
      margin-top: 10px;
    }}
    .recommendation-list {{
      display: grid;
      gap: 16px;
    }}
    .recommendation-header {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 16px;
      align-items: start;
    }}
    .status-pill {{
      background: #eef1ec;
      border-radius: 999px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      line-height: 1;
      padding: 7px 9px;
      white-space: nowrap;
    }}
    .search-form {{
      display: grid;
      gap: 12px;
    }}
    .search-form input {{
      border: 1px solid var(--line);
      border-radius: 6px;
      color: var(--ink);
      font: inherit;
      padding: 10px 12px;
      width: 100%;
    }}
    .search-form button {{
      background: var(--accent);
      border: 0;
      border-radius: 6px;
      color: #ffffff;
      cursor: pointer;
      font: inherit;
      font-weight: 700;
      justify-self: start;
      padding: 10px 12px;
    }}
    .facet-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px 14px;
    }}
    .search-result-list {{
      display: grid;
      gap: 12px;
    }}
    .search-result-header {{
      align-items: start;
      display: grid;
      gap: 12px;
      grid-template-columns: minmax(0, 1fr) auto;
    }}
    .recommendation-form {{
      align-items: end;
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 14px;
    }}
    .recommendation-form select,
    .recommendation-form input {{
      border: 1px solid var(--line);
      border-radius: 6px;
      color: var(--ink);
      font: inherit;
      padding: 9px 10px;
    }}
    .recommendation-form button {{
      background: var(--accent);
      border: 0;
      border-radius: 6px;
      color: #ffffff;
      font: inherit;
      font-weight: 700;
      padding: 10px 12px;
    }}
    .pattern-list {{
      display: grid;
      gap: 16px;
    }}
    .pattern-header {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 16px;
      align-items: start;
    }}
    .pattern-form {{
      border-top: 1px solid var(--line);
      display: grid;
      gap: 12px;
      margin-top: 14px;
      padding-top: 14px;
    }}
    .pattern-form-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }}
    .pattern-form button {{
      background: var(--accent);
      border: 0;
      border-radius: 6px;
      color: #ffffff;
      font: inherit;
      font-weight: 700;
      justify-self: start;
      padding: 10px 12px;
    }}
    code {{
      background: #eef1ec;
      border-radius: 4px;
      padding: 2px 4px;
    }}
    @media (max-width: 760px) {{
      .layout {{ grid-template-columns: 1fr; }}
      nav {{
        border-right: 0;
        border-bottom: 1px solid var(--line);
      }}
      main {{ padding: 24px 18px; }}
      .grid {{ grid-template-columns: 1fr; }}
      .video-row {{ grid-template-columns: 1fr; }}
      .scraped-card-header,
      .run-controls,
      .settings-grid,
      .pattern-form-grid,
      .facet-grid,
      .metadata-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="layout">
    <nav aria-label="Dashboard sections">
      <p class="brand">Nattome Scrape Quality Dashboard</p>
      {nav}
    </nav>
    <main>
      {overview}
    </main>
  </div>
</body>
</html>
"""


def _render_nav_item(label: str, route: str, active_path: str) -> str:
    current = ' aria-current="page"' if route == active_path else ""
    return f'<a class="nav-link" href="{html.escape(route)}"{current}>{html.escape(label)}</a>'


def _render_search(workspace: Path, query_params: dict[str, list[str]]) -> str:
    normalized_query = _normalize_query_params(query_params)
    search_query = _first_form_value(normalized_query, "q")
    selected_facets = {
        key: values
        for key, values in normalized_query.items()
        if key != "q" and values
    }
    response = search_dashboard_records(
        workspace,
        query=search_query,
        facets=selected_facets,
    )
    return f"""
      <h1>Global Search</h1>
      <p class="lede">Search indexed dashboard records and combine facets across videos, runs, curation, patterns, POVs, reports, and docs.</p>
      <section class="panel wide-panel" aria-label="Global dashboard search form">
        {_render_search_form(response)}
      </section>
      <section class="panel wide-panel" aria-label="Global search results">
        <h2>Results</h2>
        {_render_search_results(response)}
      </section>
    """


def _normalize_query_params(query_params: dict[str, object]) -> dict[str, list[str]]:
    normalized: dict[str, list[str]] = {}
    for key, value in query_params.items():
        if isinstance(value, list):
            normalized[key] = [str(item) for item in value]
        elif isinstance(value, tuple):
            normalized[key] = [str(item) for item in value]
        else:
            normalized[key] = [str(value)]
    return normalized


def _render_search_form(response: SearchResponse) -> str:
    facet_controls = "".join(
        _render_facet_group(response, facet_name)
        for facet_name in [
            "record_type",
            "run_date",
            "run_type",
            "config_version",
            "source_input",
            "video_status",
            "label",
            "score_band",
            "relevance_band",
            "engagement_band",
            "freshness",
            "author",
            "hashtag_topic",
            "pattern",
            "pov",
            "market",
            "campaign",
            "product",
            "pipeline_phase",
            "pipeline_phase_status",
        ]
        if response.facets.get(facet_name)
    )
    return f"""
      <form class="search-form" method="get" action="/search">
        <label class="field-label">
          Keyword
          <input type="search" name="q" value="{html.escape(response.query)}">
        </label>
        <div class="facet-grid">
          {facet_controls}
        </div>
        <button type="submit">Search</button>
      </form>
    """


def _render_facet_group(response: SearchResponse, facet_name: str) -> str:
    values = response.facets.get(facet_name, ())
    selected = set(response.selected_facets.get(facet_name, ()))
    checkboxes = []
    for value in values[:12]:
        checked = " checked" if value in selected else ""
        checkboxes.append(
            f"""
            <label class="check-label">
              <input type="checkbox" name="{html.escape(facet_name)}" value="{html.escape(value)}"{checked}>
              {html.escape(value)}
            </label>
            """
        )
    return f"""
      <fieldset>
        <legend>{html.escape(facet_name.replace("_", " ").title())}</legend>
        <div class="label-grid">{"".join(checkboxes)}</div>
      </fieldset>
    """


def _render_search_results(response: SearchResponse) -> str:
    if not response.results:
        return '<p class="muted">No matching dashboard records found.</p>'
    return f"""
      <div class="search-result-list">
        {"".join(_render_search_result(result) for result in response.results)}
      </div>
    """


def _render_search_result(result: object) -> str:
    url = str(getattr(result, "url"))
    link = (
        f'<a href="{html.escape(url)}">Open</a>'
        if url
        else '<span class="muted">No direct link</span>'
    )
    facet_text = _search_result_facet_text(getattr(result, "facets"))
    return f"""
      <article class="panel">
        <div class="search-result-header">
          <div>
            <span class="status-pill">{html.escape(str(getattr(result, "record_type")).replace("_", " "))}</span>
            <h3>{html.escape(str(getattr(result, "title")))}</h3>
          </div>
          {link}
        </div>
        <p>{html.escape(str(getattr(result, "context"))[:360])}</p>
        <p class="muted">{html.escape(facet_text)}</p>
      </article>
    """


def _search_result_facet_text(facets: dict[str, tuple[str, ...]]) -> str:
    parts = []
    for name in ["run_date", "run_type", "config_version", "video_status", "label", "pattern", "pov", "pipeline_phase_status"]:
        values = facets.get(name)
        if values:
            parts.append(f"{name.replace('_', ' ')}: {', '.join(values)}")
    return " | ".join(parts)


def _render_overview(workspace: Path) -> str:
    workspace = Path(workspace)
    index_pipeline_artifacts(workspace)
    compute_scrape_quality_scores(workspace)
    compute_pipeline_health(workspace)
    overview = _load_latest_overview(workspace)
    actions = _render_overview_actions()
    if overview is None:
        return f"""
      <h1>Latest Run Overview</h1>
      <p class="lede">No indexed runs yet. The dashboard is ready once a Batch Analysis Run is available.</p>
      {actions}
      <section class="grid" aria-label="Overview status">
        <article class="panel notice">
          <h2>Scrape Quality Score</h2>
          <p class="metric muted">--</p>
          <p class="muted">No raw scrape candidates have been indexed.</p>
        </article>
        <article class="panel notice">
          <h2>Pipeline Health</h2>
          <p class="metric muted">Waiting</p>
          <p class="muted">No pipeline run has been indexed for review.</p>
        </article>
        <article class="panel">
          <h2>Dashboard Store</h2>
          <p class="metric">SQLite</p>
          <p class="muted"><code>{html.escape(str(workspace / DASHBOARD_DB_PATH))}</code></p>
        </article>
        <article class="panel">
          <h2>Latest Run</h2>
          <p class="muted">Run timestamp and run type will appear after indexing.</p>
        </article>
        <article class="panel">
          <h2>Current Config Version</h2>
          <p class="muted">No active run configuration has been indexed.</p>
        </article>
        <article class="panel">
          <h2>Top Quality Drivers</h2>
          <p class="muted">Quality drivers will appear after scrape scoring.</p>
        </article>
      </section>
    """

    run = overview["run"]
    score = overview["score"]
    health_summary = overview["health"]
    config = overview["config"]
    quality_metric = str(score["score"]) if score else "--"
    quality_band = score["band"] if score else "not scored"
    health_status = health_summary["status"] if health_summary else "unknown"
    health_impact = health_summary["impact_summary"] if health_summary else "Pipeline health has not been computed."
    config_version = config.get("version") or "Not recorded"
    next_scheduled_run = config.get("next_scheduled_run") or config.get("next_run") or "Not scheduled"
    return f"""
      <h1>Latest Run Overview</h1>
      <p class="lede">Latest indexed Batch Analysis Run, scrape quality, pipeline health, and marketer review queue.</p>
      {actions}
      <section class="grid" aria-label="Overview status">
        <article class="panel">
          <h2>Scrape Quality Score</h2>
          <p class="metric">{html.escape(quality_metric)}</p>
          <p class="muted">{html.escape(quality_band)}</p>
        </article>
        <article class="panel {_health_panel_class(health_summary)}">
          <h2>Pipeline Health</h2>
          <p class="metric">{html.escape(health_status)}</p>
          <p class="muted">{html.escape(health_impact)}</p>
        </article>
        <article class="panel">
          <h2>Latest Run</h2>
          <p class="metric">{html.escape(run["run_id"])}</p>
          <p class="muted">{html.escape(run["run_timestamp"] or "Timestamp not recorded")} - {html.escape(run["mode"] or "Run type not recorded")}</p>
        </article>
        <article class="panel">
          <h2>Current Config Version</h2>
          <p class="metric">{html.escape(str(config_version))}</p>
          <p class="muted">Next scheduled run: {html.escape(str(next_scheduled_run))}</p>
        </article>
        <article class="panel">
          <h2>Top Quality Drivers</h2>
          {_render_quality_drivers(score)}
        </article>
        <article class="panel">
          <h2>Health Drilldown</h2>
          {_render_health_items(health_summary, overview["phase_issues"])}
        </article>
      </section>
      <section class="panel wide-panel" aria-label="Top raw scraped videos">
        <h2>Top Raw Scraped Videos</h2>
        {_render_video_preview(overview["videos"])}
      </section>
    """


def _render_overview_actions() -> str:
    return """
      <div class="actions" aria-label="Primary dashboard actions">
        <form class="action-form" method="post" action="/manual-runs/trigger">
          <input type="hidden" name="run_type" value="scrape_only">
          <button type="submit">Run scrape now</button>
        </form>
        <form class="action-form" method="post" action="/manual-runs/trigger">
          <input type="hidden" name="run_type" value="full_pipeline">
          <button type="submit">Run full pipeline</button>
        </form>
        <a class="action-link" href="/scrape-settings">Edit scrape settings</a>
        <a class="action-link" href="/run-history">View run history</a>
        <a class="action-link" href="/scraped-content">Browse content library</a>
      </div>
    """


def _render_run_history(workspace: Path, *, run_history_run_id: str = "") -> str:
    history = load_run_history(workspace)
    detail_markup = ""
    if run_history_run_id:
        try:
            detail_markup = _render_run_history_detail(load_run_history_detail(workspace, run_history_run_id))
        except ValueError:
            detail_markup = """
      <section class="panel wide-panel notice">
        <h2>Run detail unavailable</h2>
        <p class="muted">The selected run was not found in the indexed history.</p>
      </section>
            """
    return f"""
      <h1>Run History</h1>
      <p class="lede">Trend monitoring for scheduled and manual runs, with audit links back to existing reports and workbooks.</p>
      <div class="actions" aria-label="Run history exports">
        <a class="action-link" href="/exports/run-summaries.csv">Export run summaries CSV</a>
      </div>
      {_render_manual_run_controls()}
      <section class="panel wide-panel" aria-label="Run history table">
        <h2>Runs</h2>
        {_render_run_history_rows(history.rows)}
      </section>
      <section class="panel wide-panel" aria-label="Trend monitoring">
        <h2>Trend Monitoring</h2>
        {_render_trend_points(history.trend_points)}
      </section>
      <section class="panel wide-panel" aria-label="Config overlays">
        <h2>Config Overlays</h2>
        {_render_config_overlays(history.config_overlays)}
      </section>
      {detail_markup}
    """


def _render_manual_run_controls() -> str:
    return """
      <section class="run-controls" aria-label="Manual run controls">
        <article class="panel">
          <h2>Run scrape now</h2>
          <p class="muted">Estimated runtime: 3-8 minutes.</p>
          <p class="muted">Expected outputs: raw top-30 scrape JSON and daily top-5 handoff.</p>
          <form class="run-control-form" method="post" action="/manual-runs/trigger">
            <input type="hidden" name="run_type" value="scrape_only">
            <button type="submit">Run scrape now</button>
          </form>
        </article>
        <article class="panel">
          <h2>Run full pipeline</h2>
          <p class="muted">Estimated runtime: 15-30 minutes.</p>
          <p class="muted">Expected outputs: scrape JSON, evidence run folder, reports, workbook, and delivery log.</p>
          <form class="run-control-form" method="post" action="/manual-runs/trigger">
            <input type="hidden" name="run_type" value="full_pipeline">
            <button type="submit">Run full pipeline</button>
          </form>
        </article>
      </section>
    """


def _render_run_history_rows(rows: list[object]) -> str:
    if not rows:
        return '<p class="muted">No scheduled or manual runs have been indexed yet.</p>'
    body = "\n".join(_render_run_history_row(row) for row in rows)
    return f"""
      <div class="table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th>Run</th>
              <th>Timestamp</th>
              <th>Config</th>
              <th>Score</th>
              <th>Raw</th>
              <th>Eligible</th>
              <th>Selected</th>
              <th>Relevance</th>
              <th>Engagement</th>
              <th>Freshness</th>
              <th>Duplicate/noise</th>
              <th>Health</th>
              <th>Top issue</th>
              <th>Outputs</th>
            </tr>
          </thead>
          <tbody>{body}</tbody>
        </table>
      </div>
    """


def _render_run_history_row(row: object) -> str:
    return f"""
      <tr>
        <td><a href="/run-history?run_id={html.escape(getattr(row, "run_id"))}">{html.escape(str(getattr(row, "run_type")).title())}</a><br><code>{html.escape(getattr(row, "run_id"))}</code><br><span class="muted">Source: {html.escape(getattr(row, "source_type"))}. By {html.escape(getattr(row, "triggered_by"))}.</span></td>
        <td>{html.escape(getattr(row, "timestamp"))}</td>
        <td>{html.escape(getattr(row, "config_version"))}</td>
        <td>{_score_text(getattr(row, "scrape_quality_score"))}</td>
        <td>{getattr(row, "raw_candidates")}</td>
        <td>{getattr(row, "eligible_candidates")}</td>
        <td>{getattr(row, "selected_count")}</td>
        <td>{_percent_text(getattr(row, "average_nattome_relevance"))}</td>
        <td>{_percent_text(getattr(row, "average_engagement"))}</td>
        <td>{_score_text(getattr(row, "freshness_score"))}</td>
        <td>{_score_text(getattr(row, "duplicate_noise_score"))}</td>
        <td>{html.escape(getattr(row, "pipeline_health"))}</td>
        <td>{html.escape(getattr(row, "top_issue"))}</td>
        <td>{_render_output_links(getattr(row, "output_links"))}</td>
      </tr>
    """


def _render_trend_points(points: list[object]) -> str:
    if not points:
        return '<p class="muted">Trend charts will appear after scheduled runs are indexed.</p>'
    items = []
    for point in points:
        items.append(
            f"""
            <li>
              <strong>{html.escape(getattr(point, "timestamp"))}</strong>:
              score {_score_text(getattr(point, "score"))},
              candidates {getattr(point, "candidate_volume")},
              yield {_percent_text(getattr(point, "eligibility_yield"))},
              relevance {_percent_text(getattr(point, "average_relevance"))},
              engagement {_percent_text(getattr(point, "average_engagement"))},
              config {html.escape(getattr(point, "config_version"))}.
            </li>
            """
        )
    return f'<ol class="compact-list">{"".join(items)}</ol>'


def _render_config_overlays(overlays: list[object]) -> str:
    if not overlays:
        return '<p class="muted">No config version changes have been indexed yet.</p>'
    items = [
        f"<li><strong>{html.escape(getattr(overlay, 'version'))}</strong> first appears at {html.escape(getattr(overlay, 'first_seen_at'))} on <code>{html.escape(getattr(overlay, 'run_id'))}</code>.</li>"
        for overlay in overlays
    ]
    return f'<ul class="compact-list">{"".join(items)}</ul>'


def _render_pipeline_architecture(workspace: Path) -> str:
    architecture = load_pipeline_architecture(workspace)
    return f"""
      <h1>Pipeline Architecture</h1>
      <p class="lede">Scrape to score to select to analyze to report. This read-only view links the docs, decisions, indexed run phases, outputs, and data lineage behind the Nattome TikTok discovery pipeline.</p>
      <section class="panel wide-panel" aria-label="Pipeline flow">
        <h2>High-Level Flow</h2>
        {_render_architecture_flow(architecture.pipeline_flow)}
      </section>
      <section class="grid" aria-label="Architecture decisions and status">
        <article class="panel">
          <h2>Tool Stack and Decisions</h2>
          {_render_tool_decisions(architecture.tool_decisions)}
        </article>
        <article class="panel">
          <h2>Phase Status Map</h2>
          {_render_phase_statuses(architecture.phase_statuses)}
        </article>
        <article class="panel">
          <h2>Data Lineage</h2>
          {_render_lineage_steps(architecture.data_lineage)}
        </article>
      </section>
      <section class="panel wide-panel" aria-label="File and output map">
        <h2>File and Output Map</h2>
        {_render_file_output_map(architecture.file_output_map)}
      </section>
      <section class="panel wide-panel" aria-label="Indexed architecture docs">
        <h2>Indexed Architecture Docs</h2>
        {_render_architecture_documents(architecture.documents)}
      </section>
    """


def _render_architecture_flow(steps: list[object]) -> str:
    items = [
        f"<li><strong>{html.escape(getattr(step, 'name'))}</strong>: {html.escape(getattr(step, 'summary'))}</li>"
        for step in steps
    ]
    return f'<ol class="compact-list">{"".join(items)}</ol>'


def _render_tool_decisions(decisions: list[object]) -> str:
    if not decisions:
        return '<p class="muted">No tool decisions are available.</p>'
    items = [
        f"<li><strong>{html.escape(getattr(decision, 'name'))}</strong>: {html.escape(getattr(decision, 'summary'))}</li>"
        for decision in decisions
    ]
    return f'<ul class="compact-list">{"".join(items)}</ul>'


def _render_phase_statuses(phases: list[object]) -> str:
    if not phases:
        return '<p class="muted">No indexed phase metadata is available.</p>'
    items = []
    for phase in phases:
        detail = getattr(phase, "detail")
        detail_markup = f' <span class="muted">{html.escape(detail)}</span>' if detail else ""
        run_id = getattr(phase, "run_id")
        run_markup = f' <code>{html.escape(run_id)}</code>' if run_id else ""
        items.append(
            f"<li><strong>{html.escape(getattr(phase, 'name'))}</strong>: {html.escape(getattr(phase, 'status'))}{run_markup}{detail_markup}</li>"
        )
    return f'<ul class="compact-list">{"".join(items)}</ul>'


def _render_lineage_steps(steps: list[object]) -> str:
    if not steps:
        return '<p class="muted">No lineage data is available.</p>'
    items = []
    for step in steps:
        path = getattr(step, "path")
        path_markup = f' <code>{html.escape(path)}</code>' if path else ""
        items.append(
            f"<li><strong>{html.escape(getattr(step, 'name'))}</strong>: {html.escape(getattr(step, 'status'))}{path_markup}<br><span class=\"muted\">{html.escape(getattr(step, 'summary'))}</span></li>"
        )
    return f'<ul class="compact-list">{"".join(items)}</ul>'


def _render_file_output_map(file_output_map: dict[str, list[str]]) -> str:
    sections = []
    for label, paths in file_output_map.items():
        if not paths:
            body = '<p class="muted">No indexed files.</p>'
        else:
            body = '<ul class="compact-list">' + "".join(
                f"<li><code>{html.escape(path)}</code></li>"
                for path in paths[:12]
            ) + "</ul>"
            if len(paths) > 12:
                body += f'<p class="muted">+{len(paths) - 12} more indexed files</p>'
        sections.append(f"<article><h3>{html.escape(label)}</h3>{body}</article>")
    return f'<div class="grid">{"".join(sections)}</div>'


def _render_architecture_documents(documents: list[object]) -> str:
    if not documents:
        return '<p class="muted">No README, CONTEXT, PRD, ADR, or skill docs have been indexed.</p>'
    items = [
        f"<li><strong>{html.escape(getattr(doc, 'title'))}</strong> <span class=\"muted\">{html.escape(getattr(doc, 'doc_type'))}</span><br><code>{html.escape(getattr(doc, 'path'))}</code></li>"
        for doc in documents
    ]
    return f'<ul class="compact-list">{"".join(items)}</ul>'


def _render_run_history_detail(detail: object) -> str:
    row = getattr(detail, "row")
    return f"""
      <section class="panel wide-panel" aria-label="Run drilldown">
        <h2>Run Drilldown: {html.escape(getattr(row, "run_id"))}</h2>
        <div class="grid">
          <article>
            <h3>Raw Content</h3>
            {_render_content_items(getattr(detail, "raw_content"))}
          </article>
          <article>
            <h3>Selected Content</h3>
            {_render_content_items(getattr(detail, "selected_content"))}
          </article>
          <article>
            <h3>Quality Drivers</h3>
            {_render_quality_driver_items(getattr(detail, "quality_drivers"))}
          </article>
        </div>
        <h3>Pipeline Phases</h3>
        {_render_phase_items(getattr(detail, "pipeline_phases"))}
        <h3>Logs and Linked Outputs</h3>
        {_render_output_links(getattr(detail, "output_links"))}
      </section>
    """


def _render_content_items(items: list[object]) -> str:
    if not items:
        return '<p class="muted">No content records are linked to this run.</p>'
    rendered = [
        f"<li><strong>{html.escape(getattr(item, 'video_id'))}</strong>: {html.escape(getattr(item, 'caption'))}</li>"
        for item in items
    ]
    return f'<ul class="compact-list">{"".join(rendered)}</ul>'


def _render_quality_driver_items(drivers: list[object]) -> str:
    if not drivers:
        return '<p class="muted">No quality drivers were computed for this run.</p>'
    rendered = []
    for driver in drivers:
        if isinstance(driver, dict):
            rendered.append(f"<li>{html.escape(str(driver.get('message') or driver.get('component') or 'Driver'))}</li>")
    return f'<ul class="compact-list">{"".join(rendered)}</ul>' if rendered else '<p class="muted">No quality drivers were computed for this run.</p>'


def _render_phase_items(phases: list[object]) -> str:
    if not phases:
        return '<p class="muted">No pipeline phase metadata is linked to this run.</p>'
    rendered = []
    for phase in phases:
        if isinstance(phase, dict):
            rendered.append(
                f"<li><strong>{html.escape(str(phase.get('name') or 'phase'))}</strong>: {html.escape(str(phase.get('status') or 'unknown'))}</li>"
            )
    return f'<ul class="compact-list">{"".join(rendered)}</ul>'


def _render_output_links(links: list[object]) -> str:
    if not links:
        return '<span class="muted">No output links</span>'
    items = []
    for link in links:
        path = getattr(link, "path")
        label = getattr(link, "label")
        artifact_type = getattr(link, "artifact_type")
        items.append(
            f'<li><a href="{html.escape(path)}">{html.escape(label)}</a> <span class="muted">({html.escape(artifact_type)})</span></li>'
        )
    return f'<ul class="compact-list output-links">{"".join(items)}</ul>'


def _score_text(value: object) -> str:
    return "--" if value is None else html.escape(str(value))


def _percent_text(value: object) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "--"
    return f"{number * 100:.1f}%"


def _load_latest_overview(workspace: Path) -> dict[str, object] | None:
    db_path = workspace / DASHBOARD_DB_PATH
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        run = connection.execute(
            """
            SELECT *
            FROM batch_runs
            ORDER BY COALESCE(run_timestamp, '') DESC, run_id DESC
            LIMIT 1
            """
        ).fetchone()
        if run is None:
            return None
        run_id = run["run_id"]
        score = connection.execute(
            "SELECT * FROM scrape_quality_scores WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        health_summary = connection.execute(
            "SELECT * FROM pipeline_health_summaries WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        selected = connection.execute(
            "SELECT * FROM selected_batches WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        videos = _latest_run_videos(connection, run_id, selected)
        manifest = _json_loads(run["raw_json"])
        return {
            "run": dict(run),
            "score": dict(score) if score else None,
            "health": dict(health_summary) if health_summary else None,
            "videos": [dict(video) for video in videos],
            "config": _run_configuration(manifest, selected),
            "phase_issues": _phase_issues(manifest),
        }
    finally:
        connection.close()


def _latest_run_videos(
    connection: sqlite3.Connection,
    run_id: str,
    selected: sqlite3.Row | None,
) -> list[sqlite3.Row]:
    if selected and selected["candidate_source"]:
        rows = list(
            connection.execute(
                """
                SELECT *
                FROM raw_videos
                WHERE source_artifact_path = ?
                ORDER BY play_count DESC, like_count DESC, video_id
                LIMIT 5
                """,
                (selected["candidate_source"],),
            )
        )
        if rows:
            return rows
    return list(
        connection.execute(
            """
            SELECT *
            FROM raw_videos
            WHERE run_id = ?
            ORDER BY play_count DESC, like_count DESC, video_id
            LIMIT 5
            """,
            (run_id,),
        )
    )


def _run_configuration(manifest: dict[str, object], selected: sqlite3.Row | None) -> dict[str, object]:
    configuration = manifest.get("configuration")
    if not isinstance(configuration, dict):
        configuration = {}
    selected_value = _json_loads(selected["raw_json"]) if selected else {}
    selected_json = selected_value if isinstance(selected_value, dict) else {}
    return {
        "version": configuration.get("version")
        or configuration.get("config_version")
        or selected_json.get("config_version")
        or selected_json.get("settings_version"),
        "next_scheduled_run": configuration.get("next_scheduled_run")
        or configuration.get("next_run")
        or selected_json.get("next_scheduled_run"),
    }


def _phase_issues(manifest: dict[str, object]) -> list[str]:
    phases = manifest.get("phases")
    if not isinstance(phases, list):
        return []
    issues: list[str] = []
    for phase in phases:
        if not isinstance(phase, dict):
            continue
        status = str(phase.get("status") or "")
        if status not in {"failed", "error", "blocked"}:
            continue
        detail = phase.get("exception") or phase.get("exception_text") or phase.get("error") or phase.get("reason")
        if detail:
            issues.append(str(detail))
    return issues


def _render_quality_drivers(score: dict[str, object] | None) -> str:
    if not score:
        return '<p class="muted">No scrape quality drivers have been computed.</p>'
    drivers = _json_loads(score.get("drivers_json"))
    if not isinstance(drivers, list) or not drivers:
        return '<p class="muted">No scrape quality drivers were recorded.</p>'
    items = []
    for driver in drivers[:4]:
        if not isinstance(driver, dict):
            continue
        direction = str(driver.get("direction") or "neutral")
        message = str(driver.get("message") or driver.get("component") or "Quality driver")
        items.append(
            f'<li><strong>{html.escape(direction.title())}</strong>: {html.escape(message)}</li>'
        )
    return f'<ul class="compact-list">{"".join(items)}</ul>' if items else '<p class="muted">No scrape quality drivers were recorded.</p>'


def _render_health_items(
    health_summary: dict[str, object] | None,
    phase_issues: list[str],
) -> str:
    items: list[str] = []
    if health_summary:
        health_items = _json_loads(health_summary.get("items_json"))
        if isinstance(health_items, list):
            for item in health_items[:4]:
                if not isinstance(item, dict):
                    continue
                component = str(item.get("component") or "pipeline")
                status = str(item.get("status") or "unknown")
                impact = str(item.get("impact") or "")
                items.append(
                    f'<li><strong>{html.escape(component.replace("_", " ").title())}</strong>: {html.escape(status)}. {html.escape(impact)}</li>'
                )
    for issue in phase_issues[:2]:
        items.append(f'<li><strong>Run issue</strong>: {html.escape(issue)}</li>')
    return f'<ul class="compact-list">{"".join(items)}</ul>' if items else '<p class="muted">No pipeline drilldown is available.</p>'


def _render_video_preview(videos: list[dict[str, object]]) -> str:
    if not videos:
        return '<p class="muted">No raw scraped videos are available for this run.</p>'
    items = []
    for video in videos:
        caption = str(video.get("caption") or "Untitled TikTok")
        url = str(video.get("tiktok_url") or "")
        author = str(video.get("author_handle") or "Unknown creator")
        play_count = _format_count(video.get("play_count"))
        like_count = _format_count(video.get("like_count"))
        link = (
            f'<a href="{html.escape(url)}" target="_blank" rel="noopener">Open TikTok</a>'
            if url
            else '<span class="muted">No TikTok link</span>'
        )
        items.append(
            f"""
            <li class="video-row">
              <div>
                <p class="video-caption">{html.escape(caption)}</p>
                <p class="muted">{html.escape(author)} - {play_count} views - {like_count} likes</p>
              </div>
              {link}
            </li>
            """
        )
    return f'<ul class="video-list">{"".join(items)}</ul>'


def _health_panel_class(health_summary: dict[str, object] | None) -> str:
    if not health_summary:
        return "notice"
    severity = str(health_summary.get("severity") or "")
    return "notice" if severity in {"warning", "error", "blocked"} else ""


def _format_count(value: object) -> str:
    try:
        count = int(value)
    except (TypeError, ValueError):
        return "--"
    return f"{count:,}"


def _json_loads(value: object) -> object:
    if not value:
        return {}
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except json.JSONDecodeError:
        return {}


def _render_scraped_content(workspace: Path) -> str:
    workspace = Path(workspace)
    index_pipeline_artifacts(workspace)
    videos = _load_scraped_videos(workspace)
    if not videos:
        return """
      <h1>Raw Scraped Videos</h1>
      <p class="lede">No indexed raw scraped videos yet.</p>
      <section class="panel notice">
        <h2>Scraped Content</h2>
        <p class="muted">Raw TikTok scrape files will appear here after the artifact indexer finds them.</p>
      </section>
    """
    return f"""
      <h1>Raw Scraped Videos</h1>
      <p class="lede">Browse indexed TikTok scrape records, review selection status, and save lightweight curation notes.</p>
      <div class="actions" aria-label="Raw video exports">
        <a class="action-link" href="/exports/raw-videos.csv">Export raw videos CSV</a>
      </div>
      <section class="content-list" aria-label="Raw scraped videos">
        {"".join(_render_scraped_video(video) for video in videos)}
      </section>
    """


def _load_scraped_videos(workspace: Path) -> list[dict[str, object]]:
    connection = sqlite3.connect(workspace / DASHBOARD_DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT
                raw_videos.*,
                video_curation.labels AS curation_labels,
                video_curation.exclude_similar_reason AS exclude_similar_reason,
                video_curation.note AS curation_note
            FROM raw_videos
            LEFT JOIN video_curation
                ON video_curation.tiktok_video_id = raw_videos.video_id
            ORDER BY COALESCE(play_count, 0) DESC, video_id
            """
        )
        return [dict(row) for row in rows]
    finally:
        connection.close()


def _render_scraped_video(video: dict[str, object]) -> str:
    video_id = str(video.get("video_id") or "")
    labels = _curation_labels(video.get("curation_labels"))
    caption = str(video.get("caption") or "Untitled TikTok")
    hashtags = _hashtag_text(video.get("hashtags_json"))
    source_input = str(video.get("source_input") or "Not recorded")
    status = _display_status(video.get("selection_status"))
    engagement = _engagement_rate(video)
    relevance = _relevance_label(caption, hashtags, source_input)
    freshness = _freshness_label(video.get("created_at"))
    downloadable = "downloadable" if int(video.get("is_downloadable") or 0) else "not downloadable"
    tiktok_url = str(video.get("tiktok_url") or "")
    link = (
        f'<a href="{html.escape(tiktok_url)}" target="_blank" rel="noopener">Open TikTok</a>'
        if tiktok_url
        else '<span class="muted">No TikTok link</span>'
    )
    return f"""
        <article class="panel scraped-card">
          <div class="scraped-card-header">
            <div>
              <h2>{html.escape(caption)}</h2>
              <p class="muted">{html.escape(str(video.get("author_handle") or "Unknown creator"))} - {html.escape(status)}</p>
            </div>
            {link}
          </div>
          <dl class="metadata-grid">
            {_metadata_item("Hashtags", hashtags or "None")}
            {_metadata_item("Source Input", source_input)}
            {_metadata_item("Views", _format_count(video.get("play_count")))}
            {_metadata_item("Likes", _format_count(video.get("like_count")))}
            {_metadata_item("Comments", _format_count(video.get("comment_count")))}
            {_metadata_item("Shares", _format_count(video.get("share_count")))}
            {_metadata_item("Created Date", str(video.get("created_at") or "Not recorded"))}
            {_metadata_item("Freshness", freshness)}
            {_metadata_item("Engagement", engagement)}
            {_metadata_item("Relevance", relevance)}
            {_metadata_item("Downloadability", downloadable)}
            {_metadata_item("Run ID", str(video.get("run_id") or "Not tied to a run"))}
            {_metadata_item("Config Version", str(video.get("config_version") or "Not recorded"))}
            {_metadata_item("Status", status)}
          </dl>
          {_render_curation_form(video_id, labels, str(video.get("curation_note") or ""), str(video.get("exclude_similar_reason") or ""))}
        </article>
    """


def _metadata_item(label: str, value: str) -> str:
    return f"""
      <div>
        <dt>{html.escape(label)}</dt>
        <dd>{html.escape(value)}</dd>
      </div>
    """


def _render_curation_form(
    video_id: str,
    selected_labels: list[str],
    note: str,
    exclude_similar_reason: str,
) -> str:
    checkboxes = []
    for label in CURATION_LABELS:
        checked = " checked" if label in selected_labels else ""
        checkboxes.append(
            f"""
            <label class="check-label">
              <input type="checkbox" name="labels" value="{html.escape(label)}"{checked}>
              {html.escape(label)}
            </label>
            """
        )
    return f"""
      <form class="curation-form" method="post" action="/scraped-content/curation">
        <input type="hidden" name="video_id" value="{html.escape(video_id)}">
        <fieldset>
          <legend>Labels</legend>
          <div class="label-grid">{"".join(checkboxes)}</div>
        </fieldset>
        <label class="field-label">
          Exclude Similar Reason
          <input type="text" name="exclude_similar_reason" maxlength="160" value="{html.escape(exclude_similar_reason)}">
        </label>
        <label class="field-label">
          Note
          <textarea name="note" maxlength="500">{html.escape(note)}</textarea>
        </label>
        <button type="submit">Save curation</button>
      </form>
    """


def _save_video_curation(workspace: Path, form: dict[str, list[str]]) -> None:
    video_id = _first_form_value(form, "video_id")
    if not video_id:
        return
    labels = [label for label in form.get("labels", []) if label in CURATION_LABELS]
    exclude_reason = _first_form_value(form, "exclude_similar_reason")[:160]
    if "Exclude Similar" in labels and not exclude_reason.strip():
        labels = [label for label in labels if label != "Exclude Similar"]
    note = _first_form_value(form, "note")[:500]
    connection = sqlite3.connect(workspace / DASHBOARD_DB_PATH)
    try:
        connection.execute(
            """
            INSERT INTO video_curation (
                tiktok_video_id,
                labels,
                exclude_similar_reason,
                note,
                updated_at
            )
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(tiktok_video_id) DO UPDATE SET
                labels = excluded.labels,
                exclude_similar_reason = excluded.exclude_similar_reason,
                note = excluded.note,
                updated_at = CURRENT_TIMESTAMP
            """,
            (video_id, json.dumps(labels, ensure_ascii=True), exclude_reason, note),
        )
        connection.commit()
    finally:
        connection.close()


def _render_scrape_settings(workspace: Path) -> str:
    active = get_active_settings_version(workspace)
    versions = list_settings_versions(workspace)
    settings = active.new_settings
    active_label = _version_label(active.version)
    return f"""
      <h1>Production Scrape Settings</h1>
      <p class="lede">Validated marketer-editable scrape settings. Risky pipeline internals stay read-only in MVP.</p>
      <section class="grid" aria-label="Scrape settings status">
        <article class="panel">
          <h2>Current production config version</h2>
          <p class="metric">{html.escape(active_label)}</p>
          <p class="muted">Next scheduled run will use version {html.escape(active_label)}.</p>
        </article>
        <article class="panel">
          <h2>Last change reason</h2>
          <p>{html.escape(active.reason)}</p>
          <p class="muted">{html.escape(active.changed_by)} {html.escape(active.timestamp)}</p>
        </article>
        <article class="panel">
          <h2>Read-only MVP settings</h2>
          {_render_read_only_settings()}
        </article>
      </section>
      <section class="panel wide-panel">
        <h2>Edit production settings</h2>
        {_render_settings_form(settings)}
      </section>
      <section class="panel wide-panel">
        <h2>Config version history</h2>
        {_render_version_history(versions)}
      </section>
    """


def _render_settings_form(settings: dict[str, object]) -> str:
    checked = " checked" if settings.get("requires_downloadable_video") else ""
    return f"""
      <form class="settings-form" method="post" action="/scrape-settings/save">
        <div class="settings-grid">
          {_textarea_field("Hashtags", "hashtags", _lines(settings.get("hashtags")))}
          {_textarea_field("Keywords", "keywords", _lines(settings.get("keywords")))}
          {_textarea_field("Competitor profiles", "competitor_profiles", _lines(settings.get("competitor_profiles")))}
          {_textarea_field("Exclusion terms", "exclusion_terms", _lines(settings.get("exclusion_terms")))}
          <label class="field-label">
            Scrape scope
            <select name="scope">
              {_scope_options(str(settings.get("scope") or "all"))}
            </select>
          </label>
          {_input_field("Results per input", "results_per_input", settings.get("results_per_input"))}
          {_input_field("Top N", "top_n", settings.get("top_n"))}
          {_input_field("Daily selection size", "daily_selection_size", settings.get("daily_selection_size"))}
          {_input_field("Minimum views", "minimum_views", settings.get("minimum_views"))}
          {_input_field("Maximum age days", "maximum_age_days", settings.get("maximum_age_days"))}
          {_input_field("Minimum weighted engagement rate", "minimum_weighted_engagement_rate", settings.get("minimum_weighted_engagement_rate"))}
          <label class="check-label">
            <input type="checkbox" name="requires_downloadable_video" value="on"{checked}>
            Require downloadable video
          </label>
          {_input_field("User", "user", "local")}
          {_textarea_field("Save reason", "reason", "")}
        </div>
        <button type="submit">Save production settings</button>
      </form>
    """


def _render_read_only_settings() -> str:
    items = [
        f"<li><strong>{html.escape(label)}</strong>: {html.escape(value)}</li>"
        for label, value in READ_ONLY_SETTINGS.items()
    ]
    return f'<ul class="compact-list">{"".join(items)}</ul>'


def _render_version_history(versions: list[object]) -> str:
    if not versions:
        return '<p class="muted">No saved config versions yet.</p>'
    items = []
    for version in versions:
        label = _version_label(version.version)
        active = "active" if version.is_active else "inactive"
        rollback_text = (
            f"Rollback of v{version.rollback_of_version}. "
            if version.rollback_of_version
            else ""
        )
        settings = version.new_settings
        rollback_form = "" if version.is_active else _render_rollback_form(version.version)
        items.append(
            f"""
            <li class="history-item">
              <p><strong>{html.escape(label)}</strong> - {html.escape(active)} - {html.escape(rollback_text)}{html.escape(version.reason)}</p>
              <p class="muted">{html.escape(version.changed_by)} {html.escape(version.timestamp)}</p>
              <p class="muted">Hashtags: {html.escape(", ".join(settings.get("hashtags") or []))}</p>
              <p class="muted">Keywords: {html.escape(", ".join(settings.get("keywords") or []))}</p>
              {rollback_form}
            </li>
            """
        )
    return f'<ul class="history-list">{"".join(items)}</ul>'


def _render_rollback_form(target_version: int) -> str:
    return f"""
      <form class="rollback-form" method="post" action="/scrape-settings/rollback">
        <input type="hidden" name="target_version" value="{target_version}">
        <label class="field-label">
          Rollback reason
          <input type="text" name="reason" maxlength="240">
        </label>
        <label class="field-label">
          User
          <input type="text" name="user" value="local" maxlength="120">
        </label>
        <button type="submit">Roll back to {_version_label(target_version)}</button>
      </form>
    """


def _save_scrape_settings(workspace: Path, form: dict[str, list[str]]) -> None:
    save_settings_version(
        workspace,
        _settings_form_payload(form),
        reason=_first_form_value(form, "reason"),
        user=_first_form_value(form, "user") or "local",
    )


def _rollback_scrape_settings(workspace: Path, form: dict[str, list[str]]) -> None:
    target_version = int(_first_form_value(form, "target_version") or "0")
    rollback_settings_version(
        workspace,
        target_version=target_version,
        reason=_first_form_value(form, "reason"),
        user=_first_form_value(form, "user") or "local",
    )


def _render_recommendations(workspace: Path) -> str:
    recommendations = generate_recommendations(workspace)
    if not recommendations:
        return """
      <h1>Passive Recommendations</h1>
      <p class="lede">No scrape-quality recommendations need attention.</p>
      <section class="panel">
        <h2>Recommendations</h2>
        <p class="muted">The current indexed scrape data does not have advisory recommendations.</p>
      </section>
    """
    return f"""
      <h1>Passive Recommendations</h1>
      <p class="lede">Advisory scrape-quality recommendations with supporting runs, videos, source inputs, labels, and config versions. Settings are never changed automatically.</p>
      <section class="recommendation-list" aria-label="Passive recommendations">
        {"".join(_render_recommendation(recommendation) for recommendation in recommendations)}
      </section>
    """


def _render_recommendation(recommendation: object) -> str:
    title = str(getattr(recommendation, "recommendation_type")).replace("_", " ").title()
    status = _display_recommendation_status(str(getattr(recommendation, "status")))
    return f"""
        <article class="panel">
          <div class="recommendation-header">
            <div>
              <h2>{html.escape(title)}</h2>
              <p>{html.escape(str(getattr(recommendation, "summary")))}</p>
            </div>
            <span class="status-pill">{html.escape(status)}</span>
          </div>
          {_render_recommendation_evidence(getattr(recommendation, "supporting_evidence"))}
          {_render_recommendation_status_form(getattr(recommendation, "id"), str(getattr(recommendation, "status")))}
        </article>
    """


def _render_recommendation_evidence(evidence: object) -> str:
    if not isinstance(evidence, list) or not evidence:
        return '<p class="muted">No supporting evidence recorded.</p>'
    items = []
    for item in evidence[:10]:
        if not isinstance(item, dict):
            continue
        items.append(f"<li>{html.escape(_evidence_text(item))}</li>")
    return f"""
      <h3>Supporting evidence</h3>
      <ul class="compact-list">{"".join(items)}</ul>
    """


def _evidence_text(item: dict[str, object]) -> str:
    entity_type = str(item.get("entity_type") or "evidence")
    if entity_type == "run":
        return f"Run {item.get('run_id')} scored {item.get('score')}: {item.get('message')}"
    if entity_type == "video":
        source = f" from {item.get('source_input')}" if item.get("source_input") else ""
        return f"Video {item.get('video_id')}{source}: {item.get('caption')}"
    if entity_type == "source_input":
        return (
            f"Source input {item.get('source_input')}: "
            f"{item.get('candidate_count')} candidates, {item.get('eligible_count')} eligible"
        )
    if entity_type == "label":
        note = f" Note: {item.get('note')}" if item.get("note") else ""
        exclude_reason = (
            f" Exclude similar reason: {item.get('exclude_similar_reason')}"
            if item.get("exclude_similar_reason")
            else ""
        )
        return f"Label {item.get('label')} on video {item.get('video_id')}.{note}{exclude_reason}"
    if entity_type == "config_version":
        return f"Config version {item.get('version')} used by run {item.get('run_id')}"
    return json.dumps(item, ensure_ascii=True, sort_keys=True)


def _render_recommendation_status_form(recommendation_id: int, active_status: str) -> str:
    options = []
    for status in sorted(VALID_RECOMMENDATION_STATUSES):
        selected = " selected" if status == active_status else ""
        options.append(
            f'<option value="{html.escape(status)}"{selected}>{html.escape(_display_recommendation_status(status))}</option>'
        )
    return f"""
      <form class="recommendation-form" method="post" action="/recommendations/status">
        <input type="hidden" name="recommendation_id" value="{recommendation_id}">
        <label class="field-label">
          Lifecycle state
          <select name="status">{"".join(options)}</select>
        </label>
        <label class="field-label">
          User
          <input type="text" name="user" value="local" maxlength="120">
        </label>
        <button type="submit">Update state</button>
      </form>
    """


def _update_recommendation_status(workspace: Path, form: dict[str, list[str]]) -> None:
    recommendation_id = int(_first_form_value(form, "recommendation_id") or "0")
    update_recommendation_status(
        workspace,
        recommendation_id,
        _first_form_value(form, "status"),
        user=_first_form_value(form, "user") or "local",
    )


def _display_recommendation_status(status: str) -> str:
    return status.replace("_", " ")


def _render_pattern_library(workspace: Path) -> str:
    candidates = generate_candidate_patterns(workspace)
    approved_patterns = list_approved_patterns(workspace)
    candidate_body = (
        "".join(_render_candidate_pattern(candidate) for candidate in candidates)
        if candidates
        else '<p class="muted">No candidate patterns have been generated from indexed run analysis yet.</p>'
    )
    approved_body = (
        "".join(_render_approved_pattern(workspace, pattern) for pattern in approved_patterns)
        if approved_patterns
        else '<p class="muted">No approved patterns have been curated yet.</p>'
    )
    return f"""
      <h1>Pattern Library</h1>
      <p class="lede">External TikTok mechanics stay separate from Nattome interpretation: generated candidates on one side, marketer-approved canonical patterns on the other.</p>
      <div class="actions" aria-label="Pattern exports">
        <a class="action-link" href="/exports/approved-patterns.md">Export approved patterns Markdown</a>
      </div>
      <section class="panel wide-panel">
        <h2>Candidate Patterns</h2>
        <div class="pattern-list" aria-label="Candidate patterns">
          {candidate_body}
        </div>
      </section>
      <section class="panel wide-panel">
        <h2>Approved Patterns</h2>
        <div class="pattern-list" aria-label="Approved patterns">
          {approved_body}
        </div>
      </section>
      <section class="panel wide-panel">
        <h2>Create Approved Pattern</h2>
        {_render_pattern_create_form()}
      </section>
    """


def _render_candidate_pattern(candidate: object) -> str:
    return f"""
      <article class="panel">
        <div class="pattern-header">
          <div>
            <h3>{html.escape(str(getattr(candidate, "pattern_name")))}</h3>
            <p>{html.escape(str(getattr(candidate, "why_it_works")))}</p>
          </div>
          <span class="status-pill">{html.escape(str(getattr(candidate, "status")))}</span>
        </div>
        <dl class="metadata-grid">
          {_metadata_item("Hook Type", str(getattr(candidate, "hook_type")))}
          {_metadata_item("Format Type", str(getattr(candidate, "format_type")))}
          {_metadata_item("Emotional Trigger", str(getattr(candidate, "emotional_trigger")))}
          {_metadata_item("Source Run", str(getattr(candidate, "source_run_id") or "Not linked"))}
        </dl>
        {_render_pattern_sources(getattr(candidate, "source_videos"))}
        {_render_pattern_evidence(getattr(candidate, "performance_evidence"))}
        <form class="pattern-form" method="post" action="/pattern-library/approve">
          <input type="hidden" name="candidate_id" value="{getattr(candidate, "id")}">
          <div class="pattern-form-grid">
            {_input_field("User", "user", "local")}
            {_input_field("Approval notes", "notes", "")}
          </div>
          <button type="submit">Approve candidate</button>
        </form>
      </article>
    """


def _render_approved_pattern(workspace: Path, pattern: object) -> str:
    versions = list_pattern_versions(workspace, getattr(pattern, "id"))
    return f"""
      <article class="panel">
        <div class="pattern-header">
          <div>
            <h3>{html.escape(str(getattr(pattern, "pattern_name")))}</h3>
            <p>{html.escape(str(getattr(pattern, "why_it_works")))}</p>
          </div>
          <span class="status-pill">{html.escape(str(getattr(pattern, "status")))} v{getattr(pattern, "version")}</span>
        </div>
        <dl class="metadata-grid">
          {_metadata_item("Hook Type", str(getattr(pattern, "hook_type")))}
          {_metadata_item("Format Type", str(getattr(pattern, "format_type")))}
          {_metadata_item("Emotional Trigger", str(getattr(pattern, "emotional_trigger")))}
          {_metadata_item("Freshness", str(getattr(pattern, "freshness") or "Not set"))}
          {_metadata_item("Shoot Difficulty", str(getattr(pattern, "shoot_difficulty") or "Not set"))}
          {_metadata_item("Related POVs", ", ".join(getattr(pattern, "related_povs") or []) or "None")}
          {_metadata_item("Targeting", _targeting_text(getattr(pattern, "targeting")))}
          {_metadata_item("Updated By", str(getattr(pattern, "updated_by")))}
        </dl>
        {_render_pattern_sources(getattr(pattern, "source_videos"))}
        <h3>Nattome adaptation notes</h3>
        <p>{html.escape(str(getattr(pattern, "nattome_adaptation_notes") or "Not set"))}</p>
        <h3>Avoid notes</h3>
        <p>{html.escape(str(getattr(pattern, "avoid_notes") or "None"))}</p>
        {_render_pattern_evidence(getattr(pattern, "performance_evidence"))}
        {_render_pattern_versions(versions)}
        {_render_pattern_edit_form(pattern)}
        {_render_pattern_archive_form(pattern)}
      </article>
    """


def _render_pattern_sources(source_videos: object) -> str:
    if not isinstance(source_videos, list) or not source_videos:
        return '<p class="muted">No source videos linked.</p>'
    items = []
    for video in source_videos[:8]:
        if not isinstance(video, dict):
            continue
        video_id = str(video.get("video_id") or "source")
        url = str(video.get("tiktok_url") or "")
        caption = str(video.get("caption") or "")
        source = f' <a href="{html.escape(url)}">{html.escape(url)}</a>' if url else ""
        items.append(f"<li><strong>{html.escape(video_id)}</strong>{source}<br>{html.escape(caption)}</li>")
    return f"""
      <h3>Source videos</h3>
      <ul class="compact-list">{"".join(items)}</ul>
    """


def _render_pattern_evidence(evidence: object) -> str:
    if not isinstance(evidence, dict) or not evidence:
        return '<p class="muted">No performance evidence recorded.</p>'
    items = [
        f"<li>{html.escape(str(key).replace('_', ' ').title())}: {html.escape(str(value))}</li>"
        for key, value in evidence.items()
    ]
    return f"""
      <h3>Performance evidence</h3>
      <ul class="compact-list">{"".join(items)}</ul>
    """


def _render_pattern_versions(versions: list[object]) -> str:
    if not versions:
        return '<p class="muted">No version history recorded.</p>'
    items = [
        (
            f"<li>v{getattr(version, 'version')} {html.escape(str(getattr(version, 'change_type')))} "
            f"by {html.escape(str(getattr(version, 'changed_by')))} "
            f"{html.escape(str(getattr(version, 'changed_at')))}</li>"
        )
        for version in versions
    ]
    return f"""
      <h3>Version history</h3>
      <ul class="compact-list">{"".join(items)}</ul>
    """


def _render_pattern_create_form() -> str:
    return f"""
      <form class="pattern-form" method="post" action="/pattern-library/create">
        <div class="pattern-form-grid">
          {_input_field("Pattern name", "pattern_name", "")}
          {_input_field("Hook type", "hook_type", "")}
          {_input_field("Format type", "format_type", "")}
          {_input_field("Emotional trigger", "emotional_trigger", "")}
          {_input_field("Shoot difficulty", "shoot_difficulty", "")}
          {_input_field("Freshness", "freshness", "")}
          {_input_field("Target market", "target_market", "")}
          {_input_field("Target persona", "target_persona", "")}
          {_textarea_field("Source videos", "source_videos", "")}
          {_textarea_field("Why it works", "why_it_works", "")}
          {_textarea_field("Nattome adaptation notes", "nattome_adaptation_notes", "")}
          {_textarea_field("Related POVs", "related_povs", "")}
          {_textarea_field("Avoid notes", "avoid_notes", "")}
          {_input_field("User", "user", "local")}
        </div>
        <button type="submit">Create approved pattern</button>
      </form>
    """


def _render_pattern_edit_form(pattern: object) -> str:
    return f"""
      <form class="pattern-form" method="post" action="/pattern-library/edit">
        <input type="hidden" name="pattern_id" value="{getattr(pattern, "id")}">
        <div class="pattern-form-grid">
          {_input_field("Pattern name", "pattern_name", getattr(pattern, "pattern_name"))}
          {_input_field("Hook type", "hook_type", getattr(pattern, "hook_type"))}
          {_input_field("Format type", "format_type", getattr(pattern, "format_type"))}
          {_input_field("Emotional trigger", "emotional_trigger", getattr(pattern, "emotional_trigger"))}
          {_input_field("Status", "status", getattr(pattern, "status"))}
          {_input_field("Shoot difficulty", "shoot_difficulty", getattr(pattern, "shoot_difficulty"))}
          {_input_field("Freshness", "freshness", getattr(pattern, "freshness"))}
          {_input_field("Target market", "target_market", _targeting_field(getattr(pattern, "targeting"), "market"))}
          {_input_field("Target persona", "target_persona", _targeting_field(getattr(pattern, "targeting"), "persona"))}
          {_textarea_field("Source videos", "source_videos", _source_video_lines(getattr(pattern, "source_videos")))}
          {_textarea_field("Why it works", "why_it_works", getattr(pattern, "why_it_works"))}
          {_textarea_field("Nattome adaptation notes", "nattome_adaptation_notes", getattr(pattern, "nattome_adaptation_notes"))}
          {_textarea_field("Related POVs", "related_povs", "\n".join(getattr(pattern, "related_povs") or []))}
          {_textarea_field("Avoid notes", "avoid_notes", getattr(pattern, "avoid_notes"))}
          {_input_field("User", "user", "local")}
        </div>
        <button type="submit">Save pattern</button>
      </form>
    """


def _render_pattern_archive_form(pattern: object) -> str:
    if str(getattr(pattern, "status")) == "archived":
        return ""
    return f"""
      <form class="pattern-form" method="post" action="/pattern-library/archive">
        <input type="hidden" name="pattern_id" value="{getattr(pattern, "id")}">
        {_input_field("User", "user", "local")}
        <button type="submit">Archive pattern</button>
      </form>
    """


def _approve_pattern_candidate(workspace: Path, form: dict[str, list[str]]) -> None:
    approve_candidate_pattern(
        workspace,
        int(_first_form_value(form, "candidate_id") or "0"),
        user=_first_form_value(form, "user") or "local",
        notes=_first_form_value(form, "notes"),
    )


def _create_pattern(workspace: Path, form: dict[str, list[str]]) -> None:
    create_approved_pattern(
        workspace,
        _pattern_form_payload(form),
        user=_first_form_value(form, "user") or "local",
        status="draft",
    )


def _edit_pattern(workspace: Path, form: dict[str, list[str]]) -> None:
    update_approved_pattern(
        workspace,
        int(_first_form_value(form, "pattern_id") or "0"),
        _pattern_form_payload(form, include_status=True),
        user=_first_form_value(form, "user") or "local",
    )


def _archive_pattern(workspace: Path, form: dict[str, list[str]]) -> None:
    archive_approved_pattern(
        workspace,
        int(_first_form_value(form, "pattern_id") or "0"),
        user=_first_form_value(form, "user") or "local",
    )


def _render_nattome_pov_library(workspace: Path) -> str:
    povs = list_nattome_povs(workspace)
    approved_patterns = [
        pattern for pattern in list_approved_patterns(workspace)
        if str(getattr(pattern, "status")) == "approved"
    ]
    pattern_names = {int(getattr(pattern, "id")): str(getattr(pattern, "pattern_name")) for pattern in approved_patterns}
    pov_body = (
        "".join(_render_nattome_pov(workspace, pov, pattern_names) for pov in povs)
        if povs
        else '<p class="muted">No Nattome POV entries have been created yet.</p>'
    )
    pattern_link_body = (
        "".join(
            f"<li><strong>{html.escape(str(getattr(pattern, 'pattern_name')))}</strong> "
            f"<span class=\"muted\">{html.escape(str(getattr(pattern, 'hook_type')))} / {html.escape(str(getattr(pattern, 'format_type')))}</span></li>"
            for pattern in approved_patterns
        )
        if approved_patterns
        else '<li class="muted">No approved external patterns are available to link.</li>'
    )
    return f"""
      <h1>Nattome POV Library</h1>
      <p class="lede">Owned Nattome interpretations live here: brand-safe readings, targeting, adaptation rules, and source links. External TikTok mechanics remain in the Pattern Library and are linked only as approved inputs.</p>
      <div class="actions" aria-label="Nattome POV exports">
        <a class="action-link" href="/exports/nattome-povs.md">Export Nattome POVs Markdown</a>
      </div>
      <section class="panel wide-panel">
        <h2>Nattome POV Entries</h2>
        <div class="pattern-list" aria-label="Nattome POV entries">
          {pov_body}
        </div>
      </section>
      <section class="panel wide-panel">
        <h2>Approved Pattern Links</h2>
        <p class="muted">Use these approved external mechanics as links; keep the Nattome-owned interpretation in each POV entry.</p>
        <ul class="compact-list">{pattern_link_body}</ul>
      </section>
      <section class="panel wide-panel">
        <h2>Create Nattome POV</h2>
        {_render_nattome_pov_create_form(approved_patterns)}
      </section>
    """


def _render_nattome_pov(workspace: Path, pov: object, pattern_names: dict[int, str]) -> str:
    versions = list_nattome_pov_versions(workspace, getattr(pov, "id"))
    return f"""
      <article class="panel">
        <div class="pattern-header">
          <div>
            <h3>{html.escape(str(getattr(pov, "title")))}</h3>
            <p>{html.escape(str(getattr(pov, "description")))}</p>
          </div>
          <span class="status-pill">{html.escape(str(getattr(pov, "status")))} v{getattr(pov, "version")}</span>
        </div>
        <dl class="metadata-grid">
          {_metadata_item("Product", str(getattr(pov, "product") or "Nattome"))}
          {_metadata_item("Campaign", str(getattr(pov, "campaign") or "Not set"))}
          {_metadata_item("Market", str(getattr(pov, "market") or "Malaysia"))}
          {_metadata_item("Language", str(getattr(pov, "language") or "mixed/English"))}
          {_metadata_item("Audience / Avatar", str(getattr(pov, "audience_avatar") or "Not set"))}
          {_metadata_item("Symptom / Occasion", str(getattr(pov, "symptom_occasion") or "Not set"))}
          {_metadata_item("Channel", str(getattr(pov, "channel") or "TikTok"))}
          {_metadata_item("Updated By", str(getattr(pov, "updated_by")))}
        </dl>
        <h3>Brand-safe interpretation</h3>
        <p>{html.escape(str(getattr(pov, "brand_safe_interpretation") or "Not set"))}</p>
        <h3>Adaptation rules</h3>
        <p>{html.escape(str(getattr(pov, "adaptation_rules") or "Not set"))}</p>
        {_render_pov_source_links(getattr(pov, "source_links"))}
        {_render_pov_pattern_links(getattr(pov, "linked_pattern_ids"), pattern_names)}
        {_render_pattern_versions(versions)}
        {_render_nattome_pov_edit_form(pov, pattern_names)}
        {_render_nattome_pov_archive_form(pov)}
      </article>
    """


def _render_pov_source_links(source_links: object) -> str:
    if not isinstance(source_links, list) or not source_links:
        return '<p class="muted">No source links recorded.</p>'
    items = [
        f'<li><a href="{html.escape(str(link))}">{html.escape(str(link))}</a></li>'
        for link in source_links
        if str(link)
    ]
    return f"""
      <h3>Source links</h3>
      <ul class="compact-list">{"".join(items)}</ul>
    """


def _render_pov_pattern_links(linked_pattern_ids: object, pattern_names: dict[int, str]) -> str:
    if not isinstance(linked_pattern_ids, list) or not linked_pattern_ids:
        return '<p class="muted">No approved patterns linked.</p>'
    items = []
    for pattern_id in linked_pattern_ids:
        try:
            numeric_id = int(pattern_id)
        except (TypeError, ValueError):
            continue
        label = pattern_names.get(numeric_id, f"Approved pattern #{numeric_id}")
        items.append(f"<li>{html.escape(label)} <span class=\"muted\">#{numeric_id}</span></li>")
    return f"""
      <h3>Linked approved patterns</h3>
      <ul class="compact-list">{"".join(items)}</ul>
    """


def _render_nattome_pov_create_form(approved_patterns: list[object]) -> str:
    return f"""
      <form class="pattern-form" method="post" action="/nattome-pov-library/create">
        <div class="pattern-form-grid">
          {_input_field("Title", "title", "")}
          {_input_field("Product", "product", "Nattome")}
          {_input_field("Campaign", "campaign", "")}
          {_input_field("Market", "market", "Malaysia")}
          {_input_field("Language", "language", "mixed/English")}
          {_input_field("Audience / Avatar", "audience_avatar", "")}
          {_input_field("Symptom / Occasion", "symptom_occasion", "")}
          {_input_field("Channel", "channel", "TikTok")}
          {_textarea_field("Description", "description", "")}
          {_textarea_field("Brand-safe interpretation", "brand_safe_interpretation", "")}
          {_textarea_field("Adaptation rules", "adaptation_rules", "")}
          {_textarea_field("Source links", "source_links", "")}
          {_textarea_field("Linked approved pattern IDs", "linked_pattern_ids", _approved_pattern_id_lines(approved_patterns))}
          {_input_field("User", "user", "local")}
        </div>
        <button type="submit">Create Nattome POV</button>
      </form>
    """


def _render_nattome_pov_edit_form(pov: object, pattern_names: dict[int, str]) -> str:
    del pattern_names
    return f"""
      <form class="pattern-form" method="post" action="/nattome-pov-library/edit">
        <input type="hidden" name="pov_id" value="{getattr(pov, "id")}">
        <div class="pattern-form-grid">
          {_input_field("Title", "title", getattr(pov, "title"))}
          {_input_field("Status", "status", getattr(pov, "status"))}
          {_input_field("Product", "product", getattr(pov, "product"))}
          {_input_field("Campaign", "campaign", getattr(pov, "campaign"))}
          {_input_field("Market", "market", getattr(pov, "market"))}
          {_input_field("Language", "language", getattr(pov, "language"))}
          {_input_field("Audience / Avatar", "audience_avatar", getattr(pov, "audience_avatar"))}
          {_input_field("Symptom / Occasion", "symptom_occasion", getattr(pov, "symptom_occasion"))}
          {_input_field("Channel", "channel", getattr(pov, "channel"))}
          {_textarea_field("Description", "description", getattr(pov, "description"))}
          {_textarea_field("Brand-safe interpretation", "brand_safe_interpretation", getattr(pov, "brand_safe_interpretation"))}
          {_textarea_field("Adaptation rules", "adaptation_rules", getattr(pov, "adaptation_rules"))}
          {_textarea_field("Source links", "source_links", "\n".join(getattr(pov, "source_links") or []))}
          {_textarea_field("Linked approved pattern IDs", "linked_pattern_ids", "\n".join(str(item) for item in getattr(pov, "linked_pattern_ids") or []))}
          {_input_field("User", "user", "local")}
        </div>
        <button type="submit">Save Nattome POV</button>
      </form>
    """


def _render_nattome_pov_archive_form(pov: object) -> str:
    if str(getattr(pov, "status")) == "archived":
        return ""
    return f"""
      <form class="pattern-form" method="post" action="/nattome-pov-library/archive">
        <input type="hidden" name="pov_id" value="{getattr(pov, "id")}">
        {_input_field("User", "user", "local")}
        <button type="submit">Archive Nattome POV</button>
      </form>
    """


def _create_nattome_pov(workspace: Path, form: dict[str, list[str]]) -> None:
    create_nattome_pov(
        workspace,
        _nattome_pov_form_payload(form),
        user=_first_form_value(form, "user") or "local",
        status="draft",
    )


def _edit_nattome_pov(workspace: Path, form: dict[str, list[str]]) -> None:
    update_nattome_pov(
        workspace,
        int(_first_form_value(form, "pov_id") or "0"),
        _nattome_pov_form_payload(form, include_status=True),
        user=_first_form_value(form, "user") or "local",
    )


def _archive_nattome_pov(workspace: Path, form: dict[str, list[str]]) -> None:
    archive_nattome_pov(
        workspace,
        int(_first_form_value(form, "pov_id") or "0"),
        user=_first_form_value(form, "user") or "local",
    )


def _nattome_pov_form_payload(
    form: dict[str, list[str]],
    *,
    include_status: bool = False,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "title": _first_form_value(form, "title"),
        "description": _first_form_value(form, "description"),
        "brand_safe_interpretation": _first_form_value(form, "brand_safe_interpretation"),
        "adaptation_rules": _first_form_value(form, "adaptation_rules"),
        "product": _first_form_value(form, "product"),
        "campaign": _first_form_value(form, "campaign"),
        "market": _first_form_value(form, "market"),
        "language": _first_form_value(form, "language"),
        "audience_avatar": _first_form_value(form, "audience_avatar"),
        "symptom_occasion": _first_form_value(form, "symptom_occasion"),
        "channel": _first_form_value(form, "channel"),
        "source_links": _first_form_value(form, "source_links").splitlines(),
        "linked_pattern_ids": _first_form_value(form, "linked_pattern_ids").splitlines(),
    }
    if include_status:
        status = _first_form_value(form, "status") or "draft"
        if status not in NATTOME_POV_STATUSES:
            raise ValueError(f"Invalid Nattome POV status: {status}")
        payload["status"] = status
    return payload


def _approved_pattern_id_lines(approved_patterns: list[object]) -> str:
    ids = [str(getattr(pattern, "id")) for pattern in approved_patterns]
    return "\n".join(ids[:5])


def _pattern_form_payload(
    form: dict[str, list[str]],
    *,
    include_status: bool = False,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "pattern_name": _first_form_value(form, "pattern_name"),
        "hook_type": _first_form_value(form, "hook_type"),
        "format_type": _first_form_value(form, "format_type"),
        "emotional_trigger": _first_form_value(form, "emotional_trigger"),
        "source_videos": _parse_source_videos(_first_form_value(form, "source_videos")),
        "why_it_works": _first_form_value(form, "why_it_works"),
        "nattome_adaptation_notes": _first_form_value(form, "nattome_adaptation_notes"),
        "shoot_difficulty": _first_form_value(form, "shoot_difficulty"),
        "freshness": _first_form_value(form, "freshness"),
        "related_povs": _first_form_value(form, "related_povs").splitlines(),
        "avoid_notes": _first_form_value(form, "avoid_notes"),
        "targeting": {
            "market": _first_form_value(form, "target_market"),
            "persona": _first_form_value(form, "target_persona"),
        },
    }
    if include_status:
        status = _first_form_value(form, "status") or "draft"
        if status not in APPROVED_PATTERN_STATUSES:
            raise ValueError(f"Invalid pattern status: {status}")
        payload["status"] = status
    return payload


def _parse_source_videos(raw_value: str) -> list[dict[str, object]]:
    videos = []
    for line in raw_value.splitlines():
        line = line.strip()
        if not line:
            continue
        if "|" in line:
            video_id, url = [part.strip() for part in line.split("|", 1)]
        else:
            video_id, url = line, ""
        videos.append({"video_id": video_id, "tiktok_url": url})
    return videos


def _source_video_lines(source_videos: object) -> str:
    if not isinstance(source_videos, list):
        return ""
    lines = []
    for video in source_videos:
        if not isinstance(video, dict):
            continue
        lines.append(f"{video.get('video_id') or ''}|{video.get('tiktok_url') or ''}")
    return "\n".join(lines)


def _targeting_text(targeting: object) -> str:
    if not isinstance(targeting, dict) or not targeting:
        return "None"
    items = [f"{key}: {value}" for key, value in targeting.items() if value]
    return ", ".join(items) if items else "None"


def _targeting_field(targeting: object, key: str) -> str:
    return str(targeting.get(key) or "") if isinstance(targeting, dict) else ""


def _settings_form_payload(form: dict[str, list[str]]) -> dict[str, object]:
    return {
        "hashtags": _first_form_value(form, "hashtags"),
        "keywords": _first_form_value(form, "keywords"),
        "competitor_profiles": _first_form_value(form, "competitor_profiles"),
        "scope": _first_form_value(form, "scope") or "all",
        "results_per_input": _first_form_value(form, "results_per_input"),
        "top_n": _first_form_value(form, "top_n"),
        "daily_selection_size": _first_form_value(form, "daily_selection_size"),
        "minimum_views": _first_form_value(form, "minimum_views"),
        "maximum_age_days": _first_form_value(form, "maximum_age_days"),
        "minimum_weighted_engagement_rate": _first_form_value(
            form,
            "minimum_weighted_engagement_rate",
        ),
        "requires_downloadable_video": "requires_downloadable_video" in form,
        "exclusion_terms": _first_form_value(form, "exclusion_terms"),
    }


def _textarea_field(label: str, name: str, value: object) -> str:
    return f"""
      <label class="field-label">
        {html.escape(label)}
        <textarea name="{html.escape(name)}">{html.escape(str(value or ""))}</textarea>
      </label>
    """


def _input_field(label: str, name: str, value: object) -> str:
    return f"""
      <label class="field-label">
        {html.escape(label)}
        <input type="text" name="{html.escape(name)}" value="{html.escape(str(value or ""))}">
      </label>
    """


def _scope_options(active_scope: str) -> str:
    options = []
    for scope in ("all", "hashtags", "keywords", "profiles"):
        selected = " selected" if scope == active_scope else ""
        options.append(f'<option value="{scope}"{selected}>{scope}</option>')
    return "".join(options)


def _lines(value: object) -> str:
    if isinstance(value, list):
        return "\n".join(str(item) for item in value)
    return str(value or "")


def _version_label(version: int) -> str:
    return "Default" if version <= 0 else f"v{version}"


def _first_form_value(form: dict[str, list[str]], key: str) -> str:
    values = form.get(key) or [""]
    return values[0].strip()


def _first_query_values(query: dict[str, list[str]]) -> dict[str, str]:
    return {
        key: values[0].strip()
        for key, values in query.items()
        if values and values[0].strip()
    }


def _curation_labels(raw_value: object) -> list[str]:
    labels = _json_loads(raw_value)
    if not isinstance(labels, list):
        return []
    return [str(label) for label in labels if str(label) in CURATION_LABELS]


def _hashtag_text(raw_value: object) -> str:
    hashtags = _json_loads(raw_value)
    if not isinstance(hashtags, list):
        return ""
    return " ".join(f"#{str(tag).lstrip('#')}" for tag in hashtags)


def _display_status(value: object) -> str:
    status = str(value or "raw").lower()
    if status == "raw":
        return "raw only"
    if status in {"eligible", "selected", "analyzed"}:
        return status
    return "raw only"


def _engagement_rate(video: dict[str, object]) -> str:
    views = _int_value(video.get("play_count"))
    if views <= 0:
        return "--"
    likes = _int_value(video.get("like_count"))
    comments = _int_value(video.get("comment_count"))
    shares = _int_value(video.get("share_count"))
    rate = (likes + comments * 5 + shares * 10) / views
    return f"{rate * 100:.1f}%"


def _relevance_label(caption: str, hashtags: str, source_input: str) -> str:
    haystack = f"{caption} {hashtags} {source_input}".lower()
    matches = sum(1 for term in ("gut", "digest", "bloating", "reflux", "stomach") if term in haystack)
    if matches >= 2:
        return "high"
    if matches == 1:
        return "medium"
    return "low"


def _freshness_label(created_at: object) -> str:
    return "created date available" if created_at else "created date missing"


def _int_value(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _render_placeholder(title: str) -> str:
    escaped_title = html.escape(title)
    return f"""
      <h1>{escaped_title}</h1>
      <p class="lede">This dashboard section is reserved for a later implementation slice.</p>
      <section class="panel">
        <h2>{escaped_title}</h2>
        <p class="muted">The route is wired into the local app shell.</p>
      </section>
    """


def _title_for_path(path: str) -> str:
    for label, route in NAV_ITEMS:
        if route == path:
            return "Latest Run Overview" if route == "/" else label
    return "Dashboard"


def serve(
    workspace: Path | str = ".",
    host: str = "127.0.0.1",
    port: int = 8765,
    server_factory: Callable[..., DashboardServer] = DashboardServer,
) -> None:
    workspace_path = Path(workspace)
    initialize_dashboard_store(workspace_path)
    server = server_factory((host, port), create_handler(workspace_path))
    print(f"Nattome dashboard running at http://{host}:{server.server_address[1]}")
    print(f"Dashboard SQLite store: {workspace_path / DASHBOARD_DB_PATH}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping dashboard.")
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local Nattome dashboard shell.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--workspace", type=Path, default=Path("."))
    args = parser.parse_args()
    serve(workspace=args.workspace, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
