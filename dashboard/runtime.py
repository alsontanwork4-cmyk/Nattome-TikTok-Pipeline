from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4


FULL_PIPELINE_RUN_TYPE = "full_pipeline"
ACTIVE_MANUAL_RUN_STATUSES = {"queued", "running"}
MANUAL_RUN_STATUSES = ("queued", "running", "succeeded", "failed", "canceled")


class ActiveManualRunError(Exception):
    """Raised when a full pipeline run is already queued or running."""


def enqueue_manual_run(
    dashboard_client: object,
    *,
    triggered_by: str,
    run_type: str = FULL_PIPELINE_RUN_TYPE,
    now: datetime | None = None,
) -> dict:
    active = _call_active_manual_run(dashboard_client, run_type=run_type)
    if active:
        raise ActiveManualRunError("A full pipeline run is already active.")

    requested_at = _iso_utc(now or datetime.now(timezone.utc))
    run_id = _manual_run_id(run_type, requested_at)
    expected_outputs = _expected_output_metadata(run_id)
    manual_run = {
        "id": str(uuid4()),
        "run_id": run_id,
        "status": "queued",
        "run_type": run_type,
        "triggered_by": triggered_by,
        "requested_at": requested_at,
        "claimed_at": None,
        "finished_at": None,
        "expected_output_metadata": expected_outputs,
        "error_summary": "",
        "created_at": requested_at,
        "updated_at": requested_at,
    }
    run = {
        "run_id": run_id,
        "status": "queued",
        "run_type": run_type,
        "mode": "manual",
        "started_at": "",
        "finished_at": "",
        "duration_seconds": None,
        "triggered_by": triggered_by,
        "created_by": triggered_by,
        "error_summary": "",
        "raw_candidate_count": 0,
        "eligible_candidate_count": 0,
        "selected_count": 0,
        "created_at": requested_at,
        "updated_at": requested_at,
    }
    enqueue = getattr(dashboard_client, "enqueue_manual_run", None)
    if not callable(enqueue):
        raise RuntimeError("dashboard client does not support manual run enqueueing")
    return enqueue(manual_run, run)


def sanitize_error_summary(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    sanitized_lines = []
    for line in text.splitlines()[:4]:
        lowered = line.lower()
        if any(marker in lowered for marker in ("secret", "token", "password", "key=")):
            sanitized_lines.append("[redacted secret]")
        else:
            sanitized_lines.append(line[:240])
    return "\n".join(sanitized_lines)


def _call_active_manual_run(dashboard_client: object, *, run_type: str) -> dict | None:
    get_active = getattr(dashboard_client, "get_active_manual_run", None)
    if not callable(get_active):
        return None
    return get_active(run_type=run_type)


def _manual_run_id(run_type: str, requested_at: str) -> str:
    compact_time = (
        requested_at.replace("-", "")
        .replace(":", "")
        .replace("+00:00", "Z")
        .replace(".", "")
    )
    return f"manual_{compact_time}_{run_type}"


def _expected_output_metadata(run_id: str) -> list[dict[str, str]]:
    return [
        {
            "artifact_type": "raw_scrape",
            "bucket": "dashboard-artifacts",
            "object_path": f"runs/{run_id}/data/raw_scrape_all.json",
            "filename": "raw_scrape_all.json",
            "content_type": "application/json",
        },
        {
            "artifact_type": "selected_batch",
            "bucket": "dashboard-artifacts",
            "object_path": f"runs/{run_id}/data/selected_batch.json",
            "filename": "selected_batch.json",
            "content_type": "application/json",
        },
        {
            "artifact_type": "report",
            "bucket": "dashboard-artifacts",
            "object_path": f"runs/{run_id}/reports/selected_batch.md",
            "filename": "selected_batch.md",
            "content_type": "text/markdown",
        },
    ]


def _iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()
