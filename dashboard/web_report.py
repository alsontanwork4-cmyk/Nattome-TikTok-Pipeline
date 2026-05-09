from __future__ import annotations

import html
import re
from pathlib import Path
from urllib.parse import quote

from .report_view import ReportArtifact, load_selected_report
from .time_display import display_datetime
from .web_components import _render_empty_state

_SAFE_URL_CHARS = ":/?#[]@!$&'()*+,;=%"


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
      <h1>{html.escape(selected.display_title)}</h1>
      <p class="lede">Read-only view of the selected-batch snapshot for this pipeline run.</p>
      {_render_report_selector(artifacts, selected.run_id)}
      <article class="panel wide-panel report-reader" aria-label="Selected-batch snapshot">
        {_render_markdown(selected.markdown)}
      </article>
    """


def _render_report_selector(artifacts: list[ReportArtifact], selected_run_id: str) -> str:
    if len(artifacts) <= 1:
        return ""
    options = []
    for artifact in artifacts:
        selected = " selected" if artifact.run_id == selected_run_id else ""
        options.append(
            f'<option value="{html.escape(artifact.run_id)}"{selected}>{html.escape(artifact.display_title)}</option>'
        )
    return f"""
      <section class="panel report-selector" aria-label="Snapshot selector">
        <form method="get" action="/report">
          <label class="field-label">
            Choose snapshot
            <select name="run_id" onchange="this.form.submit()">
              {"".join(options)}
            </select>
          </label>
          <noscript><button type="submit">Open snapshot</button></noscript>
        </form>
      </section>
    """


def _render_markdown(markdown: str) -> str:
    blocks: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    ordered_items: list[str] = []
    table_rows: list[str] = []
    code_lines: list[str] = []
    in_code = False

    def flush_paragraph() -> None:
        if paragraph:
            blocks.append(f"<p>{_inline(' '.join(paragraph))}</p>")
            paragraph.clear()

    def flush_list() -> None:
        if list_items:
            blocks.append("<ul>" + "".join(f"<li>{_inline(item)}</li>" for item in list_items) + "</ul>")
            list_items.clear()
        if ordered_items:
            blocks.append("<ol>" + "".join(f"<li>{_inline(item)}</li>" for item in ordered_items) + "</ol>")
            ordered_items.clear()

    def flush_table() -> None:
        if not table_rows:
            return
        rows = [_table_cells(row) for row in table_rows if not _is_table_separator(row)]
        if rows:
            head = rows[0]
            body = rows[1:]
            header = "<thead><tr>" + "".join(f"<th>{_inline(cell)}</th>" for cell in head) + "</tr></thead>"
            body_markup = "".join(
                "<tr>" + "".join(f"<td>{_inline(cell)}</td>" for cell in row) + "</tr>"
                for row in body
            )
            blocks.append(f'<div class="table-scroll report-table"><table class="data-table">{header}<tbody>{body_markup}</tbody></table></div>')
        table_rows.clear()

    def flush_code() -> None:
        if code_lines:
            blocks.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
            code_lines.clear()

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if line.startswith("```"):
            if in_code:
                flush_code()
                in_code = False
            else:
                flush_paragraph()
                flush_list()
                flush_table()
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue
        if not line.strip():
            flush_paragraph()
            flush_list()
            flush_table()
            continue
        if _is_table_line(line):
            flush_paragraph()
            flush_list()
            table_rows.append(line)
            continue
        flush_table()
        heading_level = _heading_level(line)
        if heading_level:
            flush_paragraph()
            flush_list()
            text = line[heading_level:].strip()
            html_level = min(heading_level + 1, 4)
            blocks.append(f"<h{html_level}>{_inline(text)}</h{html_level}>")
            continue
        unordered = re.match(r"^\s*[-*]\s+(.+)$", line)
        if unordered:
            flush_paragraph()
            if ordered_items:
                flush_list()
            list_items.append(unordered.group(1))
            continue
        ordered = re.match(r"^\s*\d+[.)]\s+(.+)$", line)
        if ordered:
            flush_paragraph()
            if list_items:
                flush_list()
            ordered_items.append(ordered.group(1))
            continue
        paragraph.append(line.strip())

    flush_paragraph()
    flush_list()
    flush_table()
    flush_code()
    return "\n".join(blocks)


def _heading_level(line: str) -> int:
    match = re.match(r"^(#{1,6})\s+", line)
    return len(match.group(1)) if match else 0


def _is_table_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2


def _is_table_separator(line: str) -> bool:
    return all(char in "|:- " for char in line.strip())


def _table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _inline(text: str) -> str:
    escaped = html.escape(_localize_datetimes(text))
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    return re.sub(
        r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
        lambda match: (
            f'<a href="{quote(match.group(2), safe=_SAFE_URL_CHARS)}" '
            f'target="_blank" rel="noopener">{match.group(1)}</a>'
        ),
        escaped,
    )


def _localize_datetimes(text: str) -> str:
    return re.sub(
        r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})\b",
        lambda match: display_datetime(match.group(0)),
        text,
    )
