from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .store import connect_dashboard_store, dump_json


NATTOME_POV_STATUSES = {"draft", "approved", "archived"}


@dataclass(frozen=True)
class NattomePov:
    id: int
    title: str
    description: str
    brand_safe_interpretation: str
    adaptation_rules: str
    product: str
    campaign: str
    market: str
    language: str
    audience_avatar: str
    symptom_occasion: str
    channel: str
    status: str
    source_links: list[str]
    linked_pattern_ids: list[int]
    version: int
    created_by: str
    updated_by: str


@dataclass(frozen=True)
class NattomePovVersion:
    id: int
    pov_id: int
    version: int
    change_type: str
    changed_by: str
    changed_at: str
    pov: NattomePov


def create_nattome_pov(
    workspace: Path | str,
    fields: dict[str, object],
    *,
    user: str = "local",
    status: str = "draft",
) -> NattomePov:
    if status not in NATTOME_POV_STATUSES:
        raise ValueError(f"Invalid Nattome POV status: {status}")
    connection = connect_dashboard_store(workspace)
    try:
        _ensure_pov_version_table(connection)
        payload = _pov_payload(fields)
        cursor = connection.execute(
            """
            INSERT INTO nattome_povs (
                name,
                status,
                pov_json,
                version,
                created_by,
                updated_by,
                updated_at
            )
            VALUES (?, ?, ?, 1, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                str(payload["title"]),
                status,
                _json_dumps(payload),
                user,
                user,
            ),
        )
        pov = _pov_by_id(connection, int(cursor.lastrowid))
        _record_version(connection, pov, "created", user)
        connection.commit()
        return pov
    finally:
        connection.close()


def update_nattome_pov(
    workspace: Path | str,
    pov_id: int,
    fields: dict[str, object],
    *,
    user: str = "local",
) -> NattomePov:
    connection = connect_dashboard_store(workspace)
    try:
        _ensure_pov_version_table(connection)
        current = _pov_by_id(connection, pov_id)
        merged = _pov_payload({**_pov_to_payload(current), **fields})
        status = str(fields.get("status") or current.status)
        if status not in NATTOME_POV_STATUSES:
            raise ValueError(f"Invalid Nattome POV status: {status}")
        version = current.version + 1
        connection.execute(
            """
            UPDATE nattome_povs
            SET name = ?,
                status = ?,
                pov_json = ?,
                version = ?,
                updated_by = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                str(merged["title"]),
                status,
                _json_dumps(merged),
                version,
                user,
                pov_id,
            ),
        )
        updated = _pov_by_id(connection, pov_id)
        _record_version(connection, updated, "edited", user)
        connection.commit()
        return updated
    finally:
        connection.close()


