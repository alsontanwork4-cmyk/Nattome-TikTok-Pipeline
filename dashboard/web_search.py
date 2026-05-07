from __future__ import annotations

import html
from pathlib import Path
from urllib.parse import urlencode

from .search import SearchResponse, search_dashboard_records
from .web_components import _first_form_value, _render_empty_state, _render_page_header

def _render_search(workspace: Path, query_params: dict[str, list[str]]) -> str:
    normalized_query = _normalize_query_params(query_params)
    search_query = _first_form_value(normalized_query, "q")
    selected_facets = {
        key: values
        for key, values in normalized_query.items()
        if key != "q" and values
    }
    response = search_dashboard_records(
        workspace,
        query=search_query,
        facets=selected_facets,
    )
    return f"""
      <h1>Global Search</h1>
      <p class="lede">Search indexed dashboard records and combine facets across videos, runs, curation, patterns, POVs, reports, and docs.</p>
      <section class="panel wide-panel" aria-label="Global dashboard search form">
        {_render_search_form(response)}
      </section>
      <section class="panel wide-panel" aria-label="Global search results">
        <h2>Results</h2>
        {_render_search_results(response)}
      </section>
    """


def _normalize_query_params(query_params: dict[str, object]) -> dict[str, list[str]]:
    normalized: dict[str, list[str]] = {}
    for key, value in query_params.items():
        if isinstance(value, list):
            normalized[key] = [str(item) for item in value]
        elif isinstance(value, tuple):
            normalized[key] = [str(item) for item in value]
        else:
            normalized[key] = [str(value)]
    return normalized


def _render_search_form(response: SearchResponse) -> str:
    facet_controls = "".join(
        _render_facet_group(response, facet_name)
        for facet_name in [
            "record_type",
            "run_date",
            "run_type",
            "config_version",
            "source_input",
            "video_status",
            "label",
            "score_band",
            "relevance_band",
            "engagement_band",
            "freshness",
            "author",
            "hashtag_topic",
            "pattern",
            "pov",
            "market",
            "campaign",
            "product",
            "pipeline_phase",
            "pipeline_phase_status",
        ]
        if response.facets.get(facet_name)
    )
    return f"""
      <form class="search-form" method="get" action="/search">
        <label class="field-label">
          Keyword
          <input type="search" name="q" value="{html.escape(response.query)}">
        </label>
        <div class="facet-grid">
          {facet_controls}
        </div>
        <button type="submit">Search</button>
      </form>
    """


def _render_facet_group(response: SearchResponse, facet_name: str) -> str:
    values = response.facets.get(facet_name, ())
    selected = set(response.selected_facets.get(facet_name, ()))
    checkboxes = []
    for value in values[:12]:
        checked = " checked" if value in selected else ""
        checkboxes.append(
            f"""
            <label class="check-label">
              <input type="checkbox" name="{html.escape(facet_name)}" value="{html.escape(value)}"{checked}>
              {html.escape(value)}
            </label>
            """
        )
    return f"""
      <fieldset>
        <legend>{html.escape(facet_name.replace("_", " ").title())}</legend>
        <div class="label-grid">{"".join(checkboxes)}</div>
      </fieldset>
    """


def _render_search_results(response: SearchResponse) -> str:
    if not response.results:
        return '<p class="muted">No matching dashboard records found.</p>'
    return f"""
      <div class="search-result-list">
        {"".join(_render_search_result(result) for result in response.results)}
      </div>
    """


def _render_search_result(result: object) -> str:
    url = str(getattr(result, "url"))
    link = (
        f'<a href="{html.escape(url)}">Open</a>'
        if url
        else '<span class="muted">No direct link</span>'
    )
    facet_text = _search_result_facet_text(getattr(result, "facets"))
    return f"""
      <article class="panel">
        <div class="search-result-header">
          <div>
            <span class="status-pill">{html.escape(str(getattr(result, "record_type")).replace("_", " "))}</span>
            <h3>{html.escape(str(getattr(result, "title")))}</h3>
          </div>
          {link}
        </div>
        <p>{html.escape(str(getattr(result, "context"))[:360])}</p>
        <p class="muted">{html.escape(facet_text)}</p>
      </article>
    """


def _search_result_facet_text(facets: dict[str, tuple[str, ...]]) -> str:
    parts = []
    for name in ["run_date", "run_type", "config_version", "video_status", "label", "pattern", "pov", "pipeline_phase_status"]:
        values = facets.get(name)
        if values:
            parts.append(f"{name.replace('_', ' ')}: {', '.join(values)}")
    return " | ".join(parts)
