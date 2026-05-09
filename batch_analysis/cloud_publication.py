from __future__ import annotations

from dataclasses import dataclass, replace
import json
import os
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from .report_dates import report_date_from_timestamp

SPREADSHEET_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
REQUIRED_CLOUD_ENV_VARS = ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")


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


class CloudPublicationConfigurationError(RuntimeError):
    pass


class CloudPublicationError(RuntimeError):
    def __init__(self, message: str, *, run_folder: Path | None = None) -> None:
        super().__init__(message)
        self.run_folder = run_folder


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


class SupabaseRestClient:
    def __init__(self, supabase_url: str, service_role_key: str) -> None:
        self.supabase_url = supabase_url.rstrip("/")
        self.service_role_key = service_role_key

    def table(self, table_name: str) -> "SupabaseRestTable":
        return SupabaseRestTable(self, table_name)


class SupabaseRestTable:
    def __init__(self, client: SupabaseRestClient, table_name: str) -> None:
        self.client = client
        self.table_name = table_name
        self.payload: dict[str, Any] | None = None
        self.on_conflict: str | None = None

    def upsert(self, payload: dict[str, Any], on_conflict: str | None = None) -> "SupabaseRestTable":
        self.payload = payload
        self.on_conflict = on_conflict
        return self

    def execute(self) -> dict[str, Any]:
        if self.payload is None:
            raise RuntimeError("Supabase upsert payload was not provided")
        query = ""
        if self.on_conflict:
            query = "?" + parse.urlencode({"on_conflict": self.on_conflict})
        url = f"{self.client.supabase_url}/rest/v1/{self.table_name}{query}"
        body = json.dumps(self.payload).encode("utf-8")
        req = request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "apikey": self.client.service_role_key,
                "Authorization": f"Bearer {self.client.service_role_key}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=minimal",
            },
        )
        try:
            with request.urlopen(req, timeout=30) as response:
                response.read()
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Supabase REST upsert failed with HTTP {exc.code}: {detail}"
            ) from exc
        except error.URLError as exc:
            raise RuntimeError(f"Supabase REST upsert failed: {exc.reason}") from exc
        return {"data": []}


def missing_cloud_environment(env: dict[str, str] | None = None) -> list[str]:
    values = env if env is not None else os.environ
    return [key for key in REQUIRED_CLOUD_ENV_VARS if not values.get(key)]


def supabase_publication_adapter_from_env(
    env: dict[str, str] | None = None,
) -> SupabasePublicationAdapter:
    values = env if env is not None else os.environ
    missing = missing_cloud_environment(values)
    if missing:
        raise CloudPublicationConfigurationError(
            "cloud publication is enabled but required environment variables are missing: "
            + ", ".join(missing)
        )
    return SupabasePublicationAdapter(
        SupabaseRestClient(
            str(values["SUPABASE_URL"]),
            str(values["SUPABASE_SERVICE_ROLE_KEY"]),
        )
    )


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


def build_cloud_artifact_records(
    *,
    run_folder: Path,
    manifest: dict[str, Any],
    output_root: Path,
    candidates_path: Path | None,
) -> list[CloudArtifactRecord]:
    run_id = run_folder.name
    artifacts: list[CloudArtifactRecord] = []
    seen: set[Path] = set()

    def add_artifact(artifact_type: str, source_path: Path) -> None:
        path = source_path.resolve()
        if path in seen or not path.is_file():
            return
        seen.add(path)
        try:
            relative_path = path.relative_to(run_folder.resolve())
            storage_path = f"daily-runs/{run_id}/run/{relative_path.as_posix()}"
        except ValueError:
            try:
                relative_path = path.relative_to(output_root.resolve())
                storage_path = f"daily-runs/{run_id}/outputs/{relative_path.as_posix()}"
            except ValueError:
                storage_path = f"daily-runs/{run_id}/inputs/{path.name}"
        artifacts.append(
            artifact_record_from_path(
                run_id=run_id,
                artifact_type=artifact_type,
                source_path=path,
                storage_path=storage_path,
            )
        )

    if candidates_path is not None:
        add_artifact("daily_selection", candidates_path)
        raw_scrape = candidates_path.parent / "raw_scrape_top30.json"
        add_artifact("raw_scrape", raw_scrape)
        backfill = candidates_path.parent / "daily_backfill_candidates.json"
        add_artifact("daily_backfill", backfill)

    for output in manifest.get("outputs", {}).get("final_outputs", []):
        if not isinstance(output, dict) or not output.get("path"):
            continue
        kind = str(output.get("kind") or "")
        artifact_type = "spreadsheet" if kind == "spreadsheet" else "markdown"
        add_artifact(artifact_type, output_root / str(output["path"]))

    for relative_path in (
        "run_manifest.json",
        "batch_index.md",
        "data/selected_batch.json",
        "reports/selected_batch.md",
        "data/evidence_bundle_index.json",
        "data/cross_video_pattern_summary.json",
        "data/structured_batch_analysis.json",
        "data/refinement_hooks.json",
        "logs/telegram_delivery.json",
        "logs/evidence_artifact_cleanup.json",
    ):
        path = run_folder / relative_path
        if relative_path == "data/structured_batch_analysis.json":
            artifact_type = "json"
        else:
            artifact_type = "batch_analysis"
        add_artifact(artifact_type, path)

    return artifacts


def write_cloud_publication_log(
    run_folder: Path,
    *,
    status: str,
    artifact_count: int,
    errors: list[str] | None = None,
) -> None:
    log_path = run_folder / "logs" / "cloud_publication.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        json.dumps(
            {
                "status": status,
                "artifact_count": artifact_count,
                "errors": errors or [],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def publish_completed_run_outputs(
    *,
    run_folder: Path,
    metadata: dict[str, Any],
    manifest: dict[str, Any],
    summary: dict[str, Any],
    output_root: Path,
    candidates_path: Path | None,
    adapter: Any,
) -> PublicationResult:
    run = build_cloud_run_record(run_folder, metadata, manifest, summary)
    artifacts = build_cloud_artifact_records(
        run_folder=run_folder,
        manifest=manifest,
        output_root=output_root,
        candidates_path=candidates_path,
    )
    result = adapter.publish_run_with_artifacts(run, artifacts)
    write_cloud_publication_log(
        run_folder,
        status="published" if result.status == "succeeded" else "failed",
        artifact_count=len(artifacts),
        errors=result.errors,
    )
    if result.errors:
        raise CloudPublicationError(
            "cloud publication failed after local output generation: "
            + "; ".join(result.errors),
            run_folder=run_folder,
        )
    return result
