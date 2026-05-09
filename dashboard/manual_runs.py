from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Sequence

from .refresh import refresh_dashboard_derivatives
from .settings import get_active_settings_version
from .store import connect_dashboard_store, dump_json, load_json


SCRAPE_ONLY = "scrape_only"
FULL_PIPELINE = "full_pipeline"
MANUAL_RUN_TYPES = {SCRAPE_ONLY, FULL_PIPELINE}


@dataclass(frozen=True)
class ManualRunRecord:
    id: int
    run_id: str
    run_type: str
    source_type: str
    status: str
    config_version: str
    triggered_by: str
    triggered_at: str
    commands: list[list[str]]
    output_paths: dict[str, str]
    error_text: str


RunExecutor = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


def trigger_manual_run(
    workspace: Path | str = ".",
    run_type: str = SCRAPE_ONLY,
    *,
    triggered_by: str = "local",
    executor: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    now: datetime | None = None,
) -> ManualRunRecord:
    workspace_path = Path(workspace)
    if run_type not in MANUAL_RUN_TYPES:
        raise ValueError(f"unknown manual run type: {run_type}")

    active_settings = get_active_settings_version(workspace_path)
    config_version = f"v{active_settings.version}"
    triggered_at = _isoformat_z(now or datetime.now(timezone.utc))
    timestamp = _available_timestamp(workspace_path, run_type, now or datetime.now(timezone.utc))
    run_id = _run_id(timestamp, run_type)
    output_paths = _output_paths(timestamp, run_type)
    config_path = _ensure_scraper_config(workspace_path, active_settings.version, active_settings.new_settings)
    commands = _commands_for_run(run_type, timestamp, output_paths, config_path)
    record_id = _insert_manual_run(
        workspace_path,
        run_id=run_id,
        run_type=run_type,
        config_version=config_version,
        triggered_by=triggered_by.strip() or "local",
        triggered_at=triggered_at,
        commands=commands,
        output_paths=output_paths,
    )

    run_executor = executor or _run_command
    _update_manual_run_status(workspace_path, record_id, "running")
    error_text = ""
    status = "completed"
    for command in commands:
        result = run_executor(command, cwd=workspace_path)
        if result.returncode != 0:
            status = "failed"
            error_text = (result.stderr or result.stdout or f"command exited {result.returncode}").strip()
            break
    if status == "completed":
        try:
            refresh_dashboard_derivatives(workspace_path, intent="manual_run_completed", scope="artifacts")
        except Exception as exc:  # pragma: no cover - defensive dashboard boundary
            status = "failed"
            error_text = f"indexing failed: {exc}"
    _update_manual_run_status(workspace_path, record_id, status, error_text=error_text)
    return _manual_run_by_id(workspace_path, record_id)


def list_manual_runs(workspace: Path | str = ".") -> list[ManualRunRecord]:
    connection = connect_dashboard_store(workspace)
    try:
        rows = connection.execute(
            """
            SELECT *
            FROM manual_runs
            ORDER BY id DESC
            """
        )
        return [_row_to_manual_run(row) for row in rows]
    finally:
        connection.close()


