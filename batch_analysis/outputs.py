from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

from .evidence_io import read_json_object
from .reports import (
    avatar_for_candidate,
    claim_guardrails,
    compact_markdown_text,
    product_tie_in_for_candidate,
)


def output_json_path(run_folder: Path, filename: str) -> Path:
    path = run_folder / "data" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def output_report_path(run_folder: Path, filename: str) -> Path:
    path = run_folder / "reports" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def relative_output_path(path: Path, run_folder: Path) -> str:
    return str(path.relative_to(run_folder)).replace("\\", "/")


def bundle_artifact_path(
    run_folder: Path,
    bundle: dict[str, Any],
    artifact_name: str,
    legacy_filename: str,
) -> Path:
    artifacts = bundle.get("artifacts") if isinstance(bundle.get("artifacts"), dict) else {}
    artifact = artifacts.get(artifact_name) if isinstance(artifacts, dict) else None
    if isinstance(artifact, dict) and artifact.get("path"):
        return run_folder / str(artifact["path"])

    bundle_folder = bundle.get("bundle_folder")
    if bundle_folder:
        return run_folder / str(bundle_folder) / legacy_filename

    prefix = bundle.get("prefix")
    if prefix:
        return run_folder / "data" / f"{prefix}_{legacy_filename}"

    return run_folder / legacy_filename


def read_bundle_artifact(
    run_folder: Path,
    bundle: dict[str, Any],
    artifact_name: str,
    legacy_filename: str,
) -> dict[str, Any] | None:
    return read_json_object(
        bundle_artifact_path(run_folder, bundle, artifact_name, legacy_filename)
    )


