from __future__ import annotations

from pathlib import Path
from typing import Any

def compact_markdown_text(value: Any, fallback: str = "Not available") -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    return " ".join(text.split())

def product_tie_in_for_candidate(candidate: dict[str, Any]) -> str:
    text = compact_markdown_text(candidate.get("caption"), "").lower()
    if any(term in text for term in ("reflux", "heartburn", "acid", "indigestion")):
        return "DR for faster relief moments around reflux, heartburn, or gastric discomfort."
    if any(term in text for term in ("repair", "recover", "recovery")):
        return "DH-R/recovery for deeper repair and recovery contexts."
    return "DH for daily digestive maintenance and routine support."

def avatar_for_candidate(candidate: dict[str, Any]) -> str:
    text = compact_markdown_text(candidate.get("caption"), "").lower()
    if any(term in text for term in ("reflux", "heartburn", "bloating", "gastric", "pain")):
        return "The Sufferer"
    if "family" in text or "child" in text:
        return "Family Caregiver"
    return "Maintainer"

def claim_guardrails(claim_review: dict[str, Any] | None) -> str:
    claims = claim_review.get("flagged_claims") if isinstance(claim_review, dict) else []
    if isinstance(claims, list) and claims:
        categories = ", ".join(
            sorted({str(claim.get("category")) for claim in claims if isinstance(claim, dict)})
        )
        return f"Do not reuse flagged claim categories directly: {categories}."
    return "Avoid cure, guaranteed outcome, overnight relief, detox, and unsupported clinical claims."


def timestamped_line(item: dict[str, Any], text_key: str, fallback: str = "Evidence captured") -> str:
    timestamp = item.get("timestamp_seconds", item.get("start_seconds"))
    text = compact_markdown_text(item.get(text_key), fallback)
    if timestamp is None:
        return f"- {text}"
    return f"- {timestamp}s: {text}"


