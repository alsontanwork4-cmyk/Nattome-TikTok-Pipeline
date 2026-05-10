import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEPLOYMENT_DOC = PROJECT_ROOT / "docs" / "vps-dashboard-deployment.md"


class VpsDashboardDeploymentDocsTest(unittest.TestCase):
    def test_supabase_fastapi_vps_deployment_path_is_complete(self):
        text = DEPLOYMENT_DOC.read_text(encoding="utf-8")

        expected_fragments = [
            "uvicorn dashboard.app:create_app --factory --host 127.0.0.1 --port 8765",
            "nattome-dashboard.service",
            "nattome-dashboard-worker.service",
            "proxy_pass http://127.0.0.1:8765",
            "DASHBOARD_RUNTIME_MODE=production",
            "DASHBOARD_WORKSPACE_PATH=/opt/nattome-pipeline",
            "SUPABASE_URL=https://YOUR-PROJECT.supabase.co",
            "SUPABASE_ANON_KEY=replace_me",
            "SUPABASE_SERVICE_ROLE_KEY=replace_me",
            "SUPABASE_STORAGE_BUCKET=dashboard-artifacts",
            "Supabase Auth",
            "Supabase Postgres backups",
            "Supabase Storage export",
        ]
        for fragment in expected_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

        retired_commands = [
            "python -m dashboard.web",
            "python -c \"from dashboard.indexer import index_pipeline_artifacts",
            "apache2-utils",
            "htpasswd",
        ]
        for command in retired_commands:
            with self.subTest(command=command):
                self.assertNotIn(command, text)


if __name__ == "__main__":
    unittest.main()
