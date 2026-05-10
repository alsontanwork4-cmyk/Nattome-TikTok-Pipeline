from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .agent_settings import (
    DEFAULT_AGENT_SETTINGS,
    AGENT_KEYS,
    compile_agent_prompt,
    validate_agent_settings,
)
from .config import DashboardSettings
from .runtime import sanitize_error_summary
from .shell import template_context


GENERATION_FIELDS = (
    "temperature",
    "top_p",
    "top_k",
    "max_output_tokens",
    "candidate_count",
    "presence_penalty",
    "frequency_penalty",
    "seed",
)


def agents_template_context(
    settings: DashboardSettings,
    *,
    user: object,
    versions: list[dict],
    error: str,
    form_settings: dict | None = None,
    trace_events: list[dict] | None = None,
    now: datetime | None = None,
) -> dict:
    normalized_versions = [agent_settings_version_view(version) for version in versions]
    active = next((version for version in normalized_versions if version["is_active"]), None)
    if active is None:
        active = {
            "version": 0,
            "settings": validate_agent_settings(DEFAULT_AGENT_SETTINGS),
            "reason": "Default agent settings",
            "is_active": True,
            "rollback_of_version": None,
            "created_by": "system",
            "created_at": "",
        }
    form = validate_agent_settings(form_settings or active["settings"])
    live_rows = live_agent_rows(
        form,
        active_version=int(active["version"]),
        trace_events=trace_events or [],
        now=now or datetime.now(timezone.utc),
    )
    mascot = live_mascot_state(live_rows)
    return {
        **template_context(settings, page_title="Agents", active_path="/agents"),
        "current_user": user,
        "active": active,
        "versions": normalized_versions,
        "agents": [agent_view(agent_key, form["agents"][agent_key]) for agent_key in AGENT_KEYS],
        "live_agent_rows": live_rows,
        "trace_history": trace_history_rows(trace_events or []),
        "generation_fields": GENERATION_FIELDS,
        "mascot_state": mascot,
        "should_auto_refresh_agents": any(row["state"] == "running" for row in live_rows),
        "error": error,
    }


def agent_settings_version_view(record: dict) -> dict:
    settings = record.get("settings") if isinstance(record.get("settings"), dict) else {}
    return {
        "version": int(record.get("version") or 0),
        "settings": validate_agent_settings(settings or DEFAULT_AGENT_SETTINGS),
        "reason": str(record.get("reason") or ""),
        "is_active": bool(record.get("is_active")),
        "rollback_of_version": record.get("rollback_of_version"),
        "created_by": str(record.get("created_by") or ""),
        "created_at": str(record.get("created_at") or ""),
    }


def agent_view(agent_key: str, agent: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": agent_key,
        "display_name": agent["display_name"],
        "enabled": bool(agent["enabled"]),
        "model": agent["model"],
        "prompt_sections": [
            {"key": key, "label": key.replace("_", " ").title(), "value": value}
            for key, value in agent["prompt_sections"].items()
        ],
        "generation": agent["generation"],
        "advanced_generation_config": json.dumps(
            agent["advanced_generation_config"],
            indent=2,
            sort_keys=True,
        ),
        "compiled_prompt": compile_agent_prompt(agent_key, agent),
    }


def agents_form_payload(form: object) -> dict[str, Any]:
    settings = {"schema_version": 1, "agents": {}}
    for agent_key in AGENT_KEYS:
        default_agent = DEFAULT_AGENT_SETTINGS["agents"][agent_key]
        advanced_text = form_value(form, f"{agent_key}__advanced_generation_config").strip()
        settings["agents"][agent_key] = {
            "display_name": default_agent["display_name"],
            "enabled": f"{agent_key}__enabled" in form,
            "model": form_value(form, f"{agent_key}__model"),
            "prompt_sections": {
                section_key: form_value(form, f"{agent_key}__prompt__{section_key}")
                for section_key in default_agent["prompt_sections"]
            },
            "generation": {
                field: value
                for field in GENERATION_FIELDS
                if (value := form_value(form, f"{agent_key}__{field}")).strip()
            },
            "advanced_generation_config": json.loads(advanced_text) if advanced_text else {},
        }
    return settings


def form_value(form: object, key: str) -> str:
    value = form.get(key) if hasattr(form, "get") else ""
    return str(value or "")


def mascot_state(settings: dict[str, Any]) -> str:
    agents = settings.get("agents") if isinstance(settings, dict) else {}
    if any(not bool((agents.get(agent_key) or {}).get("enabled")) for agent_key in AGENT_KEYS):
        return "disabled"
    return "idle"


