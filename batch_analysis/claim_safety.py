from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

CLAIM_SAFETY_RULES = [
    {
        "category": "cure_claim",
        "patterns": [r"\bcures?\b", r"\bheals?\b", r"\beliminates?\b"],
        "action": "avoid",
        "reason": "Nattome should not reuse cure or disease-treatment promises.",
        "nattome_safe_language": "Talk about supporting digestive comfort and daily gut routines.",
    },
    {
        "category": "guaranteed_outcome",
        "patterns": [r"\bguarantee(?:d|s)?\b", r"\b100%\b", r"\bwill definitely\b"],
        "action": "soften",
        "reason": "Guaranteed outcomes overpromise individual results.",
        "nattome_safe_language": "Use possibility language such as may help support comfort.",
    },
    {
        "category": "one_night_fix",
        "patterns": [r"\bovernight\b", r"\bone[- ]night\b", r"\bin 24 hours\b"],
        "action": "reframe",
        "reason": "Fast-fix claims can imply unrealistic or unsubstantiated relief timing.",
        "nattome_safe_language": "Frame the angle around building a simple digestive routine.",
    },
    {
        "category": "cancer_prevention",
        "patterns": [r"\bprevent(?:s|ing)? cancer\b", r"\bstops? cancer\b", r"\bcancer prevention\b"],
        "action": "avoid",
        "reason": "Cancer prevention claims are high-risk medical claims.",
        "nattome_safe_language": "Do not connect Nattome content to cancer prevention.",
    },
    {
        "category": "zero_side_effect",
        "patterns": [r"\bzero side effects?\b", r"\bno side effects?\b", r"\bside-effect free\b"],
        "action": "avoid",
        "reason": "Absolute safety guarantees should not be reused without substantiation.",
        "nattome_safe_language": "Avoid safety guarantees; direct users to product labels and professional advice.",
    },
    {
        "category": "detox_or_cleanse",
        "patterns": [r"\bdetox(?:es|ing)?\b", r"\bcleanse(?:s|d|ing)?\b"],
        "action": "reframe",
        "reason": "Detox and cleanse language can sound pseudoscientific.",
        "nattome_safe_language": "Use digestive balance, comfort, or routine support language instead.",
    },
    {
        "category": "unverified_doctor_recommended",
        "patterns": [r"\bdoctor recommended\b", r"\brecommended by doctors?\b", r"\bdoctors? recommend\b"],
        "action": "soften",
        "reason": "Authority claims need verification before reuse.",
        "nattome_safe_language": "Use only verified professional endorsements approved for the campaign.",
    },
    {
        "category": "unsupported_clinical_percentage",
        "patterns": [
            r"\b\d{1,3}%[^.?!]*(?:clinically|proven|effective|results?|relief)",
            r"(?:clinically|proven|effective|results?|relief)[^.?!]*\b\d{1,3}%",
        ],
        "action": "avoid",
        "reason": "Clinical percentages require substantiation and approval.",
        "nattome_safe_language": "Remove unsupported percentages unless approved evidence is available.",
    },
    {
        "category": "aggressive_competitor_claim",
        "patterns": [
            r"\bbetter than (?:every |all )?competitors?\b",
            r"\bcompetitors? (?:are|is) (?:bad|toxic|useless)\b",
            r"\bstop buying\b",
        ],
        "action": "reframe",
        "reason": "Aggressive competitor claims can create brand and compliance risk.",
        "nattome_safe_language": "Compare consumer needs without attacking competitors.",
    },
]

def claim_evidence_sources_from_gemini(gemini_evidence: dict[str, Any]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for item in gemini_evidence.get("claim_evidence", []):
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if text:
            sources.append(
                {
                    "source": "gemini_claim_evidence",
                    "timestamp_seconds": item.get("timestamp_seconds"),
                    "text": text,
                }
            )
    for item in gemini_evidence.get("visible_text", []):
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if text:
            sources.append(
                {
                    "source": "gemini_visible_text",
                    "timestamp_seconds": item.get("timestamp_seconds"),
                    "text": text,
                }
            )
    for item in gemini_evidence.get("spoken_content", []):
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if text:
            sources.append(
                {
                    "source": "gemini_spoken_content",
                    "timestamp_seconds": item.get("start_seconds"),
                    "text": text,
                }
            )
    return sources

def first_matching_claim_text(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(0).strip()
    return None

def build_claim_safety_review_from_sources(
    sources: list[dict[str, Any]],
    source_artifacts: list[str],
) -> dict[str, Any]:
    flagged_claims = []
    seen_categories = set()

    for rule in CLAIM_SAFETY_RULES:
        for source in sources:
            claim_text = first_matching_claim_text(source["text"], rule["patterns"])
            if not claim_text or rule["category"] in seen_categories:
                continue
            seen_categories.add(rule["category"])
            flagged_claims.append(
                {
                    "category": rule["category"],
                    "claim_text": claim_text,
                    "evidence_source": {
                        "artifact": source["source"],
                        "timestamp_seconds": source["timestamp_seconds"],
                    },
                    "guidance": {
                        "action": rule["action"],
                        "reason": rule["reason"],
                        "nattome_safe_language": rule["nattome_safe_language"],
                    },
                }
            )
            break

    return {
        "status": "completed",
        "source_artifacts": source_artifacts,
        "flagged_claims": flagged_claims,
        "summary": {
            "flagged_count": len(flagged_claims),
            "guidance_actions": sorted(
                {claim["guidance"]["action"] for claim in flagged_claims}
            ),
        },
    }


def write_claim_safety_review_from_snapshot(
    review_path: Path,
    gemini_evidence: dict[str, Any],
) -> dict[str, Any]:
    sources = claim_evidence_sources_from_gemini(gemini_evidence)
    review = build_claim_safety_review_from_sources(
        sources,
        ["gemini_claim_evidence", "gemini_visible_text", "gemini_spoken_content"],
    )
    if gemini_evidence.get("status") not in {"completed", "partial"}:
        review["manual_review"] = {
            "required": True,
            "reason": gemini_evidence.get("reason") or "Gemini claim evidence is unavailable",
        }
    elif not sources:
        review["manual_review"] = {
            "required": True,
            "reason": "Gemini claim, visible text, and spoken content evidence are empty",
        }
    else:
        review["manual_review"] = {"required": False, "reason": None}

    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(
        json.dumps(review, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {
        "status": review["status"],
        "flagged_count": len(review["flagged_claims"]),
        "manual_review_required": review["manual_review"]["required"],
    }

