from __future__ import annotations

from pathlib import Path

from .settings import rollback_settings_version, save_settings_version
from .store import connect_dashboard_store, dump_json
from .web_components import _first_form_value
from .web_constants import CURATION_LABELS

def _save_video_curation(workspace: Path, form: dict[str, list[str]]) -> None:
    video_id = _first_form_value(form, "video_id")
    if not video_id:
        return
    labels = [label for label in form.get("labels", []) if label in CURATION_LABELS]
    exclude_reason = _first_form_value(form, "exclude_similar_reason")[:160]
    if "Exclude Similar" in labels and not exclude_reason.strip():
        labels = [label for label in labels if label != "Exclude Similar"]
    note = _first_form_value(form, "note")[:500]
    connection = connect_dashboard_store(workspace)
    try:
        connection.execute(
            """
            INSERT INTO video_curation (
                tiktok_video_id,
                labels,
                exclude_similar_reason,
                note,
                updated_at
            )
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(tiktok_video_id) DO UPDATE SET
                labels = excluded.labels,
                exclude_similar_reason = excluded.exclude_similar_reason,
                note = excluded.note,
                updated_at = CURRENT_TIMESTAMP
            """,
            (video_id, dump_json(labels), exclude_reason, note),
        )
        connection.commit()
    finally:
        connection.close()
def _save_scrape_settings(workspace: Path, form: dict[str, list[str]]) -> None:
    save_settings_version(
        workspace,
        _settings_form_payload(form),
        reason=_first_form_value(form, "reason"),
        user=_first_form_value(form, "user") or "local",
    )


def _rollback_scrape_settings(workspace: Path, form: dict[str, list[str]]) -> None:
    target_version = int(_first_form_value(form, "target_version") or "0")
    rollback_settings_version(
        workspace,
        target_version=target_version,
        reason=_first_form_value(form, "reason"),
        user=_first_form_value(form, "user") or "local",
    )
def _settings_form_payload(form: dict[str, list[str]]) -> dict[str, object]:
    engagement_rate = _first_form_value(form, "minimum_weighted_engagement_rate")
    engagement_rate_percent = _first_form_value(form, "minimum_engagement_rate_percent")
    if engagement_rate_percent:
        engagement_rate = str(float(engagement_rate_percent) / 100)
    return {
        "hashtags": _first_form_value(form, "hashtags"),
        "keywords": _first_form_value(form, "keywords"),
        "competitor_profiles": _first_form_value(form, "competitor_profiles"),
        "scope": _first_form_value(form, "scope") or "all",
        "results_per_input": _first_form_value(form, "results_per_input"),
        "top_n": _first_form_value(form, "top_n"),
        "daily_selection_size": _first_form_value(form, "daily_selection_size"),
        "minimum_views": _first_form_value(form, "minimum_views"),
        "maximum_age_days": _first_form_value(form, "maximum_age_days"),
        "minimum_weighted_engagement_rate": engagement_rate,
        "requires_downloadable_video": "requires_downloadable_video" in form,
        "exclusion_terms": _first_form_value(form, "exclusion_terms"),
    }
