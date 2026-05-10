from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .scrape_settings import (
    DEFAULT_SCRAPE_SETTINGS,
    READ_ONLY_SETTINGS,
    validate_scrape_settings,
)
from .store import connect_dashboard_store, dump_json, load_json


@dataclass(frozen=True)
class ScrapeSettingsVersion:
    version: int
    old_settings: dict[str, Any]
    new_settings: dict[str, Any]
    reason: str
    changed_by: str
    timestamp: str
    is_active: bool
    rollback_of_version: int | None = None


def save_settings_version(
    workspace: Path | str,
    raw_settings: dict[str, Any],
    *,
    reason: str,
    user: str = "local",
) -> ScrapeSettingsVersion:
    clean_reason = reason.strip()
    if not clean_reason:
        raise ValueError("saving production scrape settings requires a reason")
    new_settings = validate_scrape_settings(raw_settings)
    return _insert_settings_version(
        Path(workspace),
        old_settings=_active_settings_or_default(workspace),
        new_settings=new_settings,
        reason=clean_reason,
        user=user.strip() or "local",
        rollback_of_version=None,
    )


def rollback_settings_version(
    workspace: Path | str,
    *,
    target_version: int,
    reason: str,
    user: str = "local",
) -> ScrapeSettingsVersion:
    clean_reason = reason.strip()
    if not clean_reason:
        raise ValueError("rolling back production scrape settings requires a reason")
    target = _version_by_number(Path(workspace), target_version)
    if target is None:
        raise ValueError(f"unknown scrape settings version: {target_version}")
    return _insert_settings_version(
        Path(workspace),
        old_settings=_active_settings_or_default(workspace),
        new_settings=target.new_settings,
        reason=clean_reason,
        user=user.strip() or "local",
        rollback_of_version=target_version,
    )


def get_active_settings_version(workspace: Path | str) -> ScrapeSettingsVersion:
    version = _active_version(Path(workspace))
    if version is not None:
        return version
    return ScrapeSettingsVersion(
        version=0,
        old_settings={},
        new_settings=dict(DEFAULT_SCRAPE_SETTINGS),
        reason="Default production settings",
        changed_by="system",
        timestamp="",
        is_active=True,
        rollback_of_version=None,
    )


def list_settings_versions(workspace: Path | str) -> list[ScrapeSettingsVersion]:
    connection = connect_dashboard_store(workspace)
    try:
        rows = connection.execute(
            """
            SELECT *
            FROM scrape_settings_versions
            ORDER BY version DESC
            """
        )
        return [_row_to_version(row) for row in rows]
    finally:
        connection.close()


def _insert_settings_version(
    workspace: Path,
    *,
    old_settings: dict[str, Any],
    new_settings: dict[str, Any],
    reason: str,
    user: str,
    rollback_of_version: int | None,
) -> ScrapeSettingsVersion:
    connection = connect_dashboard_store(workspace)
    try:
        next_version = int(
            connection.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 FROM scrape_settings_versions"
            ).fetchone()[0]
        )
        old_json = _json_dumps(old_settings)
        new_json = _json_dumps(new_settings)
        connection.execute("UPDATE scrape_settings_versions SET is_active = 0")
        connection.execute(
            """
            INSERT INTO scrape_settings_versions (
                version,
                settings_json,
                old_settings_json,
                new_settings_json,
                reason,
                rollback_of_version,
                is_active,
                created_by,
                updated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                next_version,
                new_json,
                old_json,
                new_json,
                reason,
                rollback_of_version,
                user,
                user,
            ),
        )
        connection.commit()
    finally:
        connection.close()
    _write_production_settings(workspace, new_settings, next_version)
    return get_active_settings_version(workspace)


def _active_settings_or_default(workspace: Path | str) -> dict[str, Any]:
    active = _active_version(Path(workspace))
    return active.new_settings if active else dict(DEFAULT_SCRAPE_SETTINGS)


def _active_version(workspace: Path) -> ScrapeSettingsVersion | None:
    connection = connect_dashboard_store(workspace)
    try:
        row = connection.execute(
            """
            SELECT *
            FROM scrape_settings_versions
            WHERE is_active = 1
            ORDER BY version DESC
            LIMIT 1
            """
        ).fetchone()
        return _row_to_version(row) if row else None
    finally:
        connection.close()


def _version_by_number(workspace: Path, version: int) -> ScrapeSettingsVersion | None:
    connection = connect_dashboard_store(workspace)
    try:
        row = connection.execute(
            "SELECT * FROM scrape_settings_versions WHERE version = ?",
            (version,),
        ).fetchone()
        return _row_to_version(row) if row else None
    finally:
        connection.close()


def _row_to_version(row) -> ScrapeSettingsVersion:
    return ScrapeSettingsVersion(
        version=int(row["version"]),
        old_settings=_json_loads(row["old_settings_json"]),
        new_settings=_json_loads(row["new_settings_json"] or row["settings_json"]),
        reason=str(row["reason"]),
        changed_by=str(row["created_by"]),
        timestamp=str(row["created_at"]),
        is_active=bool(row["is_active"]),
        rollback_of_version=row["rollback_of_version"],
    )


def _write_production_settings(
    workspace: Path,
    settings: dict[str, Any],
    version: int,
) -> None:
    dashboard_path = workspace / "data" / "dashboard" / "production_scrape_settings.json"
    dashboard_path.parent.mkdir(parents=True, exist_ok=True)
    dashboard_path.write_text(
        _json_dumps({"version": version, "settings": settings}) + "\n",
        encoding="utf-8",
    )
    scraper_config_path = workspace / "batch_analysis" / "scrape_config.json"
    if scraper_config_path.parent.exists():
        scraper_config_path.write_text(
            _json_dumps(_scraper_config(settings, version)) + "\n",
            encoding="utf-8",
        )


def _scraper_config(settings: dict[str, Any], version: int) -> dict[str, Any]:
    return {
        "config_version": f"v{version}",
        "hashtags": settings["hashtags"],
        "keywords": settings["keywords"],
        "competitor_profiles": settings["competitor_profiles"],
        "scope": settings["scope"],
        "results_per_input": settings["results_per_input"],
        "selection": {
            "minimum_views": settings["minimum_views"],
            "maximum_age_days": settings["maximum_age_days"],
            "minimum_weighted_engagement_rate": settings[
                "minimum_weighted_engagement_rate"
            ],
            "requires_downloadable_video": settings["requires_downloadable_video"],
            "exclusion_terms": settings["exclusion_terms"],
        },
    }


def _json_dumps(value: Any) -> str:
    return dump_json(value)


def _json_loads(value: Any) -> dict[str, Any]:
    loaded = load_json(value, {})
    return loaded if isinstance(loaded, dict) else {}
