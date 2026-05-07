from __future__ import annotations

from pathlib import Path

from .web_architecture import _render_pipeline_architecture
from .web_components import _render_placeholder, _render_sidebar, _render_topbar, _title_for_path
from .web_nattome_pov_library import _render_nattome_pov_library
from .web_overview import _render_overview
from .web_pattern_library import _render_pattern_library
from .web_recommendations import _render_recommendations
from .web_run_history import _render_run_history
from .web_settings import _render_scrape_settings
from .web_theme import render_theme_styles


def render_page(
    active_path: str,
    workspace: Path,
    *,
    query_params: dict[str, list[str]] | None = None,
    run_history_run_id: str = "",
    run_history_tab: str = "",
) -> str:
    title = _title_for_path(active_path)
    query_params = query_params or {}
    sidebar = _render_sidebar(active_path)
    topbar = _render_topbar(active_path, workspace)
    if active_path == "/":
        overview = _render_overview(workspace)
    elif active_path == "/scrape-settings":
        overview = _render_scrape_settings(workspace)
    elif active_path == "/run-history":
        overview = _render_run_history(
            workspace,
            run_history_run_id=run_history_run_id,
            run_history_tab=run_history_tab,
        )
    elif active_path == "/recommendations":
        overview = _render_recommendations(workspace)
    elif active_path == "/pattern-library":
        overview = _render_pattern_library(workspace)
    elif active_path == "/nattome-pov-library":
        overview = _render_nattome_pov_library(workspace)
    elif active_path == "/pipeline-architecture":
        overview = _render_pipeline_architecture(workspace)
    else:
        overview = _render_placeholder(title)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Nattome Scrape Quality Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&display=swap" rel="stylesheet">
  <style>
{render_theme_styles()}
  </style>
</head>
<body>
  <div class="layout">
    {topbar}
    {sidebar}
    <main>
      {overview}
    </main>
  </div>
</body>
</html>
"""
