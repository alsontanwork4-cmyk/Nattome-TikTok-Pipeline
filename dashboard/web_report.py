from __future__ import annotations

from pathlib import Path

from .markdown import render_markdown
from .report_view import ReportArtifact, load_selected_report
from .web_components import _render_empty_state


def _render_report_page(
    workspace: Path,
    *,
    requested_run_id: str = "",
) -> str:
    selected, artifacts = load_selected_report(workspace, requested_run_id=requested_run_id)
    if selected is None:
        return f"""
      <h1>Report</h1>
      <p class="lede">The selected-batch snapshot will appear here after a full pipeline run writes the source-video boundary artifacts.</p>
      <section class="panel wide-panel">
        {_render_empty_state("report", "No selected-batch snapshot found", "Run the full pipeline to generate source-video snapshots.")}
      </section>
    """

    return f"""
      <h1>{_escape(selected.display_title)}</h1>
      <p class="lede">Read-only view of the selected-batch snapshot for this pipeline run.</p>
      {_render_report_selector(artifacts, selected.run_id)}
      <article class="panel wide-panel report-reader" aria-label="Selected-batch snapshot">
        {render_markdown(selected.markdown)}
      </article>
    """


def _render_report_selector(artifacts: list[ReportArtifact], selected_run_id: str) -> str:
    if len(artifacts) <= 1:
        return ""
    options = []
    for artifact in artifacts:
        selected = " selected" if artifact.run_id == selected_run_id else ""
        options.append(
            f'<option value="{_escape(artifact.run_id)}"{selected}>{_escape(artifact.display_title)}</option>'
        )
    return f"""
      <section class="panel report-selector" aria-label="Snapshot selector">
        <form method="get" action="/report">
          <label class="field-label">
            Choose snapshot
            <select name="run_id" data-auto-submit>
              {"".join(options)}
            </select>
          </label>
          <noscript><button type="submit">Open snapshot</button></noscript>
        </form>
      </section>
    """


def _escape(value: object) -> str:
    import html

    return html.escape(str(value))
