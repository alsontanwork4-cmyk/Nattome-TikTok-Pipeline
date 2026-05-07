from __future__ import annotations

import html
from collections import Counter
from pathlib import Path
from typing import Any

from .refresh import refresh_dashboard_derivatives
from .scoring import nattome_relevance, relevance_band, weighted_engagement
from .settings import get_active_settings_version
from .store import DASHBOARD_DB_PATH, connect_dashboard_store
from .web_components import (
    _format_count,
    _health_panel_class,
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
        "Local dashboard shell for monitoring scrape quality and pipeline health.",
        active_path="/",
    )
    if overview is None:
        return _render_empty_overview(workspace, header, settings)

    snapshot = _Snapshot.from_overview(overview, settings)
    selector = _render_run_switcher(run_options, selected_run_id)
    return f"""
      {header}
      <p class="lede" style="margin-top:-12px;">Marketer view: what we searched for, what we got back, whether it was useful for Nattome, and what to change next scrape.</p>
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
      <section class="panel wide-panel" aria-label="Was it useful for Nattome">
        <h2>3. Was it useful for Nattome?</h2>
        {_render_usefulness(snapshot)}
      </section>
      <section class="panel wide-panel" aria-label="Where did the scrape drift">
        <h2>4. Where did the scrape drift?</h2>
        {_render_drift(snapshot)}
      </section>
      <section class="panel wide-panel" aria-label="What should we change next scrape">
        <h2>5. What should we change next scrape?</h2>
        <p class="muted overview-disclaimer">Heuristic prompts based on this run's relevance bands and selection yield. Treat as suggestions, not commands.</p>
        {_render_change_suggestions(snapshot)}
      </section>
    """


# ---------- Snapshot ----------

