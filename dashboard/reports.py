from __future__ import annotations

from .supabase_client import ArtifactMetadata
from .view_models import format_bytes, run_view


def report_list_view(run: dict, outputs: list[dict]) -> dict:
    rendered_run = run_view(run)
    report = first_report_output(outputs)
    return {
        "run": rendered_run,
        "filename": str(report.get("filename") or report.get("object_path") or "") if report else "",
        "size": format_bytes(report.get("size_bytes")) if report else "--",
    }


def get_report_artifact(dashboard_client: object, run_id: str) -> ArtifactMetadata | None:
    get_report_artifact_method = getattr(dashboard_client, "get_report_artifact", None)
    if callable(get_report_artifact_method):
        metadata = get_report_artifact_method(run_id)
        if isinstance(metadata, ArtifactMetadata):
            return metadata
        if isinstance(metadata, dict):
            return artifact_metadata_from_output(metadata)
    outputs = dashboard_client.list_run_outputs(run_id)
    report = first_report_output(outputs)
    return artifact_metadata_from_output(report) if report else None


def first_report_output(outputs: list[dict]) -> dict | None:
    for output in outputs:
        artifact_type = str(output.get("artifact_type") or "").lower()
        content_type = str(output.get("content_type") or "").lower()
        filename = str(output.get("filename") or output.get("object_path") or "").lower()
        if artifact_type == "report" or content_type == "text/markdown" or filename.endswith(".md"):
            return output
    return None


def artifact_metadata_from_output(output: dict) -> ArtifactMetadata:
    object_path = str(output.get("object_path") or "")
    return ArtifactMetadata(
        run_id=str(output.get("run_id") or ""),
        artifact_type=str(output.get("artifact_type") or ""),
        bucket=str(output.get("bucket") or ""),
        object_path=object_path,
        filename=str(output.get("filename") or object_path.rsplit("/", 1)[-1]),
        content_type=str(output.get("content_type") or ""),
        size_bytes=output.get("size_bytes"),
        checksum=output.get("checksum"),
        created_at=output.get("created_at"),
    )
