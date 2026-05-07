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