class _Snapshot:
    def __init__(
        self,
        *,
        run: dict[str, Any],
        score: dict[str, Any] | None,
        health: dict[str, Any] | None,
        config: dict[str, Any],
        phase_issues: list[str],
        videos: list[dict[str, Any]],
        selected_ids: set[str],
        settings: dict[str, Any],
    ) -> None:
        self.run = run
        self.score = score
        self.health = health
        self.config = config
        self.phase_issues = phase_issues
        self.videos = videos
        self.selected_ids = selected_ids
        self.settings = settings

    @classmethod
    def from_overview(cls, overview: dict[str, Any], settings: dict[str, Any]) -> "_Snapshot":
        return cls(
            run=overview["run"],
            score=overview["score"],
            health=overview["health"],
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
    videos = _all_run_videos(connection, run_id, selected)
    manifest = _json_loads(run["raw_json"])
    return {
        "run": dict(run),
        "score": dict(score) if score else None,
        "health": dict(health_summary) if health_summary else None,
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
    timestamp = option["run_timestamp"] or "Timestamp not recorded"
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
    score = snapshot.score
    health_summary = snapshot.health
    run = snapshot.run
    config = snapshot.config
    quality_metric = str(score["score"]) if score else "--"
    quality_band = score["band"] if score else "not scored"
    health_status = health_summary["status"] if health_summary else "unknown"
    health_impact = health_summary["impact_summary"] if health_summary else "Pipeline health has not been computed."
    config_version = config.get("version") or "Not recorded"
    next_scheduled_run = config.get("next_scheduled_run") or "Not scheduled"
    return f"""
      <section class="grid overview-hero" aria-label="Run health snapshot">
        <article class="panel feature">
          <h2>Scrape Quality Score</h2>
          <p class="metric">{html.escape(str(quality_metric))}</p>
          <p class="muted">{html.escape(str(quality_band))}</p>
        </article>
        <article class="panel feature {_health_panel_class(health_summary)}">
          <h2>Pipeline Health</h2>
          <p class="metric">{html.escape(health_status)}</p>
          <p class="muted">{html.escape(health_impact)}</p>
        </article>
        <article class="panel feature">
          <h2>Latest Run</h2>
          <p class="run-id-metric"><code>{html.escape(str(run["run_id"]))}</code></p>
          <p class="muted">{html.escape(str(run["run_timestamp"] or "Timestamp not recorded"))} &middot; {html.escape(str(run["mode"] or "Run type not recorded"))}</p>
          <p class="muted">Config {html.escape(str(config_version))} &middot; next run {html.escape(str(next_scheduled_run))}</p>
        </article>
      </section>
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


# ---------- Section 3: usefulness ----------

def _render_usefulness(snapshot: _Snapshot) -> str:
    videos = snapshot.videos
    bands = _relevance_bands(videos)
    funnel = _funnel(snapshot)
    drivers = _quality_drivers_items(snapshot.score)
    return f"""
      <div class="overview-grid-3">
        <article>
          <h3>Relevance distribution</h3>
          {_render_relevance_bands(bands, total=len(videos))}
        </article>
        <article>
          <h3>Funnel</h3>
          {_render_funnel(funnel)}
        </article>
        <article>
          <h3>Top Quality Drivers</h3>
          {drivers}
        </article>
      </div>
    """


def _relevance_bands(videos: list[dict[str, Any]]) -> dict[str, int]:
    bands = {"high relevance": 0, "medium relevance": 0, "low relevance": 0}
    for video in videos:
        bands[relevance_band(video)] += 1
    return bands


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


def _render_relevance_bands(bands: dict[str, int], *, total: int) -> str:
    if total <= 0:
        return '<p class="muted">No videos to score.</p>'
    rows: list[str] = []
    for label, key, css in (
        ("High", "high relevance", "ok"),
        ("Medium", "medium relevance", "accent"),
        ("Low", "low relevance", "warn"),
    ):
        count = bands[key]
        rows.append(
            f'<li><span class="status-pill {css}">{label}</span> {count} of {total} ({_percent(count, total)})</li>'
        )
    return f'<ul class="overview-stat-list">{"".join(rows)}</ul>'


def _render_funnel(funnel: dict[str, int]) -> str:
    return f"""
      <ul class="overview-funnel">
        <li><span class="overview-funnel-label">Scanned</span><span class="overview-funnel-value">{funnel['scanned']}</span></li>
        <li><span class="overview-funnel-label">Eligible</span><span class="overview-funnel-value">{funnel['eligible']}</span></li>
        <li><span class="overview-funnel-label">Selected</span><span class="overview-funnel-value">{funnel['selected']}</span></li>
      </ul>
    """


def _quality_drivers_items(score: dict[str, object] | None) -> str:
    if not score:
        return '<p class="muted">No scrape quality drivers have been computed.</p>'
    drivers = _json_loads(score.get("drivers_json"))
    if not isinstance(drivers, list) or not drivers:
        return '<p class="muted">No scrape quality drivers were recorded.</p>'
    items: list[str] = []
    for driver in drivers[:4]:
        if not isinstance(driver, dict):
            continue
        direction = str(driver.get("direction") or "neutral")
        message = str(driver.get("message") or driver.get("component") or "Quality driver")
        items.append(f'<li><strong>{html.escape(direction.title())}</strong>: {html.escape(message)}</li>')
    return f'<ul class="compact-list">{"".join(items)}</ul>' if items else '<p class="muted">No scrape quality drivers were recorded.</p>'


# ---------- Section 4: drift ----------

def _render_drift(snapshot: _Snapshot) -> str:
    videos = snapshot.videos
    if not videos and not snapshot.phase_issues:
        return _render_empty_state("warning", "No drift signals yet.", "Run a scrape and the dashboard will surface low-relevance posts and weak attribution.")
    low_relevance = sorted(
        [v for v in videos if relevance_band(v) == "low relevance"],
        key=lambda v: nattome_relevance(v),
    )[:3]
    missing_source = sum(1 for v in videos if not str(v.get("source_input") or "").strip())
    drift_hashtags = _drift_hashtags(videos)
    issue_items = "".join(f"<li>{html.escape(issue)}</li>" for issue in snapshot.phase_issues[:2])
    return f"""
      <div class="overview-grid-3">
        <article>
          <h3>Low-relevance examples</h3>
          {_render_low_relevance(low_relevance)}
        </article>
        <article>
          <h3>Weak attribution</h3>
          <ul class="overview-stat-list">
            <li><strong>{missing_source}</strong> post(s) returned with no source_input recorded.</li>
            <li><strong>{sum(1 for v in videos if not int(v.get('is_downloadable') or 0))}</strong> post(s) not downloadable.</li>
          </ul>
        </article>
        <article>
          <h3>Off-topic-leaning hashtags</h3>
          {_render_drift_hashtags(drift_hashtags)}
        </article>
      </div>
      {f'<h3>Run issues</h3><ul class="compact-list">{issue_items}</ul>' if issue_items else ''}
    """


def _render_low_relevance(videos: list[dict[str, Any]]) -> str:
    if not videos:
        return '<p class="muted">No low-relevance posts in this run.</p>'
    items: list[str] = []
    for video in videos:
        caption = str(video.get("caption") or "Untitled TikTok")
        url = str(video.get("tiktok_url") or "")
        link = f' <a href="{html.escape(url)}" target="_blank" rel="noopener">Open</a>' if url else ""
        items.append(f"<li><strong>{html.escape(caption)}</strong>{link}</li>")
    return f'<ul class="compact-list">{"".join(items)}</ul>'


def _drift_hashtags(videos: list[dict[str, Any]]) -> list[tuple[str, int, float]]:
    by_tag: dict[str, list[float]] = {}
    for video in videos:
        relevance = nattome_relevance(video)
        for tag in _video_hashtags(video):
            by_tag.setdefault(tag, []).append(relevance)
    rows = []
    for tag, scores in by_tag.items():
        if len(scores) < 2:
            continue
        average = sum(scores) / len(scores)
        if average <= 0.25:
            rows.append((tag, len(scores), average))
    rows.sort(key=lambda row: (-row[1], row[2]))
    return rows[:5]


def _render_drift_hashtags(rows: list[tuple[str, int, float]]) -> str:
    if not rows:
        return '<p class="muted">No hashtags pulled mostly off-topic posts.</p>'
    items = "".join(
        f'<li><span class="chip warn">#{html.escape(tag)}</span> &mdash; {count} posts, avg relevance {average:.0%}</li>'
        for tag, count, average in rows
    )
    return f'<ul class="overview-stat-list">{items}</ul>'


# ---------- Section 5: change suggestions ----------

def _render_change_suggestions(snapshot: _Snapshot) -> str:
    keep, add, remove = _suggestions(snapshot)
    return f"""
      <div class="overview-grid-3">
        <article class="suggestion-card suggestion-keep">
          <h3>Keep</h3>
          {_render_suggestion_list(keep, empty="No clear high-yield seeds yet.")}
        </article>
        <article class="suggestion-card suggestion-add">
          <h3>Consider adding</h3>
          {_render_suggestion_list(add, empty="No new high-relevance hashtags surfaced beyond your settings.")}
        </article>
        <article class="suggestion-card suggestion-remove">
          <h3>Consider removing</h3>
          {_render_suggestion_list(remove, empty="No settings inputs are clearly underperforming.")}
        </article>
      </div>
    """


def _suggestions(snapshot: _Snapshot) -> tuple[list[str], list[str], list[str]]:
    videos = snapshot.videos
    inputs = snapshot.search_inputs
    settings_hashtags = {tag.lstrip("#").lower() for tag in inputs["hashtags"]}
    settings_keywords = {kw.lower() for kw in inputs["keywords"]}
    settings_profiles = {p.lstrip("@").lower() for p in inputs["profiles"]}

    by_tag_scores: dict[str, list[float]] = {}
    by_tag_selected: dict[str, int] = {}
    for video in videos:
        relevance = nattome_relevance(video)
        is_selected = video.get("video_id") in snapshot.selected_ids
        for tag in _video_hashtags(video):
            by_tag_scores.setdefault(tag, []).append(relevance)
            if is_selected:
                by_tag_selected[tag] = by_tag_selected.get(tag, 0) + 1

    by_source: dict[str, list[float]] = {}
    by_source_selected: dict[str, int] = {}
    for video in videos:
        source = str(video.get("source_input") or "").strip()
        if not source:
            continue
        relevance = nattome_relevance(video)
        by_source.setdefault(source, []).append(relevance)
        if video.get("video_id") in snapshot.selected_ids:
            by_source_selected[source] = by_source_selected.get(source, 0) + 1

    keep: list[str] = []
    for tag in settings_hashtags:
        scores = by_tag_scores.get(tag, [])
        if scores and sum(scores) / len(scores) >= 0.5:
            keep.append(f"#{tag} ({by_tag_selected.get(tag, 0)} selected)")
    for profile in settings_profiles:
        seed = f"@{profile}"
        scores = by_source.get(seed) or by_source.get(profile)
        if scores and sum(scores) / len(scores) >= 0.5:
            keep.append(f"{seed} ({by_source_selected.get(seed, 0) + by_source_selected.get(profile, 0)} selected)")

    add: list[str] = []
    for tag, scores in sorted(
        by_tag_scores.items(),
        key=lambda item: (-(sum(item[1]) / len(item[1])), -len(item[1])),
    ):
        if tag in settings_hashtags:
            continue
        if len(scores) < 2:
            continue
        average = sum(scores) / len(scores)
        if average < 0.5:
            continue
        add.append(f"#{tag} (avg relevance {average:.0%}, {len(scores)} posts)")
        if len(add) >= 5:
            break

    remove: list[str] = []
    for tag in settings_hashtags:
        scores = by_tag_scores.get(tag, [])
        if scores and sum(scores) / len(scores) <= 0.0 and not by_tag_selected.get(tag):
            remove.append(f"#{tag} (0% relevance, 0 selected)")
    for keyword in settings_keywords:
        scores = by_source.get(keyword) or []
        if scores and sum(scores) / len(scores) <= 0.0 and not by_source_selected.get(keyword):
            remove.append(f"\"{keyword}\" (0% relevance, 0 selected)")
    for profile in settings_profiles:
        seed = f"@{profile}"
        scores = by_source.get(seed) or by_source.get(profile) or []
        if scores and sum(scores) / len(scores) <= 0.0 and not (by_source_selected.get(seed) or by_source_selected.get(profile)):
            remove.append(f"{seed} (0% relevance, 0 selected)")

    return keep[:5], add, remove[:5]


def _render_suggestion_list(items: list[str], *, empty: str) -> str:
    if not items:
        return f'<p class="muted">{html.escape(empty)}</p>'
    rendered = "".join(f"<li>{html.escape(item)}</li>" for item in items)
    return f'<ul class="compact-list">{rendered}</ul>'


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
      <section class="grid overview-hero" aria-label="Run health snapshot">
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
      <section class="panel">
        <h2>Top Quality Drivers</h2>
        {_render_empty_state('spark', 'Artifact indexing and scoring will populate this area.')}
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
