from __future__ import annotations

import sqlite3
from pathlib import Path


DASHBOARD_DB_PATH = Path("data") / "dashboard" / "dashboard.sqlite3"

MUTABLE_TABLES = (
    "video_curation",
    "scrape_settings_versions",
    "recommendations",
    "candidate_patterns",
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
            exclude_similar_reason TEXT NOT NULL DEFAULT '',
            note TEXT NOT NULL DEFAULT '',
            {ATTRIBUTION_COLUMNS}
        )
        """
    )
    _ensure_column(connection, "video_curation", "exclude_similar_reason", "TEXT NOT NULL DEFAULT ''")
    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS scrape_settings_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version INTEGER NOT NULL,
            settings_json TEXT NOT NULL,
            old_settings_json TEXT NOT NULL DEFAULT '{{}}',
            new_settings_json TEXT NOT NULL DEFAULT '{{}}',
            reason TEXT NOT NULL,
            rollback_of_version INTEGER,
            is_active INTEGER NOT NULL DEFAULT 0,
            {ATTRIBUTION_COLUMNS}
        )
        """
    )
    _ensure_column(connection, "scrape_settings_versions", "old_settings_json", "TEXT NOT NULL DEFAULT '{}'")
    _ensure_column(connection, "scrape_settings_versions", "new_settings_json", "TEXT NOT NULL DEFAULT '{}'")
    _ensure_column(connection, "scrape_settings_versions", "rollback_of_version", "INTEGER")
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
        CREATE TABLE IF NOT EXISTS candidate_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fingerprint TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'candidate',
            pattern_json TEXT NOT NULL DEFAULT '{{}}',
            source_run_id TEXT,
            {ATTRIBUTION_COLUMNS}
        )
        """
    )
    _ensure_column(connection, "candidate_patterns", "source_run_id", "TEXT")
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
        """
        CREATE TABLE IF NOT EXISTS approved_pattern_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_id INTEGER NOT NULL,
            version INTEGER NOT NULL,
            change_type TEXT NOT NULL,
            pattern_json TEXT NOT NULL DEFAULT '{}',
            changed_by TEXT NOT NULL DEFAULT 'local',
            changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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
            run_id TEXT,
            run_type TEXT NOT NULL,
            source_type TEXT NOT NULL DEFAULT 'manual',
            status TEXT NOT NULL DEFAULT 'queued',
            config_version TEXT NOT NULL DEFAULT 'v0',
            triggered_by TEXT NOT NULL DEFAULT 'local',
            triggered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            command_json TEXT NOT NULL DEFAULT '[]',
            output_path TEXT,
            output_paths_json TEXT NOT NULL DEFAULT '{{}}',
            error_text TEXT NOT NULL DEFAULT '',
            {ATTRIBUTION_COLUMNS}
        )
        """
    )
    _ensure_column(connection, "manual_runs", "run_id", "TEXT")
    _ensure_column(connection, "manual_runs", "source_type", "TEXT NOT NULL DEFAULT 'manual'")
    _ensure_column(connection, "manual_runs", "config_version", "TEXT NOT NULL DEFAULT 'v0'")
    _ensure_column(connection, "manual_runs", "triggered_at", "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP")
    _ensure_column(connection, "manual_runs", "command_json", "TEXT NOT NULL DEFAULT '[]'")
    _ensure_column(connection, "manual_runs", "output_paths_json", "TEXT NOT NULL DEFAULT '{}'")
    _ensure_column(connection, "manual_runs", "error_text", "TEXT NOT NULL DEFAULT ''")
    _create_artifact_tables(connection)


def _ensure_column(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
    definition: str,
) -> None:
    columns = {
        row[1]
        for row in connection.execute(f"PRAGMA table_info({table_name})")
    }
    if column_name not in columns:
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def _create_artifact_tables(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS artifact_sources (
            path TEXT PRIMARY KEY,
            artifact_type TEXT NOT NULL,
            generated_at TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            indexed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS raw_videos (
            video_id TEXT PRIMARY KEY,
            source_artifact_path TEXT NOT NULL,
            tiktok_url TEXT,
            author_handle TEXT,
            caption TEXT,
            hashtags_json TEXT NOT NULL DEFAULT '[]',
            source_input TEXT,
            play_count INTEGER,
            like_count INTEGER,
            comment_count INTEGER,
            share_count INTEGER,
            created_at TEXT,
            is_downloadable INTEGER NOT NULL DEFAULT 0,
            run_id TEXT,
            config_version TEXT,
            selection_status TEXT NOT NULL DEFAULT 'raw',
            raw_json TEXT NOT NULL DEFAULT '{}',
            indexed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS selected_batches (
            path TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            selected_at TEXT,
            candidate_source TEXT,
            selected_candidate_count INTEGER NOT NULL DEFAULT 0,
            raw_json TEXT NOT NULL DEFAULT '{}',
            indexed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS batch_runs (
            run_id TEXT PRIMARY KEY,
            run_folder TEXT NOT NULL,
            run_timestamp TEXT,
            mode TEXT,
            requested_batch_size INTEGER,
            manifest_path TEXT,
            metadata_path TEXT,
            raw_json TEXT NOT NULL DEFAULT '{}',
            indexed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS run_outputs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            artifact_path TEXT NOT NULL,
            artifact_type TEXT NOT NULL,
            label TEXT NOT NULL,
            exists_on_disk INTEGER NOT NULL DEFAULT 0,
            indexed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS documentation_records (
            path TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            doc_type TEXT NOT NULL,
            indexed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS scrape_quality_scores (
            run_id TEXT PRIMARY KEY,
            score INTEGER NOT NULL,
            band TEXT NOT NULL,
            needs_attention INTEGER NOT NULL DEFAULT 0,
            candidate_volume_score INTEGER NOT NULL,
            eligibility_yield_score INTEGER NOT NULL,
            nattome_relevance_score INTEGER NOT NULL,
            freshness_score INTEGER NOT NULL,
            engagement_strength_score INTEGER NOT NULL,
            duplicate_noise_control_score INTEGER NOT NULL,
            drivers_json TEXT NOT NULL DEFAULT '[]',
            computed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS pipeline_health_summaries (
            run_id TEXT PRIMARY KEY,
            severity TEXT NOT NULL,
            status TEXT NOT NULL,
            impact_summary TEXT NOT NULL,
            items_json TEXT NOT NULL DEFAULT '[]',
            computed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
