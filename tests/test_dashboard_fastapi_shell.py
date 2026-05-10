import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from dashboard.app import create_app
from dashboard.config import DashboardSettings


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DashboardFastAPIShellTest(unittest.TestCase):
    def test_settings_load_runtime_supabase_and_workspace_paths_from_environment(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            env = {
                "DASHBOARD_RUNTIME_MODE": "production",
                "SUPABASE_URL": "https://project.supabase.co",
                "SUPABASE_ANON_KEY": "anon-key",
                "SUPABASE_SERVICE_ROLE_KEY": "service-key",
                "SUPABASE_STORAGE_BUCKET": "pipeline-artifacts",
                "DASHBOARD_WORKSPACE_PATH": str(workspace),
                "DASHBOARD_RUNS_PATH": str(workspace / "custom-runs"),
                "DASHBOARD_DATA_PATH": str(workspace / "custom-data"),
            }

            settings = DashboardSettings.from_env(env)

            self.assertEqual(settings.runtime_mode, "production")
            self.assertEqual(settings.supabase_url, "https://project.supabase.co")
            self.assertEqual(settings.supabase_anon_key, "anon-key")
            self.assertEqual(settings.supabase_service_role_key, "service-key")
            self.assertEqual(settings.supabase_storage_bucket, "pipeline-artifacts")
            self.assertEqual(settings.workspace_path, workspace.resolve())
            self.assertEqual(settings.runs_path, (workspace / "custom-runs").resolve())
            self.assertEqual(settings.data_path, (workspace / "custom-data").resolve())

    def test_fastapi_app_starts_with_health_check_and_static_assets(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            settings = DashboardSettings(workspace_path=workspace)
            client = TestClient(create_app(settings))

            health_response = client.get("/healthz")
            css_response = client.get("/static/dashboard.css")

            self.assertEqual(health_response.status_code, 200)
            self.assertEqual(health_response.json(), {"status": "ok"})
            self.assertEqual(css_response.status_code, 200)
            self.assertIn(".layout {", css_response.text)
            self.assertFalse((workspace / "data" / "dashboard" / "dashboard.sqlite3").exists())

    def test_fastapi_shell_renders_base_template_without_legacy_runtime(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            settings = DashboardSettings(workspace_path=workspace)
            client = TestClient(create_app(settings))

            response = client.get("/")

            self.assertEqual(response.status_code, 200)
            self.assertIn("<title>Nattome TikTok Scraper</title>", response.text)
            self.assertIn('<link rel="stylesheet" href="/static/dashboard.css">', response.text)
            self.assertIn('<script src="/static/dashboard.js" defer></script>', response.text)
            self.assertIn('class="layout"', response.text)
            self.assertIn("Nattome", response.text)
            self.assertFalse((workspace / "data" / "dashboard" / "dashboard.sqlite3").exists())

    def test_dashboard_app_import_does_not_import_legacy_web_server(self):
        script = (
            "import json, sys; "
            "import dashboard.app; "
            "print(json.dumps({"
            "'web_server': 'dashboard.web_server' in sys.modules, "
            "'store': 'dashboard.store' in sys.modules"
            "}))"
        )

        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

        imported_modules = json.loads(result.stdout)
        self.assertFalse(imported_modules["web_server"])
        self.assertFalse(imported_modules["store"])


if __name__ == "__main__":
    unittest.main()
