from __future__ import annotations

import json
from typing import Any

from .agent_views import trace_history_rows
from .reports import artifact_metadata_from_output
from .view_models import cell, format_bytes, list_value, output_view, run_view


RUN_DETAIL_TABS = (
    ("overview", "Overview"),
    ("posts", "Posts"),
    ("authors", "Authors"),
    ("music", "Music"),
    ("video", "Video"),
    ("agent-trace", "Agent Trace"),
    ("all-fields", "All fields"),
)


def run_history_rows(
    runs: list[dict],
    outputs_by_run: dict[str, list[dict]],
    *,
    raw_videos_by_run: dict[str, list[dict]] | None = None,
    query: str = "",
) -> list[dict]:
    rows = []
    normalized_query = query.strip().lower()
    videos_by_run = raw_videos_by_run or {}
    for run in runs:
        rendered = run_view(run)
        outputs = outputs_by_run.get(rendered["run_id"], [])
        raw_videos = videos_by_run.get(rendered["run_id"], [])
        result_count = _result_count(run)
        analytics = _run_marketing_analytics(raw_videos)
        row = {
            **rendered,
            "task_summary": _task_summary(run, result_count),
            "result_count": analytics["result_count"] or result_count,
            "total_plays": analytics["total_plays"],
            "avg_plays": analytics["avg_plays"],
            "engagements": analytics["engagements"],
            "engagement_rate": analytics["engagement_rate"],
            "top_author": analytics["top_author"],
            "top_music": analytics["top_music"],
            "input_summary": analytics["input_summary"],
            "usage": "--",
            "origin": _origin(run),
            "outputs": [_output_chip(output) for output in outputs],
        }
        if normalized_query and normalized_query not in _run_search_text(row).lower():
            continue
        rows.append(row)
    return rows


def run_detail_workbench(
    dashboard_client: object,
    *,
    run: dict,
    outputs: list[dict],
    raw_videos: list[dict],
    tab: str,
) -> dict:
    active_tab = tab if tab in {key for key, _label in RUN_DETAIL_TABS} else "overview"
    run_id = str(run.get("run_id") or "")
    raw_payload = load_raw_scrape_payload(dashboard_client, outputs)
    raw_items = _raw_items(raw_payload)
    fallback_items = _fallback_items(run_id, raw_videos) if not raw_items else []
    items = raw_items or fallback_items
    agent_trace = trace_history_rows(_run_agent_trace_events(dashboard_client, run_id))
    rendered_outputs = [output_view(output) for output in outputs]
    rendered_run = run_view(run)
    overview = _overview(
        run=rendered_run,
        raw_payload=raw_payload,
        items=items,
        outputs=rendered_outputs,
        using_fallback=not raw_items,
    )
    return {
        "tabs": [
            {"key": key, "label": label, "href": f"/runs/{run_id}?tab={key}", "active": key == active_tab}
            for key, label in RUN_DETAIL_TABS
        ],
        "active_tab": active_tab,
        "overview": overview,
        "overview_rows": [_overview_row(item, index) for index, item in enumerate(items, start=1)],
        "insights": _detail_insights(items),
        "posts": [_post_row(item, index) for index, item in enumerate(items, start=1)],
        "authors": [_author_row(item, index) for index, item in enumerate(items, start=1)],
        "music": [_music_row(item, index) for index, item in enumerate(items, start=1)],
        "video": [_video_row(item, index) for index, item in enumerate(items, start=1)],
        "agent_trace": agent_trace,
        "all_fields": [_all_fields_row(item, index) for index, item in enumerate(items, start=1)],
        "outputs": rendered_outputs,
        "using_fallback": not raw_items,
    }


def load_raw_scrape_payload(dashboard_client: object, outputs: list[dict]) -> dict:
    raw_output = first_raw_scrape_output(outputs)
    if not raw_output:
        return {}
    download = getattr(dashboard_client, "download_artifact_text", None)
    if not callable(download):
        return {}
    try:
        body = download(artifact_metadata_from_output(raw_output))
    except Exception:
        return {}
    if not body:
        return {}
    try:
        payload = json.loads(str(body))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def first_raw_scrape_output(outputs: list[dict]) -> dict | None:
    for output in outputs:
        artifact_type = str(output.get("artifact_type") or "").lower()
        filename = str(output.get("filename") or "").lower()
        object_path = str(output.get("object_path") or "").lower()
        if (
            artifact_type == "raw_scrape"
            or filename == "raw_scrape_all.json"
            or object_path.endswith("/raw_scrape_all.json")
        ):
            return output
    return None


