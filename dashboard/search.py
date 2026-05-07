from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .indexer import index_pipeline_artifacts
from .quality import NATTOME_TERMS, compute_scrape_quality_scores
from .store import DASHBOARD_DB_PATH, initialize_dashboard_store


@dataclass(frozen=True)
class SearchResult:
    record_type: str
    record_id: str
    title: str
    context: str
    url: str
    facets: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class SearchResponse:
    query: str
    selected_facets: dict[str, tuple[str, ...]]
    facets: dict[str, tuple[str, ...]]
    results: list[SearchResult]


def search_dashboard_records(
    workspace: Path | str = ".",
    *,
    query: str = "",
    facets: dict[str, list[str] | tuple[str, ...] | str] | None = None,
) -> SearchResponse:
    """Search indexed dashboard records and dashboard-owned mutable state."""
    workspace_path = Path(workspace)
    index_pipeline_artifacts(workspace_path)
    compute_scrape_quality_scores(workspace_path)
    selected_facets = _normalize_selected_facets(facets or {})
    records = _collect_records(workspace_path)
    query_filtered = [record for record in records if _matches_query(record, query)]
    filtered = [
        record
        for record in query_filtered
        if _matches_facets(record, selected_facets)
    ]
    return SearchResponse(
        query=query,
        selected_facets=selected_facets,
        facets=_available_facets(query_filtered),
        results=sorted(
            filtered,
            key=lambda result: (result.record_type, result.title.lower(), result.record_id),
        ),
    )


def _collect_records(workspace: Path) -> list[SearchResult]:
    db_path = initialize_dashboard_store(workspace)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        run_context = _run_context(connection)
        records: list[SearchResult] = []
        records.extend(_raw_video_records(connection, run_context))
        records.extend(_curation_records(connection, run_context))
        records.extend(_run_records(connection, run_context))
        records.extend(_pattern_records(connection, "candidate_patterns", "candidate_pattern"))
        records.extend(_pattern_records(connection, "approved_patterns", "approved_pattern"))
        records.extend(_pov_records(connection))
        records.extend(_report_records(connection, workspace, run_context))
        records.extend(_architecture_doc_records(connection, workspace))
        records.extend(_pipeline_phase_records(connection, run_context))
        return records
    finally:
        connection.close()


