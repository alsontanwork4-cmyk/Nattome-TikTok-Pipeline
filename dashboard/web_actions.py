from __future__ import annotations

from pathlib import Path

from .nattome_pov_library import (
    NATTOME_POV_STATUSES,
    archive_nattome_pov,
    create_nattome_pov,
    update_nattome_pov,
)
from .pattern_library import (
    APPROVED_PATTERN_STATUSES,
    approve_candidate_pattern,
    archive_approved_pattern,
    create_approved_pattern,
    update_approved_pattern,
)
from .recommendations import VALID_RECOMMENDATION_STATUSES, update_recommendation_status
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
def _update_recommendation_status(workspace: Path, form: dict[str, list[str]]) -> None:
    recommendation_id = int(_first_form_value(form, "recommendation_id") or "0")
    update_recommendation_status(
        workspace,
        recommendation_id,
        _first_form_value(form, "status"),
        user=_first_form_value(form, "user") or "local",
    )
def _approve_pattern_candidate(workspace: Path, form: dict[str, list[str]]) -> None:
    approve_candidate_pattern(
        workspace,
        int(_first_form_value(form, "candidate_id") or "0"),
        user=_first_form_value(form, "user") or "local",
        notes=_first_form_value(form, "notes"),
    )


def _create_pattern(workspace: Path, form: dict[str, list[str]]) -> None:
    create_approved_pattern(
        workspace,
        _pattern_form_payload(form),
        user=_first_form_value(form, "user") or "local",
        status="draft",
    )


def _edit_pattern(workspace: Path, form: dict[str, list[str]]) -> None:
    update_approved_pattern(
        workspace,
        int(_first_form_value(form, "pattern_id") or "0"),
        _pattern_form_payload(form, include_status=True),
        user=_first_form_value(form, "user") or "local",
    )


def _archive_pattern(workspace: Path, form: dict[str, list[str]]) -> None:
    archive_approved_pattern(
        workspace,
        int(_first_form_value(form, "pattern_id") or "0"),
        user=_first_form_value(form, "user") or "local",
    )
def _create_nattome_pov(workspace: Path, form: dict[str, list[str]]) -> None:
    create_nattome_pov(
        workspace,
        _nattome_pov_form_payload(form),
        user=_first_form_value(form, "user") or "local",
        status="draft",
    )


def _edit_nattome_pov(workspace: Path, form: dict[str, list[str]]) -> None:
    update_nattome_pov(
        workspace,
        int(_first_form_value(form, "pov_id") or "0"),
        _nattome_pov_form_payload(form, include_status=True),
        user=_first_form_value(form, "user") or "local",
    )


def _archive_nattome_pov(workspace: Path, form: dict[str, list[str]]) -> None:
    archive_nattome_pov(
        workspace,
        int(_first_form_value(form, "pov_id") or "0"),
        user=_first_form_value(form, "user") or "local",
    )


def _nattome_pov_form_payload(
    form: dict[str, list[str]],
    *,
    include_status: bool = False,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "title": _first_form_value(form, "title"),
        "description": _first_form_value(form, "description"),
        "brand_safe_interpretation": _first_form_value(form, "brand_safe_interpretation"),
        "adaptation_rules": _first_form_value(form, "adaptation_rules"),
        "product": _first_form_value(form, "product"),
        "campaign": _first_form_value(form, "campaign"),
        "market": _first_form_value(form, "market"),
        "language": _first_form_value(form, "language"),
        "audience_avatar": _first_form_value(form, "audience_avatar"),
        "symptom_occasion": _first_form_value(form, "symptom_occasion"),
        "channel": _first_form_value(form, "channel"),
        "source_links": _first_form_value(form, "source_links").splitlines(),
        "linked_pattern_ids": _first_form_value(form, "linked_pattern_ids").splitlines(),
    }
    if include_status:
        status = _first_form_value(form, "status") or "draft"
        if status not in NATTOME_POV_STATUSES:
            raise ValueError(f"Invalid Nattome POV status: {status}")
        payload["status"] = status
    return payload
def _pattern_form_payload(
    form: dict[str, list[str]],
    *,
    include_status: bool = False,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "pattern_name": _first_form_value(form, "pattern_name"),
        "hook_type": _first_form_value(form, "hook_type"),
        "format_type": _first_form_value(form, "format_type"),
        "emotional_trigger": _first_form_value(form, "emotional_trigger"),
        "source_videos": _parse_source_videos(_first_form_value(form, "source_videos")),
        "why_it_works": _first_form_value(form, "why_it_works"),
        "nattome_adaptation_notes": _first_form_value(form, "nattome_adaptation_notes"),
        "shoot_difficulty": _first_form_value(form, "shoot_difficulty"),
        "freshness": _first_form_value(form, "freshness"),
        "related_povs": _first_form_value(form, "related_povs").splitlines(),
        "avoid_notes": _first_form_value(form, "avoid_notes"),
        "targeting": {
            "market": _first_form_value(form, "target_market"),
            "persona": _first_form_value(form, "target_persona"),
        },
    }
    if include_status:
        status = _first_form_value(form, "status") or "draft"
        if status not in APPROVED_PATTERN_STATUSES:
            raise ValueError(f"Invalid pattern status: {status}")
        payload["status"] = status
    return payload


def _parse_source_videos(raw_value: str) -> list[dict[str, object]]:
    videos = []
    for line in raw_value.splitlines():
        line = line.strip()
        if not line:
            continue
        if "|" in line:
            video_id, url = [part.strip() for part in line.split("|", 1)]
        else:
            video_id, url = line, ""
        videos.append({"video_id": video_id, "tiktok_url": url})
    return videos
def _settings_form_payload(form: dict[str, list[str]]) -> dict[str, object]:
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
        "minimum_weighted_engagement_rate": _first_form_value(
            form,
            "minimum_weighted_engagement_rate",
        ),
        "requires_downloadable_video": "requires_downloadable_video" in form,
        "exclusion_terms": _first_form_value(form, "exclusion_terms"),
    }
