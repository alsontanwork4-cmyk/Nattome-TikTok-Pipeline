from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .indexer import IndexSummary, index_pipeline_artifacts


RefreshScope = Literal["artifacts", "all"]


@dataclass(frozen=True)
class DashboardRefreshResult:
    intent: str
    scope: RefreshScope
    artifact_summary: IndexSummary


def refresh_dashboard_derivatives(
    workspace: Path | str = ".",
    *,
    intent: str = "dashboard_read",
    scope: RefreshScope = "all",
) -> DashboardRefreshResult:
    """Refresh dashboard-derived tables for local artifact-backed read paths."""
    workspace_path = Path(workspace)
    artifact_summary = index_pipeline_artifacts(workspace_path)

    return DashboardRefreshResult(
        intent=intent,
        scope=scope,
        artifact_summary=artifact_summary,
    )
