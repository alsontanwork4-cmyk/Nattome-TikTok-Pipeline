from __future__ import annotations

import json
from pathlib import Path
from typing import Any

def truthy_metadata_flag(candidate: dict[str, Any], *keys: str) -> bool:
    for key in keys:
        value = candidate.get(key)
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.strip().lower() in {"true", "yes", "1"}:
            return True
    return False

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
        return "source video and Gemini evidence are complete"
    return "evidence requires manual review"


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

