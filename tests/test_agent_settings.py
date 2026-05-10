import json
import tempfile
import unittest
from pathlib import Path

from dashboard.agent_settings import (
    DEFAULT_AGENT_SETTINGS,
    compile_agent_prompt,
    resolve_agent_settings,
    validate_agent_settings,
)


class FakeAgentSettingsClient:
    def __init__(self, versions=None):
        self.versions = versions or []

    def list_agent_settings_versions(self):
        return self.versions


class AgentSettingsTest(unittest.TestCase):
    def test_default_agent_settings_normalize_two_fixed_agents(self):
        resolved = validate_agent_settings(DEFAULT_AGENT_SETTINGS)

        self.assertEqual(set(resolved["agents"]), {"gemini_video_evidence", "nattome_creative_strategy"})
        evidence = resolved["agents"]["gemini_video_evidence"]
        creative = resolved["agents"]["nattome_creative_strategy"]
        self.assertIs(evidence["enabled"], True)
        self.assertIs(creative["enabled"], True)
        self.assertEqual(evidence["model"], "gemini-2.5-flash")
        self.assertNotIn("GEMINI_API_KEY", json.dumps(resolved))
        self.assertIn("Output contract:", compile_agent_prompt("gemini_video_evidence", evidence))

    def test_local_json_fallback_is_used_when_supabase_has_no_active_version(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "agent-settings.json"
            raw_settings = json.loads(json.dumps(DEFAULT_AGENT_SETTINGS))
            raw_settings["agents"]["nattome_creative_strategy"]["enabled"] = False
            raw_settings["agents"]["nattome_creative_strategy"]["model"] = "models/gemini-2.0-flash"
            config_path.write_text(json.dumps(raw_settings), encoding="utf-8")

            resolved = resolve_agent_settings(
                data_client=FakeAgentSettingsClient([]),
                local_config_path=config_path,
            )

        self.assertEqual(resolved["source"], "local")
        self.assertIsNone(resolved["version"])
        self.assertIs(resolved["settings"]["agents"]["nattome_creative_strategy"]["enabled"], False)
        self.assertEqual(
            resolved["settings"]["agents"]["nattome_creative_strategy"]["model"],
            "models/gemini-2.0-flash",
        )

    def test_supabase_active_version_wins_over_local_fallback(self):
        raw_settings = json.loads(json.dumps(DEFAULT_AGENT_SETTINGS))
        raw_settings["agents"]["gemini_video_evidence"]["generation"]["temperature"] = "0.4"
        client = FakeAgentSettingsClient(
            [
                {"version": 3, "is_active": False, "settings": DEFAULT_AGENT_SETTINGS},
                {"version": 4, "is_active": True, "settings": raw_settings},
            ]
        )

        resolved = resolve_agent_settings(data_client=client)

        self.assertEqual(resolved["source"], "supabase")
        self.assertEqual(resolved["version"], 4)
        self.assertEqual(
            resolved["settings"]["agents"]["gemini_video_evidence"]["generation"]["temperature"],
            0.4,
        )

    def test_validation_rejects_secret_keys_invalid_model_and_missing_prompt_sections(self):
        raw_settings = json.loads(json.dumps(DEFAULT_AGENT_SETTINGS))
        raw_settings["GEMINI_API_KEY"] = "should-not-be-here"
        raw_settings["agents"]["gemini_video_evidence"]["model"] = "text-bison"
        raw_settings["agents"]["nattome_creative_strategy"]["prompt_sections"]["role"] = ""

        with self.assertRaisesRegex(ValueError, "GEMINI_API_KEY"):
            validate_agent_settings(raw_settings)

        raw_settings.pop("GEMINI_API_KEY")
        with self.assertRaisesRegex(ValueError, "model"):
            validate_agent_settings(raw_settings)

        raw_settings["agents"]["gemini_video_evidence"]["model"] = "gemini-2.5-flash"
        with self.assertRaisesRegex(ValueError, "prompt section role"):
            validate_agent_settings(raw_settings)

    def test_validation_rejects_numeric_ranges_unsupported_advanced_keys_and_conflicts(self):
        raw_settings = json.loads(json.dumps(DEFAULT_AGENT_SETTINGS))
        raw_settings["agents"]["gemini_video_evidence"]["generation"]["temperature"] = "2.5"
        with self.assertRaisesRegex(ValueError, "temperature"):
            validate_agent_settings(raw_settings)

        raw_settings = json.loads(json.dumps(DEFAULT_AGENT_SETTINGS))
        raw_settings["agents"]["gemini_video_evidence"]["advanced_generation_config"] = {
            "made_up_key": True
        }
        with self.assertRaisesRegex(ValueError, "unsupported Gemini generation config key"):
            validate_agent_settings(raw_settings)

        raw_settings = json.loads(json.dumps(DEFAULT_AGENT_SETTINGS))
        raw_settings["agents"]["gemini_video_evidence"]["advanced_generation_config"] = {
            "temperature": 0.1
        }
        with self.assertRaisesRegex(ValueError, "conflicts with polished field"):
            validate_agent_settings(raw_settings)


if __name__ == "__main__":
    unittest.main()
