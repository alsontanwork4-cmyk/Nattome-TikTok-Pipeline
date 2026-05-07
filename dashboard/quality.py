from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from typing import Any

from .store import DASHBOARD_DB_PATH, initialize_dashboard_store


COMPONENT_WEIGHTS = {
    "candidate_volume": 25,
    "eligibility_yield": 20,
    "nattome_relevance": 20,
    "freshness": 15,
    "engagement_strength": 15,
    "duplicate_noise_control": 5,
}

NATTOME_TERMS = (
    "acid reflux",
    "reflux",
    "bloating",
    "bloated",
    "gut",
    "digest",
    "digestion",
    "digestive",
    "stomach",
    "heartburn",
    "ibs",
    "constipation",
    "antacid",
    "gastric",
)


@dataclass(frozen=True)
class ScrapeQualityScore:
    run_id: str
    score: int
    band: str
    needs_attention: bool
    components: dict[str, int]
    drivers: list[dict[str, Any]]


def compute_scrape_quality_scores(workspace: Path | str = ".") -> list[ScrapeQualityScore]:
    """Compute and persist scrape-only quality scores for indexed Batch Analysis Runs."""
    workspace_path = Path(workspace)
    db_path = initialize_dashboard_store(workspace_path)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("DELETE FROM scrape_quality_scores")
        scores = [
            _score_run(connection, row)
            for row in connection.execute("SELECT * FROM batch_runs ORDER BY run_timestamp, run_id")
        ]
        for score in scores:
            _persist_score(connection, score)
        connection.commit()
        return scores
    finally:
        connection.close()


def _score_run(connection: sqlite3.Connection, run: sqlite3.Row) -> ScrapeQualityScore:
    selected = connection.execute(
        "SELECT * FROM selected_batches WHERE run_id = ?",
        (run["run_id"],),
    ).fetchone()
    selected_json = _json_loads(selected["raw_json"]) if selected else {}
    manifest_json = _json_loads(run["raw_json"])
    videos = _run_candidate_videos(connection, run["run_id"], selected)

    requested_batch_size = _positive_int(
        run["requested_batch_size"],
        _positive_int(selected_json.get("requested_batch_size"), 1),
    )
    raw_count = _positive_int(selected_json.get("input_candidate_count"), len(videos))
    if raw_count == 0:
        raw_count = len(videos)
    eligible_count = _positive_int(
        selected_json.get("eligible_candidate_count"),
        _positive_int(selected_json.get("selected_candidate_count"), 0),
    )
    run_timestamp = _parse_datetime(run["run_timestamp"])
    max_age_days = _selection_number(manifest_json, "maximum_age_days", 14.0)

    ratios = {
        "candidate_volume": _ratio(raw_count, max(requested_batch_size * 1.25, 1.0)),
        "eligibility_yield": _ratio(eligible_count, max(raw_count, 1)),
        "nattome_relevance": _average([_nattome_relevance(row) for row in videos]),
        "freshness": _average([_freshness(row, run_timestamp, max_age_days) for row in videos]),
        "engagement_strength": _ratio(_average([_weighted_engagement(row) for row in videos]), 0.08),
        "duplicate_noise_control": _duplicate_noise_control(videos),
    }
    components = {
        name: round(COMPONENT_WEIGHTS[name] * min(max(value, 0.0), 1.0))
        for name, value in ratios.items()
    }
    total = min(100, max(0, sum(components.values())))
    band = _band(total)
    return ScrapeQualityScore(
        run_id=run["run_id"],
        score=total,
        band=band,
        needs_attention=total < 60,
        components=components,
        drivers=_drivers(raw_count, eligible_count, ratios),
    )


