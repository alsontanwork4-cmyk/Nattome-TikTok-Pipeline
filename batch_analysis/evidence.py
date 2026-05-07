from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .candidates import parse_duration_seconds
from .claim_safety import write_claim_safety_review, write_claim_safety_review_from_snapshot
from .evidence_quality import write_evidence_quality, write_evidence_quality_from_snapshot
from .evidence_io import (
    gemini_evidence_from_snapshot,
    prefixed_data_artifact_path,
    prefixed_report_path,
    read_json_object,
    relative_path,
)
from .reports import write_video_evidence_report, write_video_evidence_report_from_snapshot
from .shootable_angles import generate_shootable_angles
from .tool_adapters import (
    copy_or_download_video,
    extract_audio,
    extract_timeline_frame,
    run_ocr_command,
    run_transcription_command,
    source_video_filename,
)

def safe_folder_token(value: Any) -> str:
    token = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in str(value or "unknown"))
    return token.strip("-") or "unknown"

def write_evidence_bundles(
    run_folder: Path,
    selected_batch: dict[str, Any],
    ffmpeg_bin: str,
    ocr_primary_bin: str,
    ocr_fallback_bin: str,
    transcription_bin: str,
) -> dict[str, Any]:
    bundles_root = run_folder / "evidence_bundles"
    index_entries = []

    for candidate in selected_batch["selected_candidates"]:
        candidate_id = candidate.get("id") or f"rank-{candidate['rank']}"
        bundle_relative = Path("evidence_bundles") / (
            f"{candidate['rank']:03d}_{safe_folder_token(candidate_id)}"
        )
        bundle_folder = run_folder / bundle_relative
        artifacts_folder = bundle_folder / "artifacts"
        artifacts_folder.mkdir(parents=True, exist_ok=False)

        (bundle_folder / "source_metadata.json").write_text(
            json.dumps(candidate, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        video_source = candidate.get("video_download_url") or ""
        video_artifact_path = artifacts_folder / source_video_filename(video_source)
        download_status = copy_or_download_video(video_source, video_artifact_path)
        if download_status["status"] != "downloaded" and video_artifact_path.exists():
            video_artifact_path.unlink()
        (bundle_folder / "download_status.json").write_text(
            json.dumps(download_status, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        source_video_exists = download_status["status"] == "downloaded"
        bundle_index = {
            "candidate_id": candidate_id,
            "rank": candidate["rank"],
            "bundle_folder": str(bundle_relative),
            "original_tiktok_url": candidate["url"],
            "source_metadata": str(bundle_relative / "source_metadata.json"),
            "download_status": download_status,
            "artifacts": {
                "source_video": {
                    "exists": source_video_exists,
                    "path": str(bundle_relative / "artifacts" / download_status["artifact"])
                    if source_video_exists
                    else None,
                }
            },
        }
        timeline_status = write_hybrid_timeline(
            bundle_folder,
            video_artifact_path if source_video_exists else None,
            candidate,
            ffmpeg_bin=ffmpeg_bin,
        )
        bundle_index["artifacts"]["hybrid_timeline"] = {
            "exists": timeline_status["status"] == "extracted",
            "path": str(bundle_relative / "hybrid_timeline.json"),
            "frame_count": timeline_status["frame_count"],
            "status": timeline_status["status"],
        }
        ocr_status = write_ocr_evidence(
            bundle_folder,
            ocr_primary_bin=ocr_primary_bin,
            ocr_fallback_bin=ocr_fallback_bin,
        )
        bundle_index["artifacts"]["ocr_evidence"] = {
            "exists": ocr_status["status"] == "completed",
            "path": str(bundle_relative / "ocr_evidence.json"),
            "frame_count": ocr_status["frame_count"],
            "text_frame_count": ocr_status["text_frame_count"],
            "status": ocr_status["status"],
        }
        transcript_status = write_transcript_evidence(
            bundle_folder,
            video_artifact_path if source_video_exists else None,
            ffmpeg_bin=ffmpeg_bin,
            transcription_bin=transcription_bin,
        )
        bundle_index["artifacts"]["audio"] = {
            "exists": transcript_status["audio_exists"],
            "path": str(bundle_relative / "artifacts" / "audio" / "source_audio.wav")
            if transcript_status["audio_exists"]
            else None,
            "status": transcript_status["audio_status"],
        }
        bundle_index["artifacts"]["transcript_evidence"] = {
            "exists": transcript_status["status"] == "completed",
            "path": str(bundle_relative / "transcript_evidence.json"),
            "segment_count": transcript_status["segment_count"],
            "status": transcript_status["status"],
        }
        audio_analysis_status = write_baseline_audio_analysis(bundle_folder, candidate)
        bundle_index["artifacts"]["baseline_audio_analysis"] = {
            "exists": audio_analysis_status["status"] == "completed",
            "path": str(bundle_relative / "baseline_audio_analysis.json"),
            "status": audio_analysis_status["status"],
        }
        claim_safety_status = write_claim_safety_review(bundle_folder)
        bundle_index["artifacts"]["claim_safety_review"] = {
            "exists": claim_safety_status["status"] == "completed",
            "path": str(bundle_relative / "claim_safety_review.json"),
            "status": claim_safety_status["status"],
            "flagged_count": claim_safety_status["flagged_count"],
        }
        evidence_quality = write_evidence_quality(bundle_folder, candidate)
        bundle_index["artifacts"]["evidence_quality"] = {
            "exists": evidence_quality["status"] == "completed",
            "path": str(bundle_relative / "evidence_quality.json"),
            "status": evidence_quality["status"],
            "score": evidence_quality["score"],
            "manual_review_required": evidence_quality["manual_review_required"],
        }
        report_status = write_video_evidence_report(bundle_folder, candidate)
        bundle_index["artifacts"]["video_evidence_report"] = {
            "exists": report_status["status"] == "completed",
            "path": str(bundle_relative / "video_evidence_report.md"),
            "status": report_status["status"],
        }
        (bundle_folder / "evidence_bundle_index.json").write_text(
            json.dumps(bundle_index, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        index_entries.append(bundle_index)

    evidence_index = {
        "created_at": selected_batch["selected_at"],
        "bundle_count": len(index_entries),
        "bundles": index_entries,
    }
    (bundles_root / "index.json").write_text(
        json.dumps(evidence_index, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return evidence_index

def normalized_timestamp(value: float) -> int | float:
    if value.is_integer():
        return int(value)
    return round(value, 3)

def hybrid_timeline_samples(duration_seconds: float | None) -> list[dict[str, Any]]:
    duration = duration_seconds if duration_seconds is not None else 3.0
    baseline_count = max(math.ceil(duration), 1)
    samples_by_timestamp: dict[float, str] = {
        float(second): "baseline_one_second" for second in range(baseline_count)
    }

    for timestamp in (0.5, 1.5, 2.5):
        if timestamp < duration:
            samples_by_timestamp.setdefault(timestamp, "hook_first_three_seconds")

    return [
        {
            "timestamp_seconds": normalized_timestamp(timestamp),
            "sampling_reason": samples_by_timestamp[timestamp],
        }
        for timestamp in sorted(samples_by_timestamp)
    ]

def timestamp_filename_token(timestamp_seconds: int | float) -> str:
    return f"{int(round(float(timestamp_seconds) * 1000)):06d}ms"

def write_hybrid_timeline(
    bundle_folder: Path,
    source_video_path: Path | None,
    candidate: dict[str, Any],
    ffmpeg_bin: str,
) -> dict[str, Any]:
    frames_folder = bundle_folder / "artifacts" / "frames"
    timeline_path = bundle_folder / "hybrid_timeline.json"
    duration_seconds = parse_duration_seconds(candidate)
    source_video_relative = (
        str(source_video_path.relative_to(bundle_folder)).replace("\\", "/")
        if source_video_path is not None
        else None
    )

    timeline: dict[str, Any] = {
        "status": "skipped",
        "source_video": source_video_relative,
        "duration_seconds": duration_seconds,
        "sampling_strategy": {
            "baseline_interval_seconds": 1,
            "hook_extra_timestamps_seconds": [0.5, 1.5, 2.5],
        },
        "extension_points": {
            "text_change_samples": "not_implemented",
            "scene_change_samples": "not_implemented",
        },
        "frames": [],
    }

    if source_video_path is None:
        timeline["reason"] = "source video artifact is missing"
        timeline_path.write_text(
            json.dumps(timeline, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return {"status": timeline["status"], "frame_count": 0}

    frames_folder.mkdir(parents=True, exist_ok=True)
    for sample in hybrid_timeline_samples(duration_seconds):
        filename = f"frame_{timestamp_filename_token(sample['timestamp_seconds'])}.jpg"
        frame_path = frames_folder / filename
        frame_status = extract_timeline_frame(
            ffmpeg_bin,
            source_video_path,
            sample["timestamp_seconds"],
            frame_path,
        )
        if frame_status["status"] != "completed":
            timeline["status"] = "failed"
            timeline["reason"] = frame_status["reason"]
            break

        timeline["frames"].append(
            {
                "timestamp_seconds": sample["timestamp_seconds"],
                "frame_path": str(frame_path.relative_to(bundle_folder)).replace("\\", "/"),
                "sampling_reason": sample["sampling_reason"],
            }
        )

    if timeline["frames"] and timeline.get("status") == "skipped":
        timeline["status"] = "extracted"
    timeline_path.write_text(
        json.dumps(timeline, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"status": timeline["status"], "frame_count": len(timeline["frames"])}


OCR_LANGUAGES = [
    "English",
    "Malay",
    "Simplified Chinese",
    "Traditional Chinese",
    "mixed-language text",
]

def read_timeline(bundle_folder: Path) -> dict[str, Any] | None:
    timeline_path = bundle_folder / "hybrid_timeline.json"
    if not timeline_path.exists():
        return None
    try:
        loaded = json.loads(timeline_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, dict) else None

def write_ocr_evidence(
    bundle_folder: Path,
    ocr_primary_bin: str,
    ocr_fallback_bin: str,
) -> dict[str, Any]:
    ocr_path = bundle_folder / "ocr_evidence.json"
    timeline = read_timeline(bundle_folder)
    evidence: dict[str, Any] = {
        "status": "skipped",
        "engine": {
            "primary": "paddleocr",
            "fallback": "tesseract",
            "selected": None,
        },
        "languages_requested": OCR_LANGUAGES,
        "frames": [],
        "summary": {
            "frame_count": 0,
            "text_frame_count": 0,
            "combined_text": "",
        },
    }

    if timeline is None:
        evidence["reason"] = "hybrid_timeline.json is missing or invalid"
        ocr_path.write_text(
            json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return {"status": evidence["status"], "frame_count": 0, "text_frame_count": 0}

    timeline_frames = timeline.get("frames") if isinstance(timeline.get("frames"), list) else []
    if timeline.get("status") != "extracted" or not timeline_frames:
        evidence["reason"] = "no extracted timeline frames are available for OCR"
        ocr_path.write_text(
            json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return {"status": evidence["status"], "frame_count": 0, "text_frame_count": 0}

    selected_engine = None
    last_error = None
    for frame in timeline_frames:
        frame_path = bundle_folder / str(frame["frame_path"])
        result = run_ocr_command(ocr_primary_bin, "paddleocr", frame_path)
        engine = "paddleocr"
        if result["status"] != "completed":
            last_error = result["reason"]
            result = run_ocr_command(ocr_fallback_bin, "tesseract", frame_path)
            engine = "tesseract"

        if result["status"] != "completed":
            evidence["status"] = "failed"
            evidence["reason"] = (
                "OCR tooling failed or is missing. "
                f"Tried PaddleOCR ({ocr_primary_bin}) and Tesseract ({ocr_fallback_bin}). "
                f"Last error: {result['reason']}"
            )
            if last_error:
                evidence["primary_error"] = last_error
            break

        selected_engine = selected_engine or engine
        text = result["text"]
        evidence["frames"].append(
            {
                "timestamp_seconds": frame["timestamp_seconds"],
                "frame_path": frame["frame_path"],
                "sampling_reason": frame["sampling_reason"],
                "ocr_text": text,
                "confidence": None,
                "engine": engine,
                "status": "completed",
            }
        )

    evidence["engine"]["selected"] = selected_engine
    if evidence["frames"] and evidence.get("status") == "skipped":
        evidence["status"] = "completed"
    texts = [frame["ocr_text"] for frame in evidence["frames"] if frame["ocr_text"]]
    evidence["summary"] = {
        "frame_count": len(evidence["frames"]),
        "text_frame_count": len(texts),
        "combined_text": "\n".join(texts),
    }
    ocr_path.write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {
        "status": evidence["status"],
        "frame_count": len(evidence["frames"]),
        "text_frame_count": len(texts),
    }


TRANSCRIPTION_LANGUAGES = [
    "English",
    "Malay",
    "Mandarin Chinese",
    "code-mixed English-Malay-Chinese",
]

def parse_transcript_segments(stdout: str) -> tuple[str | None, list[dict[str, Any]]]:
    if not stdout:
        return None, []
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return None, [
            {
                "start_seconds": None,
                "end_seconds": None,
                "text": stdout,
                "confidence": None,
                "language": None,
            }
        ]

    if not isinstance(payload, dict):
        return None, []

    language = payload.get("language") if isinstance(payload.get("language"), str) else None
    raw_segments = payload.get("segments")
    if not isinstance(raw_segments, list):
        text = str(payload.get("text") or "").strip()
        return language, [
            {
                "start_seconds": None,
                "end_seconds": None,
                "text": text,
                "confidence": payload.get("confidence"),
                "language": language,
            }
        ] if text else []

    segments = []
    for segment in raw_segments:
        if not isinstance(segment, dict):
            continue
        text = str(segment.get("text") or "").strip()
        if not text:
            continue
        segments.append(
            {
                "start_seconds": segment.get("start"),
                "end_seconds": segment.get("end"),
                "text": text,
                "confidence": segment.get("confidence"),
                "language": segment.get("language") or language,
            }
        )
    return language, segments

def write_transcript_evidence(
    bundle_folder: Path,
    source_video_path: Path | None,
    ffmpeg_bin: str,
    transcription_bin: str,
) -> dict[str, Any]:
    transcript_path = bundle_folder / "transcript_evidence.json"
    audio_path = bundle_folder / "artifacts" / "audio" / "source_audio.wav"
    source_video_relative = (
        str(source_video_path.relative_to(bundle_folder)).replace("\\", "/")
        if source_video_path is not None
        else None
    )
    audio_relative = str(audio_path.relative_to(bundle_folder)).replace("\\", "/")
    evidence: dict[str, Any] = {
        "status": "skipped",
        "source_video": source_video_relative,
        "audio_artifact": None,
        "engine": {
            "style": "whisper",
            "selected": None,
        },
        "languages_requested": TRANSCRIPTION_LANGUAGES,
        "segments": [],
        "summary": {
            "segment_count": 0,
            "combined_text": "",
            "has_confidence_metadata": False,
        },
    }

    if source_video_path is None:
        evidence["reason"] = "source video artifact is missing"
        transcript_path.write_text(
            json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return {
            "status": evidence["status"],
            "segment_count": 0,
            "audio_exists": False,
            "audio_status": "skipped",
        }

    audio_status = extract_audio(source_video_path, audio_path, ffmpeg_bin)
    if audio_status["status"] != "extracted":
        evidence["status"] = "failed"
        evidence["reason"] = audio_status["reason"]
        transcript_path.write_text(
            json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return {
            "status": evidence["status"],
            "segment_count": 0,
            "audio_exists": False,
            "audio_status": "failed",
        }

    evidence["audio_artifact"] = audio_relative
    result = run_transcription_command(transcription_bin, audio_path)
    if result["status"] != "completed":
        evidence["status"] = "failed"
        evidence["reason"] = (
            "Transcription tooling failed or is missing. "
            f"Tried Whisper-style executable ({transcription_bin}). "
            f"Last error: {result['reason']}"
        )
        transcript_path.write_text(
            json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return {
            "status": evidence["status"],
            "segment_count": 0,
            "audio_exists": audio_path.exists(),
            "audio_status": "extracted",
        }

    language, segments = parse_transcript_segments(result["stdout"])
    evidence["status"] = "completed"
    evidence["engine"]["selected"] = "whisper"
    evidence["language_detected"] = language
    evidence["segments"] = segments
    texts = [segment["text"] for segment in segments if segment["text"]]
    evidence["summary"] = {
        "segment_count": len(segments),
        "combined_text": "\n".join(texts),
        "has_confidence_metadata": any(
            segment.get("confidence") is not None for segment in segments
        ),
    }
    transcript_path.write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {
        "status": evidence["status"],
        "segment_count": len(segments),
        "audio_exists": audio_path.exists(),
        "audio_status": "extracted",
    }

def infer_audio_format(candidate: dict[str, Any], transcript: dict[str, Any] | None) -> str:
    hint = candidate.get("audio_format_hint")
    if hint:
        return str(hint)

    transcript_text = ""
    if transcript:
        summary = transcript.get("summary")
        if isinstance(summary, dict):
            transcript_text = str(summary.get("combined_text") or "")

    reused = candidate.get("is_reused_sound")
    if reused is True:
        return "reused_sound"
    if transcript_text:
        return "voiceover"
    if candidate.get("sound_title"):
        return "music_only"
    return "unknown"

def infer_audio_mood(candidate: dict[str, Any], transcript: dict[str, Any] | None) -> str:
    if candidate.get("audio_mood"):
        return str(candidate["audio_mood"])
    if transcript and transcript.get("status") == "completed":
        return "informational"
    if candidate.get("sound_title"):
        return "metadata_only"
    return "unknown"

def infer_hook_support(transcript: dict[str, Any] | None, audio_format: str) -> str:
    segments = transcript.get("segments") if isinstance(transcript, dict) else []
    if isinstance(segments, list):
        for segment in segments:
            if not isinstance(segment, dict):
                continue
            start = segment.get("start_seconds")
            text = str(segment.get("text") or "").strip()
            if text and (start is None or float(start) <= 3):
                return f"spoken hook supports first three seconds: {text}"
    if audio_format == "reused_sound":
        return "reused sound may support recognition, but no transcript hook was captured"
    if audio_format == "music_only":
        return "music-only hook support requires later Deep Sound Research"
    return "no audio hook evidence captured yet"

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

def write_baseline_audio_analysis(
    bundle_folder: Path,
    candidate: dict[str, Any],
) -> dict[str, Any]:
    analysis_path = bundle_folder / "baseline_audio_analysis.json"
    transcript = read_json_object(bundle_folder / "transcript_evidence.json")
    audio_format = infer_audio_format(candidate, transcript)
    hook_support = infer_hook_support(transcript, audio_format)
    analysis = {
        "status": "completed",
        "sound": {
            "title": candidate.get("sound_title"),
            "author": candidate.get("sound_author"),
            "is_reused_sound": candidate.get("is_reused_sound"),
        },
        "audio_format": audio_format,
        "mood": infer_audio_mood(candidate, transcript),
        "hook_support": hook_support,
        "nattome_recommendation": nattome_audio_recommendation(audio_format, hook_support),
        "evidence_basis": {
            "source_metadata": "source_metadata.json",
            "transcript_evidence": "transcript_evidence.json",
        },
        "deep_sound_research": {
            "status": "not_implemented",
        },
    }
    analysis_path.write_text(
        json.dumps(analysis, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {"status": analysis["status"]}


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
    }


