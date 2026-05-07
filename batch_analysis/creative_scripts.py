from __future__ import annotations

from typing import Any


def compact_text(value: Any, fallback: str = "Not available") -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    return " ".join(text.split())


def markdown_cell(value: Any, fallback: str = "Not available") -> str:
    return compact_text(value, fallback).replace("|", "\\|")


def recommended_reason(angle: dict[str, Any]) -> str:
    return compact_text(
        angle.get("recommended_because")
        or angle.get("why_recommended")
        or angle.get("why")
        or angle.get("recommendation")
        or angle.get("recommended_angle"),
        "It is the most direct concept to shoot first because the hook, format, and production setup are clear.",
    )


def ending_segment(angle: dict[str, Any]) -> dict[str, str]:
    soft_close = compact_text(angle.get("soft_close"), "")
    if soft_close:
        return {
            "time": "22-30s",
            "scene": "Close",
            "on_screen_text": "Small routine first",
            "exact_line": soft_close,
        }

    cta = compact_text(angle.get("cta"), "")
    if cta:
        return {
            "time": "22-30s",
            "scene": "Close",
            "on_screen_text": "Daily support, simple choice",
            "exact_line": cta,
        }

    return {
        "time": "22-30s",
        "scene": "Close",
        "on_screen_text": "Keep it easy",
        "exact_line": "Start with one small after-meal routine first, then keep what feels easy to repeat.",
    }


def timed_script_segments(candidate: dict[str, Any], angle: dict[str, Any]) -> list[dict[str, str]]:
    caption = compact_text(candidate.get("caption"), "").lower()
    product_context = " ".join(
        [
            compact_text(angle.get("product_fit"), ""),
            compact_text(angle.get("cta"), ""),
        ]
    ).lower()
    has_product_context = any(term in product_context for term in ("nattome", " dh", "dr", "digestive support"))
    if "reflux" in caption or "heartburn" in caption:
        discomfort = "reflux feels uncomfortable"
        opener = "If reflux feels uncomfortable after makan, start with the moment your customer already knows."
    elif "bloating" in caption or "bloated" in caption:
        discomfort = "after meals feel heavy"
        opener = "If your stomach feels heavy after makan, start with the moment everyone recognises."
    else:
        discomfort = "digestion feels off"
        opener = "If digestion feels off after makan, start with a simple moment people recognise."

    return [
        {
            "time": "0-3s",
            "scene": "Face to camera",
            "on_screen_text": discomfort.capitalize(),
            "exact_line": opener,
        },
        {
            "time": "3-8s",
            "scene": "Face to camera",
            "on_screen_text": "What changed today?",
            "exact_line": "Ask yourself: was it the portion, the timing, or the routine after the meal?",
        },
        {
            "time": "8-14s",
            "scene": "Simple routine",
            "on_screen_text": "Keep it simple",
            "exact_line": "For content, show one small routine change instead of making big health promises.",
        },
        {
            "time": "14-22s",
            "scene": "Product context" if has_product_context else "Routine proof",
            "on_screen_text": "Daily digestive support" if has_product_context else "One small habit",
            "exact_line": (
                "If Nattome fits this concept, keep the mention natural and tied to daily digestive support."
                if has_product_context
                else "Keep the story on one everyday habit, so the message feels helpful instead of salesy."
            ),
        },
        ending_segment(angle),
    ]


def recommended_shoot_markdown(
    candidate: dict[str, Any],
    angle: dict[str, Any] | None,
) -> list[str]:
    angle = angle if isinstance(angle, dict) else {}
    hook = compact_text(angle.get("hook"), "Open with the clearest digestive discomfort moment.")
    lines = [
        "### Recommended Shoot",
        "",
        f"Recommended because: {recommended_reason(angle)}",
        "",
        f"Hook: {hook}",
        "",
        "| Time | Scene | On-screen text | Exact line |",
        "|---|---|---|---|",
    ]
    for segment in timed_script_segments(candidate, angle):
        lines.append(
            "| {time} | {scene} | {on_screen_text} | {exact_line} |".format(
                time=markdown_cell(segment["time"]),
                scene=markdown_cell(segment["scene"]),
                on_screen_text=markdown_cell(segment["on_screen_text"]),
                exact_line=markdown_cell(segment["exact_line"]),
            )
        )
    lines.append("")
    return lines
