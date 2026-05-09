from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from .report_dates import report_date_from_timestamp

SPREADSHEET_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


@dataclass(frozen=True)
class CloudRunRecord:
    run_id: str
    status: str
    run_timestamp: str
    report_date: str
    mode: str
    requested_batch_size: int
    summary: dict[str, Any]
    publication_status: str
    publication_errors: list[str]
    local_run_folder: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "run_timestamp": self.run_timestamp,
            "report_date": self.report_date,
            "mode": self.mode,
            "requested_batch_size": self.requested_batch_size,
            "summary": self.summary,
            "publication_status": self.publication_status,
            "publication_errors": self.publication_errors,
            "local_run_folder": self.local_run_folder,
        }


@dataclass(frozen=True)
class PublicationResult:
    status: str
    errors: list[str]


@dataclass(frozen=True)
class CloudArtifactRecord:
    run_id: str
    artifact_type: str
    storage_path: str
    source_path: str
    filename: str
    content_type: str

    @property
    def artifact_id(self) -> str:
        return f"{self.run_id}:{self.artifact_type}:{self.storage_path}"

    def to_payload(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "run_id": self.run_id,
            "artifact_type": self.artifact_type,
            "storage_path": self.storage_path,
            "source_path": self.source_path,
            "filename": self.filename,
            "content_type": self.content_type,
        }


class SupabasePublicationAdapter:
    def __init__(
        self,
        client: Any,
        *,
        run_table: str = "daily_evidence_runs",
        artifact_table: str = "daily_evidence_artifacts",
    ) -> None:
        self.client = client
        self.run_table = run_table
        self.artifact_table = artifact_table

    def upsert_run(self, run: CloudRunRecord) -> PublicationResult:
        self._upsert(self.run_table, run.to_payload(), on_conflict="run_id")
        return PublicationResult(status="succeeded", errors=[])

    def publish_artifacts(
        self,
        artifacts: list[CloudArtifactRecord],
    ) -> PublicationResult:
        errors = []
        for artifact in artifacts:
            try:
                self._upsert(
                    self.artifact_table,
                    artifact.to_payload(),
                    on_conflict="artifact_id",
                )
            except Exception as exc:
                errors.append(f"{artifact.storage_path}: {exc}")
        return PublicationResult(
            status="failed" if errors else "succeeded",
            errors=errors,
        )

    def publish_run_with_artifacts(
        self,
        run: CloudRunRecord,
        artifacts: list[CloudArtifactRecord],
    ) -> PublicationResult:
        self.upsert_run(run)
        artifact_result = self.publish_artifacts(artifacts)
        if artifact_result.errors:
            failed_run = replace(
                run,
                publication_status="artifact_failed",
                publication_errors=artifact_result.errors,
            )
            self.upsert_run(failed_run)
            return PublicationResult(status="failed", errors=artifact_result.errors)

        published_run = replace(
            run,
            publication_status="published",
            publication_errors=[],
        )
        self.upsert_run(published_run)
        return PublicationResult(status="succeeded", errors=[])

    def _upsert(
        self,
        table_name: str,
        payload: dict[str, Any],
        *,
        on_conflict: str,
    ) -> None:
        self.client.table(table_name).upsert(
            payload,
            on_conflict=on_conflict,
        ).execute()


def build_cloud_run_record(
    run_folder: Path,
    metadata: dict[str, Any],
    manifest: dict[str, Any],
    summary: dict[str, Any] | None = None,
) -> CloudRunRecord:
    run_timestamp = str(
        metadata.get("run_timestamp") or manifest.get("run_timestamp") or ""
    )
    phase_statuses = [
        str(phase.get("status"))
        for phase in manifest.get("phases", [])
        if isinstance(phase, dict)
    ]
    if any(status == "failed" for status in phase_statuses):
        status = "failed"
    elif any(status == "partial" for status in phase_statuses):
        status = "partial"
    else:
        status = "completed"
    return CloudRunRecord(
        run_id=run_folder.name,
        status=status,
        run_timestamp=run_timestamp,
        report_date=report_date_from_timestamp(run_timestamp),
        mode=str(metadata.get("mode") or manifest.get("mode") or ""),
        requested_batch_size=int(
            metadata.get("requested_batch_size")
            or manifest.get("requested_batch_size")
            or 0
        ),
        summary=summary or {},
        publication_status="pending",
        publication_errors=[],
        local_run_folder=str(run_folder).replace("\\", "/"),
    )


def artifact_record_from_path(
    *,
    run_id: str,
    artifact_type: str,
    source_path: Path,
    storage_path: str | None = None,
) -> CloudArtifactRecord:
    return CloudArtifactRecord(
        run_id=run_id,
        artifact_type=artifact_type,
        storage_path=storage_path or f"{run_id}/{source_path.name}",
        source_path=str(source_path).replace("\\", "/"),
        filename=source_path.name,
        content_type=content_type_for_path(source_path),
    )


def content_type_for_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".md":
        return "text/markdown"
    if suffix == ".json":
        return "application/json"
    if suffix == ".xlsx":
        return SPREADSHEET_CONTENT_TYPE
    if suffix == ".csv":
        return "text/csv"
    return "application/octet-stream"