def archive_nattome_pov(
    workspace: Path | str,
    pov_id: int,
    *,
    user: str = "local",
) -> NattomePov:
    connection = connect_dashboard_store(workspace)
    try:
        _ensure_pov_version_table(connection)
        current = _pov_by_id(connection, pov_id)
        version = current.version + 1
        connection.execute(
            """
            UPDATE nattome_povs
            SET status = 'archived',
                version = ?,
                updated_by = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (version, user, pov_id),
        )
        archived = _pov_by_id(connection, pov_id)
        _record_version(connection, archived, "archived", user)
        connection.commit()
        return archived
    finally:
        connection.close()


def list_nattome_povs(workspace: Path | str = ".") -> list[NattomePov]:
    connection = connect_dashboard_store(workspace)
    try:
        _ensure_pov_version_table(connection)
        rows = connection.execute(
            """
            SELECT *
            FROM nattome_povs
            ORDER BY status = 'archived', updated_at DESC, id DESC
            """
        ).fetchall()
        return [_pov_from_row(row) for row in rows]
    finally:
        connection.close()


def list_nattome_pov_versions(
    workspace: Path | str,
    pov_id: int,
) -> list[NattomePovVersion]:
    connection = connect_dashboard_store(workspace)
    try:
        _ensure_pov_version_table(connection)
        rows = connection.execute(
            """
            SELECT *
            FROM nattome_pov_versions
            WHERE pov_id = ?
            ORDER BY version
            """,
            (pov_id,),
        ).fetchall()
        return [_version_from_row(row) for row in rows]
    finally:
        connection.close()


def _ensure_pov_version_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS nattome_pov_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pov_id INTEGER NOT NULL,
            version INTEGER NOT NULL,
            change_type TEXT NOT NULL,
            pov_json TEXT NOT NULL DEFAULT '{}',
            changed_by TEXT NOT NULL DEFAULT 'local',
            changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _pov_by_id(connection: sqlite3.Connection, pov_id: int) -> NattomePov:
    row = connection.execute(
        "SELECT * FROM nattome_povs WHERE id = ?",
        (pov_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Nattome POV {pov_id} was not found")
    return _pov_from_row(row)


def _pov_payload(fields: dict[str, object]) -> dict[str, object]:
    return {
        "title": str(fields.get("title") or fields.get("name") or "Untitled Nattome POV"),
        "description": str(fields.get("description") or ""),
        "brand_safe_interpretation": str(fields.get("brand_safe_interpretation") or ""),
        "adaptation_rules": str(fields.get("adaptation_rules") or ""),
        "product": str(fields.get("product") or "Nattome"),
        "campaign": str(fields.get("campaign") or ""),
        "market": str(fields.get("market") or "Malaysia"),
        "language": str(fields.get("language") or "mixed/English"),
        "audience_avatar": str(fields.get("audience_avatar") or ""),
        "symptom_occasion": str(fields.get("symptom_occasion") or ""),
        "channel": str(fields.get("channel") or "TikTok"),
        "source_links": [str(item) for item in _list_value(fields.get("source_links"))],
        "linked_pattern_ids": _int_list(fields.get("linked_pattern_ids")),
    }


def _pov_to_payload(pov: NattomePov) -> dict[str, object]:
    return {
        "title": pov.title,
        "description": pov.description,
        "brand_safe_interpretation": pov.brand_safe_interpretation,
        "adaptation_rules": pov.adaptation_rules,
        "product": pov.product,
        "campaign": pov.campaign,
        "market": pov.market,
        "language": pov.language,
        "audience_avatar": pov.audience_avatar,
        "symptom_occasion": pov.symptom_occasion,
        "channel": pov.channel,
        "source_links": pov.source_links,
        "linked_pattern_ids": pov.linked_pattern_ids,
    }


def _pov_from_row(row: sqlite3.Row) -> NattomePov:
    payload = _pov_payload(_json_loads(row["pov_json"]))
    return NattomePov(
        id=int(row["id"]),
        title=str(payload["title"]),
        description=str(payload["description"]),
        brand_safe_interpretation=str(payload["brand_safe_interpretation"]),
        adaptation_rules=str(payload["adaptation_rules"]),
        product=str(payload["product"]),
        campaign=str(payload["campaign"]),
        market=str(payload["market"]),
        language=str(payload["language"]),
        audience_avatar=str(payload["audience_avatar"]),
        symptom_occasion=str(payload["symptom_occasion"]),
        channel=str(payload["channel"]),
        status=str(row["status"]),
        source_links=[str(item) for item in _list_value(payload["source_links"])],
        linked_pattern_ids=_int_list(payload["linked_pattern_ids"]),
        version=int(row["version"]),
        created_by=str(row["created_by"]),
        updated_by=str(row["updated_by"]),
    )


def _version_from_row(row: sqlite3.Row) -> NattomePovVersion:
    payload = _pov_payload(_json_loads(row["pov_json"]))
    pov = NattomePov(
        id=int(row["pov_id"]),
        title=str(payload["title"]),
        description=str(payload["description"]),
        brand_safe_interpretation=str(payload["brand_safe_interpretation"]),
        adaptation_rules=str(payload["adaptation_rules"]),
        product=str(payload["product"]),
        campaign=str(payload["campaign"]),
        market=str(payload["market"]),
        language=str(payload["language"]),
        audience_avatar=str(payload["audience_avatar"]),
        symptom_occasion=str(payload["symptom_occasion"]),
        channel=str(payload["channel"]),
        status=str(_json_loads(row["pov_json"]).get("status") or ""),
        source_links=[str(item) for item in _list_value(payload["source_links"])],
        linked_pattern_ids=_int_list(payload["linked_pattern_ids"]),
        version=int(row["version"]),
        created_by=str(row["changed_by"]),
        updated_by=str(row["changed_by"]),
    )
    return NattomePovVersion(
        id=int(row["id"]),
        pov_id=int(row["pov_id"]),
        version=int(row["version"]),
        change_type=str(row["change_type"]),
        changed_by=str(row["changed_by"]),
        changed_at=str(row["changed_at"]),
        pov=pov,
    )


def _record_version(
    connection: sqlite3.Connection,
    pov: NattomePov,
    change_type: str,
    user: str,
) -> None:
    payload = _pov_to_payload(pov)
    payload["status"] = pov.status
    connection.execute(
        """
        INSERT INTO nattome_pov_versions (
            pov_id,
            version,
            change_type,
            pov_json,
            changed_by
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            pov.id,
            pov.version,
            change_type,
            _json_dumps(payload),
            user,
        ),
    )


def _list_value(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.strip():
        return [item.strip() for item in value.splitlines() if item.strip()]
    return []


def _int_list(value: object) -> list[int]:
    ids = []
    for item in _list_value(value):
        try:
            ids.append(int(item))
        except (TypeError, ValueError):
            continue
    return ids


def _json_loads(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return {}
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _json_dumps(value: object) -> str:
    return dump_json(value)
