import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

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
        raise AuthenticationError("Not needed in settings tests")

    def get_user(self, access_token: str) -> AuthenticatedUser:
        if access_token != self.user.access_token:
            raise AuthenticationError("Invalid session")
        return self.user


class FakeDashboardDataClient:
    def __init__(self):
        self.settings_versions = [
            {
                "version": 2,
                "settings": {
                    "hashtags": ["guthealth", "bloating"],
                    "keywords": ["acid reflux"],
                    "competitor_profiles": ["gaviscon"],
                    "scope": "all",
                    "results_per_input": 25,
                    "minimum_views": 10000,
                    "maximum_age_days": 14,
                    "minimum_weighted_engagement_rate": 0.025,
                    "requires_downloadable_video": True,
                    "exclusion_terms": ["weight loss"],
                },
                "reason": "Add bloating source",
                "is_active": True,
                "rollback_of_version": None,
                "created_by": "marketer@example.com",
                "created_at": "2026-05-10T01:00:00Z",
            },
            {
                "version": 1,
                "settings": {
                    "hashtags": ["guthealth"],
                    "keywords": ["acid reflux"],
                    "competitor_profiles": ["gaviscon"],
                    "scope": "all",
                    "results_per_input": 20,
                    "minimum_views": 10000,
                    "maximum_age_days": 30,
                    "minimum_weighted_engagement_rate": 0.03,
                    "requires_downloadable_video": True,
                    "exclusion_terms": [],
                },
                "reason": "Initial production settings",
                "is_active": False,
                "rollback_of_version": None,
                "created_by": "marketer@example.com",
                "created_at": "2026-05-09T01:00:00Z",
            },
        ]
        self.runs = [
            {
                "run_id": "run-1",
                "status": "succeeded",
                "run_type": "daily",
                "started_at": "2026-05-10T01:00:00Z",
                "finished_at": "2026-05-10T01:07:00Z",
                "duration_seconds": 420,
                "triggered_by": "systemd",
                "raw_candidate_count": 1,
                "eligible_candidate_count": 1,
                "selected_count": 1,
                "error_summary": "",
            }
        ]
        self.raw_videos = [
            {
                "video_id": "video-1",
                "run_id": "run-1",
                "tiktok_url": "https://tiktok.test/video-1",
                "author_handle": "@creator1",
                "caption": "Gut health hook",
                "hashtags": ["guthealth"],
                "play_count": 12000,
            }
        ]
        self.video_curation = [
            {
                "video_id": "video-1",
                "labels": ["Relevant"],
                "note": "Keep for hook planning.",
                "exclude_similar_reason": "",
                "created_by": "marketer@example.com",
                "updated_by": "marketer@example.com",
            }
        ]
        self.saved_settings: list[dict] = []
        self.rollbacks: list[dict] = []
        self.saved_curation: list[dict] = []

    def list_runs(self, *, limit: int = 50):
        return self.runs[:limit]

    def get_run(self, run_id: str):
        return next((run for run in self.runs if run["run_id"] == run_id), None)

    def list_run_outputs(self, run_id: str):
        return []

    def list_raw_videos(self):
        return self.raw_videos

    def list_video_curation(self):
        return self.video_curation

    def list_selected_videos(self):
        return []

    def list_settings_versions(self):
        return self.settings_versions

    def save_settings_version(self, settings, *, reason: str, user: str):
        record = {
            "version": 3,
            "settings": settings,
            "reason": reason,
            "is_active": True,
            "rollback_of_version": None,
            "created_by": user,
            "created_at": "2026-05-10T02:00:00Z",
        }
        self.saved_settings.append(record)
        self.settings_versions.insert(0, record)
        return record

    def rollback_settings_version(self, *, target_version: int, reason: str, user: str):
        record = {
            "version": 3,
            "settings": self.settings_versions[-1]["settings"],
            "reason": reason,
            "is_active": True,
            "rollback_of_version": target_version,
            "created_by": user,
            "created_at": "2026-05-10T02:00:00Z",
        }
        self.rollbacks.append(record)
        self.settings_versions.insert(0, record)
        return record

    def upsert_video_curation(
        self,
        video_id: str,
        *,
        labels: list[str],
        note: str,
        exclude_similar_reason: str,
        user: str,
    ):
        record = {
            "video_id": video_id,
            "labels": labels,
            "note": note,
            "exclude_similar_reason": exclude_similar_reason,
            "updated_by": user,
            "created_by": user,
        }
        self.saved_curation.append(record)
        return record


