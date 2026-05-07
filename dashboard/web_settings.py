from __future__ import annotations

import html
from pathlib import Path

from .settings import get_active_settings_version, list_settings_versions
from .web_components import (
    _lines,
    _scope_options,
    _version_label,
)

SETTING_HELP: dict[str, dict[str, str]] = {
    "hashtags": {
        "changes": "Searches TikTok hashtag pages for gut-health content.",
        "increase": "Adding more hashtags broadens discovery and can find more angles.",
        "decrease": "Removing weak hashtags narrows the scrape and can reduce noise.",
        "default": "Default: 10 gut-health hashtags.",
        "warning": "Too many broad hashtags can make the scrape slower and less focused.",
    },
    "keywords": {
        "changes": "Searches TikTok for plain-language phrases people use around symptoms and routines.",
        "increase": "Adding keywords can uncover videos that do not use your target hashtags.",
        "decrease": "Removing keywords makes the scrape more focused but may miss useful posts.",
        "default": "Default: 7 gut-health search phrases.",
        "warning": "Broad phrases can pull in wellness content that is not a Nattome fit.",
    },
    "competitor_profiles": {
        "changes": "Checks specific creator or brand profiles for inspiration and market signals.",
        "increase": "Adding profiles broadens competitor monitoring.",
        "decrease": "Removing profiles keeps the scrape focused on the most relevant accounts.",
        "default": "Default: @gaviscon, @gutgang, @drwillcole.",
        "warning": "Profiles that post outside gut health can add irrelevant candidates.",
    },
    "scope": {
        "changes": "Chooses which source type the next scrape uses.",
        "increase": "All sources gives the broadest scrape.",
        "decrease": "A single source type is faster and easier to diagnose.",
        "default": "Default: All sources.",
        "warning": "Using only one source type can hide good candidates from the others.",
    },
    "results_per_input": {
        "changes": "Sets how many TikToks to collect from each hashtag, keyword, or profile.",
        "increase": "Higher values collect more candidates and may improve discovery.",
        "decrease": "Lower values make the scrape faster but reduce coverage.",
        "default": "Default: 20. Typical range: 10-50.",
        "warning": "Very high values can slow the scrape and create more review work.",
    },
    "top_n": {
        "changes": "Sets how many of the strongest raw candidates stay in the handoff pool.",
        "increase": "Higher values keep more possibilities for selection.",
        "decrease": "Lower values make the handoff tighter and easier to review.",
        "default": "Default: 30. Typical range: 10-100.",
        "warning": "Too low can drop useful posts before they are reviewed.",
    },
    "daily_selection_size": {
        "changes": "Sets how many candidates are selected for the daily discovery handoff.",
        "increase": "Higher values give more videos to review or analyze.",
        "decrease": "Lower values keep the daily handoff more focused.",
        "default": "Default: 5. Typical range: 3-10.",
        "warning": "Too high can create more evidence and review work than needed.",
    },
    "minimum_views": {
        "changes": "Filters out TikToks below a view-count threshold.",
        "increase": "Higher values favor proven videos but reduce candidate volume.",
        "decrease": "Lower values allow earlier or niche videos into the pool.",
        "default": "Default: 10000. Typical range: 5000-50000.",
        "warning": "Too high can leave too few usable candidates.",
    },
    "maximum_age_days": {
        "changes": "Only keeps TikToks posted within the last N days.",
        "increase": "Higher values include older videos and improve volume.",
        "decrease": "Lower values prioritize fresher trends.",
        "default": "Default: 30 days. Typical range: 7-60 days.",
        "warning": "Too low can make the scrape look weak on quiet days.",
    },
    "minimum_engagement_rate_percent": {
        "changes": "Filters for videos where likes, comments, and shares are strong compared with views.",
        "increase": "Higher percentages keep stronger engagement signals but fewer videos.",
        "decrease": "Lower percentages allow more candidates into the pool.",
        "default": "Default: 3%. Typical range: 1-8%.",
        "warning": "Too high can remove useful high-view videos with average engagement.",
    },
    "requires_downloadable_video": {
        "changes": "Requires a downloadable source video before a candidate can be selected.",
        "increase": "Keeping it on improves evidence and reporting readiness.",
        "decrease": "Turning it off may keep useful TikToks that cannot be downloaded.",
        "default": "Default: On.",
        "warning": "Turning it off can create candidates that are harder to analyze later.",
    },
    "exclusion_terms": {
        "changes": "Blocks known low-quality topics, phrases, or patterns from the scrape.",
        "increase": "Adding terms can reduce repeated noise.",
        "decrease": "Removing terms allows more content through.",
        "default": "Default: none.",
        "warning": "Overly broad exclusions can remove useful gut-health content.",
    },
}


