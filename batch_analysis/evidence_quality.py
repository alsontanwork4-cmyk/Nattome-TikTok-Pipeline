from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .evidence_io import read_json_object

def truthy_metadata_flag(candidate: dict[str, Any], *keys: str) -> bool:
    for key in keys:
        value = candidate.get(key)
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.strip().lower() in {"true", "yes", "1"}:
            return True
    return False

def transcript_has_first_three_second_hook(transcript: dict[str, Any] | None) -> bool:
    segments = transcript.get("segments") if isinstance(transcript, dict) else []
    if not isinstance(segments, list):
        return False
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        text = str(segment.get("text") or "").strip()
        if not text:
            continue
        start = segment.get("start_seconds")
        if start is None:
            return True
        try:
            if float(start) <= 3:
                return True
        except (TypeError, ValueError):
            continue
    return False

def ocr_has_first_three_second_text(ocr: dict[str, Any] | None) -> bool:
    frames = ocr.get("frames") if isinstance(ocr, dict) else []
    if not isinstance(frames, list):
        return False
    for frame in frames:
        if not isinstance(frame, dict):
            continue
        text = str(frame.get("ocr_text") or "").strip()
        if not text:
            continue
        timestamp = frame.get("timestamp_seconds")
        try:
            if timestamp is None or float(timestamp) <= 3:
                return True
        except (TypeError, ValueError):
            continue
    return False

def audio_analysis_has_hook_support(audio_analysis: dict[str, Any] | None) -> bool:
    if not isinstance(audio_analysis, dict):
        return False
    hook_support = str(audio_analysis.get("hook_support") or "").lower()
    if not hook_support:
        return False
    weak_phrases = (
        "no audio hook evidence",
        "requires later deep sound research",
        "no transcript hook was captured",
    )
    return not any(phrase in hook_support for phrase in weak_phrases)

def transcript_language_detected(transcript: dict[str, Any] | None) -> bool:
    if not isinstance(transcript, dict):
        return False
    if transcript.get("language_detected"):
        return True
    segments = transcript.get("segments")
    if not isinstance(segments, list):
        return False
    return any(isinstance(segment, dict) and segment.get("language") for segment in segments)

def transcript_confidence_is_usable(transcript: dict[str, Any] | None) -> bool:
    if not isinstance(transcript, dict):
        return False
    summary = transcript.get("summary")
    if isinstance(summary, dict) and not summary.get("has_confidence_metadata"):
        return False
    segments = transcript.get("segments")
    if not isinstance(segments, list) or not segments:
        return False
    confidences = [
        segment.get("confidence")
        for segment in segments
        if isinstance(segment, dict) and segment.get("confidence") is not None
    ]
    if not confidences:
        return False
    usable = []
    for confidence in confidences:
        try:
            usable.append(float(confidence) >= 0.7)
        except (TypeError, ValueError):
            usable.append(False)
    return all(usable)

def evidence_quality_level(
    critical_failures: list[str],
    review_reasons: list[str],
) -> str:
    if critical_failures:
        return "low"
    if review_reasons:
        return "medium"
    return "high"

def evidence_quality_reason(
    level: str,
    critical_failures: list[str],
    review_reasons: list[str],
) -> str:
    reason_source = critical_failures if critical_failures else review_reasons
    if reason_source:
        return "; ".join(reason_source[:3])
    if level == "high":
        return "video, timeline, OCR, transcript, and audio evidence are complete"
    return "evidence requires manual review"

