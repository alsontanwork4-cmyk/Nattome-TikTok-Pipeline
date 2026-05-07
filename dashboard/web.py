from __future__ import annotations

import argparse
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from .store import DASHBOARD_DB_PATH, initialize_dashboard_store


NAV_ITEMS = (
    ("Overview", "/"),
    ("Scraped Content", "/scraped-content"),
    ("Run History", "/run-history"),
    ("Scrape Settings", "/scrape-settings"),
    ("Recommendations", "/recommendations"),
    ("Pattern Library", "/pattern-library"),
    ("Nattome POV Library", "/nattome-pov-library"),
    ("Pipeline Architecture", "/pipeline-architecture"),
)


class DashboardServer(ThreadingHTTPServer):
    daemon_threads = True


def create_handler(workspace: Path | str = ".") -> type[BaseHTTPRequestHandler]:
    workspace_path = Path(workspace)

    class DashboardRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed_path = urlparse(self.path).path
            if parsed_path == "/healthz":
                self._send_text("ok\n")
                return
            if parsed_path in {route for _, route in NAV_ITEMS}:
                initialize_dashboard_store(workspace_path)
                self._send_html(render_page(parsed_path, workspace_path))
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

        def _send_text(self, body: str) -> None:
            encoded = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    return DashboardRequestHandler


def render_page(active_path: str, workspace: Path) -> str:
    title = _title_for_path(active_path)
    nav = "\n".join(
        _render_nav_item(label, route, active_path)
        for label, route in NAV_ITEMS
    )
    overview = _render_overview(workspace) if active_path == "/" else _render_placeholder(title)
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


def _render_overview(workspace: Path) -> str:
    db_path = workspace / DASHBOARD_DB_PATH
    return f"""
      <h1>Latest Run Overview</h1>
      <p class="lede">Local dashboard shell for monitoring scrape quality and pipeline health.</p>
      <section class="grid" aria-label="Overview status">
        <article class="panel">
          <h2>Scrape Quality Score</h2>
          <p class="metric muted">--</p>
          <p class="muted">No indexed scrape data yet.</p>
        </article>
        <article class="panel">
          <h2>Pipeline Health</h2>
          <p class="metric muted">Ready</p>
          <p class="muted">Overview loads without Apify, Gemini, or run artifacts.</p>
        </article>
        <article class="panel">
          <h2>Dashboard Store</h2>
          <p class="metric">SQLite</p>
          <p class="muted"><code>{html.escape(str(db_path))}</code></p>
        </article>
        <article class="panel notice">
          <h2>Latest Run</h2>
          <p class="muted">No Batch Analysis Run has been indexed.</p>
        </article>
        <article class="panel">
          <h2>Current Config Version</h2>
          <p class="muted">Settings versioning is initialized for later slices.</p>
        </article>
        <article class="panel">
          <h2>Top Quality Drivers</h2>
          <p class="muted">Artifact indexing and scoring will populate this area.</p>
        </article>
      </section>
    """


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
