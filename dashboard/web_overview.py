from __future__ import annotations

import html
from collections import Counter
from pathlib import Path
from typing import Any

from .refresh import refresh_dashboard_derivatives
from .settings import get_active_settings_version
from .store import DASHBOARD_DB_PATH, connect_dashboard_store
from .time_display import display_datetime
from .web_components import (
    _format_count,
    _json_loads,
    _render_empty_state,
    _render_page_header,
)


def _render_overview(workspace: Path, *, run_id: str = "") -> str:
    workspace = Path(workspace)
    refresh_dashboard_derivatives(workspace, intent="overview", scope="all")
    run_options = _load_run_options(workspace)
    selected_run_id = _resolve_run_id(run_options, run_id)
    overview = _load_overview_for_run(workspace, selected_run_id)
    settings = _active_settings(workspace)
    header = _render_page_header(
        "Latest Run Overview",
        "Local dashboard shell for monitoring TikTok discovery runs.",
        active_path="/",
    )
    if overview is None:
        return _render_empty_overview(workspace, header, settings)

    snapshot = _Snapshot.from_overview(overview, settings)
    selector = _render_run_switcher(run_options, selected_run_id)
    return f"""
      {header}
      <p class="lede" style="margin-top:-12px;">Marketer view: what we searched for, what came back, and how many posts moved through selection.</p>
      {selector}
      {_render_hero_strip(snapshot)}
      <section class="panel wide-panel" aria-label="What did we search for">
        <h2>1. What did we search for?</h2>
        {_render_search_inputs(snapshot)}
      </section>
      <section class="panel wide-panel" aria-label="What did we actually get">
        <h2>2. What did we actually get?</h2>
        {_render_results_overview(snapshot)}
      </section>
      <section class="panel wide-panel" aria-label="Selection funnel">
        <h2>3. Selection funnel</h2>
        {_render_selection_funnel(snapshot)}
      </section>
    """


# ---------- Snapshot ----------

class _Snapshot:
    def __init__(
        self,
        *,
        run: dict[str, Any],
        config: dict[str, Any],
        phase_issues: list[str],
        videos: list[dict[str, Any]],
        selected_ids: set[str],
        settings: dict[str, Any],
    ) -> None:
        self.run = run
        self.config = config
        self.phase_issues = phase_issues
        self.videos = videos
        self.selected_ids = selected_ids
        self.settings = settings

    @classmethod
    def from_overview(cls, overview: dict[str, Any], settings: dict[str, Any]) -> "_Snapshot":
        return cls(
            run=overview["run"],
            config=overview["config"],
            phase_issues=overview["phase_issues"],
            videos=overview["videos"],
            selected_ids=overview["selected_ids"],
            settings=settings,
        )

    @property
    def search_inputs(self) -> dict[str, list[str]]:
        manifest_config = self.config.get("scraper") if isinstance(self.config.get("scraper"), dict) else {}
        return {
            "hashtags": _string_list(manifest_config.get("hashtags") or self.settings.get("hashtags")),
            "keywords": _string_list(manifest_config.get("keywords") or self.settings.get("keywords")),
            "profiles": _string_list(
                manifest_config.get("competitor_profiles") or self.settings.get("competitor_profiles")
            ),
        }


def _load_run_options(workspace: Path) -> list[dict[str, str]]:
    connection = connect_dashboard_store(workspace)
    try:
        rows = connection.execute(
            """
            SELECT run_id, run_timestamp, mode
            FROM batch_runs
            ORDER BY COALESCE(run_timestamp, '') DESC, run_id DESC
            """
        ).fetchall()
        return [
            {
                "run_id": str(row["run_id"]),
                "run_timestamp": str(row["run_timestamp"] or ""),
                "mode": str(row["mode"] or ""),
            }
            for row in rows
        ]
    finally:
        connection.close()


def _resolve_run_id(run_options: list[dict[str, str]], requested: str) -> str:
    if not run_options:
        return ""
    available = {option["run_id"] for option in run_options}
    if requested and requested in available:
        return requested
    return run_options[0]["run_id"]


