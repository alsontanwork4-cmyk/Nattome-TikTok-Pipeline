from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .runtime import sanitize_error_summary
from .supabase_client import ArtifactMetadata


@dataclass(frozen=True)
class WorkerRunResult:
    status: str = "succeeded"
    artifacts: list[ArtifactMetadata] = field(default_factory=list)
    error_summary: str = ""


WorkerRunner = Callable[[dict], WorkerRunResult]


def run_manual_worker_once(
    dashboard_client: object,
    *,
    worker_id: str,
    runner: WorkerRunner,
) -> str | None:
    claim = getattr(dashboard_client, "claim_queued_manual_run", None)
    if not callable(claim):
        raise RuntimeError("dashboard client does not support manual run claiming")
    manual_run = claim(worker_id=worker_id)
    if not manual_run:
        return None

    run_id = str(manual_run.get("run_id") or "")
    try:
        result = runner(manual_run)
        for artifact in result.artifacts:
            dashboard_client.upsert_artifact_metadata(artifact)
        status = result.status if result.status in {"succeeded", "failed", "canceled"} else "succeeded"
        error_summary = sanitize_error_summary(result.error_summary)
    except Exception as exc:  # pragma: no cover - tested through public behavior
        status = "failed"
        error_summary = sanitize_error_summary(str(exc))

    dashboard_client.mark_manual_run_status(
        run_id,
        status=status,
        error_summary=error_summary,
    )
    return status
