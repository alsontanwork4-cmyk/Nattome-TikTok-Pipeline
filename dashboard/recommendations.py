from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .indexer import index_pipeline_artifacts
from .quality import compute_scrape_quality_scores
from .settings import get_active_settings_version
from .store import connect_dashboard_store, dump_json


VALID_RECOMMENDATION_STATUSES = {"needs_more_data", "accepted", "ignored", "resolved"}

DRIVER_RECOMMENDATIONS = {
    "candidate_volume": (
        "weak_source_input_performance",
        "Review source inputs that produced too few raw candidates before expanding the next scrape.",
    ),
    "eligibility_yield": (
        "low_eligibility_yield",
        "Tighten the source mix or filters because too few indexed candidates reached eligibility.",
    ),
    "nattome_relevance": (
        "low_relevance",
        "Replace broad inputs with more Nattome-specific gut health, reflux, bloating, and digestion sources.",
    ),
    "freshness": (
        "stale_videos",
        "Refresh source inputs or age filters because the candidate set is skewing stale.",
    ),
    "engagement_strength": (
        "low_engagement",
        "Prioritize source patterns that produce stronger weighted engagement before the next scrape.",
    ),
    "duplicate_noise_control": (
        "duplicate_noise",
        "Reduce duplicate creators, missing metadata, and curation-marked noise before scaling the scrape.",
    ),
}


@dataclass(frozen=True)
class Recommendation:
    id: int
    recommendation_type: str
    status: str
    summary: str
    supporting_evidence: list[dict[str, Any]]
    resolved_at: str | None


def generate_recommendations(workspace: Path | str = ".") -> list[Recommendation]:
    """Generate passive scrape recommendations without mutating settings or scores."""
    workspace_path = Path(workspace)
    index_pipeline_artifacts(workspace_path)
    compute_scrape_quality_scores(workspace_path)
    active_config = _active_config_label(workspace_path)

    connection = connect_dashboard_store(workspace_path)
    try:
        _ensure_recommendation_columns(connection)
        if active_config:
            _resolve_stale_recommendations(connection, active_config)
        for context in _recommendation_contexts(connection):
            config_version = context["config_version"]
            if active_config and config_version and config_version != active_config:
                continue
            for recommendation_type, summary, evidence in _recommendations_for_context(
                connection,
                context,
            ):
                _insert_recommendation_if_missing(
                    connection,
                    recommendation_type=recommendation_type,
                    summary=summary,
                    evidence=evidence,
                    fingerprint=_fingerprint(recommendation_type, context["run_id"], config_version),
                )
        connection.commit()
        return _list_recommendations(connection)
    finally:
        connection.close()


def list_recommendations(workspace: Path | str = ".") -> list[Recommendation]:
    connection = connect_dashboard_store(workspace)
    try:
        _ensure_recommendation_columns(connection)
        return _list_recommendations(connection)
    finally:
        connection.close()