def _render_scrape_settings(workspace: Path) -> str:
    active = get_active_settings_version(workspace)
    versions = list_settings_versions(workspace)
    settings = active.new_settings
    active_label = _version_label(active.version)
    return f"""
      <h1>Scrape Settings</h1>
      <p class="lede">Choose what the next scheduled TikTok scrape should search, collect, and filter.</p>
      <p class="settings-status">Next scheduled scrape uses config: <strong>{html.escape(active_label)}</strong></p>
      {_render_current_settings(settings)}
      <section class="panel wide-panel settings-panel">
        <h2>Edit scrape settings</h2>
        {_render_settings_form(settings)}
      </section>
      {_render_advanced_history(versions)}
    """


def _render_settings_form(settings: dict[str, object]) -> str:
    checked = " checked" if settings.get("requires_downloadable_video") else ""
    return f"""
      <form class="settings-form" method="post" action="/scrape-settings/save">
        <section class="settings-group" aria-labelledby="where-to-search">
          <h3 id="where-to-search">Where to search</h3>
          <div class="settings-grid">
            {_textarea_setting("Hashtags", "hashtags", _lines(settings.get("hashtags")), "#guthealth\n#bloating")}
            {_textarea_setting("Keywords", "keywords", _lines(settings.get("keywords")), "bloated stomach\ngut health routine")}
            {_textarea_setting("Competitor profiles", "competitor_profiles", _lines(settings.get("competitor_profiles")), "@gaviscon\n@gutgang")}
            {_scope_setting(str(settings.get("scope") or "all"))}
          </div>
        </section>
        <section class="settings-group" aria-labelledby="how-much-to-collect">
          <h3 id="how-much-to-collect">How much to collect</h3>
          <div class="settings-grid">
            {_input_setting("Results per input", "results_per_input", settings.get("results_per_input"))}
            {_input_setting("Top N", "top_n", settings.get("top_n"))}
            {_input_setting("Daily selection size", "daily_selection_size", settings.get("daily_selection_size"))}
          </div>
        </section>
        <section class="settings-group" aria-labelledby="what-to-filter-out">
          <h3 id="what-to-filter-out">What to filter out</h3>
          <div class="settings-grid">
            {_input_setting("Minimum views", "minimum_views", settings.get("minimum_views"))}
            {_input_setting("Freshness window (days)", "maximum_age_days", settings.get("maximum_age_days"))}
            {_input_setting("Minimum engagement rate (%)", "minimum_engagement_rate_percent", _percent_value(settings.get("minimum_weighted_engagement_rate")))}
            {_checkbox_setting("Require downloadable video", "requires_downloadable_video", checked)}
            {_textarea_setting("Exclusion terms", "exclusion_terms", _lines(settings.get("exclusion_terms")), "weight loss\nunrelated supplement")}
          </div>
        </section>
        <div class="settings-save-area">
          <ul class="settings-validation-note">
            <li>At least one hashtag, keyword, or competitor profile is required.</li>
            <li>Duplicate source terms are not allowed.</li>
            <li>Number fields must use valid positive values where required.</li>
          </ul>
          {_input_setting("Save reason", "reason", "", placeholder="Why are you changing this?", required=True, show_help=False)}
          <p class="muted">Saved changes affect the next scheduled scrape.</p>
          <button type="submit">Save scrape settings</button>
        </div>
      </form>
    """


