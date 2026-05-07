from __future__ import annotations

import argparse
import html
import json
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from .health import compute_pipeline_health
from .indexer import index_pipeline_artifacts
from .quality import compute_scrape_quality_scores
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
    .actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 0 0 20px;
    }}
    .action-link {{
      background: var(--accent);
      border-radius: 6px;
      color: #ffffff;
      font-size: 14px;
      font-weight: 700;
      line-height: 1.2;
      padding: 10px 12px;
      text-decoration: none;
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
        <a class="action-link" href="/run-history">Run scrape now</a>
        <a class="action-link" href="/run-history">Run full pipeline</a>
        <a class="action-link" href="/scrape-settings">Edit scrape settings</a>
        <a class="action-link" href="/run-history">View run history</a>
        <a class="action-link" href="/scraped-content">Browse content library</a>
      </div>
    """


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
