from __future__ import annotations

import argparse
import json
import os
import time
from argparse import Namespace
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .composition import build_dashboard_data_client
from .config import DashboardSettings
from .run_publication import (
    ArtifactUpload as WorkerArtifact,
    artifact_uploads,
    publish_run_records,
)
from .runtime import sanitize_error_summary
from .supabase_client import ArtifactMetadata


@dataclass(frozen=True)
class WorkerRunResult:
    status: str = "succeeded"
    artifacts: list[ArtifactMetadata] = field(default_factory=list)
    artifact_uploads: list[WorkerArtifact] = field(default_factory=list)
    error_summary: str = ""


WorkerRunner = Callable[[dict], WorkerRunResult]
DiscoveryRunner = Callable[[Path, Path, str], Path]
CreateRun = Callable[[Namespace], Path]


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
        for artifact_upload in result.artifact_uploads:
            dashboard_client.upload_artifact_file(
                artifact_upload.source_path,
                artifact_upload.metadata,
            )
            dashboard_client.upsert_artifact_metadata(artifact_upload.metadata)
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


def run_worker_loop(
    dashboard_client: object,
    *,
    worker_id: str,
    runner: WorkerRunner,
    poll_interval_seconds: float,
    once: bool = False,
    sleep: Callable[[float], None] = time.sleep,
) -> str | None:
    if poll_interval_seconds < 0:
        raise ValueError("poll interval must be non-negative")

    while True:
        status = run_manual_worker_once(
            dashboard_client,
            worker_id=worker_id,
            runner=runner,
        )
        if once:
            return status
        if status is None:
            sleep(poll_interval_seconds)


def build_pipeline_runner(
    settings: DashboardSettings,
    dashboard_client: object,
    *,
    runs_dir: Path | None = None,
    config_path: Path | None = None,
    discovery_runner: DiscoveryRunner | None = None,
    create_run_func: CreateRun | None = None,
) -> WorkerRunner:
    resolved_runs_dir = runs_dir or _default_batch_runs_dir(settings)
    resolved_config_path = config_path or Path(settings.workspace_path) / "batch_analysis" / "scrape_config.json"
    resolved_discovery_runner = discovery_runner or _run_discovery
    if create_run_func is None:
        from batch_analysis.run import create_run as create_run_func

    def runner(manual_run: dict) -> WorkerRunResult:
        run_id = str(manual_run.get("run_id") or "")
        if not run_id:
            raise RuntimeError("manual run is missing run_id")

        timestamp = _manual_run_timestamp(manual_run)
        run_folder = _local_run_folder(resolved_runs_dir, timestamp)
        candidates_path = resolved_discovery_runner(
            run_folder,
            resolved_config_path,
            timestamp,
        )
        created_run_folder = create_run_func(
            Namespace(
                mode="daily",
                batch_size=None,
                runs_dir=resolved_runs_dir,
                config=resolved_config_path,
                candidates=candidates_path,
                timestamp=timestamp,
            )
        )
        status, error_summary = publish_run_records(
            dashboard_client,
            created_run_folder,
            run_id=run_id,
            manual_run=manual_run,
        )
        return WorkerRunResult(
            status=status,
            artifact_uploads=artifact_uploads(
                created_run_folder,
                run_id=run_id,
                storage_bucket=settings.supabase_storage_bucket,
            ),
            error_summary=error_summary,
        )

    return runner


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the dashboard manual-run worker.")
    parser.add_argument("--worker-id", required=True)
    parser.add_argument("--poll-interval", type=float, default=15)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--runs-dir", type=Path)
    parser.add_argument("--config", type=Path)
    args = parser.parse_args(argv)

    settings = DashboardSettings.from_env()
    dashboard_client = build_dashboard_data_client(settings, require_supabase=True)
    runner = build_pipeline_runner(
        settings,
        dashboard_client,
        runs_dir=args.runs_dir,
        config_path=args.config,
    )
    run_worker_loop(
        dashboard_client,
        worker_id=args.worker_id,
        runner=runner,
        poll_interval_seconds=args.poll_interval,
        once=args.once,
    )
    return 0


def _default_batch_runs_dir(settings: DashboardSettings) -> Path:
    runs_path = Path(settings.runs_path)
    return runs_path if runs_path.name == "batch-analysis" else runs_path / "batch-analysis"


def _manual_run_timestamp(manual_run: dict) -> str:
    requested_at = str(manual_run.get("requested_at") or "").strip()
    if requested_at:
        return requested_at
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _local_run_folder(runs_dir: Path, timestamp: str) -> Path:
    from batch_analysis.config import DAILY_RUN_MODE, parse_run_timestamp, run_folder_name

    return runs_dir / run_folder_name(parse_run_timestamp(timestamp), DAILY_RUN_MODE)


def _run_discovery(run_folder: Path, config_path: Path, timestamp: str) -> Path:
    from batch_analysis.config import parse_run_timestamp
    from batch_analysis.scrape_tiktok import (
        APIFY_ACTOR_ID,
        apify_run_actor,
        assert_output_paths_available,
        build_daily_selection_payload,
        build_output_payload,
        build_run_input,
        deduplicate,
        effective_scrape_options,
        load_config,
        virality_score,
    )

    token = os.environ.get("APIFY_TOKEN")
    if not token:
        raise RuntimeError("APIFY_TOKEN env var is not set.")

    output_path = run_folder / "data" / "raw_scrape_all.json"
    daily_selection_path = run_folder / "data" / "daily_selection_top_videos.json"
    assert_output_paths_available(output_path, daily_selection_path)

    config = load_config(config_path)
    scrape_args = Namespace(scope=None, results_per_input=None, download_videos=True)
    options = effective_scrape_options(config, scrape_args)
    hashtags = config.get("hashtags", []) if options["scope"] in ("all", "hashtags") else []
    keywords = config.get("keywords", []) if options["scope"] in ("all", "keywords") else []
    profiles = config.get("competitor_profiles", []) if options["scope"] in ("all", "profiles") else []
    if not (hashtags or keywords or profiles):
        raise RuntimeError("scrape config has no hashtags, keywords, or profiles for this scope")

    run_input = build_run_input(
        hashtags,
        keywords,
        profiles,
        options["results_per_input"],
        options["download_videos"],
    )
    raw_items = apify_run_actor(token, APIFY_ACTOR_ID, run_input)
    timestamp_value = parse_run_timestamp(timestamp)
    scored_items = sorted(
        deduplicate(raw_items),
        key=lambda item: virality_score(item, timestamp_value),
        reverse=True,
    )
    payload = build_output_payload(
        now=timestamp_value,
        scope=options["scope"],
        hashtags=hashtags,
        keywords=keywords,
        profiles=profiles,
        raw_item_count=len(raw_items),
        unique_items=scored_items,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    daily_selection = build_daily_selection_payload(
        full_payload=payload,
        source_scrape=output_path,
        configuration=config,
        run_timestamp=timestamp_value,
    )
    daily_selection_path.write_text(
        json.dumps(daily_selection, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return daily_selection_path


if __name__ == "__main__":
    raise SystemExit(main())