def _run_agent_trace_events(dashboard_client: object, run_id: str) -> list[dict]:
    list_events = getattr(dashboard_client, "list_agent_trace_events", None)
    if not callable(list_events):
        return []
    try:
        return list(list_events(run_id=run_id, limit=100) or [])
    except Exception:
        return []


def _overview(
    *,
    run: dict,
    raw_payload: dict,
    items: list[dict],
    outputs: list[dict],
    using_fallback: bool,
) -> dict:
    inputs = raw_payload.get("inputs") if isinstance(raw_payload.get("inputs"), dict) else {}
    return {
        "run": run,
        "scope": str(raw_payload.get("scope") or run.get("run_type") or "--"),
        "raw_item_count": raw_payload.get("raw_item_count") or run.get("raw_candidate_count") or len(items),
        "unique_result_count": raw_payload.get("unique_video_count") or len(items),
        "inputs": {
            "hashtags": _join_list(inputs.get("hashtags")),
            "keywords": _join_list(inputs.get("keywords")),
            "profiles": _join_list(inputs.get("profiles")),
        },
        "outputs": outputs,
        "output_count": len(outputs),
        "data_source": "Raw scrape artifact" if not using_fallback else "Compact raw video metadata",
    }


def _overview_row(item: dict, index: int) -> dict:
    author = _dict(item.get("authorMeta"))
    music = _dict(item.get("musicMeta"))
    video_meta = _dict(item.get("videoMeta"))
    return {
        "index": index,
        "avatar": _first(author.get("avatar"), author.get("avatarLarger"), author.get("avatarMedium")),
        "author": _first(author.get("name"), author.get("nickName"), item.get("author_handle")),
        "text": _text(item),
        "diggs": cell(item.get("diggCount") or item.get("like_count")),
        "shares": cell(item.get("shareCount") or item.get("share_count")),
        "plays": cell(item.get("playCount") or item.get("play_count")),
        "comments": cell(item.get("commentCount") or item.get("comment_count")),
        "bookmarks": cell(item.get("collectCount") or item.get("bookmarkCount")),
        "duration": cell(video_meta.get("duration") or item.get("duration_s") or item.get("duration_seconds")),
        "music_name": _first(music.get("musicName"), _nested(item, "music", "title")),
        "music_author": _first(music.get("musicAuthor"), _nested(item, "music", "author")),
        "music_original": _bool_value(
            _first(music.get("musicOriginal"), _nested(item, "music", "original"))
        ),
        "create_time": _first(item.get("createTimeISO"), item.get("created_at"), item.get("createTime")),
        "video_url": _first(item.get("webVideoUrl"), item.get("videoUrl"), item.get("url")),
    }


def _raw_items(payload: dict) -> list[dict]:
    for key in ("raw_items", "items", "top", "candidates"):
        values = payload.get(key)
        if isinstance(values, list):
            return [value for value in values if isinstance(value, dict)]
    return []


def _fallback_items(run_id: str, raw_videos: list[dict]) -> list[dict]:
    items = []
    for video in raw_videos:
        if str(video.get("run_id") or "") != run_id:
            continue
        hashtags = list_value(video.get("hashtags"))
        items.append(
            {
                "id": video.get("video_id"),
                "webVideoUrl": video.get("tiktok_url"),
                "text": video.get("caption"),
                "hashtags": [{"name": tag} for tag in hashtags],
                "playCount": video.get("play_count"),
                "diggCount": video.get("like_count"),
                "commentCount": video.get("comment_count"),
                "shareCount": video.get("share_count"),
                "createTimeISO": video.get("created_at"),
                "authorMeta": {"name": video.get("author_handle")},
                "_fallback": True,
                "_source_input": video.get("source_input"),
            }
        )
    return items


