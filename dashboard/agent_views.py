from __future__ import annotations

import json
from typing import Any

from .agent_settings import (
    DEFAULT_AGENT_SETTINGS,
    AGENT_KEYS,
    compile_agent_prompt,
    validate_agent_settings,
)
from .config import DashboardSettings
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
    return {
        **template_context(settings, page_title="Agents", active_path="/agents"),
        "current_user": user,
        "active": active,
        "versions": normalized_versions,
        "agents": [agent_view(agent_key, form["agents"][agent_key]) for agent_key in AGENT_KEYS],
        "generation_fields": GENERATION_FIELDS,
        "mascot_state": mascot_state(form),
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
