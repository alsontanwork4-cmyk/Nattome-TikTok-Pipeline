from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

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
        return datetime.fromisoformat(run_timestamp.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return "unknown-date"

def default_final_outputs(metadata: dict[str, Any]) -> list[dict[str, str]]:
    report_date = report_date_from_metadata(metadata)
    return [
        {
            "label": "Top 5 Creative Production Report",
            "path": (
                f"reports/{report_date}/"
                f"top5_creative_production_report_{report_date}.md"
            ),
        },
        {
            "label": "Excel Planning Workbook",
            "path": (
                f"reports/{report_date}/"
                f"top5_angle_planning_sheet_{report_date}.xlsx"
            ),
        },
    ]

def build_telegram_brief_message(
    run_folder: Path,
    metadata: dict[str, Any],
    cross_video_summary: dict[str, Any],
    final_outputs: list[dict[str, Any]] | None = None,
) -> str:
    angles = cross_video_summary.get("top_priority_shootable_angles")
    top_angles = angles[:3] if isinstance(angles, list) else []
    recommendation = cross_video_summary.get("recommendation")
    if not isinstance(recommendation, dict):
        recommendation = {}

    lines = [
        "Nattome Batch Analysis Final Outputs",
        f"Run: {metadata.get('run_timestamp', 'unknown')} ({metadata.get('mode', 'unknown')})",
        f"Videos compared: {cross_video_summary.get('source_video_count', 0)}",
        (
            "Shoot first: "
            f"{recommendation.get('what_to_shoot_first', 'No recommendation')} "
            f"({recommendation.get('candidate_id', 'no candidate')})"
        ),
        "",
        "Top priority Shootable Angles:",
    ]
    if top_angles:
        for angle in top_angles:
            if not isinstance(angle, dict):
                continue
            score = angle.get("priority_score") if isinstance(angle.get("priority_score"), dict) else {}
            lines.append(
                "{rank}. {candidate} - {title} - {score}/30".format(
                    rank=angle.get("rank", "?"),
                    candidate=angle.get("candidate_id", "unknown"),
                    title=angle.get("angle_title", "Shootable angle"),
                    score=score.get("total", "?"),
                )
            )
    else:
        lines.append("No shootable angles available.")

    lines.extend(["", "Outputs:"])
    outputs = final_outputs if final_outputs else default_final_outputs(metadata)
    for output in outputs:
        if not isinstance(output, dict):
            continue
        label = output.get("label", "Output")
        path = output.get("path", "")
        lines.append(f"{label}: {path}")
    lines.append(f"Run folder: {run_folder}")
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

def deliver_telegram_brief(
    run_folder: Path,
    metadata: dict[str, Any],
    cross_video_summary: dict[str, Any],
    telegram_config: dict[str, Any],
    final_outputs: list[dict[str, Any]] | None = None,
    sender=send_telegram_message,
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

    try:
        response = sender(token, chat_id, message)
    except Exception as exc:
        status = {
            "status": "failed",
            "reason": str(exc),
            "message_character_count": len(message),
        }
    else:
        status = {
            "status": "sent",
            "telegram_response": response,
            "message_character_count": len(message),
        }
    log_path.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return status