def _post_row(item: dict, index: int) -> dict:
    video_meta = _dict(item.get("videoMeta"))
    author = _dict(item.get("authorMeta"))
    return {
        "index": index,
        "cover": _first(
            video_meta.get("coverUrl"),
            video_meta.get("coverMediumUrl"),
            video_meta.get("cover"),
            item.get("coverUrl"),
        ),
        "text": _text(item),
        "diggs": cell(item.get("diggCount") or item.get("like_count")),
        "shares": cell(item.get("shareCount") or item.get("share_count")),
        "plays": cell(item.get("playCount") or item.get("play_count")),
        "comments": cell(item.get("commentCount") or item.get("comment_count")),
        "duration": cell(video_meta.get("duration") or item.get("duration_s") or item.get("duration_seconds")),
        "is_ad": _bool_value(item.get("isAd")),
        "hashtags": _hashtags(item),
        "author": _first(author.get("name"), author.get("nickName"), item.get("author_handle")),
        "video_url": _first(item.get("webVideoUrl"), item.get("videoUrl"), item.get("url")),
        "create_time": _first(item.get("createTimeISO"), item.get("created_at"), item.get("createTime")),
    }


def _author_row(item: dict, index: int) -> dict:
    author = _dict(item.get("authorMeta"))
    return {
        "index": index,
        "avatar": _first(author.get("avatar"), author.get("avatarLarger"), author.get("avatarMedium")),
        "name": _first(author.get("name"), item.get("author_handle")),
        "nickname": author.get("nickName") or "",
        "verified": _bool_value(author.get("verified")),
        "signature": author.get("signature") or "",
        "fans": cell(author.get("fans")),
        "videos": cell(author.get("video")),
        "private_account": _bool_value(author.get("privateAccount")),
        "seller": cell(author.get("ttSeller")),
        "bio_link": cell(author.get("bioLink")),
        "author_id": cell(author.get("id")),
        "text": _text(item),
    }


def _music_row(item: dict, index: int) -> dict:
    music = _dict(item.get("musicMeta"))
    return {
        "index": index,
        "cover": _first(music.get("coverMediumUrl"), music.get("coverThumb"), music.get("coverLarge")),
        "name": _first(music.get("musicName"), _nested(item, "music", "title")),
        "author": _first(music.get("musicAuthor"), _nested(item, "music", "author")),
        "original": _bool_value(_first(music.get("musicOriginal"), _nested(item, "music", "original"))),
        "album": cell(music.get("musicAlbum")),
        "play_url": cell(music.get("playUrl")),
    }


def _video_row(item: dict, index: int) -> dict:
    video_meta = _dict(item.get("videoMeta"))
    return {
        "index": index,
        "cover": _first(video_meta.get("coverUrl"), video_meta.get("coverMediumUrl"), item.get("coverUrl")),
        "duration": cell(video_meta.get("duration") or item.get("duration_s") or item.get("duration_seconds")),
        "definition": cell(video_meta.get("definition")),
        "format": cell(video_meta.get("format")),
        "height": cell(video_meta.get("height")),
        "width": cell(video_meta.get("width")),
        "download": cell(
            _first(
                video_meta.get("downloadAddr"),
                video_meta.get("downloadUrl"),
                item.get("video_download_url"),
                item.get("downloadedVideoUrl"),
            )
        ),
        "text": _text(item),
    }


def _all_fields_row(item: dict, index: int) -> dict:
    title = _first(_text(item), item.get("id"), f"Result {index}")
    return {
        "index": index,
        "title": str(title)[:160],
        "fields": [{"key": key, "value": _field_value(value)} for key, value in sorted(item.items())],
    }


def _output_chip(output: dict) -> dict:
    filename = str(output.get("filename") or output.get("object_path") or "")
    return {
        "label": filename or str(output.get("artifact_type") or "output"),
        "href": f"/artifacts/{output.get('object_path')}" if output.get("object_path") else "",
        "size": format_bytes(output.get("size_bytes")),
    }


