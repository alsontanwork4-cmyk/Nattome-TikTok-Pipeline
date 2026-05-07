from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from .run_history import RunHistoryDetail, RunHistoryRow, load_run_history, load_run_history_detail
from .scoring import (
    nattome_relevance,
    percent_text as _plain_percent_text,
    score_text as _plain_score_text,
    weighted_engagement,
)
from .web_components import _format_count, _hashtag_text, _json_loads
from .web_constants import CURATION_LABELS

_TABS: tuple[tuple[str, str], ...] = (
    ("overview", "Overview"),
    ("posts", "Posts"),
    ("authors", "Authors"),
    ("music", "Music"),
    ("video", "Video"),
    ("all-fields", "All Fields"),
)
_DEFAULT_TAB = "overview"


def _render_run_history(
    workspace: Path,
    *,
    run_history_run_id: str = "",
    run_history_tab: str = "",
) -> str:
    history = load_run_history(workspace)
    rows = history.rows
    selected_run_id = _resolve_selected_run_id(rows, run_history_run_id)
    active_tab = run_history_tab if run_history_tab in {tab for tab, _ in _TABS} else _DEFAULT_TAB
    detail_markup = _render_run_detail_section(workspace, selected_run_id, active_tab)
    return f"""
      <h1>Run History</h1>
      <p class="lede">Pick a run to inspect its scraped content. The newest run opens by default; switch runs from the selector below.</p>
      <div class="actions" aria-label="Run history exports">
        <a class="action-link" href="/exports/run-summaries.csv">Export run summaries CSV</a>
        <a class="action-link secondary" href="/exports/raw-videos.csv">Export raw videos CSV</a>
      </div>
      {_render_manual_run_controls()}
      <section class="panel wide-panel" aria-label="Run selector">
        <h2>Runs</h2>
        {_render_run_selector(rows, selected_run_id)}
      </section>
      {detail_markup}
      <section class="panel wide-panel" aria-label="Trend monitoring">
        <h2>Trend Monitoring</h2>
        {_render_trend_points(history.trend_points)}
      </section>
      <section class="panel wide-panel" aria-label="Config overlays">
        <h2>Config Overlays</h2>
        {_render_config_overlays(history.config_overlays)}
      </section>
    """


def _resolve_selected_run_id(rows: list[RunHistoryRow], requested_run_id: str) -> str:
    if not rows:
        return ""
    available = {row.run_id for row in rows}
    if requested_run_id and requested_run_id in available:
        return requested_run_id
    return rows[0].run_id


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


def _render_run_selector(rows: list[RunHistoryRow], selected_run_id: str) -> str:
    if not rows:
        return '<p class="muted">No scheduled or manual runs have been indexed yet.</p>'
    body = "\n".join(_render_run_selector_row(row, selected_run_id) for row in rows)
    return f"""
      <div class="table-scroll">
        <table class="data-table run-selector-table">
          <thead>
            <tr>
              <th>Run</th>
              <th>Timestamp</th>
              <th>Scanned</th>
              <th>Eligible</th>
              <th>Selected</th>
              <th>Score</th>
              <th>Health</th>
              <th>Outputs</th>
            </tr>
          </thead>
          <tbody>{body}</tbody>
        </table>
      </div>
    """


def _render_run_selector_row(row: RunHistoryRow, selected_run_id: str) -> str:
    is_active = row.run_id == selected_run_id
    row_class = ' class="run-selector-active"' if is_active else ""
    label = str(row.run_type).title()
    return f"""
      <tr{row_class}>
        <td><a href="/run-history?run_id={html.escape(row.run_id)}">{html.escape(label)}</a><br><code>{html.escape(row.run_id)}</code><br><span class="muted">Source: {html.escape(row.source_type)}. By {html.escape(row.triggered_by)}.</span></td>
        <td>{html.escape(row.timestamp)}</td>
        <td>{row.raw_candidates}</td>
        <td>{row.eligible_candidates}</td>
        <td>{row.selected_count}</td>
        <td>{_score_text(row.scrape_quality_score)}</td>
        <td>{html.escape(row.pipeline_health)}</td>
        <td>{_render_output_links(row.output_links)}</td>
      </tr>
    """


