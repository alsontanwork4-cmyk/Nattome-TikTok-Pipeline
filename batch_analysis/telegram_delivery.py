from __future__ import annotations

import os
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .evidence_io import relative_path

TELEGRAM_BOT_TOKEN_ENV = "TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID_ENV = "TELEGRAM_CHAT_ID"
try:
    SINGAPORE_TIME_ZONE = ZoneInfo("Asia/Singapore")
except ZoneInfoNotFoundError:
    SINGAPORE_TIME_ZONE = timezone(timedelta(hours=8))

TelegramSender = Callable[[str, str, str], dict[str, Any]]
TelegramDocumentSender = Callable[[str, str, Path], dict[str, Any]]


def send_telegram_message(bot_token: str, chat_id: str, text: str) -> dict[str, Any]:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = urlencode({"chat_id": chat_id, "text": text}).encode("utf-8")
    request = Request(
        url,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(request, timeout=30) as response:
        return {
            "status": "sent",
            "http_status": getattr(response, "status", None),
        }


def send_telegram_document(bot_token: str, chat_id: str, document_path: Path) -> dict[str, Any]:
    boundary = f"----nattome-{uuid4().hex}"
    file_bytes = document_path.read_bytes()
    body = b"".join(
        [
            f"--{boundary}\r\n".encode("utf-8"),
            b'Content-Disposition: form-data; name="chat_id"\r\n\r\n',
            str(chat_id).encode("utf-8"),
            b"\r\n",
            f"--{boundary}\r\n".encode("utf-8"),
            (
                'Content-Disposition: form-data; name="document"; '
                f'filename="{document_path.name}"\r\n'
            ).encode("utf-8"),
            b"Content-Type: text/markdown\r\n\r\n",
            file_bytes,
            b"\r\n",
            f"--{boundary}--\r\n".encode("utf-8"),
        ]
    )
    request = Request(
        f"https://api.telegram.org/bot{bot_token}/sendDocument",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urlopen(request, timeout=60) as response:
        return {
            "status": "sent",
            "http_status": getattr(response, "status", None),
        }


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def singapore_run_time(run_folder: Path) -> str:
    metadata = read_json(run_folder / "run_metadata.json")
    raw_timestamp = metadata.get("run_timestamp")
    if isinstance(raw_timestamp, str):
        try:
            parsed = datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00"))
        except ValueError:
            parsed = None
        if parsed is not None:
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(SINGAPORE_TIME_ZONE).replace(microsecond=0).isoformat()
    return datetime.now(SINGAPORE_TIME_ZONE).replace(microsecond=0).isoformat()


def selected_video_count(run_folder: Path, report_paths: list[str]) -> int:
    selected_batch = read_json(run_folder / "data" / "selected_batch.json")
    count = selected_batch.get("selected_candidate_count")
    if isinstance(count, int):
        return count
    candidates = selected_batch.get("selected_candidates")
    if isinstance(candidates, list):
        return len(candidates)
    return len(report_paths)


def final_outputs_summary(run_folder: Path, report_paths: list[str], status: str) -> str:
    success_or_fail = "Success" if status == "completed" else "Fail"
    return "\n".join(
        [
            "Nattome Batch Analysis Final Outputs",
            f"Run: {singapore_run_time(run_folder)}",
            f"Videos compared: {selected_video_count(run_folder, report_paths)}",
            f"Success or Fail: {success_or_fail}",
        ]
    )


def telegram_phase_record(
    status: str,
    *,
    outputs: dict[str, Any] | None = None,
    failure_details: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "name": "telegram_delivery",
        "status": status,
        "inputs": {
            "reports": "outputs.final_outputs",
            "bot_token_env": TELEGRAM_BOT_TOKEN_ENV,
            "chat_id_env": TELEGRAM_CHAT_ID_ENV,
        },
        "outputs": outputs or {},
    }
    if failure_details:
        record["failure_details"] = failure_details
    return record


def deliver_reports_to_telegram(
    run_folder: Path,
    report_paths: list[str],
    *,
    bot_token: str | None = None,
    chat_id: str | None = None,
    sender: TelegramSender | None = None,
    document_sender: TelegramDocumentSender | None = None,
) -> dict[str, Any]:
    if not report_paths:
        return telegram_phase_record(
            "skipped",
            failure_details=[{"reason": "no generated Nattome POV reports to deliver"}],
        )

    resolved_bot_token = bot_token if bot_token is not None else os.environ.get(TELEGRAM_BOT_TOKEN_ENV)
    resolved_chat_id = chat_id if chat_id is not None else os.environ.get(TELEGRAM_CHAT_ID_ENV)
    missing = []
    if not resolved_bot_token:
        missing.append(TELEGRAM_BOT_TOKEN_ENV)
    if not resolved_chat_id:
        missing.append(TELEGRAM_CHAT_ID_ENV)
    if missing:
        return telegram_phase_record(
            "missing_credentials",
            failure_details=[{"reason": f"missing Telegram environment variables: {', '.join(missing)}"}],
        )

    active_sender = sender or send_telegram_message
    active_document_sender = document_sender or send_telegram_document
    deliveries: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    existing_report_paths = [run_folder / report_path for report_path in report_paths if (run_folder / report_path).exists()]

    if existing_report_paths:
        try:
            active_sender(
                resolved_bot_token,
                resolved_chat_id,
                final_outputs_summary(run_folder, report_paths, "completed"),
            )
        except Exception as exc:
            failures.append({"path": "telegram_summary", "reason": str(exc)})

    for report_path in report_paths:
        absolute_report_path = run_folder / report_path
        if not absolute_report_path.exists():
            failures.append({"path": report_path, "reason": "report artifact is missing"})
            continue
        try:
            active_document_sender(resolved_bot_token, resolved_chat_id, absolute_report_path)
            deliveries.append({"path": report_path, "document_count": 1})
        except Exception as exc:
            failures.append({"path": report_path, "reason": str(exc)})

    if deliveries and failures:
        status = "partial"
    elif deliveries:
        status = "completed"
    else:
        status = "failed"

    return telegram_phase_record(
        status,
        outputs={"deliveries": deliveries},
        failure_details=failures,
    )
