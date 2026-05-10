from __future__ import annotations

from dataclasses import dataclass
from typing import Any


DASHBOARD_TABLE_CONTRACT: dict[str, tuple[str, ...]] = {
    "runs": (
        "run_id",
        "status",
        "run_type",
        "mode",
        "started_at",
        "finished_at",
        "duration_seconds",
        "triggered_by",
        "created_by",
        "error_summary",
        "raw_candidate_count",
        "eligible_candidate_count",
        "selected_count",
        "report_date",
        "summary",
        "created_at",
        "updated_at",
    ),
    "run_outputs": (
        "run_id",
        "artifact_type",
        "bucket",
        "object_path",
        "filename",
        "content_type",
        "size_bytes",
        "checksum",
        "created_at",
    ),
    "raw_videos": (
        "video_id",
        "run_id",
        "tiktok_url",
        "author_handle",
        "caption",
        "hashtags",
        "source_input",
        "play_count",
        "like_count",
        "comment_count",
        "share_count",
        "created_at",
        "updated_at",
    ),
    "selected_videos": (
        "run_id",
        "video_id",
        "selection_rank",
        "selection_reason",
        "evidence_status",
        "created_at",
        "updated_at",
    ),
    "video_curation": (
        "video_id",
        "labels",
        "note",
        "exclude_similar_reason",
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
    ),
    "scrape_settings_versions": (
        "version",
        "settings",
        "reason",
        "is_active",
        "rollback_of_version",
        "created_by",
        "created_at",
    ),
    "manual_runs": (
        "id",
        "run_id",
        "status",
        "run_type",
        "triggered_by",
        "requested_at",
        "claimed_at",
        "finished_at",
        "error_summary",
        "created_at",
        "updated_at",
    ),
}

ARTIFACT_METADATA_FIELDS = frozenset(DASHBOARD_TABLE_CONTRACT["run_outputs"])


@dataclass(frozen=True)
class ArtifactMetadata:
    run_id: str
    artifact_type: str
    bucket: str
    object_path: str
    filename: str
    content_type: str = ""
    size_bytes: int | None = None
    checksum: str | None = None
    created_at: str | None = None

    def to_record(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "artifact_type": self.artifact_type,
            "bucket": self.bucket,
            "object_path": self.object_path,
            "filename": self.filename,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
            "checksum": self.checksum,
            "created_at": self.created_at,
        }


class DashboardSupabaseClient:
    def __init__(self, client: Any, *, storage_bucket: str):
        self._client = client
        self.storage_bucket = storage_bucket

    def list_runs(self, *, limit: int = 50) -> list[dict[str, Any]]:
        response = (
            self._client.table("runs")
            .select("*")
            .order("started_at", desc=True)
            .limit(limit)
            .execute()
        )
        return list(response.data or [])

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        response = (
            self._client.table("runs")
            .select("*")
            .eq("run_id", run_id)
            .limit(1)
            .execute()
        )
        rows = list(response.data or [])
        return rows[0] if rows else None

    def list_run_outputs(self, run_id: str) -> list[dict[str, Any]]:
        response = (
            self._client.table("run_outputs")
            .select("*")
            .eq("run_id", run_id)
            .order("created_at", desc=False)
            .execute()
        )
        return list(response.data or [])

    def get_artifact_metadata(self, artifact_id: str) -> ArtifactMetadata | None:
        response = (
            self._client.table("run_outputs")
            .select("*")
            .eq("object_path", artifact_id)
            .limit(1)
            .execute()
        )
        rows = list(response.data or [])
        if not rows:
            return None
        return _artifact_metadata_from_record(
            rows[0],
            default_bucket=self.storage_bucket,
            fallback_object_path=artifact_id,
        )

    def upsert_manual_run(self, record: dict[str, Any]) -> list[dict[str, Any]]:
        response = self._client.table("manual_runs").upsert(record, on_conflict="id").execute()
        return list(response.data or [])

    def upsert_artifact_metadata(self, metadata: ArtifactMetadata) -> list[dict[str, Any]]:
        response = (
            self._client.table("run_outputs")
            .upsert(metadata.to_record(), on_conflict="run_id,object_path")
            .execute()
        )
        return list(response.data or [])

    def create_signed_artifact_url(
        self,
        metadata: ArtifactMetadata,
        *,
        expires_in: int = 3600,
    ) -> str:
        response = (
            self._client.storage.from_(metadata.bucket or self.storage_bucket)
            .create_signed_url(metadata.object_path, expires_in)
        )
        return str(response.get("signedURL") or response.get("signedUrl") or "")


def _artifact_metadata_from_record(
    record: dict[str, Any],
    *,
    default_bucket: str,
    fallback_object_path: str,
) -> ArtifactMetadata:
    object_path = str(record.get("object_path") or fallback_object_path)
    return ArtifactMetadata(
        run_id=str(record.get("run_id") or ""),
        artifact_type=str(record.get("artifact_type") or ""),
        bucket=str(record.get("bucket") or default_bucket),
        object_path=object_path,
        filename=str(record.get("filename") or object_path.rsplit("/", 1)[-1]),
        content_type=str(record.get("content_type") or ""),
        size_bytes=record.get("size_bytes"),
        checksum=record.get("checksum"),
        created_at=record.get("created_at"),
    )
