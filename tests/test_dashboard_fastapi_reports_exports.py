import csv
import tempfile
import unittest
from io import StringIO
from pathlib import Path

from fastapi.testclient import TestClient

from dashboard.app import create_app
from dashboard.auth import AuthSession, AuthenticatedUser, AuthenticationError
from dashboard.config import DashboardSettings
from dashboard.supabase_client import ArtifactMetadata


class FakeSupabaseAuthClient:
    def __init__(self):
        self.user = AuthenticatedUser(
            user_id="user-123",
            email="owner@example.com",
            access_token="token-123",
        )

    def sign_in_with_password(self, email: str, password: str) -> AuthSession:
        raise AuthenticationError("Not needed in report/export tests")

    def get_user(self, access_token: str) -> AuthenticatedUser:
        if access_token != self.user.access_token:
            raise AuthenticationError("Invalid session")
        return self.user


class FakeDashboardDataClient:
    def __init__(self):
        self.runs = [
            {
                "run_id": "run-present",
                "status": "succeeded",
                "run_type": "daily",
                "started_at": "2026-05-10T01:00:00Z",
                "finished_at": "2026-05-10T01:07:00Z",
                "duration_seconds": 420,
                "triggered_by": "systemd",
                "raw_candidate_count": 2,
                "eligible_candidate_count": 1,
                "selected_count": 1,
                "error_summary": "",
            },
            {
                "run_id": "run-missing",
                "status": "succeeded",
                "run_type": "daily",
                "started_at": "2026-05-09T01:00:00Z",
                "finished_at": "2026-05-09T01:04:00Z",
                "duration_seconds": 240,
                "triggered_by": "systemd",
                "raw_candidate_count": 0,
                "eligible_candidate_count": 0,
                "selected_count": 0,
                "error_summary": "",
            },
        ]
        self.outputs = {
            "run-present": [
                {
                    "run_id": "run-present",
                    "artifact_type": "report",
                    "bucket": "dashboard-artifacts",
                    "object_path": "runs/run-present/report.md",
                    "filename": "report.md",
                    "content_type": "text/markdown",
                    "size_bytes": 200,
                    "checksum": "sha256:abc",
                    "created_at": "2026-05-10T01:07:00Z",
                },
                {
                    "run_id": "run-present",
                    "artifact_type": "workbook",
                    "bucket": "dashboard-artifacts",
                    "object_path": "runs/run-present/workbook.xlsx",
                    "filename": "workbook.xlsx",
                    "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "size_bytes": 1024,
                    "checksum": "sha256:def",
                    "created_at": "2026-05-10T01:07:00Z",
                },
            ],
            "run-missing": [
                {
                    "run_id": "run-missing",
                    "artifact_type": "report",
                    "bucket": "dashboard-artifacts",
                    "object_path": "runs/run-missing/report.md",
                    "filename": "report.md",
                    "content_type": "text/markdown",
                    "size_bytes": 0,
                    "checksum": "",
                    "created_at": "2026-05-09T01:04:00Z",
                }
            ],
        }
        self.artifact_bodies = {
            "runs/run-present/report.md": (
                "# What We Learned\n\n"
                "- Selected at: 2026-05-10T01:07:00Z\n"
                "- Lead with the breakfast setup.\n\n"
                "| Concept | Hook |\n"
                "|---|---|\n"
                "| Routine demo | Show breakfast setup |\n"
            )
        }
        self.raw_videos = [
            {
                "video_id": "video-1",
                "run_id": "run-present",
                "tiktok_url": "https://tiktok.test/video-1",
                "author_handle": "@creator1",
                "caption": "Gut health hook",
                "hashtags": ["guthealth", "bloating"],
                "source_input": "#guthealth",
                "play_count": 12000,
                "like_count": 900,
                "comment_count": 20,
                "share_count": 80,
                "created_at": "2026-05-10T00:00:00Z",
            },
            {
                "video_id": "video-2",
                "run_id": "run-present",
                "tiktok_url": "https://tiktok.test/video-2",
                "author_handle": "@creator2",
                "caption": "Generic wellness clip",
                "hashtags": ["wellness"],
                "source_input": "#wellness",
                "play_count": 8000,
                "like_count": 100,
                "comment_count": 2,
                "share_count": 1,
                "created_at": "2026-05-10T00:05:00Z",
            },
        ]
        self.selected_videos = [
            {
                "run_id": "run-present",
                "video_id": "video-1",
                "selection_rank": 1,
                "selection_reason": "Strong Nattome hook",
                "evidence_status": "analyzed",
            }
        ]
    def list_runs(self, *, limit: int = 50):
        return self.runs[:limit]

    def get_run(self, run_id: str):
        return next((run for run in self.runs if run["run_id"] == run_id), None)

    def list_run_outputs(self, run_id: str):
        return self.outputs.get(run_id, [])

    def get_report_artifact(self, run_id: str):
        for output in self.list_run_outputs(run_id):
            if output["artifact_type"] == "report":
                return ArtifactMetadata(**output)
        return None

    def download_artifact_text(self, metadata: ArtifactMetadata):
        return self.artifact_bodies.get(metadata.object_path)

    def list_raw_videos(self):
        return self.raw_videos

    def list_selected_videos(self):
        return self.selected_videos