def update_recommendation_status(
    workspace: Path | str,
    recommendation_id: int,
    status: str,
    *,
    user: str = "local",
) -> Recommendation:
    if status not in VALID_RECOMMENDATION_STATUSES:
        raise ValueError(
            "recommendation status must be one of: "
            + ", ".join(sorted(VALID_RECOMMENDATION_STATUSES))
        )
    connection = connect_dashboard_store(workspace)
    try:
        _ensure_recommendation_columns(connection)
        resolved_sql = ", resolved_at = CURRENT_TIMESTAMP" if status == "resolved" else ""
        connection.execute(
            f"""
            UPDATE recommendations
            SET status = ?,
                updated_by = ?,
                updated_at = CURRENT_TIMESTAMP
                {resolved_sql}
            WHERE id = ?
            """,
            (status, user.strip() or "local", recommendation_id),
        )
        row = connection.execute(
            "SELECT * FROM recommendations WHERE id = ?",
            (recommendation_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"unknown recommendation: {recommendation_id}")
        connection.commit()
        return _row_to_recommendation(row)
    finally:
        connection.close()


def _recommendation_contexts(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            batch_runs.*,
            scrape_quality_scores.score AS quality_score,
            scrape_quality_scores.drivers_json AS drivers_json,
            selected_batches.raw_json AS selected_json,
            selected_batches.candidate_source AS candidate_source
        FROM batch_runs
        JOIN scrape_quality_scores
            ON scrape_quality_scores.run_id = batch_runs.run_id
        LEFT JOIN selected_batches
            ON selected_batches.run_id = batch_runs.run_id
        WHERE scrape_quality_scores.needs_attention = 1
        ORDER BY COALESCE(batch_runs.run_timestamp, ''), batch_runs.run_id
        """
    )
    contexts = []
    for row in rows:
        manifest = _json_dict(row["raw_json"])
        selected = _json_dict(row["selected_json"])
        contexts.append(
            {
                "run_id": str(row["run_id"]),
                "run_timestamp": str(row["run_timestamp"] or ""),
                "manifest_path": str(row["manifest_path"] or ""),
                "candidate_source": str(row["candidate_source"] or ""),
                "quality_score": int(row["quality_score"]),
                "drivers": _json_list(row["drivers_json"]),
                "config_version": _config_version(manifest, selected),
            }
        )
    return contexts


def _recommendations_for_context(
    connection: sqlite3.Connection,
    context: dict[str, Any],
) -> list[tuple[str, str, list[dict[str, Any]]]]:
    recommendations = []
    for driver in context["drivers"]:
        if not isinstance(driver, dict) or driver.get("direction") != "hurt":
            continue
        component = str(driver.get("component") or "")
        mapped = DRIVER_RECOMMENDATIONS.get(component)
        if mapped is None:
            continue
        recommendation_type, summary = mapped
        evidence = _supporting_evidence(connection, context, driver)
        recommendations.append((recommendation_type, summary, evidence))
    return recommendations


def _supporting_evidence(
    connection: sqlite3.Connection,
    context: dict[str, Any],
    driver: dict[str, Any],
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = [
        {
            "entity_type": "run",
            "run_id": context["run_id"],
            "path": context["manifest_path"],
            "score": context["quality_score"],
            "message": driver.get("message") or "",
        }
    ]
    if context["config_version"]:
        evidence.append(
            {
                "entity_type": "config_version",
                "version": context["config_version"],
                "run_id": context["run_id"],
            }
        )
    evidence.extend(_source_input_evidence(connection, context))
    evidence.extend(_video_evidence(connection, context))
    evidence.extend(_curation_evidence(connection, context))
    return evidence


def _source_input_evidence(
    connection: sqlite3.Connection,
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "entity_type": "source_input",
            "source_input": str(row["source_input"] or "Not recorded"),
            "candidate_count": int(row["candidate_count"]),
            "eligible_count": int(row["eligible_count"]),
            "run_id": context["run_id"],
        }
        for row in connection.execute(
            """
            SELECT
                COALESCE(source_input, '') AS source_input,
                COUNT(*) AS candidate_count,
                SUM(CASE WHEN selection_status IN ('eligible', 'selected', 'analyzed') THEN 1 ELSE 0 END) AS eligible_count
            FROM raw_videos
            WHERE source_artifact_path = ?
            GROUP BY COALESCE(source_input, '')
            ORDER BY eligible_count ASC, candidate_count DESC, source_input
            LIMIT 3
            """,
            (context["candidate_source"],),
        )
    ]


def _video_evidence(
    connection: sqlite3.Connection,
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "entity_type": "video",
            "video_id": str(row["video_id"]),
            "tiktok_url": str(row["tiktok_url"] or ""),
            "caption": str(row["caption"] or ""),
            "source_input": str(row["source_input"] or ""),
            "run_id": context["run_id"],
        }
        for row in connection.execute(
            """
            SELECT video_id, tiktok_url, caption, source_input, play_count
            FROM raw_videos
            WHERE source_artifact_path = ?
            ORDER BY COALESCE(play_count, 0) DESC, video_id
            LIMIT 3
            """,
            (context["candidate_source"],),
        )
    ]


def _curation_evidence(
    connection: sqlite3.Connection,
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            video_curation.tiktok_video_id,
            video_curation.labels,
            video_curation.note,
            video_curation.exclude_similar_reason
        FROM video_curation
        JOIN raw_videos
            ON raw_videos.video_id = video_curation.tiktok_video_id
        WHERE raw_videos.source_artifact_path = ?
        ORDER BY video_curation.tiktok_video_id
        LIMIT 5
        """,
        (context["candidate_source"],),
    )
    evidence = []
    for row in rows:
        labels = _json_list(row["labels"])
        for label in labels:
            evidence.append(
                {
                    "entity_type": "label",
                    "video_id": str(row["tiktok_video_id"]),
                    "label": str(label),
                    "note": str(row["note"] or ""),
                    "exclude_similar_reason": str(row["exclude_similar_reason"] or ""),
                    "run_id": context["run_id"],
                }
            )
    return evidence


def _insert_recommendation_if_missing(
    connection: sqlite3.Connection,
    *,
    recommendation_type: str,
    summary: str,
    evidence: list[dict[str, Any]],
    fingerprint: str,
) -> None:
    existing = connection.execute(
        "SELECT id FROM recommendations WHERE fingerprint = ?",
        (fingerprint,),
    ).fetchone()
    if existing:
        return
    connection.execute(
        """
        INSERT INTO recommendations (
            recommendation_type,
            status,
            summary,
            supporting_evidence_json,
            fingerprint
        )
        VALUES (?, 'needs_more_data', ?, ?, ?)
        """,
        (
            recommendation_type,
            summary,
            dump_json(evidence),
            fingerprint,
        ),
    )


def _resolve_stale_recommendations(connection: sqlite3.Connection, active_config: str) -> None:
    for row in connection.execute(
        """
        SELECT id, supporting_evidence_json
        FROM recommendations
        WHERE status IN ('needs_more_data', 'accepted', 'ignored')
        """
    ):
        evidence_config = _evidence_config_version(row["supporting_evidence_json"])
        if evidence_config and evidence_config != active_config:
            connection.execute(
                """
                UPDATE recommendations
                SET status = 'resolved',
                    resolved_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (row["id"],),
            )


def _list_recommendations(connection: sqlite3.Connection) -> list[Recommendation]:
    return [
        _row_to_recommendation(row)
        for row in connection.execute(
            """
            SELECT *
            FROM recommendations
            ORDER BY
                CASE status
                    WHEN 'needs_more_data' THEN 0
                    WHEN 'accepted' THEN 1
                    WHEN 'ignored' THEN 2
                    WHEN 'resolved' THEN 3
                    ELSE 4
                END,
                id
            """
        )
    ]


def _row_to_recommendation(row: sqlite3.Row) -> Recommendation:
    return Recommendation(
        id=int(row["id"]),
        recommendation_type=str(row["recommendation_type"]),
        status=str(row["status"]),
        summary=str(row["summary"]),
        supporting_evidence=_json_list(row["supporting_evidence_json"]),
        resolved_at=row["resolved_at"],
    )


def _ensure_recommendation_columns(connection: sqlite3.Connection) -> None:
    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(recommendations)")
    }
    if "fingerprint" not in columns:
        connection.execute("ALTER TABLE recommendations ADD COLUMN fingerprint TEXT NOT NULL DEFAULT ''")


def _active_config_label(workspace: Path) -> str:
    active = get_active_settings_version(workspace)
    return f"v{active.version}" if active.version > 0 else ""


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
    return str(version or "")


def _fingerprint(recommendation_type: str, run_id: str, config_version: str) -> str:
    return "|".join([recommendation_type, run_id, config_version])


def _evidence_config_version(raw_evidence: Any) -> str:
    for item in _json_list(raw_evidence):
        if isinstance(item, dict) and item.get("entity_type") == "config_version":
            return str(item.get("version") or "")
    return ""


def _json_dict(value: Any) -> dict[str, Any]:
    if not value:
        return {}
    try:
        loaded = json.loads(str(value))
    except (TypeError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _json_list(value: Any) -> list[Any]:
    if not value:
        return []
    try:
        loaded = json.loads(str(value))
    except (TypeError, json.JSONDecodeError):
        return []
    return loaded if isinstance(loaded, list) else []