def _render_run_detail_section(workspace: Path, selected_run_id: str, active_tab: str) -> str:
    if not selected_run_id:
        return ""
    try:
        detail = load_run_history_detail(workspace, selected_run_id)
    except ValueError:
        return """
      <section class="panel wide-panel notice">
        <h2>Run detail unavailable</h2>
        <p class="muted">The selected run was not found in the indexed history.</p>
      </section>
        """
    return _render_run_workbench(detail, active_tab)


def _render_run_workbench(detail: RunHistoryDetail, active_tab: str) -> str:
    row = detail.row
    header = f"""
      <header class="run-workbench-header">
        <div>
          <p class="muted run-workbench-eyebrow">Currently inspecting</p>
          <h2>{html.escape(str(row.run_type).title())}</h2>
          <p class="muted">{html.escape(row.timestamp)} &middot; <code>{html.escape(row.run_id)}</code></p>
        </div>
        <dl class="run-summary-stats">
          <div><dt>Scanned</dt><dd>{row.raw_candidates}</dd></div>
          <div><dt>Eligible</dt><dd>{row.eligible_candidates}</dd></div>
          <div><dt>Selected</dt><dd>{row.selected_count}</dd></div>
          <div><dt>Score</dt><dd>{_score_text(row.scrape_quality_score)}</dd></div>
          <div><dt>Health</dt><dd>{html.escape(row.pipeline_health)}</dd></div>
        </dl>
      </header>
    """
    return f"""
      <section class="panel wide-panel run-workbench" aria-label="Run drilldown">
        {header}
        {_render_tab_nav(row.run_id, active_tab)}
        <div class="run-tab-panel">
          {_render_active_tab(detail, active_tab)}
        </div>
      </section>
    """


def _render_tab_nav(run_id: str, active_tab: str) -> str:
    items: list[str] = []
    for slug, label in _TABS:
        is_active = slug == active_tab
        active_attr = ' aria-current="page"' if is_active else ""
        href = f"/run-history?run_id={html.escape(run_id)}&tab={html.escape(slug)}"
        items.append(f'<a class="run-tab-link" href="{href}"{active_attr}>{html.escape(label)}</a>')
    return f'<nav class="run-tab-nav" aria-label="Run inspection tabs">{"".join(items)}</nav>'


def _render_active_tab(detail: RunHistoryDetail, active_tab: str) -> str:
    if active_tab == "posts":
        return _render_posts_tab(detail)
    if active_tab == "authors":
        return _render_authors_tab(detail)
    if active_tab == "music":
        return _render_music_tab(detail)
    if active_tab == "video":
        return _render_video_tab(detail)
    if active_tab == "all-fields":
        return _render_all_fields_tab(detail)
    return _render_overview_tab(detail)


def _render_overview_tab(detail: RunHistoryDetail) -> str:
    row = detail.row
    excluded_count = max(row.raw_candidates - row.selected_count, 0)
    config_items = _render_selection_config(detail.selection_config)
    issues = _render_top_issues(detail)
    return f"""
      <div class="grid run-overview-grid">
        <article>
          <h3>Run Summary</h3>
          <ul class="compact-list">
            <li><strong>Config Version:</strong> {html.escape(row.config_version)}</li>
            <li><strong>Average Relevance:</strong> {_percent_text(row.average_nattome_relevance)}</li>
            <li><strong>Average Engagement:</strong> {_percent_text(row.average_engagement)}</li>
            <li><strong>Freshness Score:</strong> {_score_text(row.freshness_score)}</li>
            <li><strong>Duplicate / Noise Score:</strong> {_score_text(row.duplicate_noise_score)}</li>
          </ul>
        </article>
        <article>
          <h3>Selection Filter</h3>
          {config_items}
          <p class="muted run-selection-counts">
            Selected {row.selected_count} of {row.raw_candidates} scanned ({excluded_count} excluded).
          </p>
        </article>
        <article>
          <h3>Top Issues</h3>
          {issues}
        </article>
      </div>
      <h3>Logs and Linked Outputs</h3>
      {_render_output_links(detail.output_links)}
    """


