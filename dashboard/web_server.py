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