def source_metadata_for_bundle(
    run_folder: Path,
    bundle: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    source_metadata = bundle.get("source_metadata")
    if isinstance(source_metadata, dict) and source_metadata.get("path"):
        loaded = read_json_object(run_folder / str(source_metadata["path"]))
        return loaded or candidate
    if isinstance(source_metadata, str):
        loaded = read_json_object(run_folder / source_metadata)
        return loaded or candidate

    bundle_folder = bundle.get("bundle_folder")
    if bundle_folder:
        loaded = read_json_object(run_folder / str(bundle_folder) / "source_metadata.json")
        return loaded or candidate
    return candidate


def shootable_angles_for_bundle(
    run_folder: Path,
    bundle: dict[str, Any],
) -> list[dict[str, Any]]:
    loaded = read_bundle_artifact(
        run_folder,
        bundle,
        "shootable_angles",
        "shootable_angles.json",
    )
    angles = loaded.get("angles") if isinstance(loaded, dict) else []
    if not isinstance(angles, list):
        return []
    return [angle for angle in angles if isinstance(angle, dict)]


def write_selected_batch(run_folder: Path, selected_batch: dict[str, Any]) -> None:
    json_path = output_json_path(run_folder, "selected_batch.json")
    json_path.write_text(
        json.dumps(selected_batch, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Selected Batch Preview",
        "",
        f"- Selected at: {selected_batch['selected_at']}",
        f"- Requested batch size: {selected_batch['requested_batch_size']}",
        f"- Input candidates: {selected_batch['input_candidate_count']}",
        f"- Eligible candidates: {selected_batch['eligible_candidate_count']}",
        f"- Selected candidates: {selected_batch['selected_candidate_count']}",
        "",
        "| Rank | ID | Views | Weighted ER | Relevance | Score | URL |",
        "|---:|---|---:|---:|---:|---:|---|",
    ]
    for candidate in selected_batch["selected_candidates"]:
        lines.append(
            "| {rank} | {id} | {views} | {er:.4f} | {relevance:.4f} | {score:.4f} | {url} |".format(
                rank=candidate["rank"],
                id=candidate["id"],
                views=candidate["play_count"],
                er=candidate["weighted_engagement_rate"],
                relevance=candidate["nattome_relevance_score"],
                score=candidate["selection_score"],
                url=candidate["url"],
            )
        )
    lines.extend(["", "## Excluded Candidates", ""])
    for candidate in selected_batch["excluded_candidates"]:
        lines.append(f"- `{candidate['id']}`: {candidate['reason']}")

    markdown_path = output_report_path(run_folder, "selected_batch.md")
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

PRIORITY_SCORE_DIMENSIONS = [
    "viral_strength",
    "nattome_relevance",
    "evidence_confidence",
    "brand_safety",
    "ease_of_production",
    "product_fit",
]

def priority_score_points(candidate: dict[str, Any], bundle_folder: Path) -> dict[str, int]:
    quality = read_json_object(bundle_folder / "evidence_quality.json") or {}
    claim_review = read_json_object(bundle_folder / "claim_safety_review.json") or {}
    audio_analysis = read_json_object(bundle_folder / "baseline_audio_analysis.json") or {}
    return priority_score_points_from_artifacts(candidate, quality, claim_review, audio_analysis)


def priority_score_points_from_artifacts(
    candidate: dict[str, Any],
    quality: dict[str, Any] | None,
    claim_review: dict[str, Any] | None,
    audio_analysis: dict[str, Any] | None,
) -> dict[str, int]:
    quality = quality or {}
    claim_review = claim_review or {}
    audio_analysis = audio_analysis or {}

    views = int(candidate.get("play_count") or 0)
    engagement = float(candidate.get("weighted_engagement_rate") or 0)
    viral_strength = 1
    if views >= 250000 or engagement >= 0.15:
        viral_strength = 5
    elif views >= 100000 or engagement >= 0.10:
        viral_strength = 4
    elif views >= 50000 or engagement >= 0.06:
        viral_strength = 3
    elif views >= 10000 or engagement >= 0.03:
        viral_strength = 2

    relevance = float(candidate.get("nattome_relevance_score") or 0)
    nattome_relevance = max(1, min(5, math.ceil(relevance * 5)))

    quality_score = quality.get("evidence_quality_score") if isinstance(quality, dict) else {}
    quality_level = quality_score.get("level") if isinstance(quality_score, dict) else None
    evidence_confidence = {"high": 5, "medium": 3, "low": 1}.get(str(quality_level), 1)

    flagged_claims = claim_review.get("flagged_claims") if isinstance(claim_review, dict) else []
    flagged_count = len(flagged_claims) if isinstance(flagged_claims, list) else 0
    brand_safety = 5 if flagged_count == 0 else 3 if flagged_count <= 2 else 1

    audio_format = str(audio_analysis.get("audio_format") or candidate.get("audio_format_hint") or "").lower()
    if audio_format in {"talking_head", "voiceover", "original_voice"}:
        ease_of_production = 5
    elif audio_format in {"reused_sound", "music_only"}:
        ease_of_production = 3
    else:
        ease_of_production = 4

    product_fit_text = product_tie_in_for_candidate(candidate).lower()
    if any(product in product_fit_text for product in ("dr", "dh-r", "dh ")):
        product_fit = 5 if relevance >= 0.5 else 4
    else:
        product_fit = 3

    return {
        "viral_strength": viral_strength,
        "nattome_relevance": nattome_relevance,
        "evidence_confidence": evidence_confidence,
        "brand_safety": brand_safety,
        "ease_of_production": ease_of_production,
        "product_fit": product_fit,
    }

def hook_pattern_for_bundle(bundle_folder: Path) -> str:
    quality = read_json_object(bundle_folder / "evidence_quality.json") or {}
    return hook_pattern_from_quality(quality)


def hook_pattern_from_quality(quality: dict[str, Any]) -> str:
    checks = quality.get("checks") if isinstance(quality, dict) else {}
    hook_check = checks.get("first_three_second_hook") if isinstance(checks, dict) else {}
    if isinstance(hook_check, dict) and hook_check.get("clear"):
        return "Clear first-three-second problem hook"
    return "Unclear hook requiring manual review"

def emotional_trigger_for_candidate(candidate: dict[str, Any]) -> str:
    text = compact_markdown_text(candidate.get("caption"), "").lower()
    if any(term in text for term in ("bloating", "reflux", "heartburn", "pain", "gastric")):
        return "Digestive discomfort relief"
    if any(term in text for term in ("routine", "daily", "morning", "after meals")):
        return "Routine confidence"
    if any(term in text for term in ("warning", "mistake", "avoid")):
        return "Problem avoidance"
    return "Digestive-health curiosity"

def add_pattern(patterns: dict[str, set[str]], pattern: str, candidate_id: str) -> None:
    patterns.setdefault(pattern, set()).add(candidate_id)

def pattern_rows(patterns: dict[str, set[str]]) -> list[dict[str, Any]]:
    return [
        {
            "pattern": pattern,
            "video_count": len(candidate_ids),
            "candidate_ids": sorted(candidate_ids),
        }
        for pattern, candidate_ids in sorted(
            patterns.items(), key=lambda item: (-len(item[1]), item[0])
        )
    ]

def write_cross_video_pattern_summary(
    run_folder: Path,
    selected_batch: dict[str, Any],
    evidence_index: dict[str, Any],
) -> dict[str, Any]:
    hooks: dict[str, set[str]] = {}
    formats: dict[str, set[str]] = {}
    emotional_triggers: dict[str, set[str]] = {}
    audio_patterns: dict[str, set[str]] = {}
    risky_claims: dict[str, set[str]] = {}
    opportunities: dict[str, set[str]] = {}
    angle_rows = []

    candidates_by_id = {
        str(candidate.get("id")): candidate
        for candidate in selected_batch.get("selected_candidates", [])
        if isinstance(candidate, dict)
    }

    for bundle in evidence_index.get("bundles", []):
        if not isinstance(bundle, dict):
            continue
        candidate_id = str(bundle.get("candidate_id") or "")
        candidate = candidates_by_id.get(candidate_id)
        if not isinstance(candidate, dict):
            continue

        audio_analysis = (
            read_bundle_artifact(
                run_folder,
                bundle,
                "baseline_audio_analysis",
                "baseline_audio_analysis.json",
            )
            or {}
        )
        claim_review = (
            read_bundle_artifact(
                run_folder,
                bundle,
                "claim_safety_review",
                "claim_safety_review.json",
            )
            or {}
        )
        quality = (
            read_bundle_artifact(
                run_folder,
                bundle,
                "evidence_quality",
                "evidence_quality.json",
            )
            or {}
        )

        audio_format = str(
            audio_analysis.get("audio_format") or candidate.get("audio_format_hint") or "unknown"
        )
        hook_pattern = hook_pattern_from_quality(quality)
        emotional_trigger = emotional_trigger_for_candidate(candidate)
        opportunity = product_tie_in_for_candidate(candidate)
        add_pattern(hooks, hook_pattern, candidate_id)
        add_pattern(formats, audio_format, candidate_id)
        add_pattern(emotional_triggers, emotional_trigger, candidate_id)
        add_pattern(
            audio_patterns,
            str(audio_analysis.get("hook_support") or "audio hook support not available"),
            candidate_id,
        )
        add_pattern(opportunities, opportunity, candidate_id)

        claims = claim_review.get("flagged_claims") if isinstance(claim_review, dict) else []
        if isinstance(claims, list) and claims:
            for claim in claims:
                if isinstance(claim, dict):
                    add_pattern(risky_claims, str(claim.get("category") or "unknown"), candidate_id)
        else:
            add_pattern(risky_claims, "No risky claims flagged from available evidence", candidate_id)

        quality_score = quality.get("evidence_quality_score") if isinstance(quality, dict) else {}
        for angle in shootable_angles_for_bundle(run_folder, bundle):
            priority_score = angle.get("priority_score") if isinstance(angle.get("priority_score"), dict) else {}
            dimensions = priority_score.get("dimensions") if isinstance(priority_score, dict) else {}
            if not isinstance(dimensions, dict) or not dimensions:
                dimensions = priority_score_points_from_artifacts(
                    candidate,
                    quality,
                    claim_review,
                    audio_analysis,
                )
            total = priority_score.get("total") if isinstance(priority_score, dict) else None
            if not isinstance(total, int):
                total = sum(value for value in dimensions.values() if isinstance(value, int))
            angle_rows.append(
                {
                "candidate_id": candidate_id,
                "source_tiktok_url": candidate.get("url"),
                "angle_title": angle.get("angle_title") or "Shootable Angle",
                "hook": angle.get("hook") or "",
                "avatar": angle.get("avatar") or avatar_for_candidate(candidate),
                "format": angle.get("format") or "",
                "product_fit": angle.get("product_fit") or opportunity,
                "recommended_angle": angle.get("recommendation")
                or angle.get("recommended_angle")
                or "",
                "claim_guardrails": angle.get("claim_guardrails") or claim_guardrails(claim_review),
                "source_evidence": angle.get("source_evidence")
                if isinstance(angle.get("source_evidence"), list)
                else [],
                "evidence_quality": quality_score.get("level", "unknown")
                if isinstance(quality_score, dict)
                else "unknown",
                "priority_score": {
                    "dimensions": dimensions,
                    "total": total,
                    "max_points": priority_score.get("max_points", 30)
                    if isinstance(priority_score, dict)
                    else 30,
                },
                "why": (
                    f"{total}/30 score balances viral signal, Nattome fit, evidence confidence, "
                    "brand safety, and production ease."
                ),
                }
            )

    angle_rows.sort(
        key=lambda row: (
            -int(row["priority_score"]["total"]),
            str(row["candidate_id"]),
        )
    )
    for rank, angle in enumerate(angle_rows, start=1):
        angle["rank"] = rank

    top_angle = angle_rows[0] if angle_rows else None
    recommendation = {
        "what_to_shoot_first": top_angle["angle_title"] if top_angle else "No shootable angle available",
        "candidate_id": top_angle["candidate_id"] if top_angle else None,
        "why": top_angle["why"] if top_angle else "No selected videos were available to score.",
    }

    summary = {
        "created_at": selected_batch.get("selected_at"),
        "source_video_count": len(evidence_index.get("bundles", [])),
        "priority_score_dimensions": PRIORITY_SCORE_DIMENSIONS,
        "pattern_comparison": {
            "hooks": pattern_rows(hooks),
            "formats": pattern_rows(formats),
            "emotional_triggers": pattern_rows(emotional_triggers),
            "audio_patterns": pattern_rows(audio_patterns),
            "risky_claims": pattern_rows(risky_claims),
            "nattome_opportunities": pattern_rows(opportunities),
        },
        "top_priority_shootable_angles": angle_rows,
        "recommendation": recommendation,
    }

    json_path = output_json_path(run_folder, "cross_video_pattern_summary.json")
    json_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Cross-Video Pattern Summary",
        "",
        f"- Source videos compared: {summary['source_video_count']}",
        "- Nattome Priority Score: six dimensions, five points each, total out of 30.",
        "",
        "## Cross-Video Pattern Comparison",
        "",
    ]
    section_titles = {
        "hooks": "Hooks",
        "formats": "Formats",
        "emotional_triggers": "Emotional Triggers",
        "audio_patterns": "Audio Patterns",
        "risky_claims": "Risky Claims",
        "nattome_opportunities": "Nattome Opportunities",
    }
    for key, title in section_titles.items():
        lines.extend([f"### {title}", ""])
        rows = summary["pattern_comparison"][key]
        if rows:
            for row in rows:
                lines.append(
                    f"- {row['pattern']}: {row['video_count']} video(s) ({', '.join(row['candidate_ids'])})"
                )
        else:
            lines.append("- No pattern available.")
        lines.append("")

    lines.extend(["## Top Priority Shootable Angles", ""])
    if angle_rows:
        lines.extend(
            [
                "| Rank | Candidate | Nattome Priority Score | Avatar | Product Fit | Recommended Angle |",
                "|---:|---|---:|---|---|---|",
            ]
        )
        for angle in angle_rows:
            lines.append(
                "| {rank} | {candidate} | {score}/30 | {avatar} | {product_fit} | {recommended} |".format(
                    rank=angle["rank"],
                    candidate=angle["candidate_id"],
                    score=angle["priority_score"]["total"],
                    avatar=angle["avatar"],
                    product_fit=angle["product_fit"],
                    recommended=angle["recommended_angle"],
                )
            )
    else:
        lines.append("No shootable angles were available.")

    lines.extend(
        [
            "",
            "## What To Shoot First",
            "",
            f"- Shoot first: {recommendation['what_to_shoot_first']}",
            f"- Candidate: {recommendation['candidate_id'] or 'Not available'}",
            f"- Why: {recommendation['why']}",
        ]
    )

    markdown_path = output_report_path(run_folder, "cross_video_pattern_summary.md")
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": "completed", "top_angle_count": len(angle_rows), "summary": summary}

def first_angle_by_candidate(cross_video_summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    angles = cross_video_summary.get("top_priority_shootable_angles")
    if not isinstance(angles, list):
        return {}
    by_candidate = {}
    for angle in angles:
        if not isinstance(angle, dict):
            continue
        candidate_id = str(angle.get("candidate_id") or "")
        if candidate_id and candidate_id not in by_candidate:
            by_candidate[candidate_id] = angle
    return by_candidate

def write_structured_json_and_spreadsheet_summary(
    run_folder: Path,
    selected_batch: dict[str, Any],
    evidence_index: dict[str, Any],
    metadata: dict[str, Any],
    cross_video_summary: dict[str, Any],
) -> dict[str, Any]:
    candidates_by_id = {
        str(candidate.get("id")): candidate
        for candidate in selected_batch.get("selected_candidates", [])
        if isinstance(candidate, dict)
    }
    angles_by_candidate = first_angle_by_candidate(cross_video_summary)
    videos = []
    spreadsheet_rows = []

    for bundle in evidence_index.get("bundles", []):
        if not isinstance(bundle, dict):
            continue
        candidate_id = str(bundle.get("candidate_id") or "")
        candidate = candidates_by_id.get(candidate_id)
        if not isinstance(candidate, dict):
            continue

        timeline = read_bundle_artifact(run_folder, bundle, "hybrid_timeline", "hybrid_timeline.json")
        ocr = read_bundle_artifact(run_folder, bundle, "ocr_evidence", "ocr_evidence.json")
        transcript = read_bundle_artifact(
            run_folder, bundle, "transcript_evidence", "transcript_evidence.json"
        )
        audio_analysis = read_bundle_artifact(
            run_folder,
            bundle,
            "baseline_audio_analysis",
            "baseline_audio_analysis.json",
        )
        claim_review = read_bundle_artifact(
            run_folder,
            bundle,
            "claim_safety_review",
            "claim_safety_review.json",
        )
        quality = read_bundle_artifact(run_folder, bundle, "evidence_quality", "evidence_quality.json")
        gemini_evidence = read_bundle_artifact(
            run_folder,
            bundle,
            "gemini_evidence",
            "gemini_evidence.json",
        )
        angle = angles_by_candidate.get(candidate_id, {})
        quality_score = quality.get("evidence_quality_score") if isinstance(quality, dict) else {}
        manual_review = quality.get("manual_review_flag") if isinstance(quality, dict) else {}
        priority_score = angle.get("priority_score") if isinstance(angle, dict) else None
        if not isinstance(priority_score, dict):
            priority_score = {
                "dimensions": priority_score_points_from_artifacts(
                    candidate,
                    quality,
                    claim_review,
                    audio_analysis,
                ),
                "total": 0,
                "max_points": 30,
            }
            priority_score["total"] = sum(priority_score["dimensions"].values())

        hook_type = hook_pattern_from_quality(quality or {})
        audio_format = "unknown"
        if isinstance(audio_analysis, dict):
            audio_format = str(audio_analysis.get("audio_format") or audio_format)
        if audio_format == "unknown":
            audio_format = str(candidate.get("audio_format_hint") or "unknown")

        emotional_trigger = emotional_trigger_for_candidate(candidate)
        product_fit = str(angle.get("product_fit") or product_tie_in_for_candidate(candidate))
        recommended_angle = str(angle.get("angle_title") or "")
        avatar = str(angle.get("avatar") or avatar_for_candidate(candidate))

        videos.append(
            {
                "candidate_id": candidate_id,
                "source_metadata": source_metadata_for_bundle(run_folder, bundle, candidate),
                "evidence_bundle_index": bundle,
                "gemini_evidence": gemini_evidence,
                "hybrid_timeline": timeline,
                "ocr_evidence": ocr,
                "transcript_evidence": transcript,
                "audio_analysis": audio_analysis,
                "virality_analysis": {
                    "views": candidate.get("play_count", 0),
                    "weighted_engagement_rate": candidate.get("weighted_engagement_rate", 0),
                    "selection_score": candidate.get("selection_score", 0),
                    "nattome_relevance_score": candidate.get("nattome_relevance_score", 0),
                },
                "claim_safety_review": claim_review,
                "quality_score": quality_score,
                "manual_review_flag": manual_review,
                "shootable_angles": [angle] if isinstance(angle, dict) and angle else [],
                "nattome_priority_score": priority_score,
            }
        )
        spreadsheet_rows.append(
            {
                "link": candidate.get("url") or "",
                "topic": compact_markdown_text(candidate.get("caption")),
                "hook_type": hook_type,
                "format": audio_format,
                "emotional_trigger": emotional_trigger,
                "avatar": avatar,
                "product_fit": product_fit,
                "priority_score": priority_score["total"],
                "evidence_quality": quality_score.get("level", "unknown")
                if isinstance(quality_score, dict)
                else "unknown",
                "recommended_angle": recommended_angle,
            }
        )

    structured = {
        "batch_metadata": metadata,
        "selection_decisions": selected_batch,
        "evidence_bundle_index": evidence_index,
        "cross_video_pattern_summary": cross_video_summary,
        "videos": videos,
    }
    structured_path = output_json_path(run_folder, "structured_batch_analysis.json")
    structured_path.write_text(
        json.dumps(structured, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    spreadsheet_path = output_json_path(run_folder, "spreadsheet_summary.csv")
    fieldnames = [
        "link",
        "topic",
        "hook_type",
        "format",
        "emotional_trigger",
        "avatar",
        "product_fit",
        "priority_score",
        "evidence_quality",
        "recommended_angle",
    ]
    with spreadsheet_path.open("w", newline="", encoding="utf-8") as spreadsheet_file:
        writer = csv.DictWriter(spreadsheet_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(spreadsheet_rows)

    return {
        "status": "completed",
        "structured_json_path": relative_output_path(structured_path, run_folder),
        "spreadsheet_path": relative_output_path(spreadsheet_path, run_folder),
        "row_count": len(spreadsheet_rows),
    }

