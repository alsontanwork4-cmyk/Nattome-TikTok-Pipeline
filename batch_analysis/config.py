from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MODE_DEFAULT_BATCH_SIZE = {
    "debug": 1,
    "quick": 5,
    "default": 10,
    "deep": 20,
}

RUN_SUBDIRECTORIES = [
    "reports",
    "data",
    "evidence",
    "logs",
]

LEGACY_OUTPUT_SUBDIRECTORIES = [
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
