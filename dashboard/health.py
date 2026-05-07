from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
import sqlite3
from typing import Any

from .store import initialize_dashboard_store


SEVERITY_ORDER = {
    "info": 0,
    "warning": 1,
    "error": 2,
    "blocked": 3,
}


@dataclass(frozen=True)
class PipelineHealthItem:
    component: str
    severity: str
    status: str
    impact: str
    details: dict[str, Any]


@dataclass(frozen=True)
class PipelineHealthSummary:
    run_id: str
    severity: str
    status: str
    impact_summary: str
    items: list[PipelineHealthItem]


def compute_pipeline_health(workspace: Path | str = ".") -> list[PipelineHealthSummary]:
    """Summarize operational health for indexed Batch Analysis Runs."""
    workspace_path = Path(workspace)
    db_path = initialize_dashboard_store(workspace_path)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("DELETE FROM pipeline_health_summaries")
        summaries = [
            _summarize_run(connection, workspace_path, row)
            for row in connection.execute("SELECT * FROM batch_runs ORDER BY run_timestamp, run_id")
        ]
        for summary in summaries:
            _persist_summary(connection, summary)
        connection.commit()
        return summaries
    finally:
        connection.close()


def _summarize_run(
    connection: sqlite3.Connection,
    workspace: Path,
    run: sqlite3.Row,
) -> PipelineHealthSummary:
    run_id = str(run["run_id"])
    run_folder = workspace / str(run["run_folder"])
    manifest = _json_loads(run["raw_json"])
    phases = _phase_map(manifest)
    selected = connection.execute(
        "SELECT * FROM selected_batches WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    raw_count = _count(connection, "raw_videos", "run_id", run_id)
    selected_json = _json_loads(selected["raw_json"]) if selected else {}
    candidate_source = selected["candidate_source"] if selected else _candidate_source_from_manifest(manifest)
    bundle_path = run_folder / "data" / "evidence_bundle_index.json"
    bundle_index = _read_json(bundle_path)
    telegram_log_path = run_folder / "logs" / "telegram_delivery.json"
    telegram_log = _read_json(telegram_log_path)

    items = [
        _apify_scrape_item(connection, workspace, run, raw_count, candidate_source),
        _raw_candidates_item(workspace, run, raw_count, candidate_source),
        _selected_batch_item(workspace, run, selected, selected_json),
        _source_video_item(workspace, run, bundle_path, bundle_index),
        _gemini_item(workspace, run, phases, bundle_path, bundle_index),
        _report_item(connection, workspace, run, phases, bundle_index),
        _excel_item(connection, workspace, run, phases),
        _telegram_item(workspace, run, phases, telegram_log_path, telegram_log),
    ]
    items.extend(_phase_error_items(workspace, run, phases))

    severity = max((item.severity for item in items), key=lambda value: SEVERITY_ORDER[value])
    status = _summary_status(severity, items)
    return PipelineHealthSummary(
        run_id=run_id,
        severity=severity,
        status=status,
        impact_summary=_impact_summary(status, severity),
        items=items,
    )


def _apify_scrape_item(
    connection: sqlite3.Connection,
    workspace: Path,
    run: sqlite3.Row,
    raw_count: int,
    candidate_source: str | None,
) -> PipelineHealthItem:
    raw_source = connection.execute(
        """
        SELECT * FROM artifact_sources
        WHERE artifact_type = 'raw_scrape'
        ORDER BY generated_at DESC, path
        LIMIT 1
        """
    ).fetchone()
    if raw_count > 0 or raw_source:
        return _item(
            "apify_scrape",
            "info",
            "completed",
            f"Apify produced raw scrape data for review; {raw_count} candidates are tied to this run.",
            run,
            phase="apify_scrape",
            file_path=candidate_source or (raw_source["path"] if raw_source else None),
            raw_json=_json_loads(raw_source["metadata_json"]) if raw_source else None,
            timestamp=raw_source["generated_at"] if raw_source else run["run_timestamp"],
        )
    return _item(
        "apify_scrape",
        "blocked",
        "missing",
        "No raw Apify scrape data is available, so downstream marketer review cannot start.",
        run,
        phase="apify_scrape",
        file_path=candidate_source,
    )


def _raw_candidates_item(
    workspace: Path,
    run: sqlite3.Row,
    raw_count: int,
    candidate_source: str | None,
) -> PipelineHealthItem:
    source_path = _workspace_path(workspace, candidate_source)
    if source_path and source_path.exists() and raw_count > 0:
        return _item(
            "raw_candidates",
            "info",
            "completed",
            f"Raw candidate file is present with {raw_count} indexed candidate records.",
            run,
            phase="candidate_selection",
            file_path=candidate_source,
            raw_json=_read_json(source_path),
        )
    if raw_count > 0:
        return _item(
            "raw_candidates",
            "warning",
            "partial",
            "Candidates were indexed, but the original raw candidate file was not found for debugging.",
            run,
            phase="candidate_selection",
            file_path=candidate_source,
        )
    return _item(
        "raw_candidates",
        "blocked",
        "missing",
        "No raw candidates are indexed for this run.",
        run,
        phase="candidate_selection",
        file_path=candidate_source,
    )


def _selected_batch_item(
    workspace: Path,
    run: sqlite3.Row,
    selected: sqlite3.Row | None,
    selected_json: dict[str, Any],
) -> PipelineHealthItem:
    if selected and int(selected["selected_candidate_count"] or 0) > 0:
        return _item(
            "selected_batch",
            "info",
            "completed",
            f"{selected['selected_candidate_count']} candidates were selected for analysis.",
            run,
            phase="candidate_selection",
            file_path=selected["path"],
            raw_json=selected_json,
        )
    if selected:
        return _item(
            "selected_batch",
            "warning",
            "partial",
            "The selected batch exists, but no candidates were selected for analysis.",
            run,
            phase="candidate_selection",
            file_path=selected["path"],
            raw_json=selected_json,
        )
    return _item(
        "selected_batch",
        "blocked",
        "missing",
        "No selected batch file is available, so evidence generation cannot proceed.",
        run,
        phase="candidate_selection",
    )


def _source_video_item(
    workspace: Path,
    run: sqlite3.Row,
    bundle_path: Path,
    bundle_index: dict[str, Any],
) -> PipelineHealthItem:
    states = _bundle_states(bundle_index, "source_video")
    available = sum(1 for state in states if state == "available")
    total = len(states)
    details_json = bundle_index if bundle_index else None
    if total and available == total:
        severity, status = "info", "completed"
        impact = "Source videos are available for every selected candidate."
    elif available:
        severity, status = "warning", "partial"
        impact = f"Only {available} of {total} source videos are available; some evidence may be incomplete."
    else:
        severity, status = "blocked", "missing"
        impact = "No selected source videos are available, blocking evidence review."
    return _item(
        "source_videos",
        severity,
        status,
        impact,
        run,
        phase="evidence_bundles",
        file_path=_relative_path(workspace, bundle_path) if bundle_path.exists() else None,
        raw_json=details_json,
    )


def _gemini_item(
    workspace: Path,
    run: sqlite3.Row,
    phases: dict[str, dict[str, Any]],
    bundle_path: Path,
    bundle_index: dict[str, Any],
) -> PipelineHealthItem:
    phase = phases.get("gemini_evidence", {})
    phase_status = str(phase.get("status") or "")
    states = _artifact_states(bundle_index, "gemini_evidence")
    completed = sum(1 for state in states if state == "completed")
    total = len(states)
    if total and completed == total and phase_status not in {"failed", "error", "blocked"}:
        severity, status = "info", "completed"
        impact = "Gemini evidence is available for every selected candidate."
    elif phase_status in {"failed", "error"}:
        severity, status = "error", phase_status
        impact = "Gemini evidence failed, so marketer-facing analysis may be unavailable."
    elif phase_status == "blocked":
        severity, status = "blocked", "blocked"
        impact = "Gemini evidence is blocked by an earlier pipeline step."
    elif completed:
        severity, status = "warning", "partial"
        impact = f"Gemini evidence is partial: {completed} of {total} candidates completed."
    else:
        severity, status = "warning", "missing"
        impact = "Gemini evidence is not available yet."
    return _item(
        "gemini_evidence",
        severity,
        status,
        impact,
        run,
        phase="gemini_evidence",
        file_path=_relative_path(workspace, bundle_path) if bundle_path.exists() else None,
        raw_json=phase or bundle_index or None,
        exception_text=_exception_text(phase),
    )


def _report_item(
    connection: sqlite3.Connection,
    workspace: Path,
    run: sqlite3.Row,
    phases: dict[str, dict[str, Any]],
    bundle_index: dict[str, Any],
) -> PipelineHealthItem:
    reports = _outputs(connection, run["run_id"], ("report_markdown",))
    run_folder = workspace / str(run["run_folder"])
    run_reports = sorted((run_folder / "reports").glob("*.md"))
    states = _artifact_states(bundle_index, "video_evidence_report")
    completed_states = sum(1 for state in states if state == "completed")
    completed = len(reports) or len(run_reports) or completed_states
    if completed:
        severity, status = "info", "completed"
        impact = f"{completed} marketer-readable report artifacts are available."
    else:
        phase = phases.get("cross_video_pattern_summary") or phases.get("report_generation") or {}
        status = str(phase.get("status") or "missing")
        severity = "error" if status in {"failed", "error"} else "warning"
        impact = "No marketer-readable report artifact was generated."
    first = reports[0] if reports else None
    return _item(
        "report_generation",
        severity,
        status,
        impact,
        run,
        phase="report_generation",
        file_path=first["artifact_path"] if first else (_relative_path(workspace, run_reports[0]) if run_reports else None),
        raw_json=dict(first) if first else None,
    )


def _excel_item(
    connection: sqlite3.Connection,
    workspace: Path,
    run: sqlite3.Row,
    phases: dict[str, dict[str, Any]],
) -> PipelineHealthItem:
    outputs = _outputs(connection, run["run_id"], ("excel_workbook", "structured_outputs"))
    csv_path = workspace / str(run["run_folder"]) / "data" / "spreadsheet_summary.csv"
    if outputs or csv_path.exists():
        first = outputs[0] if outputs else None
        return _item(
            "excel_generation",
            "info",
            "completed",
            "Planning spreadsheet output is available for downstream use.",
            run,
            phase="structured_outputs",
            file_path=first["artifact_path"] if first else _relative_path(workspace, csv_path),
            raw_json=dict(first) if first else None,
        )
    phase = phases.get("structured_outputs") or {}
    status = str(phase.get("status") or "missing")
    severity = "error" if status in {"failed", "error"} else "warning"
    return _item(
        "excel_generation",
        severity,
        status,
        "No spreadsheet output is available for planning workflows.",
        run,
        phase="structured_outputs",
        raw_json=phase or None,
        exception_text=_exception_text(phase),
    )


def _telegram_item(
    workspace: Path,
    run: sqlite3.Row,
    phases: dict[str, dict[str, Any]],
    log_path: Path,
    telegram_log: dict[str, Any],
) -> PipelineHealthItem:
    phase = phases.get("telegram_delivery") or {}
    status = str(telegram_log.get("status") or phase.get("status") or "missing")
    if status in {"sent", "completed"}:
        severity = "info"
        impact = "Telegram delivery completed."
    elif status == "skipped":
        severity = "warning"
        impact = "Telegram delivery was skipped; marketers may need to read the dashboard or files directly."
    elif status in {"failed", "error"}:
        severity = "error"
        impact = "Telegram delivery failed; marketers may not receive the run summary automatically."
    else:
        severity = "warning"
        impact = "Telegram delivery status is unavailable."
    return _item(
        "telegram_delivery",
        severity,
        status,
        impact,
        run,
        phase="telegram_delivery",
        log_path=_relative_path(workspace, log_path) if log_path.exists() else None,
        raw_json=telegram_log or phase or None,
        exception_text=_exception_text(telegram_log) or _exception_text(phase),
    )


def _phase_error_items(
    workspace: Path,
    run: sqlite3.Row,
    phases: dict[str, dict[str, Any]],
) -> list[PipelineHealthItem]:
    items: list[PipelineHealthItem] = []
    covered = {
        "apify_scrape",
        "candidate_selection",
        "evidence_bundles",
        "gemini_evidence",
        "cross_video_pattern_summary",
        "report_generation",
        "structured_outputs",
        "telegram_delivery",
    }
    for phase_name, phase in phases.items():
        status = str(phase.get("status") or "")
        if phase_name in covered or status not in {"failed", "error", "blocked"}:
            continue
        severity = "blocked" if status == "blocked" else "error"
        items.append(
            _item(
                f"phase_error:{phase_name}",
                severity,
                status,
                f"{phase_name.replace('_', ' ').title()} reported {status}.",
                run,
                phase=phase_name,
                raw_json=phase,
                exception_text=_exception_text(phase),
            )
        )
    return items


def _item(
    component: str,
    severity: str,
    status: str,
    impact: str,
    run: sqlite3.Row,
    *,
    phase: str,
    log_path: str | None = None,
    raw_json: Any | None = None,
    exception_text: str | None = None,
    file_path: str | None = None,
    timestamp: str | None = None,
) -> PipelineHealthItem:
    return PipelineHealthItem(
        component=component,
        severity=severity,
        status=status,
        impact=impact,
        details={
            "phase": phase,
            "status": status,
            "log_path": log_path,
            "raw_json": raw_json,
            "exception_text": exception_text,
            "file_path": file_path,
            "timestamp": timestamp or run["run_timestamp"],
        },
    )


def _phase_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    phases = manifest.get("phases")
    if not isinstance(phases, list):
        return {}
    return {
        str(phase.get("name")): phase
        for phase in phases
        if isinstance(phase, dict) and phase.get("name")
    }


def _bundle_states(bundle_index: dict[str, Any], key: str) -> list[str]:
    bundles = bundle_index.get("bundles")
    if not isinstance(bundles, list):
        return []
    states: list[str] = []
    for bundle in bundles:
        if isinstance(bundle, dict) and isinstance(bundle.get(key), dict):
            state = bundle[key].get("state")
            if state:
                states.append(str(state))
    return states


def _artifact_states(bundle_index: dict[str, Any], artifact: str) -> list[str]:
    bundles = bundle_index.get("bundles")
    if not isinstance(bundles, list):
        return []
    states: list[str] = []
    for bundle in bundles:
        artifacts = bundle.get("artifacts") if isinstance(bundle, dict) else None
        artifact_data = artifacts.get(artifact) if isinstance(artifacts, dict) else None
        if isinstance(artifact_data, dict) and artifact_data.get("state"):
            states.append(str(artifact_data["state"]))
    return states


def _outputs(
    connection: sqlite3.Connection,
    run_id: str,
    artifact_types: tuple[str, ...],
) -> list[sqlite3.Row]:
    placeholders = ",".join("?" for _ in artifact_types)
    return list(
        connection.execute(
            f"""
            SELECT * FROM run_outputs
            WHERE run_id = ?
              AND artifact_type IN ({placeholders})
              AND exists_on_disk = 1
            ORDER BY artifact_path
            """,
            (run_id, *artifact_types),
        )
    )


def _summary_status(severity: str, items: list[PipelineHealthItem]) -> str:
    if severity == "blocked":
        return "blocked"
    if severity == "error":
        return "error"
    if severity == "warning":
        return "partial" if any(item.status == "partial" for item in items) else "warning"
    return "completed"


def _impact_summary(status: str, severity: str) -> str:
    if status == "completed":
        return "Pipeline outputs are ready for marketer review."
    if status == "partial":
        return "Pipeline outputs are partially ready; review warnings before using the run."
    if status == "warning":
        return "Pipeline completed with delivery or artifact warnings."
    if status == "error":
        return "Pipeline hit an error that may leave marketer outputs incomplete."
    if severity == "blocked":
        return "Pipeline is blocked before marketer-ready outputs can be trusted."
    return "Pipeline status needs review."


def _persist_summary(connection: sqlite3.Connection, summary: PipelineHealthSummary) -> None:
    connection.execute(
        """
        INSERT INTO pipeline_health_summaries (
            run_id,
            severity,
            status,
            impact_summary,
            items_json
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            summary.run_id,
            summary.severity,
            summary.status,
            summary.impact_summary,
            json.dumps([asdict(item) for item in summary.items], ensure_ascii=True, sort_keys=True),
        ),
    )


def _candidate_source_from_manifest(manifest: dict[str, Any]) -> str | None:
    for phase in manifest.get("phases", []):
        if not isinstance(phase, dict) or phase.get("name") != "candidate_selection":
            continue
        inputs = phase.get("inputs")
        if isinstance(inputs, dict) and inputs.get("candidates_path"):
            return str(inputs["candidates_path"]).replace("\\", "/")
    return None


def _count(connection: sqlite3.Connection, table: str, column: str, value: str) -> int:
    return int(
        connection.execute(
            f"SELECT COUNT(*) FROM {table} WHERE {column} = ?",
            (value,),
        ).fetchone()[0]
    )


def _exception_text(value: dict[str, Any]) -> str | None:
    for key in ("exception", "exception_text", "error", "reason"):
        candidate = value.get(key)
        if candidate:
            return str(candidate)
    return None


def _workspace_path(workspace: Path, relative: str | None) -> Path | None:
    if not relative:
        return None
    path = Path(relative)
    if path.is_absolute():
        return path
    return workspace / path


def _relative_path(workspace: Path, path: Path) -> str:
    try:
        return str(path.relative_to(workspace)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _json_loads(value: Any) -> dict[str, Any]:
    if not value:
        return {}
    try:
        data = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}
