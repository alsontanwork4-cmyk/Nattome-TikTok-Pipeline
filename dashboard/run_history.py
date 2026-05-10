from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .manual_runs import list_manual_runs
from .refresh import refresh_dashboard_derivatives
from .scoring import nattome_relevance, weighted_engagement
from .store import connect_dashboard_store


@dataclass(frozen=True)
class RunOutputLink:
    label: str
    artifact_type: str
    path: str
    exists_on_disk: bool


@dataclass(frozen=True)
class RunHistoryRow:
    run_id: str
    timestamp: str
    run_type: str
    source_type: str
    triggered_by: str
    config_version: str
    raw_candidates: int
    eligible_candidates: int
    selected_count: int
    average_nattome_relevance: float
    average_engagement: float
    top_issue: str
    output_links: list[RunOutputLink]
    status: str = ""


@dataclass(frozen=True)
class RunContentItem:
    video_id: str
    caption: str
    author_handle: str
    selection_status: str
    tiktok_url: str


@dataclass(frozen=True)
class RunHistoryDetail:
    row: RunHistoryRow
    raw_content: list[RunContentItem]
    selected_content: list[RunContentItem]
    videos: list[dict[str, Any]]
    selected_video_ids: set[str]
    pipeline_phases: list[dict[str, Any]]
    logs: list[str]
    output_links: list[RunOutputLink]
    selection_config: dict[str, Any]


@dataclass(frozen=True)
class RunHistory:
    rows: list[RunHistoryRow]


def load_run_history(workspace: Path | str = ".") -> RunHistory:
    workspace_path = Path(workspace)
    _refresh_derived_dashboard_data(workspace_path)
    connection = connect_dashboard_store(workspace_path)
    try:
        scheduled_rows = [
            _scheduled_run_row(connection, row)
            for row in connection.execute(
                """
                SELECT *
                FROM batch_runs
                ORDER BY COALESCE(run_timestamp, '') DESC, run_id DESC
                """
            )
        ]
        manual_rows = [_manual_run_row(run) for run in list_manual_runs(workspace_path)]
        rows = sorted(
            [*scheduled_rows, *manual_rows],
            key=lambda row: (row.timestamp, row.run_id),
            reverse=True,
        )
        return RunHistory(rows=rows)
    finally:
        connection.close()


def load_run_history_detail(workspace: Path | str, run_id: str) -> RunHistoryDetail:
    workspace_path = Path(workspace)
    history = load_run_history(workspace_path)
    row = next((candidate for candidate in history.rows if candidate.run_id == run_id), None)
    if row is None:
        raise ValueError(f"run not found: {run_id}")
    connection = connect_dashboard_store(workspace_path)
    try:
        run = connection.execute("SELECT * FROM batch_runs WHERE run_id = ?", (run_id,)).fetchone()
        if run is None:
            return RunHistoryDetail(
                row=row,
                raw_content=[],
                selected_content=[],
                videos=[],
                selected_video_ids=set(),
                pipeline_phases=[],
                logs=[],
                output_links=row.output_links,
                selection_config={},
            )
        selected = _selected_batch(connection, run_id)
        raw_videos = _candidate_videos(connection, run_id, selected)
        selected_ids = _selected_video_ids(selected)
        manifest = _json_loads(run["raw_json"])
        videos_with_curation = _videos_with_curation(connection, raw_videos)
        return RunHistoryDetail(
            row=row,
            raw_content=[_content_item(video) for video in raw_videos],
            selected_content=[
                _content_item(video)
                for video in raw_videos
                if video["video_id"] in selected_ids or video["selection_status"] in {"selected", "analyzed"}
            ],
            videos=videos_with_curation,
            selected_video_ids=selected_ids,
            pipeline_phases=_phase_list(manifest),
            logs=[link.path for link in row.output_links if link.artifact_type == "log"],
            output_links=row.output_links,
            selection_config=_selection_config(manifest),
        )
    finally:
        connection.close()


