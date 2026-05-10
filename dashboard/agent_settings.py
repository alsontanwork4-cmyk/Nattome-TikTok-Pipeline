from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from batch_analysis.gemini_reports import DEFAULT_GEMINI_MODEL, NATTOME_POV_REPORT_OUTLINE


AGENT_KEYS = ("gemini_video_evidence", "nattome_creative_strategy")
POLISHED_GENERATION_KEYS = frozenset(
    {
        "temperature",
        "top_p",
        "top_k",
        "max_output_tokens",
        "candidate_count",
        "presence_penalty",
        "frequency_penalty",
        "seed",
    }
)
SUPPORTED_ADVANCED_GENERATION_KEYS = frozenset(
    {
        "response_mime_type",
        "response_schema",
        "stop_sequences",
        "thinking_config",
        "safety_settings",
        *POLISHED_GENERATION_KEYS,
    }
)

DEFAULT_AGENT_SETTINGS: dict[str, Any] = {
    "schema_version": 1,
    "agents": {
        "gemini_video_evidence": {
            "display_name": "Gemini Video Evidence Agent",
            "enabled": True,
            "model": DEFAULT_GEMINI_MODEL,
            "prompt_sections": {
                "role": "Watch one TikTok source video and extract observable evidence only.",
                "input_contract": (
                    "Use one uploaded source video and the candidate metadata JSON supplied "
                    "by the pipeline."
                ),
                "output_contract": (
                    "Return compact JSON with timestamped visual observations, spoken "
                    "content notes, visible text, hook evidence, pacing/editing notes, "
                    "emotional triggers, creator behavior, claim evidence, and uncertainty notes."
                ),
                "safety": (
                    "Use timestamps wherever possible. Distinguish observed evidence from "
                    "interpretation and do not infer unsupported clinical outcomes."
                ),
            },
            "generation": {
                "temperature": 0.2,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,
            },
            "advanced_generation_config": {"response_mime_type": "application/json"},
        },
        "nattome_creative_strategy": {
            "display_name": "Nattome Creative Strategist Agent",
            "enabled": True,
            "model": DEFAULT_GEMINI_MODEL,
            "prompt_sections": {
                "role": "Write a marketer-facing Nattome POV inspiration report from evidence.",
                "input_contract": (
                    "Use the Evidence Analyst output JSON, candidate metadata JSON, and "
                    "the fixed Nattome brand POV reference."
                ),
                "creative_direction": (
                    "Write a specific, non-generic report for a marketer planning a shoot. "
                    "Ground recommendations in observable video evidence or explicit Nattome "
                    "brand guidance."
                ),
                "report_outline": NATTOME_POV_REPORT_OUTLINE,
                "claim_safety": (
                    "Do not invent clinical claims, product outcomes, doctor recommendations, "
                    "guaranteed relief, cure language, or disease-prevention claims."
                ),
            },
            "generation": {
                "temperature": 0.45,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,
            },
            "advanced_generation_config": {},
        },
    },
}


def validate_agent_settings(raw_settings: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw_settings, dict):
        raise ValueError("agent settings must be an object")
    if _contains_key(raw_settings, "GEMINI_API_KEY"):
        raise ValueError("GEMINI_API_KEY must not be stored in dashboard-managed agent config")

    agents = raw_settings.get("agents")
    if not isinstance(agents, dict):
        raise ValueError("agent settings must include an agents object")

    normalized = {"schema_version": 1, "agents": {}}
    for agent_key in AGENT_KEYS:
        if agent_key not in agents:
            raise ValueError(f"missing agent config: {agent_key}")
        default_agent = DEFAULT_AGENT_SETTINGS["agents"][agent_key]
        raw_agent = agents[agent_key]
        if not isinstance(raw_agent, dict):
            raise ValueError(f"{agent_key} config must be an object")
        normalized["agents"][agent_key] = _normalize_agent(agent_key, raw_agent, default_agent)

    extra_agents = set(agents) - set(AGENT_KEYS)
    if extra_agents:
        raise ValueError(f"unsupported agent config: {', '.join(sorted(extra_agents))}")
    return normalized


def compile_agent_prompt(agent_key: str, agent_config: dict[str, Any]) -> str:
    if agent_key not in AGENT_KEYS:
        raise ValueError(f"unsupported agent config: {agent_key}")
    prompt_sections = agent_config.get("prompt_sections") or {}
    lines: list[str] = [str(agent_config.get("display_name") or agent_key), ""]
    for section_key, section_text in prompt_sections.items():
        lines.extend([_section_title(section_key), str(section_text).strip(), ""])
    return "\n".join(lines).rstrip() + "\n"


def resolve_agent_settings(
    *,
    data_client: Any | None = None,
    local_config_path: Path | str | None = None,
) -> dict[str, Any]:
    active_version = _active_agent_settings_version(data_client)
    if active_version is not None:
        return {
            "source": "supabase",
            "version": active_version.get("version"),
            "settings": validate_agent_settings(active_version.get("settings") or {}),
        }

    local_settings = _load_local_settings(local_config_path)
    if local_settings is not None:
        return {
            "source": "local",
            "version": None,
            "settings": validate_agent_settings(local_settings),
        }

    return {
        "source": "defaults",
        "version": None,
        "settings": validate_agent_settings(DEFAULT_AGENT_SETTINGS),
    }


