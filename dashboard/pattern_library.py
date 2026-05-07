from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any

from .indexer import index_pipeline_artifacts
from .store import connect_dashboard_store, dump_json


APPROVED_PATTERN_STATUSES = {"draft", "approved", "archived"}


@dataclass(frozen=True)
class CandidatePattern:
    id: int
    status: str
    pattern_name: str
    hook_type: str
    format_type: str
    emotional_trigger: str
    source_videos: list[dict[str, object]]
    why_it_works: str
    performance_evidence: dict[str, object]
    source_run_id: str


@dataclass(frozen=True)
class ApprovedPattern:
    id: int
    pattern_name: str
    status: str
    hook_type: str
    format_type: str
    emotional_trigger: str
    source_videos: list[dict[str, object]]
    why_it_works: str
    nattome_adaptation_notes: str
    shoot_difficulty: str
    freshness: str
    performance_evidence: dict[str, object]
    approval_metadata: dict[str, object]
    related_povs: list[str]
    avoid_notes: str
    targeting: dict[str, object]
    version: int
    source_candidate_id: int | None
    created_by: str
    updated_by: str


@dataclass(frozen=True)
class PatternVersion:
    id: int
    pattern_id: int
    version: int
    change_type: str
    changed_by: str
    changed_at: str
    pattern: ApprovedPattern


def generate_candidate_patterns(
    workspace: Path | str = ".",
    *,
    user: str = "local",
) -> list[CandidatePattern]:
    workspace_path = Path(workspace)
    index_pipeline_artifacts(workspace_path)
    connection = connect_dashboard_store(workspace_path)
    try:
        videos = _load_pattern_source_videos(connection)
        if not videos:
            return list_candidate_patterns(workspace_path)
        payload = _candidate_payload(videos)
        fingerprint = _candidate_fingerprint(payload)
        connection.execute(
            """
            INSERT INTO candidate_patterns (
                fingerprint,
                status,
                pattern_json,
                source_run_id,
                created_by,
                updated_by,
                updated_at
            )
            VALUES (?, 'candidate', ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(fingerprint) DO UPDATE SET
                pattern_json = excluded.pattern_json,
                source_run_id = excluded.source_run_id,
                updated_by = excluded.updated_by,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                fingerprint,
                _json_dumps(payload),
                str(payload.get("source_run_id") or ""),
                user,
                user,
            ),
        )
        connection.commit()
        return _fetch_candidate_patterns(connection)
    finally:
        connection.close()


def list_candidate_patterns(workspace: Path | str = ".") -> list[CandidatePattern]:
    connection = connect_dashboard_store(workspace)
    try:
        return _fetch_candidate_patterns(connection)
    finally:
        connection.close()


def approve_candidate_pattern(
    workspace: Path | str,
    candidate_id: int,
    *,
    user: str = "local",
    notes: str = "",
) -> ApprovedPattern:
    connection = connect_dashboard_store(workspace)
    try:
        candidate = _candidate_by_id(connection, candidate_id)
        if candidate is None:
            raise ValueError(f"Candidate pattern {candidate_id} was not found")
        payload = _approved_payload_from_candidate(candidate, user=user, notes=notes)
        cursor = connection.execute(
            """
            INSERT INTO approved_patterns (
                name,
                status,
                pattern_json,
                version,
                created_by,
                updated_by,
                updated_at
            )
            VALUES (?, 'approved', ?, 1, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                str(payload["pattern_name"]),
                _json_dumps(payload),
                user,
                user,
            ),
        )
        pattern_id = int(cursor.lastrowid)
        approved = _approved_by_id(connection, pattern_id)
        _record_version(connection, approved, "approved", user)
        connection.commit()
        return approved
    finally:
        connection.close()


