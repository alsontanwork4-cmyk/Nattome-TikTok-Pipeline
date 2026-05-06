#!/usr/bin/env python3
"""Create a Nattome TikTok Batch Analysis Run skeleton."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlencode, urlparse
from urllib.request import Request, urlopen


MODE_DEFAULT_BATCH_SIZE = {
    "debug": 1,
    "quick": 5,
    "default": 10,
    "deep": 20,
}

RUN_SUBDIRECTORIES = [
    "batch_outputs/markdown",
    "batch_outputs/json",
    "batch_outputs/spreadsheets",
    "evidence_bundles",
    "logs",
]

DEFAULT_CONFIG: dict[str, Any] = {
    "selection": {
        "minimum_views": 10000,
        "maximum_age_days": 30,
        "minimum_weighted_engagement_rate": 0.03,
        "requires_tiktok_link": True,
        "requires_downloadable_video": True,
    },
    "outputs": {
        "markdown": "batch_outputs/markdown",
        "json": "batch_outputs/json",
        "spreadsheet": "batch_outputs/spreadsheets",
        "evidence_bundles": "evidence_bundles",
        "logs": "logs",
    },
    "tool_stack": {
        "discovery_download": "Apify",
        "video_processing": "FFmpeg",
        "ocr_primary": "PaddleOCR",
        "ocr_fallback": "Tesseract",
        "transcription": "Whisper-style multilingual transcription",
    },
    "telegram": {
        "enabled": True,
        "bot_token_env": "TELEGRAM_BOT_TOKEN",
        "chat_id_env": "TELEGRAM_CHAT_ID",
    },
    "cleanup": {
        "enabled": False,
        "requires_report_approval": True,
        "report_approved": False,
        "remove_source_videos": True,
        "remove_frames": True,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a runnable Nattome TikTok Batch Analysis Run skeleton."
    )
    parser.add_argument(
        "--mode",
        choices=sorted(MODE_DEFAULT_BATCH_SIZE),
        default="default",
        help="Run mode. Defaults to the 10-video Default Batch.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        help="Requested batch size. Defaults to the selected mode's standard size.",
    )
    parser.add_argument(
        "--runs-dir",
        type=Path,
        default=Path("runs") / "batch-analysis",
        help="Directory where timestamped Run Folders are created.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Optional JSON config file to merge into the recorded run configuration.",
    )
    parser.add_argument(
        "--candidates",
        type=Path,
        help="Apify output or local fixture JSON containing TikTok candidate metadata.",
    )
    parser.add_argument(
        "--timestamp",
        help="UTC timestamp for deterministic runs or tests, for example 2026-05-06T13:45:30Z.",
    )
    parser.add_argument(
        "--ffmpeg-bin",
        default="ffmpeg",
        help="FFmpeg executable used for Hybrid Timeline frame extraction.",
    )
    parser.add_argument(
        "--ocr-primary-bin",
        default="paddleocr",
        help="Primary OCR executable used for frame text extraction.",
    )
    parser.add_argument(
        "--ocr-fallback-bin",
        default="tesseract",
        help="Fallback OCR executable used when the primary OCR path is unavailable.",
    )
    parser.add_argument(
        "--transcription-bin",
        default="whisper",
        help="Whisper-style executable used for multilingual speech transcription.",
    )
    return parser.parse_args()


def parse_run_timestamp(value: str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc).replace(microsecond=0)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid timestamp: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def isoformat_z(timestamp: datetime) -> str:
    return timestamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_folder_name(timestamp: datetime, mode: str) -> str:
    return f"{timestamp.strftime('%Y%m%dT%H%M%SZ')}_{mode}"


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(config_path: Path | None) -> dict[str, Any]:
    if config_path is None:
        return DEFAULT_CONFIG
    if not config_path.exists():
        raise FileNotFoundError(f"required config file not found: {config_path}")
    try:
        loaded = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid config JSON: {config_path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise ValueError(f"invalid config JSON: expected object at {config_path}")
    return deep_merge(DEFAULT_CONFIG, loaded)


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

    return reasons


def select_candidates(
    candidates: list[dict[str, Any]],
    configuration: dict[str, Any],
    run_timestamp: datetime,
    batch_size: int,
    candidates_path: Path | None,
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

    ranked = sorted(
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
        "requested_batch_size": batch_size,
        "input_candidate_count": len(candidates),
        "eligible_candidate_count": len(eligible),
        "selected_candidate_count": len(selected),
        "minimum_eligibility_filter": configuration["selection"],
        "selected_candidates": selected,
        "excluded_candidates": excluded,
    }


def write_selected_batch(run_folder: Path, selected_batch: dict[str, Any]) -> None:
    json_path = run_folder / "batch_outputs" / "json" / "selected_batch.json"
    json_path.write_text(
        json.dumps(selected_batch, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Selected Batch Preview",
        "",
        f"- Selected at: {selected_batch['selected_at']}",
        f"- Requested batch size: {selected_batch['requested_batch_size']}",
        f"- Input candidates: {selected_batch['input_candidate_count']}",
        f"- Eligible candidates: {selected_batch['eligible_candidate_count']}",
        f"- Selected candidates: {selected_batch['selected_candidate_count']}",
        "",
        "| Rank | ID | Views | Weighted ER | Relevance | Score | URL |",
        "|---:|---|---:|---:|---:|---:|---|",
    ]
    for candidate in selected_batch["selected_candidates"]:
        lines.append(
            "| {rank} | {id} | {views} | {er:.4f} | {relevance:.4f} | {score:.4f} | {url} |".format(
                rank=candidate["rank"],
                id=candidate["id"],
                views=candidate["play_count"],
                er=candidate["weighted_engagement_rate"],
                relevance=candidate["nattome_relevance_score"],
                score=candidate["selection_score"],
                url=candidate["url"],
            )
        )
    lines.extend(["", "## Excluded Candidates", ""])
    for candidate in selected_batch["excluded_candidates"]:
        lines.append(f"- `{candidate['id']}`: {candidate['reason']}")

    markdown_path = run_folder / "batch_outputs" / "markdown" / "selected_batch.md"
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def safe_folder_token(value: Any) -> str:
    token = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in str(value or "unknown"))
    return token.strip("-") or "unknown"


def source_video_filename(source: str) -> str:
    parsed = urlparse(source)
    suffix = Path(unquote(parsed.path)).suffix if parsed.scheme else Path(source).suffix
    return f"source_video{suffix or '.mp4'}"


def copy_or_download_video(source: str, destination: Path) -> dict[str, Any]:
    if not source:
        return {
            "status": "missing",
            "reason": "no downloadable video source was provided in candidate metadata",
        }

    parsed = urlparse(source)
    try:
        if parsed.scheme in ("http", "https"):
            with urlopen(source, timeout=60) as response:
                destination.write_bytes(response.read())
        else:
            source_path = Path(unquote(parsed.path)) if parsed.scheme == "file" else Path(source)
            if not source_path.exists():
                return {
                    "status": "failed",
                    "reason": f"download source does not exist: {source}",
                    "source": source,
                }
            shutil.copyfile(source_path, destination)
    except Exception as exc:
        return {
            "status": "failed",
            "reason": str(exc),
            "source": source,
        }

    return {
        "status": "downloaded",
        "source": source,
        "artifact": destination.name,
        "bytes": destination.stat().st_size,
    }


def write_evidence_bundles(
    run_folder: Path,
    selected_batch: dict[str, Any],
    ffmpeg_bin: str,
    ocr_primary_bin: str,
    ocr_fallback_bin: str,
    transcription_bin: str,
) -> dict[str, Any]:
    bundles_root = run_folder / "evidence_bundles"
    index_entries = []

    for candidate in selected_batch["selected_candidates"]:
        candidate_id = candidate.get("id") or f"rank-{candidate['rank']}"
        bundle_relative = Path("evidence_bundles") / (
            f"{candidate['rank']:03d}_{safe_folder_token(candidate_id)}"
        )
        bundle_folder = run_folder / bundle_relative
        artifacts_folder = bundle_folder / "artifacts"
        artifacts_folder.mkdir(parents=True, exist_ok=False)

        (bundle_folder / "source_metadata.json").write_text(
            json.dumps(candidate, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        video_source = candidate.get("video_download_url") or ""
        video_artifact_path = artifacts_folder / source_video_filename(video_source)
        download_status = copy_or_download_video(video_source, video_artifact_path)
        if download_status["status"] != "downloaded" and video_artifact_path.exists():
            video_artifact_path.unlink()
        (bundle_folder / "download_status.json").write_text(
            json.dumps(download_status, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        source_video_exists = download_status["status"] == "downloaded"
        bundle_index = {
            "candidate_id": candidate_id,
            "rank": candidate["rank"],
            "bundle_folder": str(bundle_relative),
            "original_tiktok_url": candidate["url"],
            "source_metadata": str(bundle_relative / "source_metadata.json"),
            "download_status": download_status,
            "artifacts": {
                "source_video": {
                    "exists": source_video_exists,
                    "path": str(bundle_relative / "artifacts" / download_status["artifact"])
                    if source_video_exists
                    else None,
                }
            },
        }
        timeline_status = write_hybrid_timeline(
            bundle_folder,
            video_artifact_path if source_video_exists else None,
            candidate,
            ffmpeg_bin=ffmpeg_bin,
        )
        bundle_index["artifacts"]["hybrid_timeline"] = {
            "exists": timeline_status["status"] == "extracted",
            "path": str(bundle_relative / "hybrid_timeline.json"),
            "frame_count": timeline_status["frame_count"],
            "status": timeline_status["status"],
        }
        ocr_status = write_ocr_evidence(
            bundle_folder,
            ocr_primary_bin=ocr_primary_bin,
            ocr_fallback_bin=ocr_fallback_bin,
        )
        bundle_index["artifacts"]["ocr_evidence"] = {
            "exists": ocr_status["status"] == "completed",
            "path": str(bundle_relative / "ocr_evidence.json"),
            "frame_count": ocr_status["frame_count"],
            "text_frame_count": ocr_status["text_frame_count"],
            "status": ocr_status["status"],
        }
        transcript_status = write_transcript_evidence(
            bundle_folder,
            video_artifact_path if source_video_exists else None,
            ffmpeg_bin=ffmpeg_bin,
            transcription_bin=transcription_bin,
        )
        bundle_index["artifacts"]["audio"] = {
            "exists": transcript_status["audio_exists"],
            "path": str(bundle_relative / "artifacts" / "audio" / "source_audio.wav")
            if transcript_status["audio_exists"]
            else None,
            "status": transcript_status["audio_status"],
        }
        bundle_index["artifacts"]["transcript_evidence"] = {
            "exists": transcript_status["status"] == "completed",
            "path": str(bundle_relative / "transcript_evidence.json"),
            "segment_count": transcript_status["segment_count"],
            "status": transcript_status["status"],
        }
        audio_analysis_status = write_baseline_audio_analysis(bundle_folder, candidate)
        bundle_index["artifacts"]["baseline_audio_analysis"] = {
            "exists": audio_analysis_status["status"] == "completed",
            "path": str(bundle_relative / "baseline_audio_analysis.json"),
            "status": audio_analysis_status["status"],
        }
        claim_safety_status = write_claim_safety_review(bundle_folder)
        bundle_index["artifacts"]["claim_safety_review"] = {
            "exists": claim_safety_status["status"] == "completed",
            "path": str(bundle_relative / "claim_safety_review.json"),
            "status": claim_safety_status["status"],
            "flagged_count": claim_safety_status["flagged_count"],
        }
        evidence_quality = write_evidence_quality(bundle_folder, candidate)
        bundle_index["artifacts"]["evidence_quality"] = {
            "exists": evidence_quality["status"] == "completed",
            "path": str(bundle_relative / "evidence_quality.json"),
            "status": evidence_quality["status"],
            "score": evidence_quality["score"],
            "manual_review_required": evidence_quality["manual_review_required"],
        }
        report_status = write_video_evidence_report(bundle_folder, candidate)
        bundle_index["artifacts"]["video_evidence_report"] = {
            "exists": report_status["status"] == "completed",
            "path": str(bundle_relative / "video_evidence_report.md"),
            "status": report_status["status"],
        }
        (bundle_folder / "evidence_bundle_index.json").write_text(
            json.dumps(bundle_index, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        index_entries.append(bundle_index)

    evidence_index = {
        "created_at": selected_batch["selected_at"],
        "bundle_count": len(index_entries),
        "bundles": index_entries,
    }
    (bundles_root / "index.json").write_text(
        json.dumps(evidence_index, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return evidence_index


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


def normalized_timestamp(value: float) -> int | float:
    if value.is_integer():
        return int(value)
    return round(value, 3)


def hybrid_timeline_samples(duration_seconds: float | None) -> list[dict[str, Any]]:
    duration = duration_seconds if duration_seconds is not None else 3.0
    baseline_count = max(math.ceil(duration), 1)
    samples_by_timestamp: dict[float, str] = {
        float(second): "baseline_one_second" for second in range(baseline_count)
    }

    for timestamp in (0.5, 1.5, 2.5):
        if timestamp < duration:
            samples_by_timestamp.setdefault(timestamp, "hook_first_three_seconds")

    return [
        {
            "timestamp_seconds": normalized_timestamp(timestamp),
            "sampling_reason": samples_by_timestamp[timestamp],
        }
        for timestamp in sorted(samples_by_timestamp)
    ]


def timestamp_filename_token(timestamp_seconds: int | float) -> str:
    return f"{int(round(float(timestamp_seconds) * 1000)):06d}ms"


def write_hybrid_timeline(
    bundle_folder: Path,
    source_video_path: Path | None,
    candidate: dict[str, Any],
    ffmpeg_bin: str,
) -> dict[str, Any]:
    frames_folder = bundle_folder / "artifacts" / "frames"
    timeline_path = bundle_folder / "hybrid_timeline.json"
    duration_seconds = parse_duration_seconds(candidate)
    source_video_relative = (
        str(source_video_path.relative_to(bundle_folder)).replace("\\", "/")
        if source_video_path is not None
        else None
    )

    timeline: dict[str, Any] = {
        "status": "skipped",
        "source_video": source_video_relative,
        "duration_seconds": duration_seconds,
        "sampling_strategy": {
            "baseline_interval_seconds": 1,
            "hook_extra_timestamps_seconds": [0.5, 1.5, 2.5],
        },
        "extension_points": {
            "text_change_samples": "not_implemented",
            "scene_change_samples": "not_implemented",
        },
        "frames": [],
    }

    if source_video_path is None:
        timeline["reason"] = "source video artifact is missing"
        timeline_path.write_text(
            json.dumps(timeline, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return {"status": timeline["status"], "frame_count": 0}

    frames_folder.mkdir(parents=True, exist_ok=True)
    for sample in hybrid_timeline_samples(duration_seconds):
        filename = f"frame_{timestamp_filename_token(sample['timestamp_seconds'])}.jpg"
        frame_path = frames_folder / filename
        command = [
            ffmpeg_bin,
            "-y",
            "-ss",
            str(sample["timestamp_seconds"]),
            "-i",
            str(source_video_path),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(frame_path),
        ]
        try:
            completed = subprocess.run(command, text=True, capture_output=True, timeout=60)
        except FileNotFoundError:
            timeline["status"] = "failed"
            timeline["reason"] = f"FFmpeg executable not found: {ffmpeg_bin}"
            break
        except subprocess.TimeoutExpired:
            timeline["status"] = "failed"
            timeline["reason"] = f"FFmpeg timed out at {sample['timestamp_seconds']} seconds"
            break

        if completed.returncode != 0:
            timeline["status"] = "failed"
            timeline["reason"] = completed.stderr.strip() or "FFmpeg frame extraction failed"
            break

        timeline["frames"].append(
            {
                "timestamp_seconds": sample["timestamp_seconds"],
                "frame_path": str(frame_path.relative_to(bundle_folder)).replace("\\", "/"),
                "sampling_reason": sample["sampling_reason"],
            }
        )

    if timeline["frames"] and timeline.get("status") == "skipped":
        timeline["status"] = "extracted"
    timeline_path.write_text(
        json.dumps(timeline, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"status": timeline["status"], "frame_count": len(timeline["frames"])}


OCR_LANGUAGES = [
    "English",
    "Malay",
    "Simplified Chinese",
    "Traditional Chinese",
    "mixed-language text",
]


def ocr_command(engine: str, executable: str, frame_path: Path) -> list[str]:
    if engine == "paddleocr":
        return [executable, "--image_dir", str(frame_path), "--lang", "ch"]
    return [executable, str(frame_path), "stdout", "-l", "eng+msa+chi_sim+chi_tra"]


def run_ocr_command(executable: str, engine: str, frame_path: Path) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            ocr_command(engine, executable, frame_path),
            text=True,
            capture_output=True,
            timeout=60,
        )
    except FileNotFoundError:
        return {
            "status": "tool_missing",
            "reason": f"{engine} executable not found: {executable}",
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "failed",
            "reason": f"{engine} timed out for {frame_path.name}",
        }

    if completed.returncode != 0:
        return {
            "status": "failed",
            "reason": completed.stderr.strip() or f"{engine} OCR failed",
        }

    return {
        "status": "completed",
        "text": completed.stdout.strip(),
    }


def read_timeline(bundle_folder: Path) -> dict[str, Any] | None:
    timeline_path = bundle_folder / "hybrid_timeline.json"
    if not timeline_path.exists():
        return None
    try:
        loaded = json.loads(timeline_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, dict) else None


def write_ocr_evidence(
    bundle_folder: Path,
    ocr_primary_bin: str,
    ocr_fallback_bin: str,
) -> dict[str, Any]:
    ocr_path = bundle_folder / "ocr_evidence.json"
    timeline = read_timeline(bundle_folder)
    evidence: dict[str, Any] = {
        "status": "skipped",
        "engine": {
            "primary": "paddleocr",
            "fallback": "tesseract",
            "selected": None,
        },
        "languages_requested": OCR_LANGUAGES,
        "frames": [],
        "summary": {
            "frame_count": 0,
            "text_frame_count": 0,
            "combined_text": "",
        },
    }

    if timeline is None:
        evidence["reason"] = "hybrid_timeline.json is missing or invalid"
        ocr_path.write_text(
            json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return {"status": evidence["status"], "frame_count": 0, "text_frame_count": 0}

    timeline_frames = timeline.get("frames") if isinstance(timeline.get("frames"), list) else []
    if timeline.get("status") != "extracted" or not timeline_frames:
        evidence["reason"] = "no extracted timeline frames are available for OCR"
        ocr_path.write_text(
            json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return {"status": evidence["status"], "frame_count": 0, "text_frame_count": 0}

    selected_engine = None
    last_error = None
    for frame in timeline_frames:
        frame_path = bundle_folder / str(frame["frame_path"])
        result = run_ocr_command(ocr_primary_bin, "paddleocr", frame_path)
        engine = "paddleocr"
        if result["status"] != "completed":
            last_error = result["reason"]
            result = run_ocr_command(ocr_fallback_bin, "tesseract", frame_path)
            engine = "tesseract"

        if result["status"] != "completed":
            evidence["status"] = "failed"
            evidence["reason"] = (
                "OCR tooling failed or is missing. "
                f"Tried PaddleOCR ({ocr_primary_bin}) and Tesseract ({ocr_fallback_bin}). "
                f"Last error: {result['reason']}"
            )
            if last_error:
                evidence["primary_error"] = last_error
            break

        selected_engine = selected_engine or engine
        text = result["text"]
        evidence["frames"].append(
            {
                "timestamp_seconds": frame["timestamp_seconds"],
                "frame_path": frame["frame_path"],
                "sampling_reason": frame["sampling_reason"],
                "ocr_text": text,
                "confidence": None,
                "engine": engine,
                "status": "completed",
            }
        )

    evidence["engine"]["selected"] = selected_engine
    if evidence["frames"] and evidence.get("status") == "skipped":
        evidence["status"] = "completed"
    texts = [frame["ocr_text"] for frame in evidence["frames"] if frame["ocr_text"]]
    evidence["summary"] = {
        "frame_count": len(evidence["frames"]),
        "text_frame_count": len(texts),
        "combined_text": "\n".join(texts),
    }
    ocr_path.write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {
        "status": evidence["status"],
        "frame_count": len(evidence["frames"]),
        "text_frame_count": len(texts),
    }


TRANSCRIPTION_LANGUAGES = [
    "English",
    "Malay",
    "Mandarin Chinese",
    "code-mixed English-Malay-Chinese",
]


def extract_audio(
    source_video_path: Path,
    audio_path: Path,
    ffmpeg_bin: str,
) -> dict[str, Any]:
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg_bin,
        "-y",
        "-i",
        str(source_video_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(audio_path),
    ]
    try:
        completed = subprocess.run(command, text=True, capture_output=True, timeout=60)
    except FileNotFoundError:
        return {
            "status": "failed",
            "reason": f"FFmpeg executable not found: {ffmpeg_bin}",
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "failed",
            "reason": "FFmpeg timed out during audio extraction",
        }

    if completed.returncode != 0:
        return {
            "status": "failed",
            "reason": completed.stderr.strip() or "FFmpeg audio extraction failed",
        }

    return {
        "status": "extracted",
        "path": str(audio_path),
    }


def run_transcription_command(transcription_bin: str, audio_path: Path) -> dict[str, Any]:
    command = [
        transcription_bin,
        str(audio_path),
        "--language",
        "auto",
        "--task",
        "transcribe",
    ]
    try:
        completed = subprocess.run(command, text=True, capture_output=True, timeout=120)
    except FileNotFoundError:
        return {
            "status": "tool_missing",
            "reason": f"transcription executable not found: {transcription_bin}",
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "failed",
            "reason": "transcription command timed out",
        }

    if completed.returncode != 0:
        return {
            "status": "failed",
            "reason": completed.stderr.strip() or "transcription command failed",
        }

    return {
        "status": "completed",
        "stdout": completed.stdout.strip(),
    }


def parse_transcript_segments(stdout: str) -> tuple[str | None, list[dict[str, Any]]]:
    if not stdout:
        return None, []
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return None, [
            {
                "start_seconds": None,
                "end_seconds": None,
                "text": stdout,
                "confidence": None,
                "language": None,
            }
        ]

    if not isinstance(payload, dict):
        return None, []

    language = payload.get("language") if isinstance(payload.get("language"), str) else None
    raw_segments = payload.get("segments")
    if not isinstance(raw_segments, list):
        text = str(payload.get("text") or "").strip()
        return language, [
            {
                "start_seconds": None,
                "end_seconds": None,
                "text": text,
                "confidence": payload.get("confidence"),
                "language": language,
            }
        ] if text else []

    segments = []
    for segment in raw_segments:
        if not isinstance(segment, dict):
            continue
        text = str(segment.get("text") or "").strip()
        if not text:
            continue
        segments.append(
            {
                "start_seconds": segment.get("start"),
                "end_seconds": segment.get("end"),
                "text": text,
                "confidence": segment.get("confidence"),
                "language": segment.get("language") or language,
            }
        )
    return language, segments


def write_transcript_evidence(
    bundle_folder: Path,
    source_video_path: Path | None,
    ffmpeg_bin: str,
    transcription_bin: str,
) -> dict[str, Any]:
    transcript_path = bundle_folder / "transcript_evidence.json"
    audio_path = bundle_folder / "artifacts" / "audio" / "source_audio.wav"
    source_video_relative = (
        str(source_video_path.relative_to(bundle_folder)).replace("\\", "/")
        if source_video_path is not None
        else None
    )
    audio_relative = str(audio_path.relative_to(bundle_folder)).replace("\\", "/")
    evidence: dict[str, Any] = {
        "status": "skipped",
        "source_video": source_video_relative,
        "audio_artifact": None,
        "engine": {
            "style": "whisper",
            "selected": None,
        },
        "languages_requested": TRANSCRIPTION_LANGUAGES,
        "segments": [],
        "summary": {
            "segment_count": 0,
            "combined_text": "",
            "has_confidence_metadata": False,
        },
    }

    if source_video_path is None:
        evidence["reason"] = "source video artifact is missing"
        transcript_path.write_text(
            json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return {
            "status": evidence["status"],
            "segment_count": 0,
            "audio_exists": False,
            "audio_status": "skipped",
        }

    audio_status = extract_audio(source_video_path, audio_path, ffmpeg_bin)
    if audio_status["status"] != "extracted":
        evidence["status"] = "failed"
        evidence["reason"] = audio_status["reason"]
        transcript_path.write_text(
            json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return {
            "status": evidence["status"],
            "segment_count": 0,
            "audio_exists": False,
            "audio_status": "failed",
        }

    evidence["audio_artifact"] = audio_relative
    result = run_transcription_command(transcription_bin, audio_path)
    if result["status"] != "completed":
        evidence["status"] = "failed"
        evidence["reason"] = (
            "Transcription tooling failed or is missing. "
            f"Tried Whisper-style executable ({transcription_bin}). "
            f"Last error: {result['reason']}"
        )
        transcript_path.write_text(
            json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return {
            "status": evidence["status"],
            "segment_count": 0,
            "audio_exists": audio_path.exists(),
            "audio_status": "extracted",
        }

    language, segments = parse_transcript_segments(result["stdout"])
    evidence["status"] = "completed"
    evidence["engine"]["selected"] = "whisper"
    evidence["language_detected"] = language
    evidence["segments"] = segments
    texts = [segment["text"] for segment in segments if segment["text"]]
    evidence["summary"] = {
        "segment_count": len(segments),
        "combined_text": "\n".join(texts),
        "has_confidence_metadata": any(
            segment.get("confidence") is not None for segment in segments
        ),
    }
    transcript_path.write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {
        "status": evidence["status"],
        "segment_count": len(segments),
        "audio_exists": audio_path.exists(),
        "audio_status": "extracted",
    }


def read_json_object(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, dict) else None


def infer_audio_format(candidate: dict[str, Any], transcript: dict[str, Any] | None) -> str:
    hint = candidate.get("audio_format_hint")
    if hint:
        return str(hint)

    transcript_text = ""
    if transcript:
        summary = transcript.get("summary")
        if isinstance(summary, dict):
            transcript_text = str(summary.get("combined_text") or "")

    reused = candidate.get("is_reused_sound")
    if reused is True:
        return "reused_sound"
    if transcript_text:
        return "voiceover"
    if candidate.get("sound_title"):
        return "music_only"
    return "unknown"


def infer_audio_mood(candidate: dict[str, Any], transcript: dict[str, Any] | None) -> str:
    if candidate.get("audio_mood"):
        return str(candidate["audio_mood"])
    if transcript and transcript.get("status") == "completed":
        return "informational"
    if candidate.get("sound_title"):
        return "metadata_only"
    return "unknown"


def infer_hook_support(transcript: dict[str, Any] | None, audio_format: str) -> str:
    segments = transcript.get("segments") if isinstance(transcript, dict) else []
    if isinstance(segments, list):
        for segment in segments:
            if not isinstance(segment, dict):
                continue
            start = segment.get("start_seconds")
            text = str(segment.get("text") or "").strip()
            if text and (start is None or float(start) <= 3):
                return f"spoken hook supports first three seconds: {text}"
    if audio_format == "reused_sound":
        return "reused sound may support recognition, but no transcript hook was captured"
    if audio_format == "music_only":
        return "music-only hook support requires later Deep Sound Research"
    return "no audio hook evidence captured yet"


def nattome_audio_recommendation(audio_format: str, hook_support: str) -> dict[str, str]:
    if "no audio hook evidence" in hook_support:
        return {
            "action": "avoid",
            "reason": "No usable audio evidence was captured for adaptation.",
        }
    if audio_format in {"talking_head", "voiceover", "reused_sound", "music_only"}:
        return {
            "action": "adapt",
            "reason": "Use the audio style as inspiration while rewriting claims for Nattome-safe language.",
        }
    return {
        "action": "adapt",
        "reason": "Audio evidence is limited; adapt only after human review.",
    }


def write_baseline_audio_analysis(
    bundle_folder: Path,
    candidate: dict[str, Any],
) -> dict[str, Any]:
    analysis_path = bundle_folder / "baseline_audio_analysis.json"
    transcript = read_json_object(bundle_folder / "transcript_evidence.json")
    audio_format = infer_audio_format(candidate, transcript)
    hook_support = infer_hook_support(transcript, audio_format)
    analysis = {
        "status": "completed",
        "sound": {
            "title": candidate.get("sound_title"),
            "author": candidate.get("sound_author"),
            "is_reused_sound": candidate.get("is_reused_sound"),
        },
        "audio_format": audio_format,
        "mood": infer_audio_mood(candidate, transcript),
        "hook_support": hook_support,
        "nattome_recommendation": nattome_audio_recommendation(audio_format, hook_support),
        "evidence_basis": {
            "source_metadata": "source_metadata.json",
            "transcript_evidence": "transcript_evidence.json",
        },
        "deep_sound_research": {
            "status": "not_implemented",
        },
    }
    analysis_path.write_text(
        json.dumps(analysis, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"status": analysis["status"]}


CLAIM_SAFETY_RULES = [
    {
        "category": "cure_claim",
        "patterns": [r"\bcures?\b", r"\bheals?\b", r"\beliminates?\b"],
        "action": "avoid",
        "reason": "Nattome should not reuse cure or disease-treatment promises.",
        "nattome_safe_language": "Talk about supporting digestive comfort and daily gut routines.",
    },
    {
        "category": "guaranteed_outcome",
        "patterns": [r"\bguarantee(?:d|s)?\b", r"\b100%\b", r"\bwill definitely\b"],
        "action": "soften",
        "reason": "Guaranteed outcomes overpromise individual results.",
        "nattome_safe_language": "Use possibility language such as may help support comfort.",
    },
    {
        "category": "one_night_fix",
        "patterns": [r"\bovernight\b", r"\bone[- ]night\b", r"\bin 24 hours\b"],
        "action": "reframe",
        "reason": "Fast-fix claims can imply unrealistic or unsubstantiated relief timing.",
        "nattome_safe_language": "Frame the angle around building a simple digestive routine.",
    },
    {
        "category": "cancer_prevention",
        "patterns": [r"\bprevent(?:s|ing)? cancer\b", r"\bstops? cancer\b", r"\bcancer prevention\b"],
        "action": "avoid",
        "reason": "Cancer prevention claims are high-risk medical claims.",
        "nattome_safe_language": "Do not connect Nattome content to cancer prevention.",
    },
    {
        "category": "zero_side_effect",
        "patterns": [r"\bzero side effects?\b", r"\bno side effects?\b", r"\bside-effect free\b"],
        "action": "avoid",
        "reason": "Absolute safety guarantees should not be reused without substantiation.",
        "nattome_safe_language": "Avoid safety guarantees; direct users to product labels and professional advice.",
    },
    {
        "category": "detox_or_cleanse",
        "patterns": [r"\bdetox(?:es|ing)?\b", r"\bcleanse(?:s|d|ing)?\b"],
        "action": "reframe",
        "reason": "Detox and cleanse language can sound pseudoscientific.",
        "nattome_safe_language": "Use digestive balance, comfort, or routine support language instead.",
    },
    {
        "category": "unverified_doctor_recommended",
        "patterns": [r"\bdoctor recommended\b", r"\brecommended by doctors?\b", r"\bdoctors? recommend\b"],
        "action": "soften",
        "reason": "Authority claims need verification before reuse.",
        "nattome_safe_language": "Use only verified professional endorsements approved for the campaign.",
    },
    {
        "category": "unsupported_clinical_percentage",
        "patterns": [
            r"\b\d{1,3}%[^.?!]*(?:clinically|proven|effective|results?|relief)",
            r"(?:clinically|proven|effective|results?|relief)[^.?!]*\b\d{1,3}%",
        ],
        "action": "avoid",
        "reason": "Clinical percentages require substantiation and approval.",
        "nattome_safe_language": "Remove unsupported percentages unless approved evidence is available.",
    },
    {
        "category": "aggressive_competitor_claim",
        "patterns": [
            r"\bbetter than (?:every |all )?competitors?\b",
            r"\bcompetitors? (?:are|is) (?:bad|toxic|useless)\b",
            r"\bstop buying\b",
        ],
        "action": "reframe",
        "reason": "Aggressive competitor claims can create brand and compliance risk.",
        "nattome_safe_language": "Compare consumer needs without attacking competitors.",
    },
]


def claim_evidence_sources(bundle_folder: Path) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    ocr = read_json_object(bundle_folder / "ocr_evidence.json")
    if isinstance(ocr, dict):
        frames = ocr.get("frames")
        if isinstance(frames, list):
            for frame in frames:
                if not isinstance(frame, dict):
                    continue
                text = str(frame.get("ocr_text") or "").strip()
                if not text:
                    continue
                sources.append(
                    {
                        "source": "ocr_evidence",
                        "timestamp_seconds": frame.get("timestamp_seconds"),
                        "text": text,
                    }
                )

    transcript = read_json_object(bundle_folder / "transcript_evidence.json")
    if isinstance(transcript, dict):
        segments = transcript.get("segments")
        if isinstance(segments, list):
            for segment in segments:
                if not isinstance(segment, dict):
                    continue
                text = str(segment.get("text") or "").strip()
                if not text:
                    continue
                sources.append(
                    {
                        "source": "transcript_evidence",
                        "timestamp_seconds": segment.get("start_seconds"),
                        "text": text,
                    }
                )
    return sources


def first_matching_claim_text(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(0).strip()
    return None


def write_claim_safety_review(bundle_folder: Path) -> dict[str, Any]:
    review_path = bundle_folder / "claim_safety_review.json"
    sources = claim_evidence_sources(bundle_folder)
    flagged_claims = []
    seen_categories = set()

    for rule in CLAIM_SAFETY_RULES:
        for source in sources:
            claim_text = first_matching_claim_text(source["text"], rule["patterns"])
            if not claim_text or rule["category"] in seen_categories:
                continue
            seen_categories.add(rule["category"])
            flagged_claims.append(
                {
                    "category": rule["category"],
                    "claim_text": claim_text,
                    "evidence_source": {
                        "artifact": source["source"],
                        "timestamp_seconds": source["timestamp_seconds"],
                    },
                    "guidance": {
                        "action": rule["action"],
                        "reason": rule["reason"],
                        "nattome_safe_language": rule["nattome_safe_language"],
                    },
                }
            )
            break

    review = {
        "status": "completed",
        "source_artifacts": ["ocr_evidence.json", "transcript_evidence.json"],
        "flagged_claims": flagged_claims,
        "summary": {
            "flagged_count": len(flagged_claims),
            "guidance_actions": sorted(
                {claim["guidance"]["action"] for claim in flagged_claims}
            ),
        },
    }
    review_path.write_text(
        json.dumps(review, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {
        "status": review["status"],
        "flagged_count": len(flagged_claims),
    }


def truthy_metadata_flag(candidate: dict[str, Any], *keys: str) -> bool:
    for key in keys:
        value = candidate.get(key)
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.strip().lower() in {"true", "yes", "1"}:
            return True
    return False


def transcript_has_first_three_second_hook(transcript: dict[str, Any] | None) -> bool:
    segments = transcript.get("segments") if isinstance(transcript, dict) else []
    if not isinstance(segments, list):
        return False
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        text = str(segment.get("text") or "").strip()
        if not text:
            continue
        start = segment.get("start_seconds")
        if start is None:
            return True
        try:
            if float(start) <= 3:
                return True
        except (TypeError, ValueError):
            continue
    return False


def ocr_has_first_three_second_text(ocr: dict[str, Any] | None) -> bool:
    frames = ocr.get("frames") if isinstance(ocr, dict) else []
    if not isinstance(frames, list):
        return False
    for frame in frames:
        if not isinstance(frame, dict):
            continue
        text = str(frame.get("ocr_text") or "").strip()
        if not text:
            continue
        timestamp = frame.get("timestamp_seconds")
        try:
            if timestamp is None or float(timestamp) <= 3:
                return True
        except (TypeError, ValueError):
            continue
    return False


def audio_analysis_has_hook_support(audio_analysis: dict[str, Any] | None) -> bool:
    if not isinstance(audio_analysis, dict):
        return False
    hook_support = str(audio_analysis.get("hook_support") or "").lower()
    if not hook_support:
        return False
    weak_phrases = (
        "no audio hook evidence",
        "requires later deep sound research",
        "no transcript hook was captured",
    )
    return not any(phrase in hook_support for phrase in weak_phrases)


def transcript_language_detected(transcript: dict[str, Any] | None) -> bool:
    if not isinstance(transcript, dict):
        return False
    if transcript.get("language_detected"):
        return True
    segments = transcript.get("segments")
    if not isinstance(segments, list):
        return False
    return any(isinstance(segment, dict) and segment.get("language") for segment in segments)


def transcript_confidence_is_usable(transcript: dict[str, Any] | None) -> bool:
    if not isinstance(transcript, dict):
        return False
    summary = transcript.get("summary")
    if isinstance(summary, dict) and not summary.get("has_confidence_metadata"):
        return False
    segments = transcript.get("segments")
    if not isinstance(segments, list) or not segments:
        return False
    confidences = [
        segment.get("confidence")
        for segment in segments
        if isinstance(segment, dict) and segment.get("confidence") is not None
    ]
    if not confidences:
        return False
    usable = []
    for confidence in confidences:
        try:
            usable.append(float(confidence) >= 0.7)
        except (TypeError, ValueError):
            usable.append(False)
    return all(usable)


def evidence_quality_level(
    critical_failures: list[str],
    review_reasons: list[str],
) -> str:
    if critical_failures:
        return "low"
    if review_reasons:
        return "medium"
    return "high"


def evidence_quality_reason(
    level: str,
    critical_failures: list[str],
    review_reasons: list[str],
) -> str:
    reason_source = critical_failures if critical_failures else review_reasons
    if reason_source:
        return "; ".join(reason_source[:3])
    if level == "high":
        return "video, timeline, OCR, transcript, and audio evidence are complete"
    return "evidence requires manual review"


def write_evidence_quality(
    bundle_folder: Path,
    candidate: dict[str, Any],
) -> dict[str, Any]:
    quality_path = bundle_folder / "evidence_quality.json"
    download_status = read_json_object(bundle_folder / "download_status.json") or {}
    timeline = read_json_object(bundle_folder / "hybrid_timeline.json")
    ocr = read_json_object(bundle_folder / "ocr_evidence.json")
    transcript = read_json_object(bundle_folder / "transcript_evidence.json")
    audio_analysis = read_json_object(bundle_folder / "baseline_audio_analysis.json")
    claim_safety_review = read_json_object(bundle_folder / "claim_safety_review.json")
    visible_text_expected = truthy_metadata_flag(
        candidate,
        "visible_text_expected",
        "has_visible_text",
        "text_overlay_expected",
    )

    critical_failures: list[str] = []
    review_reasons: list[str] = []
    manual_review_reasons: list[str] = []

    download_ok = download_status.get("status") == "downloaded"
    if not download_ok:
        critical_failures.append("video download failed")

    timeline_ok = isinstance(timeline, dict) and timeline.get("status") == "extracted"
    if not timeline_ok:
        critical_failures.append("timeline extraction incomplete")

    ocr_status = ocr.get("status") if isinstance(ocr, dict) else None
    ocr_text_frame_count = 0
    if isinstance(ocr, dict) and isinstance(ocr.get("summary"), dict):
        try:
            ocr_text_frame_count = int(ocr["summary"].get("text_frame_count") or 0)
        except (TypeError, ValueError):
            ocr_text_frame_count = 0
    ocr_visible_text_failed = visible_text_expected and (
        ocr_status != "completed" or ocr_text_frame_count == 0
    )
    if ocr_visible_text_failed:
        critical_failures.append("OCR failed on visible text")
        manual_review_reasons.append("ocr_failed_on_visible_text")
    elif ocr_status != "completed":
        review_reasons.append("OCR evidence incomplete")

    transcript_status = transcript.get("status") if isinstance(transcript, dict) else None
    transcript_language_ok = transcript_language_detected(transcript)
    transcript_confidence_ok = transcript_confidence_is_usable(transcript)
    if transcript_status != "completed":
        critical_failures.append("transcript failed")
        manual_review_reasons.append("transcript_language_detection_failed")
    elif not transcript_language_ok:
        review_reasons.append("language detection failed")
        manual_review_reasons.append("transcript_language_detection_failed")
    elif not transcript_confidence_ok:
        review_reasons.append("transcript confidence is incomplete or low")

    first_three_second_hook_clear = (
        ocr_has_first_three_second_text(ocr)
        or transcript_has_first_three_second_hook(transcript)
        or audio_analysis_has_hook_support(audio_analysis)
    )
    if not first_three_second_hook_clear:
        review_reasons.append("first-three-second hook unclear")
        manual_review_reasons.append("first_three_second_hook_unclear")

    audio_ok = isinstance(audio_analysis, dict) and audio_analysis.get("status") == "completed"
    if not audio_ok:
        review_reasons.append("audio analysis incomplete")

    flagged_claim_count = 0
    if isinstance(claim_safety_review, dict) and isinstance(
        claim_safety_review.get("summary"), dict
    ):
        try:
            flagged_claim_count = int(claim_safety_review["summary"].get("flagged_count") or 0)
        except (TypeError, ValueError):
            flagged_claim_count = 0
    if flagged_claim_count:
        review_reasons.append("claim safety review flagged unsafe claims")
        manual_review_reasons.append("claim_safety_review_flagged_claims")

    level = evidence_quality_level(critical_failures, review_reasons)
    if level in {"medium", "low"}:
        manual_review_reasons.insert(0, f"evidence_quality_{level}")

    quality = {
        "status": "completed",
        "evidence_quality_score": {
            "level": level,
            "reason": evidence_quality_reason(level, critical_failures, review_reasons),
        },
        "manual_review_flag": {
            "required": bool(manual_review_reasons),
            "reasons": list(dict.fromkeys(manual_review_reasons)),
        },
        "checks": {
            "video_download": {
                "status": download_status.get("status", "missing"),
                "passed": download_ok,
            },
            "timeline_completeness": {
                "status": timeline.get("status") if isinstance(timeline, dict) else "missing",
                "passed": timeline_ok,
            },
            "ocr_quality": {
                "status": ocr_status or "missing",
                "visible_text_expected": visible_text_expected,
                "text_frame_count": ocr_text_frame_count,
                "passed": ocr_status == "completed" and not ocr_visible_text_failed,
            },
            "transcript_quality": {
                "status": transcript_status or "missing",
                "language_detected": transcript_language_ok,
                "confidence_usable": transcript_confidence_ok,
                "passed": (
                    transcript_status == "completed"
                    and transcript_language_ok
                    and transcript_confidence_ok
                ),
            },
            "first_three_second_hook": {
                "clear": first_three_second_hook_clear,
            },
            "audio_analysis": {
                "status": audio_analysis.get("status")
                if isinstance(audio_analysis, dict)
                else "missing",
                "passed": audio_ok,
            },
            "claim_uncertainty": {
                "status": "flagged" if flagged_claim_count else "clear",
                "flagged_count": flagged_claim_count,
            },
        },
    }
    quality_path.write_text(
        json.dumps(quality, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {
        "status": quality["status"],
        "score": level,
        "manual_review_required": quality["manual_review_flag"]["required"],
    }


def compact_markdown_text(value: Any, fallback: str = "Not available") -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    return " ".join(text.split())


def report_status_line(artifact: dict[str, Any] | None, artifact_name: str) -> str:
    if not isinstance(artifact, dict):
        return f"{artifact_name} evidence not available."
    status = artifact.get("status", "missing")
    if status in {"completed", "extracted", "downloaded"}:
        return f"{artifact_name} evidence captured in `{artifact_name}.json`."
    reason = compact_markdown_text(artifact.get("reason"), "No reason recorded")
    return f"{artifact_name} evidence not available: {reason}."


def first_ocr_summary(ocr: dict[str, Any] | None) -> str:
    if not isinstance(ocr, dict) or ocr.get("status") != "completed":
        return report_status_line(ocr, "OCR")
    summary = ocr.get("summary") if isinstance(ocr.get("summary"), dict) else {}
    combined = compact_markdown_text(summary.get("combined_text"), "No OCR text captured")
    return (
        f"OCR completed across {summary.get('frame_count', 0)} frame(s); "
        f"{summary.get('text_frame_count', 0)} frame(s) contained text. Summary: {combined}"
    )


def first_transcript_summary(transcript: dict[str, Any] | None) -> str:
    if not isinstance(transcript, dict) or transcript.get("status") != "completed":
        return report_status_line(transcript, "Transcript")
    summary = transcript.get("summary") if isinstance(transcript.get("summary"), dict) else {}
    combined = compact_markdown_text(summary.get("combined_text"), "No transcript text captured")
    language = transcript.get("language_detected") or "not detected"
    return (
        f"Transcript completed with language `{language}` and "
        f"{summary.get('segment_count', 0)} segment(s). Summary: {combined}"
    )


def product_tie_in_for_candidate(candidate: dict[str, Any]) -> str:
    text = compact_markdown_text(candidate.get("caption"), "").lower()
    if any(term in text for term in ("reflux", "heartburn", "acid", "indigestion")):
        return "DR for faster relief moments around reflux, heartburn, or gastric discomfort."
    if any(term in text for term in ("repair", "recover", "recovery")):
        return "DH-R/recovery for deeper repair and recovery contexts."
    return "DH for daily digestive maintenance and routine support."


def avatar_for_candidate(candidate: dict[str, Any]) -> str:
    text = compact_markdown_text(candidate.get("caption"), "").lower()
    if any(term in text for term in ("reflux", "heartburn", "bloating", "gastric", "pain")):
        return "The Sufferer"
    if "family" in text or "child" in text:
        return "Family Caregiver"
    return "Maintainer"


def claim_guardrails(claim_review: dict[str, Any] | None) -> str:
    claims = claim_review.get("flagged_claims") if isinstance(claim_review, dict) else []
    if isinstance(claims, list) and claims:
        categories = ", ".join(
            sorted({str(claim.get("category")) for claim in claims if isinstance(claim, dict)})
        )
        return f"Do not reuse flagged claim categories directly: {categories}."
    return "Avoid cure, guaranteed outcome, overnight relief, detox, and unsupported clinical claims."


def write_video_evidence_report(
    bundle_folder: Path,
    candidate: dict[str, Any],
) -> dict[str, Any]:
    report_path = bundle_folder / "video_evidence_report.md"
    download_status = read_json_object(bundle_folder / "download_status.json")
    timeline = read_json_object(bundle_folder / "hybrid_timeline.json")
    ocr = read_json_object(bundle_folder / "ocr_evidence.json")
    transcript = read_json_object(bundle_folder / "transcript_evidence.json")
    audio_analysis = read_json_object(bundle_folder / "baseline_audio_analysis.json")
    claim_review = read_json_object(bundle_folder / "claim_safety_review.json")
    quality = read_json_object(bundle_folder / "evidence_quality.json")

    quality_score = quality.get("evidence_quality_score") if isinstance(quality, dict) else {}
    manual_review = quality.get("manual_review_flag") if isinstance(quality, dict) else {}
    checks = quality.get("checks") if isinstance(quality, dict) else {}
    first_three_check = (
        checks.get("first_three_second_hook") if isinstance(checks, dict) else {}
    )
    source_url = compact_markdown_text(candidate.get("url"), "")
    caption = compact_markdown_text(candidate.get("caption"))
    report_title = compact_markdown_text(candidate.get("id"), f"rank-{candidate.get('rank')}")

    lines = [
        f"# Video Evidence Report: {report_title}",
        "",
        "## Video Reference",
        "",
        f"- Source TikTok: [Source TikTok]({source_url})" if source_url else "- Source TikTok: Not available",
        f"- Caption: {caption}",
        f"- Creator: {compact_markdown_text(candidate.get('author_handle'))}",
        f"- Views: {candidate.get('play_count', 0)}",
        f"- Weighted engagement rate: {candidate.get('weighted_engagement_rate', 0)}",
        f"- Evidence Bundle: `{bundle_folder.name}/`",
        (
            "- Local evidence artifacts: `source_metadata.json`, `download_status.json`, "
            "`hybrid_timeline.json`, `ocr_evidence.json`, `transcript_evidence.json`, "
            "`baseline_audio_analysis.json`, `claim_safety_review.json`, `evidence_quality.json`"
        ),
        "",
        "## Executive Creative Read",
        "",
        (
            f"- Evidence quality: {quality_score.get('level', 'unknown')} - "
            f"{quality_score.get('reason', 'No reason recorded')}"
        ),
        (
            f"- Manual review required: {manual_review.get('required', False)} "
            f"({', '.join(manual_review.get('reasons', [])) if isinstance(manual_review.get('reasons'), list) else 'no reasons'})"
        ),
        "- Recommendation: Treat this as evidence-led inspiration, not a final script.",
        "",
        "## First 3 Seconds Hook Audit",
        "",
        (
            "- Hook clarity: clear based on captured evidence."
            if isinstance(first_three_check, dict) and first_three_check.get("clear")
            else "- Hook clarity: unclear from captured evidence."
        ),
    ]

    if not (isinstance(timeline, dict) and timeline.get("status") == "extracted"):
        lines.append("- This report does not claim video evidence was inspected because required artifacts are missing.")

    lines.extend(["", "## Hybrid Timeline", ""])
    if isinstance(timeline, dict) and timeline.get("status") == "extracted":
        lines.extend(["| Time | Frame | Sampling reason |", "| --- | --- | --- |"])
        for frame in timeline.get("frames", [])[:12]:
            if not isinstance(frame, dict):
                continue
            lines.append(
                f"| {frame.get('timestamp_seconds')} | `{frame.get('frame_path')}` | {frame.get('sampling_reason')} |"
            )
    else:
        reason = compact_markdown_text(
            timeline.get("reason") if isinstance(timeline, dict) else None,
            "artifact missing",
        )
        lines.append(f"Hybrid timeline evidence not available: {reason}.")

    lines.extend(
        [
            "",
            "## OCR Text Summary",
            "",
            first_ocr_summary(ocr),
            "",
            "## Speech Transcript Summary",
            "",
            first_transcript_summary(transcript),
            "",
            "## Audio/Music Trend Analysis",
            "",
        ]
    )
    if isinstance(audio_analysis, dict) and audio_analysis.get("status") == "completed":
        lines.extend(
            [
                f"- Audio format: {audio_analysis.get('audio_format', 'unknown')}",
                f"- Mood: {audio_analysis.get('mood', 'unknown')}",
                f"- Hook support: {audio_analysis.get('hook_support', 'not available')}",
                f"- Nattome audio action: {audio_analysis.get('nattome_recommendation', {}).get('action', 'review')}",
                "- Artifact: `baseline_audio_analysis.json`",
            ]
        )
    else:
        lines.append("Audio analysis evidence not available.")

    lines.extend(
        [
            "",
            "## Virality Breakdown",
            "",
            (
                f"- Viral signal: {candidate.get('play_count', 0)} views with "
                f"{candidate.get('weighted_engagement_rate', 0)} weighted engagement."
            ),
            f"- Nattome relevance score: {candidate.get('nattome_relevance_score', 0)}",
            "- Caution: Do not treat missing media evidence as proof of a creative mechanism.",
            "",
            "## Nattome POV",
            "",
            f"- Product fit: {product_tie_in_for_candidate(candidate)}",
            "- Reuse stance: Adapt the topic and structure only after claim guardrails are applied.",
            "",
            "## Shootable Angles",
            "",
            "### Angle 1: Digestive Comfort Routine Check",
            "",
            f"- Hook: Turn the creator topic into a safe question: `{caption}`",
            f"- Avatar: {avatar_for_candidate(candidate)}",
            "- Format: Talking-head explainer with simple on-screen text.",
            f"- Product tie-in: {product_tie_in_for_candidate(candidate)}",
            "- Script beats: problem moment; simple routine cue; product-safe support language; reminder to read labels.",
            "- CTA: Save this for your next meal routine.",
            f"- Claim guardrails: {claim_guardrails(claim_review)}",
            "",
            "## Claim Safety Review",
            "",
            "- Artifact: `claim_safety_review.json`",
        ]
    )
    claims = claim_review.get("flagged_claims") if isinstance(claim_review, dict) else []
    if isinstance(claims, list) and claims:
        for claim in claims:
            if not isinstance(claim, dict):
                continue
            guidance = claim.get("guidance") if isinstance(claim.get("guidance"), dict) else {}
            lines.append(
                f"- {claim.get('category')}: `{claim.get('claim_text')}` -> {guidance.get('action', 'review')}"
            )
    else:
        lines.append("- No unsafe claims were flagged from available OCR or transcript evidence.")

    lines.extend(
        [
            "",
            "## Evidence Quality",
            "",
            "- Artifact: `evidence_quality.json`",
            f"- Score: {quality_score.get('level', 'unknown')}",
            f"- Reason: {quality_score.get('reason', 'No reason recorded')}",
            (
                f"- Manual review flag: {manual_review.get('required', False)} "
                f"({', '.join(manual_review.get('reasons', [])) if isinstance(manual_review.get('reasons'), list) else 'no reasons'})"
            ),
        ]
    )

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": "completed"}


PRIORITY_SCORE_DIMENSIONS = [
    "viral_strength",
    "nattome_relevance",
    "evidence_confidence",
    "brand_safety",
    "ease_of_production",
    "product_fit",
]


def priority_score_points(candidate: dict[str, Any], bundle_folder: Path) -> dict[str, int]:
    quality = read_json_object(bundle_folder / "evidence_quality.json") or {}
    claim_review = read_json_object(bundle_folder / "claim_safety_review.json") or {}
    audio_analysis = read_json_object(bundle_folder / "baseline_audio_analysis.json") or {}

    views = int(candidate.get("play_count") or 0)
    engagement = float(candidate.get("weighted_engagement_rate") or 0)
    viral_strength = 1
    if views >= 250000 or engagement >= 0.15:
        viral_strength = 5
    elif views >= 100000 or engagement >= 0.10:
        viral_strength = 4
    elif views >= 50000 or engagement >= 0.06:
        viral_strength = 3
    elif views >= 10000 or engagement >= 0.03:
        viral_strength = 2

    relevance = float(candidate.get("nattome_relevance_score") or 0)
    nattome_relevance = max(1, min(5, math.ceil(relevance * 5)))

    quality_score = quality.get("evidence_quality_score") if isinstance(quality, dict) else {}
    quality_level = quality_score.get("level") if isinstance(quality_score, dict) else None
    evidence_confidence = {"high": 5, "medium": 3, "low": 1}.get(str(quality_level), 1)

    flagged_claims = claim_review.get("flagged_claims") if isinstance(claim_review, dict) else []
    flagged_count = len(flagged_claims) if isinstance(flagged_claims, list) else 0
    brand_safety = 5 if flagged_count == 0 else 3 if flagged_count <= 2 else 1

    audio_format = str(audio_analysis.get("audio_format") or candidate.get("audio_format_hint") or "").lower()
    if audio_format in {"talking_head", "voiceover", "original_voice"}:
        ease_of_production = 5
    elif audio_format in {"reused_sound", "music_only"}:
        ease_of_production = 3
    else:
        ease_of_production = 4

    product_fit_text = product_tie_in_for_candidate(candidate).lower()
    if any(product in product_fit_text for product in ("dr", "dh-r", "dh ")):
        product_fit = 5 if relevance >= 0.5 else 4
    else:
        product_fit = 3

    return {
        "viral_strength": viral_strength,
        "nattome_relevance": nattome_relevance,
        "evidence_confidence": evidence_confidence,
        "brand_safety": brand_safety,
        "ease_of_production": ease_of_production,
        "product_fit": product_fit,
    }


def hook_pattern_for_bundle(bundle_folder: Path) -> str:
    quality = read_json_object(bundle_folder / "evidence_quality.json") or {}
    checks = quality.get("checks") if isinstance(quality, dict) else {}
    hook_check = checks.get("first_three_second_hook") if isinstance(checks, dict) else {}
    if isinstance(hook_check, dict) and hook_check.get("clear"):
        return "Clear first-three-second problem hook"
    return "Unclear hook requiring manual review"


def emotional_trigger_for_candidate(candidate: dict[str, Any]) -> str:
    text = compact_markdown_text(candidate.get("caption"), "").lower()
    if any(term in text for term in ("bloating", "reflux", "heartburn", "pain", "gastric")):
        return "Digestive discomfort relief"
    if any(term in text for term in ("routine", "daily", "morning", "after meals")):
        return "Routine confidence"
    if any(term in text for term in ("warning", "mistake", "avoid")):
        return "Problem avoidance"
    return "Digestive-health curiosity"


def add_pattern(patterns: dict[str, set[str]], pattern: str, candidate_id: str) -> None:
    patterns.setdefault(pattern, set()).add(candidate_id)


def pattern_rows(patterns: dict[str, set[str]]) -> list[dict[str, Any]]:
    return [
        {
            "pattern": pattern,
            "video_count": len(candidate_ids),
            "candidate_ids": sorted(candidate_ids),
        }
        for pattern, candidate_ids in sorted(
            patterns.items(), key=lambda item: (-len(item[1]), item[0])
        )
    ]


def write_cross_video_pattern_summary(
    run_folder: Path,
    selected_batch: dict[str, Any],
    evidence_index: dict[str, Any],
) -> dict[str, Any]:
    hooks: dict[str, set[str]] = {}
    formats: dict[str, set[str]] = {}
    emotional_triggers: dict[str, set[str]] = {}
    audio_patterns: dict[str, set[str]] = {}
    risky_claims: dict[str, set[str]] = {}
    opportunities: dict[str, set[str]] = {}
    angle_rows = []

    candidates_by_id = {
        str(candidate.get("id")): candidate
        for candidate in selected_batch.get("selected_candidates", [])
        if isinstance(candidate, dict)
    }

    for bundle in evidence_index.get("bundles", []):
        if not isinstance(bundle, dict):
            continue
        candidate_id = str(bundle.get("candidate_id") or "")
        candidate = candidates_by_id.get(candidate_id)
        if not isinstance(candidate, dict):
            continue

        bundle_folder = run_folder / str(bundle.get("bundle_folder"))
        audio_analysis = read_json_object(bundle_folder / "baseline_audio_analysis.json") or {}
        claim_review = read_json_object(bundle_folder / "claim_safety_review.json") or {}
        quality = read_json_object(bundle_folder / "evidence_quality.json") or {}

        audio_format = str(
            audio_analysis.get("audio_format") or candidate.get("audio_format_hint") or "unknown"
        )
        hook_pattern = hook_pattern_for_bundle(bundle_folder)
        emotional_trigger = emotional_trigger_for_candidate(candidate)
        opportunity = product_tie_in_for_candidate(candidate)
        add_pattern(hooks, hook_pattern, candidate_id)
        add_pattern(formats, audio_format, candidate_id)
        add_pattern(emotional_triggers, emotional_trigger, candidate_id)
        add_pattern(
            audio_patterns,
            str(audio_analysis.get("hook_support") or "audio hook support not available"),
            candidate_id,
        )
        add_pattern(opportunities, opportunity, candidate_id)

        claims = claim_review.get("flagged_claims") if isinstance(claim_review, dict) else []
        if isinstance(claims, list) and claims:
            for claim in claims:
                if isinstance(claim, dict):
                    add_pattern(risky_claims, str(claim.get("category") or "unknown"), candidate_id)
        else:
            add_pattern(risky_claims, "No risky claims flagged from available evidence", candidate_id)

        dimensions = priority_score_points(candidate, bundle_folder)
        total = sum(dimensions.values())
        quality_score = quality.get("evidence_quality_score") if isinstance(quality, dict) else {}
        angle_rows.append(
            {
                "candidate_id": candidate_id,
                "source_tiktok_url": candidate.get("url"),
                "angle_title": "Digestive Comfort Routine Check",
                "hook": f"Turn this creator topic into a safe question: {compact_markdown_text(candidate.get('caption'))}",
                "avatar": avatar_for_candidate(candidate),
                "format": "Talking-head explainer with simple on-screen text.",
                "product_fit": opportunity,
                "recommended_angle": (
                    "Adapt the pain point and structure, then keep the product role to support language."
                ),
                "claim_guardrails": claim_guardrails(claim_review),
                "evidence_quality": quality_score.get("level", "unknown")
                if isinstance(quality_score, dict)
                else "unknown",
                "priority_score": {
                    "dimensions": dimensions,
                    "total": total,
                    "max_points": 30,
                },
                "why": (
                    f"{total}/30 score balances viral signal, Nattome fit, evidence confidence, "
                    "brand safety, and production ease."
                ),
            }
        )

    angle_rows.sort(
        key=lambda row: (
            -int(row["priority_score"]["total"]),
            str(row["candidate_id"]),
        )
    )
    for rank, angle in enumerate(angle_rows, start=1):
        angle["rank"] = rank

    top_angle = angle_rows[0] if angle_rows else None
    recommendation = {
        "what_to_shoot_first": top_angle["angle_title"] if top_angle else "No shootable angle available",
        "candidate_id": top_angle["candidate_id"] if top_angle else None,
        "why": top_angle["why"] if top_angle else "No selected videos were available to score.",
    }

    summary = {
        "created_at": selected_batch.get("selected_at"),
        "source_video_count": len(evidence_index.get("bundles", [])),
        "priority_score_dimensions": PRIORITY_SCORE_DIMENSIONS,
        "pattern_comparison": {
            "hooks": pattern_rows(hooks),
            "formats": pattern_rows(formats),
            "emotional_triggers": pattern_rows(emotional_triggers),
            "audio_patterns": pattern_rows(audio_patterns),
            "risky_claims": pattern_rows(risky_claims),
            "nattome_opportunities": pattern_rows(opportunities),
        },
        "top_priority_shootable_angles": angle_rows,
        "recommendation": recommendation,
    }

    json_path = run_folder / "batch_outputs" / "json" / "cross_video_pattern_summary.json"
    json_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Cross-Video Pattern Summary",
        "",
        f"- Source videos compared: {summary['source_video_count']}",
        "- Nattome Priority Score: six dimensions, five points each, total out of 30.",
        "",
        "## Cross-Video Pattern Comparison",
        "",
    ]
    section_titles = {
        "hooks": "Hooks",
        "formats": "Formats",
        "emotional_triggers": "Emotional Triggers",
        "audio_patterns": "Audio Patterns",
        "risky_claims": "Risky Claims",
        "nattome_opportunities": "Nattome Opportunities",
    }
    for key, title in section_titles.items():
        lines.extend([f"### {title}", ""])
        rows = summary["pattern_comparison"][key]
        if rows:
            for row in rows:
                lines.append(
                    f"- {row['pattern']}: {row['video_count']} video(s) ({', '.join(row['candidate_ids'])})"
                )
        else:
            lines.append("- No pattern available.")
        lines.append("")

    lines.extend(["## Top Priority Shootable Angles", ""])
    if angle_rows:
        lines.extend(
            [
                "| Rank | Candidate | Nattome Priority Score | Avatar | Product Fit | Recommended Angle |",
                "|---:|---|---:|---|---|---|",
            ]
        )
        for angle in angle_rows:
            lines.append(
                "| {rank} | {candidate} | {score}/30 | {avatar} | {product_fit} | {recommended} |".format(
                    rank=angle["rank"],
                    candidate=angle["candidate_id"],
                    score=angle["priority_score"]["total"],
                    avatar=angle["avatar"],
                    product_fit=angle["product_fit"],
                    recommended=angle["recommended_angle"],
                )
            )
    else:
        lines.append("No shootable angles were available.")

    lines.extend(
        [
            "",
            "## What To Shoot First",
            "",
            f"- Shoot first: {recommendation['what_to_shoot_first']}",
            f"- Candidate: {recommendation['candidate_id'] or 'Not available'}",
            f"- Why: {recommendation['why']}",
        ]
    )

    markdown_path = run_folder / "batch_outputs" / "markdown" / "cross_video_pattern_summary.md"
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": "completed", "top_angle_count": len(angle_rows), "summary": summary}


def first_angle_by_candidate(cross_video_summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    angles = cross_video_summary.get("top_priority_shootable_angles")
    if not isinstance(angles, list):
        return {}
    by_candidate = {}
    for angle in angles:
        if not isinstance(angle, dict):
            continue
        candidate_id = str(angle.get("candidate_id") or "")
        if candidate_id and candidate_id not in by_candidate:
            by_candidate[candidate_id] = angle
    return by_candidate


def write_structured_json_and_spreadsheet_summary(
    run_folder: Path,
    selected_batch: dict[str, Any],
    evidence_index: dict[str, Any],
    metadata: dict[str, Any],
    cross_video_summary: dict[str, Any],
) -> dict[str, Any]:
    candidates_by_id = {
        str(candidate.get("id")): candidate
        for candidate in selected_batch.get("selected_candidates", [])
        if isinstance(candidate, dict)
    }
    angles_by_candidate = first_angle_by_candidate(cross_video_summary)
    videos = []
    spreadsheet_rows = []

    for bundle in evidence_index.get("bundles", []):
        if not isinstance(bundle, dict):
            continue
        candidate_id = str(bundle.get("candidate_id") or "")
        candidate = candidates_by_id.get(candidate_id)
        if not isinstance(candidate, dict):
            continue

        bundle_folder = run_folder / str(bundle.get("bundle_folder"))
        timeline = read_json_object(bundle_folder / "hybrid_timeline.json")
        ocr = read_json_object(bundle_folder / "ocr_evidence.json")
        transcript = read_json_object(bundle_folder / "transcript_evidence.json")
        audio_analysis = read_json_object(bundle_folder / "baseline_audio_analysis.json")
        claim_review = read_json_object(bundle_folder / "claim_safety_review.json")
        quality = read_json_object(bundle_folder / "evidence_quality.json")
        angle = angles_by_candidate.get(candidate_id, {})
        quality_score = quality.get("evidence_quality_score") if isinstance(quality, dict) else {}
        manual_review = quality.get("manual_review_flag") if isinstance(quality, dict) else {}
        priority_score = angle.get("priority_score") if isinstance(angle, dict) else None
        if not isinstance(priority_score, dict):
            dimensions = priority_score_points(candidate, bundle_folder)
            priority_score = {
                "dimensions": dimensions,
                "total": sum(dimensions.values()),
                "max_points": 30,
            }

        hook_type = hook_pattern_for_bundle(bundle_folder)
        audio_format = "unknown"
        if isinstance(audio_analysis, dict):
            audio_format = str(audio_analysis.get("audio_format") or audio_format)
        if audio_format == "unknown":
            audio_format = str(candidate.get("audio_format_hint") or "unknown")

        emotional_trigger = emotional_trigger_for_candidate(candidate)
        product_fit = str(angle.get("product_fit") or product_tie_in_for_candidate(candidate))
        recommended_angle = str(angle.get("angle_title") or "Digestive Comfort Routine Check")
        avatar = str(angle.get("avatar") or avatar_for_candidate(candidate))

        videos.append(
            {
                "candidate_id": candidate_id,
                "source_metadata": read_json_object(bundle_folder / "source_metadata.json") or candidate,
                "evidence_bundle_index": bundle,
                "hybrid_timeline": timeline,
                "ocr_evidence": ocr,
                "transcript_evidence": transcript,
                "audio_analysis": audio_analysis,
                "virality_analysis": {
                    "views": candidate.get("play_count", 0),
                    "weighted_engagement_rate": candidate.get("weighted_engagement_rate", 0),
                    "selection_score": candidate.get("selection_score", 0),
                    "nattome_relevance_score": candidate.get("nattome_relevance_score", 0),
                },
                "claim_safety_review": claim_review,
                "quality_score": quality_score,
                "manual_review_flag": manual_review,
                "shootable_angles": [angle] if isinstance(angle, dict) and angle else [],
                "nattome_priority_score": priority_score,
            }
        )
        spreadsheet_rows.append(
            {
                "link": candidate.get("url") or "",
                "topic": compact_markdown_text(candidate.get("caption")),
                "hook_type": hook_type,
                "format": audio_format,
                "emotional_trigger": emotional_trigger,
                "avatar": avatar,
                "product_fit": product_fit,
                "priority_score": priority_score["total"],
                "evidence_quality": quality_score.get("level", "unknown")
                if isinstance(quality_score, dict)
                else "unknown",
                "recommended_angle": recommended_angle,
            }
        )

    structured = {
        "batch_metadata": metadata,
        "selection_decisions": selected_batch,
        "evidence_bundle_index": evidence_index,
        "cross_video_pattern_summary": cross_video_summary,
        "videos": videos,
    }
    structured_path = run_folder / "batch_outputs" / "json" / "structured_batch_analysis.json"
    structured_path.write_text(
        json.dumps(structured, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    spreadsheet_path = run_folder / "batch_outputs" / "spreadsheets" / "spreadsheet_summary.csv"
    fieldnames = [
        "link",
        "topic",
        "hook_type",
        "format",
        "emotional_trigger",
        "avatar",
        "product_fit",
        "priority_score",
        "evidence_quality",
        "recommended_angle",
    ]
    with spreadsheet_path.open("w", newline="", encoding="utf-8") as spreadsheet_file:
        writer = csv.DictWriter(spreadsheet_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(spreadsheet_rows)

    return {
        "status": "completed",
        "structured_json_path": str(structured_path.relative_to(run_folder)),
        "spreadsheet_path": str(spreadsheet_path.relative_to(run_folder)),
        "row_count": len(spreadsheet_rows),
    }


def telegram_credentials(telegram_config: dict[str, Any]) -> tuple[str | None, str | None, list[str]]:
    token_env = str(telegram_config.get("bot_token_env") or "TELEGRAM_BOT_TOKEN")
    chat_id_env = str(telegram_config.get("chat_id_env") or "TELEGRAM_CHAT_ID")
    token = telegram_config.get("bot_token") or os.environ.get(token_env)
    chat_id = telegram_config.get("chat_id") or os.environ.get(chat_id_env)
    missing = []
    if not token:
        missing.append(token_env)
    if not chat_id:
        missing.append(chat_id_env)
    return str(token) if token else None, str(chat_id) if chat_id else None, missing


def build_telegram_brief_message(
    run_folder: Path,
    metadata: dict[str, Any],
    cross_video_summary: dict[str, Any],
) -> str:
    angles = cross_video_summary.get("top_priority_shootable_angles")
    top_angles = angles[:3] if isinstance(angles, list) else []
    recommendation = cross_video_summary.get("recommendation")
    if not isinstance(recommendation, dict):
        recommendation = {}

    lines = [
        "Nattome Weekly Evidence Brief",
        f"Run: {metadata.get('run_timestamp', 'unknown')} ({metadata.get('mode', 'unknown')})",
        f"Videos compared: {cross_video_summary.get('source_video_count', 0)}",
        (
            "Shoot first: "
            f"{recommendation.get('what_to_shoot_first', 'No recommendation')} "
            f"({recommendation.get('candidate_id', 'no candidate')})"
        ),
        "",
        "Top priority Shootable Angles:",
    ]
    if top_angles:
        for angle in top_angles:
            if not isinstance(angle, dict):
                continue
            score = angle.get("priority_score") if isinstance(angle.get("priority_score"), dict) else {}
            lines.append(
                "{rank}. {candidate} - {title} - {score}/30".format(
                    rank=angle.get("rank", "?"),
                    candidate=angle.get("candidate_id", "unknown"),
                    title=angle.get("angle_title", "Shootable angle"),
                    score=score.get("total", "?"),
                )
            )
    else:
        lines.append("No shootable angles available.")

    lines.extend(
        [
            "",
            "Outputs:",
            "Markdown: batch_outputs/markdown/cross_video_pattern_summary.md",
            "JSON: batch_outputs/json/structured_batch_analysis.json",
            "Spreadsheet: batch_outputs/spreadsheets/spreadsheet_summary.csv",
            f"Run folder: {run_folder}",
        ]
    )
    return "\n".join(lines)


def send_telegram_message(token: str, chat_id: str, text: str) -> dict[str, Any]:
    payload = urlencode(
        {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")
    request = Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8", errors="replace")
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"ok": False, "raw_response": body}


def deliver_telegram_brief(
    run_folder: Path,
    metadata: dict[str, Any],
    cross_video_summary: dict[str, Any],
    telegram_config: dict[str, Any],
    sender=send_telegram_message,
) -> dict[str, Any]:
    log_path = run_folder / "logs" / "telegram_delivery.json"
    if telegram_config.get("enabled", True) is False:
        status = {
            "status": "skipped",
            "reason": "Telegram delivery disabled in runtime configuration",
        }
        log_path.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return status

    token, chat_id, missing = telegram_credentials(telegram_config)
    message = build_telegram_brief_message(run_folder, metadata, cross_video_summary)
    if missing:
        status = {
            "status": "skipped",
            "reason": "missing Telegram credentials",
            "missing": missing,
            "message_character_count": len(message),
        }
        log_path.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return status

    try:
        response = sender(token, chat_id, message)
    except Exception as exc:
        status = {
            "status": "failed",
            "reason": str(exc),
            "message_character_count": len(message),
        }
    else:
        status = {
            "status": "sent",
            "telegram_response": response,
            "message_character_count": len(message),
        }
    log_path.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return status


def write_refinement_hooks(run_folder: Path, cross_video_summary: dict[str, Any]) -> dict[str, Any]:
    angles = cross_video_summary.get("top_priority_shootable_angles")
    top_angles = angles if isinstance(angles, list) else []
    hooks = {
        "deep_sound_research": {
            "status": "extension_point",
            "source": "baseline_audio_analysis",
            "trigger": "Run deeper sound research when reused sound or music appears to drive virality.",
            "candidate_ids": [
                str(angle.get("candidate_id"))
                for angle in top_angles
                if isinstance(angle, dict) and angle.get("candidate_id")
            ],
        },
        "multilingual_quality_improvements": {
            "status": "extension_point",
            "source": "ocr_evidence and transcript_evidence",
            "trigger": "Improve OCR/transcription where language detection, confidence, or mixed-language capture is weak.",
        },
        "full_script_generation": {
            "status": "extension_point",
            "source": "top_priority_shootable_angles",
            "trigger": "Generate full scripts only for selected winning Shootable Angles after human approval.",
            "candidate_ids": [
                str(angle.get("candidate_id"))
                for angle in top_angles[:5]
                if isinstance(angle, dict) and angle.get("candidate_id")
            ],
        },
    }
    hooks_path = run_folder / "batch_outputs" / "json" / "refinement_hooks.json"
    hooks_path.write_text(
        json.dumps(hooks, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"status": "completed", "path": str(hooks_path.relative_to(run_folder))}


def resolved_inside(parent: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def remove_artifact(path: Path, run_folder: Path, removed: list[dict[str, Any]]) -> None:
    if not path.exists() or not resolved_inside(run_folder, path):
        return
    if path.is_dir():
        shutil.rmtree(path)
        artifact_type = "directory"
    else:
        path.unlink()
        artifact_type = "file"
    removed.append(
        {
            "path": str(path.relative_to(run_folder)),
            "type": artifact_type,
        }
    )


def durable_outputs_exist(run_folder: Path, bundle_folder: Path) -> bool:
    required = [
        bundle_folder / "video_evidence_report.md",
        run_folder / "batch_outputs" / "markdown" / "cross_video_pattern_summary.md",
        run_folder / "batch_outputs" / "json" / "structured_batch_analysis.json",
        run_folder / "batch_outputs" / "spreadsheets" / "spreadsheet_summary.csv",
    ]
    return all(path.exists() for path in required)


def cleanup_evidence_artifacts(
    run_folder: Path,
    evidence_index: dict[str, Any],
    cleanup_config: dict[str, Any],
) -> dict[str, Any]:
    log_path = run_folder / "logs" / "evidence_artifact_cleanup.json"
    if cleanup_config.get("enabled", False) is not True:
        status = {
            "status": "skipped",
            "reason": "cleanup disabled in runtime configuration",
            "removed_artifact_count": 0,
            "bundles": [],
        }
        log_path.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return status

    if cleanup_config.get("requires_report_approval", True) and not cleanup_config.get(
        "report_approved", False
    ):
        status = {
            "status": "skipped",
            "reason": "report approval not confirmed",
            "removed_artifact_count": 0,
            "bundles": [],
        }
        log_path.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return status

    bundle_logs = []
    for bundle in evidence_index.get("bundles", []):
        if not isinstance(bundle, dict):
            continue
        bundle_folder = run_folder / str(bundle.get("bundle_folder"))
        removed: list[dict[str, Any]] = []
        if cleanup_config.get("remove_source_videos", True):
            source_video = bundle.get("artifacts", {}).get("source_video", {})
            if isinstance(source_video, dict) and source_video.get("path"):
                remove_artifact(run_folder / str(source_video["path"]), run_folder, removed)
        if cleanup_config.get("remove_frames", True):
            remove_artifact(bundle_folder / "artifacts" / "frames", run_folder, removed)
        bundle_logs.append(
            {
                "candidate_id": bundle.get("candidate_id"),
                "removed_artifacts": removed,
                "preserved_outputs": durable_outputs_exist(run_folder, bundle_folder),
            }
        )

    removed_count = sum(len(bundle["removed_artifacts"]) for bundle in bundle_logs)
    status = {
        "status": "completed",
        "removed_artifact_count": removed_count,
        "bundles": bundle_logs,
    }
    log_path.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return status


def build_metadata(
    args: argparse.Namespace,
    timestamp: datetime,
    configuration: dict[str, Any],
    has_candidate_selection: bool,
    has_evidence_bundles: bool,
    has_hybrid_timeline: bool,
    has_ocr: bool,
    has_transcription: bool,
    has_audio_music_trend_analysis: bool,
    has_claim_safety_review: bool,
    has_evidence_quality: bool,
    has_video_evidence_reports: bool,
    has_cross_video_pattern_summary: bool,
    has_structured_json_output: bool,
    has_spreadsheet_summary: bool,
    has_telegram_delivery: bool,
    has_evidence_artifact_cleanup: bool,
    has_refinement_hooks: bool,
) -> dict[str, Any]:
    batch_size = args.batch_size or MODE_DEFAULT_BATCH_SIZE[args.mode]
    return {
        "run_timestamp": isoformat_z(timestamp),
        "mode": args.mode,
        "requested_batch_size": batch_size,
        "configuration": configuration,
        "implementation_status": {
            "candidate_selection": "implemented" if has_candidate_selection else "not_implemented",
            "video_download": "implemented" if has_evidence_bundles else "not_implemented",
            "hybrid_timeline": "implemented" if has_hybrid_timeline else "not_implemented",
            "ocr": "implemented" if has_ocr else "not_implemented",
            "transcription": "implemented" if has_transcription else "not_implemented",
            "audio_music_trend_analysis": "implemented"
            if has_audio_music_trend_analysis
            else "not_implemented",
            "claim_safety_review": "implemented"
            if has_claim_safety_review
            else "not_implemented",
            "evidence_quality": "implemented" if has_evidence_quality else "not_implemented",
            "video_evidence_reports": "implemented"
            if has_video_evidence_reports
            else "not_implemented",
            "cross_video_pattern_summary": "implemented"
            if has_cross_video_pattern_summary
            else "not_implemented",
            "structured_json_output": "implemented"
            if has_structured_json_output
            else "not_implemented",
            "spreadsheet_summary": "implemented"
            if has_spreadsheet_summary
            else "not_implemented",
            "telegram_delivery": "implemented" if has_telegram_delivery else "not_implemented",
            "evidence_artifact_cleanup": "implemented"
            if has_evidence_artifact_cleanup
            else "not_implemented",
            "refinement_hooks": "implemented" if has_refinement_hooks else "not_implemented",
        },
        "notes": [
            "This run records missing setup or missing evidence instead of fabricating analysis.",
            "Cross-video summaries compare only captured evidence and selected candidate metadata.",
        ],
    }


def write_batch_index(
    run_folder: Path,
    metadata: dict[str, Any],
    has_candidate_selection: bool,
    has_evidence_bundles: bool,
    has_cross_video_pattern_summary: bool,
    has_structured_json_output: bool,
    has_spreadsheet_summary: bool,
    has_telegram_delivery: bool,
    has_evidence_artifact_cleanup: bool,
    has_refinement_hooks: bool,
) -> None:
    lines = [
        "# Batch Analysis Run",
        "",
        f"- Run timestamp: {metadata['run_timestamp']}",
        f"- Mode: {metadata['mode']}",
        f"- Requested batch size: {metadata['requested_batch_size']}",
        f"- Status: {'selected_batch_preview_created' if has_candidate_selection else 'skeleton_created'}",
        "",
        "## Output Folders",
        "",
    ]
    for subdirectory in RUN_SUBDIRECTORIES:
        lines.append(f"- `{subdirectory}`")
    lines.extend(
        [
            "",
            "## Selection",
            "",
        ]
    )
    if has_candidate_selection:
        lines.extend(
            [
                "- JSON: `batch_outputs/json/selected_batch.json`",
                "- Markdown: `batch_outputs/markdown/selected_batch.md`",
            ]
        )
    else:
        lines.append("- Candidate selection was not run because no candidate metadata file was provided.")
    lines.extend(["", "## Evidence Bundles", ""])
    if has_evidence_bundles:
        lines.append("- Index: `evidence_bundles/index.json`")
    else:
        lines.append("- Evidence bundles were not created because no selected batch was available.")
    lines.extend(["", "## Cross-Video Pattern Summary", ""])
    if has_cross_video_pattern_summary:
        lines.extend(
            [
                "- Markdown: `batch_outputs/markdown/cross_video_pattern_summary.md`",
                "- JSON: `batch_outputs/json/cross_video_pattern_summary.json`",
            ]
        )
    else:
        lines.append("- Cross-video pattern summary was not created because no evidence bundles were available.")
    lines.extend(["", "## Structured Outputs", ""])
    if has_structured_json_output:
        lines.append("- Structured JSON: `batch_outputs/json/structured_batch_analysis.json`")
    else:
        lines.append("- Structured JSON was not created because no evidence bundles were available.")
    if has_spreadsheet_summary:
        lines.append("- Spreadsheet summary: `batch_outputs/spreadsheets/spreadsheet_summary.csv`")
    else:
        lines.append("- Spreadsheet summary was not created because no evidence bundles were available.")
    lines.extend(["", "## Telegram Delivery", ""])
    if has_telegram_delivery:
        lines.append("- Delivery log: `logs/telegram_delivery.json`")
    else:
        lines.append("- Telegram delivery was not attempted because required batch outputs were unavailable.")
    lines.extend(["", "## Cleanup And Refinement", ""])
    if has_evidence_artifact_cleanup:
        lines.append("- Cleanup log: `logs/evidence_artifact_cleanup.json`")
    else:
        lines.append("- Evidence artifact cleanup was not evaluated because no evidence bundles were available.")
    if has_refinement_hooks:
        lines.append("- Refinement hooks: `batch_outputs/json/refinement_hooks.json`")
    else:
        lines.append("- Refinement hooks were not created because no cross-video summary was available.")
    lines.extend(
        [
            "",
            "## Not Implemented Yet",
            "",
            "Source video artifacts are only present when candidate metadata includes a downloadable video source.",
        ]
    )
    (run_folder / "batch_index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def create_run(args: argparse.Namespace) -> Path:
    if args.batch_size is not None and args.batch_size < 1:
        raise ValueError("batch size must be at least 1")

    configuration = load_config(args.config)
    timestamp = parse_run_timestamp(args.timestamp)
    candidates = load_candidates(args.candidates)
    batch_size = args.batch_size or MODE_DEFAULT_BATCH_SIZE[args.mode]
    run_folder = args.runs_dir / run_folder_name(timestamp, args.mode)

    if run_folder.exists():
        raise FileExistsError(f"run folder already exists: {run_folder}")

    for subdirectory in RUN_SUBDIRECTORIES:
        (run_folder / subdirectory).mkdir(parents=True, exist_ok=False)

    selected_batch = None
    if candidates is not None:
        selected_batch = select_candidates(
            candidates,
            configuration,
            timestamp,
            batch_size,
            args.candidates,
        )

    evidence_index = None
    if selected_batch is not None:
        evidence_index = write_evidence_bundles(
            run_folder,
            selected_batch,
            args.ffmpeg_bin,
            args.ocr_primary_bin,
            args.ocr_fallback_bin,
            args.transcription_bin,
        )

    cross_video_summary = None
    if selected_batch is not None and evidence_index is not None:
        cross_video_summary = write_cross_video_pattern_summary(
            run_folder,
            selected_batch,
            evidence_index,
        )

    has_hybrid_timeline = evidence_index is not None
    has_ocr = evidence_index is not None
    has_transcription = evidence_index is not None
    has_audio_music_trend_analysis = evidence_index is not None
    has_claim_safety_review = evidence_index is not None
    has_evidence_quality = evidence_index is not None
    has_video_evidence_reports = evidence_index is not None
    has_structured_outputs = (
        selected_batch is not None
        and evidence_index is not None
        and cross_video_summary is not None
    )
    has_telegram_delivery = has_structured_outputs
    has_evidence_artifact_cleanup = evidence_index is not None
    has_refinement_hooks = has_structured_outputs
    metadata = build_metadata(
        args,
        timestamp,
        configuration,
        selected_batch is not None,
        evidence_index is not None,
        has_hybrid_timeline,
        has_ocr,
        has_transcription,
        has_audio_music_trend_analysis,
        has_claim_safety_review,
        has_evidence_quality,
        has_video_evidence_reports,
        cross_video_summary is not None,
        has_structured_outputs,
        has_structured_outputs,
        has_telegram_delivery,
        has_evidence_artifact_cleanup,
        has_refinement_hooks,
    )
    (run_folder / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    if has_structured_outputs:
        write_structured_json_and_spreadsheet_summary(
            run_folder,
            selected_batch,
            evidence_index,
            metadata,
            cross_video_summary["summary"],
        )
        write_refinement_hooks(run_folder, cross_video_summary["summary"])
    if has_telegram_delivery:
        deliver_telegram_brief(
            run_folder,
            metadata,
            cross_video_summary["summary"],
            configuration.get("telegram", {}),
        )
    if has_evidence_artifact_cleanup:
        cleanup_evidence_artifacts(
            run_folder,
            evidence_index,
            configuration.get("cleanup", {}),
        )
    if selected_batch is not None:
        write_selected_batch(run_folder, selected_batch)
    write_batch_index(
        run_folder,
        metadata,
        selected_batch is not None,
        evidence_index is not None,
        cross_video_summary is not None,
        has_structured_outputs,
        has_structured_outputs,
        has_telegram_delivery,
        has_evidence_artifact_cleanup,
        has_refinement_hooks,
    )
    return run_folder


def main() -> int:
    args = parse_args()
    try:
        run_folder = create_run(args)
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"created Batch Analysis Run: {run_folder}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
