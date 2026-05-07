from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .evidence_io import read_json_object

def compact_markdown_text(value: Any, fallback: str = "Not available") -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    return " ".join(text.split())

def report_status_line(artifact: dict[str, Any] | None, artifact_name: str) -> str:
    if not isinstance(artifact, dict):
        return f"{artifact_name} evidence not available."
    status = artifact.get("status", "missing")
    if status in {"completed", "extracted", "downloaded"}:
        return f"{artifact_name} evidence captured in `{artifact_name}.json`."
    reason = compact_markdown_text(artifact.get("reason"), "No reason recorded")
    return f"{artifact_name} evidence not available: {reason}."

def first_ocr_summary(ocr: dict[str, Any] | None) -> str:
    if not isinstance(ocr, dict) or ocr.get("status") != "completed":
        return report_status_line(ocr, "OCR")
    summary = ocr.get("summary") if isinstance(ocr.get("summary"), dict) else {}
    combined = compact_markdown_text(summary.get("combined_text"), "No OCR text captured")
    return (
        f"OCR completed across {summary.get('frame_count', 0)} frame(s); "
        f"{summary.get('text_frame_count', 0)} frame(s) contained text. Summary: {combined}"
    )

def first_transcript_summary(transcript: dict[str, Any] | None) -> str:
    if not isinstance(transcript, dict) or transcript.get("status") != "completed":
        return report_status_line(transcript, "Transcript")
    summary = transcript.get("summary") if isinstance(transcript.get("summary"), dict) else {}
    combined = compact_markdown_text(summary.get("combined_text"), "No transcript text captured")
    language = transcript.get("language_detected") or "not detected"
    return (
        f"Transcript completed with language `{language}` and "
        f"{summary.get('segment_count', 0)} segment(s). Summary: {combined}"
    )

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