def _videos_with_curation(
    connection: sqlite3.Connection,
    raw_videos: list[sqlite3.Row],
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for video in raw_videos:
        curation = connection.execute(
            """
            SELECT labels, exclude_similar_reason, note
            FROM video_curation
            WHERE tiktok_video_id = ?
            """,
            (video["video_id"],),
        ).fetchone()
        record = dict(video)
        record["curation_labels"] = curation["labels"] if curation else None
        record["exclude_similar_reason"] = curation["exclude_similar_reason"] if curation else ""
        record["curation_note"] = curation["note"] if curation else ""
        enriched.append(record)
    return enriched


def _selection_config(manifest: dict[str, Any]) -> dict[str, Any]:
    configuration = manifest.get("configuration")
    if not isinstance(configuration, dict):
        return {}
    selection = configuration.get("selection")
    return selection if isinstance(selection, dict) else {}


def _refresh_derived_dashboard_data(workspace: Path) -> None:
    refresh_dashboard_derivatives(workspace, intent="run_history", scope="all")


def _scheduled_run_row(connection: sqlite3.Connection, run: sqlite3.Row) -> RunHistoryRow:
    run_id = str(run["run_id"])
    selected = _selected_batch(connection, run_id)
    videos = _candidate_videos(connection, run_id, selected)
    selected_json = _json_loads(selected["raw_json"]) if selected else {}
    raw_candidates = _positive_int(selected_json.get("input_candidate_count"), len(videos))
    eligible_candidates = _positive_int(
        selected_json.get("eligible_candidate_count"),
        sum(1 for video in videos if video["selection_status"] in {"eligible", "selected", "analyzed"}),
    )
    selected_count = _positive_int(
        selected_json.get("selected_candidate_count"),
        int(selected["selected_candidate_count"]) if selected else 0,
    )
    manifest = _json_loads(run["raw_json"])
    return RunHistoryRow(
        run_id=run_id,
        timestamp=str(run["run_timestamp"] or ""),
        run_type=f"scheduled {str(run['mode'] or 'run').replace('_', ' ')}",
        source_type="scheduled",
        triggered_by="pipeline",
        config_version=_config_version(manifest, selected_json),
        raw_candidates=raw_candidates,
        eligible_candidates=eligible_candidates,
        selected_count=selected_count,
        average_nattome_relevance=_average([nattome_relevance(video) for video in videos]),
        average_engagement=_average([weighted_engagement(video) for video in videos]),
        top_issue=_top_issue(manifest),
        output_links=_output_links(connection, run_id),
    )


def _manual_run_row(run: object) -> RunHistoryRow:
    return RunHistoryRow(
        run_id=getattr(run, "run_id"),
        timestamp=getattr(run, "triggered_at"),
        run_type=f"manual {getattr(run, 'run_type').replace('_', ' ')}",
        source_type=getattr(run, "source_type"),
        triggered_by=getattr(run, "triggered_by"),
        config_version=getattr(run, "config_version"),
        raw_candidates=0,
        eligible_candidates=0,
        selected_count=0,
        average_nattome_relevance=0.0,
        average_engagement=0.0,
        top_issue=getattr(run, "error_text") or "Await indexed output metrics",
        output_links=[
            RunOutputLink(
                label=label.replace("_", " ").title(),
                artifact_type=label,
                path=path,
                exists_on_disk=False,
            )
            for label, path in getattr(run, "output_paths").items()
        ],
        status=getattr(run, "status"),
    )


def _selected_batch(connection: sqlite3.Connection, run_id: str) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM selected_batches WHERE run_id = ?",
        (run_id,),
    ).fetchone()


def _candidate_videos(
    connection: sqlite3.Connection,
    run_id: str,
    selected: sqlite3.Row | None,
) -> list[sqlite3.Row]:
    if selected and selected["candidate_source"]:
        rows = list(
            connection.execute(
                """
                SELECT *
                FROM raw_videos
                WHERE source_artifact_path = ?
                ORDER BY video_id
                """,
                (selected["candidate_source"],),
            )
        )
        if rows:
            return rows
    return list(
        connection.execute(
            """
            SELECT *
            FROM raw_videos
            WHERE run_id = ?
            ORDER BY video_id
            """,
            (run_id,),
        )
    )


def _selected_video_ids(selected: sqlite3.Row | None) -> set[str]:
    if selected is None:
        return set()
    selected_json = _json_loads(selected["raw_json"])
    candidates = selected_json.get("selected_candidates")
    if not isinstance(candidates, list):
        return set()
    return {
        str(candidate.get("id") or candidate.get("video_id") or "")
        for candidate in candidates
        if isinstance(candidate, dict)
    } - {""}


def _output_links(connection: sqlite3.Connection, run_id: str) -> list[RunOutputLink]:
    return [
        RunOutputLink(
            label=str(row["label"]),
            artifact_type=str(row["artifact_type"]),
            path=str(row["artifact_path"]),
            exists_on_disk=bool(row["exists_on_disk"]),
        )
        for row in connection.execute(
            """
            SELECT label, artifact_type, artifact_path, exists_on_disk
            FROM run_outputs
            WHERE run_id = ?
            ORDER BY artifact_type, artifact_path
            """,
            (run_id,),
        )
    ]


def _config_version(manifest: dict[str, Any], selected_json: dict[str, Any]) -> str:
    configuration = manifest.get("configuration")
    if not isinstance(configuration, dict):
        configuration = {}
    version = (
        configuration.get("version")
        or configuration.get("config_version")
        or selected_json.get("config_version")
        or selected_json.get("settings_version")
    )
    return str(version or "Not recorded")


def _top_issue(manifest: dict[str, Any]) -> str:
    for phase in _phase_list(manifest):
        status = str(phase.get("status") or "")
        if status not in {"failed", "error", "blocked"}:
            continue
        detail = phase.get("exception") or phase.get("exception_text") or phase.get("error") or phase.get("reason")
        if detail:
            return str(detail)
        phase_name = str(phase.get("name") or "Pipeline phase").replace("_", " ").title()
        return f"{phase_name} reported {status}"
    return "No blocking issue"


def _content_item(video: sqlite3.Row) -> RunContentItem:
    return RunContentItem(
        video_id=str(video["video_id"]),
        caption=str(video["caption"] or ""),
        author_handle=str(video["author_handle"] or ""),
        selection_status=str(video["selection_status"] or "raw"),
        tiktok_url=str(video["tiktok_url"] or ""),
    )


def _phase_list(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    phases = manifest.get("phases")
    if not isinstance(phases, list):
        return []
    return [phase for phase in phases if isinstance(phase, dict)]


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _json_loads(value: Any) -> Any:
    if not value:
        return {}
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {}


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default