def _textarea_setting(label: str, name: str, value: object, placeholder: str = "") -> str:
    return _setting_shell(
        label,
        name,
        f'<textarea id="{html.escape(name)}" name="{html.escape(name)}" placeholder="{html.escape(placeholder)}">{html.escape(str(value or ""))}</textarea>',
    )


def _input_setting(
    label: str,
    name: str,
    value: object,
    *,
    placeholder: str = "",
    required: bool = False,
    show_help: bool = True,
) -> str:
    required_attr = " required" if required else ""
    return _setting_shell(
        label,
        name,
        f'<input id="{html.escape(name)}" type="text" name="{html.escape(name)}" value="{html.escape(str(value or ""))}" placeholder="{html.escape(placeholder)}"{required_attr}>',
        show_help=show_help,
    )


def _scope_setting(active_scope: str) -> str:
    return _setting_shell(
        "Scrape scope",
        "scope",
        f'<select id="scope" name="scope">{_scope_options(active_scope)}</select>',
    )


def _checkbox_setting(label: str, name: str, checked: str) -> str:
    return _setting_shell(
        label,
        name,
        f"""
        <label class="check-label">
          <input id="{html.escape(name)}" type="checkbox" name="{html.escape(name)}" value="on"{checked}>
          Keep only videos that can be downloaded
        </label>
        """,
    )


def _setting_shell(
    label: str,
    name: str,
    control_html: str,
    *,
    show_help: bool = True,
) -> str:
    if show_help:
        label_markup = _render_setting_help(name, label)
    else:
        label_markup = f"""
        <div class="setting-label-row">
          <label class="field-label" for="{html.escape(name)}">{html.escape(label)}</label>
        </div>
        """
    return f"""
      <div class="settings-field">
        {label_markup}
        {control_html}
      </div>
    """


def _render_setting_help(name: str, label: str) -> str:
    help_text = SETTING_HELP.get(name, {})
    items = [
        ("What it is", help_text.get("changes", "")),
        ("Recommended range", help_text.get("default", "")),
    ]
    rows = [
        f"<li><strong>{html.escape(row_label)}</strong>: {html.escape(text)}</li>"
        for row_label, text in items
        if text
    ]
    return f"""
      <details class="setting-help">
        <summary>
          <label class="field-label" for="{html.escape(name)}">{html.escape(label)}</label>
          <span class="setting-help-pill">Explain</span>
        </summary>
        <ul>{"".join(rows)}</ul>
      </details>
    """


def _percent_value(value: object) -> str:
    try:
        percent = float(value) * 100
    except (TypeError, ValueError):
        return ""
    return f"{percent:g}"


def _render_current_settings(settings: dict[str, object]) -> str:
    items = [
        ("Hashtags", _settings_list(settings.get("hashtags"), prefix="#"), _list_count(settings.get("hashtags"))),
        ("Keywords", _settings_list(settings.get("keywords")), _list_count(settings.get("keywords"))),
        ("Competitor profiles", _settings_list(settings.get("competitor_profiles"), prefix="@"), _list_count(settings.get("competitor_profiles"))),
        ("Exclusion terms", _settings_list(settings.get("exclusion_terms")) or "None", _list_count(settings.get("exclusion_terms"))),
        ("Scrape scope", str(settings.get("scope") or "all"), ""),
        ("Results per input", str(settings.get("results_per_input") or ""), ""),
        ("Top N", str(settings.get("top_n") or ""), ""),
        ("Daily selection size", str(settings.get("daily_selection_size") or ""), ""),
        ("Minimum views", _format_views(settings.get("minimum_views")), ""),
        ("Freshness window (days)", str(settings.get("maximum_age_days") or ""), ""),
        (
            "Minimum engagement rate",
            _format_engagement_rate(settings.get("minimum_weighted_engagement_rate")),
            "",
        ),
        (
            "Require downloadable video",
            "Yes" if settings.get("requires_downloadable_video") else "No",
            "",
        ),
    ]
    rows = [
        f"""
        <div class="current-setting-row">
          <dt>{html.escape(label)}{_count_suffix(count)}</dt>
          <dd>{html.escape(value)}</dd>
        </div>
        """
        for label, value, count in items
    ]
    return f"""
      <section class="panel wide-panel current-settings" aria-label="Current scrape settings">
        <h2>Your current settings</h2>
        <p class="muted current-settings-helper">Reference what the next run will use today; edit below to change them.</p>
        <dl class="current-settings-grid">{"".join(rows)}</dl>
      </section>
    """


