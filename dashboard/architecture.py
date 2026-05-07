from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .indexer import index_pipeline_artifacts
from .store import connect_dashboard_store


@dataclass(frozen=True)
class ArchitectureDocument:
    path: str
    title: str
    doc_type: str


@dataclass(frozen=True)
class PipelineFlowStep:
    name: str
    summary: str


@dataclass(frozen=True)
class ToolDecision:
    name: str
    summary: str


@dataclass(frozen=True)
class PhaseStatus:
    name: str
    status: str
    run_id: str
    detail: str


@dataclass(frozen=True)
class LineageStep:
    name: str
    path: str
    status: str
    summary: str


@dataclass(frozen=True)
class PipelineArchitecture:
    documents: list[ArchitectureDocument]
    pipeline_flow: list[PipelineFlowStep]
    tool_decisions: list[ToolDecision]
    phase_statuses: list[PhaseStatus]
    file_output_map: dict[str, list[str]]
    data_lineage: list[LineageStep]


def load_pipeline_architecture(workspace: Path | str = ".") -> PipelineArchitecture:
    """Build a read-only architecture view model from indexed pipeline artifacts."""
    workspace_path = Path(workspace)
    index_pipeline_artifacts(workspace_path)
    connection = connect_dashboard_store(workspace_path)
    try:
        latest_run = _latest_run(connection)
        documents = _documents(connection)
        return PipelineArchitecture(
            documents=documents,
            pipeline_flow=_pipeline_flow(),
            tool_decisions=_tool_decisions(),
            phase_statuses=_phase_statuses(latest_run),
            file_output_map=_file_output_map(connection, documents),
            data_lineage=_data_lineage(connection, latest_run),
        )
    finally:
        connection.close()


def _documents(connection: sqlite3.Connection) -> list[ArchitectureDocument]:
    type_order = {
        "readme": 0,
        "domain_context": 1,
        "prd": 2,
        "adr": 3,
        "skill": 4,
    }
    rows = connection.execute(
        """
        SELECT path, title, doc_type
        FROM documentation_records
        ORDER BY doc_type, path
        """
    ).fetchall()
    docs = [
        ArchitectureDocument(
            path=str(row["path"]),
            title=str(row["title"]),
            doc_type=str(row["doc_type"]),
        )
        for row in rows
    ]
    return sorted(docs, key=lambda doc: (type_order.get(doc.doc_type, 99), doc.path))


def _pipeline_flow() -> list[PipelineFlowStep]:
    return [
        PipelineFlowStep("Scrape", "Apify collects TikTok candidates and downloadable source-video links."),
        PipelineFlowStep("Score", "The dashboard scores candidate volume, relevance, freshness, engagement, and noise."),
        PipelineFlowStep("Select", "The batch run applies eligibility filters and selects the highest-value candidates."),
        PipelineFlowStep("Analyze", "Gemini produces evidence-first video observations for selected source videos."),
        PipelineFlowStep("Report", "The pipeline writes marketer-facing reports, workbooks, logs, and audit JSON."),
    ]


def _tool_decisions() -> list[ToolDecision]:
    return [
        ToolDecision(
            "Apify discovery/download",
            "Apify is the discovery and download boundary for TikTok candidate metadata and source videos.",
        ),
        ToolDecision(
            "Gemini evidence-first analysis",
            "Gemini analyzes source videos before local report generation so creative recommendations cite evidence.",
        ),
        ToolDecision(
            "Local dashboard index",
            "SQLite indexes raw scrapes, run folders, outputs, docs, curation, settings, and dashboard-only state.",
        ),
        ToolDecision(
            "Durable output formats",
            "Markdown, structured JSON, Excel workbooks, and logs stay linked for marketer review and audit trails.",
        ),
    ]


def _phase_statuses(latest_run: sqlite3.Row | None) -> list[PhaseStatus]:
    default_phases = [
        "apify_scrape",
        "candidate_selection",
        "evidence_bundles",
        "gemini_evidence",
        "report_generation",
        "excel_generation",
        "telegram_delivery",
    ]
    if latest_run is None:
        return [
            PhaseStatus(name=phase, status="not indexed", run_id="", detail="No Batch Analysis Run has been indexed yet.")
            for phase in default_phases
        ]
    run_id = str(latest_run["run_id"])
    manifest = _json_loads(latest_run["raw_json"])
    phases = manifest.get("phases")
    if not isinstance(phases, list) or not phases:
        return [
            PhaseStatus(name=phase, status="not recorded", run_id=run_id, detail="Latest run has no phase metadata.")
            for phase in default_phases
        ]
    statuses: list[PhaseStatus] = []
    for phase in phases:
        if not isinstance(phase, dict):
            continue
        name = str(phase.get("name") or "phase")
        status = str(phase.get("status") or "unknown")
        detail = str(phase.get("reason") or phase.get("exception") or phase.get("error") or "")
        statuses.append(PhaseStatus(name=name, status=status, run_id=run_id, detail=detail))
    return statuses


