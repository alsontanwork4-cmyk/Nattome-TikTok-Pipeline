from __future__ import annotations

import html
import json

from pathlib import Path

from .scoring import engagement_rate_text, freshness_label, percent_text, relevance_label, score_text
from .web_constants import CURATION_LABELS, NAV_GROUPS, NAV_ITEMS

_ICON_PATHS: dict[str, str] = {
    "overview": '<path d="M3 12 12 4l9 8"/><path d="M5 10v10h14V10"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    "content": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m10 9 6 3-6 3z" fill="currentColor" stroke="none"/>',
    "history": '<path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v5h5"/><path d="M12 8v5l3 2"/>',
    "report": '<path d="M6 3h9l3 3v15H6z"/><path d="M15 3v4h4"/><path d="M9 11h6"/><path d="M9 15h6"/><path d="M9 19h4"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h0a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h0a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v0a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
    "architecture": '<path d="M4 6h6v4H4z"/><path d="M14 6h6v4h-6z"/><path d="M9 14h6v4H9z"/><path d="M7 10v2h10v-2"/>',
    "warning": '<path d="M12 3 2 20h20z"/><path d="M12 10v5"/><circle cx="12" cy="18" r="0.6" fill="currentColor" stroke="none"/>',
    "empty": '<rect x="4" y="6" width="16" height="14" rx="2"/><path d="M4 10h16"/><path d="M9 14h6"/>',
    "db": '<ellipse cx="12" cy="6" rx="8" ry="3"/><path d="M4 6v6c0 1.7 3.6 3 8 3s8-1.3 8-3V6"/><path d="M4 12v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>',
    "leaf": '<path d="M5 19c0-8 6-14 14-14-1 9-6 14-14 14z" fill="currentColor" stroke="none" opacity=".95"/><path d="M5 19c4-4 8-7 14-14" stroke="rgba(255,255,255,.55)" stroke-width="1.2"/>',
    "spark": '<path d="m4 16 4-5 4 3 4-7 4 5"/>',
}

def _icon(name: str) -> str:
    paths = _ICON_PATHS.get(name, '')
    return (
        f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true">{paths}</svg>'
    )


def _render_nav_item(label: str, route: str, active_path: str, icon_key: str = "") -> str:
    current = ' aria-current="page"' if route == active_path else ""
    icon_markup = _icon(icon_key) if icon_key else ""
    return (
        f'<a class="nav-link" href="{html.escape(route)}"{current}>'
        f'{icon_markup}<span>{html.escape(label)}</span></a>'
    )


def _render_sidebar(active_path: str) -> str:
    groups = []
    for group_label, items in NAV_GROUPS:
        links = "\n".join(
            _render_nav_item(label, route, active_path, icon_key)
            for label, route, icon_key in items
        )
        groups.append(
            f'<div class="nav-group">'
            f'<p class="nav-group-label">{html.escape(group_label)}</p>'
            f'{links}'
            f'</div>'
        )
    return (
        '<aside class="sidebar" aria-label="Dashboard sections">'
        + "".join(groups)
        + '</aside>'
    )


def _render_breadcrumb(active_path: str) -> str:
    title = _title_for_path(active_path)
    if active_path == "/":
        return (
            '<nav class="breadcrumb" aria-label="Breadcrumb">'
            '<span class="current">Overview</span>'
            '</nav>'
        )
    return (
        '<nav class="breadcrumb" aria-label="Breadcrumb">'
        '<a href="/">Dashboard</a>'
        '<span class="sep" aria-hidden="true">/</span>'
        f'<span class="current">{html.escape(title)}</span>'
        '</nav>'
    )


def _render_topbar(active_path: str, workspace: Path) -> str:
    return f"""
    <header class="topbar" role="banner">
      <a class="brand-mark" href="/" aria-label="Nattome dashboard home">
        {_render_brand_logo()}
        <span class="brand-tag">Nattome TikTok Scraper</span>
      </a>
      <div class="topbar-meta">
        <span class="meta-pill primary"><span class="dot" aria-hidden="true"></span>Pipeline ready</span>
        <span class="meta-pill">{_icon('db')}Local workspace</span>
      </div>
    </header>
    """


