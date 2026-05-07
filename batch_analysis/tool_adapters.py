from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse
from urllib.request import urlopen


GEMINI_FLASH_MODEL = "gemini-2.5-flash"


def source_video_filename(source: str) -> str:
    parsed = urlparse(source)
    suffix = Path(unquote(parsed.path)).suffix if parsed.scheme else Path(source).suffix
    return f"source_video{suffix or '.mp4'}"


def copy_or_download_video(source: str, destination: Path) -> dict[str, Any]:
    if not source:
        return {
            "status": "missing",
            "reason": "no downloadable video source was provided in candidate metadata",
        }

    parsed = urlparse(source)
    try:
        if parsed.scheme in ("http", "https"):
            with urlopen(source, timeout=60) as response:
                destination.write_bytes(response.read())
        else:
            source_path = Path(unquote(parsed.path)) if parsed.scheme == "file" else Path(source)
            if not source_path.exists():
                return {
                    "status": "failed",
                    "reason": f"download source does not exist: {source}",
                    "source": source,
                }
            shutil.copyfile(source_path, destination)
    except Exception as exc:
        return {
            "status": "failed",
            "reason": str(exc),
            "source": source,
        }

    return {
        "status": "downloaded",
        "source": source,
        "artifact": destination.name,
        "bytes": destination.stat().st_size,
    }


def timestamp_value(item: dict[str, Any], *keys: str) -> int | float | None:
    for key in keys:
        if key not in item:
            continue
        value = item.get(key)
        if value is None or value == "":
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        return int(numeric) if numeric.is_integer() else numeric
    return None


def normalize_visual_observation(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp_seconds": timestamp_value(item, "timestamp_seconds", "timestamp", "time"),
        "observation": str(
            item.get("observation")
            or item.get("description")
            or item.get("text")
            or ""
        ).strip(),
        "confidence": item.get("confidence"),
    }


def normalize_visible_text(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp_seconds": timestamp_value(item, "timestamp_seconds", "timestamp", "time"),
        "text": str(item.get("text") or item.get("ocr_text") or "").strip(),
        "confidence": item.get("confidence"),
        "source": "visible_text",
    }


def normalize_spoken_content(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "start_seconds": timestamp_value(item, "start_seconds", "start", "timestamp_seconds"),
        "end_seconds": timestamp_value(item, "end_seconds", "end"),
        "text": str(item.get("text") or item.get("transcript") or "").strip(),
        "language": item.get("language"),
        "confidence": item.get("confidence"),
    }


def normalize_audio_cue(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp_seconds": timestamp_value(item, "timestamp_seconds", "timestamp", "time"),
        "cue": str(item.get("cue") or item.get("description") or item.get("text") or "").strip(),
        "confidence": item.get("confidence"),
    }


def normalize_hook_evidence(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp_seconds": timestamp_value(item, "timestamp_seconds", "timestamp", "time"),
        "evidence": str(item.get("evidence") or item.get("description") or item.get("text") or "").strip(),
        "source": item.get("source"),
        "confidence": item.get("confidence"),
    }


def normalize_claim_evidence(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp_seconds": timestamp_value(item, "timestamp_seconds", "timestamp", "time"),
        "text": str(item.get("text") or item.get("claim") or "").strip(),
        "source": item.get("source"),
        "confidence": item.get("confidence"),
    }


EVIDENCE_NORMALIZERS = {
    "visual_observations": normalize_visual_observation,
    "visible_text": normalize_visible_text,
    "spoken_content": normalize_spoken_content,
    "audio_cues": normalize_audio_cue,
    "hook_evidence": normalize_hook_evidence,
    "claim_evidence": normalize_claim_evidence,
}


class GeminiFlashAdapter:
    def __init__(
        self,
        *,
        model: str = GEMINI_FLASH_MODEL,
        api_key: str | None = None,
        api_key_env: str = "GEMINI_API_KEY",
        client: Any | None = None,
    ):
        self.model = model
        self.api_key = api_key
        self.api_key_env = api_key_env
        self.client = client

    def configured_api_key(self) -> str:
        return self.api_key if self.api_key is not None else os.environ.get(self.api_key_env, "")

    def analyze_source_video(
        self,
        source_video_path: Path,
        candidate_context: dict[str, Any],
    ) -> dict[str, Any]:
        api_key = self.configured_api_key()
        if not api_key:
            return {
                "status": "missing_credentials",
                "model": self.model,
                "reason": f"Gemini API key is missing; set {self.api_key_env}",
                "visual_observations": [],
                "visible_text": [],
                "spoken_content": [],
                "audio_cues": [],
                "hook_evidence": [],
                "claim_evidence": [],
                "missing_evidence": list(EVIDENCE_NORMALIZERS),
            }
        if self.client is None:
            return {
                "status": "failed",
                "model": self.model,
                "reason": "No Gemini client is configured for this run",
                "visual_observations": [],
                "visible_text": [],
                "spoken_content": [],
                "audio_cues": [],
                "hook_evidence": [],
                "claim_evidence": [],
                "missing_evidence": list(EVIDENCE_NORMALIZERS),
            }

        try:
            response = self.client.analyze_video(
                model=self.model,
                api_key=api_key,
                source_video_path=source_video_path,
                candidate_context=candidate_context,
            )
        except Exception as exc:
            return {
                "status": "failed",
                "model": self.model,
                "reason": str(exc),
                "visual_observations": [],
                "visible_text": [],
                "spoken_content": [],
                "audio_cues": [],
                "hook_evidence": [],
                "claim_evidence": [],
                "missing_evidence": list(EVIDENCE_NORMALIZERS),
            }

        return normalize_gemini_response(response, self.model)


def normalize_gemini_response(response: Any, model: str) -> dict[str, Any]:
    payload = response if isinstance(response, dict) else {}
    evidence: dict[str, Any] = {
        "status": "completed",
        "model": model,
    }
    missing_evidence = []
    for key, normalizer in EVIDENCE_NORMALIZERS.items():
        raw_items = payload.get(key)
        items = raw_items if isinstance(raw_items, list) else []
        normalized = [
            normalized_item
            for normalized_item in (normalizer(item) for item in items if isinstance(item, dict))
            if any(value not in (None, "") for value in normalized_item.values())
        ]
        evidence[key] = normalized
        if not normalized:
            missing_evidence.append(key)

    if missing_evidence:
        evidence["status"] = "partial" if len(missing_evidence) < len(EVIDENCE_NORMALIZERS) else "failed"
        evidence["missing_evidence"] = missing_evidence
    else:
        evidence["missing_evidence"] = []
    return evidence