def write_evidence_quality(
    bundle_folder: Path,
    candidate: dict[str, Any],
) -> dict[str, Any]:
    quality_path = bundle_folder / "evidence_quality.json"
    download_status = read_json_object(bundle_folder / "download_status.json") or {}
    timeline = read_json_object(bundle_folder / "hybrid_timeline.json")
    ocr = read_json_object(bundle_folder / "ocr_evidence.json")
    transcript = read_json_object(bundle_folder / "transcript_evidence.json")
    audio_analysis = read_json_object(bundle_folder / "baseline_audio_analysis.json")
    claim_safety_review = read_json_object(bundle_folder / "claim_safety_review.json")
    visible_text_expected = truthy_metadata_flag(
        candidate,
        "visible_text_expected",
        "has_visible_text",
        "text_overlay_expected",
    )

    critical_failures: list[str] = []
    review_reasons: list[str] = []
    manual_review_reasons: list[str] = []

    download_ok = download_status.get("status") == "downloaded"
    if not download_ok:
        critical_failures.append("video download failed")

    timeline_ok = isinstance(timeline, dict) and timeline.get("status") == "extracted"
    if not timeline_ok:
        critical_failures.append("timeline extraction incomplete")

    ocr_status = ocr.get("status") if isinstance(ocr, dict) else None
    ocr_text_frame_count = 0
    if isinstance(ocr, dict) and isinstance(ocr.get("summary"), dict):
        try:
            ocr_text_frame_count = int(ocr["summary"].get("text_frame_count") or 0)
        except (TypeError, ValueError):
            ocr_text_frame_count = 0
    ocr_visible_text_failed = visible_text_expected and (
        ocr_status != "completed" or ocr_text_frame_count == 0
    )
    if ocr_visible_text_failed:
        critical_failures.append("OCR failed on visible text")
        manual_review_reasons.append("ocr_failed_on_visible_text")
    elif ocr_status != "completed":
        review_reasons.append("OCR evidence incomplete")

    transcript_status = transcript.get("status") if isinstance(transcript, dict) else None
    transcript_language_ok = transcript_language_detected(transcript)
    transcript_confidence_ok = transcript_confidence_is_usable(transcript)
    if transcript_status != "completed":
        critical_failures.append("transcript failed")
        manual_review_reasons.append("transcript_language_detection_failed")
    elif not transcript_language_ok:
        review_reasons.append("language detection failed")
        manual_review_reasons.append("transcript_language_detection_failed")
    elif not transcript_confidence_ok:
        review_reasons.append("transcript confidence is incomplete or low")

    first_three_second_hook_clear = (
        ocr_has_first_three_second_text(ocr)
        or transcript_has_first_three_second_hook(transcript)
        or audio_analysis_has_hook_support(audio_analysis)
    )
    if not first_three_second_hook_clear:
        review_reasons.append("first-three-second hook unclear")
        manual_review_reasons.append("first_three_second_hook_unclear")

    audio_ok = isinstance(audio_analysis, dict) and audio_analysis.get("status") == "completed"
    if not audio_ok:
        review_reasons.append("audio analysis incomplete")

    flagged_claim_count = 0
    if isinstance(claim_safety_review, dict) and isinstance(
        claim_safety_review.get("summary"), dict
    ):
        try:
            flagged_claim_count = int(claim_safety_review["summary"].get("flagged_count") or 0)
        except (TypeError, ValueError):
            flagged_claim_count = 0
    if flagged_claim_count:
        review_reasons.append("claim safety review flagged unsafe claims")
        manual_review_reasons.append("claim_safety_review_flagged_claims")

    level = evidence_quality_level(critical_failures, review_reasons)
    if level in {"medium", "low"}:
        manual_review_reasons.insert(0, f"evidence_quality_{level}")

    quality = {
        "status": "completed",
        "evidence_quality_score": {
            "level": level,
            "reason": evidence_quality_reason(level, critical_failures, review_reasons),
        },
        "manual_review_flag": {
            "required": bool(manual_review_reasons),
            "reasons": list(dict.fromkeys(manual_review_reasons)),
        },
        "checks": {
            "video_download": {
                "status": download_status.get("status", "missing"),
                "passed": download_ok,
            },
            "timeline_completeness": {
                "status": timeline.get("status") if isinstance(timeline, dict) else "missing",
                "passed": timeline_ok,
            },
            "ocr_quality": {
                "status": ocr_status or "missing",
                "visible_text_expected": visible_text_expected,
                "text_frame_count": ocr_text_frame_count,
                "passed": ocr_status == "completed" and not ocr_visible_text_failed,
            },
            "transcript_quality": {
                "status": transcript_status or "missing",
                "language_detected": transcript_language_ok,
                "confidence_usable": transcript_confidence_ok,
                "passed": (
                    transcript_status == "completed"
                    and transcript_language_ok
                    and transcript_confidence_ok
                ),
            },
            "first_three_second_hook": {
                "clear": first_three_second_hook_clear,
            },
            "audio_analysis": {
                "status": audio_analysis.get("status")
                if isinstance(audio_analysis, dict)
                else "missing",
                "passed": audio_ok,
            },
            "claim_uncertainty": {
                "status": "flagged" if flagged_claim_count else "clear",
                "flagged_count": flagged_claim_count,
            },
        },
    }
    quality_path.write_text(
        json.dumps(quality, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {
        "status": quality["status"],
        "score": level,
        "manual_review_required": quality["manual_review_flag"]["required"],
    }


def gemini_section_count(gemini_evidence: dict[str, Any], section: str) -> int:
    items = gemini_evidence.get(section)
    return len(items) if isinstance(items, list) else 0


def gemini_has_first_three_second_hook(gemini_evidence: dict[str, Any]) -> bool:
    for section, text_key, timestamp_key in (
        ("hook_evidence", "evidence", "timestamp_seconds"),
        ("visible_text", "text", "timestamp_seconds"),
        ("spoken_content", "text", "start_seconds"),
        ("audio_cues", "cue", "timestamp_seconds"),
    ):
        items = gemini_evidence.get(section)
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict) or not str(item.get(text_key) or "").strip():
                continue
            timestamp = item.get(timestamp_key)
            try:
                if timestamp is None or float(timestamp) <= 3:
                    return True
            except (TypeError, ValueError):
                continue
    return False


def write_evidence_quality_from_snapshot(
    quality_path: Path,
    candidate: dict[str, Any],
    snapshot: dict[str, Any],
    gemini_evidence: dict[str, Any],
    claim_safety_review: dict[str, Any] | None,
) -> dict[str, Any]:
    critical_failures: list[str] = []
    review_reasons: list[str] = []
    manual_review_reasons: list[str] = []

    source_video_state = snapshot.get("source_video", {}).get("state")
    if source_video_state != "available":
        critical_failures.append("source video unavailable")

    gemini_status = gemini_evidence.get("status")
    if gemini_status not in {"completed", "partial"}:
        critical_failures.append(
            gemini_evidence.get("reason") or "Gemini evidence not available"
        )
        manual_review_reasons.append("gemini_evidence_unavailable")

    required_sections = [
        ("visual_observations", "visual"),
        ("visible_text", "visible text"),
        ("spoken_content", "spoken"),
        ("audio_cues", "audio"),
        ("hook_evidence", "hook"),
        ("claim_evidence", "claim"),
    ]
    section_counts = {
        section: gemini_section_count(gemini_evidence, section)
        for section, _label in required_sections
    }
    for section, label in required_sections:
        if section_counts[section] == 0:
            review_reasons.append(f"missing Gemini {label} evidence")
            manual_review_reasons.append(f"missing_gemini_{section}")

    visible_text_expected = truthy_metadata_flag(
        candidate,
        "visible_text_expected",
        "has_visible_text",
        "text_overlay_expected",
    )
    if visible_text_expected and section_counts["visible_text"] == 0:
        critical_failures.append("Gemini visible text evidence missing despite expected text")

    first_three_second_hook_clear = gemini_has_first_three_second_hook(gemini_evidence)
    if not first_three_second_hook_clear:
        review_reasons.append("first-three-second hook unclear")
        manual_review_reasons.append("first_three_second_hook_unclear")

    flagged_claim_count = 0
    if isinstance(claim_safety_review, dict) and isinstance(
        claim_safety_review.get("summary"), dict
    ):
        try:
            flagged_claim_count = int(claim_safety_review["summary"].get("flagged_count") or 0)
        except (TypeError, ValueError):
            flagged_claim_count = 0
    if flagged_claim_count:
        review_reasons.append("claim safety review flagged unsafe claims")
        manual_review_reasons.append("claim_safety_review_flagged_claims")

    level = evidence_quality_level(critical_failures, review_reasons)
    if level in {"medium", "low"}:
        manual_review_reasons.insert(0, f"evidence_quality_{level}")

    quality = {
        "status": "completed",
        "evidence_quality_score": {
            "level": level,
            "reason": evidence_quality_reason(
                level,
                critical_failures + review_reasons,
                [],
            ),
        },
        "manual_review_flag": {
            "required": bool(manual_review_reasons),
            "reasons": list(dict.fromkeys(manual_review_reasons)),
        },
        "checks": {
            "source_video": {
                "status": source_video_state or "missing",
                "passed": source_video_state == "available",
            },
            "gemini_visual_evidence": {
                "count": section_counts["visual_observations"],
                "passed": section_counts["visual_observations"] > 0,
            },
            "gemini_visible_text": {
                "count": section_counts["visible_text"],
                "visible_text_expected": visible_text_expected,
                "passed": section_counts["visible_text"] > 0 or not visible_text_expected,
            },
            "gemini_spoken_content": {
                "count": section_counts["spoken_content"],
                "passed": section_counts["spoken_content"] > 0,
            },
            "gemini_audio_cues": {
                "count": section_counts["audio_cues"],
                "passed": section_counts["audio_cues"] > 0,
            },
            "first_three_second_hook": {
                "clear": first_three_second_hook_clear,
            },
            "gemini_claim_evidence": {
                "count": section_counts["claim_evidence"],
                "passed": section_counts["claim_evidence"] > 0,
            },
            "claim_uncertainty": {
                "status": "flagged" if flagged_claim_count else "clear",
                "flagged_count": flagged_claim_count,
            },
        },
    }
    quality_path.parent.mkdir(parents=True, exist_ok=True)
    quality_path.write_text(
        json.dumps(quality, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {
        "status": quality["status"],
        "score": level,
        "manual_review_required": quality["manual_review_flag"]["required"],
    }

