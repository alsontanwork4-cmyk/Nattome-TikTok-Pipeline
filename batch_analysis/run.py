from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .candidates import load_candidates, select_candidates
from .cleanup import cleanup_evidence_artifacts
from .config import (
    LEGACY_OUTPUT_SUBDIRECTORIES,
    MODE_DEFAULT_BATCH_SIZE,
    RUN_SUBDIRECTORIES,
    isoformat_z,
    load_config,
    parse_run_timestamp,
    run_folder_name,
)
from .evidence import write_evidence_bundles
from .outputs import (
    write_cross_video_pattern_summary,
    write_selected_batch,
    write_structured_json_and_spreadsheet_summary,
)
from .run_manifest import build_run_manifest, write_batch_index_from_manifest
from .telegram import deliver_telegram_brief

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
            "source": "ocr_evidence and transcript_evidence",
            "trigger": "Improve OCR/transcription where language detection, confidence, or mixed-language capture is weak.",
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
    hooks_path = run_folder / "batch_outputs" / "json" / "refinement_hooks.json"
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
    has_hybrid_timeline: bool,
    has_ocr: bool,
    has_transcription: bool,
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
            "hybrid_timeline": "implemented" if has_hybrid_timeline else "not_implemented",
            "ocr": "implemented" if has_ocr else "not_implemented",
            "transcription": "implemented" if has_transcription else "not_implemented",
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

def write_batch_index(
    run_folder: Path,
    metadata: dict[str, Any],
    has_candidate_selection: bool,
    has_evidence_bundles: bool,
    has_cross_video_pattern_summary: bool,
    has_structured_json_output: bool,
    has_spreadsheet_summary: bool,
    has_telegram_delivery: bool,
    has_evidence_artifact_cleanup: bool,
    has_refinement_hooks: bool,
) -> None:
    lines = [
        "# Batch Analysis Run",
        "",
        f"- Run timestamp: {metadata['run_timestamp']}",
        f"- Mode: {metadata['mode']}",
        f"- Requested batch size: {metadata['requested_batch_size']}",
        f"- Status: {'selected_batch_preview_created' if has_candidate_selection else 'skeleton_created'}",
        "",
        "## Output Folders",
        "",
    ]
    for subdirectory in RUN_SUBDIRECTORIES:
        lines.append(f"- `{subdirectory}`")
    lines.extend(
        [
            "",
            "## Selection",
            "",
        ]
    )
    if has_candidate_selection:
        lines.extend(
            [
                "- JSON: `batch_outputs/json/selected_batch.json`",
                "- Markdown: `batch_outputs/markdown/selected_batch.md`",
            ]
        )
    else:
        lines.append("- Candidate selection was not run because no candidate metadata file was provided.")
    lines.extend(["", "## Evidence Bundles", ""])
    if has_evidence_bundles:
        lines.append("- Index: `evidence_bundles/index.json`")
    else:
        lines.append("- Evidence bundles were not created because no selected batch was available.")
    lines.extend(["", "## Cross-Video Pattern Summary", ""])
    if has_cross_video_pattern_summary:
        lines.extend(
            [
                "- Markdown: `batch_outputs/markdown/cross_video_pattern_summary.md`",
                "- JSON: `batch_outputs/json/cross_video_pattern_summary.json`",
            ]
        )
    else:
        lines.append("- Cross-video pattern summary was not created because no evidence bundles were available.")
    lines.extend(["", "## Structured Outputs", ""])
    if has_structured_json_output:
        lines.append("- Structured JSON: `batch_outputs/json/structured_batch_analysis.json`")
    else:
        lines.append("- Structured JSON was not created because no evidence bundles were available.")
    if has_spreadsheet_summary:
        lines.append("- Spreadsheet summary: `batch_outputs/spreadsheets/spreadsheet_summary.csv`")
    else:
        lines.append("- Spreadsheet summary was not created because no evidence bundles were available.")
    lines.extend(["", "## Telegram Delivery", ""])
    if has_telegram_delivery:
        lines.append("- Delivery log: `logs/telegram_delivery.json`")
    else:
        lines.append("- Telegram delivery was not attempted because required batch outputs were unavailable.")
    lines.extend(["", "## Cleanup And Refinement", ""])
    if has_evidence_artifact_cleanup:
        lines.append("- Cleanup log: `logs/evidence_artifact_cleanup.json`")
    else:
        lines.append("- Evidence artifact cleanup was not evaluated because no evidence bundles were available.")
    if has_refinement_hooks:
        lines.append("- Refinement hooks: `batch_outputs/json/refinement_hooks.json`")
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
    (run_folder / "batch_index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

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
    if candidates is not None:
        for subdirectory in LEGACY_OUTPUT_SUBDIRECTORIES:
            (run_folder / subdirectory).mkdir(parents=True, exist_ok=True)
        selected_batch = select_candidates(
            candidates,
            configuration,
            timestamp,
            batch_size,
            args.candidates,
        )

    evidence_index = None
    if selected_batch is not None:
        evidence_index = write_evidence_bundles(
            run_folder,
            selected_batch,
            args.ffmpeg_bin,
            args.ocr_primary_bin,
            args.ocr_fallback_bin,
            args.transcription_bin,
        )

    cross_video_summary = None
    if selected_batch is not None and evidence_index is not None:
        cross_video_summary = write_cross_video_pattern_summary(
            run_folder,
            selected_batch,
            evidence_index,
        )

    has_hybrid_timeline = evidence_index is not None
    has_ocr = evidence_index is not None
    has_transcription = evidence_index is not None
    has_audio_music_trend_analysis = evidence_index is not None
    has_claim_safety_review = evidence_index is not None
    has_evidence_quality = evidence_index is not None
    has_video_evidence_reports = evidence_index is not None
    has_structured_outputs = (
        selected_batch is not None
        and evidence_index is not None
        and cross_video_summary is not None
    )
    has_telegram_delivery = has_structured_outputs
    has_evidence_artifact_cleanup = evidence_index is not None
    has_refinement_hooks = has_structured_outputs
    metadata = build_metadata(
        args,
        timestamp,
        configuration,
        selected_batch is not None,
        evidence_index is not None,
        has_hybrid_timeline,
        has_ocr,
        has_transcription,
        has_audio_music_trend_analysis,
        has_claim_safety_review,
        has_evidence_quality,
        has_video_evidence_reports,
        cross_video_summary is not None,
        has_structured_outputs,
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
        has_evidence_bundles=evidence_index is not None,
        has_cross_video_pattern_summary=cross_video_summary is not None,
        has_structured_outputs=has_structured_outputs,
        has_telegram_delivery=has_telegram_delivery,
        has_evidence_artifact_cleanup=has_evidence_artifact_cleanup,
        has_refinement_hooks=has_refinement_hooks,
    )
    if has_structured_outputs:
        write_structured_json_and_spreadsheet_summary(
            run_folder,
            selected_batch,
            evidence_index,
            metadata,
            cross_video_summary["summary"],
        )
        write_refinement_hooks(run_folder, cross_video_summary["summary"])
    if has_telegram_delivery:
        deliver_telegram_brief(
            run_folder,
            metadata,
            cross_video_summary["summary"],
            configuration.get("telegram", {}),
        )
    if has_evidence_artifact_cleanup:
        cleanup_evidence_artifacts(
            run_folder,
            evidence_index,
            configuration.get("cleanup", {}),
        )
    if selected_batch is not None:
        write_selected_batch(run_folder, selected_batch)
    write_batch_index_from_manifest(run_folder, manifest)
    return run_folder
