from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

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


def nattome_relevance(video: Any) -> float:
    return min(_nattome_match_count(video) / 4, 1.0)


def relevance_band(video: Any) -> str:
    matches = _nattome_match_count(video)
    if matches >= 2:
        return "high relevance"
    if matches == 1:
        return "medium relevance"
    return "low relevance"


def relevance_label(video: Any) -> str:
    return relevance_band(video).replace(" relevance", "")


def weighted_engagement(video: Any) -> float:
    views = max(_positive_int(_value(video, "play_count"), 0), 1)
    likes = _positive_int(_value(video, "like_count"), 0)
    comments = _positive_int(_value(video, "comment_count"), 0)
    shares = _positive_int(_value(video, "share_count"), 0)
    return (likes + comments * 5 + shares * 10) / views


def engagement_band(video: Any) -> str:
    engagement = weighted_engagement(video)
    if engagement >= 0.08:
        return "high engagement"
    if engagement >= 0.03:
        return "medium engagement"
    return "low engagement"


def engagement_rate_text(video: Any) -> str:
    views = _positive_int(_value(video, "play_count"), 0)
    if views <= 0:
        return "--"
    return f"{weighted_engagement(video) * 100:.1f}%"


def video_score_band(video: Any) -> str:
    relevance = relevance_band(video)
    engagement = engagement_band(video)
    if relevance == "high relevance" and engagement == "high engagement":
        return "strong scrape"
    if relevance != "low relevance" and engagement != "low engagement":
        return "usable scrape"
    return "needs attention"


def score_band(score: int) -> str:
    if score >= 80:
        return "strong scrape"
    if score >= 60:
        return "usable scrape"
    return "needs attention"


def scrape_freshness_score(
    video: Any,
    run_timestamp: datetime | str | None,
    max_age_days: float,
) -> float:
    created = parse_datetime(_value(video, "created_at"))
    run_time = parse_datetime(run_timestamp)
    if created is None or run_time is None:
        return 0.5
    age_days = max((run_time - created).total_seconds() / 86400, 0.0)
    return 1.0 - min(age_days / max(max_age_days, 1.0), 1.0)


def freshness_facet(created_at: Any, run_timestamp: datetime | str | None) -> str:
    created = parse_datetime(created_at)
    run_time = parse_datetime(run_timestamp)
    if created is None or run_time is None:
        return "undated"
    age_days = max((run_time - created).total_seconds() / 86400, 0.0)
    if age_days <= 14:
        return "fresh"
    if age_days <= 45:
        return "aging"
    return "stale"


def freshness_label(created_at: Any) -> str:
    return "created date available" if created_at else "created date missing"


def score_text(value: object) -> str:
    return "--" if value is None else str(value)


def percent_text(value: object) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "--"
    return f"{number * 100:.1f}%"


def parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, (int, float)):
        parsed = datetime.fromtimestamp(value, tz=timezone.utc)
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _nattome_match_count(video: Any) -> int:
    haystack = " ".join(
        [
            str(_value(video, "caption") or ""),
            _hashtag_text(video),
            str(_value(video, "source_input") or ""),
        ]
    ).lower()
    return sum(1 for term in NATTOME_TERMS if term in haystack)


def _hashtag_text(video: Any) -> str:
    hashtags = _value(video, "hashtags", None)
    if hashtags is None:
        hashtags = _json_loads(_value(video, "hashtags_json", None))
    if isinstance(hashtags, list):
        return " ".join(str(item) for item in hashtags)
    return str(hashtags or "")


def _value(source: Any, key: str, default: Any = "") -> Any:
    if isinstance(source, dict):
        return source.get(key, default)
    keys = getattr(source, "keys", None)
    if callable(keys) and key in keys():
        return source[key]
    return getattr(source, key, default)


def _json_loads(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if not value:
        return {}
    try:
        return json.loads(str(value))
    except json.JSONDecodeError:
        return {}


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default
