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

    def list_runs(self, *, limit: int = 50):
        return self.runs[:limit]

    def get_run(self, run_id: str):
        return next((run for run in self.runs if run["run_id"] == run_id), None)

    def list_run_outputs(self, run_id: str):
        return self.outputs.get(run_id, [])

    def get_active_manual_run(self, *, run_type: str):
        return self.active_manual_run

    def enqueue_manual_run(self, manual_run: dict, run: dict):
        self.enqueued_manual_runs.append((manual_run, run))
        self.runs.insert(0, run)
        return manual_run


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

    def test_runs_route_lists_supported_statuses_with_legacy_theme(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = self._client(Path(temp_dir), FakeDashboardDataClient())

            response = client.get("/runs")

            self.assertEqual(response.status_code, 200)
            self.assertIn('method="post" action="/runs"', response.text)
            self.assertIn("Run full pipeline", response.text)
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

    def test_run_detail_renders_metadata_outputs_and_redacted_failure_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = self._client(Path(temp_dir), FakeDashboardDataClient())

            succeeded_response = client.get("/runs/run-succeeded")
            failed_response = client.get("/runs/run-failed")

            self.assertEqual(succeeded_response.status_code, 200)
            self.assertIn("run-succeeded", succeeded_response.text)
            self.assertIn("daily", succeeded_response.text)
            self.assertIn("2026-05-10T00:00:00Z", succeeded_response.text)
            self.assertIn("2026-05-10T00:08:30Z", succeeded_response.text)
            self.assertIn("8m 30s", succeeded_response.text)
            self.assertIn("report.md", succeeded_response.text)
            self.assertIn("text/markdown", succeeded_response.text)
            self.assertIn("4.0 KB", succeeded_response.text)
            self.assertIn("sha256:abc", succeeded_response.text)
            self.assertEqual(failed_response.status_code, 200)
            self.assertIn("Gemini request failed", failed_response.text)
            self.assertIn("[redacted secret]", failed_response.text)
            self.assertNotIn("secret-value", failed_response.text)

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
