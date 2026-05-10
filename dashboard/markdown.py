from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

from batch_analysis.config import run_folder_timezone

_SAFE_URL_CHARS = ":/?#[]@!$&'()*+,;=%"


def render_markdown(markdown: str) -> str:
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
            blocks.append(
                f'<div class="table-scroll report-table"><table class="data-table">{header}<tbody>{body_markup}</tbody></table></div>'
            )
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


def display_datetime(value: Any, *, fallback: str = "--") -> str:
    parsed = _parse_datetime(value)
    if parsed is None:
        text = str(value or "").strip()
        return text or fallback
    return parsed.astimezone(run_folder_timezone()).strftime("%Y-%m-%d %H:%M:%S %z")


def _parse_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, (int, float)):
        parsed = datetime.fromtimestamp(value, tz=timezone.utc)
    else:
        text = str(value).strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
