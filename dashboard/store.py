from __future__ import annotations

import sqlite3
from pathlib import Path


DASHBOARD_DB_PATH = Path("data") / "dashboard" / "dashboard.sqlite3"

MUTABLE_TABLES = (
    "video_curation",
    "scrape_settings_versions",
    "recommendations",
    "approved_patterns",
    "nattome_povs",
    "manual_runs",
)

ATTRIBUTION_COLUMNS = """
    created_by TEXT NOT NULL DEFAULT 'local',
    updated_by TEXT NOT NULL DEFAULT 'local',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
"""


def initialize_dashboard_store(workspace: Path | str = ".") -> Path:
    """Create the dashboard-owned SQLite database and return its path."""
    workspace_path = Path(workspace)
    db_path = workspace_path / DASHBOARD_DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_path)
    try:
        connection.execute("PRAGMA user_version = 1")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS dashboard_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO dashboard_metadata (key, value)
            VALUES ('schema_name', 'nattome_scrape_quality_dashboard')
            """
        )
        _create_mutable_tables(connection)
        connection.commit()
    finally:
        connection.close()

    return db_path


def _create_mutable_tables(connection: sqlite3.Connection) -> None:
    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS video_curation (
            tiktok_video_id TEXT PRIMARY KEY,
            labels TEXT NOT NULL DEFAULT '[]',
            note TEXT NOT NULL DEFAULT '',
            {ATTRIBUTION_COLUMNS}
        )
        """
    )
    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS scrape_settings_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version INTEGER NOT NULL,
            settings_json TEXT NOT NULL,
            reason TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 0,
            {ATTRIBUTION_COLUMNS}
        )
        """
    )
    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recommendation_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            summary TEXT NOT NULL,
            supporting_evidence_json TEXT NOT NULL DEFAULT '[]',
            resolved_at TEXT,
            {ATTRIBUTION_COLUMNS}
        )
        """
    )
    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS approved_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            pattern_json TEXT NOT NULL DEFAULT '{{}}',
            version INTEGER NOT NULL DEFAULT 1,
            {ATTRIBUTION_COLUMNS}
        )
        """
    )
    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS nattome_povs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            pov_json TEXT NOT NULL DEFAULT '{{}}',
            version INTEGER NOT NULL DEFAULT 1,
            {ATTRIBUTION_COLUMNS}
        )
        """
    )
    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS manual_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            triggered_by TEXT NOT NULL DEFAULT 'local',
            output_path TEXT,
            {ATTRIBUTION_COLUMNS}
        )
        """
    )
