from __future__ import annotations

import json
import mimetypes
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

from .report_dates import report_date_from_timestamp

def telegram_credentials(telegram_config: dict[str, Any]) -> tuple[str | None, str | None, list[str]]:
    token_env = str(telegram_config.get("bot_token_env") or "TELEGRAM_BOT_TOKEN")
    chat_id_env = str(telegram_config.get("chat_id_env") or "TELEGRAM_CHAT_ID")
    token = telegram_config.get("bot_token") or os.environ.get(token_env)
    chat_id = telegram_config.get("chat_id") or os.environ.get(chat_id_env)
    missing = []
    if not token:
        missing.append(token_env)
    if not chat_id:
        missing.append(chat_id_env)
    return str(token) if token else None, str(chat_id) if chat_id else None, missing

def report_date_from_metadata(metadata: dict[str, Any]) -> str:
    run_timestamp = str(metadata.get("run_timestamp") or "")
    try:
        return report_date_from_timestamp(run_timestamp)
    except ValueError:
        return "unknown-date"

def default_final_outputs(metadata: dict[str, Any]) -> list[dict[str, str]]:
    report_date = report_date_from_metadata(metadata)
    return [
        {
            "label": "Daily Top-3 Creative Production Report",
            "path": (
                f"reports/{report_date}/"
                f"production_creative_report_{report_date}.md"
            ),
        },
        {
            "label": "Excel Planning Workbook",
            "path": (
                f"reports/{report_date}/"
                f"production_angle_planning_sheet_{report_date}.xlsx"
            ),
        },
    ]

def run_success_label(
    cross_video_summary: dict[str, Any],
    final_outputs: list[dict[str, Any]] | None = None,
) -> str:
    source_video_count = int(cross_video_summary.get("source_video_count") or 0)
    outputs = default_final_outputs({}) if final_outputs is None else final_outputs
    return "Success" if source_video_count > 0 and outputs else "Fail"

def build_telegram_brief_message(
    run_folder: Path,
    metadata: dict[str, Any],
    cross_video_summary: dict[str, Any],
    final_outputs: list[dict[str, Any]] | None = None,
) -> str:
    lines = [
        "Nattome Batch Analysis Final Outputs",
        f"Run: {metadata.get('run_timestamp', 'unknown')}",
        f"Videos compared: {cross_video_summary.get('source_video_count', 0)}",
        f"Success or Fail: {run_success_label(cross_video_summary, final_outputs)}",
    ]
    return "\n".join(lines)

def send_telegram_message(token: str, chat_id: str, text: str) -> dict[str, Any]:
    payload = urlencode(
        {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")
    request = Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8", errors="replace")
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"ok": False, "raw_response": body}

def multipart_form_data(fields: dict[str, str], file_field: str, file_path: Path) -> tuple[bytes, str]:
    boundary = f"----CodexTelegramBoundary{uuid4().hex}"
    mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    body = bytearray()

    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode("utf-8")
        )

    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(
        (
            f'Content-Disposition: form-data; name="{file_field}"; '
            f'filename="{file_path.name}"\r\n'
        ).encode("utf-8")
    )
    body.extend(f"Content-Type: {mime_type}\r\n\r\n".encode("utf-8"))
    body.extend(file_path.read_bytes())
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    return bytes(body), boundary

def send_telegram_document(token: str, chat_id: str, document_path: Path) -> dict[str, Any]:
    payload, boundary = multipart_form_data(
        {"chat_id": chat_id, "disable_content_type_detection": "false"},
        "document",
        document_path,
    )
    request = Request(
        f"https://api.telegram.org/bot{token}/sendDocument",
        data=payload,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urlopen(request, timeout=60) as response:
        body = response.read().decode("utf-8", errors="replace")
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"ok": False, "raw_response": body}

def resolve_output_document_paths(
    run_folder: Path,
    metadata: dict[str, Any],
    final_outputs: list[dict[str, Any]] | None,
) -> tuple[list[Path], list[str]]:
    outputs = default_final_outputs(metadata) if final_outputs is None else final_outputs
    resolved_paths: list[Path] = []
    missing_paths: list[str] = []
    ancestors = [run_folder, *run_folder.parents]

    for output in outputs:
        if not isinstance(output, dict):
            continue
        raw_path = str(output.get("path") or "").strip()
        if not raw_path:
            continue
        path = Path(raw_path)
        candidates: list[Path] = []
        if path.is_absolute():
            candidates.append(path)
        else:
            for ancestor in ancestors:
                candidates.append(ancestor / path)
                candidates.append(ancestor / "outputs" / path)
        resolved = next((candidate for candidate in candidates if candidate.exists()), None)
        if resolved is None:
            missing_paths.append(raw_path)
            continue
        resolved_paths.append(resolved)
    return resolved_paths, missing_paths

def deliver_telegram_brief(
    run_folder: Path,
    metadata: dict[str, Any],
    cross_video_summary: dict[str, Any],
    telegram_config: dict[str, Any],
    final_outputs: list[dict[str, Any]] | None = None,
    sender=send_telegram_message,
    document_sender=send_telegram_document,
) -> dict[str, Any]:
    log_path = run_folder / "logs" / "telegram_delivery.json"
    if telegram_config.get("enabled", True) is False:
        status = {
            "status": "skipped",
            "reason": "Telegram delivery disabled in runtime configuration",
        }
        log_path.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return status

    token, chat_id, missing = telegram_credentials(telegram_config)
    message = build_telegram_brief_message(
        run_folder,
        metadata,
        cross_video_summary,
        final_outputs,
    )
    if missing:
        status = {
            "status": "skipped",
            "reason": "missing Telegram credentials",
            "missing": missing,
            "message_character_count": len(message),
        }
        log_path.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return status
    document_paths, missing_output_paths = resolve_output_document_paths(
        run_folder,
        metadata,
        final_outputs,
    )
    if missing_output_paths:
        status = {
            "status": "failed",
            "reason": "missing final output attachments",
            "missing_output_paths": missing_output_paths,
            "message_character_count": len(message),
        }
        log_path.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return status

    try:
        message_response = sender(token, chat_id, message)
        document_responses = [
            {
                "path": str(document_path),
                "response": document_sender(token, chat_id, document_path),
            }
            for document_path in document_paths
        ]
    except Exception as exc:
        status = {
            "status": "failed",
            "reason": str(exc),
            "message_character_count": len(message),
        }
    else:
        status = {
            "status": "sent",
            "telegram_response": {
                "message": message_response,
                "documents": document_responses,
            },
            "message_character_count": len(message),
            "sent_document_count": len(document_responses),
        }
    log_path.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return status