def _render_selection_config(config: dict[str, Any]) -> str:
    if not config:
        return '<p class="muted">No selection filter recorded for this run.</p>'
    items: list[str] = []
    for key, value in config.items():
        items.append(
            f"<li><strong>{html.escape(_humanize_key(key))}:</strong> {html.escape(str(value))}</li>"
        )
    return f'<ul class="compact-list">{"".join(items)}</ul>'


def _render_top_issues(detail: RunHistoryDetail) -> str:
    issues: list[str] = []
    if detail.row.top_issue and detail.row.top_issue != "No blocking issue":
        issues.append(html.escape(detail.row.top_issue))
    for driver in detail.quality_drivers[:3]:
        if isinstance(driver, dict) and driver.get("direction") == "hurt":
            message = str(driver.get("message") or driver.get("component") or "")
            if message:
                issues.append(html.escape(message))
    if not issues:
        return '<p class="muted">No blocking issues recorded.</p>'
    rendered = "".join(f"<li>{issue}</li>" for issue in issues)
    return f'<ul class="compact-list">{rendered}</ul>'


def _render_posts_tab(detail: RunHistoryDetail) -> str:
    videos = _ranked_videos(detail)
    if not videos:
        return '<p class="muted">No raw scraped videos are linked to this run.</p>'
    rows_markup = "\n".join(_render_post_row(index + 1, video, detail) for index, video in enumerate(videos))
    return f"""
      <div class="table-scroll">
        <table class="data-table posts-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Status</th>
              <th>Author</th>
              <th>Caption / Hook</th>
              <th>Views</th>
              <th>Likes</th>
              <th>Comments</th>
              <th>Shares</th>
              <th>Weighted Engagement</th>
              <th>Nattome Relevance</th>
              <th>Selection Score</th>
              <th>Created</th>
              <th>Music</th>
              <th>Downloadable</th>
              <th>Risk Flags</th>
              <th>Open</th>
            </tr>
          </thead>
          <tbody>{rows_markup}</tbody>
        </table>
      </div>
      {_render_curation_drawer(videos, detail.row.run_id)}
    """


def _ranked_videos(detail: RunHistoryDetail) -> list[dict[str, Any]]:
    videos = list(detail.videos)

    def _sort_key(video: dict[str, Any]) -> tuple[int, float, int]:
        is_selected = 0 if video["video_id"] in detail.selected_video_ids else 1
        return (is_selected, -weighted_engagement(video), -int(video.get("play_count") or 0))

    videos.sort(key=_sort_key)
    return videos