def create_approved_pattern(
    workspace: Path | str,
    fields: dict[str, object],
    *,
    user: str = "local",
    status: str = "draft",
) -> ApprovedPattern:
    if status not in APPROVED_PATTERN_STATUSES:
        raise ValueError(f"Invalid pattern status: {status}")
    connection = connect_dashboard_store(workspace)
    try:
        payload = _approved_payload(fields)
        cursor = connection.execute(
            """
            INSERT INTO approved_patterns (
                name,
                status,
                pattern_json,
                version,
                created_by,
                updated_by,
                updated_at
            )
            VALUES (?, ?, ?, 1, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                str(payload["pattern_name"]),
                status,
                _json_dumps(payload),
                user,
                user,
            ),
        )
        approved = _approved_by_id(connection, int(cursor.lastrowid))
        _record_version(connection, approved, "created", user)
        connection.commit()
        return approved
    finally:
        connection.close()


def update_approved_pattern(
    workspace: Path | str,
    pattern_id: int,
    fields: dict[str, object],
    *,
    user: str = "local",
) -> ApprovedPattern:
    connection = connect_dashboard_store(workspace)
    try:
        current = _approved_by_id(connection, pattern_id)
        merged = _approved_payload({**_approved_to_payload(current), **fields})
        status = str(fields.get("status") or current.status)
        if status not in APPROVED_PATTERN_STATUSES:
            raise ValueError(f"Invalid pattern status: {status}")
        version = current.version + 1
        connection.execute(
            """
            UPDATE approved_patterns
            SET name = ?,
                status = ?,
                pattern_json = ?,
                version = ?,
                updated_by = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                str(merged["pattern_name"]),
                status,
                _json_dumps(merged),
                version,
                user,
                pattern_id,
            ),
        )
        updated = _approved_by_id(connection, pattern_id)
        _record_version(connection, updated, "edited", user)
        connection.commit()
        return updated
    finally:
        connection.close()


def archive_approved_pattern(
    workspace: Path | str,
    pattern_id: int,
    *,
    user: str = "local",
) -> ApprovedPattern:
    connection = connect_dashboard_store(workspace)
    try:
        current = _approved_by_id(connection, pattern_id)
        version = current.version + 1
        connection.execute(
            """
            UPDATE approved_patterns
            SET status = 'archived',
                version = ?,
                updated_by = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (version, user, pattern_id),
        )
        archived = _approved_by_id(connection, pattern_id)
        _record_version(connection, archived, "archived", user)
        connection.commit()
        return archived
    finally:
        connection.close()


def list_approved_patterns(workspace: Path | str = ".") -> list[ApprovedPattern]:
    connection = connect_dashboard_store(workspace)
    try:
        rows = connection.execute(
            """
            SELECT *
            FROM approved_patterns
            ORDER BY status = 'archived', updated_at DESC, id DESC
            """
        ).fetchall()
        return [_approved_from_row(row) for row in rows]
    finally:
        connection.close()


def list_pattern_versions(
    workspace: Path | str,
    pattern_id: int,
) -> list[PatternVersion]:
    connection = connect_dashboard_store(workspace)
    try:
        rows = connection.execute(
            """
            SELECT *
            FROM approved_pattern_versions
            WHERE pattern_id = ?
            ORDER BY version
            """,
            (pattern_id,),
        ).fetchall()
        return [_version_from_row(row) for row in rows]
    finally:
        connection.close()


def _load_pattern_source_videos(connection: sqlite3.Connection) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT
            video_id,
            tiktok_url,
            author_handle,
            caption,
            hashtags_json,
            source_input,
            play_count,
            like_count,
            comment_count,
            share_count,
            created_at,
            run_id,
            source_artifact_path,
            selection_status
        FROM raw_videos
        WHERE selection_status IN ('eligible', 'selected', 'analyzed')
        ORDER BY run_id DESC, play_count DESC, video_id
        LIMIT 12
        """
    ).fetchall()
    return [dict(row) for row in rows]