def _normalize_agent(
    agent_key: str,
    raw_agent: dict[str, Any],
    default_agent: dict[str, Any],
) -> dict[str, Any]:
    prompt_sections = _prompt_sections(
        raw_agent.get("prompt_sections", default_agent["prompt_sections"]),
        required_sections=default_agent["prompt_sections"].keys(),
    )
    generation = _generation_config(raw_agent.get("generation", default_agent["generation"]))
    advanced = _advanced_generation_config(raw_agent.get("advanced_generation_config", {}), generation)
    model = _model_name(raw_agent.get("model", default_agent["model"]), agent_key)
    return {
        "display_name": str(raw_agent.get("display_name") or default_agent["display_name"]).strip(),
        "enabled": _bool_value(raw_agent.get("enabled", default_agent["enabled"])),
        "model": model,
        "prompt_sections": prompt_sections,
        "generation": generation,
        "advanced_generation_config": advanced,
    }


def _prompt_sections(raw_sections: Any, *, required_sections: Any) -> dict[str, str]:
    if not isinstance(raw_sections, dict):
        raise ValueError("prompt_sections must be an object")
    normalized: dict[str, str] = {}
    for section_key in required_sections:
        text = str(raw_sections.get(section_key) or "").strip()
        if not text:
            raise ValueError(f"prompt section {section_key} is required")
        normalized[str(section_key)] = text
    return normalized


def _generation_config(raw_generation: Any) -> dict[str, Any]:
    if not isinstance(raw_generation, dict):
        raise ValueError("generation must be an object")
    return {
        "temperature": _float_range(
            raw_generation.get("temperature", 0.2),
            "temperature",
            minimum=0,
            maximum=2,
        ),
        "top_p": _float_range(raw_generation.get("top_p", 0.95), "top_p", minimum=0, maximum=1),
        "top_k": _positive_int(raw_generation.get("top_k", 40), "top_k"),
        "max_output_tokens": _positive_int(
            raw_generation.get("max_output_tokens", 8192),
            "max_output_tokens",
        ),
        "candidate_count": _positive_int(raw_generation.get("candidate_count", 1), "candidate_count"),
        "presence_penalty": _float_range(
            raw_generation.get("presence_penalty", 0),
            "presence_penalty",
            minimum=-2,
            maximum=2,
        ),
        "frequency_penalty": _float_range(
            raw_generation.get("frequency_penalty", 0),
            "frequency_penalty",
            minimum=-2,
            maximum=2,
        ),
        "seed": _optional_int(raw_generation.get("seed"), "seed"),
    }


def _advanced_generation_config(raw_advanced: Any, generation: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw_advanced, dict):
        raise ValueError("advanced_generation_config must be an object")
    normalized = copy.deepcopy(raw_advanced)
    for key in normalized:
        if key not in SUPPORTED_ADVANCED_GENERATION_KEYS:
            raise ValueError(f"unsupported Gemini generation config key: {key}")
        if key in generation:
            raise ValueError(f"advanced_generation_config.{key} conflicts with polished field {key}")
    return normalized


def _model_name(raw_model: Any, agent_key: str) -> str:
    model = str(raw_model or "").strip()
    if not (model.startswith("gemini-") or model.startswith("models/gemini-")):
        raise ValueError(f"{agent_key} model must be a Gemini model name")
    return model


def _active_agent_settings_version(data_client: Any | None) -> dict[str, Any] | None:
    if data_client is None or not hasattr(data_client, "list_agent_settings_versions"):
        return None
    versions = list(data_client.list_agent_settings_versions() or [])
    active = [version for version in versions if version.get("is_active")]
    if active:
        return active[0]
    return versions[0] if versions else None


def _load_local_settings(local_config_path: Path | str | None) -> dict[str, Any] | None:
    if local_config_path is None:
        return None
    path = Path(local_config_path)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("local agent settings JSON must be an object")
    return payload


def _section_title(section_key: str) -> str:
    return f"{section_key.replace('_', ' ').capitalize()}:"


def _contains_key(value: Any, key_name: str) -> bool:
    if isinstance(value, dict):
        return any(str(key) == key_name or _contains_key(child, key_name) for key, child in value.items())
    if isinstance(value, list):
        return any(_contains_key(child, key_name) for child in value)
    return False


def _bool_value(raw_value: Any) -> bool:
    if isinstance(raw_value, bool):
        return raw_value
    return str(raw_value).strip().lower() in {"1", "true", "yes", "on"}


def _float_range(raw_value: Any, field_name: str, *, minimum: float, maximum: float) -> float:
    try:
        value = float(str(raw_value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a number") from exc
    if value < minimum or value > maximum:
        raise ValueError(f"{field_name} must be between {minimum:g} and {maximum:g}")
    return value


def _positive_int(raw_value: Any, field_name: str) -> int:
    try:
        value = int(str(raw_value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a whole number") from exc
    if value <= 0:
        raise ValueError(f"{field_name} must be greater than zero")
    return value


def _optional_int(raw_value: Any, field_name: str) -> int | None:
    if raw_value in (None, ""):
        return None
    try:
        return int(str(raw_value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a whole number") from exc