def _render_post_row(rank: int, video: dict[str, Any], detail: RunHistoryDetail) -> str:
    music = _music_payload(video)
    music_text = music.get("title") or "Original sound"
    if music.get("author"):
        music_text += f" - {music['author']}"
    risk_flags = _risk_flags(video, detail)
    is_selected = video["video_id"] in detail.selected_video_ids
    status_label = "Selected" if is_selected else _display_status_label(str(video.get("selection_status") or "raw"))
    status_class = "ok" if is_selected else _status_pill_class(str(video.get("selection_status") or "raw"))
    tiktok_url = str(video.get("tiktok_url") or "")
    open_link = (
        f'<a href="{html.escape(tiktok_url)}" target="_blank" rel="noopener">Open TikTok</a>'
        if tiktok_url
        else '<span class="muted">--</span>'
    )
    selection_score = _selection_score(video, detail)
    return f"""
      <tr>
        <td>{rank}</td>
        <td><span class="status-pill {status_class}">{html.escape(status_label)}</span></td>
        <td>{html.escape(str(video.get("author_handle") or "Unknown"))}</td>
        <td><div class="post-hook">{html.escape(_truncate(str(video.get("caption") or "Untitled TikTok"), 140))}</div><span class="muted hashtag-line">{html.escape(_hashtag_text(video.get("hashtags_json")))}</span></td>
        <td>{_format_count(video.get("play_count"))}</td>
        <td>{_format_count(video.get("like_count"))}</td>
        <td>{_format_count(video.get("comment_count"))}</td>
        <td>{_format_count(video.get("share_count"))}</td>
        <td>{_percent_text(weighted_engagement(video))}</td>
        <td>{_percent_text(nattome_relevance(video))}</td>
        <td>{_score_text(selection_score)}</td>
        <td>{html.escape(str(video.get("created_at") or "--"))}</td>
        <td>{html.escape(_truncate(music_text, 36))}</td>
        <td>{"Yes" if int(video.get("is_downloadable") or 0) else "No"}</td>
        <td>{_render_risk_flags(risk_flags)}</td>
        <td>{open_link}</td>
      </tr>
    """


def _render_authors_tab(detail: RunHistoryDetail) -> str:
    if not detail.videos:
        return '<p class="muted">No authors are linked to this run.</p>'
    grouped: dict[str, dict[str, Any]] = {}
    for video in detail.videos:
        author = str(video.get("author_handle") or "Unknown")
        bucket = grouped.setdefault(
            author,
            {"posts": 0, "selected": 0, "views": 0, "likes": 0, "engagements": []},
        )
        bucket["posts"] += 1
        if video["video_id"] in detail.selected_video_ids:
            bucket["selected"] += 1
        bucket["views"] += int(video.get("play_count") or 0)
        bucket["likes"] += int(video.get("like_count") or 0)
        bucket["engagements"].append(weighted_engagement(video))
    rows: list[str] = []
    for author, bucket in sorted(grouped.items(), key=lambda item: item[1]["views"], reverse=True):
        engagements = bucket["engagements"] or [0.0]
        average_engagement = sum(engagements) / len(engagements)
        rows.append(
            f"""
            <tr>
              <td>{html.escape(author)}</td>
              <td>{bucket['posts']}</td>
              <td>{bucket['selected']}</td>
              <td>{_format_count(bucket['views'])}</td>
              <td>{_format_count(bucket['likes'])}</td>
              <td>{_percent_text(average_engagement)}</td>
            </tr>
            """
        )
    return f"""
      <div class="table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th>Author</th>
              <th>Posts</th>
              <th>Selected</th>
              <th>Views</th>
              <th>Likes</th>
              <th>Avg Engagement</th>
            </tr>
          </thead>
          <tbody>{"".join(rows)}</tbody>
        </table>
      </div>
    """


def _render_music_tab(detail: RunHistoryDetail) -> str:
    if not detail.videos:
        return '<p class="muted">No music signals are linked to this run.</p>'
    grouped: dict[str, dict[str, Any]] = {}
    for video in detail.videos:
        music = _music_payload(video)
        title = str(music.get("title") or "Original sound")
        bucket = grouped.setdefault(
            title,
            {"author": str(music.get("author") or ""), "original": bool(music.get("original")), "posts": 0, "views": 0},
        )
        bucket["posts"] += 1
        bucket["views"] += int(video.get("play_count") or 0)
        if music.get("author") and not bucket["author"]:
            bucket["author"] = str(music["author"])
        if music.get("original"):
            bucket["original"] = True
    rows: list[str] = []
    for title, bucket in sorted(grouped.items(), key=lambda item: item[1]["posts"], reverse=True):
        rows.append(
            f"""
            <tr>
              <td>{html.escape(title)}</td>
              <td>{html.escape(bucket['author'] or '--')}</td>
              <td>{'Yes' if bucket['original'] else 'No'}</td>
              <td>{bucket['posts']}</td>
              <td>{_format_count(bucket['views'])}</td>
            </tr>
            """
        )
    return f"""
      <div class="table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th>Music</th>
              <th>Music Author</th>
              <th>Original</th>
              <th>Posts</th>
              <th>Views</th>
            </tr>
          </thead>
          <tbody>{"".join(rows)}</tbody>
        </table>
      </div>
    """


