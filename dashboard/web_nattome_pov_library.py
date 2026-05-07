from __future__ import annotations

import html
from pathlib import Path

from .nattome_pov_library import list_nattome_pov_versions, list_nattome_povs
from .web_components import _input_field, _metadata_item, _textarea_field

def _render_nattome_pov_library(workspace: Path) -> str:
    povs = list_nattome_povs(workspace)
    pov_body = (
        "".join(_render_nattome_pov(workspace, pov) for pov in povs)
        if povs
        else '<p class="muted">No Nattome POV entries have been created yet.</p>'
    )
    return f"""
      <h1>Nattome POV Library</h1>
      <p class="lede">Owned Nattome interpretations live here: brand-safe readings, targeting, adaptation rules, and source links.</p>
      <div class="actions" aria-label="Nattome POV exports">
        <a class="action-link" href="/exports/nattome-povs.md">Export Nattome POVs Markdown</a>
      </div>
      <section class="panel wide-panel">
        <h2>Nattome POV Entries</h2>
        <div class="library-list" aria-label="Nattome POV entries">
          {pov_body}
        </div>
      </section>
      <section class="panel wide-panel">
        <h2>Create Nattome POV</h2>
        {_render_nattome_pov_create_form()}
      </section>
    """


def _render_nattome_pov(workspace: Path, pov: object) -> str:
    versions = list_nattome_pov_versions(workspace, getattr(pov, "id"))
    return f"""
      <article class="panel">
        <div class="library-header">
          <div>
            <h3>{html.escape(str(getattr(pov, "title")))}</h3>
            <p>{html.escape(str(getattr(pov, "description")))}</p>
          </div>
          <span class="status-pill">{html.escape(str(getattr(pov, "status")))} v{getattr(pov, "version")}</span>
        </div>
        <dl class="metadata-grid">
          {_metadata_item("Product", str(getattr(pov, "product") or "Nattome"))}
          {_metadata_item("Campaign", str(getattr(pov, "campaign") or "Not set"))}
          {_metadata_item("Market", str(getattr(pov, "market") or "Malaysia"))}
          {_metadata_item("Language", str(getattr(pov, "language") or "mixed/English"))}
          {_metadata_item("Audience / Avatar", str(getattr(pov, "audience_avatar") or "Not set"))}
          {_metadata_item("Symptom / Occasion", str(getattr(pov, "symptom_occasion") or "Not set"))}
          {_metadata_item("Channel", str(getattr(pov, "channel") or "TikTok"))}
          {_metadata_item("Updated By", str(getattr(pov, "updated_by")))}
        </dl>
        <h3>Brand-safe interpretation</h3>
        <p>{html.escape(str(getattr(pov, "brand_safe_interpretation") or "Not set"))}</p>
        <h3>Adaptation rules</h3>
        <p>{html.escape(str(getattr(pov, "adaptation_rules") or "Not set"))}</p>
        {_render_pov_source_links(getattr(pov, "source_links"))}
        {_render_version_history(versions)}
        {_render_nattome_pov_edit_form(pov)}
        {_render_nattome_pov_archive_form(pov)}
      </article>
    """


def _render_pov_source_links(source_links: object) -> str:
    if not isinstance(source_links, list) or not source_links:
        return '<p class="muted">No source links recorded.</p>'
    items = [
        f'<li><a href="{html.escape(str(link))}">{html.escape(str(link))}</a></li>'
        for link in source_links
        if str(link)
    ]
    return f"""
      <h3>Source links</h3>
      <ul class="compact-list">{"".join(items)}</ul>
    """


def _render_version_history(versions: list[object]) -> str:
    if not versions:
        return '<p class="muted">No version history recorded.</p>'
    items = [
        (
            f"<li>v{getattr(version, 'version')} {html.escape(str(getattr(version, 'change_type')))} "
            f"by {html.escape(str(getattr(version, 'changed_by')))} "
            f"{html.escape(str(getattr(version, 'changed_at')))}</li>"
        )
        for version in versions
    ]
    return f"""
      <h3>Version history</h3>
      <ul class="compact-list">{"".join(items)}</ul>
    """


def _render_nattome_pov_create_form() -> str:
    return f"""
      <form class="library-form" method="post" action="/nattome-pov-library/create">
        <div class="library-form-grid">
          {_input_field("Title", "title", "")}
          {_input_field("Product", "product", "Nattome")}
          {_input_field("Campaign", "campaign", "")}
          {_input_field("Market", "market", "Malaysia")}
          {_input_field("Language", "language", "mixed/English")}
          {_input_field("Audience / Avatar", "audience_avatar", "")}
          {_input_field("Symptom / Occasion", "symptom_occasion", "")}
          {_input_field("Channel", "channel", "TikTok")}
          {_textarea_field("Description", "description", "")}
          {_textarea_field("Brand-safe interpretation", "brand_safe_interpretation", "")}
          {_textarea_field("Adaptation rules", "adaptation_rules", "")}
          {_textarea_field("Source links", "source_links", "")}
          {_input_field("User", "user", "local")}
        </div>
        <button type="submit">Create Nattome POV</button>
      </form>
    """


def _render_nattome_pov_edit_form(pov: object) -> str:
    return f"""
      <form class="library-form" method="post" action="/nattome-pov-library/edit">
        <input type="hidden" name="pov_id" value="{getattr(pov, "id")}">
        <div class="library-form-grid">
          {_input_field("Title", "title", getattr(pov, "title"))}
          {_input_field("Status", "status", getattr(pov, "status"))}
          {_input_field("Product", "product", getattr(pov, "product"))}
          {_input_field("Campaign", "campaign", getattr(pov, "campaign"))}
          {_input_field("Market", "market", getattr(pov, "market"))}
          {_input_field("Language", "language", getattr(pov, "language"))}
          {_input_field("Audience / Avatar", "audience_avatar", getattr(pov, "audience_avatar"))}
          {_input_field("Symptom / Occasion", "symptom_occasion", getattr(pov, "symptom_occasion"))}
          {_input_field("Channel", "channel", getattr(pov, "channel"))}
          {_textarea_field("Description", "description", getattr(pov, "description"))}
          {_textarea_field("Brand-safe interpretation", "brand_safe_interpretation", getattr(pov, "brand_safe_interpretation"))}
          {_textarea_field("Adaptation rules", "adaptation_rules", getattr(pov, "adaptation_rules"))}
          {_textarea_field("Source links", "source_links", "\n".join(getattr(pov, "source_links") or []))}
          {_input_field("User", "user", "local")}
        </div>
        <button type="submit">Save Nattome POV</button>
      </form>
    """


def _render_nattome_pov_archive_form(pov: object) -> str:
    if str(getattr(pov, "status")) == "archived":
        return ""
    return f"""
      <form class="library-form" method="post" action="/nattome-pov-library/archive">
        <input type="hidden" name="pov_id" value="{getattr(pov, "id")}">
        {_input_field("User", "user", "local")}
        <button type="submit">Archive Nattome POV</button>
      </form>
    """
