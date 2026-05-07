from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import isoformat_z

def load_candidates(candidates_path: Path | None) -> list[dict[str, Any]] | None:
    if candidates_path is None:
        return None
    if not candidates_path.exists():
        raise FileNotFoundError(f"candidate metadata file not found: {candidates_path}")
    try:
        payload = json.loads(candidates_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid candidate JSON: {candidates_path}: {exc}") from exc

    if isinstance(payload, list):
        candidates = payload
    elif isinstance(payload, dict):
        if isinstance(payload.get("top"), list):
            candidates = payload["top"]
        elif isinstance(payload.get("items"), list):
            candidates = payload["items"]
        elif isinstance(payload.get("candidates"), list):
            candidates = payload["candidates"]
        else:
            raise ValueError(
                f"candidate JSON must contain a top, items, or candidates list: {candidates_path}"
            )
    else:
        raise ValueError(f"candidate JSON must be an object or list: {candidates_path}")

    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            raise ValueError(f"candidate at index {index} is not an object")
    return candidates

def int_value(candidate: dict[str, Any], *keys: str) -> int:
    for key in keys:
        value = candidate.get(key)
        if value is None or value == "":
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return 0

def parse_candidate_timestamp(value: Any) -> datetime | None:
    if value is None or value == "":
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

def candidate_created_at(candidate: dict[str, Any]) -> datetime | None:
    for key in ("created_at", "createTimeISO", "createTime"):
        parsed = parse_candidate_timestamp(candidate.get(key))
        if parsed is not None:
            return parsed
    return None

def weighted_engagement_rate(candidate: dict[str, Any]) -> float:
    views = max(int_value(candidate, "play_count", "playCount", "views"), 1)
    likes = int_value(candidate, "like_count", "diggCount", "likes")
    comments = int_value(candidate, "comment_count", "commentCount", "comments")
    shares = int_value(candidate, "share_count", "shareCount", "shares")
    weighted = likes + comments * 5 + shares * 10
    return weighted / views

def usable_tiktok_link(candidate: dict[str, Any]) -> str:
    url = str(candidate.get("url") or candidate.get("webVideoUrl") or candidate.get("videoUrl") or "")
    if "tiktok.com" not in url or "/video/" not in url:
        return ""
    return url

def downloadable_video_source(candidate: dict[str, Any]) -> str:
    for key in (
        "video_download_url",
        "download_url",
        "downloadUrl",
        "downloadLink",
        "media_url",
        "mediaUrl",
    ):
        value = candidate.get(key)
        if value:
            return str(value)
    return ""

def nattome_relevance_score(candidate: dict[str, Any]) -> float:
    hashtags = candidate.get("hashtags") or []
    if isinstance(hashtags, list):
        hashtag_text = " ".join(str(item) for item in hashtags)
    else:
        hashtag_text = str(hashtags)
    haystack = " ".join(
        [
            str(candidate.get("caption") or candidate.get("text") or ""),
            hashtag_text,
            str(candidate.get("source_input") or ""),
        ]
    ).lower()
    terms = [
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
    ]
    matches = sum(1 for term in terms if term in haystack)
    return min(matches / 4, 1.0)

def selection_score(candidate: dict[str, Any], run_timestamp: datetime) -> float:
    views = max(int_value(candidate, "play_count", "playCount", "views"), 1)
    reach = math.log10(views + 1)
    created = candidate_created_at(candidate)
    if created is None:
        recency = 0.5
    else:
        age_days = max((run_timestamp - created).total_seconds() / 86400, 0)
        recency = 0.5 ** (age_days / 7)
    return weighted_engagement_rate(candidate) * reach * recency + nattome_relevance_score(candidate)

def normalize_candidate(candidate: dict[str, Any], run_timestamp: datetime, rank: int) -> dict[str, Any]:
    created = candidate_created_at(candidate)
    if isinstance(candidate.get("authorMeta"), dict):
        author_handle = candidate.get("author_handle") or candidate["authorMeta"].get("name")
    else:
        author_handle = candidate.get("author_handle")
    return {
        "rank": rank,
        "id": candidate.get("id") or candidate.get("video_id") or candidate.get("videoId"),
        "url": usable_tiktok_link(candidate),
        "video_download_url": downloadable_video_source(candidate),
        "author_handle": author_handle,
        "caption": candidate.get("caption") or candidate.get("text") or "",
        "play_count": int_value(candidate, "play_count", "playCount", "views"),
        "like_count": int_value(candidate, "like_count", "diggCount", "likes"),
        "comment_count": int_value(candidate, "comment_count", "commentCount", "comments"),
        "share_count": int_value(candidate, "share_count", "shareCount", "shares"),
        "created_at": created.strftime("%Y-%m-%dT%H:%M:%SZ") if created else None,
        "duration_seconds": parse_duration_seconds(candidate),
        "sound_title": sound_title(candidate),
        "sound_author": sound_author(candidate),
        "is_reused_sound": is_reused_sound(candidate),
        "audio_format_hint": candidate.get("audio_format_hint"),
        "audio_mood": candidate.get("audio_mood"),
        "visible_text_expected": candidate.get("visible_text_expected"),
        "has_visible_text": candidate.get("has_visible_text"),
        "text_overlay_expected": candidate.get("text_overlay_expected"),
        "weighted_engagement_rate": round(weighted_engagement_rate(candidate), 4),
        "nattome_relevance_score": round(nattome_relevance_score(candidate), 4),
        "selection_score": round(selection_score(candidate, run_timestamp), 4),
    }

def exclusion_reasons(
    candidate: dict[str, Any], configuration: dict[str, Any], run_timestamp: datetime
) -> list[str]:
    selection = configuration["selection"]
    reasons = []
    views = int_value(candidate, "play_count", "playCount", "views")
    if views < int(selection["minimum_views"]):
        reasons.append(f"below minimum views ({views} < {selection['minimum_views']})")

    created = candidate_created_at(candidate)
    if created is None:
        reasons.append("missing created_at timestamp")
    else:
        age_days = max((run_timestamp - created).total_seconds() / 86400, 0)
        if age_days > int(selection["maximum_age_days"]):
            reasons.append(f"older than {selection['maximum_age_days']} days")

    engagement_rate = weighted_engagement_rate(candidate)
    minimum_engagement = float(selection["minimum_weighted_engagement_rate"])
    if engagement_rate < minimum_engagement:
        reasons.append(
            "below minimum weighted engagement rate "
            f"({engagement_rate:.4f} < {minimum_engagement:.4f})"
        )

    if selection.get("requires_tiktok_link", True) and not usable_tiktok_link(candidate):
        reasons.append("missing usable TikTok link")

    if selection.get("requires_downloadable_video", True) and not downloadable_video_source(candidate):
        reasons.append("missing downloadable video source")

    return reasons

def select_candidates(
    candidates: list[dict[str, Any]],
    configuration: dict[str, Any],
    run_timestamp: datetime,
    batch_size: int,
    candidates_path: Path | None,
    *,
    preserve_order: bool = False,
) -> dict[str, Any]:
    eligible = []
    excluded = []
    for index, candidate in enumerate(candidates):
        candidate_id = candidate.get("id") or candidate.get("video_id") or candidate.get("videoId") or f"candidate-{index}"
        reasons = exclusion_reasons(candidate, configuration, run_timestamp)
        if reasons:
            excluded.append(
                {
                    "id": candidate_id,
                    "url": candidate.get("url") or candidate.get("webVideoUrl") or candidate.get("videoUrl"),
                    "reason": "; ".join(reasons),
                }
            )
            continue
        eligible.append(candidate)

    ranked = eligible if preserve_order else sorted(
        eligible,
        key=lambda candidate: selection_score(candidate, run_timestamp),
        reverse=True,
    )
    selected = [
        normalize_candidate(candidate, run_timestamp, rank)
        for rank, candidate in enumerate(ranked[:batch_size], start=1)
    ]

    return {
        "selected_at": isoformat_z(run_timestamp),
        "candidate_source": str(candidates_path) if candidates_path else None,
        "selection_strategy": "input_order" if preserve_order else "viral_relevance_score",
        "requested_batch_size": batch_size,
        "input_candidate_count": len(candidates),
        "eligible_candidate_count": len(eligible),
        "selected_candidate_count": len(selected),
        "minimum_eligibility_filter": configuration["selection"],
        "selected_candidates": selected,
        "excluded_candidates": excluded,
    }

def parse_duration_seconds(candidate: dict[str, Any]) -> float | None:
    for key in ("duration_seconds", "duration", "video_duration", "videoDuration"):
        value = candidate.get(key)
        if value is None or value == "":
            continue
        try:
            duration = float(value)
        except (TypeError, ValueError):
            continue
        if duration > 0:
            return duration

    for key in ("duration_ms", "durationMs", "video_duration_ms"):
        value = candidate.get(key)
        if value is None or value == "":
            continue
        try:
            duration = float(value) / 1000
        except (TypeError, ValueError):
            continue
        if duration > 0:
            return duration
    return None

def sound_title(candidate: dict[str, Any]) -> str | None:
    if candidate.get("sound_title"):
        return str(candidate["sound_title"])
    if candidate.get("music_title"):
        return str(candidate["music_title"])
    music_meta = candidate.get("musicMeta")
    if isinstance(music_meta, dict):
        value = music_meta.get("musicName") or music_meta.get("name")
        if value:
            return str(value)
    return None

def sound_author(candidate: dict[str, Any]) -> str | None:
    if candidate.get("sound_author"):
        return str(candidate["sound_author"])
    music_meta = candidate.get("musicMeta")
    if isinstance(music_meta, dict):
        value = music_meta.get("musicAuthor") or music_meta.get("authorName")
        if value:
            return str(value)
    return None

def is_reused_sound(candidate: dict[str, Any]) -> bool | None:
    for key in ("is_reused_sound", "isReusedSound"):
        if key in candidate:
            return bool(candidate[key])
    for key in ("is_original_sound", "isOriginalSound"):
        if key in candidate:
            return not bool(candidate[key])
    title = sound_title(candidate)
    if title:
        return "original sound" not in title.lower()
    return None
