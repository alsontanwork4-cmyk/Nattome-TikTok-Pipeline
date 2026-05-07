from __future__ import annotations

import html
from pathlib import Path

from .nattome_pov_library import list_nattome_pov_versions, list_nattome_povs
from .pattern_library import list_approved_patterns
from .web_components import _input_field, _metadata_item, _render_empty_state, _render_page_header, _textarea_field
from .web_pattern_library import _render_pattern_versions

def _render_nattome_pov_library(workspace: Path) -> str:
    povs = list_nattome_povs(workspace)
    approved_patterns = [
        pattern for pattern in list_approved_patterns(workspace)
        if str(getattr(pattern, "status")) == "approved"
    ]
    pattern_names = {int(getattr(pattern, "id")): str(getattr(pattern, "pattern_name")) for pattern in approved_patterns}
    pov_body = (
        "".join(_render_nattome_pov(workspace, pov, pattern_names) for pov in povs)
        if povs
        else '<p class="muted">No Nattome POV entries have been created yet.</p>'
    )
    pattern_link_body = (
        "".join(
            f"<li><strong>{html.escape(str(getattr(pattern, 'pattern_name')))}</strong> "
            f"<span class=\"muted\">{html.escape(str(getattr(pattern, 'hook_type')))} / {html.escape(str(getattr(pattern, 'format_type')))}</span></li>"
            for pattern in approved_patterns
        )
        if approved_patterns
        else '<li class="muted">No approved external patterns are available to link.</li>'
    )
    return f"""
      <h1>Nattome POV Library</h1>
      <p class="lede">Owned Nattome interpretations live here: brand-safe readings, targeting, adaptation rules, and source links. External TikTok mechanics remain in the Pattern Library and are linked only as approved inputs.</p>
      <div class="actions" aria-label="Nattome POV exports">
        <a class="action-link" href="/exports/nattome-povs.md">Export Nattome POVs Markdown</a>
      </div>
      <section class="panel wide-panel">
        <h2>Nattome POV Entries</h2>
        <div class="pattern-list" aria-label="Nattome POV entries">
          {pov_body}
        </div>
      </section>
      <section class="panel wide-panel">
        <h2>Approved Pattern Links</h2>
        <p class="muted">Use these approved external mechanics as links; keep the Nattome-owned interpretation in each POV entry.</p>
        <ul class="compact-list">{pattern_link_body}</ul>
      </section>
      <section class="panel wide-panel">
        <h2>Create Nattome POV</h2>
        {_render_nattome_pov_create_form(approved_patterns)}
      </section>
    """


def _render_nattome_pov(workspace: Path, pov: object, pattern_names: dict[int, str]) -> str:
    versions = list_nattome_pov_versions(workspace, getattr(pov, "id"))
    return f"""
      <article class="panel">
        <div class="pattern-header">
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
        {_render_pov_pattern_links(getattr(pov, "linked_pattern_ids"), pattern_names)}
        {_render_pattern_versions(versions)}
        {_render_nattome_pov_edit_form(pov, pattern_names)}
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


def _render_pov_pattern_links(linked_pattern_ids: object, pattern_names: dict[int, str]) -> str:
    if not isinstance(linked_pattern_ids, list) or not linked_pattern_ids:
        return '<p class="muted">No approved patterns linked.</p>'
    items = []
    for pattern_id in linked_pattern_ids:
        try:
            numeric_id = int(pattern_id)
        except (TypeError, ValueError):
            continue
        label = pattern_names.get(numeric_id, f"Approved pattern #{numeric_id}")
        items.append(f"<li>{html.escape(label)} <span class=\"muted\">#{numeric_id}</span></li>")
    return f"""
      <h3>Linked approved patterns</h3>
      <ul class="compact-list">{"".join(items)}</ul>
    """


def _render_nattome_pov_create_form(approved_patterns: list[object]) -> str:
    return f"""
      <form class="pattern-form" method="post" action="/nattome-pov-library/create">
        <div class="pattern-form-grid">
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
          {_textarea_field("Linked approved pattern IDs", "linked_pattern_ids", _approved_pattern_id_lines(approved_patterns))}
          {_input_field("User", "user", "local")}
        </div>
        <button type="submit">Create Nattome POV</button>
      </form>
    """


def _render_nattome_pov_edit_form(pov: object, pattern_names: dict[int, str]) -> str:
    del pattern_names
    return f"""
      <form class="pattern-form" method="post" action="/nattome-pov-library/edit">
        <input type="hidden" name="pov_id" value="{getattr(pov, "id")}">
        <div class="pattern-form-grid">
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
          {_textarea_field("Linked approved pattern IDs", "linked_pattern_ids", "\n".join(str(item) for item in getattr(pov, "linked_pattern_ids") or []))}
          {_input_field("User", "user", "local")}
        </div>
        <button type="submit">Save Nattome POV</button>
      </form>
    """


def _render_nattome_pov_archive_form(pov: object) -> str:
    if str(getattr(pov, "status")) == "archived":
        return ""
    return f"""
      <form class="pattern-form" method="post" action="/nattome-pov-library/archive">
        <input type="hidden" name="pov_id" value="{getattr(pov, "id")}">
        {_input_field("User", "user", "local")}
        <button type="submit">Archive Nattome POV</button>
      </form>
    """
def _approved_pattern_id_lines(approved_patterns: list[object]) -> str:
    ids = [str(getattr(pattern, "id")) for pattern in approved_patterns]
    return "\n".join(ids[:5])
