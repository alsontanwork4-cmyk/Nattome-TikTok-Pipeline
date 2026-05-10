from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .candidates import load_candidates, select_candidates
from .config import (
    DAILY_RUN_MODE,
    DAILY_SELECTION_SIZE,
    MODE_DEFAULT_BATCH_SIZE,
    RUN_SUBDIRECTORIES,
    isoformat_local,
    load_config,
    parse_run_timestamp,
    run_folder_name,
)
from .evidence_io import EvidenceBundleStore
from .gemini_reports import GeminiClientFactory, generate_nattome_pov_reports
from .telegram_delivery import TelegramDocumentSender, TelegramSender, deliver_reports_to_telegram


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def runtime_mode(args: argparse.Namespace) -> str:
    return str(getattr(args, "mode", None) or DAILY_RUN_MODE)


def requested_batch_size(args: argparse.Namespace) -> int:
    explicit_batch_size = getattr(args, "batch_size", None)
    if explicit_batch_size is not None:
        return int(explicit_batch_size)
    return int(MODE_DEFAULT_BATCH_SIZE.get(runtime_mode(args), 3))


def output_path(run_folder: Path, subdirectory: str, filename: str) -> Path:
    path = run_folder / subdirectory / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_selected_batch(run_folder: Path, selected_batch: dict[str, Any]) -> None:
    write_json(output_path(run_folder, "data", "selected_batch.json"), selected_batch)

    lines = [
        "# Selected Batch Preview",
        "",
        f"- Selected at: {selected_batch['selected_at']}",
        f"- Requested batch size: {selected_batch['requested_batch_size']}",
        f"- Input candidates: {selected_batch['input_candidate_count']}",
        f"- Eligible candidates: {selected_batch['eligible_candidate_count']}",
        f"- Selected candidates: {selected_batch['selected_candidate_count']}",
        "",
        "| Rank | ID | Views | Weighted ER | Virality | URL |",
        "|---:|---|---:|---:|---:|---|",
    ]
    for candidate in selected_batch["selected_candidates"]:
        lines.append(
            "| {rank} | {id} | {views} | {er:.4f} | {virality:.4f} | {url} |".format(
                rank=candidate["rank"],
                id=candidate["id"],
                views=candidate["play_count"],
                er=candidate["weighted_engagement_rate"],
                virality=candidate["virality_score"],
                url=candidate["url"],
            )
        )
    lines.extend(["", "## Excluded Candidates", ""])
    for candidate in selected_batch["excluded_candidates"]:
        lines.append(f"- `{candidate['id']}`: {candidate['reason']}")

    output_path(run_folder, "reports", "selected_batch.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def build_metadata(
    args: argparse.Namespace,
    timestamp: Any,
    configuration: dict[str, Any],
    *,
    has_candidate_selection: bool,
    has_source_video_snapshots: bool,
) -> dict[str, Any]:
    return {
        "run_timestamp": isoformat_local(timestamp),
        "mode": runtime_mode(args),
        "requested_batch_size": requested_batch_size(args),
        "configuration": configuration,
        "implementation_status": {
            "candidate_selection": "implemented" if has_candidate_selection else "not_implemented",
            "source_video_download": "implemented" if has_source_video_snapshots else "not_implemented",
            "gemini_nattome_pov_reports": "implemented" if has_source_video_snapshots else "not_implemented",
        },
        "notes": [
            "Python orchestrates discovery, selection, source-video snapshots, Gemini status tracking, and artifact persistence.",
            "Gemini is responsible for evidence interpretation and marketer-facing creative report wording.",
        ],
    }


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


def runtime_phase(
    name: str,
    completed: bool,
    *,
    inputs: dict[str, Any] | None = None,
    outputs: dict[str, Any] | None = None,
    skipped_note: str,
) -> dict[str, Any]:
    return phase_record(
        name,
        "completed" if completed else "skipped",
        inputs=inputs,
        outputs=outputs if completed else {},
        notes=[] if completed else [skipped_note],
    )


