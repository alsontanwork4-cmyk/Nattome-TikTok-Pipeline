from __future__ import annotations

import html
from pathlib import Path

from .architecture import load_pipeline_architecture
from .web_components import _render_empty_state, _render_page_header

def _render_pipeline_architecture(workspace: Path) -> str:
    architecture = load_pipeline_architecture(workspace)
    return f"""
      <h1>Pipeline Architecture</h1>
      <p class="lede">Scrape to score to select to analyze to report. This read-only view links the docs, decisions, indexed run phases, outputs, and data lineage behind the Nattome TikTok discovery pipeline.</p>
      <section class="panel wide-panel" aria-label="Pipeline flow">
        <h2>High-Level Flow</h2>
        {_render_architecture_flow(architecture.pipeline_flow)}
      </section>
      <section class="grid" aria-label="Architecture decisions and status">
        <article class="panel">
          <h2>Tool Stack and Decisions</h2>
          {_render_tool_decisions(architecture.tool_decisions)}
        </article>
        <article class="panel">
          <h2>Phase Status Map</h2>
          {_render_phase_statuses(architecture.phase_statuses)}
        </article>
        <article class="panel">
          <h2>Data Lineage</h2>
          {_render_lineage_steps(architecture.data_lineage)}
        </article>
      </section>
      <section class="panel wide-panel" aria-label="File and output map">
        <h2>File and Output Map</h2>
        {_render_file_output_map(architecture.file_output_map)}
      </section>
      <section class="panel wide-panel" aria-label="Indexed architecture docs">
        <h2>Indexed Architecture Docs</h2>
        {_render_architecture_documents(architecture.documents)}
      </section>
    """


def _render_architecture_flow(steps: list[object]) -> str:
    items = [
        f"<li><strong>{html.escape(getattr(step, 'name'))}</strong>: {html.escape(getattr(step, 'summary'))}</li>"
        for step in steps
    ]
    return f'<ol class="compact-list">{"".join(items)}</ol>'


def _render_tool_decisions(decisions: list[object]) -> str:
    if not decisions:
        return '<p class="muted">No tool decisions are available.</p>'
    items = [
        f"<li><strong>{html.escape(getattr(decision, 'name'))}</strong>: {html.escape(getattr(decision, 'summary'))}</li>"
        for decision in decisions
    ]
    return f'<ul class="compact-list">{"".join(items)}</ul>'


def _render_phase_statuses(phases: list[object]) -> str:
    if not phases:
        return '<p class="muted">No indexed phase metadata is available.</p>'
    items = []
    for phase in phases:
        detail = getattr(phase, "detail")
        detail_markup = f' <span class="muted">{html.escape(detail)}</span>' if detail else ""
        run_id = getattr(phase, "run_id")
        run_markup = f' <code>{html.escape(run_id)}</code>' if run_id else ""
        items.append(
            f"<li><strong>{html.escape(getattr(phase, 'name'))}</strong>: {html.escape(getattr(phase, 'status'))}{run_markup}{detail_markup}</li>"
        )
    return f'<ul class="compact-list">{"".join(items)}</ul>'


def _render_lineage_steps(steps: list[object]) -> str:
    if not steps:
        return '<p class="muted">No lineage data is available.</p>'
    items = []
    for step in steps:
        path = getattr(step, "path")
        path_markup = f' <code>{html.escape(path)}</code>' if path else ""
        items.append(
            f"<li><strong>{html.escape(getattr(step, 'name'))}</strong>: {html.escape(getattr(step, 'status'))}{path_markup}<br><span class=\"muted\">{html.escape(getattr(step, 'summary'))}</span></li>"
        )
    return f'<ul class="compact-list">{"".join(items)}</ul>'


def _render_file_output_map(file_output_map: dict[str, list[str]]) -> str:
    sections = []
    for label, paths in file_output_map.items():
        if not paths:
            body = '<p class="muted">No indexed files.</p>'
        else:
            body = '<ul class="compact-list">' + "".join(
                f"<li><code>{html.escape(path)}</code></li>"
                for path in paths[:12]
            ) + "</ul>"
            if len(paths) > 12:
                body += f'<p class="muted">+{len(paths) - 12} more indexed files</p>'
        sections.append(f"<article><h3>{html.escape(label)}</h3>{body}</article>")
    return f'<div class="grid">{"".join(sections)}</div>'


def _render_architecture_documents(documents: list[object]) -> str:
    if not documents:
        return '<p class="muted">No README, CONTEXT, PRD, ADR, or skill docs have been indexed.</p>'
    items = [
        f"<li><strong>{html.escape(getattr(doc, 'title'))}</strong> <span class=\"muted\">{html.escape(getattr(doc, 'doc_type'))}</span><br><code>{html.escape(getattr(doc, 'path'))}</code></li>"
        for doc in documents
    ]
    return f'<ul class="compact-list">{"".join(items)}</ul>'
