from __future__ import annotations

import html
from pathlib import Path
from urllib.parse import urlencode

from .run_history import load_run_history, load_run_history_detail
from .web_components import _format_count, _percent_text, _render_empty_state, _render_page_header, _score_text

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
