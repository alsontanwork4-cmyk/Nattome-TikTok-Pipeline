from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .candidates import load_candidates, select_candidates
from .cleanup import cleanup_evidence_artifacts
from .cloud_publication import (
    CloudPublicationConfigurationError,
    CloudPublicationError,
    publish_completed_run_outputs,
    supabase_publication_adapter_from_env,
    write_cloud_publication_log,
)
from .config import (
    DAILY_BACKFILL_LIMIT,
    DAILY_RUN_MODE,
    DAILY_SELECTION_SIZE,
    MODE_DEFAULT_BATCH_SIZE,
    RUN_SUBDIRECTORIES,
    isoformat_z,
    load_config,
    parse_run_timestamp,
    run_folder_name,
)
from .evidence import write_snapshot_evidence_outputs
from .evidence_io import EvidenceBundleStore
from .outputs import (
    write_cross_video_pattern_summary,
    write_selected_batch,
    write_structured_json_output,
    write_top5_creative_production_report,
)
from .planning_workbook import write_top5_angle_planning_workbook
from .run_manifest import build_run_manifest, write_batch_index_from_manifest, write_run_manifest
from .telegram import deliver_telegram_brief
from .tool_adapters import GeminiFlashAdapter


def runtime_mode(args: argparse.Namespace) -> str:
    return str(getattr(args, "mode", None) or DAILY_RUN_MODE)


def requested_batch_size(args: argparse.Namespace) -> int:
    explicit_batch_size = getattr(args, "batch_size", None)
    if explicit_batch_size is not None:
        return int(explicit_batch_size)
    return int(MODE_DEFAULT_BATCH_SIZE.get(runtime_mode(args), DAILY_SELECTION_SIZE))


def output_root_for_args(args: argparse.Namespace) -> Path:
    explicit_output_root = getattr(args, "outputs_dir", None)
    if explicit_output_root is not None:
        return explicit_output_root
    return args.runs_dir.parent / "outputs"