def _candidate_payload(videos: list[dict[str, object]]) -> dict[str, object]:
    source_videos = [_source_video(video) for video in videos]
    captions = " ".join(str(video.get("caption") or "") for video in videos)
    hook_type = _infer_hook_type(captions)
    format_type = _infer_format_type(captions)
    emotional_trigger = _infer_emotional_trigger(captions)
    return {
        "pattern_name": _pattern_name(captions, hook_type, format_type),
        "hook_type": hook_type,
        "format_type": format_type,
        "emotional_trigger": emotional_trigger,
        "source_videos": source_videos,
        "why_it_works": _why_it_works(hook_type, format_type, emotional_trigger),
        "performance_evidence": _performance_evidence(videos),
        "source_run_id": str(videos[0].get("run_id") or ""),
    }


def _source_video(video: dict[str, object]) -> dict[str, object]:
    return {
        "video_id": str(video.get("video_id") or ""),
        "tiktok_url": str(video.get("tiktok_url") or ""),
        "author_handle": str(video.get("author_handle") or ""),
        "caption": str(video.get("caption") or ""),
        "source_input": str(video.get("source_input") or ""),
        "run_id": str(video.get("run_id") or ""),
        "source_artifact_path": str(video.get("source_artifact_path") or ""),
    }


def _candidate_fingerprint(payload: dict[str, object]) -> str:
    video_ids = [
        str(video.get("video_id"))
        for video in payload.get("source_videos", [])
        if isinstance(video, dict)
    ]
    return "|".join(
        [
            str(payload.get("hook_type") or ""),
            str(payload.get("format_type") or ""),
            str(payload.get("emotional_trigger") or ""),
            ",".join(sorted(video_ids)),
        ]
    )


def _infer_hook_type(captions: str) -> str:
    text = captions.lower()
    if "?" in text or any(term in text for term in ["bloating", "discomfort", "problem"]):
        return "problem_solution"
    if any(term in text for term in ["myth", "mistake", "wrong"]):
        return "myth_bust"
    return "demonstration"


def _infer_format_type(captions: str) -> str:
    text = captions.lower()
    if "routine" in text or "demo" in text:
        return "routine_demo"
    if "pov" in text:
        return "pov_scene"
    return "talking_head"


def _infer_emotional_trigger(captions: str) -> str:
    text = captions.lower()
    if any(term in text for term in ["relief", "discomfort", "bloating"]):
        return "relief"
    if any(term in text for term in ["confidence", "ready", "before work"]):
        return "confidence"
    return "curiosity"


def _pattern_name(captions: str, hook_type: str, format_type: str) -> str:
    text = captions.lower()
    if "bloating" in text and format_type == "routine_demo":
        return "Bloating relief routine demo"
    return f"{hook_type.replace('_', ' ').title()} {format_type.replace('_', ' ').title()}"


def _why_it_works(hook_type: str, format_type: str, emotional_trigger: str) -> str:
    return (
        f"External TikTok mechanic pairs a {hook_type.replace('_', ' ')} hook "
        f"with a {format_type.replace('_', ' ')} format to create {emotional_trigger}."
    )


def _performance_evidence(videos: list[dict[str, object]]) -> dict[str, object]:
    views = [_int_value(video.get("play_count")) for video in videos]
    likes = [_int_value(video.get("like_count")) for video in videos]
    comments = [_int_value(video.get("comment_count")) for video in videos]
    shares = [_int_value(video.get("share_count")) for video in videos]
    return {
        "source_video_count": len(videos),
        "median_views": int(median(views)) if views else 0,
        "total_likes": sum(likes),
        "total_comments": sum(comments),
        "total_shares": sum(shares),
    }


