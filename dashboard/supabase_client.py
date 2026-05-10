from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
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
        "claimed_by",
        "finished_at",
        "expected_output_metadata",
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

    def get_report_artifact(self, run_id: str) -> ArtifactMetadata | None:
        response = (
            self._client.table("run_outputs")
            .select("*")
            .eq("run_id", run_id)
            .eq("artifact_type", "report")
            .limit(1)
            .execute()
        )
        rows = list(response.data or [])
        if not rows:
            return None
        return _artifact_metadata_from_record(
            rows[0],
            default_bucket=self.storage_bucket,
            fallback_object_path=str(rows[0].get("object_path") or ""),
        )

    def download_artifact_text(self, metadata: ArtifactMetadata) -> str | None:
        payload = (
            self._client.storage.from_(metadata.bucket or self.storage_bucket)
            .download(metadata.object_path)
        )
        if payload is None:
            return None
        if isinstance(payload, bytes):
            return payload.decode("utf-8")
        if isinstance(payload, str):
            return payload
        if hasattr(payload, "decode"):
            return payload.decode("utf-8")
        return str(payload)

    def list_raw_videos(self) -> list[dict[str, Any]]:
        response = (
            self._client.table("raw_videos")
            .select("*")
            .order("play_count", desc=True)
            .order("video_id", desc=False)
            .execute()
        )
        return list(response.data or [])

    def list_selected_videos(self) -> list[dict[str, Any]]:
        response = self._client.table("selected_videos").select("*").execute()
        return list(response.data or [])

    def list_video_curation(self) -> list[dict[str, Any]]:
        response = self._client.table("video_curation").select("*").execute()
        return list(response.data or [])

    def list_settings_versions(self) -> list[dict[str, Any]]:
        response = (
            self._client.table("scrape_settings_versions")
            .select("*")
            .order("version", desc=True)
            .execute()
        )
        return list(response.data or [])

    def save_settings_version(
        self,
        settings: dict[str, Any],
        *,
        reason: str,
        user: str,
    ) -> dict[str, Any]:
        versions = self.list_settings_versions()
        next_version = _next_settings_version(versions)
        record = {
            "version": next_version,
            "settings": settings,
            "reason": reason,
            "is_active": True,
            "rollback_of_version": None,
            "created_by": user,
            "updated_by": user,
        }
        return self._insert_settings_version(record)

    def rollback_settings_version(
        self,
        *,
        target_version: int,
        reason: str,
        user: str,
    ) -> dict[str, Any]:
        versions = self.list_settings_versions()
        target = next(
            (version for version in versions if int(version.get("version") or 0) == target_version),
            None,
        )
        if target is None:
            raise ValueError(f"unknown scrape settings version: {target_version}")
        record = {
            "version": _next_settings_version(versions),
            "settings": target.get("settings") or {},
            "reason": reason,
            "is_active": True,
            "rollback_of_version": target_version,
            "created_by": user,
            "updated_by": user,
        }
        return self._insert_settings_version(record)

    def upsert_video_curation(
        self,
        video_id: str,
        *,
        labels: list[str],
        note: str,
        exclude_similar_reason: str,
        user: str,
    ) -> dict[str, Any]:
        record = {
            "video_id": video_id,
            "labels": labels,
            "note": note,
            "exclude_similar_reason": exclude_similar_reason,
            "created_by": user,
            "updated_by": user,
        }
        response = (
            self._client.table("video_curation")
            .upsert(record, on_conflict="video_id")
            .execute()
        )
        rows = list(response.data or [])
        return rows[0] if rows else record

    def _insert_settings_version(self, record: dict[str, Any]) -> dict[str, Any]:
        (
            self._client.table("scrape_settings_versions")
            .update({"is_active": False})
            .eq("is_active", True)
            .execute()
        )
        response = self._client.table("scrape_settings_versions").insert(record).execute()
        rows = list(response.data or [])
        return rows[0] if rows else record

    def upsert_manual_run(self, record: dict[str, Any]) -> list[dict[str, Any]]:
        response = self._client.table("manual_runs").upsert(record, on_conflict="id").execute()
        return list(response.data or [])

    def enqueue_manual_run(
        self,
        manual_run: dict[str, Any],
        run: dict[str, Any],
    ) -> dict[str, Any]:
        self._client.table("runs").upsert(run, on_conflict="run_id").execute()
        rows = self.upsert_manual_run(manual_run)
        return rows[0] if rows else manual_run

    def get_active_manual_run(self, *, run_type: str) -> dict[str, Any] | None:
        response = (
            self._client.table("manual_runs")
            .select("*")
            .eq("run_type", run_type)
            .order("requested_at", desc=True)
            .execute()
        )
        for row in list(response.data or []):
            if str(row.get("status") or "").lower() in {"queued", "running"}:
                return row
        return None

    def claim_queued_manual_run(self, *, worker_id: str) -> dict[str, Any] | None:
        response = (
            self._client.table("manual_runs")
            .select("*")
            .eq("status", "queued")
            .order("requested_at", desc=False)
            .limit(1)
            .execute()
        )
        queued = list(response.data or [])
        if not queued:
            return None
        manual_run = queued[0]
        run_id = str(manual_run.get("run_id") or "")
        claimed_at = _iso_now()
        updates = {
            "status": "running",
            "claimed_by": worker_id,
            "claimed_at": claimed_at,
            "updated_at": claimed_at,
        }
        claim_response = (
            self._client.table("manual_runs")
            .update(updates)
            .eq("id", manual_run.get("id"))
            .eq("status", "queued")
            .execute()
        )
        claimed_rows = list(claim_response.data or [])
        if not claimed_rows:
            return None
        (
            self._client.table("runs")
            .update(
                {
                    "status": "running",
                    "started_at": claimed_at,
                    "updated_at": claimed_at,
                }
            )
            .eq("run_id", run_id)
            .execute()
        )
        return claimed_rows[0]

    def mark_manual_run_status(
        self,
        run_id: str,
        *,
        status: str,
        error_summary: str = "",
    ) -> None:
        finished_at = _iso_now()
        updates = {
            "status": status,
            "error_summary": error_summary,
            "finished_at": finished_at,
            "updated_at": finished_at,
        }
        (
            self._client.table("manual_runs")
            .update(updates)
            .eq("run_id", run_id)
            .execute()
        )
        (
            self._client.table("runs")
            .update(
                {
                    "status": status,
                    "finished_at": finished_at,
                    "error_summary": error_summary,
                    "updated_at": finished_at,
                }
            )
            .eq("run_id", run_id)
            .execute()
        )

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


def _next_settings_version(versions: list[dict[str, Any]]) -> int:
    if not versions:
        return 1
    return max(int(version.get("version") or 0) for version in versions) + 1


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
