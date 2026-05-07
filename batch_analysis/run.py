from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .candidates import load_candidates, select_candidates
from .cleanup import cleanup_evidence_artifacts
from .config import (
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
    write_structured_json_and_spreadsheet_summary,
    write_top5_creative_production_report,
)
from .planning_workbook import write_top5_angle_planning_workbook
from .run_manifest import build_run_manifest, write_batch_index_from_manifest, write_run_manifest
from .telegram import deliver_telegram_brief
from .tool_adapters import GeminiFlashAdapter


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
    has_spreadsheet_summary: bool,
    has_telegram_delivery: bool,
    has_evidence_artifact_cleanup: bool,
    has_refinement_hooks: bool,
) -> dict[str, Any]:
    batch_size = args.batch_size or MODE_DEFAULT_BATCH_SIZE[args.mode]
    return {
        "run_timestamp": isoformat_z(timestamp),
        "mode": args.mode,
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
            "spreadsheet_summary": "implemented"
            if has_spreadsheet_summary
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

def create_run(args: argparse.Namespace) -> Path:
    if args.batch_size is not None and args.batch_size < 1:
        raise ValueError("batch size must be at least 1")

    configuration = load_config(args.config)
    timestamp = parse_run_timestamp(args.timestamp)
    candidates = load_candidates(args.candidates)
    batch_size = args.batch_size or MODE_DEFAULT_BATCH_SIZE[args.mode]
    run_folder = args.runs_dir / run_folder_name(timestamp, args.mode)

    if run_folder.exists():
        raise FileExistsError(f"run folder already exists: {run_folder}")

    for subdirectory in RUN_SUBDIRECTORIES:
        (run_folder / subdirectory).mkdir(parents=True, exist_ok=False)

    selected_batch = None
    flat_evidence_index = None
    gemini_evidence_statuses: list[dict[str, Any]] = []
    if candidates is not None:
        selected_batch = select_candidates(
            candidates,
            configuration,
            timestamp,
            batch_size,
            args.candidates,
            preserve_order=args.mode == "daily",
        )

    if selected_batch is not None:
        evidence_store = EvidenceBundleStore(run_folder)
        evidence_store.write_source_snapshots(selected_batch["selected_candidates"])
        tool_stack_config = configuration.get("tool_stack", {})
        gemini_adapter = getattr(args, "gemini_adapter", None) or GeminiFlashAdapter(
            model=tool_stack_config.get("gemini_model", "gemini-2.5-flash"),
            api_key_env=tool_stack_config.get("gemini_api_key_env", "GEMINI_API_KEY"),
        )
        flat_index_entries = []
        for candidate in selected_batch["selected_candidates"]:
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
            flat_index_entries.append(evidence_store.load_snapshot(candidate))
        flat_evidence_index = {
            "created_at": selected_batch["selected_at"],
            "bundle_count": len(flat_index_entries),
            "bundles": flat_index_entries,
        }
        (run_folder / "data" / "evidence_bundle_index.json").write_text(
            json.dumps(flat_evidence_index, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    cross_video_summary = None
    if selected_batch is not None and flat_evidence_index is not None:
        cross_video_summary = write_cross_video_pattern_summary(
            run_folder,
            selected_batch,
            flat_evidence_index,
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
    )
    has_telegram_delivery = has_structured_outputs
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
        False,
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
    if has_structured_outputs:
        write_structured_json_and_spreadsheet_summary(
            run_folder,
            selected_batch,
            flat_evidence_index,
            metadata,
            cross_video_summary["summary"],
        )
        output_root = output_root_for_args(args)
        report_status = write_top5_creative_production_report(
            run_folder,
            output_root,
            selected_batch,
            flat_evidence_index,
            metadata["run_timestamp"],
        )
        workbook_status = write_top5_angle_planning_workbook(
            run_folder,
            output_root,
            selected_batch,
            flat_evidence_index,
            metadata["run_timestamp"],
        )
        final_outputs = [
            {
                "label": "Top 5 Creative Production Report",
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
        write_run_manifest(run_folder, manifest)
        write_refinement_hooks(run_folder, cross_video_summary["summary"])
    if has_telegram_delivery:
        deliver_telegram_brief(
            run_folder,
            metadata,
            cross_video_summary["summary"],
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
    return run_folder
