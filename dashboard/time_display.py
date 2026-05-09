from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from batch_analysis.config import run_folder_timezone


def display_datetime(value: Any, *, fallback: str = "--") -> str:
    parsed = _parse_datetime(value)
    if parsed is None:
        text = str(value or "").strip()
        return text or fallback
    return parsed.astimezone(run_folder_timezone()).strftime("%Y-%m-%d %H:%M:%S %z")


def display_datetime_field(key: str, value: Any) -> str:
    if _is_datetime_field(key):
        return display_datetime(value)
    return str(value)


def _is_datetime_field(key: str) -> bool:
    normalized = key.lower()
    return (
        normalized.endswith("_at")
        or normalized.endswith("_timestamp")
        or normalized in {"timestamp", "generated_at", "selected_at", "created_at", "updated_at"}
    )


def _parse_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, (int, float)):
        parsed = datetime.fromtimestamp(value, tz=timezone.utc)
    else:
        text = str(value).strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