def _render_video_tab(detail: RunHistoryDetail) -> str:
    if not detail.videos:
        return '<p class="muted">No video records are linked to this run.</p>'
    rows: list[str] = []
    for video in _ranked_videos(detail):
        raw = _raw_payload(video)
        duration = raw.get("duration_s") or raw.get("duration_seconds") or "--"
        download_url = str(raw.get("video_download_url") or "")
        download_link = (
            f'<a href="{html.escape(download_url)}" target="_blank" rel="noopener">Download</a>'
            if download_url
            else '<span class="muted">--</span>'
        )
        evidence_state = "Selected" if video["video_id"] in detail.selected_video_ids else _display_status_label(
            str(video.get("selection_status") or "raw")
        )
        rows.append(
            f"""
            <tr>
              <td>{html.escape(str(video.get("video_id")))}</td>
              <td>{html.escape(str(duration))}</td>
              <td>{'Yes' if int(video.get("is_downloadable") or 0) else 'No'}</td>
              <td>{download_link}</td>
              <td>{html.escape(str(video.get("tiktok_url") or "--"))}</td>
              <td>{html.escape(evidence_state)}</td>
            </tr>
            """
        )
    return f"""
      <div class="table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th>Video ID</th>
              <th>Duration (s)</th>
              <th>Downloadable</th>
              <th>Download URL</th>
              <th>TikTok URL</th>
              <th>Evidence Status</th>
            </tr>
          </thead>
          <tbody>{"".join(rows)}</tbody>
        </table>
      </div>
    """


def _render_all_fields_tab(detail: RunHistoryDetail) -> str:
    if not detail.videos:
        return '<p class="muted">No raw fields are available for this run.</p>'
    items: list[str] = []
    for video in detail.videos:
        raw_payload = _raw_payload(video)
        merged = {**video, **raw_payload}
        merged.pop("raw_json", None)
        rows = "".join(
            f"<tr><th scope=\"row\">{html.escape(_humanize_key(key))}</th><td>{html.escape(_format_field(value))}</td></tr>"
            for key, value in sorted(merged.items())
            if value not in (None, "", [], {})
        )
        items.append(
            f"""
            <details class="all-fields-row">
              <summary><strong>{html.escape(str(video.get("video_id")))}</strong> &middot; {html.escape(_truncate(str(video.get("caption") or ""), 80))}</summary>
              <div class="table-scroll"><table class="data-table all-fields-table"><tbody>{rows}</tbody></table></div>
            </details>
            """
        )
    return f'<div class="all-fields-stack">{"".join(items)}</div>'


def _render_curation_drawer(videos: list[dict[str, Any]], run_id: str) -> str:
    if not videos:
        return ""
    cards: list[str] = []
    for video in videos[:30]:
        cards.append(_render_curation_card(video, run_id))
    return f"""
      <details class="curation-drawer">
        <summary>Curate posts for this run</summary>
        <div class="curation-drawer-list">{"".join(cards)}</div>
      </details>
    """


