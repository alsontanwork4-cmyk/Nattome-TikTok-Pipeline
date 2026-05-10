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
        raise AuthenticationError("Not needed in runs tests")

    def get_user(self, access_token: str) -> AuthenticatedUser:
        if access_token != self.user.access_token:
            raise AuthenticationError("Invalid session")
        return self.user


class FakeDashboardDataClient:
    def __init__(self):
        self.enqueued_manual_runs = []
        self.active_manual_run = None
        self.runs = [
            {
                "run_id": "run-queued",
                "status": "queued",
                "run_type": "daily",
                "started_at": "2026-05-10T01:00:00Z",
                "finished_at": "",
                "duration_seconds": None,
                "triggered_by": "owner@example.com",
                "raw_candidate_count": 0,
                "eligible_candidate_count": 0,
                "selected_count": 0,
                "error_summary": "",
            },
            {
                "run_id": "run-running",
                "status": "running",
                "run_type": "daily",
                "started_at": "2026-05-10T00:50:00Z",
                "finished_at": "",
                "duration_seconds": None,
                "triggered_by": "worker",
                "raw_candidate_count": 12,
                "eligible_candidate_count": 6,
                "selected_count": 3,
                "error_summary": "",
            },
            {
                "run_id": "run-succeeded",
                "status": "succeeded",
                "run_type": "daily",
                "started_at": "2026-05-10T00:00:00Z",
                "finished_at": "2026-05-10T00:08:30Z",
                "duration_seconds": 510,
                "triggered_by": "systemd",
                "raw_candidate_count": 30,
                "eligible_candidate_count": 9,
                "selected_count": 3,
                "error_summary": "",
            },
            {
                "run_id": "run-failed",
                "status": "failed",
                "run_type": "manual",
                "started_at": "2026-05-09T23:00:00Z",
                "finished_at": "2026-05-09T23:01:00Z",
                "duration_seconds": 60,
                "triggered_by": "owner@example.com",
                "raw_candidate_count": 2,
                "eligible_candidate_count": 0,
                "selected_count": 0,
                "error_summary": "SUPABASE_SERVICE_ROLE_KEY=secret-value\nGemini request failed",
            },
            {
                "run_id": "run-canceled",
                "status": "canceled",
                "run_type": "manual",
                "started_at": "2026-05-09T22:00:00Z",
                "finished_at": "2026-05-09T22:02:00Z",
                "duration_seconds": 120,
                "triggered_by": "owner@example.com",
                "raw_candidate_count": 5,
                "eligible_candidate_count": 1,
                "selected_count": 0,
                "error_summary": "Canceled by user",
            },
        ]
        self.outputs = {
            "run-succeeded": [
                {
                    "artifact_type": "raw_scrape",
                    "bucket": "dashboard-artifacts",
                    "object_path": "runs/run-succeeded/data/raw_scrape_all.json",
                    "filename": "raw_scrape_all.json",
                    "content_type": "application/json",
                    "size_bytes": 8192,
                    "checksum": "sha256:raw",
                    "created_at": "2026-05-10T00:07:00Z",
                },
                {
                    "artifact_type": "report",
                    "bucket": "dashboard-artifacts",
                    "object_path": "runs/run-succeeded/report.md",
                    "filename": "report.md",
                    "content_type": "text/markdown",
                    "size_bytes": 4096,
                    "checksum": "sha256:abc",
                    "created_at": "2026-05-10T00:08:00Z",
                }
            ]
        }
        self.artifact_bodies = {
            "runs/run-succeeded/data/raw_scrape_all.json": """
            {
              "generated_at": "2026-05-10T08:00:00+08:00",
              "scope": "all",
              "inputs": {
                "hashtags": ["guthealth"],
                "keywords": ["bloating"],
                "profiles": ["gaviscon"]
              },
              "raw_item_count": 2,
              "unique_video_count": 1,
              "raw_items": [
                {
                  "id": "video-raw-1",
                  "webVideoUrl": "https://www.tiktok.com/@nattome/video/123",
                  "text": "Bloating is REAL #guthealth",
                  "diggCount": 36500,
                  "shareCount": 465,
                  "playCount": 803200,
                  "commentCount": 45,
                  "isAd": false,
                  "createTimeISO": "2026-05-10T00:00:00Z",
                  "hashtags": [{"name": "guthealth"}, {"name": "bloating"}],
                  "authorMeta": {
                    "id": "author-1",
                    "name": "nattomecreator",
                    "nickName": "Nattome Creator",
                    "verified": true,
                    "signature": "Gut health creator",
                    "fans": 4400000,
                    "video": 4711,
                    "privateAccount": false,
                    "avatar": "https://cdn.example/avatar.jpg"
                  },
                  "musicMeta": {
                    "musicName": "original sound",
                    "musicAuthor": "Nattome Creator",
                    "musicOriginal": true,
                    "musicAlbum": "",
                    "playUrl": "https://cdn.example/music.mp3",
                    "coverMediumUrl": "https://cdn.example/music.jpg"
                  },
                  "videoMeta": {
                    "coverUrl": "https://cdn.example/cover.jpg",
                    "duration": 8,
                    "definition": "540p",
                    "format": "mp4",
                    "height": 1024,
                    "width": 576,
                    "downloadAddr": "https://cdn.example/video.mp4"
                  }
                }
              ]
            }
            """
        }
        self.raw_videos = [
            {
                "video_id": "video-raw-1",
                "run_id": "run-succeeded",
                "tiktok_url": "https://www.tiktok.com/@nattome/video/123",
                "author_handle": "nattomecreator",
                "caption": "Bloating is REAL #guthealth",
                "hashtags": ["guthealth", "bloating"],
                "source_input": "#guthealth",
                "play_count": 803200,
                "like_count": 36500,
                "comment_count": 45,
                "share_count": 465,
                "created_at": "2026-05-10T00:00:00Z",
            },
            {
                "video_id": "fallback-video",
                "run_id": "run-running",
                "tiktok_url": "https://www.tiktok.com/@fallback/video/1",
                "author_handle": "fallbackauthor",
                "caption": "Fallback compact caption",
                "hashtags": ["fallbacktag"],
                "source_input": "#fallbacktag",
                "play_count": 12000,
                "like_count": 900,
                "comment_count": 20,
                "share_count": 80,
                "created_at": "2026-05-10T00:50:00Z",
            }
        ]
        self.agent_trace_events = {
            "run-succeeded": [
                {
                    "event_id": "trace-1",
                    "run_id": "run-succeeded",
                    "agent": "gemini_video_evidence",
                    "candidate_id": "video-raw-1",
                    "candidate_prefix": "001-video-raw-1",
                    "substep": "generating_evidence",
                    "status": "completed",
                    "started_at": "2026-05-10T00:04:00Z",
                    "ended_at": "2026-05-10T00:04:42Z",
                    "duration_ms": 42000,
                    "artifact_references": ["data/001_video_gemini_evidence.json"],
                    "error_summary": "",
                },
                {
                    "event_id": "trace-2",
                    "run_id": "run-succeeded",
                    "agent": "nattome_creative_strategy",
                    "candidate_id": "video-raw-1",
                    "candidate_prefix": "001-video-raw-1",
                    "substep": "generating_creative_strategy",
                    "status": "failed",
                    "started_at": "2026-05-10T00:05:00Z",
                    "ended_at": "2026-05-10T00:05:03Z",
                    "duration_ms": 3000,
                    "artifact_references": [],
                    "error_summary": "GEMINI_API_KEY=secret\nCreative generation failed",
                },
            ]
        }

    def list_runs(self, *, limit: int = 50):
        return self.runs[:limit]

    def get_run(self, run_id: str):
        return next((run for run in self.runs if run["run_id"] == run_id), None)

    def list_run_outputs(self, run_id: str):
        return self.outputs.get(run_id, [])

    def download_artifact_text(self, metadata):
        return self.artifact_bodies.get(metadata.object_path)

    def list_raw_videos(self):
        return self.raw_videos

    def list_agent_trace_events(self, *, run_id: str, limit: int = 100):
        return self.agent_trace_events.get(run_id, [])[:limit]

    def get_active_manual_run(self, *, run_type: str):
        return self.active_manual_run

    def enqueue_manual_run(self, manual_run: dict, run: dict):
        self.enqueued_manual_runs.append((manual_run, run))
        self.runs.insert(0, run)
        return manual_run


