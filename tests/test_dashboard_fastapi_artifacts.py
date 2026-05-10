import tempfile
import unittest
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
        raise AuthenticationError("Not needed in artifact tests")

    def get_user(self, access_token: str) -> AuthenticatedUser:
        if access_token != self.user.access_token:
            raise AuthenticationError("Invalid session")
        return self.user


class FakeDashboardDataClient:
    def __init__(self):
        self.metadata = {
            "runs/run-1/report.md": ArtifactMetadata(
                run_id="run-1",
                artifact_type="report",
                bucket="dashboard-artifacts",
                object_path="runs/run-1/report.md",
                filename="report.md",
                content_type="text/markdown",
            ),
            "runs/run-1/missing-object.md": ArtifactMetadata(
                run_id="run-1",
                artifact_type="report",
                bucket="dashboard-artifacts",
                object_path="runs/run-1/missing-object.md",
                filename="missing-object.md",
                content_type="text/markdown",
            ),
        }

    def list_runs(self, *, limit: int = 50):
        return []

    def get_run(self, run_id: str):
        return None

    def list_run_outputs(self, run_id: str):
        return []

    def get_artifact_metadata(self, artifact_id: str):
        return self.metadata.get(artifact_id)

    def create_signed_artifact_url(
        self,
        metadata: ArtifactMetadata,
        *,
        expires_in: int = 900,
    ) -> str:
        if metadata.object_path == "runs/run-1/missing-object.md":
            return ""
        return "https://storage.example/signed/report.md?token=short-lived"


class DashboardFastAPIArtifactsTest(unittest.TestCase):
    def test_artifact_route_requires_authentication(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = TestClient(
                create_app(DashboardSettings(workspace_path=Path(temp_dir))),
                follow_redirects=False,
            )

            response = client.get("/artifacts/runs/run-1/report.md")

            self.assertEqual(response.status_code, 303)
            self.assertEqual(response.headers["location"], "/login")

    def test_artifact_route_redirects_to_signed_storage_url(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = self._client(Path(temp_dir), FakeDashboardDataClient())

            response = client.get("/artifacts/runs/run-1/report.md", follow_redirects=False)

            self.assertEqual(response.status_code, 303)
            self.assertEqual(
                response.headers["location"],
                "https://storage.example/signed/report.md?token=short-lived",
            )

    def test_artifact_route_returns_clear_missing_metadata_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = self._client(Path(temp_dir), FakeDashboardDataClient())

            response = client.get("/artifacts/runs/run-1/unknown.md")

            self.assertEqual(response.status_code, 404)
            self.assertIn("Artifact not found", response.text)
            self.assertIn("No Supabase artifact metadata exists for this route.", response.text)
            self.assertNotIn("dashboard-artifacts", response.text)

    def test_artifact_route_returns_clear_missing_object_state_without_bucket_details(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            client = self._client(Path(temp_dir), FakeDashboardDataClient())

            response = client.get("/artifacts/runs/run-1/missing-object.md")

            self.assertEqual(response.status_code, 502)
            self.assertIn("Artifact unavailable", response.text)
            self.assertIn("Supabase Storage did not return a signed download URL.", response.text)
            self.assertNotIn("dashboard-artifacts", response.text)
            self.assertNotIn("missing-object.md", response.text)

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