def _render_curation_card(video: dict[str, Any], run_id: str) -> str:
    video_id = str(video.get("video_id") or "")
    selected_labels = _curation_labels(video.get("curation_labels"))
    note = str(video.get("curation_note") or "")
    exclude_similar_reason = str(video.get("exclude_similar_reason") or "")
    checkboxes: list[str] = []
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
    caption = _truncate(str(video.get("caption") or "Untitled TikTok"), 80)
    return f"""
      <article class="curation-card">
        <header><strong>{html.escape(caption)}</strong> <span class="muted">{html.escape(video_id)}</span></header>
        <form class="curation-form" method="post" action="/run-history/curation">
          <input type="hidden" name="video_id" value="{html.escape(video_id)}">
          <input type="hidden" name="run_id" value="{html.escape(run_id)}">
          <input type="hidden" name="redirect_tab" value="posts">
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
      </article>
    """


def _render_trend_points(points: list[object]) -> str:
    if not points:
        return '<p class="muted">Trend charts will appear after scheduled runs are indexed.</p>'
    items: list[str] = []
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


def _render_output_links(links: list[object]) -> str:
    if not links:
        return '<span class="muted">No output links</span>'
    items: list[str] = []
    for link in links:
        path = getattr(link, "path")
        label = getattr(link, "label")
        artifact_type = getattr(link, "artifact_type")
        items.append(
            f'<li><a href="{html.escape(path)}">{html.escape(label)}</a> <span class="muted">({html.escape(artifact_type)})</span></li>'
        )
    return f'<ul class="compact-list output-links">{"".join(items)}</ul>'


def _render_risk_flags(flags: list[str]) -> str:
    if not flags:
        return '<span class="muted">--</span>'
    return "".join(f'<span class="status-pill warn">{html.escape(flag)}</span>' for flag in flags)


def _risk_flags(video: dict[str, Any], detail: RunHistoryDetail) -> list[str]:
    flags: list[str] = []
    if not int(video.get("is_downloadable") or 0):
        flags.append("Not downloadable")
    if nattome_relevance(video) <= 0:
        flags.append("Off-topic")
    if int(video.get("play_count") or 0) < int(detail.selection_config.get("minimum_views") or 0):
        flags.append("Below view floor")
    labels = _curation_labels(video.get("curation_labels"))
    if "Exclude Similar" in labels:
        flags.append("Excluded by marketer")
    return flags


def _selection_score(video: dict[str, Any], detail: RunHistoryDetail) -> int:
    base = (nattome_relevance(video) * 0.6 + min(weighted_engagement(video) / 0.1, 1.0) * 0.4) * 100
    if video["video_id"] in detail.selected_video_ids:
        base = max(base, 70.0)
    return int(round(base))


def _music_payload(video: dict[str, Any]) -> dict[str, Any]:
    raw = _raw_payload(video)
    music = raw.get("music") if isinstance(raw, dict) else None
    if isinstance(music, dict):
        return music
    return {}


def _raw_payload(video: dict[str, Any]) -> dict[str, Any]:
    raw = _json_loads(video.get("raw_json"))
    return raw if isinstance(raw, dict) else {}


def _curation_labels(raw_value: object) -> list[str]:
    labels = _json_loads(raw_value)
    if not isinstance(labels, list):
        return []
    return [str(label) for label in labels if str(label) in CURATION_LABELS]


def _display_status_label(status: str) -> str:
    if status == "raw":
        return "Raw only"
    return status.title()


def _status_pill_class(status: str) -> str:
    if status in {"selected", "analyzed"}:
        return "ok"
    if status == "eligible":
        return "accent"
    return ""


def _humanize_key(key: str) -> str:
    return key.replace("_", " ").replace("-", " ").title()


def _truncate(text: str, length: int) -> str:
    if len(text) <= length:
        return text
    return text[: length - 1].rstrip() + "..."


def _format_field(value: object) -> str:
    if isinstance(value, (dict, list)):
        try:
            return json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(value)
    return str(value)


def _score_text(value: object) -> str:
    return html.escape(_plain_score_text(value))


def _percent_text(value: object) -> str:
    return _plain_percent_text(value)
