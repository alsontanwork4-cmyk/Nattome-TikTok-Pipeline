from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DAILY_SELECTION_SIZE = 5
DAILY_RUN_MODE = "daily"
DEFAULT_RUN_FOLDER_TIME_ZONE = "Asia/Singapore"

MODE_DEFAULT_BATCH_SIZE = {
    "daily": DAILY_SELECTION_SIZE,
}

RUN_SUBDIRECTORIES = [
    "reports",
    "data",
    "evidence",
    "logs",
]

DEFAULT_CONFIG: dict[str, Any] = {
    "selection": {
        "minimum_views": 10000,
        "maximum_age_days": 150,
        "minimum_weighted_engagement_rate": 0.03,
        "requires_tiktok_link": True,
        "requires_downloadable_video": True,
    },
    "outputs": {
        "selection_json": "data/selected_batch.json",
        "selection_markdown": "reports/selected_batch.md",
        "source_video_index": "data/evidence_bundle_index.json",
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


def isoformat_local(timestamp: datetime) -> str:
    return timestamp.astimezone(run_folder_timezone()).replace(microsecond=0).isoformat()


def run_folder_timezone() -> tzinfo:
    name = os.environ.get("NATTOME_RUN_FOLDER_TIME_ZONE", DEFAULT_RUN_FOLDER_TIME_ZONE)
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return timezone(timedelta(hours=8))


def run_folder_name(timestamp: datetime, mode: str) -> str:
    local_timestamp = timestamp.astimezone(run_folder_timezone())
    return f"{local_timestamp.strftime('%Y%m%dT%H%M%S%z')}_{mode}"


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