def live_agent_rows(
    settings: dict[str, Any],
    *,
    active_version: int,
    trace_events: list[dict],
    now: datetime,
) -> list[dict[str, Any]]:
    agents = settings.get("agents") if isinstance(settings, dict) else {}
    rows = []
    for agent_key in AGENT_KEYS:
        agent = agents.get(agent_key) or {}
        agent_events = _events_for_agent(trace_events, agent_key)
        latest = agent_events[0] if agent_events else {}
        latest_error = next(
            (
                sanitize_error_summary(event.get("error_summary"))
                for event in agent_events
                if sanitize_error_summary(event.get("error_summary"))
            ),
            "",
        )
        state = _agent_state(agent, latest)
        rows.append(
            {
                "key": agent_key,
                "display_name": str(agent.get("display_name") or agent_key),
                "enabled": bool(agent.get("enabled")),
                "model": str(agent.get("model") or ""),
                "config_version": active_version,
                "state": state,
                "state_key": state.replace(" ", "-"),
                "current_candidate": _candidate_reference(latest),
                "elapsed": _elapsed_text(latest, now) if state == "running" else "",
                "latest_error_summary": latest_error,
                "last_completed_at": _last_completed_at(agent_events),
            }
        )
    return rows


def live_mascot_state(rows: list[dict[str, Any]]) -> str:
    states = {str(row.get("state") or "") for row in rows}
    for state in ("failed", "running", "queued", "disabled"):
        if state in states:
            return state
    return "idle"


def trace_history_rows(trace_events: list[dict], *, limit: int = 12) -> list[dict[str, Any]]:
    return [
        {
            "agent": _agent_display_name(str(event.get("agent") or "")),
            "substep": str(event.get("substep") or ""),
            "status": str(event.get("status") or "").lower(),
            "run_id": str(event.get("run_id") or ""),
            "candidate_reference": _candidate_reference(event),
            "started_at": str(event.get("started_at") or ""),
            "ended_at": str(event.get("ended_at") or ""),
            "artifact_references": [
                str(reference)
                for reference in (event.get("artifact_references") or [])
                if str(reference)
            ],
            "error_summary": sanitize_error_summary(event.get("error_summary")),
        }
        for event in _sorted_trace_events(trace_events)[:limit]
    ]


def _events_for_agent(trace_events: list[dict], agent_key: str) -> list[dict]:
    return [
        event
        for event in _sorted_trace_events(trace_events)
        if str(event.get("agent") or "") == agent_key
    ]


def _sorted_trace_events(trace_events: list[dict]) -> list[dict]:
    return sorted(trace_events, key=_event_sort_time, reverse=True)


def _event_sort_time(event: dict) -> datetime:
    return max(
        _parse_datetime(event.get("started_at")),
        _parse_datetime(event.get("ended_at")),
        _parse_datetime(event.get("updated_at")),
    )


def _agent_state(agent: dict[str, Any], latest: dict) -> str:
    if not bool(agent.get("enabled")):
        return "disabled"
    status = str(latest.get("status") or "").lower()
    if status in {"queued", "running", "failed", "disabled"}:
        return status
    if status in {"completed", "succeeded", "success"}:
        return "last succeeded"
    return "idle"


def _candidate_reference(event: dict) -> str:
    return str(event.get("candidate_prefix") or event.get("candidate_id") or "")


def _elapsed_text(event: dict, now: datetime) -> str:
    started_at = _parse_datetime(event.get("started_at"))
    ended_at = _parse_datetime(event.get("ended_at"))
    end = ended_at if ended_at != datetime.min.replace(tzinfo=timezone.utc) else _as_utc(now)
    seconds = max(0, int((end - started_at).total_seconds()))
    minutes, remaining_seconds = divmod(seconds, 60)
    hours, remaining_minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {remaining_minutes}m"
    if minutes:
        return f"{minutes}m {remaining_seconds}s"
    return f"{remaining_seconds}s"


def _last_completed_at(events: list[dict]) -> str:
    for event in events:
        if str(event.get("status") or "").lower() in {"completed", "succeeded", "success"}:
            return str(event.get("ended_at") or event.get("started_at") or "")
    return ""


def _agent_display_name(agent_key: str) -> str:
    default_agent = DEFAULT_AGENT_SETTINGS["agents"].get(agent_key)
    if default_agent:
        return str(default_agent["display_name"])
    return agent_key


def _parse_datetime(value: object) -> datetime:
    text = str(value or "").strip()
    if not text:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)
    return _as_utc(parsed)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
