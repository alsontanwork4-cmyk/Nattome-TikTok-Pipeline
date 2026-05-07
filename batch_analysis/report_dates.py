from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone, tzinfo
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_REPORT_TIME_ZONE = "Asia/Singapore"


def report_timezone() -> tzinfo:
    name = os.environ.get("NATTOME_REPORT_TIME_ZONE", DEFAULT_REPORT_TIME_ZONE)
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return timezone(timedelta(hours=8))


def report_date_from_timestamp(timestamp: str) -> str:
    parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(report_timezone()).strftime("%Y-%m-%d")


def report_output_path(
    output_root: Path,
    report_date: str,
    filename: str,
    run_id: str = "",
) -> Path:
    path = output_root / "reports" / report_date
    if run_id:
        path = path / run_id
    return path / filename
