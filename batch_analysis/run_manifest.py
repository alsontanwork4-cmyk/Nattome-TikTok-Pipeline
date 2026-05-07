from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import RUN_SUBDIRECTORIES, isoformat_z


def phase_record(
    name: str,
    status: str,
    *,
    inputs: dict[str, Any] | None = None,
    outputs: dict[str, Any] | None = None,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "name": name,
        "status": status,
        "inputs": inputs or {},
        "outputs": outputs or {},
    }
    if notes:
        record["notes"] = notes
    return record


def build_run_manifest(
    args: Any,
    timestamp: Any,
    configuration: dict[str, Any],
    *,
    has_candidate_selection: bool,
    has_evidence_bundles: bool,
    has_cross_video_pattern_summary: bool,
    has_structured_outputs: bool,
    has_telegram_delivery: bool,
    has_evidence_artifact_cleanup: bool,
    has_refinement_hooks: bool,
    gemini_evidence_statuses: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    batch_size = args.batch_size
    if batch_size is None:
        from .config import MODE_DEFAULT_BATCH_SIZE

        batch_size = MODE_DEFAULT_BATCH_SIZE[args.mode]

    candidates_path = str(args.candidates) if args.candidates else None
    gemini_statuses = gemini_evidence_statuses or []
    failed_gemini_statuses = [
        status
        for status in gemini_statuses
        if status.get("status") in {"failed", "missing_credentials"}
    ]
    partial_gemini_statuses = [
        status for status in gemini_statuses if status.get("status") == "partial"
    ]
    if failed_gemini_statuses:
        gemini_phase_status = "failed"
    elif partial_gemini_statuses:
        gemini_phase_status = "partial"
    elif gemini_statuses:
        gemini_phase_status = "completed"
    else:
        gemini_phase_status = "skipped"
    gemini_notes = [
        f"{status.get('candidate_id')}: {status.get('reason')}"
        for status in failed_gemini_statuses
        if status.get("reason")
    ]

    phases = [
        phase_record(
            "run_folder",
            "completed",
            outputs={"folders": list(RUN_SUBDIRECTORIES)},
        ),
        phase_record(
            "candidate_selection",
            "completed" if has_candidate_selection else "skipped",
            inputs={"candidates_path": candidates_path, "requested_batch_size": batch_size},
            outputs={
                "json": "batch_outputs/json/selected_batch.json",
                "markdown": "batch_outputs/markdown/selected_batch.md",
            }
            if has_candidate_selection
            else {},
            notes=[] if has_candidate_selection else ["No candidate metadata file was provided."],
        ),
        phase_record(
            "evidence_bundles",
            "completed" if has_evidence_bundles else "skipped",
            outputs={"index": "evidence_bundles/index.json"} if has_evidence_bundles else {},
            notes=[] if has_evidence_bundles else ["Evidence bundles require a selected batch."],
        ),
        phase_record(
            "gemini_evidence",
            gemini_phase_status,
            inputs={
                "primary_adapter": configuration.get("tool_stack", {}).get("primary_adapter"),
                "model": configuration.get("tool_stack", {}).get("gemini_model"),
            },
            outputs={"evidence": "data/*_gemini_evidence.json"} if gemini_statuses else {},
            notes=gemini_notes
            if gemini_notes
            else ([] if gemini_statuses else ["Gemini evidence extraction has not run yet."]),
        ),
        phase_record(
            "cross_video_pattern_summary",
            "completed" if has_cross_video_pattern_summary else "skipped",
            outputs={
                "markdown": "batch_outputs/markdown/cross_video_pattern_summary.md",
                "json": "batch_outputs/json/cross_video_pattern_summary.json",
            }
            if has_cross_video_pattern_summary
            else {},
        ),
        phase_record(
            "structured_outputs",
            "completed" if has_structured_outputs else "skipped",
            outputs={
                "json": "batch_outputs/json/structured_batch_analysis.json",
                "spreadsheet": "batch_outputs/spreadsheets/spreadsheet_summary.csv",
            }
            if has_structured_outputs
            else {},
        ),
        phase_record(
            "telegram_delivery",
            "completed" if has_telegram_delivery else "skipped",
            outputs={"log": "logs/telegram_delivery.json"} if has_telegram_delivery else {},
        ),
        phase_record(
            "evidence_artifact_cleanup",
            "completed" if has_evidence_artifact_cleanup else "skipped",
            outputs={"log": "logs/evidence_artifact_cleanup.json"}
            if has_evidence_artifact_cleanup
            else {},
        ),
        phase_record(
            "refinement_hooks",
            "completed" if has_refinement_hooks else "skipped",
            outputs={"json": "batch_outputs/json/refinement_hooks.json"}
            if has_refinement_hooks
            else {},
        ),
    ]

    return {
        "run_timestamp": isoformat_z(timestamp),
        "mode": args.mode,
        "requested_batch_size": batch_size,
        "configuration": configuration,
        "folders": list(RUN_SUBDIRECTORIES),
        "phases": phases,
        "outputs": {},
    }


def write_run_manifest(run_folder: Path, manifest: dict[str, Any]) -> None:
    (run_folder / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def render_batch_index(manifest: dict[str, Any]) -> str:
    phase_by_name = {
        phase["name"]: phase
        for phase in manifest.get("phases", [])
        if isinstance(phase, dict) and "name" in phase
    }
    candidate_selection = phase_by_name.get("candidate_selection", {})
    evidence_bundles = phase_by_name.get("evidence_bundles", {})
    cross_video_summary = phase_by_name.get("cross_video_pattern_summary", {})
    structured_outputs = phase_by_name.get("structured_outputs", {})
    telegram_delivery = phase_by_name.get("telegram_delivery", {})
    cleanup = phase_by_name.get("evidence_artifact_cleanup", {})
    refinement_hooks = phase_by_name.get("refinement_hooks", {})

    lines = [
        "# Batch Analysis Run",
        "",
        f"- Run timestamp: {manifest['run_timestamp']}",
        f"- Mode: {manifest['mode']}",
        f"- Requested batch size: {manifest['requested_batch_size']}",
        f"- Status: {'selected_batch_preview_created' if candidate_selection.get('status') == 'completed' else 'skeleton_created'}",
        f"- Manifest: `run_manifest.json`",
        "",
        "## Output Folders",
        "",
    ]
    for subdirectory in manifest.get("folders", []):
        lines.append(f"- `{subdirectory}`")

    lines.extend(["", "## Selection", ""])
    selection_outputs = candidate_selection.get("outputs", {})
    if candidate_selection.get("status") == "completed":
        lines.extend(
            [
                f"- JSON: `{selection_outputs['json']}`",
                f"- Markdown: `{selection_outputs['markdown']}`",
            ]
        )
    else:
        lines.append("- Candidate selection was not run because no candidate metadata file was provided.")

    lines.extend(["", "## Evidence Bundles", ""])
    evidence_outputs = evidence_bundles.get("outputs", {})
    if evidence_bundles.get("status") == "completed":
        lines.append(f"- Index: `{evidence_outputs['index']}`")
    else:
        lines.append("- Evidence bundles were not created because no selected batch was available.")

    lines.extend(["", "## Cross-Video Pattern Summary", ""])
    summary_outputs = cross_video_summary.get("outputs", {})
    if cross_video_summary.get("status") == "completed":
        lines.extend(
            [
                f"- Markdown: `{summary_outputs['markdown']}`",
                f"- JSON: `{summary_outputs['json']}`",
            ]
        )
    else:
        lines.append("- Cross-video pattern summary was not created because no evidence bundles were available.")

    lines.extend(["", "## Structured Outputs", ""])
    structured = structured_outputs.get("outputs", {})
    if structured_outputs.get("status") == "completed":
        lines.append(f"- Structured JSON: `{structured['json']}`")
        lines.append(f"- Spreadsheet summary: `{structured['spreadsheet']}`")
    else:
        lines.append("- Structured JSON was not created because no evidence bundles were available.")
        lines.append("- Spreadsheet summary was not created because no evidence bundles were available.")

    lines.extend(["", "## Telegram Delivery", ""])
    telegram_outputs = telegram_delivery.get("outputs", {})
    if telegram_delivery.get("status") == "completed":
        lines.append(f"- Delivery log: `{telegram_outputs['log']}`")
    else:
        lines.append("- Telegram delivery was not attempted because required batch outputs were unavailable.")

    lines.extend(["", "## Cleanup And Refinement", ""])
    cleanup_outputs = cleanup.get("outputs", {})
    if cleanup.get("status") == "completed":
        lines.append(f"- Cleanup log: `{cleanup_outputs['log']}`")
    else:
        lines.append("- Evidence artifact cleanup was not evaluated because no evidence bundles were available.")
    hook_outputs = refinement_hooks.get("outputs", {})
    if refinement_hooks.get("status") == "completed":
        lines.append(f"- Refinement hooks: `{hook_outputs['json']}`")
    else:
        lines.append("- Refinement hooks were not created because no cross-video summary was available.")

    lines.extend(
        [
            "",
            "## Not Implemented Yet",
            "",
            "Source video artifacts are only present when candidate metadata includes a downloadable video source.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_batch_index_from_manifest(run_folder: Path, manifest: dict[str, Any]) -> None:
    manifest["outputs"]["batch_index"] = "batch_index.md"
    (run_folder / "batch_index.md").write_text(
        render_batch_index(manifest),
        encoding="utf-8",
    )
    write_run_manifest(run_folder, manifest)
