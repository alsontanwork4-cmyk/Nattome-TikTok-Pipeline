from __future__ import annotations

from .config import DashboardSettings
from .scrape_settings import DEFAULT_SCRAPE_SETTINGS
from .shell import template_context


def settings_template_context(
    settings: DashboardSettings,
    *,
    user: object,
    versions: list[dict],
    error: str,
    form_settings: dict | None = None,
) -> dict:
    normalized_versions = [settings_version_view(version) for version in versions]
    active = next((version for version in normalized_versions if version["is_active"]), None)
    if active is None:
        active = {
            "version": 0,
            "settings": dict(DEFAULT_SCRAPE_SETTINGS),
            "reason": "Default production settings",
            "is_active": True,
            "rollback_of_version": None,
            "created_by": "system",
            "created_at": "",
        }
    return {
        **template_context(settings, page_title="Scrape Settings", active_path="/settings"),
        "current_user": user,
        "active": active,
        "versions": normalized_versions,
        "form": settings_form_view(form_settings or active["settings"]),
        "scope_options": [
            ("all", "All sources"),
            ("hashtags", "Only hashtags"),
            ("keywords", "Only keywords"),
            ("profiles", "Only competitor profiles"),
        ],
        "error": error,
    }


def settings_version_view(record: dict) -> dict:
    settings = record.get("settings")
    if not isinstance(settings, dict):
        settings = record.get("new_settings") if isinstance(record.get("new_settings"), dict) else {}
    return {
        "version": int(record.get("version") or 0),
        "settings": {**DEFAULT_SCRAPE_SETTINGS, **settings},
        "reason": str(record.get("reason") or ""),
        "is_active": bool(record.get("is_active")),
        "rollback_of_version": record.get("rollback_of_version"),
        "created_by": str(record.get("created_by") or record.get("changed_by") or ""),
        "created_at": str(record.get("created_at") or record.get("timestamp") or ""),
    }


def settings_form_view(settings: dict) -> dict:
    return {
        "hashtags": lines(settings.get("hashtags")),
        "keywords": lines(settings.get("keywords")),
        "competitor_profiles": lines(settings.get("competitor_profiles")),
        "scope": str(settings.get("scope") or "all"),
        "results_per_input": settings.get("results_per_input") or "",
        "minimum_views": settings.get("minimum_views") or "",
        "maximum_age_days": settings.get("maximum_age_days") or "",
        "minimum_engagement_rate_percent": percent_value(
            settings.get("minimum_weighted_engagement_rate")
        ),
        "requires_downloadable_video": bool(settings.get("requires_downloadable_video")),
        "exclusion_terms": lines(settings.get("exclusion_terms")),
    }


def settings_form_payload(form: object) -> dict[str, object]:
    engagement_rate = form_value(form, "minimum_weighted_engagement_rate")
    engagement_rate_percent = form_value(form, "minimum_engagement_rate_percent")
    if engagement_rate_percent:
        engagement_rate = str(float(engagement_rate_percent) / 100)
    return {
        "hashtags": form_value(form, "hashtags"),
        "keywords": form_value(form, "keywords"),
        "competitor_profiles": form_value(form, "competitor_profiles"),
        "scope": form_value(form, "scope") or "all",
        "results_per_input": form_value(form, "results_per_input"),
        "minimum_views": form_value(form, "minimum_views"),
        "maximum_age_days": form_value(form, "maximum_age_days"),
        "minimum_weighted_engagement_rate": engagement_rate,
        "requires_downloadable_video": "requires_downloadable_video" in form,
        "exclusion_terms": form_value(form, "exclusion_terms"),
    }


def form_settings_from_payload(payload: dict[str, object]) -> dict:
    settings = dict(DEFAULT_SCRAPE_SETTINGS)
    settings.update(payload)
    try:
        settings["minimum_weighted_engagement_rate"] = float(
            payload.get("minimum_weighted_engagement_rate") or 0
        )
    except (TypeError, ValueError):
        settings["minimum_weighted_engagement_rate"] = payload.get(
            "minimum_weighted_engagement_rate"
        )
    return settings


def form_value(form: object, key: str) -> str:
    value = form.get(key) if hasattr(form, "get") else ""
    return str(value or "")


def lines(value: object) -> str:
    if isinstance(value, list):
        return "\n".join(str(item) for item in value)
    return str(value or "")


def percent_value(value: object) -> str:
    try:
        percent = float(value) * 100
    except (TypeError, ValueError):
        return ""
    return f"{percent:g}"