class FailingDashboardDataClient:
    def list_runs(self, *, limit: int = 50):
        raise RuntimeError("Supabase Postgres unavailable")


class DashboardFastAPIReportsExportsTest(unittest.TestCase):
    def test_report_routes_require_authentication(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = TestClient(
                create_app(DashboardSettings(workspace_path=Path(temp_dir))),
                follow_redirects=False,
            )

            reports_response = client.get("/reports")
            report_response = client.get("/reports/run-present")
            raw_export_response = client.get("/exports/raw-videos.csv")
            summary_export_response = client.get("/exports/run-summaries.csv")

            for response in [
                reports_response,
                report_response,
                raw_export_response,
                summary_export_response,
            ]:
                with self.subTest(path=response.request.url.path):
                    self.assertEqual(response.status_code, 303)
                    self.assertEqual(response.headers["location"], "/login")

    def test_reports_route_lists_report_runs_with_legacy_theme(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = self._client(Path(temp_dir), FakeDashboardDataClient())

            response = client.get("/reports")

            self.assertEqual(response.status_code, 200)
            self.assertIn("Reports", response.text)
            self.assertIn('<section class="panel">', response.text)
            self.assertIn('href="/reports/run-present"', response.text)
            self.assertIn('href="/reports/run-missing"', response.text)
            self.assertIn("report.md", response.text)

    def test_reports_route_renders_data_error_instead_of_internal_server_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = self._client(Path(temp_dir), FailingDashboardDataClient())

            response = client.get("/reports")

            self.assertEqual(response.status_code, 503)
            self.assertIn("Reports unavailable", response.text)
            self.assertIn("Supabase Postgres unavailable", response.text)
            self.assertIn("No Supabase reports yet", response.text)

    def test_report_detail_renders_markdown_and_missing_artifact_empty_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = self._client(Path(temp_dir), FakeDashboardDataClient())

            present_response = client.get("/reports/run-present")
            missing_response = client.get("/reports/run-missing")

            self.assertEqual(present_response.status_code, 200)
            self.assertIn("What We Learned", present_response.text)
            self.assertIn("Selected at: 2026-05-10 09:07:00 +0800", present_response.text)
            self.assertIn("Lead with the breakfast setup.", present_response.text)
            self.assertIn("<table", present_response.text)
            self.assertIn("Routine demo", present_response.text)
            self.assertIn('class="panel wide-panel report-reader"', present_response.text)
            self.assertEqual(missing_response.status_code, 200)
            self.assertIn("Report unavailable", missing_response.text)
            self.assertIn("No report Markdown artifact is available for this run.", missing_response.text)
            self.assertNotIn("dashboard-artifacts", missing_response.text)

    def test_csv_exports_download_supabase_data(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = self._client(Path(temp_dir), FakeDashboardDataClient())

            raw_response = client.get("/exports/raw-videos.csv")
            summary_response = client.get("/exports/run-summaries.csv")

            raw_rows = list(csv.DictReader(StringIO(raw_response.text)))
            summary_rows = list(csv.DictReader(StringIO(summary_response.text)))
            self.assertEqual(raw_response.status_code, 200)
            self.assertEqual(raw_response.headers["content-type"], "text/csv; charset=utf-8")
            self.assertEqual(
                raw_response.headers["content-disposition"],
                'attachment; filename="nattome-raw-videos.csv"',
            )
            self.assertEqual([row["video_id"] for row in raw_rows], ["video-1", "video-2"])
            self.assertEqual(raw_rows[0]["hashtags"], "guthealth; bloating")
            self.assertEqual(raw_rows[0]["selection_status"], "analyzed")
            self.assertEqual(
                raw_rows[0].keys(),
                {
                    "video_id",
                    "tiktok_url",
                    "author_handle",
                    "caption",
                    "hashtags",
                    "source_input",
                    "play_count",
                    "like_count",
                    "comment_count",
                    "share_count",
                    "created_at",
                    "is_downloadable",
                    "run_id",
                    "config_version",
                    "selection_status",
                    "source_artifact_path",
                },
            )
            self.assertEqual(raw_rows[1]["selection_status"], "raw")
            self.assertEqual(summary_response.status_code, 200)
            self.assertEqual(
                summary_response.headers["content-disposition"],
                'attachment; filename="nattome-run-summaries.csv"',
            )
            self.assertEqual([row["run_id"] for row in summary_rows], ["run-present", "run-missing"])
            self.assertEqual(summary_rows[0]["raw_candidates"], "2")
            self.assertEqual(summary_rows[0]["selected_count"], "1")
            self.assertIn("report", summary_rows[0]["output_types"])
            self.assertIn("runs/run-present/report.md", summary_rows[0]["output_links"])

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
