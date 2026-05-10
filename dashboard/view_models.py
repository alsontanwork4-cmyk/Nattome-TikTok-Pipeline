from __future__ import annotations

import json

from .runtime import sanitize_error_summary


def run_view(row: dict) -> dict:
    status = str(row.get("status") or "unknown").lower()
    return {
        "run_id": str(row.get("run_id") or ""),
        "status": status,
        "status_label": status_label(status),
        "status_tone": status_tone(status),
        "run_type": str(row.get("run_type") or row.get("mode") or ""),
        "started_at": str(row.get("started_at") or ""),
        "finished_at": str(row.get("finished_at") or ""),
        "duration": format_duration(row.get("duration_seconds")),
        "triggered_by": str(row.get("triggered_by") or row.get("created_by") or ""),
        "raw_candidate_count": row.get("raw_candidate_count") or 0,
        "eligible_candidate_count": row.get("eligible_candidate_count") or 0,
        "selected_count": row.get("selected_count") or 0,
        "error_summary": safe_error_summary(row.get("error_summary")),
    }


def output_view(row: dict) -> dict:
    object_path = str(row.get("object_path") or "")
    return {
        "artifact_type": str(row.get("artifact_type") or ""),
        "bucket": str(row.get("bucket") or ""),
        "object_path": object_path,
        "artifact_href": f"/artifacts/{object_path}" if object_path else "",
        "filename": str(row.get("filename") or row.get("object_path") or ""),
        "content_type": str(row.get("content_type") or ""),
        "size": format_bytes(row.get("size_bytes")),
        "checksum": str(row.get("checksum") or ""),
        "created_at": str(row.get("created_at") or ""),
    }


def status_label(status: str) -> str:
    return {
        "queued": "Queued",
        "running": "Running",
        "succeeded": "Succeeded",
        "failed": "Failed",
        "canceled": "Canceled",
        "cancelled": "Canceled",
    }.get(status, status.title() or "Unknown")


def status_tone(status: str) -> str:
    if status == "succeeded":
        return "ok"
    if status in {"queued", "running"}:
        return "accent"
    if status in {"failed", "error"}:
        return "err"
    if status in {"canceled", "cancelled"}:
        return "warn"
    return "warn"


def format_duration(value: object) -> str:
    try:
        seconds = int(value)
    except (TypeError, ValueError):
        return "--"
    minutes, remaining_seconds = divmod(seconds, 60)
    hours, remaining_minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {remaining_minutes}m {remaining_seconds}s"
    if minutes:
        return f"{minutes}m {remaining_seconds}s"
    return f"{remaining_seconds}s"


def format_bytes(value: object) -> str:
    try:
        size = int(value)
    except (TypeError, ValueError):
        return "--"
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size} B"


def output_count_label(outputs: list[dict]) -> str:
    if not outputs:
        return "No outputs published"
    if len(outputs) == 1:
        return "1 output available"
    return f"{len(outputs)} outputs available"


def list_value(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.strip():
        try:
            loaded = json.loads(value)
        except json.JSONDecodeError:
            return [value]
        return loaded if isinstance(loaded, list) else [value]
    return []


def cell(value: object) -> object:
    return "" if value is None else value


def safe_error_summary(value: object) -> str:
    return sanitize_error_summary(value)