def _approved_payload_from_candidate(
    candidate: CandidatePattern,
    *,
    user: str,
    notes: str,
) -> dict[str, object]:
    return _approved_payload(
        {
            "pattern_name": candidate.pattern_name,
            "hook_type": candidate.hook_type,
            "format_type": candidate.format_type,
            "emotional_trigger": candidate.emotional_trigger,
            "source_videos": candidate.source_videos,
            "why_it_works": candidate.why_it_works,
            "nattome_adaptation_notes": "",
            "shoot_difficulty": "",
            "freshness": "",
            "performance_evidence": candidate.performance_evidence,
            "approval_metadata": {
                "approved_by": user,
                "approval_notes": notes,
                "source_candidate_id": candidate.id,
            },
            "related_povs": [],
            "avoid_notes": "",
            "targeting": {},
            "source_candidate_id": candidate.id,
        }
    )


def _approved_payload(fields: dict[str, object]) -> dict[str, object]:
    return {
        "pattern_name": str(fields.get("pattern_name") or fields.get("name") or "Untitled pattern"),
        "hook_type": str(fields.get("hook_type") or ""),
        "format_type": str(fields.get("format_type") or ""),
        "emotional_trigger": str(fields.get("emotional_trigger") or ""),
        "source_videos": _list_of_dicts(fields.get("source_videos")),
        "why_it_works": str(fields.get("why_it_works") or ""),
        "nattome_adaptation_notes": str(fields.get("nattome_adaptation_notes") or ""),
        "shoot_difficulty": str(fields.get("shoot_difficulty") or ""),
        "freshness": str(fields.get("freshness") or ""),
        "performance_evidence": _dict_value(fields.get("performance_evidence")),
        "approval_metadata": _dict_value(fields.get("approval_metadata")),
        "related_povs": [str(item) for item in _list_value(fields.get("related_povs"))],
        "avoid_notes": str(fields.get("avoid_notes") or ""),
        "targeting": _dict_value(fields.get("targeting")),
        "source_candidate_id": _optional_int(fields.get("source_candidate_id")),
    }


def _approved_to_payload(pattern: ApprovedPattern) -> dict[str, object]:
    return {
        "pattern_name": pattern.pattern_name,
        "hook_type": pattern.hook_type,
        "format_type": pattern.format_type,
        "emotional_trigger": pattern.emotional_trigger,
        "source_videos": pattern.source_videos,
        "why_it_works": pattern.why_it_works,
        "nattome_adaptation_notes": pattern.nattome_adaptation_notes,
        "shoot_difficulty": pattern.shoot_difficulty,
        "freshness": pattern.freshness,
        "performance_evidence": pattern.performance_evidence,
        "approval_metadata": pattern.approval_metadata,
        "related_povs": pattern.related_povs,
        "avoid_notes": pattern.avoid_notes,
        "targeting": pattern.targeting,
        "source_candidate_id": pattern.source_candidate_id,
    }


def _fetch_candidate_patterns(connection: sqlite3.Connection) -> list[CandidatePattern]:
    rows = connection.execute(
        """
        SELECT *
        FROM candidate_patterns
        WHERE status = 'candidate'
        ORDER BY updated_at DESC, id DESC
        """
    ).fetchall()
    return [_candidate_from_row(row) for row in rows]


def _candidate_by_id(
    connection: sqlite3.Connection,
    candidate_id: int,
) -> CandidatePattern | None:
    row = connection.execute(
        "SELECT * FROM candidate_patterns WHERE id = ?",
        (candidate_id,),
    ).fetchone()
    return _candidate_from_row(row) if row else None


