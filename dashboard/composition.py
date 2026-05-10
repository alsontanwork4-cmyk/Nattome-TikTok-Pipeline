from __future__ import annotations

from .config import DashboardSettings
from .supabase_client import DashboardSupabaseClient


class EmptyDashboardDataClient:
    def list_runs(self, *, limit: int = 50) -> list[dict]:
        return []

    def get_run(self, run_id: str) -> dict | None:
        return None

    def list_run_outputs(self, run_id: str) -> list[dict]:
        return []

    def get_artifact_metadata(self, artifact_id: str) -> object | None:
        return None

    def create_signed_artifact_url(
        self,
        metadata: object,
        *,
        expires_in: int = 900,
    ) -> str:
        return ""

    def get_report_artifact(self, run_id: str) -> object | None:
        return None

    def download_artifact_text(self, metadata: object) -> str | None:
        return None

    def list_raw_videos(self) -> list[dict]:
        return []

    def list_selected_videos(self) -> list[dict]:
        return []

    def list_settings_versions(self) -> list[dict]:
        return []

    def save_settings_version(
        self,
        settings: dict,
        *,
        reason: str,
        user: str,
    ) -> dict:
        return {}

    def rollback_settings_version(
        self,
        *,
        target_version: int,
        reason: str,
        user: str,
    ) -> dict:
        return {}

    def get_active_manual_run(self, *, run_type: str) -> dict | None:
        return None

    def enqueue_manual_run(self, manual_run: dict, run: dict) -> dict:
        return manual_run


def build_dashboard_data_client(
    settings: DashboardSettings,
    *,
    require_supabase: bool | None = None,
) -> object:
    if require_supabase is None:
        require_supabase = settings.runtime_mode == "production"

    if not settings.supabase_url or not settings.supabase_service_role_key:
        if require_supabase:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for the "
                "production dashboard data client."
            )
        return EmptyDashboardDataClient()

    try:
        from supabase import create_client
    except ImportError as exc:  # pragma: no cover - dependency issue is environment-specific
        if not require_supabase:
            return EmptyDashboardDataClient()
        raise RuntimeError(
            "The supabase package is required for the production dashboard data client."
        ) from exc

    return DashboardSupabaseClient(
        create_client(settings.supabase_url, settings.supabase_service_role_key),
        storage_bucket=settings.supabase_storage_bucket,
    )