def write_video_evidence_report(
    bundle_folder: Path,
    candidate: dict[str, Any],
) -> dict[str, Any]:
    report_path = bundle_folder / "video_evidence_report.md"
    download_status = read_json_object(bundle_folder / "download_status.json")
    timeline = read_json_object(bundle_folder / "hybrid_timeline.json")
    ocr = read_json_object(bundle_folder / "ocr_evidence.json")
    transcript = read_json_object(bundle_folder / "transcript_evidence.json")
    audio_analysis = read_json_object(bundle_folder / "baseline_audio_analysis.json")
    claim_review = read_json_object(bundle_folder / "claim_safety_review.json")
    quality = read_json_object(bundle_folder / "evidence_quality.json")

    quality_score = quality.get("evidence_quality_score") if isinstance(quality, dict) else {}
    manual_review = quality.get("manual_review_flag") if isinstance(quality, dict) else {}
    checks = quality.get("checks") if isinstance(quality, dict) else {}
    first_three_check = (
        checks.get("first_three_second_hook") if isinstance(checks, dict) else {}
    )
    source_url = compact_markdown_text(candidate.get("url"), "")
    caption = compact_markdown_text(candidate.get("caption"))
    report_title = compact_markdown_text(candidate.get("id"), f"rank-{candidate.get('rank')}")

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
        f"- Evidence Bundle: `{bundle_folder.name}/`",
        (
            "- Local evidence artifacts: `source_metadata.json`, `download_status.json`, "
            "`hybrid_timeline.json`, `ocr_evidence.json`, `transcript_evidence.json`, "
            "`baseline_audio_analysis.json`, `claim_safety_review.json`, `evidence_quality.json`"
        ),
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
        "## First 3 Seconds Hook Audit",
        "",
        (
            "- Hook clarity: clear based on captured evidence."
            if isinstance(first_three_check, dict) and first_three_check.get("clear")
            else "- Hook clarity: unclear from captured evidence."
        ),
    ]

    if not (isinstance(timeline, dict) and timeline.get("status") == "extracted"):
        lines.append("- This report does not claim video evidence was inspected because required artifacts are missing.")

    lines.extend(["", "## Hybrid Timeline", ""])
    if isinstance(timeline, dict) and timeline.get("status") == "extracted":
        lines.extend(["| Time | Frame | Sampling reason |", "| --- | --- | --- |"])
        for frame in timeline.get("frames", [])[:12]:
            if not isinstance(frame, dict):
                continue
            lines.append(
                f"| {frame.get('timestamp_seconds')} | `{frame.get('frame_path')}` | {frame.get('sampling_reason')} |"
            )
    else:
        reason = compact_markdown_text(
            timeline.get("reason") if isinstance(timeline, dict) else None,
            "artifact missing",
        )
        lines.append(f"Hybrid timeline evidence not available: {reason}.")

    lines.extend(
        [
            "",
            "## OCR Text Summary",
            "",
            first_ocr_summary(ocr),
            "",
            "## Speech Transcript Summary",
            "",
            first_transcript_summary(transcript),
            "",
            "## Audio/Music Trend Analysis",
            "",
        ]
    )
    if isinstance(audio_analysis, dict) and audio_analysis.get("status") == "completed":
        lines.extend(
            [
                f"- Audio format: {audio_analysis.get('audio_format', 'unknown')}",
                f"- Mood: {audio_analysis.get('mood', 'unknown')}",
                f"- Hook support: {audio_analysis.get('hook_support', 'not available')}",
                f"- Nattome audio action: {audio_analysis.get('nattome_recommendation', {}).get('action', 'review')}",
                "- Artifact: `baseline_audio_analysis.json`",
            ]
        )
    else:
        lines.append("Audio analysis evidence not available.")

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
            "- Caution: Do not treat missing media evidence as proof of a creative mechanism.",
            "",
            "## Nattome POV",
            "",
            f"- Product fit: {product_tie_in_for_candidate(candidate)}",
            "- Reuse stance: Adapt the topic and structure only after claim guardrails are applied.",
            "",
            "## Shootable Angles",
            "",
            "### Angle 1: Digestive Comfort Routine Check",
            "",
            f"- Hook: Turn the creator topic into a safe question: `{caption}`",
            f"- Avatar: {avatar_for_candidate(candidate)}",
            "- Format: Talking-head explainer with simple on-screen text.",
            f"- Product tie-in: {product_tie_in_for_candidate(candidate)}",
            "- Script beats: problem moment; simple routine cue; product-safe support language; reminder to read labels.",
            "- CTA: Save this for your next meal routine.",
            f"- Claim guardrails: {claim_guardrails(claim_review)}",
            "",
            "## Claim Safety Review",
            "",
            "- Artifact: `claim_safety_review.json`",
        ]
    )
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
        lines.append("- No unsafe claims were flagged from available OCR or transcript evidence.")

    lines.extend(
        [
            "",
            "## Evidence Quality",
            "",
            "- Artifact: `evidence_quality.json`",
            f"- Score: {quality_score.get('level', 'unknown')}",
            f"- Reason: {quality_score.get('reason', 'No reason recorded')}",
            (
                f"- Manual review flag: {manual_review.get('required', False)} "
                f"({', '.join(manual_review.get('reasons', [])) if isinstance(manual_review.get('reasons'), list) else 'no reasons'})"
            ),
        ]
    )

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": "completed"}


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
            "## Nattome POV",
            "",
            f"- Product fit: {product_tie_in_for_candidate(candidate)}",
            "- Reuse stance: Adapt the topic and structure only after claim guardrails are applied.",
            "",
            "## Shootable Angles",
            "",
            "### Angle 1: Digestive Comfort Routine Check",
            "",
            f"- Hook: Turn the creator topic into a safe question: `{caption}`",
            f"- Avatar: {avatar_for_candidate(candidate)}",
            "- Format: Talking-head explainer with simple on-screen text.",
            f"- Product tie-in: {product_tie_in_for_candidate(candidate)}",
            "- Script beats: problem moment; simple routine cue; product-safe support language; reminder to read labels.",
            "- CTA: Save this for your next meal routine.",
            f"- Claim guardrails: {claim_guardrails(claim_review)}",
            "",
            "## Claim Safety Review",
            "",
        ]
    )
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


