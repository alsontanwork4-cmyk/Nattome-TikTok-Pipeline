from __future__ import annotations

from typing import Any

VALID_SCOPES = {"all", "hashtags", "keywords", "profiles"}

DEFAULT_SCRAPE_SETTINGS: dict[str, Any] = {
    "hashtags": [
        "bloating",
        "guthealth",
        "ibs",
        "digestion",
        "gutfeeling",
        "stomachhealth",
        "constipation",
        "acidreflux",
        "guttok",
        "healthygut",
    ],
    "keywords": [
        "bloated stomach",
        "stomach pain after eating",
        "ibs tips",
        "gut health routine",
        "natural antacid",
        "fix bloating",
        "digestive health",
    ],
    "competitor_profiles": ["gaviscon", "gutgang", "drwillcole"],
    "scope": "all",
    "results_per_input": 20,
    "minimum_views": 10000,
    "maximum_age_days": 150,
    "minimum_weighted_engagement_rate": 0.03,
    "requires_downloadable_video": True,
    "exclusion_terms": [],
}

READ_ONLY_SETTINGS: dict[str, str] = {
    "API keys": "APIFY_TOKEN",
    "Apify actor ID": "clockworks~tiktok-scraper",
    "Output paths": "runs/batch-analysis/<timestamp>_daily",
    "Pipeline boundary": "source-video snapshots",
}


def validate_scrape_settings(raw_settings: dict[str, Any]) -> dict[str, Any]:
    settings = dict(DEFAULT_SCRAPE_SETTINGS)
    settings["hashtags"] = _normalized_tokens(
        raw_settings.get("hashtags", settings["hashtags"]),
        strip_prefix="#",
        field_name="hashtags",
    )
    settings["keywords"] = _normalized_tokens(
        raw_settings.get("keywords", settings["keywords"]),
        field_name="keywords",
    )
    settings["competitor_profiles"] = _normalized_tokens(
        raw_settings.get("competitor_profiles", settings["competitor_profiles"]),
        strip_prefix="@",
        field_name="competitor profiles",
    )
    settings["scope"] = _scope_value(raw_settings.get("scope", settings["scope"]))
    settings["results_per_input"] = _positive_int(
        raw_settings.get("results_per_input", settings["results_per_input"]),
        "results per input",
    )
    settings["minimum_views"] = _non_negative_int(
        raw_settings.get("minimum_views", settings["minimum_views"]),
        "minimum views",
    )
    settings["maximum_age_days"] = _positive_int(
        raw_settings.get("maximum_age_days", settings["maximum_age_days"]),
        "maximum age days",
    )
    settings["minimum_weighted_engagement_rate"] = _non_negative_float(
        raw_settings.get(
            "minimum_weighted_engagement_rate",
            settings["minimum_weighted_engagement_rate"],
        ),
        "minimum weighted engagement rate",
    )
    settings["requires_downloadable_video"] = _bool_value(
        raw_settings.get(
            "requires_downloadable_video",
            settings["requires_downloadable_video"],
        )
    )
    settings["exclusion_terms"] = _normalized_tokens(
        raw_settings.get("exclusion_terms", settings["exclusion_terms"]),
        field_name="exclusion terms",
    )
    if not (
        settings["hashtags"]
        or settings["keywords"]
        or settings["competitor_profiles"]
    ):
        raise ValueError("at least one hashtag, keyword, or competitor profile is required")
    return settings


def _normalized_tokens(
    raw_value: Any,
    *,
    field_name: str,
    strip_prefix: str = "",
) -> list[str]:
    tokens: list[str] = []
    if isinstance(raw_value, str):
        pieces = raw_value.replace(",", "\n").splitlines()
    elif isinstance(raw_value, list):
        pieces = raw_value
    elif raw_value is None:
        pieces = []
    else:
        raise ValueError(f"{field_name} must be text or a list")
    seen: set[str] = set()
    for piece in pieces:
        token = str(piece).strip()
        if strip_prefix:
            token = token.lstrip(strip_prefix).strip()
        if not token:
            continue
        key = token.casefold()
        if key in seen:
            raise ValueError(f"duplicate {field_name}: {token}")
        seen.add(key)
        tokens.append(token)
    return tokens


def _scope_value(raw_value: Any) -> str:
    scope = str(raw_value or "").strip().lower()
    if scope not in VALID_SCOPES:
        raise ValueError(f"scope must be one of: {', '.join(sorted(VALID_SCOPES))}")
    return scope


def _positive_int(raw_value: Any, field_name: str) -> int:
    value = _int_value(raw_value, field_name)
    if value <= 0:
        raise ValueError(f"{field_name} must be greater than zero")
    return value


def _non_negative_int(raw_value: Any, field_name: str) -> int:
    value = _int_value(raw_value, field_name)
    if value < 0:
        raise ValueError(f"{field_name} cannot be negative")
    return value


def _int_value(raw_value: Any, field_name: str) -> int:
    try:
        return int(str(raw_value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a whole number") from exc


def _non_negative_float(raw_value: Any, field_name: str) -> float:
    try:
        value = float(str(raw_value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a number") from exc
    if value < 0:
        raise ValueError(f"{field_name} cannot be negative")
    return value


def _bool_value(raw_value: Any) -> bool:
    if isinstance(raw_value, bool):
        return raw_value
    return str(raw_value).strip().lower() in {"1", "true", "yes", "on"}
