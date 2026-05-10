from __future__ import annotations

import json
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


def engagement_rate_text(video: Any) -> str:
    views = _positive_int(_value(video, "play_count"), 0)
    if views <= 0:
        return "--"
    return f"{weighted_engagement(video) * 100:.1f}%"


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