class FailingDashboardDataClient:
    def list_runs(self, *, limit: int = 50):
        raise RuntimeError("Supabase Postgres unavailable")


class DashboardFastAPIRunsTest(unittest.TestCase):
    def test_runs_route_requires_authentication(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = TestClient(
                create_app(DashboardSettings(workspace_path=Path(temp_dir))),
                follow_redirects=False,
            )

            response = client.get("/runs")

            self.assertEqual(response.status_code, 303)
            self.assertEqual(response.headers["location"], "/login")

    def test_legacy_run_history_route_is_removed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = TestClient(
                create_app(DashboardSettings(workspace_path=Path(temp_dir))),
                follow_redirects=False,
            )

            response = client.get("/run-history")

            self.assertEqual(response.status_code, 404)

    def test_manual_run_trigger_requires_authentication(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = TestClient(
                create_app(DashboardSettings(workspace_path=Path(temp_dir))),
                follow_redirects=False,
            )

            response = client.post("/runs")

            self.assertEqual(response.status_code, 303)
            self.assertEqual(response.headers["location"], "/login")

    def test_manual_run_trigger_queues_full_pipeline_without_running_worker(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_client = FakeDashboardDataClient()
            client = self._client(Path(temp_dir), data_client)

            response = client.post("/runs", follow_redirects=False)

            self.assertEqual(response.status_code, 303)
            self.assertEqual(response.headers["location"], "/runs")
            self.assertEqual(len(data_client.enqueued_manual_runs), 1)
            manual_run, run = data_client.enqueued_manual_runs[0]
            self.assertEqual(manual_run["status"], "queued")
            self.assertEqual(manual_run["run_type"], "full_pipeline")
            self.assertEqual(manual_run["triggered_by"], "owner@example.com")
            self.assertIn("requested_at", manual_run)
            self.assertGreaterEqual(len(manual_run["expected_output_metadata"]), 3)
            self.assertEqual(run["status"], "queued")
            self.assertEqual(run["run_id"], manual_run["run_id"])
            self.assertEqual(run["triggered_by"], "owner@example.com")

    def test_manual_run_trigger_rejects_duplicate_active_full_pipeline_run(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_client = FakeDashboardDataClient()
            data_client.active_manual_run = {
                "id": "manual-active",
                "run_id": "run-active",
                "status": "running",
                "run_type": "full_pipeline",
            }
            client = self._client(Path(temp_dir), data_client)

            response = client.post("/runs", follow_redirects=False)

            self.assertEqual(response.status_code, 409)
            self.assertIn("A full pipeline run is already active.", response.text)
            self.assertEqual(data_client.enqueued_manual_runs, [])

    def test_runs_route_renders_empty_state_without_sqlite_runtime(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            data_client = FakeDashboardDataClient()
            data_client.runs = []
            client = self._client(workspace, data_client)

            response = client.get("/runs")

            self.assertEqual(response.status_code, 200)
            self.assertIn("Runs", response.text)
            self.assertIn("No Supabase runs yet", response.text)
            self.assertIn('<section class="panel">', response.text)
            self.assertFalse((workspace / "data" / "dashboard" / "dashboard.sqlite3").exists())

    def test_runs_route_renders_data_error_instead_of_internal_server_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = self._client(Path(temp_dir), FailingDashboardDataClient())

            response = client.get("/runs")

            self.assertEqual(response.status_code, 503)
            self.assertIn("Supabase Postgres unavailable", response.text)
            self.assertIn("No Supabase runs yet", response.text)

    def test_runs_route_lists_supported_statuses_with_legacy_theme(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = self._client(Path(temp_dir), FakeDashboardDataClient())

            response = client.get("/runs")

            self.assertEqual(response.status_code, 200)
            self.assertIn('method="post" action="/runs"', response.text)
            self.assertIn("Run full pipeline", response.text)
            self.assertIn("TikTok Scraper Runs", response.text)
            self.assertIn("Scraped 30 TikTok results", response.text)
            self.assertIn("803,200", response.text)
            self.assertIn("nattomecreator", response.text)
            self.assertIn('<table class="data-table runs-table">', response.text)
            for run_id in [
                "run-queued",
                "run-running",
                "run-succeeded",
                "run-failed",
                "run-canceled",
            ]:
                with self.subTest(run_id=run_id):
                    self.assertIn(f'href="/runs/{run_id}"', response.text)
            for label in ["Queued", "Running", "Succeeded", "Failed", "Canceled"]:
                with self.subTest(label=label):
                    self.assertIn(label, response.text)

    def test_runs_route_filters_by_query_parameter(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = self._client(Path(temp_dir), FakeDashboardDataClient())

            response = client.get("/runs?q=run-succeeded")

            self.assertEqual(response.status_code, 200)
            self.assertIn('href="/runs/run-succeeded"', response.text)
            self.assertNotIn('href="/runs/run-failed"', response.text)

    def test_run_detail_renders_metadata_outputs_and_redacted_failure_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = self._client(Path(temp_dir), FakeDashboardDataClient())

            succeeded_response = client.get("/runs/run-succeeded")
            failed_response = client.get("/runs/run-failed")

            self.assertEqual(succeeded_response.status_code, 200)
            self.assertIn("run-succeeded", succeeded_response.text)
            self.assertIn("2026-05-10T00:00:00Z", succeeded_response.text)
            self.assertIn("8m 30s", succeeded_response.text)
            self.assertIn("Raw scrape artifact", succeeded_response.text)
            self.assertIn("guthealth", succeeded_response.text)
            self.assertIn("Total Plays", succeeded_response.text)
            self.assertIn("Music original?", succeeded_response.text)
            self.assertEqual(failed_response.status_code, 200)
            self.assertIn("Gemini request failed", failed_response.text)
            self.assertIn("[redacted secret]", failed_response.text)
            self.assertNotIn("secret-value", failed_response.text)

    def test_run_detail_renders_tiktok_output_tabs_from_raw_scrape_artifact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = self._client(Path(temp_dir), FakeDashboardDataClient())

            overview = client.get("/runs/run-succeeded")
            posts = client.get("/runs/run-succeeded?tab=posts")
            authors = client.get("/runs/run-succeeded?tab=authors")
            music = client.get("/runs/run-succeeded?tab=music")
            video = client.get("/runs/run-succeeded?tab=video")
            all_fields = client.get("/runs/run-succeeded?tab=all-fields")

            self.assertEqual(overview.status_code, 200)
            for label in ["Overview", "Posts", "Authors", "Music", "Video", "All fields", "Agent Trace"]:
                with self.subTest(label=label):
                    self.assertIn(label, overview.text)
            self.assertIn('href="/runs/run-succeeded?tab=posts" aria-current="page"', posts.text)
            self.assertIn("Bloating is REAL #guthealth", posts.text)
            self.assertIn("803200", posts.text)
            self.assertIn("https://www.tiktok.com/@nattome/video/123", posts.text)
            self.assertIn("Nattome Creator", authors.text)
            self.assertIn("Gut health creator", authors.text)
            self.assertIn("original sound", music.text)
            self.assertIn("https://cdn.example/music.mp3", music.text)
            self.assertIn("540p", video.text)
            self.assertIn("https://cdn.example/video.mp4", video.text)
            self.assertIn("authorMeta", all_fields.text)
            self.assertIn("video-raw-1", all_fields.text)

    def test_run_detail_agent_trace_tab_filters_rows_to_selected_run(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_client = FakeDashboardDataClient()
            data_client.agent_trace_events["other-run"] = [
                {
                    "event_id": "other",
                    "run_id": "other-run",
                    "agent": "gemini_video_evidence",
                    "candidate_prefix": "other-candidate",
                    "substep": "generating_evidence",
                    "status": "completed",
                    "started_at": "2026-05-10T00:00:00Z",
                    "ended_at": "2026-05-10T00:00:01Z",
                    "duration_ms": 1000,
                    "artifact_references": [],
                    "error_summary": "",
                }
            ]
            client = self._client(Path(temp_dir), data_client)

            response = client.get("/runs/run-succeeded?tab=agent-trace")

            self.assertEqual(response.status_code, 200)
            self.assertIn('href="/runs/run-succeeded?tab=agent-trace" aria-current="page"', response.text)
            self.assertIn("Gemini Video Evidence Agent", response.text)
            self.assertIn("Nattome Creative Strategist Agent", response.text)
            self.assertIn("001-video-raw-1", response.text)
            self.assertIn("generating_evidence", response.text)
            self.assertIn("generating_creative_strategy", response.text)
            self.assertIn("42s", response.text)
            self.assertIn("3s", response.text)
            self.assertIn("data/001_video_gemini_evidence.json", response.text)
            self.assertIn("[redacted secret]", response.text)
            self.assertIn("Creative generation failed", response.text)
            self.assertNotIn("other-candidate", response.text)
            self.assertNotIn("secret", response.text.lower().replace("[redacted secret]", ""))

    def test_run_detail_agent_trace_tab_renders_empty_state_without_trace_data(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = self._client(Path(temp_dir), FakeDashboardDataClient())

            response = client.get("/runs/run-running?tab=agent-trace")

            self.assertEqual(response.status_code, 200)
            self.assertIn("No agent trace events for this run yet.", response.text)
            self.assertIn("Fallback compact caption", client.get("/runs/run-running?tab=posts").text)

    def test_run_detail_falls_back_to_compact_raw_videos_without_raw_scrape_artifact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = self._client(Path(temp_dir), FakeDashboardDataClient())

            response = client.get("/runs/run-running?tab=posts")

            self.assertEqual(response.status_code, 200)
            self.assertIn("Compact raw video metadata", response.text)
            self.assertIn("Fallback compact caption", response.text)
            self.assertIn("fallbackauthor", response.text)
            self.assertIn("fallbacktag", response.text)

    def test_missing_run_detail_returns_404(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = self._client(Path(temp_dir), FakeDashboardDataClient())

            response = client.get("/runs/not-found")

            self.assertEqual(response.status_code, 404)
            self.assertIn("Run not found", response.text)

    def _client(self, workspace: Path, data_client: FakeDashboardDataClient) -> TestClient:
        auth_client = FakeSupabaseAuthClient()
        client = TestClient(
            create_app(
                DashboardSettings(workspace_path=workspace),
                auth_client=auth_client,
                dashboard_client=data_client,
            )
        )
        client.cookies.set("dashboard_access_token", auth_client.user.access_token)
        return client


if __name__ == "__main__":
    unittest.main()
