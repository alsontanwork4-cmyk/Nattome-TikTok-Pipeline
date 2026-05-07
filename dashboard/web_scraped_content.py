from __future__ import annotations

import html
from pathlib import Path

from .refresh import refresh_dashboard_derivatives
from .store import connect_dashboard_store
from .web_components import (
    _curation_labels,
    _display_status,
    _engagement_rate,
    _format_count,
    _freshness_label,
    _hashtag_text,
    _json_loads,
    _metadata_item,
    _render_empty_state,
    _render_page_header,
    _relevance_label,
)
from .web_constants import CURATION_LABELS

def _render_scraped_content(workspace: Path) -> str:
    workspace = Path(workspace)
    refresh_dashboard_derivatives(workspace, intent="scraped_content", scope="artifacts")
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
    connection = connect_dashboard_store(workspace)
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