def _run_marketing_analytics(raw_videos: list[dict]) -> dict:
    if not raw_videos:
        return {
            "result_count": 0,
            "total_plays": "--",
            "avg_plays": "--",
            "engagements": "--",
            "engagement_rate": "--",
            "top_author": "--",
            "top_music": "--",
            "input_summary": "--",
        }
    total_plays = sum(_int(video.get("play_count")) for video in raw_videos)
    likes = sum(_int(video.get("like_count")) for video in raw_videos)
    comments = sum(_int(video.get("comment_count")) for video in raw_videos)
    shares = sum(_int(video.get("share_count")) for video in raw_videos)
    top_video = max(raw_videos, key=lambda video: _int(video.get("play_count")), default={})
    source_inputs = sorted(
        {str(video.get("source_input") or "") for video in raw_videos if video.get("source_input")}
    )
    engagements = likes + comments + shares
    return {
        "result_count": len(raw_videos),
        "total_plays": _format_int(total_plays),
        "avg_plays": _format_int(round(total_plays / len(raw_videos))) if raw_videos else "--",
        "engagements": _format_int(engagements),
        "engagement_rate": _format_percent(engagements / total_plays) if total_plays else "--",
        "top_author": str(top_video.get("author_handle") or "--"),
        "top_music": str(top_video.get("music_title") or top_video.get("sound_title") or "--"),
        "input_summary": ", ".join(source_inputs[:3]) + ("..." if len(source_inputs) > 3 else "")
        if source_inputs
        else "--",
    }


def _detail_insights(items: list[dict]) -> dict:
    plays = [_int(_first(item.get("playCount"), item.get("play_count"))) for item in items]
    likes = [_int(_first(item.get("diggCount"), item.get("like_count"))) for item in items]
    comments = [_int(_first(item.get("commentCount"), item.get("comment_count"))) for item in items]
    shares = [_int(_first(item.get("shareCount"), item.get("share_count"))) for item in items]
    total_plays = sum(plays)
    engagements = sum(likes) + sum(comments) + sum(shares)
    top_item = max(items, key=lambda item: _int(_first(item.get("playCount"), item.get("play_count"))), default={})
    top_author = _first(_dict(top_item.get("authorMeta")).get("name"), top_item.get("author_handle"), "--")
    top_music = _first(_dict(top_item.get("musicMeta")).get("musicName"), _nested(top_item, "music", "title"), "--")
    return {
        "total_plays": _format_int(total_plays),
        "avg_plays": _format_int(round(total_plays / len(items))) if items else "--",
        "engagements": _format_int(engagements),
        "engagement_rate": _format_percent(engagements / total_plays) if total_plays else "--",
        "top_author": top_author,
        "top_music": top_music,
    }


def _result_count(run: dict) -> int:
    for key in ("raw_candidate_count", "selected_count", "eligible_candidate_count"):
        try:
            value = int(run.get(key) or 0)
        except (TypeError, ValueError):
            value = 0
        if value:
            return value
    return 0


def _task_summary(run: dict, result_count: int) -> str:
    run_type = str(run.get("run_type") or run.get("mode") or "run").replace("_", " ")
    if result_count == 1:
        return f"Scraped 1 TikTok result ({run_type})"
    return f"Scraped {result_count} TikTok results ({run_type})"


def _origin(run: dict) -> str:
    triggered_by = str(run.get("triggered_by") or run.get("created_by") or "").strip()
    if not triggered_by:
        return "API"
    if "@" in triggered_by:
        return "Manual"
    return triggered_by


def _run_search_text(row: dict) -> str:
    return " ".join(
        str(row.get(key) or "")
        for key in ("run_id", "status_label", "run_type", "started_at", "finished_at", "triggered_by", "task_summary")
    )


def _dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _nested(value: dict, key: str, nested_key: str) -> object:
    nested = value.get(key)
    if isinstance(nested, dict):
        return nested.get(nested_key)
    return None


def _first(*values: object) -> object:
    for value in values:
        if value not in (None, ""):
            return value
    return ""


def _text(item: dict) -> str:
    return str(_first(item.get("text"), item.get("caption"), item.get("description")))


def _hashtags(item: dict) -> list[str]:
    hashtags = item.get("hashtags")
    if isinstance(hashtags, list):
        values = []
        for hashtag in hashtags:
            if isinstance(hashtag, dict) and hashtag.get("name"):
                values.append(str(hashtag["name"]))
            elif isinstance(hashtag, str):
                values.append(hashtag)
        return values
    return []


def _join_list(value: object) -> str:
    values = list_value(value)
    return ", ".join(str(item) for item in values) if values else "--"


def _bool_value(value: object) -> str:
    if value is True:
        return "Yes"
    if value is False:
        return "No"
    if value in (None, ""):
        return "--"
    return "Yes" if bool(value) else "No"


def _field_value(value: object) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    return "" if value is None else str(value)


def _int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _format_int(value: int) -> str:
    return f"{value:,}"


def _format_percent(value: float) -> str:
    return f"{value * 100:.2f}%"
