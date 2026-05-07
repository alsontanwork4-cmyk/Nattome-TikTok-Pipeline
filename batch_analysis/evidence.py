from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .claim_safety import write_claim_safety_review_from_snapshot
from .evidence_quality import write_evidence_quality_from_snapshot
from .evidence_io import (
    gemini_evidence_from_snapshot,
    prefixed_data_artifact_path,
    prefixed_report_path,
    read_json_object,
    relative_path,
)
from .reports import write_video_evidence_report_from_snapshot
from .shootable_angles import generate_shootable_angles

def nattome_audio_recommendation(audio_format: str, hook_support: str) -> dict[str, str]:
    if "no audio hook evidence" in hook_support:
        return {
            "action": "avoid",
            "reason": "No usable audio evidence was captured for adaptation.",
        }
    if audio_format in {"talking_head", "voiceover", "reused_sound", "music_only"}:
        return {
            "action": "adapt",
            "reason": "Use the audio style as inspiration while rewriting claims for Nattome-safe language.",
        }
    return {
        "action": "adapt",
        "reason": "Audio evidence is limited; adapt only after human review.",
    }


def infer_gemini_audio_format(candidate: dict[str, Any], gemini_evidence: dict[str, Any]) -> str:
    if candidate.get("audio_format_hint"):
        return str(candidate["audio_format_hint"])
    audio_cues = gemini_evidence.get("audio_cues")
    spoken_content = gemini_evidence.get("spoken_content")
    if isinstance(spoken_content, list) and spoken_content:
        return "voiceover"
    if isinstance(audio_cues, list):
        cue_text = " ".join(str(cue.get("cue") or "") for cue in audio_cues if isinstance(cue, dict)).lower()
        if any(term in cue_text for term in ("music", "song", "sound", "beat")):
            return "music_or_reused_sound"
        if cue_text:
            return "audio_cue"
    return "unknown"


def infer_gemini_audio_mood(candidate: dict[str, Any], gemini_evidence: dict[str, Any]) -> str:
    if candidate.get("audio_mood"):
        return str(candidate["audio_mood"])
    audio_cues = gemini_evidence.get("audio_cues")
    if isinstance(audio_cues, list) and audio_cues:
        return "gemini_described"
    if gemini_evidence.get("status") not in {"completed", "partial"}:
        return "manual_review_required"
    return "unknown"


def infer_gemini_hook_support(gemini_evidence: dict[str, Any]) -> str:
    hook_items = gemini_evidence.get("hook_evidence")
    if isinstance(hook_items, list) and hook_items:
        first = next((item for item in hook_items if isinstance(item, dict)), None)
        if first is not None:
            return f"Gemini hook evidence: {first.get('evidence')}"
    audio_cues = gemini_evidence.get("audio_cues")
    if isinstance(audio_cues, list) and audio_cues:
        first = next((item for item in audio_cues if isinstance(item, dict)), None)
        if first is not None:
            return f"Gemini audio cue may support hook: {first.get('cue')}"
    return "Gemini hook or audio evidence is unavailable; manual review required"


def write_baseline_audio_analysis_from_snapshot(
    analysis_path: Path,
    candidate: dict[str, Any],
    gemini_evidence: dict[str, Any],
) -> dict[str, Any]:
    audio_format = infer_gemini_audio_format(candidate, gemini_evidence)
    hook_support = infer_gemini_hook_support(gemini_evidence)
    analysis = {
        "status": "completed",
        "sound": {
            "title": candidate.get("sound_title"),
            "author": candidate.get("sound_author"),
            "is_reused_sound": candidate.get("is_reused_sound"),
        },
        "audio_format": audio_format,
        "mood": infer_gemini_audio_mood(candidate, gemini_evidence),
        "hook_support": hook_support,
        "nattome_recommendation": nattome_audio_recommendation(audio_format, hook_support),
        "evidence_basis": {
            "source": "evidence_bundle_snapshot",
            "gemini_sections": ["audio_cues", "hook_evidence", "spoken_content"],
        },
        "manual_review": {
            "required": gemini_evidence.get("status") not in {"completed", "partial"}
            or not gemini_evidence.get("audio_cues"),
            "reason": None
            if gemini_evidence.get("audio_cues")
            else "Gemini audio cues are unavailable",
        },
        "deep_sound_research": {
            "status": "not_implemented",
        },
    }
    analysis_path.parent.mkdir(parents=True, exist_ok=True)
    analysis_path.write_text(
        json.dumps(analysis, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"status": analysis["status"]}


def write_snapshot_evidence_outputs(
    run_folder: Path,
    candidate: dict[str, Any],
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    gemini_evidence = gemini_evidence_from_snapshot(run_folder, snapshot)

    audio_path = prefixed_data_artifact_path(run_folder, snapshot, "baseline_audio_analysis")
    write_baseline_audio_analysis_from_snapshot(audio_path, candidate, gemini_evidence)
    audio_analysis = read_json_object(audio_path) or {}

    claim_path = prefixed_data_artifact_path(run_folder, snapshot, "claim_safety_review")
    write_claim_safety_review_from_snapshot(claim_path, gemini_evidence)
    claim_review = read_json_object(claim_path) or {}

    quality_path = prefixed_data_artifact_path(run_folder, snapshot, "evidence_quality")
    write_evidence_quality_from_snapshot(
        quality_path,
        candidate,
        snapshot,
        gemini_evidence,
        claim_review,
    )
    quality = read_json_object(quality_path) or {}
    shootable_angles = generate_shootable_angles(
        candidate,
        snapshot,
        gemini_evidence,
        claim_safety_review=claim_review,
        evidence_quality=quality,
    )
    angles_path = prefixed_data_artifact_path(run_folder, snapshot, "shootable_angles")
    angles_path.write_text(
        json.dumps(
            {
                "status": "completed",
                "candidate_id": snapshot.get("candidate_id"),
                "angles": shootable_angles,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    report_path = prefixed_report_path(run_folder, snapshot, "video_evidence_report")
    write_video_evidence_report_from_snapshot(
        report_path,
        candidate,
        snapshot,
        gemini_evidence,
        audio_analysis,
        claim_review,
        quality,
        shootable_angles,
    )

    snapshot.setdefault("artifacts", {})
    for artifact_name, path in {
        "baseline_audio_analysis": audio_path,
        "claim_safety_review": claim_path,
        "evidence_quality": quality_path,
        "shootable_angles": angles_path,
        "video_evidence_report": report_path,
    }.items():
        snapshot["artifacts"][artifact_name] = {
            "state": "completed",
            "path": relative_path(path, run_folder),
        }

    snapshot_path = snapshot.get("snapshot_path")
    if snapshot_path:
        (run_folder / str(snapshot_path)).write_text(
            json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    return {
        "status": "completed",
        "report_path": relative_path(report_path, run_folder),
        "quality_path": relative_path(quality_path, run_folder),
        "claim_safety_review_path": relative_path(claim_path, run_folder),
        "baseline_audio_analysis_path": relative_path(audio_path, run_folder),
        "shootable_angles_path": relative_path(angles_path, run_folder),
    }