def _render_brand_logo() -> str:
    logo_path = Path(__file__).resolve().parent / "assets" / "nattome-logo.png"
    if logo_path.is_file():
        return '<img class="brand-logo" src="/static/nattome-logo.png" alt="Nattome">'
    return f'<span class="leaf">{_icon("leaf")}</span><span>Nattome</span>'


def _render_page_header(title: str, lede: str, active_path: str = "/", actions_html: str = "") -> str:
    actions_block = f'<div class="page-actions">{actions_html}</div>' if actions_html else ""
    return f"""
      {_render_breadcrumb(active_path)}
      <h1>{html.escape(title)}</h1>
      <p class="lede">{html.escape(lede)}</p>
      {actions_block}
    """


def _render_empty_state(icon_key: str, headline: str, helper: str = "") -> str:
    helper_markup = f'<p class="muted" style="margin:4px 0 0;font-size:13px;">{html.escape(helper)}</p>' if helper else ""
    return f"""
      <div class="empty-state">
        <span class="empty-state-icon">{_icon(icon_key)}</span>
        <div>
          <p style="margin:0;color:var(--ink-2);font-weight:600;">{html.escape(headline)}</p>
          {helper_markup}
        </div>
      </div>
    """
def _metadata_item(label: str, value: str) -> str:
    return f"""
      <div>
        <dt>{html.escape(label)}</dt>
        <dd>{html.escape(value)}</dd>
      </div>
    """
def _textarea_field(label: str, name: str, value: object) -> str:
    return f"""
      <label class="field-label">
        {html.escape(label)}
        <textarea name="{html.escape(name)}">{html.escape(str(value or ""))}</textarea>
      </label>
    """


def _input_field(label: str, name: str, value: object) -> str:
    return f"""
      <label class="field-label">
        {html.escape(label)}
        <input type="text" name="{html.escape(name)}" value="{html.escape(str(value or ""))}">
      </label>
    """


def _scope_options(active_scope: str) -> str:
    labels = {
        "all": "All sources",
        "hashtags": "Only hashtags",
        "keywords": "Only keywords",
        "profiles": "Only competitor profiles",
    }
    options = []
    for scope in ("all", "hashtags", "keywords", "profiles"):
        selected = " selected" if scope == active_scope else ""
        options.append(f'<option value="{scope}"{selected}>{html.escape(labels[scope])}</option>')
    return "".join(options)


def _lines(value: object) -> str:
    if isinstance(value, list):
        return "\n".join(str(item) for item in value)
    return str(value or "")


def _version_label(version: int) -> str:
    return "Default" if version <= 0 else f"v{version}"


def _first_form_value(form: dict[str, list[str]], key: str) -> str:
    values = form.get(key) or [""]
    return values[0].strip()


def _first_query_values(query: dict[str, list[str]]) -> dict[str, str]:
    return {
        key: values[0].strip()
        for key, values in query.items()
        if values and values[0].strip()
    }


def _curation_labels(raw_value: object) -> list[str]:
    labels = _json_loads(raw_value)
    if not isinstance(labels, list):
        return []
    return [str(label) for label in labels if str(label) in CURATION_LABELS]


def _hashtag_text(raw_value: object) -> str:
    hashtags = _json_loads(raw_value)
    if not isinstance(hashtags, list):
        return ""
    return " ".join(f"#{str(tag).lstrip('#')}" for tag in hashtags)


def _display_status(value: object) -> str:
    status = str(value or "raw").lower()
    if status == "raw":
        return "raw only"
    if status in {"eligible", "selected", "analyzed"}:
        return status
    return "raw only"


def _engagement_rate(video: dict[str, object]) -> str:
    return engagement_rate_text(video)


def _relevance_label(caption: str, hashtags: str, source_input: str) -> str:
    return relevance_label(
        {
            "caption": caption,
            "hashtags": hashtags,
            "source_input": source_input,
        }
    )


def _freshness_label(created_at: object) -> str:
    return freshness_label(created_at)


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
def _score_text(value: object) -> str:
    return html.escape(score_text(value))


def _percent_text(value: object) -> str:
    return percent_text(value)
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
