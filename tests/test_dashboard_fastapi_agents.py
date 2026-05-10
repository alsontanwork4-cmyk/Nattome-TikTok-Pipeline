import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from dashboard.agent_settings import DEFAULT_AGENT_SETTINGS
from dashboard.agent_views import agents_template_context
from dashboard.app import create_app
from dashboard.auth import AuthSession, AuthenticatedUser, AuthenticationError
from dashboard.config import DashboardSettings


class FakeSupabaseAuthClient:
    def __init__(self):
        self.user = AuthenticatedUser(
            user_id="user-123",
            email="owner@example.com",
            access_token="token-123",
        )

    def sign_in_with_password(self, email: str, password: str) -> AuthSession:
        raise AuthenticationError("Not needed in agents tests")

    def get_user(self, access_token: str) -> AuthenticatedUser:
        if access_token != self.user.access_token:
            raise AuthenticationError("Invalid session")
        return self.user


class FakeDashboardDataClient:
    def __init__(self):
        self.agent_versions = [
            {
                "version": 2,
                "settings": DEFAULT_AGENT_SETTINGS,
                "reason": "Tune default prompts",
                "is_active": True,
                "rollback_of_version": None,
                "created_by": "marketer@example.com",
                "created_at": "2026-05-10T01:00:00Z",
            },
            {
                "version": 1,
                "settings": DEFAULT_AGENT_SETTINGS,
                "reason": "Initial agent settings",
                "is_active": False,
                "rollback_of_version": None,
                "created_by": "marketer@example.com",
                "created_at": "2026-05-09T01:00:00Z",
            },
        ]
        self.saved_agent_settings = []
        self.rollbacks = []
        self.agent_trace_events = []

    def list_agent_settings_versions(self):
        return self.agent_versions

    def list_recent_agent_trace_events(self, *, limit: int = 100):
        return self.agent_trace_events[:limit]

    def save_agent_settings_version(self, settings, *, reason: str, user: str):
        record = {
            "version": 3,
            "settings": settings,
            "reason": reason,
            "is_active": True,
            "rollback_of_version": None,
            "created_by": user,
            "created_at": "2026-05-10T02:00:00Z",
        }
        self.saved_agent_settings.append(record)
        self.agent_versions.insert(0, record)
        return record

    def rollback_agent_settings_version(self, *, target_version: int, reason: str, user: str):
        record = {
            "version": 3,
            "settings": DEFAULT_AGENT_SETTINGS,
            "reason": reason,
            "is_active": True,
            "rollback_of_version": target_version,
            "created_by": user,
            "created_at": "2026-05-10T02:00:00Z",
        }
        self.rollbacks.append(record)
        self.agent_versions.insert(0, record)
        return record