def _run_candidate_videos(
    connection: sqlite3.Connection,
    run_id: str,
    selected: sqlite3.Row | None,
) -> list[sqlite3.Row]:
    if selected and selected["candidate_source"]:
        rows = list(
            connection.execute(
                "SELECT * FROM raw_videos WHERE source_artifact_path = ? ORDER BY video_id",
                (selected["candidate_source"],),
            )
        )
        if rows:
            return rows
    return list(
        connection.execute(
            "SELECT * FROM raw_videos WHERE run_id = ? ORDER BY video_id",
            (run_id,),
        )
    )


def _persist_score(connection: sqlite3.Connection, score: ScrapeQualityScore) -> None:
    connection.execute(
        """
        INSERT INTO scrape_quality_scores (
            run_id,
            score,
            band,
            needs_attention,
            candidate_volume_score,
            eligibility_yield_score,
            nattome_relevance_score,
            freshness_score,
            engagement_strength_score,
            duplicate_noise_control_score,
            drivers_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            score.run_id,
            score.score,
            score.band,
            1 if score.needs_attention else 0,
            score.components["candidate_volume"],
            score.components["eligibility_yield"],
            score.components["nattome_relevance"],
            score.components["freshness"],
            score.components["engagement_strength"],
            score.components["duplicate_noise_control"],
            json.dumps(score.drivers, ensure_ascii=True, sort_keys=True),
        ),
    )


def _band(score: int) -> str:
    if score >= 80:
        return "strong scrape"
    if score >= 60:
        return "usable scrape"
    return "needs attention"


def _drivers(
    raw_count: int,
    eligible_count: int,
    ratios: dict[str, float],
) -> list[dict[str, Any]]:
    labels = {
        "candidate_volume": f"{raw_count} raw candidates indexed",
        "eligibility_yield": f"{eligible_count} eligible candidates",
        "nattome_relevance": "average Nattome relevance from captions, hashtags, and source inputs",
        "freshness": "average candidate freshness",
        "engagement_strength": "average weighted engagement rate",
        "duplicate_noise_control": "metadata completeness and creator diversity",
    }
    drivers = []
    for name, ratio in ratios.items():
        if ratio >= 0.8:
            direction = "helped"
        elif ratio < 0.6:
            direction = "hurt"
        else:
            direction = "neutral"
        drivers.append(
            {
                "component": name,
                "direction": direction,
                "message": labels[name],
                "component_score": round(COMPONENT_WEIGHTS[name] * min(max(ratio, 0.0), 1.0)),
            }
        )
    return drivers


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


def _freshness(row: sqlite3.Row, run_timestamp: datetime | None, max_age_days: float) -> float:
    created = _parse_datetime(row["created_at"])
    if created is None or run_timestamp is None:
        return 0.5
    age_days = max((run_timestamp - created).total_seconds() / 86400, 0.0)
    return 1.0 - min(age_days / max(max_age_days, 1.0), 1.0)


def _weighted_engagement(row: sqlite3.Row) -> float:
    views = max(_positive_int(row["play_count"], 0), 1)
    likes = _positive_int(row["like_count"], 0)
    comments = _positive_int(row["comment_count"], 0)
    shares = _positive_int(row["share_count"], 0)
    return (likes + comments * 5 + shares * 10) / views


def _duplicate_noise_control(videos: list[sqlite3.Row]) -> float:
    if not videos:
        return 0.0
    complete = [
        bool(row["tiktok_url"])
        and bool(row["caption"])
        and bool(row["source_input"])
        and bool(row["is_downloadable"])
        for row in videos
    ]
    handles = [row["author_handle"] for row in videos if row["author_handle"]]
    metadata_completeness = sum(1 for item in complete if item) / len(videos)
    creator_diversity = len(set(handles)) / len(videos) if handles else 0.0
    return (metadata_completeness + min(creator_diversity / 0.7, 1.0)) / 2


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return min(numerator / denominator, 1.0)


def _selection_number(manifest: dict[str, Any], key: str, default: float) -> float:
    selection = manifest.get("configuration", {}).get("selection", {})
    value = selection.get(key) if isinstance(selection, dict) else None
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    return None


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
