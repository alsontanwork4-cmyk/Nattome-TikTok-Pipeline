from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, tzinfo
import os
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .refresh import refresh_dashboard_derivatives
from .store import connect_dashboard_store

DEFAULT_REPORT_TIME_ZONE = "Asia/Singapore"


@dataclass(frozen=True)
class ReportArtifact:
    run_id: str
    run_timestamp: str
    report_date: str
    path: str
    absolute_path: Path
    markdown: str

    @property
    def display_title(self) -> str:
        return f"Report - {self.report_date} - Run {self.run_id}"


def load_report_artifacts(workspace: Path | str = ".") -> list[ReportArtifact]:
    workspace_path = Path(workspace)
    refresh_dashboard_derivatives(workspace_path, intent="report_page", scope="artifacts")
    connection = connect_dashboard_store(workspace_path)
    try:
        artifacts: list[ReportArtifact] = []
        rows = list(
            connection.execute(
                """
                SELECT run_id, run_timestamp, run_folder, raw_json
                FROM batch_runs
                ORDER BY COALESCE(run_timestamp, '') DESC, run_id DESC
                """
            )
        )
        for row in rows:
            run_id = str(row["run_id"])
            run_timestamp = str(row["run_timestamp"] or "")
            report_date = _report_date(run_timestamp, run_id)
            artifact = _artifact_for_run(
                workspace_path,
                run_id=run_id,
                run_timestamp=run_timestamp,
                report_date=report_date,
                run_folder=str(row["run_folder"] or ""),
                manifest=_json_loads(row["raw_json"]),
            )
            if artifact is not None:
                artifacts.append(artifact)
        return artifacts
    finally:
        connection.close()


def load_selected_report(
    workspace: Path | str = ".",
    *,
    requested_run_id: str = "",
) -> tuple[ReportArtifact | None, list[ReportArtifact]]:
    artifacts = load_report_artifacts(workspace)
    if requested_run_id:
        selected = next((artifact for artifact in artifacts if artifact.run_id == requested_run_id), None)
        if selected is not None:
            return selected, artifacts
    return (artifacts[0], artifacts) if artifacts else (None, artifacts)


def _artifact_for_run(
    workspace: Path,
    *,
    run_id: str,
    run_timestamp: str,
    report_date: str,
    run_folder: str,
    manifest: dict[str, Any],
) -> ReportArtifact | None:
    for path in _candidate_report_paths(
        workspace,
        run_folder,
        manifest,
    ):
        if not path.is_file():
            continue
        try:
            markdown = path.read_text(encoding="utf-8")
        except OSError:
            continue
        return ReportArtifact(
            run_id=run_id,
            run_timestamp=run_timestamp,
            report_date=report_date,
            path=_relative_path(workspace, path),
            absolute_path=path,
            markdown=markdown,
        )
    return None


def _candidate_report_paths(
    workspace: Path,
    run_folder: str,
    manifest: dict[str, Any],
) -> list[Path]:
    outputs = manifest.get("outputs") if isinstance(manifest, dict) else {}
    run_path = workspace / run_folder
    paths = [run_path / "reports" / "selected_batch.md"]
    if isinstance(outputs, dict) and outputs.get("selected_batch_markdown"):
        paths.insert(0, run_path / str(outputs["selected_batch_markdown"]))
    return _dedupe_paths(paths)


def _report_date(run_timestamp: str, run_id: str) -> str:
    if run_timestamp:
        try:
            return _report_date_from_timestamp(run_timestamp)
        except ValueError:
            pass
    if len(run_id) >= 8 and run_id[:8].isdigit():
        return f"{run_id[:4]}-{run_id[4:6]}-{run_id[6:8]}"
    return "unknown-date"


def _report_date_from_timestamp(timestamp: str) -> str:
    parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(_report_timezone()).strftime("%Y-%m-%d")


def _report_timezone() -> tzinfo:
    name = os.environ.get("NATTOME_REPORT_TIME_ZONE", DEFAULT_REPORT_TIME_ZONE)
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return timezone(timedelta(hours=8))


def _json_loads(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    try:
        loaded = json.loads(str(value or "{}"))
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _relative_path(workspace: Path, path: Path) -> str:
    try:
        return str(path.relative_to(workspace)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    deduped: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(path)
    return deduped
