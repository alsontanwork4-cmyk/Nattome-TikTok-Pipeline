from __future__ import annotations

import math
from typing import Any


PRIORITY_SCORE_DIMENSIONS = [
    "viral_strength",
    "nattome_relevance",
    "evidence_confidence",
    "brand_safety",
    "ease_of_production",
    "product_fit",
]


def compact_text(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    return " ".join(text.split())


def product_fit_for_candidate(candidate: dict[str, Any]) -> str:
    caption = compact_text(candidate.get("caption")).lower()
    if any(term in caption for term in ("reflux", "heartburn", "acid", "indigestion")):
        return "DR for faster relief moments around reflux, heartburn, or gastric discomfort."
    if any(term in caption for term in ("repair", "recover", "recovery")):
        return "DH-R/recovery for deeper repair and recovery contexts."
    return "DH for daily digestive maintenance and routine support."


def avatar_for_candidate(candidate: dict[str, Any]) -> str:
    caption = compact_text(candidate.get("caption")).lower()
    if any(term in caption for term in ("reflux", "heartburn", "bloating", "gastric", "pain")):
        return "The Sufferer"
    if "family" in caption or "child" in caption:
        return "Family Caregiver"
    return "Maintainer"


def claim_guardrails_from_review(claim_safety_review: dict[str, Any] | None) -> str:
    claims = claim_safety_review.get("flagged_claims") if isinstance(claim_safety_review, dict) else []
    if isinstance(claims, list) and claims:
        categories = ", ".join(
            sorted(
                {
                    str(claim.get("category"))
                    for claim in claims
                    if isinstance(claim, dict) and claim.get("category")
                }
            )
        )
        return f"Do not reuse flagged claim categories directly: {categories}."
    return "Avoid cure, guaranteed outcome, overnight relief, detox, and unsupported clinical claims."


def first_text(items: Any, key: str) -> str:
    if not isinstance(items, list):
        return ""
    for item in items:
        if isinstance(item, dict):
            text = compact_text(item.get(key))
            if text:
                return text
    return ""


def evidence_count(gemini_evidence: dict[str, Any], section: str) -> int:
    items = gemini_evidence.get(section)
    return len(items) if isinstance(items, list) else 0


def evidence_confidence_points(
    gemini_evidence: dict[str, Any],
    evidence_quality: dict[str, Any] | None,
) -> int:
    quality_score = evidence_quality.get("evidence_quality_score") if isinstance(evidence_quality, dict) else {}
    quality_level = quality_score.get("level") if isinstance(quality_score, dict) else None
    if quality_level:
        return {"high": 5, "medium": 3, "low": 1}.get(str(quality_level), 1)

    populated_sections = sum(
        1
        for section in (
            "visual_observations",
            "visible_text",
            "spoken_content",
            "audio_cues",
            "hook_evidence",
            "claim_evidence",
        )
        if evidence_count(gemini_evidence, section)
    )
    if populated_sections >= 5:
        return 5
    if populated_sections >= 3:
        return 3
    return 1


def viral_strength_points(candidate: dict[str, Any]) -> int:
    views = int(candidate.get("play_count") or 0)
    engagement = float(candidate.get("weighted_engagement_rate") or 0)
    if views >= 250000 or engagement >= 0.15:
        return 5
    if views >= 100000 or engagement >= 0.10:
        return 4
    if views >= 50000 or engagement >= 0.06:
        return 3
    if views >= 10000 or engagement >= 0.03:
        return 2
    return 1


def nattome_relevance_points(candidate: dict[str, Any]) -> int:
    relevance = float(candidate.get("nattome_relevance_score") or 0)
    return max(1, min(5, math.ceil(relevance * 5)))


def brand_safety_points(claim_safety_review: dict[str, Any] | None) -> int:
    claims = claim_safety_review.get("flagged_claims") if isinstance(claim_safety_review, dict) else []
    flagged_count = len(claims) if isinstance(claims, list) else 0
    if flagged_count == 0:
        return 5
    if flagged_count <= 2:
        return 3
    return 1


def ease_of_production_points(audio_format: str) -> int:
    normalized = audio_format.lower()
    if normalized in {"talking_head", "voiceover", "original_voice", "audio_cue"}:
        return 5
    if normalized in {"reused_sound", "music_only", "music_or_reused_sound"}:
        return 3
    return 4


def product_fit_points(candidate: dict[str, Any]) -> int:
    relevance = float(candidate.get("nattome_relevance_score") or 0)
    product_fit = product_fit_for_candidate(candidate).lower()
    if any(product in product_fit for product in ("dr", "dh-r", "dh ")):
        return 5 if relevance >= 0.5 else 4
    return 3


def nattome_priority_score(
    candidate: dict[str, Any],
    gemini_evidence: dict[str, Any],
    *,
    claim_safety_review: dict[str, Any] | None = None,
    evidence_quality: dict[str, Any] | None = None,
    audio_format: str = "unknown",
) -> dict[str, Any]:
    dimensions = {
        "viral_strength": viral_strength_points(candidate),
        "nattome_relevance": nattome_relevance_points(candidate),
        "evidence_confidence": evidence_confidence_points(gemini_evidence, evidence_quality),
        "brand_safety": brand_safety_points(claim_safety_review),
        "ease_of_production": ease_of_production_points(audio_format),
        "product_fit": product_fit_points(candidate),
    }
    return {
        "dimensions": dimensions,
        "total": sum(dimensions.values()),
        "max_points": 30,
    }


def inferred_audio_format(gemini_evidence: dict[str, Any]) -> str:
    if evidence_count(gemini_evidence, "spoken_content"):
        return "voiceover"
    cue = first_text(gemini_evidence.get("audio_cues"), "cue").lower()
    if any(term in cue for term in ("music", "song", "sound", "beat")):
        return "music_or_reused_sound"
    if cue:
        return "audio_cue"
    return "unknown"


def base_angle(
    candidate: dict[str, Any],
    gemini_evidence: dict[str, Any],
    claim_safety_review: dict[str, Any] | None,
    evidence_quality: dict[str, Any] | None,
    *,
    title: str,
    hook: str,
    format_name: str,
    recommendation: str,
    source_evidence: list[str],
) -> dict[str, Any]:
    audio_format = inferred_audio_format(gemini_evidence)
    return {
        "angle_title": title,
        "hook": hook,
        "avatar": avatar_for_candidate(candidate),
        "format": format_name,
        "product_fit": product_fit_for_candidate(candidate),
        "recommendation": recommendation,
        "claim_guardrails": claim_guardrails_from_review(claim_safety_review),
        "source_evidence": source_evidence,
        "priority_score": nattome_priority_score(
            candidate,
            gemini_evidence,
            claim_safety_review=claim_safety_review,
            evidence_quality=evidence_quality,
            audio_format=audio_format,
        ),
    }


def has_evidence_anchor(gemini_evidence: dict[str, Any]) -> bool:
    if gemini_evidence.get("status") not in {"completed", "partial"}:
        return False
    return any(
        evidence_count(gemini_evidence, section)
        for section in (
            "visual_observations",
            "visible_text",
            "spoken_content",
            "audio_cues",
            "hook_evidence",
            "claim_evidence",
        )
    )


def generate_shootable_angles(
    candidate: dict[str, Any],
    snapshot: dict[str, Any],
    gemini_evidence: dict[str, Any],
    *,
    claim_safety_review: dict[str, Any] | None = None,
    evidence_quality: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if not has_evidence_anchor(gemini_evidence):
        return []

    angles: list[dict[str, Any]] = []
    caption = compact_text(candidate.get("caption"), "digestive comfort routine")
    hook_evidence = first_text(gemini_evidence.get("hook_evidence"), "evidence")
    visual_evidence = first_text(gemini_evidence.get("visual_observations"), "observation")
    visible_text = first_text(gemini_evidence.get("visible_text"), "text")
    spoken_content = first_text(gemini_evidence.get("spoken_content"), "text")
    audio_cue = first_text(gemini_evidence.get("audio_cues"), "cue")
    claim_text = first_text(gemini_evidence.get("claim_evidence"), "text")

    if hook_evidence and visual_evidence:
        angles.append(
            base_angle(
                candidate,
                gemini_evidence,
                claim_safety_review,
                evidence_quality,
                title="Digestive Comfort Routine Check",
                hook=f"Reframe the observed hook as a Nattome-safe question: {hook_evidence}",
                format_name="Talking-head explainer with simple on-screen text.",
                recommendation=(
                    "Open with the same problem moment, then move into routine support language instead of promises."
                ),
                source_evidence=["hook_evidence", "visual_observations"],
            )
        )

    if visible_text or claim_text:
        source_evidence = []
        if visible_text:
            source_evidence.append("visible_text")
        if claim_text:
            source_evidence.append("claim_evidence")
        text_anchor = visible_text or claim_text
        angles.append(
            base_angle(
                candidate,
                gemini_evidence,
                claim_safety_review,
                evidence_quality,
                title="On-Screen Claim Rewrite",
                hook=f"Turn `{text_anchor}` into a safer prompt about {caption}.",
                format_name="Text-led explainer with claim-safe overlays.",
                recommendation=(
                    "Keep the audience tension, remove unsupported outcomes, and use Nattome product-fit language."
                ),
                source_evidence=source_evidence,
            )
        )

    if audio_cue and spoken_content:
        angles.append(
            base_angle(
                candidate,
                gemini_evidence,
                claim_safety_review,
                evidence_quality,
                title="Voiceover Pattern Adaptation",
                hook=f"Use a calm voiceover opener based on: {spoken_content}",
                format_name="Voiceover with simple B-roll and product-safe captions.",
                recommendation=(
                    f"Borrow the audio pacing cue `{audio_cue}` while rewriting the advice for a digestive routine."
                ),
                source_evidence=["audio_cues", "spoken_content"],
            )
        )

    return angles[:3]
