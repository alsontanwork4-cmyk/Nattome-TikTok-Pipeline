from __future__ import annotations

import html
from pathlib import Path

from .recommendations import VALID_RECOMMENDATION_STATUSES, generate_recommendations
from .web_components import _render_empty_state, _render_page_header

def _render_recommendations(workspace: Path) -> str:
    recommendations = generate_recommendations(workspace)
    if not recommendations:
        return """
      <h1>Passive Recommendations</h1>
      <p class="lede">No scrape-quality recommendations need attention.</p>
      <section class="panel">
        <h2>Recommendations</h2>
        <p class="muted">The current indexed scrape data does not have advisory recommendations.</p>
      </section>
    """
    return f"""
      <h1>Passive Recommendations</h1>
      <p class="lede">Advisory scrape-quality recommendations with supporting runs, videos, source inputs, labels, and config versions. Settings are never changed automatically.</p>
      <section class="recommendation-list" aria-label="Passive recommendations">
        {"".join(_render_recommendation(recommendation) for recommendation in recommendations)}
      </section>
    """


def _render_recommendation(recommendation: object) -> str:
    title = str(getattr(recommendation, "recommendation_type")).replace("_", " ").title()
    status = _display_recommendation_status(str(getattr(recommendation, "status")))
    return f"""
        <article class="panel">
          <div class="recommendation-header">
            <div>
              <h2>{html.escape(title)}</h2>
              <p>{html.escape(str(getattr(recommendation, "summary")))}</p>
            </div>
            <span class="status-pill">{html.escape(status)}</span>
          </div>
          {_render_recommendation_evidence(getattr(recommendation, "supporting_evidence"))}
          {_render_recommendation_status_form(getattr(recommendation, "id"), str(getattr(recommendation, "status")))}
        </article>
    """


def _render_recommendation_evidence(evidence: object) -> str:
    if not isinstance(evidence, list) or not evidence:
        return '<p class="muted">No supporting evidence recorded.</p>'
    items = []
    for item in evidence[:10]:
        if not isinstance(item, dict):
            continue
        items.append(f"<li>{html.escape(_evidence_text(item))}</li>")
    return f"""
      <h3>Supporting evidence</h3>
      <ul class="compact-list">{"".join(items)}</ul>
    """


def _evidence_text(item: dict[str, object]) -> str:
    entity_type = str(item.get("entity_type") or "evidence")
    if entity_type == "run":
        return f"Run {item.get('run_id')} scored {item.get('score')}: {item.get('message')}"
    if entity_type == "video":
        source = f" from {item.get('source_input')}" if item.get("source_input") else ""
        return f"Video {item.get('video_id')}{source}: {item.get('caption')}"
    if entity_type == "source_input":
        return (
            f"Source input {item.get('source_input')}: "
            f"{item.get('candidate_count')} candidates, {item.get('eligible_count')} eligible"
        )
    if entity_type == "label":
        note = f" Note: {item.get('note')}" if item.get("note") else ""
        exclude_reason = (
            f" Exclude similar reason: {item.get('exclude_similar_reason')}"
            if item.get("exclude_similar_reason")
            else ""
        )
        return f"Label {item.get('label')} on video {item.get('video_id')}.{note}{exclude_reason}"
    if entity_type == "config_version":
        return f"Config version {item.get('version')} used by run {item.get('run_id')}"
    return json.dumps(item, ensure_ascii=True, sort_keys=True)


def _render_recommendation_status_form(recommendation_id: int, active_status: str) -> str:
    options = []
    for status in sorted(VALID_RECOMMENDATION_STATUSES):
        selected = " selected" if status == active_status else ""
        options.append(
            f'<option value="{html.escape(status)}"{selected}>{html.escape(_display_recommendation_status(status))}</option>'
        )
    return f"""
      <form class="recommendation-form" method="post" action="/recommendations/status">
        <input type="hidden" name="recommendation_id" value="{recommendation_id}">
        <label class="field-label">
          Lifecycle state
          <select name="status">{"".join(options)}</select>
        </label>
        <label class="field-label">
          User
          <input type="text" name="user" value="local" maxlength="120">
        </label>
        <button type="submit">Update state</button>
      </form>
    """


def _display_recommendation_status(status: str) -> str:
    return status.replace("_", " ")