class DashboardFastAPISettingsCurationTest(unittest.TestCase):
    def test_settings_and_curation_routes_require_authentication(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = TestClient(
                create_app(DashboardSettings(workspace_path=Path(temp_dir))),
                follow_redirects=False,
            )

            responses = [
                client.get("/settings"),
                client.post("/settings", data={}),
                client.post("/settings/1/rollback", data={}),
                client.post("/videos/video-1/curation", data={}),
            ]

            for response in responses:
                with self.subTest(path=response.request.url.path):
                    self.assertEqual(response.status_code, 303)
                    self.assertEqual(response.headers["location"], "/login")

    def test_settings_view_renders_active_settings_and_version_history(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client, _ = self._client(Path(temp_dir), FakeDashboardDataClient())

            response = client.get("/settings")

            self.assertEqual(response.status_code, 200)
            self.assertIn("Scrape Settings", response.text)
            self.assertIn("Next scheduled scrape uses config: <strong>v2</strong>", response.text)
            self.assertIn("guthealth", response.text)
            self.assertIn("bloating", response.text)
            self.assertIn("Add bloating source", response.text)
            self.assertIn('action="/settings"', response.text)
            self.assertIn('action="/settings/1/rollback"', response.text)
            self.assertIn('<section class="panel wide-panel settings-panel unified-settings"', response.text)

    def test_settings_save_validates_and_persists_new_version_with_auth_identity(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_client = FakeDashboardDataClient()
            client, _ = self._client(Path(temp_dir), data_client)

            response = client.post(
                "/settings",
                data={
                    "hashtags": "#guthealth\n#digestion",
                    "keywords": "acid reflux",
                    "competitor_profiles": "@gaviscon",
                    "scope": "hashtags",
                    "results_per_input": "30",
                    "minimum_views": "12000",
                    "maximum_age_days": "21",
                    "minimum_engagement_rate_percent": "4",
                    "requires_downloadable_video": "on",
                    "exclusion_terms": "weight loss",
                    "reason": "Add digestion hashtag",
                },
                follow_redirects=False,
            )

            self.assertEqual(response.status_code, 303)
            self.assertEqual(response.headers["location"], "/settings")
            self.assertEqual(len(data_client.saved_settings), 1)
            saved = data_client.saved_settings[0]
            self.assertEqual(saved["created_by"], "owner@example.com")
            self.assertEqual(saved["reason"], "Add digestion hashtag")
            self.assertEqual(saved["settings"]["hashtags"], ["guthealth", "digestion"])
            self.assertEqual(saved["settings"]["scope"], "hashtags")
            self.assertEqual(saved["settings"]["minimum_weighted_engagement_rate"], 0.04)

    def test_settings_save_rerenders_clear_validation_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_client = FakeDashboardDataClient()
            client, _ = self._client(Path(temp_dir), data_client)

            response = client.post(
                "/settings",
                data={
                    "hashtags": "#guthealth\n#guthealth",
                    "keywords": "",
                    "competitor_profiles": "",
                    "scope": "all",
                    "results_per_input": "20",
                    "minimum_views": "10000",
                    "maximum_age_days": "14",
                    "minimum_engagement_rate_percent": "3",
                    "reason": "Duplicate source",
                },
            )

            self.assertEqual(response.status_code, 400)
            self.assertIn("Settings could not be saved", response.text)
            self.assertIn("duplicate hashtags: guthealth", response.text)
            self.assertEqual(data_client.saved_settings, [])

    def test_settings_rollback_persists_new_active_version_with_auth_identity(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_client = FakeDashboardDataClient()
            client, _ = self._client(Path(temp_dir), data_client)

            response = client.post(
                "/settings/1/rollback",
                data={"reason": "Restore original sources"},
                follow_redirects=False,
            )

            self.assertEqual(response.status_code, 303)
            self.assertEqual(response.headers["location"], "/settings")
            self.assertEqual(len(data_client.rollbacks), 1)
            rollback = data_client.rollbacks[0]
            self.assertEqual(rollback["rollback_of_version"], 1)
            self.assertEqual(rollback["reason"], "Restore original sources")
            self.assertEqual(rollback["created_by"], "owner@example.com")

    def test_run_detail_renders_curation_form_and_saves_labels_notes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_client = FakeDashboardDataClient()
            client, _ = self._client(Path(temp_dir), data_client)

            detail_response = client.get("/runs/run-1")
            save_response = client.post(
                "/videos/video-1/curation",
                data={
                    "run_id": "run-1",
                    "labels": ["Relevant", "Good Nattome Fit"],
                    "note": "Use this as a breakfast hook.",
                    "exclude_similar_reason": "",
                },
                follow_redirects=False,
            )

            self.assertEqual(detail_response.status_code, 200)
            self.assertIn("Gut health hook", detail_response.text)
            self.assertIn('action="/videos/video-1/curation"', detail_response.text)
            self.assertIn("Keep for hook planning.", detail_response.text)
            self.assertEqual(save_response.status_code, 303)
            self.assertEqual(save_response.headers["location"], "/runs/run-1")
            self.assertEqual(len(data_client.saved_curation), 1)
            saved = data_client.saved_curation[0]
            self.assertEqual(saved["labels"], ["Relevant", "Good Nattome Fit"])
            self.assertEqual(saved["note"], "Use this as a breakfast hook.")
            self.assertEqual(saved["updated_by"], "owner@example.com")

    def _client(
        self,
        workspace: Path,
        data_client: FakeDashboardDataClient,
    ) -> tuple[TestClient, FakeSupabaseAuthClient]:
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


if __name__ == "__main__":
    unittest.main()
