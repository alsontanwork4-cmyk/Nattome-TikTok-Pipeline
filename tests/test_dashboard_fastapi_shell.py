import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from dashboard.app import create_app
from dashboard.auth import AuthSession, AuthenticatedUser, AuthenticationError
from dashboard.config import DashboardSettings


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class FakeSupabaseAuthClient:
    def __init__(self):
        self.sessions: dict[str, AuthenticatedUser] = {}

    def sign_in_with_password(self, email: str, password: str) -> AuthSession:
        if email != "owner@example.com" or password != "correct-password":
            raise AuthenticationError("Invalid login credentials")
        user = AuthenticatedUser(
            user_id="user-123",
            email=email,
            access_token="token-123",
        )
        self.sessions[user.access_token] = user
        return AuthSession(
            access_token=user.access_token,
            refresh_token="refresh-123",
            expires_in=3600,
            user=user,
        )

    def get_user(self, access_token: str) -> AuthenticatedUser:
        try:
            return self.sessions[access_token]
        except KeyError as exc:
            raise AuthenticationError("Invalid session") from exc


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

    def test_dashboard_shell_requires_authenticated_user(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = DashboardSettings(workspace_path=Path(temp_dir))
            client = TestClient(create_app(settings), follow_redirects=False)

            response = client.get("/")

            self.assertEqual(response.status_code, 303)
            self.assertEqual(response.headers["location"], "/login")

    def test_login_page_is_public_and_uses_legacy_theme(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = DashboardSettings(workspace_path=Path(temp_dir))
            client = TestClient(create_app(settings))

            response = client.get("/login")

            self.assertEqual(response.status_code, 200)
            self.assertIn("<title>Nattome TikTok Scraper</title>", response.text)
            self.assertIn('<a class="brand-mark" href="/"', response.text)
            self.assertIn('<section class="panel feature">', response.text)
            self.assertIn('<form class="settings-form login-form"', response.text)
            self.assertIn('name="email"', response.text)
            self.assertIn('name="password"', response.text)

    def test_login_sets_session_cookie_and_exposes_authenticated_user_identity(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = DashboardSettings(workspace_path=Path(temp_dir))
            auth_client = FakeSupabaseAuthClient()
            client = TestClient(
                create_app(settings, auth_client=auth_client),
                follow_redirects=False,
            )

            login_response = client.post(
                "/login",
                data={"email": "owner@example.com", "password": "correct-password"},
            )
            dashboard_response = client.get("/")

            self.assertEqual(login_response.status_code, 303)
            self.assertEqual(login_response.headers["location"], "/")
            self.assertIn("dashboard_access_token", login_response.headers["set-cookie"])
            self.assertEqual(dashboard_response.status_code, 200)
            self.assertIn("owner@example.com", dashboard_response.text)
            self.assertIn('data-auth-user-id="user-123"', dashboard_response.text)

    def test_login_failure_rerenders_login_without_setting_session_cookie(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = DashboardSettings(workspace_path=Path(temp_dir))
            client = TestClient(
                create_app(settings, auth_client=FakeSupabaseAuthClient()),
                follow_redirects=False,
            )

            response = client.post(
                "/login",
                data={"email": "owner@example.com", "password": "wrong-password"},
            )

            self.assertEqual(response.status_code, 401)
            self.assertIn("Invalid email or password", response.text)
            self.assertNotIn("dashboard_access_token", response.headers.get("set-cookie", ""))

    def test_logout_clears_session_cookie_and_returns_to_login(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = DashboardSettings(workspace_path=Path(temp_dir))
            client = TestClient(
                create_app(settings, auth_client=FakeSupabaseAuthClient()),
                follow_redirects=False,
            )
            client.post(
                "/login",
                data={"email": "owner@example.com", "password": "correct-password"},
            )

            logout_response = client.post("/logout")
            dashboard_response = client.get("/")

            self.assertEqual(logout_response.status_code, 303)
            self.assertEqual(logout_response.headers["location"], "/login")
            self.assertIn("dashboard_access_token", logout_response.headers["set-cookie"])
            self.assertEqual(dashboard_response.status_code, 303)
            self.assertEqual(dashboard_response.headers["location"], "/login")

    def test_fastapi_shell_renders_base_template_without_legacy_runtime(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            settings = DashboardSettings(workspace_path=workspace)
            client = self._authenticated_client(settings)

            response = client.get("/")

            self.assertEqual(response.status_code, 200)
            self.assertIn("<title>Nattome TikTok Scraper</title>", response.text)
            self.assertIn('<link rel="stylesheet" href="/static/dashboard.css">', response.text)
            self.assertIn('<script src="/static/dashboard.js" defer></script>', response.text)
            self.assertIn('class="layout"', response.text)
            self.assertIn("Nattome", response.text)
            self.assertFalse((workspace / "data" / "dashboard" / "dashboard.sqlite3").exists())

    def test_fastapi_shell_reuses_legacy_dashboard_theme_patterns(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = DashboardSettings(workspace_path=Path(temp_dir))
            client = self._authenticated_client(settings)

            response = client.get("/")
            css_response = client.get("/static/dashboard.css")

            self.assertEqual(response.status_code, 200)
            self.assertIn('<a class="brand-mark" href="/"', response.text)
            self.assertIn('class="brand-logo"', response.text)
            self.assertIn('<div class="topbar-meta">', response.text)
            self.assertIn('<span class="meta-pill primary">', response.text)
            self.assertIn('<div class="nav-group">', response.text)
            self.assertIn('<a class="nav-link" href="/" aria-current="page">', response.text)
            self.assertIn('<nav class="breadcrumb" aria-label="Breadcrumb">', response.text)
            self.assertIn('<div class="page-actions">', response.text)
            self.assertIn('<section class="panel feature overview-hero">', response.text)
            self.assertIn('<div class="empty-state">', response.text)
            self.assertIn('class="action-link" href="/runs"', response.text)
            self.assertEqual(css_response.status_code, 200)
            self.assertIn("--accent: #B85B2E;", css_response.text)
            self.assertIn(".nav-link[aria-current=\"page\"]", css_response.text)
            self.assertIn(".status-pill.ok", css_response.text)
            self.assertIn(".overview-hero", css_response.text)

    def test_fastapi_visual_language_decision_is_documented_for_later_pages(self):
        adr = PROJECT_ROOT / "docs" / "adr" / "0003-supabase-first-fastapi-dashboard-rewrite.md"
        body = adr.read_text(encoding="utf-8")

        self.assertIn(
            "Later FastAPI page slices must keep this legacy visual language",
            body,
        )

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

    def _authenticated_client(self, settings: DashboardSettings) -> TestClient:
        auth_client = FakeSupabaseAuthClient()
        user = AuthenticatedUser(
            user_id="user-123",
            email="owner@example.com",
            access_token="token-123",
        )
        auth_client.sessions[user.access_token] = user
        client = TestClient(create_app(settings, auth_client=auth_client))
        client.cookies.set("dashboard_access_token", user.access_token)
        return client


if __name__ == "__main__":
    unittest.main()
