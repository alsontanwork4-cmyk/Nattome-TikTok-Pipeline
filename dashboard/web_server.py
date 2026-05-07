from __future__ import annotations

import argparse
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urlparse

from .exports import (
    export_approved_patterns_markdown,
    export_nattome_povs_markdown,
    export_raw_videos_csv,
    export_run_summaries_csv,
)
from .manual_runs import trigger_manual_run
from .store import DASHBOARD_DB_PATH, initialize_dashboard_store
from .web_actions import (
    _approve_pattern_candidate,
    _archive_nattome_pov,
    _archive_pattern,
    _create_nattome_pov,
    _create_pattern,
    _edit_nattome_pov,
    _edit_pattern,
    _rollback_scrape_settings,
    _save_scrape_settings,
    _save_video_curation,
    _update_recommendation_status,
)
from .web_components import _first_form_value, _first_query_values
from .web_constants import NAV_ITEMS
from .web_layout import render_page

FormData = dict[str, list[str]]
ExportRoute = tuple[Callable[[Path, FormData], str], str, str]
PostFormAction = tuple[Callable[[Path, FormData], object], str]
NAV_ROUTES = {route for _, route in NAV_ITEMS}


def _export_raw_videos(workspace: Path, query: FormData) -> str:
    return export_raw_videos_csv(workspace, filters=_first_query_values(query))


def _export_run_summaries(workspace: Path, query: FormData) -> str:
    return export_run_summaries_csv(workspace)


def _export_approved_patterns(workspace: Path, query: FormData) -> str:
    return export_approved_patterns_markdown(workspace)


def _export_nattome_povs(workspace: Path, query: FormData) -> str:
    return export_nattome_povs_markdown(workspace)


GET_EXPORT_ROUTES: dict[str, ExportRoute] = {
    "/exports/raw-videos.csv": (
        _export_raw_videos,
        "text/csv; charset=utf-8",
        "nattome-raw-videos.csv",
    ),
    "/exports/run-summaries.csv": (
        _export_run_summaries,
        "text/csv; charset=utf-8",
        "nattome-run-summaries.csv",
    ),
    "/exports/approved-patterns.md": (
        _export_approved_patterns,
        "text/markdown; charset=utf-8",
        "nattome-approved-patterns.md",
    ),
    "/exports/nattome-povs.md": (
        _export_nattome_povs,
        "text/markdown; charset=utf-8",
        "nattome-povs.md",
    ),
}

POST_FORM_ACTIONS: dict[str, PostFormAction] = {
    "/scraped-content/curation": (_save_video_curation, "/scraped-content"),
    "/scrape-settings/save": (_save_scrape_settings, "/scrape-settings"),
    "/scrape-settings/rollback": (_rollback_scrape_settings, "/scrape-settings"),
    "/recommendations/status": (_update_recommendation_status, "/recommendations"),
    "/pattern-library/approve": (_approve_pattern_candidate, "/pattern-library"),
    "/pattern-library/create": (_create_pattern, "/pattern-library"),
    "/pattern-library/edit": (_edit_pattern, "/pattern-library"),
    "/pattern-library/archive": (_archive_pattern, "/pattern-library"),
    "/nattome-pov-library/create": (_create_nattome_pov, "/nattome-pov-library"),
    "/nattome-pov-library/edit": (_edit_nattome_pov, "/nattome-pov-library"),
    "/nattome-pov-library/archive": (_archive_nattome_pov, "/nattome-pov-library"),
}


class DashboardServer(ThreadingHTTPServer):
    daemon_threads = True


def resolve_dashboard_workspace(workspace: Path | str = ".") -> Path:
    """Return the pipeline workspace even when launched from a nested dashboard path."""
    workspace_path = Path(workspace).expanduser()
    if not workspace_path.is_absolute():
        workspace_path = Path.cwd() / workspace_path
    workspace_path = workspace_path.resolve()
    if _has_pipeline_workspace_markers(workspace_path):
        return workspace_path
    for parent in workspace_path.parents:
        if _has_pipeline_workspace_markers(parent) and (parent / "dashboard").is_dir():
            return parent
    return workspace_path


def _has_pipeline_workspace_markers(path: Path) -> bool:
    return (path / "runs" / "batch-analysis").is_dir() or (path / "data" / "raw_scrapes").is_dir()


def create_handler(
    workspace: Path | str = ".",
    *,
    manual_run_executor: Callable[..., object] | None = None,
) -> type[BaseHTTPRequestHandler]:
    workspace_path = resolve_dashboard_workspace(workspace)

    def trigger_manual_run_action(current_workspace: Path, form: FormData) -> object:
        return trigger_manual_run(
            current_workspace,
            _first_form_value(form, "run_type") or "scrape_only",
            triggered_by=_first_form_value(form, "user") or "local",
            executor=manual_run_executor,
        )

    post_form_actions = {
        **POST_FORM_ACTIONS,
        "/manual-runs/trigger": (trigger_manual_run_action, "/run-history"),
    }

    class DashboardRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed_path = self._request_path()
            if parsed_path == "/healthz":
                self._send_text("ok\n")
                return

            export_route = GET_EXPORT_ROUTES.get(parsed_path)
            if export_route:
                self._handle_export_route(export_route)
                return

            if parsed_path in NAV_ROUTES:
                initialize_dashboard_store(workspace_path)
                query = self._query_params()
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
            form_action = post_form_actions.get(self._request_path())
            if form_action:
                self._handle_form_action(form_action)
                return
            self.send_error(404, "Dashboard route not found")

        def log_message(self, format: str, *args: object) -> None:
            return

        def _request_path(self) -> str:
            return urlparse(self.path).path

        def _query_params(self) -> FormData:
            return parse_qs(urlparse(self.path).query)

        def _read_request_body(self) -> str:
            length = int(self.headers.get("Content-Length") or 0)
            return self.rfile.read(length).decode("utf-8")

        def _parse_form(self) -> FormData:
            return parse_qs(self._read_request_body())

        def _handle_export_route(self, export_route: ExportRoute) -> None:
            body_factory, content_type, filename = export_route
            initialize_dashboard_store(workspace_path)
            self._send_export(
                body_factory(workspace_path, self._query_params()),
                content_type=content_type,
                filename=filename,
            )

        def _handle_form_action(self, form_action: PostFormAction) -> None:
            action, redirect_location = form_action
            initialize_dashboard_store(workspace_path)
            form = self._parse_form()
            try:
                action(workspace_path, form)
            except ValueError as exc:
                self._send_error_page(400, str(exc))
                return
            self._redirect(redirect_location)

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
def serve(
    workspace: Path | str = ".",
    host: str = "127.0.0.1",
    port: int = 8765,
    server_factory: Callable[..., DashboardServer] = DashboardServer,
) -> None:
    workspace_path = resolve_dashboard_workspace(workspace)
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
