from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .refresh import refresh_dashboard_derivatives
from .store import connect_dashboard_store


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
        for row in connection.execute(
            """
            SELECT run_id, run_timestamp, run_folder, raw_json
            FROM batch_runs
            ORDER BY COALESCE(run_timestamp, '') DESC, run_id DESC
            """
        ):
            artifact = _artifact_for_run(
                workspace_path,
                run_id=str(row["run_id"]),
                run_timestamp=str(row["run_timestamp"] or ""),
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
    run_folder: str,
    manifest: dict[str, Any],
) -> ReportArtifact | None:
    report_date = _report_date(run_timestamp, run_id)
    for path in _candidate_report_paths(workspace, report_date, run_folder, manifest):
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
    report_date: str,
    run_folder: str,
    manifest: dict[str, Any],
) -> list[Path]:
    paths: list[Path] = []
    outputs = manifest.get("outputs") if isinstance(manifest, dict) else {}
    output_root = _output_root(workspace, outputs)
    final_outputs = outputs.get("final_outputs") if isinstance(outputs, dict) else None
    if isinstance(final_outputs, list):
        for item in final_outputs:
            if not isinstance(item, dict):
                continue
            kind = str(item.get("kind") or "").lower()
            label = str(item.get("label") or "").lower()
            raw_path = item.get("path")
            if raw_path and (kind == "markdown" or "report" in label):
                paths.append(output_root / str(raw_path))

    paths.extend(
        [
            workspace
            / "outputs"
            / "reports"
            / report_date
            / f"top5_creative_production_report_{report_date}.md",
            workspace / "outputs" / "reports" / report_date / f"report_{report_date}.md",
        ]
    )
    paths.extend(sorted((workspace / "outputs" / "reports" / report_date).glob("*.md")))

    run_path = workspace / run_folder
    paths.extend(sorted((run_path / "reports").glob("top5_creative_production_report_*.md")))
    return _dedupe_paths(paths)


def _output_root(workspace: Path, outputs: object) -> Path:
    if isinstance(outputs, dict):
        raw_root = outputs.get("output_root")
        if raw_root:
            path = Path(str(raw_root))
            return path if path.is_absolute() else workspace / path
    return workspace / "outputs"


def _report_date(run_timestamp: str, run_id: str) -> str:
    if run_timestamp:
        try:
            parsed = datetime.fromisoformat(run_timestamp.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).strftime("%Y-%m-%d")
        except ValueError:
            pass
    if len(run_id) >= 8 and run_id[:8].isdigit():
        return f"{run_id[:4]}-{run_id[4:6]}-{run_id[6:8]}"
    return "unknown-date"


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