def _run_command(command: Sequence[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def _insert_manual_run(
    workspace: Path,
    *,
    run_id: str,
    run_type: str,
    config_version: str,
    triggered_by: str,
    triggered_at: str,
    commands: list[list[str]],
    output_paths: dict[str, str],
) -> int:
    connection = connect_dashboard_store(workspace)
    try:
        cursor = connection.execute(
            """
            INSERT INTO manual_runs (
                run_id,
                run_type,
                source_type,
                status,
                config_version,
                triggered_by,
                triggered_at,
                command_json,
                output_path,
                output_paths_json,
                created_by,
                updated_by
            )
            VALUES (?, ?, 'manual', 'queued', ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                run_type,
                config_version,
                triggered_by,
                triggered_at,
                _json_dumps(commands),
                next(iter(output_paths.values()), None),
                _json_dumps(output_paths),
                triggered_by,
                triggered_by,
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)
    finally:
        connection.close()


def _update_manual_run_status(
    workspace: Path,
    record_id: int,
    status: str,
    *,
    error_text: str = "",
) -> None:
    connection = connect_dashboard_store(workspace)
    try:
        connection.execute(
            """
            UPDATE manual_runs
            SET status = ?,
                error_text = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, error_text, record_id),
        )
        connection.commit()
    finally:
        connection.close()


def _manual_run_by_id(workspace: Path, record_id: int) -> ManualRunRecord:
    connection = connect_dashboard_store(workspace)
    try:
        row = connection.execute(
            "SELECT * FROM manual_runs WHERE id = ?",
            (record_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"manual run not found: {record_id}")
        return _row_to_manual_run(row)
    finally:
        connection.close()


def _commands_for_run(
    run_type: str,
    timestamp: datetime,
    output_paths: dict[str, str],
    config_path: str,
) -> list[list[str]]:
    scrape_command = [
        sys.executable,
        "skills/nattome-tiktok-candidate-discovery/scripts/scrape_tiktok.py",
        "--config",
        config_path,
        "--output",
        output_paths["raw_scrape"],
        "--top",
        "30",
        "--download-videos",
        "--daily-selection-output",
        output_paths["daily_selection"],
    ]
    if run_type == SCRAPE_ONLY:
        return [scrape_command]
    batch_command = [
        sys.executable,
        "scripts/run_batch_analysis.py",
        "--candidates",
        output_paths["daily_selection"],
        "--backfill-candidates",
        output_paths["daily_backfill"],
        "--config",
        config_path,
        "--timestamp",
        _isoformat_z(timestamp),
    ]
    return [scrape_command, batch_command]


def _ensure_scraper_config(workspace: Path, version: int, settings: dict[str, object]) -> str:
    relative_path = Path("skills") / "nattome-tiktok-candidate-discovery" / "config.json"
    config_path = workspace / relative_path
    config_path.parent.mkdir(parents=True, exist_ok=True)
    selection = {
        "minimum_views": settings.get("minimum_views", 10000),
        "maximum_age_days": settings.get("maximum_age_days", 150),
        "minimum_weighted_engagement_rate": settings.get("minimum_weighted_engagement_rate", 0.03),
        "requires_downloadable_video": settings.get("requires_downloadable_video", True),
        "exclusion_terms": settings.get("exclusion_terms", []),
    }
    config = {
        "config_version": f"v{version}",
        "hashtags": settings.get("hashtags", []),
        "keywords": settings.get("keywords", []),
        "competitor_profiles": settings.get("competitor_profiles", []),
        "scope": settings.get("scope", "all"),
        "results_per_input": settings.get("results_per_input", 20),
        "top_n": settings.get("top_n", 30),
        "selection": selection,
    }
    config_path.write_text(_json_dumps(config) + "\n", encoding="utf-8")
    return relative_path.as_posix()


def _available_timestamp(workspace: Path, run_type: str, base: datetime) -> datetime:
    timestamp = base.astimezone(timezone.utc).replace(microsecond=0)
    while _paths_exist(workspace, _output_paths(timestamp, run_type)):
        timestamp += timedelta(seconds=1)
    return timestamp


def _paths_exist(workspace: Path, output_paths: dict[str, str]) -> bool:
    for output_path in output_paths.values():
        if (workspace / output_path).exists():
            return True
    return False


def _output_paths(timestamp: datetime, run_type: str) -> dict[str, str]:
    stamp = timestamp.strftime("%Y%m%dT%H%M%SZ")
    date = timestamp.strftime("%Y-%m-%d")
    run_id = _run_id(timestamp, run_type)
    run_root = f"data/daily_runs/{run_id}"
    paths = {
        "run_data_folder": run_root,
        "raw_scrape": f"{run_root}/raw_scrape_top30.json",
        "daily_selection": f"{run_root}/daily_selection_top3.json",
        "daily_backfill": f"{run_root}/daily_backfill_candidates.json",
    }
    if run_type == FULL_PIPELINE:
        paths["run_folder"] = f"runs/batch-analysis/{stamp}_daily"
        paths["final_reports"] = f"outputs/reports/{date}"
    return paths


def _run_id(timestamp: datetime, run_type: str) -> str:
    return f"manual_{timestamp.strftime('%Y%m%dT%H%M%SZ')}_{run_type}"


def _row_to_manual_run(row) -> ManualRunRecord:
    return ManualRunRecord(
        id=int(row["id"]),
        run_id=str(row["run_id"] or ""),
        run_type=str(row["run_type"]),
        source_type=str(row["source_type"]),
        status=str(row["status"]),
        config_version=str(row["config_version"]),
        triggered_by=str(row["triggered_by"]),
        triggered_at=str(row["triggered_at"]),
        commands=_json_loads(row["command_json"], []),
        output_paths=_json_loads(row["output_paths_json"], {}),
        error_text=str(row["error_text"] or ""),
    )


def _json_dumps(value: object) -> str:
    return dump_json(value)


def _json_loads(value: str | None, fallback):
    return load_json(value, fallback)


def _isoformat_z(timestamp: datetime) -> str:
    return timestamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