def write_refinement_hooks(run_folder: Path, cross_video_summary: dict[str, Any]) -> dict[str, Any]:
    angles = cross_video_summary.get("top_priority_shootable_angles")
    top_angles = angles if isinstance(angles, list) else []
    hooks = {
        "deep_sound_research": {
            "status": "extension_point",
            "source": "baseline_audio_analysis",
            "trigger": "Run deeper sound research when reused sound or music appears to drive virality.",
            "candidate_ids": [
                str(angle.get("candidate_id"))
                for angle in top_angles
                if isinstance(angle, dict) and angle.get("candidate_id")
            ],
        },
        "multilingual_quality_improvements": {
            "status": "extension_point",
            "source": "gemini_evidence",
            "trigger": "Improve Gemini evidence capture where language detection, confidence, or mixed-language capture is weak.",
        },
        "full_script_generation": {
            "status": "extension_point",
            "source": "top_priority_shootable_angles",
            "trigger": "Generate full scripts only for selected winning Shootable Angles after human approval.",
            "candidate_ids": [
                str(angle.get("candidate_id"))
                for angle in top_angles[:5]
                if isinstance(angle, dict) and angle.get("candidate_id")
            ],
        },
    }
    hooks_path = run_folder / "data" / "refinement_hooks.json"
    hooks_path.parent.mkdir(parents=True, exist_ok=True)
    hooks_path.write_text(
        json.dumps(hooks, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"status": "completed", "path": str(hooks_path.relative_to(run_folder))}

def build_metadata(
    args: argparse.Namespace,
    timestamp: datetime,
    configuration: dict[str, Any],
    has_candidate_selection: bool,
    has_evidence_bundles: bool,
    has_gemini_evidence: bool,
    has_audio_music_trend_analysis: bool,
    has_claim_safety_review: bool,
    has_evidence_quality: bool,
    has_video_evidence_reports: bool,
    has_cross_video_pattern_summary: bool,
    has_structured_json_output: bool,
    has_telegram_delivery: bool,
    has_evidence_artifact_cleanup: bool,
    has_refinement_hooks: bool,
) -> dict[str, Any]:
    batch_size = requested_batch_size(args)
    mode = runtime_mode(args)
    return {
        "run_timestamp": isoformat_z(timestamp),
        "mode": mode,
        "requested_batch_size": batch_size,
        "configuration": configuration,
        "implementation_status": {
            "candidate_selection": "implemented" if has_candidate_selection else "not_implemented",
            "video_download": "implemented" if has_evidence_bundles else "not_implemented",
            "gemini_evidence": "implemented" if has_gemini_evidence else "not_implemented",
            "audio_music_trend_analysis": "implemented"
            if has_audio_music_trend_analysis
            else "not_implemented",
            "claim_safety_review": "implemented"
            if has_claim_safety_review
            else "not_implemented",
            "evidence_quality": "implemented" if has_evidence_quality else "not_implemented",
            "video_evidence_reports": "implemented"
            if has_video_evidence_reports
            else "not_implemented",
            "cross_video_pattern_summary": "implemented"
            if has_cross_video_pattern_summary
            else "not_implemented",
            "structured_json_output": "implemented"
            if has_structured_json_output
            else "not_implemented",
            "telegram_delivery": "implemented" if has_telegram_delivery else "not_implemented",
            "evidence_artifact_cleanup": "implemented"
            if has_evidence_artifact_cleanup
            else "not_implemented",
            "refinement_hooks": "implemented" if has_refinement_hooks else "not_implemented",
        },
        "notes": [
            "This run records missing setup or missing evidence instead of fabricating analysis.",
            "Cross-video summaries compare only captured evidence and selected candidate metadata.",
        ],
    }


def selected_batch_from_candidates(
    candidates: list[dict[str, Any]] | None,
    configuration: dict[str, Any],
    timestamp: datetime,
    batch_size: int,
    candidates_path: Path | None,
    *,
    preserve_order: bool,
) -> dict[str, Any] | None:
    if candidates is None:
        return None
    return select_candidates(
        candidates,
        configuration,
        timestamp,
        batch_size,
        candidates_path,
        preserve_order=preserve_order,
    )


def has_production_qualifying_angle(run_folder: Path, snapshot: dict[str, Any]) -> bool:
    artifact = snapshot.get("artifacts", {}).get("shootable_angles")
    if not isinstance(artifact, dict) or not artifact.get("path"):
        return False
    try:
        payload = json.loads((run_folder / str(artifact["path"])).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    angles = payload.get("angles") if isinstance(payload, dict) else []
    return isinstance(angles, list) and any(isinstance(angle, dict) for angle in angles)


def production_selected_batch(
    selected_batch: dict[str, Any],
    production_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    batch = dict(selected_batch)
    batch["selected_candidates"] = []
    for production_rank, candidate in enumerate(production_candidates, start=1):
        production_candidate = dict(candidate)
        production_candidate["production_rank"] = production_rank
        batch["selected_candidates"].append(production_candidate)
    batch["selected_candidate_count"] = len(production_candidates)
    batch["requested_batch_size"] = DAILY_SELECTION_SIZE
    return batch


def evidence_index_for_candidates(
    evidence_index: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    candidate_ids = {str(candidate.get("id") or "") for candidate in candidates}
    bundles = [
        bundle
        for bundle in evidence_index.get("bundles", [])
        if isinstance(bundle, dict) and str(bundle.get("candidate_id") or "") in candidate_ids
    ]
    return {
        "created_at": evidence_index.get("created_at"),
        "bundle_count": len(bundles),
        "bundles": bundles,
    }


def candidate_preview_payload(selected_batch: dict[str, Any] | None) -> dict[str, Any]:
    if selected_batch is None:
        return {"top": []}
    return {
        "generated_at": selected_batch.get("selected_at"),
        "selection_strategy": selected_batch.get("selection_strategy"),
        "selection_count": selected_batch.get("selected_candidate_count", 0),
        "top": selected_batch.get("selected_candidates", []),
        "excluded_candidates": selected_batch.get("excluded_candidates", []),
    }


def create_run(args: argparse.Namespace) -> Path:
    batch_size = requested_batch_size(args)
    mode = runtime_mode(args)
    if batch_size < 1:
        raise ValueError("batch size must be at least 1")

    configuration = load_config(getattr(args, "config", None))
    timestamp = parse_run_timestamp(getattr(args, "timestamp", None))
    candidates = load_candidates(getattr(args, "candidates", None))
    backfill_candidates = load_candidates(getattr(args, "backfill_candidates", None))
    run_folder = args.runs_dir / run_folder_name(timestamp, mode)

    if run_folder.exists():
        raise FileExistsError(f"run folder already exists: {run_folder}")

    for subdirectory in RUN_SUBDIRECTORIES:
        (run_folder / subdirectory).mkdir(parents=True, exist_ok=False)

    selected_batch = None
    backfill_batch = None
    flat_evidence_index = None
    gemini_evidence_statuses: list[dict[str, Any]] = []
    if candidates is not None:
        selected_batch = selected_batch_from_candidates(
            candidates,
            configuration,
            timestamp,
            batch_size,
            getattr(args, "candidates", None),
            preserve_order=mode == DAILY_RUN_MODE,
        )
    if backfill_candidates is not None:
        backfill_batch = selected_batch_from_candidates(
            backfill_candidates,
            configuration,
            timestamp,
            DAILY_BACKFILL_LIMIT,
            getattr(args, "backfill_candidates", None),
            preserve_order=True,
        )

    analyzed_candidates: list[dict[str, Any]] = []
    production_qualified_candidates: list[dict[str, Any]] = []
    run_level_gemini_failure = False
    if selected_batch is not None:
        evidence_store = EvidenceBundleStore(run_folder)
        tool_stack_config = configuration.get("tool_stack", {})
        gemini_adapter = getattr(args, "gemini_adapter", None) or GeminiFlashAdapter(
            model=tool_stack_config.get("gemini_model", "gemini-2.5-flash"),
            api_key_env=tool_stack_config.get("gemini_api_key_env", "GEMINI_API_KEY"),
        )
        flat_index_entries = []

        def analyze_candidate(candidate: dict[str, Any]) -> bool:
            nonlocal run_level_gemini_failure
            evidence_store.write_source_snapshot(candidate)
            snapshot = evidence_store.load_snapshot(candidate)
            source_video = snapshot.get("source_video")
            if isinstance(source_video, dict) and source_video.get("state") == "available":
                evidence = gemini_adapter.analyze_source_video(
                    run_folder / str(source_video["path"]),
                    candidate,
                )
                snapshot = evidence_store.write_gemini_evidence(candidate, evidence)
                gemini_evidence_statuses.append(
                    {
                        "candidate_id": snapshot.get("candidate_id"),
                        "status": evidence.get("status"),
                        "reason": evidence.get("reason"),
                    }
                )
                if evidence.get("status") == "missing_credentials":
                    run_level_gemini_failure = True
            else:
                reason = (
                    source_video.get("reason")
                    if isinstance(source_video, dict)
                    else "source video artifact is unavailable"
                )
                snapshot.setdefault("artifacts", {})
                snapshot["artifacts"]["gemini_evidence"] = {
                    "state": "missing",
                    "path": None,
                    "reason": reason,
                    "missing_evidence": [
                        "visual_observations",
                        "visible_text",
                        "spoken_content",
                        "audio_cues",
                        "hook_evidence",
                        "claim_evidence",
                    ],
                }
                snapshot_path = snapshot.get("snapshot_path")
                if snapshot_path:
                    (run_folder / str(snapshot_path)).write_text(
                        json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )
                gemini_evidence_statuses.append(
                    {
                        "candidate_id": snapshot.get("candidate_id"),
                        "status": "missing",
                        "reason": reason,
                    }
                )
            write_snapshot_evidence_outputs(run_folder, candidate, snapshot)
            final_snapshot = evidence_store.load_snapshot(candidate)
            flat_index_entries.append(final_snapshot)
            analyzed_candidates.append(candidate)
            if has_production_qualifying_angle(run_folder, final_snapshot):
                production_qualified_candidates.append(candidate)
                return True
            return False

        for candidate in selected_batch["selected_candidates"]:
            analyze_candidate(candidate)
            if run_level_gemini_failure:
                break

        if (
            not run_level_gemini_failure
            and len(production_qualified_candidates) < DAILY_SELECTION_SIZE
            and backfill_batch is not None
        ):
            for candidate in backfill_batch["selected_candidates"][:DAILY_BACKFILL_LIMIT]:
                analyze_candidate(candidate)
                if len(production_qualified_candidates) >= DAILY_SELECTION_SIZE:
                    break

        flat_evidence_index = {
            "created_at": selected_batch["selected_at"],
            "bundle_count": len(flat_index_entries),
            "bundles": flat_index_entries,
        }
        (run_folder / "data" / "evidence_bundle_index.json").write_text(
            json.dumps(flat_evidence_index, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    production_batch = (
        production_selected_batch(selected_batch, production_qualified_candidates)
        if selected_batch is not None
        else None
    )
    production_evidence_index = (
        evidence_index_for_candidates(flat_evidence_index, production_qualified_candidates)
        if flat_evidence_index is not None
        else None
    )

    cross_video_summary = None
    if (
        production_batch is not None
        and production_evidence_index is not None
        and not run_level_gemini_failure
    ):
        cross_video_summary = write_cross_video_pattern_summary(
            run_folder,
            production_batch,
            production_evidence_index,
        )

    has_gemini_evidence = flat_evidence_index is not None
    has_audio_music_trend_analysis = flat_evidence_index is not None
    has_claim_safety_review = flat_evidence_index is not None
    has_evidence_quality = flat_evidence_index is not None
    has_video_evidence_reports = flat_evidence_index is not None
    has_structured_outputs = (
        selected_batch is not None
        and flat_evidence_index is not None
        and cross_video_summary is not None
        and not run_level_gemini_failure
    )
    has_production_outputs = (
        has_structured_outputs
        and production_batch is not None
        and production_evidence_index is not None
        and len(production_qualified_candidates) > 0
    )
    has_telegram_delivery = selected_batch is not None
    has_evidence_artifact_cleanup = flat_evidence_index is not None
    has_refinement_hooks = has_structured_outputs
    metadata = build_metadata(
        args,
        timestamp,
        configuration,
        selected_batch is not None,
        flat_evidence_index is not None,
        has_gemini_evidence,
        has_audio_music_trend_analysis,
        has_claim_safety_review,
        has_evidence_quality,
        has_video_evidence_reports,
        cross_video_summary is not None,
        has_structured_outputs,
        has_telegram_delivery,
        has_evidence_artifact_cleanup,
        has_refinement_hooks,
    )
    (run_folder / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    manifest = build_run_manifest(
        args,
        timestamp,
        configuration,
        has_candidate_selection=selected_batch is not None,
        has_evidence_bundles=flat_evidence_index is not None,
        has_cross_video_pattern_summary=cross_video_summary is not None,
        has_structured_outputs=has_structured_outputs,
        has_telegram_delivery=has_telegram_delivery,
        has_evidence_artifact_cleanup=has_evidence_artifact_cleanup,
        has_refinement_hooks=has_refinement_hooks,
        gemini_evidence_statuses=gemini_evidence_statuses,
    )
    final_outputs: list[dict[str, Any]] = []
    manifest["outputs"]["final_outputs"] = []
    manifest["outputs"]["production_status"] = (
        "skipped" if selected_batch is not None else "not_requested"
    )
    manifest["outputs"]["production_qualified_count"] = len(production_qualified_candidates)
    if has_structured_outputs:
        write_structured_json_output(
            run_folder,
            production_batch,
            flat_evidence_index,
            metadata,
            cross_video_summary["summary"],
            original_daily_selection=candidate_preview_payload(selected_batch),
            daily_backfill_candidates=candidate_preview_payload(backfill_batch),
            analyzed_candidates=analyzed_candidates,
            production_qualified_candidates=production_qualified_candidates,
        )
    if has_production_outputs:
        output_root = output_root_for_args(args)
        report_status = write_top5_creative_production_report(
            run_folder,
            output_root,
            production_batch,
            production_evidence_index,
            metadata["run_timestamp"],
            run_folder.name,
        )
        workbook_status = write_top5_angle_planning_workbook(
            run_folder,
            output_root,
            production_batch,
            production_evidence_index,
            metadata["run_timestamp"],
            run_folder.name,
        )
        final_outputs = [
            {
                "label": "Daily Top-3 Creative Production Report",
                "kind": "markdown",
                "path": report_status["path"],
            },
            {
                "label": "Excel Planning Workbook",
                "kind": "spreadsheet",
                "path": workbook_status["path"],
            },
        ]
        manifest["outputs"]["output_root"] = str(output_root)
        manifest["outputs"]["final_outputs"] = final_outputs
        manifest["outputs"]["production_status"] = "completed"
        write_run_manifest(run_folder, manifest)
        write_refinement_hooks(run_folder, cross_video_summary["summary"])
    if has_telegram_delivery:
        deliver_telegram_brief(
            run_folder,
            metadata,
            cross_video_summary["summary"] if cross_video_summary else {"source_video_count": 0},
            configuration.get("telegram", {}),
            final_outputs,
        )
    if has_evidence_artifact_cleanup:
        cleanup_evidence_artifacts(
            run_folder,
            flat_evidence_index,
            configuration.get("cleanup", {}),
        )
    if selected_batch is not None:
        write_selected_batch(run_folder, selected_batch)
    write_batch_index_from_manifest(run_folder, manifest)
    if getattr(args, "cloud_publication_enabled", False):
        cloud_adapter = getattr(args, "cloud_publication_adapter", None)
        if cloud_adapter is None:
            try:
                cloud_adapter = supabase_publication_adapter_from_env()
            except CloudPublicationConfigurationError as exc:
                write_cloud_publication_log(
                    run_folder,
                    status="failed",
                    artifact_count=0,
                    errors=[str(exc)],
                )
                raise CloudPublicationError(str(exc), run_folder=run_folder) from exc
        publish_completed_run_outputs(
            run_folder=run_folder,
            metadata=metadata,
            manifest=manifest,
            summary=cross_video_summary["summary"] if cross_video_summary else {},
            output_root=output_root_for_args(args),
            candidates_path=getattr(args, "candidates", None),
            adapter=cloud_adapter,
        )
    return run_folder
