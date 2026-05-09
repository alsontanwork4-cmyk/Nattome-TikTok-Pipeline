from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from batch_analysis.report_dates import report_date_from_timestamp

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
        rows = list(
            connection.execute(
                """
                SELECT run_id, run_timestamp, run_folder, raw_json
                FROM batch_runs
                ORDER BY COALESCE(run_timestamp, '') DESC, run_id DESC
                """
            )
        )
        has_final_outputs = _has_final_output_reports(rows)
        ambiguous_final_output_paths = _ambiguous_final_output_paths(workspace_path, rows)
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
                allow_legacy_fallback=not has_final_outputs,
                ambiguous_final_output_paths=ambiguous_final_output_paths,
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
    allow_legacy_fallback: bool,
    ambiguous_final_output_paths: set[str],
) -> ReportArtifact | None:
    for path in _candidate_report_paths(
        workspace,
        report_date,
        run_folder,
        manifest,
        allow_legacy_fallback=allow_legacy_fallback,
        ambiguous_final_output_paths=ambiguous_final_output_paths,
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
    report_date: str,
    run_folder: str,
    manifest: dict[str, Any],
    *,
    allow_legacy_fallback: bool = True,
    ambiguous_final_output_paths: set[str] | None = None,
) -> list[Path]:
    paths: list[Path] = []
    ambiguous_final_output_paths = ambiguous_final_output_paths or set()
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
            if not raw_path or (kind != "markdown" and "report" not in label):
                continue
            path = output_root / str(raw_path)
            if _path_key(path) in ambiguous_final_output_paths:
                continue
            paths.append(path)

    if allow_legacy_fallback:
        paths.extend(
            [
                workspace
                / "outputs"
                / "reports"
                / report_date
                / f"production_creative_report_{report_date}.md",
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
    paths.extend(sorted((run_path / "reports").glob("production_creative_report_*.md")))
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
            return report_date_from_timestamp(run_timestamp)
        except ValueError:
            pass
    if len(run_id) >= 8 and run_id[:8].isdigit():
        return f"{run_id[:4]}-{run_id[4:6]}-{run_id[6:8]}"
    return "unknown-date"


def _has_final_output_reports(rows: list[Any]) -> bool:
    for row in rows:
        manifest = _json_loads(row["raw_json"])
        outputs = manifest.get("outputs") if isinstance(manifest, dict) else {}
        final_outputs = outputs.get("final_outputs") if isinstance(outputs, dict) else None
        if not isinstance(final_outputs, list):
            continue
        if any(isinstance(item, dict) and item.get("path") for item in final_outputs):
            return True
    return False


def _ambiguous_final_output_paths(workspace: Path, rows: list[Any]) -> set[str]:
    counts: dict[str, int] = {}
    for row in rows:
        manifest = _json_loads(row["raw_json"])
        outputs = manifest.get("outputs") if isinstance(manifest, dict) else {}
        if not isinstance(outputs, dict):
            continue
        output_root = _output_root(workspace, outputs)
        final_outputs = outputs.get("final_outputs")
        if not isinstance(final_outputs, list):
            continue
        seen_for_run: set[str] = set()
        for item in final_outputs:
            if not isinstance(item, dict):
                continue
            kind = str(item.get("kind") or "").lower()
            label = str(item.get("label") or "").lower()
            raw_path = item.get("path")
            if not raw_path or (kind != "markdown" and "report" not in label):
                continue
            seen_for_run.add(_path_key(output_root / str(raw_path)))
        for key in seen_for_run:
            counts[key] = counts.get(key, 0) + 1
    return {key for key, count in counts.items() if count > 1}


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


def _path_key(path: Path) -> str:
    return str(path).replace("\\", "/").lower()
