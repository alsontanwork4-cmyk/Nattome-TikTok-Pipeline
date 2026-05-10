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
        raise AuthenticationError("Not needed in overview tests")

    def get_user(self, access_token: str) -> AuthenticatedUser:
        if access_token != self.user.access_token:
            raise AuthenticationError("Invalid session")
        return self.user


class FakeDashboardDataClient:
    def __init__(self):
        self.runs = [
            {
                "run_id": "run-latest",
                "status": "failed",
                "run_type": "daily",
                "started_at": "2026-05-10T01:00:00Z",
                "finished_at": "2026-05-10T01:04:00Z",
                "duration_seconds": 240,
                "triggered_by": "systemd",
                "raw_candidate_count": 30,
                "eligible_candidate_count": 11,
                "selected_count": 3,
                "error_summary": "Gemini request failed after upload",
            },
            {
                "run_id": "run-older",
                "status": "succeeded",
                "run_type": "daily",
                "started_at": "2026-05-09T01:00:00Z",
                "finished_at": "2026-05-09T01:08:00Z",
                "duration_seconds": 480,
                "triggered_by": "systemd",
                "raw_candidate_count": 27,
                "eligible_candidate_count": 8,
                "selected_count": 3,
                "error_summary": "",
            },
        ]
        self.outputs = {
            "run-latest": [
                {
                    "artifact_type": "report",
                    "bucket": "dashboard-artifacts",
                    "object_path": "runs/run-latest/report.md",
                    "filename": "report.md",
                    "content_type": "text/markdown",
                    "size_bytes": 4096,
                    "checksum": "sha256:abc",
                    "created_at": "2026-05-10T01:04:00Z",
                },
                {
                    "artifact_type": "workbook",
                    "bucket": "dashboard-artifacts",
                    "object_path": "runs/run-latest/workbook.xlsx",
                    "filename": "workbook.xlsx",
                    "content_type": (
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    ),
                    "size_bytes": 8192,
                    "checksum": "sha256:def",
                    "created_at": "2026-05-10T01:04:00Z",
                },
            ],
        }

    def list_runs(self, *, limit: int = 50):
        return self.runs[:limit]

    def get_run(self, run_id: str):
        return next((run for run in self.runs if run["run_id"] == run_id), None)

    def list_run_outputs(self, run_id: str):
        return self.outputs.get(run_id, [])


class DashboardFastAPIOverviewTest(unittest.TestCase):
    def test_overview_route_requires_authentication(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = TestClient(
                create_app(DashboardSettings(workspace_path=Path(temp_dir))),
                follow_redirects=False,
            )

            response = client.get("/")

            self.assertEqual(response.status_code, 303)
            self.assertEqual(response.headers["location"], "/login")

    def test_overview_renders_empty_state_without_sqlite_runtime(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            data_client = FakeDashboardDataClient()
            data_client.runs = []
            client = self._client(workspace, data_client)

            response = client.get("/")

            self.assertEqual(response.status_code, 200)
            self.assertIn("Overview", response.text)
            self.assertIn("No Supabase run data yet", response.text)
            self.assertIn("The worker has not published dashboard metadata.", response.text)
            self.assertIn('href="/runs"', response.text)
            self.assertIn('<section class="panel feature overview-hero">', response.text)
            self.assertFalse((workspace / "data" / "dashboard" / "dashboard.sqlite3").exists())

    def test_overview_renders_latest_run_summary_links_and_operational_issue(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = self._client(Path(temp_dir), FakeDashboardDataClient())

            response = client.get("/")

            self.assertEqual(response.status_code, 200)
            self.assertIn("Latest run", response.text)
            self.assertIn('href="/runs/run-latest"', response.text)
            self.assertNotIn('href="/runs/run-older"', response.text)
            self.assertIn("Failed", response.text)
            self.assertIn("2026-05-10T01:00:00Z", response.text)
            self.assertIn("2026-05-10T01:04:00Z", response.text)
            self.assertIn("4m 0s", response.text)
            self.assertIn("Raw candidates", response.text)
            self.assertIn("Eligible candidates", response.text)
            self.assertIn("Selected", response.text)
            self.assertIn(">30<", response.text)
            self.assertIn(">11<", response.text)
            self.assertIn(">3<", response.text)
            self.assertIn("2 outputs available", response.text)
            self.assertIn('href="/reports/run-latest"', response.text)
            self.assertIn('href="/artifacts/runs/run-latest/report.md"', response.text)
            self.assertIn('href="/artifacts/runs/run-latest/workbook.xlsx"', response.text)
            self.assertIn("Gemini request failed after upload", response.text)

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
