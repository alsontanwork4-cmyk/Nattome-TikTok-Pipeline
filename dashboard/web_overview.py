from __future__ import annotations

import html
import sqlite3
from pathlib import Path

from .health import compute_pipeline_health
from .indexer import index_pipeline_artifacts
from .quality import compute_scrape_quality_scores
from .store import DASHBOARD_DB_PATH
from .web_components import (
    _display_status,
    _engagement_rate,
    _format_count,
    _freshness_label,
    _hashtag_text,
    _health_panel_class,
    _json_loads,
    _percent_text,
    _render_empty_state,
    _render_page_header,
    _score_text,
)

def _render_overview(workspace: Path) -> str:
    workspace = Path(workspace)
    index_pipeline_artifacts(workspace)
    compute_scrape_quality_scores(workspace)
    compute_pipeline_health(workspace)
    overview = _load_latest_overview(workspace)
    actions = _render_overview_actions()
    header = _render_page_header(
        "Latest Run Overview",
        "Local dashboard shell for monitoring scrape quality and pipeline health.",
        active_path="/",
    )
    if overview is None:
        db_path = html.escape(str(workspace / DASHBOARD_DB_PATH))
        return f"""
      {header}
      <p class="lede" style="margin-top:-12px;">No indexed runs yet. The dashboard is ready once a Batch Analysis Run is available.</p>
      {actions}
      <section class="grid" aria-label="Overview status">
        <article class="panel feature">
          <h2>Scrape Quality Score</h2>
          <p class="metric muted">--</p>
          <p class="muted">No raw scrape candidates have been indexed.</p>
        </article>
        <article class="panel feature">
          <h2>Pipeline Health</h2>
          <p class="metric">Ready</p>
          <p class="muted">Overview loads without Apify, Gemini, or run artifacts.</p>
        </article>
        <article class="panel feature">
          <h2>Dashboard Store</h2>
          <p class="metric">SQLite</p>
          <p class="muted"><code>{db_path}</code></p>
        </article>
        <article class="panel notice">
          <h2>Latest Run</h2>
          {_render_empty_state('warning', 'No Batch Analysis Run has been indexed.', 'Trigger a run above to populate this overview.')}
        </article>
        <article class="panel">
          <h2>Current Config Version</h2>
          {_render_empty_state('settings', 'Settings versioning is initialized for later slices.')}
        </article>
        <article class="panel">
          <h2>Top Quality Drivers</h2>
          {_render_empty_state('spark', 'Artifact indexing and scoring will populate this area.')}
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
      {header}
      <p class="lede" style="margin-top:-12px;">Latest indexed Batch Analysis Run, scrape quality, pipeline health, and marketer review queue.</p>
      {actions}
      <section class="grid" aria-label="Overview status">
        <article class="panel feature">
          <h2>Scrape Quality Score</h2>
          <p class="metric">{html.escape(quality_metric)}</p>
          <p class="muted">{html.escape(quality_band)}</p>
        </article>
        <article class="panel feature {_health_panel_class(health_summary)}">
          <h2>Pipeline Health</h2>
          <p class="metric">{html.escape(health_status)}</p>
          <p class="muted">{html.escape(health_impact)}</p>
        </article>
        <article class="panel">
          <h2>Latest Run</h2>
          <p class="metric">{html.escape(run["run_id"])}</p>
          <p class="muted">{html.escape(run["run_timestamp"] or "Timestamp not recorded")} &middot; {html.escape(run["mode"] or "Run type not recorded")}</p>
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
        <a class="action-link secondary" href="/scrape-settings">Edit scrape settings</a>
        <a class="action-link secondary" href="/run-history">View run history</a>
        <a class="action-link secondary" href="/scraped-content">Browse content library</a>
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