def build_run_manifest(
    args: Any,
    timestamp: Any,
    configuration: dict[str, Any],
    *,
    has_candidate_selection: bool,
    has_source_video_snapshots: bool,
) -> dict[str, Any]:
    batch_size = getattr(args, "batch_size", None)
    if batch_size is None:
        batch_size = DAILY_SELECTION_SIZE
    mode = str(getattr(args, "mode", None) or DAILY_RUN_MODE)
    raw_candidates_path = getattr(args, "candidates", None)
    candidates_path = str(raw_candidates_path) if raw_candidates_path else None

    phases = [
        phase_record(
            "run_folder",
            "completed",
            outputs={"folders": list(RUN_SUBDIRECTORIES)},
        ),
        runtime_phase(
            "candidate_selection",
            has_candidate_selection,
            inputs={"candidates_path": candidates_path, "requested_batch_size": batch_size},
            outputs={
                "json": "data/selected_batch.json",
                "markdown": "reports/selected_batch.md",
            },
            skipped_note="No candidate metadata file was provided.",
        ),
        runtime_phase(
            "source_video_snapshots",
            has_source_video_snapshots,
            outputs={"index": "data/evidence_bundle_index.json"},
            skipped_note="Source video snapshots require a selected batch.",
        ),
    ]

    return {
        "run_timestamp": isoformat_local(timestamp),
        "mode": mode,
        "requested_batch_size": batch_size,
        "configuration": configuration,
        "folders": list(RUN_SUBDIRECTORIES),
        "phases": phases,
        "outputs": {},
    }


def write_run_manifest(run_folder: Path, manifest: dict[str, Any]) -> None:
    write_json(run_folder / "run_manifest.json", manifest)


def existing_run_artifacts(run_folder: Path) -> list[Path]:
    candidates = [
        run_folder / "run_metadata.json",
        run_folder / "run_manifest.json",
        run_folder / "data" / "selected_batch.json",
        run_folder / "data" / "evidence_bundle_index.json",
        run_folder / "reports" / "selected_batch.md",
    ]
    return [path for path in candidates if path.exists()]


def create_run(
    args: argparse.Namespace,
    *,
    gemini_client_factory: GeminiClientFactory | None = None,
    telegram_sender: TelegramSender | None = None,
    telegram_document_sender: TelegramDocumentSender | None = None,
) -> Path:
    batch_size = requested_batch_size(args)
    mode = runtime_mode(args)
    if batch_size < 1:
        raise ValueError("batch size must be at least 1")

    configuration = load_config(getattr(args, "config", None))
    timestamp = parse_run_timestamp(getattr(args, "timestamp", None))
    candidates = load_candidates(getattr(args, "candidates", None))
    run_folder = args.runs_dir / run_folder_name(timestamp, mode)

    existing_artifacts = existing_run_artifacts(run_folder)
    if existing_artifacts:
        raise FileExistsError(f"run folder already contains batch analysis artifacts: {run_folder}")

    for subdirectory in RUN_SUBDIRECTORIES:
        (run_folder / subdirectory).mkdir(parents=True, exist_ok=True)

    selected_batch = None
    if candidates is not None:
        selected_batch = select_candidates(
            candidates,
            configuration,
            timestamp,
            batch_size,
            getattr(args, "candidates", None),
            preserve_order=mode == DAILY_RUN_MODE,
        )

    evidence_index = None
    gemini_reports = None
    if selected_batch is not None:
        write_selected_batch(run_folder, selected_batch)
        evidence_index = EvidenceBundleStore(run_folder).write_source_snapshots(
            selected_batch["selected_candidates"]
        )
        gemini_reports = generate_nattome_pov_reports(
            run_folder,
            selected_batch["selected_candidates"],
            client_factory=gemini_client_factory,
        )

    metadata = build_metadata(
        args,
        timestamp,
        configuration,
        has_candidate_selection=selected_batch is not None,
        has_source_video_snapshots=evidence_index is not None,
    )
    write_json(run_folder / "run_metadata.json", metadata)

    manifest = build_run_manifest(
        args,
        timestamp,
        configuration,
        has_candidate_selection=selected_batch is not None,
        has_source_video_snapshots=evidence_index is not None,
    )
    if gemini_reports is not None:
        manifest["phases"].extend(gemini_reports["phases"])
        manifest["outputs"]["final_outputs"] = gemini_reports["final_outputs"]
        telegram_delivery = deliver_reports_to_telegram(
            run_folder,
            gemini_reports["final_outputs"],
            sender=telegram_sender,
            document_sender=telegram_document_sender,
        )
        manifest["phases"].append(telegram_delivery)
        manifest["outputs"]["pipeline_status"] = (
            "nattome_pov_reports_delivered"
            if telegram_delivery["status"] == "completed"
            else "nattome_pov_reports_completed"
            if gemini_reports["final_outputs"]
            else "source_video_download_completed"
        )
    else:
        manifest["outputs"]["final_outputs"] = []
        manifest["outputs"]["pipeline_status"] = "skeleton_created"
    write_run_manifest(run_folder, manifest)
    return run_folder
