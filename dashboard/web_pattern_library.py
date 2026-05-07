from __future__ import annotations

import html
from pathlib import Path

from .pattern_library import generate_candidate_patterns, list_approved_patterns, list_pattern_versions
from .web_components import _input_field, _metadata_item, _render_empty_state, _render_page_header, _textarea_field

def _render_pattern_library(workspace: Path) -> str:
    candidates = generate_candidate_patterns(workspace)
    approved_patterns = list_approved_patterns(workspace)
    candidate_body = (
        "".join(_render_candidate_pattern(candidate) for candidate in candidates)
        if candidates
        else '<p class="muted">No candidate patterns have been generated from indexed run analysis yet.</p>'
    )
    approved_body = (
        "".join(_render_approved_pattern(workspace, pattern) for pattern in approved_patterns)
        if approved_patterns
        else '<p class="muted">No approved patterns have been curated yet.</p>'
    )
    return f"""
      <h1>Pattern Library</h1>
      <p class="lede">External TikTok mechanics stay separate from Nattome interpretation: generated candidates on one side, marketer-approved canonical patterns on the other.</p>
      <div class="actions" aria-label="Pattern exports">
        <a class="action-link" href="/exports/approved-patterns.md">Export approved patterns Markdown</a>
      </div>
      <section class="panel wide-panel">
        <h2>Candidate Patterns</h2>
        <div class="pattern-list" aria-label="Candidate patterns">
          {candidate_body}
        </div>
      </section>
      <section class="panel wide-panel">
        <h2>Approved Patterns</h2>
        <div class="pattern-list" aria-label="Approved patterns">
          {approved_body}
        </div>
      </section>
      <section class="panel wide-panel">
        <h2>Create Approved Pattern</h2>
        {_render_pattern_create_form()}
      </section>
    """


def _render_candidate_pattern(candidate: object) -> str:
    return f"""
      <article class="panel">
        <div class="pattern-header">
          <div>
            <h3>{html.escape(str(getattr(candidate, "pattern_name")))}</h3>
            <p>{html.escape(str(getattr(candidate, "why_it_works")))}</p>
          </div>
          <span class="status-pill">{html.escape(str(getattr(candidate, "status")))}</span>
        </div>
        <dl class="metadata-grid">
          {_metadata_item("Hook Type", str(getattr(candidate, "hook_type")))}
          {_metadata_item("Format Type", str(getattr(candidate, "format_type")))}
          {_metadata_item("Emotional Trigger", str(getattr(candidate, "emotional_trigger")))}
          {_metadata_item("Source Run", str(getattr(candidate, "source_run_id") or "Not linked"))}
        </dl>
        {_render_pattern_sources(getattr(candidate, "source_videos"))}
        {_render_pattern_evidence(getattr(candidate, "performance_evidence"))}
        <form class="pattern-form" method="post" action="/pattern-library/approve">
          <input type="hidden" name="candidate_id" value="{getattr(candidate, "id")}">
          <div class="pattern-form-grid">
            {_input_field("User", "user", "local")}
            {_input_field("Approval notes", "notes", "")}
          </div>
          <button type="submit">Approve candidate</button>
        </form>
      </article>
    """


def _render_approved_pattern(workspace: Path, pattern: object) -> str:
    versions = list_pattern_versions(workspace, getattr(pattern, "id"))
    return f"""
      <article class="panel">
        <div class="pattern-header">
          <div>
            <h3>{html.escape(str(getattr(pattern, "pattern_name")))}</h3>
            <p>{html.escape(str(getattr(pattern, "why_it_works")))}</p>
          </div>
          <span class="status-pill">{html.escape(str(getattr(pattern, "status")))} v{getattr(pattern, "version")}</span>
        </div>
        <dl class="metadata-grid">
          {_metadata_item("Hook Type", str(getattr(pattern, "hook_type")))}
          {_metadata_item("Format Type", str(getattr(pattern, "format_type")))}
          {_metadata_item("Emotional Trigger", str(getattr(pattern, "emotional_trigger")))}
          {_metadata_item("Freshness", str(getattr(pattern, "freshness") or "Not set"))}
          {_metadata_item("Shoot Difficulty", str(getattr(pattern, "shoot_difficulty") or "Not set"))}
          {_metadata_item("Related POVs", ", ".join(getattr(pattern, "related_povs") or []) or "None")}
          {_metadata_item("Targeting", _targeting_text(getattr(pattern, "targeting")))}
          {_metadata_item("Updated By", str(getattr(pattern, "updated_by")))}
        </dl>
        {_render_pattern_sources(getattr(pattern, "source_videos"))}
        <h3>Nattome adaptation notes</h3>
        <p>{html.escape(str(getattr(pattern, "nattome_adaptation_notes") or "Not set"))}</p>
        <h3>Avoid notes</h3>
        <p>{html.escape(str(getattr(pattern, "avoid_notes") or "None"))}</p>
        {_render_pattern_evidence(getattr(pattern, "performance_evidence"))}
        {_render_pattern_versions(versions)}
        {_render_pattern_edit_form(pattern)}
        {_render_pattern_archive_form(pattern)}
      </article>
    """


