from __future__ import annotations

import json
import mimetypes
import os
import shutil
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import parse_qsl, unquote, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen


GEMINI_FLASH_MODEL = "gemini-2.5-flash"
GEMINI_API_BASE = "https://generativelanguage.googleapis.com"


def source_video_filename(source: str) -> str:
    parsed = urlparse(source)
    suffix = Path(unquote(parsed.path)).suffix if parsed.scheme else Path(source).suffix
    return f"source_video{suffix or '.mp4'}"


def apify_authenticated_url(source: str) -> str:
    parsed = urlparse(source)
    if parsed.netloc != "api.apify.com":
        return source
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if query.get("token"):
        return source
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        return source
    query["token"] = token
    return urlunparse(parsed._replace(query=urlencode(query)))


def copy_or_download_video(source: str, destination: Path) -> dict[str, Any]:
    if not source:
        return {
            "status": "missing",
            "reason": "no downloadable video source was provided in candidate metadata",
        }

    parsed = urlparse(source)
    try:
        if parsed.scheme in ("http", "https"):
            download_source = apify_authenticated_url(source)
            with urlopen(download_source, timeout=60) as response:
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


def json_request(url: str, *, api_key: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="GET" if payload is None else "POST",
    )
    try:
        with urlopen(request, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini HTTP {exc.code}: {body}") from exc


def extract_response_text(response: dict[str, Any]) -> str:
    candidates = response.get("candidates") if isinstance(response, dict) else None
    if not isinstance(candidates, list):
        return ""
    chunks = []
    for candidate in candidates:
        content = candidate.get("content") if isinstance(candidate, dict) else None
        parts = content.get("parts") if isinstance(content, dict) else None
        if not isinstance(parts, list):
            continue
        for part in parts:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                chunks.append(part["text"])
    return "\n".join(chunks).strip()


def parse_json_text(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.startswith("json"):
            stripped = stripped[4:]
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        stripped = stripped[start : end + 1]
    loaded = json.loads(stripped)
    if not isinstance(loaded, dict):
        raise RuntimeError("Gemini response JSON was not an object")
    return loaded


class GeminiVideoClient:
    def upload_file(self, *, api_key: str, source_video_path: Path) -> dict[str, Any]:
        mime_type = mimetypes.guess_type(source_video_path.name)[0] or "video/mp4"
        file_bytes = source_video_path.read_bytes()
        start_request = Request(
            f"{GEMINI_API_BASE}/upload/v1beta/files",
            data=json.dumps({"file": {"display_name": source_video_path.name}}).encode("utf-8"),
            headers={
                "x-goog-api-key": api_key,
                "X-Goog-Upload-Protocol": "resumable",
                "X-Goog-Upload-Command": "start",
                "X-Goog-Upload-Header-Content-Length": str(len(file_bytes)),
                "X-Goog-Upload-Header-Content-Type": mime_type,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(start_request, timeout=60) as response:
                upload_url = response.headers.get("x-goog-upload-url")
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Gemini upload start HTTP {exc.code}: {body}") from exc
        if not upload_url:
            raise RuntimeError("Gemini upload did not return an upload URL")

        upload_request = Request(
            upload_url,
            data=file_bytes,
            headers={
                "Content-Length": str(len(file_bytes)),
                "X-Goog-Upload-Offset": "0",
                "X-Goog-Upload-Command": "upload, finalize",
            },
            method="POST",
        )
        try:
            with urlopen(upload_request, timeout=300) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Gemini upload finalize HTTP {exc.code}: {body}") from exc
        file_info = payload.get("file") if isinstance(payload, dict) else None
        if not isinstance(file_info, dict):
            raise RuntimeError("Gemini upload response did not include file metadata")
        file_info.setdefault("mimeType", mime_type)
        return file_info

    def wait_for_file(self, *, api_key: str, file_info: dict[str, Any]) -> dict[str, Any]:
        name = file_info.get("name")
        if not name:
            return file_info
        deadline = time.monotonic() + 600
        current = file_info
        while str(current.get("state") or "").upper() == "PROCESSING":
            if time.monotonic() > deadline:
                raise RuntimeError(f"Gemini file processing timed out for {name}")
            time.sleep(5)
            current = json_request(f"{GEMINI_API_BASE}/v1beta/{name}", api_key=api_key)
        state = str(current.get("state") or "").upper()
        if state and state not in ("ACTIVE", "STATE_UNSPECIFIED"):
            raise RuntimeError(f"Gemini file processing failed for {name}: {state}")
        return current

    def analyze_video(
        self,
        *,
        model: str,
        api_key: str,
        source_video_path: Path,
        candidate_context: dict[str, Any],
    ) -> dict[str, Any]:
        uploaded = self.wait_for_file(
            api_key=api_key,
            file_info=self.upload_file(api_key=api_key, source_video_path=source_video_path),
        )
        file_uri = uploaded.get("uri")
        mime_type = uploaded.get("mimeType") or mimetypes.guess_type(source_video_path.name)[0] or "video/mp4"
        if not file_uri:
            raise RuntimeError("Gemini uploaded file did not include a file URI")

        prompt = {
            "task": "Extract evidence from this TikTok for Nattome batch analysis. Return JSON only.",
            "candidate": {
                "id": candidate_context.get("id"),
                "url": candidate_context.get("url"),
                "caption": candidate_context.get("caption"),
                "duration_seconds": candidate_context.get("duration_seconds"),
                "sound_title": candidate_context.get("sound_title"),
                "sound_author": candidate_context.get("sound_author"),
            },
            "required_schema": {
                "visual_observations": [
                    {"timestamp_seconds": 0, "observation": "what is visibly happening", "confidence": 0.0}
                ],
                "visible_text": [
                    {"timestamp_seconds": 0, "text": "on-screen text exactly as visible", "confidence": 0.0}
                ],
                "spoken_content": [
                    {
                        "start_seconds": 0,
                        "end_seconds": 1,
                        "text": "spoken words or subtitle transcript",
                        "language": "English/Malay/Mandarin/Manglish/etc",
                        "confidence": 0.0,
                    }
                ],
                "audio_cues": [
                    {"timestamp_seconds": 0, "cue": "voiceover, music, sound effect, or audio format", "confidence": 0.0}
                ],
                "hook_evidence": [
                    {"timestamp_seconds": 0, "evidence": "first-three-second hook evidence", "confidence": 0.0}
                ],
                "claim_evidence": [
                    {"timestamp_seconds": 0, "text": "health, medical, product, cure, symptom, or outcome claim", "confidence": 0.0}
                ],
            },
            "rules": [
                "Use timestamps in seconds.",
                "Preserve visible text and spoken content verbatim when possible.",
                "Use empty arrays when evidence is absent or not confidently detectable.",
                "Do not create shootable angles or marketing recommendations.",
                "Do not infer claims that are not visible, spoken, or clearly present in the source video.",
            ],
        }
        response = json_request(
            f"{GEMINI_API_BASE}/v1beta/models/{model}:generateContent",
            api_key=api_key,
            payload={
                "contents": [
                    {
                        "parts": [
                            {"file_data": {"mime_type": mime_type, "file_uri": file_uri}},
                            {"text": json.dumps(prompt, ensure_ascii=False)},
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.1,
                    "responseMimeType": "application/json",
                },
            },
        )
        text = extract_response_text(response)
        if not text:
            raise RuntimeError("Gemini response did not include text output")
        return parse_json_text(text)


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
        self.client = client if client is not None else GeminiVideoClient()

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