class DashboardFastAPIAgentsTest(unittest.TestCase):
    def test_agents_routes_require_authentication(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = TestClient(
                create_app(DashboardSettings(workspace_path=Path(temp_dir))),
                follow_redirects=False,
            )

            responses = [
                client.get("/agents"),
                client.post("/agents", data={}),
                client.post("/agents/1/rollback", data={}),
            ]

            for response in responses:
                with self.subTest(path=response.request.url.path):
                    self.assertEqual(response.status_code, 303)
                    self.assertEqual(response.headers["location"], "/login")

    def test_agents_view_renders_fixed_agents_previews_nav_and_mascot(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client, _ = self._client(Path(temp_dir), FakeDashboardDataClient())

            response = client.get("/agents")

            self.assertEqual(response.status_code, 200)
            self.assertIn("Agents", response.text)
            self.assertIn("Gemini Video Evidence Agent", response.text)
            self.assertIn("Nattome Creative Strategist Agent", response.text)
            self.assertIn("Compiled prompt preview", response.text)
            self.assertIn("Output contract:", response.text)
            self.assertIn("Nattome brand POV reference", response.text)
            self.assertIn('class="agent-mascot"', response.text)
            self.assertIn('data-state="idle"', response.text)
            self.assertLess(response.text.index('href="/agents"'), response.text.index('href="/settings"'))
            self.assertIn('action="/agents/1/rollback"', response.text)
            self.assertNotIn("smoke", response.text.lower())

    def test_agents_view_renders_live_status_rows_trace_history_and_polling_marker(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_client = FakeDashboardDataClient()
            data_client.agent_trace_events = [
                {
                    "event_id": "evt-running",
                    "run_id": "run-live",
                    "agent": "gemini_video_evidence",
                    "candidate_id": "video-1",
                    "candidate_prefix": "001-first-video",
                    "substep": "generating_evidence",
                    "status": "running",
                    "started_at": "2026-05-10T01:59:30+00:00",
                    "ended_at": None,
                    "config_source": "supabase",
                    "config_version": 2,
                    "artifact_references": ["data/001_evidence.json"],
                    "error_summary": "",
                },
                {
                    "event_id": "evt-failed",
                    "run_id": "run-earlier",
                    "agent": "nattome_creative_strategy",
                    "candidate_id": "video-2",
                    "candidate_prefix": "002-second-video",
                    "substep": "generating_creative_strategy",
                    "status": "failed",
                    "started_at": "2026-05-10T01:54:00+00:00",
                    "ended_at": "2026-05-10T01:55:00+00:00",
                    "config_source": "supabase",
                    "config_version": 2,
                    "artifact_references": [],
                    "error_summary": "Gemini quota exceeded",
                },
            ]
            client, _ = self._client(Path(temp_dir), data_client)

            response = client.get("/agents")

            self.assertEqual(response.status_code, 200)
            self.assertIn("Live agent runs", response.text)
            self.assertIn("Gemini Video Evidence Agent", response.text)
            self.assertIn("Nattome Creative Strategist Agent", response.text)
            self.assertIn("generating_evidence", response.text)
            self.assertIn("run-live", response.text)
            self.assertIn("001-first-video", response.text)
            self.assertIn("running", response.text)
            self.assertIn("Gemini quota exceeded", response.text)
            self.assertIn('data-agent-auto-refresh="5"', response.text)
            self.assertIn('href="/agents"', response.text)
            self.assertIn('data-state="failed"', response.text)

    def test_agents_view_model_derives_state_priority_and_preserves_latest_error(self):
        settings = DashboardSettings(workspace_path=Path("."))
        trace_events = [
            {
                "event_id": "failed-old",
                "run_id": "run-1",
                "agent": "gemini_video_evidence",
                "candidate_id": "video-1",
                "candidate_prefix": "001-old",
                "substep": "generating_evidence",
                "status": "failed",
                "started_at": "2026-05-10T01:00:00+00:00",
                "ended_at": "2026-05-10T01:01:00+00:00",
                "config_source": "supabase",
                "config_version": 2,
                "artifact_references": [],
                "error_summary": "Earlier failure remains visible",
            },
            {
                "event_id": "running-new",
                "run_id": "run-2",
                "agent": "gemini_video_evidence",
                "candidate_id": "video-2",
                "candidate_prefix": "002-new",
                "substep": "uploading_video",
                "status": "running",
                "started_at": "2026-05-10T01:59:00+00:00",
                "ended_at": None,
                "config_source": "supabase",
                "config_version": 2,
                "artifact_references": [],
                "error_summary": "",
            },
            {
                "event_id": "queued",
                "run_id": "run-3",
                "agent": "nattome_creative_strategy",
                "candidate_id": "video-3",
                "candidate_prefix": "003-queued",
                "substep": "generating_creative_strategy",
                "status": "queued",
                "started_at": "2026-05-10T01:58:00+00:00",
                "ended_at": None,
                "config_source": "supabase",
                "config_version": 2,
                "artifact_references": [],
                "error_summary": "",
            },
        ]

        context = agents_template_context(
            settings,
            user=object(),
            versions=FakeDashboardDataClient().agent_versions,
            error="",
            trace_events=trace_events,
            now=datetime(2026, 5, 10, 2, 0, tzinfo=timezone.utc),
        )

        rows = {row["key"]: row for row in context["live_agent_rows"]}
        self.assertEqual(rows["gemini_video_evidence"]["state"], "running")
        self.assertEqual(rows["gemini_video_evidence"]["elapsed"], "1m 0s")
        self.assertEqual(rows["gemini_video_evidence"]["latest_error_summary"], "Earlier failure remains visible")
        self.assertEqual(rows["nattome_creative_strategy"]["state"], "queued")
        self.assertEqual(context["mascot_state"], "running")
        self.assertTrue(context["should_auto_refresh_agents"])

    def test_agents_view_model_clears_failed_state_after_newer_success(self):
        settings = DashboardSettings(workspace_path=Path("."))
        trace_events = [
            {
                "event_id": "failed-old",
                "run_id": "run-1",
                "agent": "nattome_creative_strategy",
                "candidate_id": "video-1",
                "candidate_prefix": "001-old",
                "substep": "generating_creative_strategy",
                "status": "failed",
                "started_at": "2026-05-10T01:00:00+00:00",
                "ended_at": "2026-05-10T01:01:00+00:00",
                "error_summary": "Previous model error",
            },
            {
                "event_id": "completed-new",
                "run_id": "run-2",
                "agent": "nattome_creative_strategy",
                "candidate_id": "video-2",
                "candidate_prefix": "002-new",
                "substep": "completed",
                "status": "completed",
                "started_at": "2026-05-10T01:59:00+00:00",
                "ended_at": "2026-05-10T02:00:00+00:00",
                "error_summary": "",
            },
        ]

        context = agents_template_context(
            settings,
            user=object(),
            versions=FakeDashboardDataClient().agent_versions,
            error="",
            trace_events=trace_events,
            now=datetime(2026, 5, 10, 2, 1, tzinfo=timezone.utc),
        )

        rows = {row["key"]: row for row in context["live_agent_rows"]}
        self.assertEqual(rows["nattome_creative_strategy"]["state"], "last succeeded")
        self.assertEqual(rows["nattome_creative_strategy"]["latest_error_summary"], "Previous model error")
        self.assertEqual(rows["nattome_creative_strategy"]["last_completed_at"], "2026-05-10T02:00:00+00:00")
        self.assertEqual(context["mascot_state"], "idle")
        self.assertFalse(context["should_auto_refresh_agents"])

    def test_agents_save_validates_and_persists_with_auth_identity(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_client = FakeDashboardDataClient()
            client, _ = self._client(Path(temp_dir), data_client)
            payload = self._form_payload()
            payload["gemini_video_evidence__model"] = "models/gemini-2.0-flash"
            payload["gemini_video_evidence__temperature"] = "0.3"
            payload["reason"] = "Tune evidence model"

            response = client.post("/agents", data=payload, follow_redirects=False)

            self.assertEqual(response.status_code, 303)
            self.assertEqual(response.headers["location"], "/agents")
            self.assertEqual(len(data_client.saved_agent_settings), 1)
            saved = data_client.saved_agent_settings[0]
            self.assertEqual(saved["created_by"], "owner@example.com")
            self.assertEqual(saved["reason"], "Tune evidence model")
            self.assertEqual(saved["settings"]["agents"]["gemini_video_evidence"]["model"], "models/gemini-2.0-flash")
            self.assertEqual(saved["settings"]["agents"]["gemini_video_evidence"]["generation"]["temperature"], 0.3)

    def test_agents_save_rerenders_validation_error_without_saving(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_client = FakeDashboardDataClient()
            client, _ = self._client(Path(temp_dir), data_client)
            payload = self._form_payload()
            payload["gemini_video_evidence__advanced_generation_config"] = json.dumps({"temperature": 0.1})
            payload["reason"] = "Conflicting temperature"

            response = client.post("/agents", data=payload)

            self.assertEqual(response.status_code, 400)
            self.assertIn("Agent settings could not be saved", response.text)
            self.assertIn("conflicts with polished field", response.text)
            self.assertEqual(data_client.saved_agent_settings, [])

    def test_agents_rollback_persists_new_active_version_with_auth_identity(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_client = FakeDashboardDataClient()
            client, _ = self._client(Path(temp_dir), data_client)

            response = client.post(
                "/agents/1/rollback",
                data={"reason": "Restore prompt baseline"},
                follow_redirects=False,
            )

            self.assertEqual(response.status_code, 303)
            self.assertEqual(response.headers["location"], "/agents")
            self.assertEqual(len(data_client.rollbacks), 1)
            rollback = data_client.rollbacks[0]
            self.assertEqual(rollback["rollback_of_version"], 1)
            self.assertEqual(rollback["created_by"], "owner@example.com")

    def _client(self, workspace: Path, data_client: FakeDashboardDataClient):
        auth_client = FakeSupabaseAuthClient()
        client = TestClient(
            create_app(
                DashboardSettings(workspace_path=workspace),
                auth_client=auth_client,
                dashboard_client=data_client,
            )
        )
        client.cookies.set("dashboard_access_token", auth_client.user.access_token)
        return client, auth_client

    def _form_payload(self):
        payload = {"reason": "Update agent settings"}
        for agent_key, agent in DEFAULT_AGENT_SETTINGS["agents"].items():
            payload[f"{agent_key}__enabled"] = "on"
            payload[f"{agent_key}__model"] = agent["model"]
            for section_key, section_text in agent["prompt_sections"].items():
                payload[f"{agent_key}__prompt__{section_key}"] = section_text
            for field in (
                "temperature",
                "top_p",
                "top_k",
                "max_output_tokens",
                "candidate_count",
                "presence_penalty",
                "frequency_penalty",
            ):
                payload[f"{agent_key}__{field}"] = str(agent["generation"].get(field, ""))
            payload[f"{agent_key}__seed"] = ""
            payload[f"{agent_key}__advanced_generation_config"] = json.dumps(
                agent["advanced_generation_config"]
            )
        return payload


if __name__ == "__main__":
    unittest.main()
