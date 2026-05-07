from __future__ import annotations

import html
from pathlib import Path

from .settings import READ_ONLY_SETTINGS, get_active_settings_version, list_settings_versions
from .web_components import (
    _input_field,
    _lines,
    _render_empty_state,
    _render_page_header,
    _scope_options,
    _textarea_field,
    _version_label,
)

def _render_scrape_settings(workspace: Path) -> str:
    active = get_active_settings_version(workspace)
    versions = list_settings_versions(workspace)
    settings = active.new_settings
    active_label = _version_label(active.version)
    return f"""
      <h1>Production Scrape Settings</h1>
      <p class="lede">Validated marketer-editable scrape settings. Risky pipeline internals stay read-only in MVP.</p>
      <section class="grid" aria-label="Scrape settings status">
        <article class="panel">
          <h2>Current production config version</h2>
          <p class="metric">{html.escape(active_label)}</p>
          <p class="muted">Next scheduled run will use version {html.escape(active_label)}.</p>
        </article>
        <article class="panel">
          <h2>Last change reason</h2>
          <p>{html.escape(active.reason)}</p>
          <p class="muted">{html.escape(active.changed_by)} {html.escape(active.timestamp)}</p>
        </article>
        <article class="panel">
          <h2>Read-only MVP settings</h2>
          {_render_read_only_settings()}
        </article>
      </section>
      <section class="panel wide-panel">
        <h2>Edit production settings</h2>
        {_render_settings_form(settings)}
      </section>
      <section class="panel wide-panel">
        <h2>Config version history</h2>
        {_render_version_history(versions)}
      </section>
    """


def _render_settings_form(settings: dict[str, object]) -> str:
    checked = " checked" if settings.get("requires_downloadable_video") else ""
    return f"""
      <form class="settings-form" method="post" action="/scrape-settings/save">
        <div class="settings-grid">
          {_textarea_field("Hashtags", "hashtags", _lines(settings.get("hashtags")))}
          {_textarea_field("Keywords", "keywords", _lines(settings.get("keywords")))}
          {_textarea_field("Competitor profiles", "competitor_profiles", _lines(settings.get("competitor_profiles")))}
          {_textarea_field("Exclusion terms", "exclusion_terms", _lines(settings.get("exclusion_terms")))}
          <label class="field-label">
            Scrape scope
            <select name="scope">
              {_scope_options(str(settings.get("scope") or "all"))}
            </select>
          </label>
          {_input_field("Results per input", "results_per_input", settings.get("results_per_input"))}
          {_input_field("Top N", "top_n", settings.get("top_n"))}
          {_input_field("Daily selection size", "daily_selection_size", settings.get("daily_selection_size"))}
          {_input_field("Minimum views", "minimum_views", settings.get("minimum_views"))}
          {_input_field("Maximum age days", "maximum_age_days", settings.get("maximum_age_days"))}
          {_input_field("Minimum weighted engagement rate", "minimum_weighted_engagement_rate", settings.get("minimum_weighted_engagement_rate"))}
          <label class="check-label">
            <input type="checkbox" name="requires_downloadable_video" value="on"{checked}>
            Require downloadable video
          </label>
          {_input_field("User", "user", "local")}
          {_textarea_field("Save reason", "reason", "")}
        </div>
        <button type="submit">Save production settings</button>
      </form>
    """


def _render_read_only_settings() -> str:
    items = [
        f"<li><strong>{html.escape(label)}</strong>: {html.escape(value)}</li>"
        for label, value in READ_ONLY_SETTINGS.items()
    ]
    return f'<ul class="compact-list">{"".join(items)}</ul>'


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
          <input type="text" name="reason" maxlength="240">
        </label>
        <label class="field-label">
          User
          <input type="text" name="user" value="local" maxlength="120">
        </label>
        <button type="submit">Roll back to {_version_label(target_version)}</button>
      </form>
    """
