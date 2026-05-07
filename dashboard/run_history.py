from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .health import compute_pipeline_health
from .indexer import index_pipeline_artifacts
from .manual_runs import list_manual_runs
from .quality import NATTOME_TERMS, compute_scrape_quality_scores
from .store import DASHBOARD_DB_PATH, initialize_dashboard_store


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
    scrape_quality_score: int | None
    raw_candidates: int
    eligible_candidates: int
    selected_count: int
    average_nattome_relevance: float
    average_engagement: float
    freshness_score: int | None
    duplicate_noise_score: int | None
    pipeline_health: str
    top_issue: str
    output_links: list[RunOutputLink]


@dataclass(frozen=True)
class RunTrendPoint:
    run_id: str
    timestamp: str
    score: int | None
    candidate_volume: int
    eligibility_yield: float
    average_relevance: float
    average_engagement: float
    config_version: str


@dataclass(frozen=True)
class ConfigOverlay:
    version: str
    first_seen_at: str
    run_id: str


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
    quality_drivers: list[dict[str, Any]]
    pipeline_phases: list[dict[str, Any]]
    logs: list[str]
    output_links: list[RunOutputLink]


@dataclass(frozen=True)
class RunHistory:
    rows: list[RunHistoryRow]
    trend_points: list[RunTrendPoint]
    config_overlays: list[ConfigOverlay]


def load_run_history(workspace: Path | str = ".") -> RunHistory:
    workspace_path = Path(workspace)
    _refresh_derived_dashboard_data(workspace_path)
    db_path = initialize_dashboard_store(workspace_path)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
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
        trend_points = [_trend_point(row) for row in reversed(scheduled_rows)]
        return RunHistory(
            rows=rows,
            trend_points=trend_points,
            config_overlays=_config_overlays(trend_points),
        )
    finally:
        connection.close()


def load_run_history_detail(workspace: Path | str, run_id: str) -> RunHistoryDetail:
    workspace_path = Path(workspace)
    history = load_run_history(workspace_path)
    row = next((candidate for candidate in history.rows if candidate.run_id == run_id), None)
    if row is None:
        raise ValueError(f"run not found: {run_id}")
    connection = sqlite3.connect(workspace_path / DASHBOARD_DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        run = connection.execute("SELECT * FROM batch_runs WHERE run_id = ?", (run_id,)).fetchone()
        if run is None:
            return RunHistoryDetail(
                row=row,
                raw_content=[],
                selected_content=[],
                quality_drivers=[],
                pipeline_phases=[],
                logs=[],
                output_links=row.output_links,
            )
        selected = _selected_batch(connection, run_id)
        raw_videos = _candidate_videos(connection, run_id, selected)
        selected_ids = _selected_video_ids(selected)
        score = connection.execute(
            "SELECT drivers_json FROM scrape_quality_scores WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        manifest = _json_loads(run["raw_json"])
        return RunHistoryDetail(
            row=row,
            raw_content=[_content_item(video) for video in raw_videos],
            selected_content=[
                _content_item(video)
                for video in raw_videos
                if video["video_id"] in selected_ids or video["selection_status"] in {"selected", "analyzed"}
            ],
            quality_drivers=_json_list(score["drivers_json"] if score else None),
            pipeline_phases=_phase_list(manifest),
            logs=[link.path for link in row.output_links if link.artifact_type == "log"],
            output_links=row.output_links,
        )
    finally:
        connection.close()


def _refresh_derived_dashboard_data(workspace: Path) -> None:
    index_pipeline_artifacts(workspace)
    compute_scrape_quality_scores(workspace)
    compute_pipeline_health(workspace)


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
    score = connection.execute(
        "SELECT * FROM scrape_quality_scores WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    health = connection.execute(
        "SELECT * FROM pipeline_health_summaries WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    manifest = _json_loads(run["raw_json"])
    return RunHistoryRow(
        run_id=run_id,
        timestamp=str(run["run_timestamp"] or ""),
        run_type=f"scheduled {str(run['mode'] or 'run').replace('_', ' ')}",
        source_type="scheduled",
        triggered_by="pipeline",
        config_version=_config_version(manifest, selected_json),
        scrape_quality_score=int(score["score"]) if score else None,
        raw_candidates=raw_candidates,
        eligible_candidates=eligible_candidates,
        selected_count=selected_count,
        average_nattome_relevance=_average([_nattome_relevance(video) for video in videos]),
        average_engagement=_average([_weighted_engagement(video) for video in videos]),
        freshness_score=int(score["freshness_score"]) if score else None,
        duplicate_noise_score=int(score["duplicate_noise_control_score"]) if score else None,
        pipeline_health=str(health["status"]) if health else "unknown",
        top_issue=_top_issue(health, score),
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
        scrape_quality_score=None,
        raw_candidates=0,
        eligible_candidates=0,
        selected_count=0,
        average_nattome_relevance=0.0,
        average_engagement=0.0,
        freshness_score=None,
        duplicate_noise_score=None,
        pipeline_health=getattr(run, "status"),
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
    )


def _trend_point(row: RunHistoryRow) -> RunTrendPoint:
    eligibility_yield = row.eligible_candidates / row.raw_candidates if row.raw_candidates else 0.0
    return RunTrendPoint(
        run_id=row.run_id,
        timestamp=row.timestamp,
        score=row.scrape_quality_score,
        candidate_volume=row.raw_candidates,
        eligibility_yield=eligibility_yield,
        average_relevance=row.average_nattome_relevance,
        average_engagement=row.average_engagement,
        config_version=row.config_version,
    )


def _config_overlays(points: list[RunTrendPoint]) -> list[ConfigOverlay]:
    overlays: list[ConfigOverlay] = []
    seen: set[str] = set()
    for point in points:
        if not point.config_version or point.config_version in seen:
            continue
        seen.add(point.config_version)
        overlays.append(
            ConfigOverlay(
                version=point.config_version,
                first_seen_at=point.timestamp,
                run_id=point.run_id,
            )
        )
    return overlays


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


def _top_issue(health: sqlite3.Row | None, score: sqlite3.Row | None) -> str:
    if health:
        items = _json_list(health["items_json"])
        for item in items:
            if not isinstance(item, dict):
                continue
            severity = str(item.get("severity") or "")
            if severity in {"blocked", "error", "warning"}:
                return str(item.get("impact") or item.get("component") or "Review pipeline health")
    if score:
        drivers = _json_list(score["drivers_json"])
        for driver in drivers:
            if isinstance(driver, dict) and driver.get("direction") == "hurt":
                return str(driver.get("message") or "Review scrape quality drivers")
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


def _nattome_relevance(row: sqlite3.Row) -> float:
    hashtags = _json_loads(row["hashtags_json"])
    hashtag_text = " ".join(str(item) for item in hashtags) if isinstance(hashtags, list) else str(hashtags)
    haystack = " ".join(
        [
            str(row["caption"] or ""),
            hashtag_text,
            str(row["source_input"] or ""),
        ]
    ).lower()
    matches = sum(1 for term in NATTOME_TERMS if term in haystack)
    return min(matches / 4, 1.0)


def _weighted_engagement(row: sqlite3.Row) -> float:
    views = max(_positive_int(row["play_count"], 0), 1)
    likes = _positive_int(row["like_count"], 0)
    comments = _positive_int(row["comment_count"], 0)
    shares = _positive_int(row["share_count"], 0)
    return (likes + comments * 5 + shares * 10) / views


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


def _json_list(value: Any) -> list[Any]:
    data = _json_loads(value)
    return data if isinstance(data, list) else []


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default
