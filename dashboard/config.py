from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from batch_analysis.env import load_dotenv_files


_DASHBOARD_ROOT = Path(__file__).resolve().parent
_PROJECT_ROOT = _DASHBOARD_ROOT.parent


@dataclass(frozen=True)
class DashboardSettings:
    runtime_mode: str = "development"
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_storage_bucket: str = "dashboard-artifacts"
    workspace_path: Path | str = _PROJECT_ROOT
    runs_path: Path | str | None = None
    data_path: Path | str | None = None
    templates_path: Path | str = _DASHBOARD_ROOT / "templates"
    assets_path: Path | str = _DASHBOARD_ROOT / "assets"

    def __post_init__(self) -> None:
        workspace_path = _resolve_path(self.workspace_path)
        object.__setattr__(self, "workspace_path", workspace_path)
        object.__setattr__(
            self,
            "runs_path",
            _resolve_path(self.runs_path) if self.runs_path is not None else workspace_path / "runs",
        )
        object.__setattr__(
            self,
            "data_path",
            _resolve_path(self.data_path) if self.data_path is not None else workspace_path / "data",
        )
        object.__setattr__(self, "templates_path", _resolve_path(self.templates_path))
        object.__setattr__(self, "assets_path", _resolve_path(self.assets_path))

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "DashboardSettings":
        if env is None:
            load_dotenv_files([Path.cwd(), _PROJECT_ROOT])
        source = os.environ if env is None else env
        workspace_path = _env_path(source, "DASHBOARD_WORKSPACE_PATH", _PROJECT_ROOT)
        return cls(
            runtime_mode=source.get("DASHBOARD_RUNTIME_MODE", "development"),
            supabase_url=source.get("SUPABASE_URL", ""),
            supabase_anon_key=source.get("SUPABASE_ANON_KEY", ""),
            supabase_service_role_key=source.get("SUPABASE_SERVICE_ROLE_KEY", ""),
            supabase_storage_bucket=source.get(
                "SUPABASE_STORAGE_BUCKET",
                "dashboard-artifacts",
            ),
            workspace_path=workspace_path,
            runs_path=_env_path(source, "DASHBOARD_RUNS_PATH", Path(workspace_path) / "runs"),
            data_path=_env_path(source, "DASHBOARD_DATA_PATH", Path(workspace_path) / "data"),
            templates_path=_env_path(
                source,
                "DASHBOARD_TEMPLATES_PATH",
                _DASHBOARD_ROOT / "templates",
            ),
            assets_path=_env_path(source, "DASHBOARD_ASSETS_PATH", _DASHBOARD_ROOT / "assets"),
        )


def _env_path(source: Mapping[str, str], key: str, fallback: Path | str) -> Path | str:
    value = source.get(key)
    return value if value else fallback


def _resolve_path(path: Path | str) -> Path:
    return Path(path).expanduser().resolve()