def _list_count(value: object) -> str:
    if isinstance(value, list):
        meaningful = [item for item in value if str(item).strip()]
        return str(len(meaningful))
    text = str(value or "").strip()
    return "1" if text else "0"


def _count_suffix(count: str) -> str:
    if not count:
        return ""
    return f' <span class="setting-count">({html.escape(count)})</span>'


def _format_engagement_rate(value: object) -> str:
    try:
        rate = float(value)
    except (TypeError, ValueError):
        return ""
    if rate <= 0:
        return "0%"
    return f"{rate * 100:g}% (decimal {rate:g})"


def _format_views(value: object) -> str:
    try:
        views = int(value)
    except (TypeError, ValueError):
        return str(value or "")
    return f"{views:,}"


def _settings_list(value: object, *, prefix: str = "") -> str:
    if not isinstance(value, list):
        text = str(value or "").strip()
        return f"{prefix}{text}" if text and prefix and not text.startswith(prefix) else text
    tokens = []
    for item in value:
        token = str(item).strip()
        if not token:
            continue
        if prefix and not token.startswith(prefix):
            token = f"{prefix}{token}"
        tokens.append(token)
    return ", ".join(tokens)


def _render_advanced_history(versions: list[object]) -> str:
    return f"""
      <details class="panel wide-panel advanced-settings">
        <summary>Advanced: version history and rollback</summary>
        <div class="advanced-settings-body">
          {_render_version_history(versions)}
        </div>
      </details>
    """


def _render_version_history(versions: list[object]) -> str:
    if not versions:
        return '<p class="muted">No saved config versions yet.</p>'
    items = []
    for version in versions:
        label = _version_label(version.version)
        active = "active" if version.is_active else "inactive"
        rollback_text = (
            f"Rollback of v{version.rollback_of_version}. "
            if version.rollback_of_version
            else ""
        )
        settings = version.new_settings
        rollback_form = "" if version.is_active else _render_rollback_form(version.version)
        items.append(
            f"""
            <li class="history-item">
              <p><strong>{html.escape(label)}</strong> - {html.escape(active)} - {html.escape(rollback_text)}{html.escape(version.reason)}</p>
              <p class="muted">{html.escape(version.changed_by)} {html.escape(version.timestamp)}</p>
              <p class="muted">Hashtags: {html.escape(", ".join(settings.get("hashtags") or []))}</p>
              <p class="muted">Keywords: {html.escape(", ".join(settings.get("keywords") or []))}</p>
              {rollback_form}
            </li>
            """
        )
    return f'<ul class="history-list">{"".join(items)}</ul>'


def _render_rollback_form(target_version: int) -> str:
    return f"""
      <form class="rollback-form" method="post" action="/scrape-settings/rollback">
        <input type="hidden" name="target_version" value="{target_version}">
        <label class="field-label">
          Rollback reason
          <input type="text" name="reason" maxlength="240" placeholder="Why are you rolling back?" required>
        </label>
        <button type="submit">Roll back to {_version_label(target_version)}</button>
      </form>
    """