def write_video_evidence_report_from_snapshot(
    report_path: Path,
    candidate: dict[str, Any],
    snapshot: dict[str, Any],
    gemini_evidence: dict[str, Any],
    audio_analysis: dict[str, Any],
    claim_review: dict[str, Any],
    quality: dict[str, Any],
    shootable_angles: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    quality_score = quality.get("evidence_quality_score") if isinstance(quality, dict) else {}
    manual_review = quality.get("manual_review_flag") if isinstance(quality, dict) else {}
    source_url = compact_markdown_text(candidate.get("url"), "")
    caption = compact_markdown_text(candidate.get("caption"))
    report_title = compact_markdown_text(candidate.get("id"), f"rank-{candidate.get('rank')}")
    source_video = snapshot.get("source_video") if isinstance(snapshot.get("source_video"), dict) else {}
    gemini_status = str(gemini_evidence.get("status") or "missing")
    gemini_reason = compact_markdown_text(
        gemini_evidence.get("reason"),
        "No Gemini evidence reason recorded",
    )

    lines = [
        f"# Video Evidence Report: {report_title}",
        "",
        "## Video Reference",
        "",
        f"- Source TikTok: [Source TikTok]({source_url})" if source_url else "- Source TikTok: Not available",
        f"- Caption: {caption}",
        f"- Creator: {compact_markdown_text(candidate.get('author_handle'))}",
        f"- Views: {candidate.get('play_count', 0)}",
        f"- Weighted engagement rate: {candidate.get('weighted_engagement_rate', 0)}",
        f"- Evidence Bundle Snapshot: `{snapshot.get('snapshot_path', 'snapshot unavailable')}`",
        f"- Source video state: {source_video.get('state', 'missing')}",
        "",
        "## Executive Creative Read",
        "",
        (
            f"- Evidence quality: {quality_score.get('level', 'unknown')} - "
            f"{quality_score.get('reason', 'No reason recorded')}"
        ),
        (
            f"- Manual review required: {manual_review.get('required', False)} "
            f"({', '.join(manual_review.get('reasons', [])) if isinstance(manual_review.get('reasons'), list) else 'no reasons'})"
        ),
        "- Recommendation: Treat this as evidence-led inspiration, not a final script.",
        "",
        "## Gemini Evidence State",
        "",
        f"- Status: {gemini_status}",
    ]
    if gemini_status not in {"completed", "partial"}:
        lines.append(f"- Gemini evidence not available: {gemini_reason}.")
    missing_sections = gemini_evidence.get("missing_evidence")
    if isinstance(missing_sections, list) and missing_sections:
        lines.append(f"- Missing sections: {', '.join(str(section) for section in missing_sections)}")

    lines.extend(["", "## First 3 Seconds Hook Audit", ""])
    hook_items = gemini_evidence.get("hook_evidence")
    if isinstance(hook_items, list) and hook_items:
        lines.extend(timestamped_line(item, "evidence") for item in hook_items if isinstance(item, dict))
    else:
        lines.append("- Hook clarity: uncertain because Gemini hook evidence is missing.")

    lines.extend(["", "## Visual Evidence", ""])
    visual_items = gemini_evidence.get("visual_observations")
    if isinstance(visual_items, list) and visual_items:
        lines.extend(timestamped_line(item, "observation") for item in visual_items if isinstance(item, dict))
    else:
        lines.append("- Visual observations are unavailable; do not infer scenes or creator actions.")

    lines.extend(["", "## Visible Text Evidence", ""])
    visible_text = gemini_evidence.get("visible_text")
    if isinstance(visible_text, list) and visible_text:
        lines.extend(timestamped_line(item, "text") for item in visible_text if isinstance(item, dict))
    else:
        lines.append("- Visible text evidence is unavailable; do not infer on-screen claims.")

    lines.extend(["", "## Spoken Content Evidence", ""])
    spoken_content = gemini_evidence.get("spoken_content")
    if isinstance(spoken_content, list) and spoken_content:
        lines.extend(timestamped_line(item, "text") for item in spoken_content if isinstance(item, dict))
    else:
        lines.append("- Spoken content evidence is unavailable; do not infer transcript claims.")

    lines.extend(["", "## Audio/Music Trend Analysis", ""])
    if isinstance(audio_analysis, dict) and audio_analysis.get("status") == "completed":
        lines.extend(
            [
                f"- Audio format: {audio_analysis.get('audio_format', 'unknown')}",
                f"- Mood: {audio_analysis.get('mood', 'unknown')}",
                f"- Hook support: {audio_analysis.get('hook_support', 'not available')}",
                f"- Nattome audio action: {audio_analysis.get('nattome_recommendation', {}).get('action', 'review')}",
            ]
        )
    else:
        lines.append("- Audio analysis requires manual review.")

    lines.extend(
        [
            "",
            "## Virality Breakdown",
            "",
            (
                f"- Viral signal: {candidate.get('play_count', 0)} views with "
                f"{candidate.get('weighted_engagement_rate', 0)} weighted engagement."
            ),
            f"- Nattome relevance score: {candidate.get('nattome_relevance_score', 0)}",
            "- Caution: Do not treat missing Gemini evidence as proof of a creative mechanism.",
            "",
            "## Shootable Angles",
            "",
        ]
    )
    angles = shootable_angles if isinstance(shootable_angles, list) else []
    if angles:
        for index, angle in enumerate(angles, start=1):
            if not isinstance(angle, dict):
                continue
            score = angle.get("priority_score") if isinstance(angle.get("priority_score"), dict) else {}
            lines.extend(
                [
                    f"### Angle {index}: {angle.get('angle_title', 'Shootable Angle')}",
                    "",
                    f"- Hook: {angle.get('hook', 'Not available')}",
                    f"- Avatar: {angle.get('avatar', 'Not available')}",
                    f"- Format: {angle.get('format', 'Not available')}",
                    f"- Product fit: {angle.get('product_fit', 'Not available')}",
                    f"- Recommendation: {angle.get('recommendation', 'Not available')}",
                    f"- Claim guardrails: {angle.get('claim_guardrails', 'Not available')}",
                    f"- Source evidence: {', '.join(angle.get('source_evidence', [])) if isinstance(angle.get('source_evidence'), list) else 'Not available'}",
                    f"- Nattome Priority Score: {score.get('total', 'unknown')}/{score.get('max_points', 30)}",
                    "",
                ]
            )
    else:
        lines.extend(
            [
                "No evidence-backed Shootable Angle was generated from this snapshot.",
                "",
            ]
        )

    lines.extend(["## Claim Safety Review", ""])
    claims = claim_review.get("flagged_claims") if isinstance(claim_review, dict) else []
    if isinstance(claims, list) and claims:
        for claim in claims:
            if not isinstance(claim, dict):
                continue
            guidance = claim.get("guidance") if isinstance(claim.get("guidance"), dict) else {}
            lines.append(
                f"- {claim.get('category')}: `{claim.get('claim_text')}` -> {guidance.get('action', 'review')}"
            )
    else:
        lines.append("- No unsafe claims were flagged from available Gemini evidence.")

    lines.extend(
        [
            "",
            "## Evidence Quality",
            "",
            f"- Score: {quality_score.get('level', 'unknown')}",
            f"- Reason: {quality_score.get('reason', 'No reason recorded')}",
            (
                f"- Manual review flag: {manual_review.get('required', False)} "
                f"({', '.join(manual_review.get('reasons', [])) if isinstance(manual_review.get('reasons'), list) else 'no reasons'})"
            ),
        ]
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": "completed"}