def _approved_by_id(connection: sqlite3.Connection, pattern_id: int) -> ApprovedPattern:
    row = connection.execute(
        "SELECT * FROM approved_patterns WHERE id = ?",
        (pattern_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Approved pattern {pattern_id} was not found")
    return _approved_from_row(row)


def _candidate_from_row(row: sqlite3.Row) -> CandidatePattern:
    payload = _json_loads(row["pattern_json"])
    return CandidatePattern(
        id=int(row["id"]),
        status=str(row["status"]),
        pattern_name=str(payload.get("pattern_name") or "Untitled pattern"),
        hook_type=str(payload.get("hook_type") or ""),
        format_type=str(payload.get("format_type") or ""),
        emotional_trigger=str(payload.get("emotional_trigger") or ""),
        source_videos=_list_of_dicts(payload.get("source_videos")),
        why_it_works=str(payload.get("why_it_works") or ""),
        performance_evidence=_dict_value(payload.get("performance_evidence")),
        source_run_id=str(row["source_run_id"] or payload.get("source_run_id") or ""),
    )


def _approved_from_row(row: sqlite3.Row) -> ApprovedPattern:
    payload = _approved_payload(_json_loads(row["pattern_json"]))
    return ApprovedPattern(
        id=int(row["id"]),
        pattern_name=str(payload["pattern_name"]),
        status=str(row["status"]),
        hook_type=str(payload["hook_type"]),
        format_type=str(payload["format_type"]),
        emotional_trigger=str(payload["emotional_trigger"]),
        source_videos=_list_of_dicts(payload["source_videos"]),
        why_it_works=str(payload["why_it_works"]),
        nattome_adaptation_notes=str(payload["nattome_adaptation_notes"]),
        shoot_difficulty=str(payload["shoot_difficulty"]),
        freshness=str(payload["freshness"]),
        performance_evidence=_dict_value(payload["performance_evidence"]),
        approval_metadata=_dict_value(payload["approval_metadata"]),
        related_povs=[str(item) for item in _list_value(payload["related_povs"])],
        avoid_notes=str(payload["avoid_notes"]),
        targeting=_dict_value(payload["targeting"]),
        version=int(row["version"]),
        source_candidate_id=_optional_int(payload.get("source_candidate_id")),
        created_by=str(row["created_by"]),
        updated_by=str(row["updated_by"]),
    )


def _version_from_row(row: sqlite3.Row) -> PatternVersion:
    payload = _approved_payload(_json_loads(row["pattern_json"]))
    pattern = ApprovedPattern(
        id=int(row["pattern_id"]),
        pattern_name=str(payload["pattern_name"]),
        status=str(payload.get("status") or ""),
        hook_type=str(payload["hook_type"]),
        format_type=str(payload["format_type"]),
        emotional_trigger=str(payload["emotional_trigger"]),
        source_videos=_list_of_dicts(payload["source_videos"]),
        why_it_works=str(payload["why_it_works"]),
        nattome_adaptation_notes=str(payload["nattome_adaptation_notes"]),
        shoot_difficulty=str(payload["shoot_difficulty"]),
        freshness=str(payload["freshness"]),
        performance_evidence=_dict_value(payload["performance_evidence"]),
        approval_metadata=_dict_value(payload["approval_metadata"]),
        related_povs=[str(item) for item in _list_value(payload["related_povs"])],
        avoid_notes=str(payload["avoid_notes"]),
        targeting=_dict_value(payload["targeting"]),
        version=int(row["version"]),
        source_candidate_id=_optional_int(payload.get("source_candidate_id")),
        created_by=str(row["changed_by"]),
        updated_by=str(row["changed_by"]),
    )
    return PatternVersion(
        id=int(row["id"]),
        pattern_id=int(row["pattern_id"]),
        version=int(row["version"]),
        change_type=str(row["change_type"]),
        changed_by=str(row["changed_by"]),
        changed_at=str(row["changed_at"]),
        pattern=pattern,
    )


def _record_version(
    connection: sqlite3.Connection,
    pattern: ApprovedPattern,
    change_type: str,
    user: str,
) -> None:
    payload = _approved_to_payload(pattern)
    payload["status"] = pattern.status
    connection.execute(
        """
        INSERT INTO approved_pattern_versions (
            pattern_id,
            version,
            change_type,
            pattern_json,
            changed_by
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            pattern.id,
            pattern.version,
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


def _list_of_dicts(value: object) -> list[dict[str, object]]:
    return [item for item in _list_value(value) if isinstance(item, dict)]


def _dict_value(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _optional_int(value: object) -> int | None:
    if value in {None, ""}:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _int_value(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


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