def _run_context(connection: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    context: dict[str, dict[str, Any]] = {}
    score_rows = {
        str(row["run_id"]): row
        for row in connection.execute("SELECT * FROM scrape_quality_scores")
    }
    for row in connection.execute("SELECT * FROM batch_runs"):
        manifest = _json_loads(row["raw_json"])
        run_id = str(row["run_id"])
        score = score_rows.get(run_id)
        context[run_id] = {
            "run_id": run_id,
            "run_date": _date_text(row["run_timestamp"]),
            "run_type": str(row["mode"] or "run"),
            "config_version": _config_version(manifest),
            "manifest": manifest,
            "score_band": str(score["band"] if score else ""),
            "run_timestamp": str(row["run_timestamp"] or ""),
        }
    for selected in connection.execute("SELECT * FROM selected_batches"):
        run_id = str(selected["run_id"])
        selected_json = _json_loads(selected["raw_json"])
        if run_id not in context:
            context[run_id] = {"run_id": run_id}
        context[run_id]["source_input"] = str(selected["candidate_source"] or "")
        if selected_json.get("config_version"):
            context[run_id]["config_version"] = str(selected_json["config_version"])
    return context


def _raw_video_records(
    connection: sqlite3.Connection,
    run_context: dict[str, dict[str, Any]],
) -> list[SearchResult]:
    rows = connection.execute(
        """
        SELECT
            raw_videos.*,
            video_curation.labels AS curation_labels,
            video_curation.note AS curation_note
        FROM raw_videos
        LEFT JOIN video_curation
            ON video_curation.tiktok_video_id = raw_videos.video_id
        """
    ).fetchall()
    records = []
    for row in rows:
        run_id = str(row["run_id"] or "")
        hashtags = _json_list(row["hashtags_json"])
        labels = _json_list(row["curation_labels"])
        context = _compact_text(
            row["caption"],
            row["author_handle"],
            " ".join(f"#{item}" for item in hashtags),
            row["source_input"],
            " ".join(labels),
            row["curation_note"],
            row["tiktok_url"],
            run_id,
        )
        records.append(
            SearchResult(
                record_type="raw_video",
                record_id=str(row["video_id"]),
                title=str(row["caption"] or row["video_id"] or "Untitled video"),
                context=context,
                url=str(row["tiktok_url"] or ""),
                facets=_facets(
                    {
                        **_run_facets(run_context.get(run_id, {})),
                        "record_type": "raw_video",
                        "video_status": str(row["selection_status"] or "raw"),
                        "label": labels,
                        "score_band": [
                            run_context.get(run_id, {}).get("score_band") or "",
                            _video_score_band(row, hashtags),
                        ],
                        "relevance_band": _relevance_band(row["caption"], hashtags, row["source_input"]),
                        "engagement_band": _engagement_band(row),
                        "freshness": _freshness(row["created_at"], run_context.get(run_id, {})),
                        "author": str(row["author_handle"] or ""),
                        "hashtag_topic": hashtags,
                        "source_input": str(row["source_input"] or ""),
                    }
                ),
            )
        )
    return records


def _curation_records(
    connection: sqlite3.Connection,
    run_context: dict[str, dict[str, Any]],
) -> list[SearchResult]:
    rows = connection.execute(
        """
        SELECT
            video_curation.*,
            raw_videos.caption,
            raw_videos.author_handle,
            raw_videos.run_id,
            raw_videos.source_input,
            raw_videos.hashtags_json,
            raw_videos.tiktok_url
        FROM video_curation
        LEFT JOIN raw_videos
            ON raw_videos.video_id = video_curation.tiktok_video_id
        """
    ).fetchall()
    records = []
    for row in rows:
        labels = _json_list(row["labels"])
        run_id = str(row["run_id"] or "")
        context = _compact_text(
            row["caption"],
            " ".join(labels),
            row["exclude_similar_reason"],
            row["note"],
            row["author_handle"],
        )
        records.append(
            SearchResult(
                record_type="curation",
                record_id=str(row["tiktok_video_id"]),
                title=f"Curation for {row['tiktok_video_id']}",
                context=context,
                url=str(row["tiktok_url"] or ""),
                facets=_facets(
                    {
                        **_run_facets(run_context.get(run_id, {})),
                        "record_type": "curation",
                        "label": labels,
                        "source_input": str(row["source_input"] or ""),
                        "hashtag_topic": _json_list(row["hashtags_json"]),
                    }
                ),
            )
        )
    return records


def _run_records(
    connection: sqlite3.Connection,
    run_context: dict[str, dict[str, Any]],
) -> list[SearchResult]:
    records = []
    for run in connection.execute("SELECT * FROM batch_runs"):
        run_id = str(run["run_id"])
        video_context = _run_video_context(connection, run_id)
        manifest = _json_loads(run["raw_json"])
        records.append(
            SearchResult(
                record_type="run",
                record_id=run_id,
                title=f"{str(run['mode'] or 'run').title()} run {run_id}",
                context=_compact_text(run_id, run["run_timestamp"], json.dumps(manifest), video_context),
                url=f"/run-history?run_id={run_id}",
                facets=_facets({**_run_facets(run_context.get(run_id, {})), "record_type": "run"}),
            )
        )
    return records


def _pattern_records(
    connection: sqlite3.Connection,
    table_name: str,
    record_type: str,
) -> list[SearchResult]:
    rows = connection.execute(f"SELECT * FROM {table_name}").fetchall()
    records = []
    for row in rows:
        payload = _json_loads(row["pattern_json"])
        fallback_name = str(row["name"]) if "name" in row.keys() else "Untitled pattern"
        pattern_name = str(payload.get("pattern_name") or fallback_name)
        context = _compact_text(pattern_name, row["status"], json.dumps(payload, ensure_ascii=True))
        targeting = payload.get("targeting") if isinstance(payload.get("targeting"), dict) else {}
        records.append(
            SearchResult(
                record_type=record_type,
                record_id=str(row["id"]),
                title=pattern_name,
                context=context,
                url="/pattern-library",
                facets=_facets(
                    {
                        "record_type": record_type,
                        "pattern": pattern_name,
                        "video_status": str(row["status"] or ""),
                        "freshness": str(payload.get("freshness") or ""),
                        "pov": _json_list(payload.get("related_povs")),
                        "market": str(targeting.get("market") or ""),
                    }
                ),
            )
        )
    return records


def _pov_records(connection: sqlite3.Connection) -> list[SearchResult]:
    rows = connection.execute("SELECT * FROM nattome_povs").fetchall()
    records = []
    for row in rows:
        payload = _json_loads(row["pov_json"])
        title = str(payload.get("title") or row["name"] or "Untitled Nattome POV")
        records.append(
            SearchResult(
                record_type="nattome_pov",
                record_id=str(row["id"]),
                title=title,
                context=_compact_text(title, row["status"], json.dumps(payload, ensure_ascii=True)),
                url="/nattome-pov-library",
                facets=_facets(
                    {
                        "record_type": "nattome_pov",
                        "pov": title,
                        "video_status": str(row["status"] or ""),
                        "market": str(payload.get("market") or ""),
                        "campaign": str(payload.get("campaign") or ""),
                        "product": str(payload.get("product") or ""),
                        "pattern": [str(item) for item in _json_list(payload.get("linked_pattern_ids"))],
                    }
                ),
            )
        )
    return records


def _report_records(
    connection: sqlite3.Connection,
    workspace: Path,
    run_context: dict[str, dict[str, Any]],
) -> list[SearchResult]:
    rows = connection.execute(
        """
        SELECT *
        FROM run_outputs
        WHERE artifact_type IN ('report_markdown', 'report_json', 'excel_workbook')
        """
    ).fetchall()
    records = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (str(row["run_id"]), str(row["artifact_path"]))
        if key in seen:
            continue
        seen.add(key)
        path = str(row["artifact_path"])
        content = _read_text(workspace / path)
        records.append(
            SearchResult(
                record_type="report",
                record_id=path,
                title=str(row["label"] or Path(path).name),
                context=_compact_text(path, row["artifact_type"], content),
                url=path,
                facets=_facets(
                    {
                        **_run_facets(run_context.get(str(row["run_id"]), {})),
                        "record_type": "report",
                    }
                ),
            )
        )
    return records


def _architecture_doc_records(connection: sqlite3.Connection, workspace: Path) -> list[SearchResult]:
    rows = connection.execute("SELECT * FROM documentation_records").fetchall()
    records = []
    for row in rows:
        path = str(row["path"])
        records.append(
            SearchResult(
                record_type="architecture_doc",
                record_id=path,
                title=str(row["title"]),
                context=_compact_text(path, row["doc_type"], _read_text(workspace / path)),
                url=path,
                facets=_facets(
                    {
                        "record_type": "architecture_doc",
                        "pipeline_phase": str(row["doc_type"]),
                    }
                ),
            )
        )
    return records


def _pipeline_phase_records(
    connection: sqlite3.Connection,
    run_context: dict[str, dict[str, Any]],
) -> list[SearchResult]:
    records = []
    for run in connection.execute("SELECT * FROM batch_runs"):
        run_id = str(run["run_id"])
        manifest = _json_loads(run["raw_json"])
        phases = manifest.get("phases") if isinstance(manifest, dict) else []
        if not isinstance(phases, list):
            continue
        for phase in phases:
            if not isinstance(phase, dict):
                continue
            name = str(phase.get("name") or "phase")
            status = str(phase.get("status") or "unknown")
            records.append(
                SearchResult(
                    record_type="pipeline_phase",
                    record_id=f"{run_id}:{name}",
                    title=f"{name.replace('_', ' ').title()} phase",
                    context=_compact_text(run_id, name, status, json.dumps(phase, ensure_ascii=True)),
                    url=f"/run-history?run_id={run_id}",
                    facets=_facets(
                        {
                            **_run_facets(run_context.get(run_id, {})),
                            "record_type": "pipeline_phase",
                            "pipeline_phase": name,
                            "pipeline_phase_status": status,
                        }
                    ),
                )
            )
    return records


def _run_facets(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_date": str(context.get("run_date") or ""),
        "run_type": str(context.get("run_type") or ""),
        "config_version": str(context.get("config_version") or ""),
        "source_input": str(context.get("source_input") or ""),
        "score_band": str(context.get("score_band") or ""),
    }


def _matches_query(result: SearchResult, query: str) -> bool:
    terms = [term for term in query.lower().split() if term]
    if not terms:
        return True
    haystack = " ".join([result.record_type, result.record_id, result.title, result.context]).lower()
    return all(term in haystack for term in terms)


def _matches_facets(
    result: SearchResult,
    selected_facets: dict[str, tuple[str, ...]],
) -> bool:
    for name, selected_values in selected_facets.items():
        if not selected_values:
            continue
        values = {value.lower() for value in result.facets.get(name, ())}
        if not any(value.lower() in values for value in selected_values):
            return False
    return True


def _available_facets(results: list[SearchResult]) -> dict[str, tuple[str, ...]]:
    available: dict[str, set[str]] = {}
    for result in results:
        for name, values in result.facets.items():
            clean_values = {value for value in values if value}
            if clean_values:
                available.setdefault(name, set()).update(clean_values)
    return {
        name: tuple(sorted(values, key=str.lower))
        for name, values in sorted(available.items())
    }


def _normalize_selected_facets(
    facets: dict[str, list[str] | tuple[str, ...] | str],
) -> dict[str, tuple[str, ...]]:
    normalized: dict[str, tuple[str, ...]] = {}
    for name, value in facets.items():
        if isinstance(value, str):
            values = [value]
        else:
            values = list(value)
        normalized[name] = tuple(str(item) for item in values if str(item))
    return normalized


def _facets(raw_facets: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    facets: dict[str, tuple[str, ...]] = {}
    for name, value in raw_facets.items():
        values = _value_list(value)
        if values:
            facets[name] = tuple(values)
    return facets


def _value_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        values = [str(item) for item in value if str(item)]
    else:
        values = [str(value)] if str(value) else []
    return sorted(set(values), key=str.lower)


def _json_loads(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        data = json.loads(str(value))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _json_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item)]
    if not value:
        return []
    try:
        data = json.loads(str(value))
    except json.JSONDecodeError:
        return [str(value)]
    if isinstance(data, list):
        return [str(item) for item in data if str(item)]
    return [str(data)] if str(data) else []


def _compact_text(*parts: Any) -> str:
    text = " ".join(str(part) for part in parts if part)
    return " ".join(text.split())


def _date_text(value: Any) -> str:
    text = str(value or "")
    return text[:10] if len(text) >= 10 else text


def _config_version(manifest: dict[str, Any]) -> str:
    config = manifest.get("configuration") if isinstance(manifest, dict) else {}
    if isinstance(config, dict):
        return str(config.get("version") or "")
    return ""


def _run_video_context(connection: sqlite3.Connection, run_id: str) -> str:
    rows = connection.execute(
        """
        SELECT caption, author_handle, source_input, hashtags_json
        FROM raw_videos
        WHERE run_id = ?
        """,
        (run_id,),
    ).fetchall()
    return _compact_text(
        *[
            _compact_text(row["caption"], row["author_handle"], row["source_input"], " ".join(_json_list(row["hashtags_json"])))
            for row in rows
        ]
    )


def _relevance_band(caption: Any, hashtags: list[str], source_input: Any) -> str:
    haystack = _compact_text(caption, " ".join(hashtags), source_input).lower()
    matches = sum(1 for term in NATTOME_TERMS if term in haystack)
    if matches >= 2:
        return "high relevance"
    if matches == 1:
        return "medium relevance"
    return "low relevance"


def _engagement_band(row: sqlite3.Row) -> str:
    views = max(_int_value(row["play_count"]), 1)
    engagement = (_int_value(row["like_count"]) + _int_value(row["comment_count"]) * 5 + _int_value(row["share_count"]) * 10) / views
    if engagement >= 0.08:
        return "high engagement"
    if engagement >= 0.03:
        return "medium engagement"
    return "low engagement"


def _video_score_band(row: sqlite3.Row, hashtags: list[str]) -> str:
    relevance = _relevance_band(row["caption"], hashtags, row["source_input"])
    engagement = _engagement_band(row)
    if relevance == "high relevance" and engagement == "high engagement":
        return "strong scrape"
    if relevance != "low relevance" and engagement != "low engagement":
        return "usable scrape"
    return "needs attention"


def _freshness(created_at: Any, context: dict[str, Any]) -> str:
    created = _parse_datetime(created_at)
    run_timestamp = _parse_datetime(context.get("run_timestamp"))
    if created is None or run_timestamp is None:
        return "undated"
    age_days = max((run_timestamp - created).total_seconds() / 86400, 0.0)
    if age_days <= 14:
        return "fresh"
    if age_days <= 45:
        return "aging"
    return "stale"


def _parse_datetime(value: Any) -> datetime | None:
    text = str(value or "")
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _read_text(path: Path) -> str:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return path.name
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""