def _file_output_map(
    connection: sqlite3.Connection,
    documents: list[ArchitectureDocument],
) -> dict[str, list[str]]:
    raw_scrapes = _column_values(
        connection,
        "SELECT path FROM artifact_sources WHERE artifact_type = 'raw_scrape' ORDER BY path",
    )
    run_folders = _column_values(connection, "SELECT run_folder FROM batch_runs ORDER BY run_folder")
    reports = _column_values(
        connection,
        """
        SELECT artifact_path FROM run_outputs
        WHERE artifact_type IN ('report_markdown', 'report_json')
        ORDER BY artifact_path
        """,
    )
    workbooks = _column_values(
        connection,
        """
        SELECT artifact_path FROM run_outputs
        WHERE artifact_type = 'excel_workbook'
        ORDER BY artifact_path
        """,
    )
    logs = _column_values(
        connection,
        """
        SELECT artifact_path FROM run_outputs
        WHERE artifact_type = 'log'
        ORDER BY artifact_path
        """,
    )
    return {
        "Raw scrapes": raw_scrapes,
        "Run folders": run_folders,
        "Reports": reports,
        "Workbooks": workbooks,
        "Logs": logs,
        "Documentation": [doc.path for doc in documents],
    }


def _data_lineage(
    connection: sqlite3.Connection,
    latest_run: sqlite3.Row | None,
) -> list[LineageStep]:
    if latest_run is None:
        return [
            LineageStep("Raw scrape", "", "not indexed", "No raw scrape has been linked to an indexed run yet."),
            LineageStep("Selected batch", "", "not indexed", "No selected batch has been indexed yet."),
            LineageStep("Final report", "", "not indexed", "No final output has been indexed yet."),
        ]
    run_id = str(latest_run["run_id"])
    selected = connection.execute(
        "SELECT * FROM selected_batches WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    outputs = _output_paths_by_type(connection, run_id)
    raw_path = str(selected["candidate_source"] or "") if selected else ""
    selected_path = str(selected["path"] or "") if selected else ""
    return [
        LineageStep(
            "Raw scrape",
            raw_path,
            "available" if raw_path else "missing",
            "Candidate metadata and source-video URLs enter the pipeline here.",
        ),
        LineageStep(
            "Selected batch",
            selected_path,
            "available" if selected_path else "missing",
            "Eligibility and ranking reduce the scrape to the analysis set.",
        ),
        LineageStep(
            "Evidence bundle index",
            _first(outputs, "selected_batch", "manifest", "metadata"),
            "available" if outputs else "missing",
            "Run metadata and evidence indexes connect selected videos to analysis artifacts.",
        ),
        LineageStep(
            "Final report",
            _first(outputs, "report_markdown"),
            "available" if outputs.get("report_markdown") else "missing",
            "Markdown reports carry the marketer-facing creative read.",
        ),
        LineageStep(
            "Planning workbook",
            _first(outputs, "excel_workbook"),
            "available" if outputs.get("excel_workbook") else "missing",
            "Excel workbooks turn approved angles into production planning rows.",
        ),
        LineageStep(
            "Delivery log",
            _first(outputs, "log"),
            "available" if outputs.get("log") else "missing",
            "Logs preserve delivery and operational status after outputs are generated.",
        ),
    ]


def _latest_run(connection: sqlite3.Connection) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT *
        FROM batch_runs
        ORDER BY COALESCE(run_timestamp, '') DESC, run_id DESC
        LIMIT 1
        """
    ).fetchone()


def _column_values(connection: sqlite3.Connection, query: str) -> list[str]:
    values = [str(row[0]) for row in connection.execute(query).fetchall() if row[0]]
    return sorted(set(values))


def _output_paths_by_type(connection: sqlite3.Connection, run_id: str) -> dict[str, list[str]]:
    paths: dict[str, list[str]] = {}
    for row in connection.execute(
        """
        SELECT artifact_type, artifact_path
        FROM run_outputs
        WHERE run_id = ?
        ORDER BY artifact_type, artifact_path
        """,
        (run_id,),
    ):
        paths.setdefault(str(row["artifact_type"]), []).append(str(row["artifact_path"]))
    return paths


def _first(values: dict[str, list[str]], *keys: str) -> str:
    for key in keys:
        if values.get(key):
            return values[key][0]
    return ""


def _json_loads(value: object) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