def _load_overview_for_run(workspace: Path, run_id: str) -> dict[str, object] | None:
    if not run_id:
        return _load_latest_overview(workspace)
    connection = connect_dashboard_store(workspace)
    try:
        run = connection.execute(
            "SELECT * FROM batch_runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        if run is None:
            return _load_latest_overview(workspace)
        return _build_overview(connection, run)
    finally:
        connection.close()


def _load_latest_overview(workspace: Path) -> dict[str, object] | None:
    connection = connect_dashboard_store(workspace)
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
        return _build_overview(connection, run)
    finally:
        connection.close()


def _build_overview(connection, run) -> dict[str, object]:
    run_id = run["run_id"]
    selected = connection.execute(
        "SELECT * FROM selected_batches WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    videos = _all_run_videos(connection, run_id, selected)
    manifest = _json_loads(run["raw_json"])
    return {
        "run": dict(run),
        "videos": [dict(video) for video in videos],
        "selected_ids": _selected_ids(selected),
        "config": _run_configuration(manifest, selected),
        "phase_issues": _phase_issues(manifest),
    }


def _all_run_videos(connection, run_id: str, selected) -> list:
    if selected and selected["candidate_source"]:
        rows = list(
            connection.execute(
                """
                SELECT *
                FROM raw_videos
                WHERE source_artifact_path = ?
                ORDER BY play_count DESC, like_count DESC, video_id
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
            """,
            (run_id,),
        )
    )


def _selected_ids(selected) -> set[str]:
    if selected is None:
        return set()
    payload = _json_loads(selected["raw_json"])
    if not isinstance(payload, dict):
        return set()
    candidates = payload.get("selected_candidates")
    if not isinstance(candidates, list):
        return set()
    return {
        str(item.get("id") or item.get("video_id") or "")
        for item in candidates
        if isinstance(item, dict)
    } - {""}


def _run_configuration(manifest: dict[str, object], selected) -> dict[str, object]:
    configuration = manifest.get("configuration")
    if not isinstance(configuration, dict):
        configuration = {}
    selected_value = _json_loads(selected["raw_json"]) if selected else {}
    selected_json = selected_value if isinstance(selected_value, dict) else {}
    scraper = configuration.get("scraper") if isinstance(configuration.get("scraper"), dict) else {}
    return {
        "version": configuration.get("version")
        or configuration.get("config_version")
        or selected_json.get("config_version")
        or selected_json.get("settings_version"),
        "next_scheduled_run": configuration.get("next_scheduled_run")
        or configuration.get("next_run")
        or selected_json.get("next_scheduled_run"),
        "scraper": scraper,
        "selection": configuration.get("selection") if isinstance(configuration.get("selection"), dict) else {},
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


def _active_settings(workspace: Path) -> dict[str, Any]:
    try:
        version = get_active_settings_version(workspace)
        return dict(version.new_settings)
    except Exception:
        return {}


# ---------- Run switcher ----------

def _render_run_switcher(run_options: list[dict[str, str]], selected_run_id: str) -> str:
    if len(run_options) <= 1:
        return ""
    selected_index = next(
        (i for i, option in enumerate(run_options) if option["run_id"] == selected_run_id),
        0,
    )
    newer = run_options[selected_index - 1] if selected_index > 0 else None
    older = run_options[selected_index + 1] if selected_index + 1 < len(run_options) else None
    newest = run_options[0]
    is_latest = selected_index == 0
    nav_buttons = []
    if newer is not None:
        nav_buttons.append(
            f'<a class="run-switch-btn" href="/?run_id={html.escape(newer["run_id"])}">&larr; Newer</a>'
        )
    else:
        nav_buttons.append('<span class="run-switch-btn disabled">&larr; Newer</span>')
    if older is not None:
        nav_buttons.append(
            f'<a class="run-switch-btn" href="/?run_id={html.escape(older["run_id"])}">Older &rarr;</a>'
        )
    else:
        nav_buttons.append('<span class="run-switch-btn disabled">Older &rarr;</span>')
    if not is_latest:
        nav_buttons.append(
            f'<a class="run-switch-btn primary" href="/?run_id={html.escape(newest["run_id"])}">Jump to latest</a>'
        )
    history_items = "".join(
        _render_run_switch_option(option, option["run_id"] == selected_run_id)
        for option in run_options
    )
    return f"""
      <section class="panel wide-panel run-switcher" aria-label="Run switcher">
        <div class="run-switcher-controls">
          <div>
            <p class="run-switcher-eyebrow muted">Inspecting</p>
            <p class="run-switcher-current"><code>{html.escape(selected_run_id)}</code></p>
          </div>
          <div class="run-switch-actions">{"".join(nav_buttons)}</div>
        </div>
        <details class="run-switcher-history">
          <summary>All indexed runs ({len(run_options)})</summary>
          <ul class="run-switcher-list">{history_items}</ul>
        </details>
      </section>
    """


def _render_run_switch_option(option: dict[str, str], is_selected: bool) -> str:
    classes = "run-switcher-item"
    if is_selected:
        classes += " active"
    timestamp = display_datetime(option["run_timestamp"], fallback="Timestamp not recorded")
    mode = option["mode"] or "run"
    return f"""
      <li class="{classes}">
        <a href="/?run_id={html.escape(option['run_id'])}">
          <code>{html.escape(option['run_id'])}</code>
          <span class="muted">{html.escape(timestamp)} &middot; {html.escape(mode)}</span>
        </a>
      </li>
    """


# ---------- Hero strip ----------

def _render_hero_strip(snapshot: _Snapshot) -> str:
    run = snapshot.run
    config = snapshot.config
    config_version = config.get("version") or "Not recorded"
    next_scheduled_run = display_datetime(config.get("next_scheduled_run"), fallback="Not scheduled")
    run_timestamp = display_datetime(run["run_timestamp"], fallback="Timestamp not recorded")
    inputs_count = sum(len(items) for items in snapshot.search_inputs.values())
    return f"""
      <section class="grid overview-hero" aria-label="Run snapshot">
        {_render_run_issues_card(snapshot.phase_issues)}
        <article class="panel feature">
          <h2>Latest Run</h2>
          <p class="run-id-metric"><code>{html.escape(str(run["run_id"]))}</code></p>
          <p class="muted">{html.escape(run_timestamp)} &middot; {html.escape(str(run["mode"] or "Run type not recorded"))}</p>
          <p class="muted">Config {html.escape(str(config_version))} &middot; next run {html.escape(str(next_scheduled_run))}</p>
        </article>
        <article class="panel feature">
          <h2>Source Inputs</h2>
          <p class="metric">{inputs_count}</p>
          <p class="muted">hashtags, keywords, and competitor profiles active for this run.</p>
        </article>
      </section>
    """


def _render_run_issues_card(phase_issues: list[str]) -> str:
    issue_count = len(phase_issues)
    status = "No run issues" if issue_count == 0 else f"{issue_count} issue(s)"
    detail = "No failed, error, or blocked phases recorded." if issue_count == 0 else phase_issues[0]
    return f"""
        <article class="panel feature">
          <h2>Run Issues</h2>
          <p class="metric">{html.escape(status)}</p>
          <p class="muted">{html.escape(detail)}</p>
        </article>
    """


# ---------- Section 1: search inputs ----------

def _render_search_inputs(snapshot: _Snapshot) -> str:
    inputs = snapshot.search_inputs
    return f"""
      <div class="overview-grid-3">
        <article>
          <h3>Hashtags</h3>
          {_render_chip_list(_format_hashtags(inputs["hashtags"]))}
        </article>
        <article>
          <h3>Keywords</h3>
          {_render_chip_list(inputs["keywords"])}
        </article>
        <article>
          <h3>Competitor Profiles</h3>
          {_render_chip_list(_format_profiles(inputs["profiles"]))}
        </article>
      </div>
    """


def _render_chip_list(items: list[str]) -> str:
    if not items:
        return '<p class="muted">None recorded.</p>'
    chips = "".join(f'<span class="chip">{html.escape(item)}</span>' for item in items)
    return f'<div class="chip-row">{chips}</div>'


# ---------- Section 2: what we got ----------

def _render_results_overview(snapshot: _Snapshot) -> str:
    videos = snapshot.videos
    if not videos:
        return _render_empty_state(
            "empty",
            "No raw videos returned for this run.",
            "Once a scrape lands you'll see top hashtags, creators, and content formats here.",
        )
    top_hashtags = _hashtag_counts(videos).most_common(8)
    top_creators = _top_creators(videos)
    formats = _format_breakdown(videos)
    return f"""
      <div class="overview-grid-3">
        <article>
          <h3>Top result hashtags</h3>
          {_render_count_list(top_hashtags, prefix="#")}
        </article>
        <article>
          <h3>Top creators</h3>
          {_render_creator_list(top_creators)}
        </article>
        <article>
          <h3>Content format mix</h3>
          {_render_format_breakdown(formats, len(videos))}
        </article>
      </div>
      <h3>Sample posts</h3>
      {_render_sample_posts(videos[:5])}
    """


def _hashtag_counts(videos: list[dict[str, Any]]) -> Counter:
    counter: Counter = Counter()
    for video in videos:
        for tag in _video_hashtags(video):
            counter[tag] += 1
    return counter


def _video_hashtags(video: dict[str, Any]) -> list[str]:
    raw = _json_loads(video.get("hashtags_json"))
    if not isinstance(raw, list):
        return []
    cleaned: list[str] = []
    for tag in raw:
        token = str(tag).strip().lstrip("#").lower()
        if token:
            cleaned.append(token)
    return cleaned


def _top_creators(videos: list[dict[str, Any]]) -> list[tuple[str, int, int]]:
    grouped: dict[str, dict[str, int]] = {}
    for video in videos:
        author = str(video.get("author_handle") or "Unknown").lstrip("@")
        bucket = grouped.setdefault(author, {"posts": 0, "views": 0})
        bucket["posts"] += 1
        bucket["views"] += int(video.get("play_count") or 0)
    rows = sorted(
        ((author, data["posts"], data["views"]) for author, data in grouped.items()),
        key=lambda row: (-row[2], -row[1]),
    )
    return rows[:5]


def _format_breakdown(videos: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "downloadable": sum(1 for v in videos if int(v.get("is_downloadable") or 0)),
        "with_source": sum(1 for v in videos if str(v.get("source_input") or "").strip()),
        "hashtag_seeded": sum(1 for v in videos if str(v.get("source_input") or "").strip().startswith("#")),
        "keyword_seeded": sum(
            1 for v in videos
            if (s := str(v.get("source_input") or "").strip()) and not s.startswith("#") and not s.startswith("@")
        ),
        "profile_seeded": sum(1 for v in videos if str(v.get("source_input") or "").strip().startswith("@")),
    }


def _render_count_list(items: list[tuple[str, int]], *, prefix: str = "") -> str:
    if not items:
        return '<p class="muted">No data.</p>'
    rendered = "".join(
        f'<li><span class="chip">{html.escape(prefix + label)}</span> <span class="muted">x{count}</span></li>'
        for label, count in items
    )
    return f'<ul class="overview-stat-list">{rendered}</ul>'


def _render_creator_list(creators: list[tuple[str, int, int]]) -> str:
    if not creators:
        return '<p class="muted">No creators in this run.</p>'
    rendered = "".join(
        f'<li><strong>@{html.escape(author)}</strong> &mdash; {posts} post(s), {_format_count(views)} views</li>'
        for author, posts, views in creators
    )
    return f'<ul class="overview-stat-list">{rendered}</ul>'


def _render_format_breakdown(formats: dict[str, int], total: int) -> str:
    if total <= 0:
        return '<p class="muted">No data.</p>'
    items = [
        ("Downloadable", formats["downloadable"]),
        ("Hashtag-seeded", formats["hashtag_seeded"]),
        ("Keyword-seeded", formats["keyword_seeded"]),
        ("Profile-seeded", formats["profile_seeded"]),
    ]
    rendered = "".join(
        f"<li><strong>{html.escape(label)}:</strong> {count} of {total} ({_percent(count, total)})</li>"
        for label, count in items
    )
    return f'<ul class="overview-stat-list">{rendered}</ul>'


def _render_sample_posts(videos: list[dict[str, Any]]) -> str:
    if not videos:
        return '<p class="muted">No sample posts.</p>'
    rows: list[str] = []
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
        rows.append(
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
    return f'<ul class="video-list">{"".join(rows)}</ul>'


# ---------- Section 3: selection funnel ----------

def _render_selection_funnel(snapshot: _Snapshot) -> str:
    funnel = _funnel(snapshot)
    return f"""
      <article>
        {_render_funnel(funnel)}
      </article>
    """


def _funnel(snapshot: _Snapshot) -> dict[str, int]:
    videos = snapshot.videos
    eligible = sum(
        1 for v in videos
        if str(v.get("selection_status") or "raw") in {"eligible", "selected", "analyzed"}
    )
    return {
        "scanned": len(videos),
        "eligible": eligible,
        "selected": len(snapshot.selected_ids),
    }


def _render_funnel(funnel: dict[str, int]) -> str:
    return f"""
      <ul class="overview-funnel">
        <li><span class="overview-funnel-label">Scanned</span><span class="overview-funnel-value">{funnel['scanned']}</span></li>
        <li><span class="overview-funnel-label">Eligible</span><span class="overview-funnel-value">{funnel['eligible']}</span></li>
        <li><span class="overview-funnel-label">Selected</span><span class="overview-funnel-value">{funnel['selected']}</span></li>
      </ul>
    """


# ---------- Empty state ----------

def _render_empty_overview(workspace: Path, header: str, settings: dict[str, Any]) -> str:
    db_path = html.escape(str(workspace / DASHBOARD_DB_PATH))
    inputs = {
        "hashtags": _string_list(settings.get("hashtags")),
        "keywords": _string_list(settings.get("keywords")),
        "profiles": _string_list(settings.get("competitor_profiles")),
    }
    return f"""
      {header}
      <p class="lede" style="margin-top:-12px;">No indexed runs yet. The dashboard is ready once a Batch Analysis Run is available.</p>
      <section class="grid overview-hero" aria-label="Run snapshot">
        <article class="panel feature">
          <h2>Indexed Runs</h2>
          <p class="metric muted">0</p>
          <p class="muted">No Batch Analysis Run has been indexed.</p>
        </article>
        <article class="panel feature">
          <h2>Dashboard Store</h2>
          <p class="metric">SQLite</p>
          <p class="muted"><code>{db_path}</code></p>
        </article>
      </section>
      <section class="panel wide-panel" aria-label="What did we search for">
        <h2>1. What did we search for?</h2>
        <p class="muted">Pulled from your active scrape settings until the first run lands.</p>
        <div class="overview-grid-3">
          <article>
            <h3>Hashtags</h3>
            {_render_chip_list(_format_hashtags(inputs["hashtags"]))}
          </article>
          <article>
            <h3>Keywords</h3>
            {_render_chip_list(inputs["keywords"])}
          </article>
          <article>
            <h3>Competitor Profiles</h3>
            {_render_chip_list(_format_profiles(inputs["profiles"]))}
          </article>
        </div>
      </section>
      <section class="panel notice">
        <h2>Latest Run</h2>
        {_render_empty_state('warning', 'No Batch Analysis Run has been indexed.', 'Trigger a run above to populate this overview.')}
      </section>
    """


# ---------- helpers ----------

def _string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _format_hashtags(items: list[str]) -> list[str]:
    return [f"#{item.lstrip('#')}" for item in items]


def _format_profiles(items: list[str]) -> list[str]:
    return [f"@{item.lstrip('@')}" for item in items]


def _percent(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "0%"
    return f"{(numerator / denominator) * 100:.0f}%"
