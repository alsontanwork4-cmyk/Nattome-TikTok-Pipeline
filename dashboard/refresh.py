from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .health import PipelineHealthSummary, compute_pipeline_health
from .indexer import IndexSummary, index_pipeline_artifacts
from .quality import ScrapeQualityScore, compute_scrape_quality_scores


RefreshScope = Literal["artifacts", "quality", "all"]


@dataclass(frozen=True)
class DashboardRefreshResult:
    intent: str
    scope: RefreshScope
    artifact_summary: IndexSummary
    quality_scores: list[ScrapeQualityScore]
    health_summaries: list[PipelineHealthSummary]


def refresh_dashboard_derivatives(
    workspace: Path | str = ".",
    *,
    intent: str = "dashboard_read",
    scope: RefreshScope = "all",
) -> DashboardRefreshResult:
    """Refresh dashboard-derived tables for local artifact-backed read paths."""
    workspace_path = Path(workspace)
    artifact_summary = index_pipeline_artifacts(workspace_path)
    quality_scores: list[ScrapeQualityScore] = []
    health_summaries: list[PipelineHealthSummary] = []

    if scope in {"quality", "all"}:
        quality_scores = compute_scrape_quality_scores(workspace_path)
    if scope == "all":
        health_summaries = compute_pipeline_health(workspace_path)

    return DashboardRefreshResult(
        intent=intent,
        scope=scope,
        artifact_summary=artifact_summary,
        quality_scores=quality_scores,
        health_summaries=health_summaries,
    )