def _render_pattern_sources(source_videos: object) -> str:
    if not isinstance(source_videos, list) or not source_videos:
        return '<p class="muted">No source videos linked.</p>'
    items = []
    for video in source_videos[:8]:
        if not isinstance(video, dict):
            continue
        video_id = str(video.get("video_id") or "source")
        url = str(video.get("tiktok_url") or "")
        caption = str(video.get("caption") or "")
        source = f' <a href="{html.escape(url)}">{html.escape(url)}</a>' if url else ""
        items.append(f"<li><strong>{html.escape(video_id)}</strong>{source}<br>{html.escape(caption)}</li>")
    return f"""
      <h3>Source videos</h3>
      <ul class="compact-list">{"".join(items)}</ul>
    """


def _render_pattern_evidence(evidence: object) -> str:
    if not isinstance(evidence, dict) or not evidence:
        return '<p class="muted">No performance evidence recorded.</p>'
    items = [
        f"<li>{html.escape(str(key).replace('_', ' ').title())}: {html.escape(str(value))}</li>"
        for key, value in evidence.items()
    ]
    return f"""
      <h3>Performance evidence</h3>
      <ul class="compact-list">{"".join(items)}</ul>
    """


def _render_pattern_versions(versions: list[object]) -> str:
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


def _render_pattern_create_form() -> str:
    return f"""
      <form class="pattern-form" method="post" action="/pattern-library/create">
        <div class="pattern-form-grid">
          {_input_field("Pattern name", "pattern_name", "")}
          {_input_field("Hook type", "hook_type", "")}
          {_input_field("Format type", "format_type", "")}
          {_input_field("Emotional trigger", "emotional_trigger", "")}
          {_input_field("Shoot difficulty", "shoot_difficulty", "")}
          {_input_field("Freshness", "freshness", "")}
          {_input_field("Target market", "target_market", "")}
          {_input_field("Target persona", "target_persona", "")}
          {_textarea_field("Source videos", "source_videos", "")}
          {_textarea_field("Why it works", "why_it_works", "")}
          {_textarea_field("Nattome adaptation notes", "nattome_adaptation_notes", "")}
          {_textarea_field("Related POVs", "related_povs", "")}
          {_textarea_field("Avoid notes", "avoid_notes", "")}
          {_input_field("User", "user", "local")}
        </div>
        <button type="submit">Create approved pattern</button>
      </form>
    """


def _render_pattern_edit_form(pattern: object) -> str:
    return f"""
      <form class="pattern-form" method="post" action="/pattern-library/edit">
        <input type="hidden" name="pattern_id" value="{getattr(pattern, "id")}">
        <div class="pattern-form-grid">
          {_input_field("Pattern name", "pattern_name", getattr(pattern, "pattern_name"))}
          {_input_field("Hook type", "hook_type", getattr(pattern, "hook_type"))}
          {_input_field("Format type", "format_type", getattr(pattern, "format_type"))}
          {_input_field("Emotional trigger", "emotional_trigger", getattr(pattern, "emotional_trigger"))}
          {_input_field("Status", "status", getattr(pattern, "status"))}
          {_input_field("Shoot difficulty", "shoot_difficulty", getattr(pattern, "shoot_difficulty"))}
          {_input_field("Freshness", "freshness", getattr(pattern, "freshness"))}
          {_input_field("Target market", "target_market", _targeting_field(getattr(pattern, "targeting"), "market"))}
          {_input_field("Target persona", "target_persona", _targeting_field(getattr(pattern, "targeting"), "persona"))}
          {_textarea_field("Source videos", "source_videos", _source_video_lines(getattr(pattern, "source_videos")))}
          {_textarea_field("Why it works", "why_it_works", getattr(pattern, "why_it_works"))}
          {_textarea_field("Nattome adaptation notes", "nattome_adaptation_notes", getattr(pattern, "nattome_adaptation_notes"))}
          {_textarea_field("Related POVs", "related_povs", "\n".join(getattr(pattern, "related_povs") or []))}
          {_textarea_field("Avoid notes", "avoid_notes", getattr(pattern, "avoid_notes"))}
          {_input_field("User", "user", "local")}
        </div>
        <button type="submit">Save pattern</button>
      </form>
    """


def _render_pattern_archive_form(pattern: object) -> str:
    if str(getattr(pattern, "status")) == "archived":
        return ""
    return f"""
      <form class="pattern-form" method="post" action="/pattern-library/archive">
        <input type="hidden" name="pattern_id" value="{getattr(pattern, "id")}">
        {_input_field("User", "user", "local")}
        <button type="submit">Archive pattern</button>
      </form>
    """
def _source_video_lines(source_videos: object) -> str:
    if not isinstance(source_videos, list):
        return ""
    lines = []
    for video in source_videos:
        if not isinstance(video, dict):
            continue
        lines.append(f"{video.get('video_id') or ''}|{video.get('tiktok_url') or ''}")
    return "\n".join(lines)


def _targeting_text(targeting: object) -> str:
    if not isinstance(targeting, dict) or not targeting:
        return "None"
    items = [f"{key}: {value}" for key, value in targeting.items() if value]
    return ", ".join(items) if items else "None"


def _targeting_field(targeting: object, key: str) -> str:
    return str(targeting.get(key) or "") if isinstance(targeting, dict) else ""
