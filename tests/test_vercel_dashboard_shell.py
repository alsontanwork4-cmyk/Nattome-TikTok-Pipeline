import json
import unittest
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
APP_ROOT = WORKSPACE / "web" / "vercel-dashboard"
README = WORKSPACE / "README.md"


class VercelDashboardShellTest(unittest.TestCase):
    def test_next_typescript_app_lives_separately_from_python_dashboard(self):
        package_json = json.loads((APP_ROOT / "package.json").read_text(encoding="utf-8"))

        self.assertEqual(package_json["name"], "nattome-vercel-dashboard")
        self.assertTrue((APP_ROOT / "src" / "app" / "page.tsx").is_file())
        self.assertTrue((WORKSPACE / "dashboard" / "web.py").is_file())
        self.assertIn("next", package_json["dependencies"])
        self.assertIn("typescript", package_json["devDependencies"])
        self.assertIn("build", package_json["scripts"])
        self.assertIn("typecheck", package_json["scripts"])

    def test_vercel_app_has_private_supabase_auth_boundary(self):
        middleware = (APP_ROOT / "src" / "middleware.ts").read_text(encoding="utf-8")
        auth = (APP_ROOT / "src" / "lib" / "auth.ts").read_text(encoding="utf-8")
        page = (APP_ROOT / "src" / "app" / "page.tsx").read_text(encoding="utf-8")

        self.assertIn("createServerClient", middleware)
        self.assertIn("auth.getUser", middleware)
        self.assertIn("/login", middleware)
        self.assertIn("export const config", middleware)
        self.assertIn("requireAuthenticatedUser", auth)
        self.assertIn("redirect(\"/login\")", auth)
        self.assertIn("requireAuthenticatedUser", page)

    def test_data_access_layer_exposes_latest_run_interface(self):
        data_access = (APP_ROOT / "src" / "lib" / "dailyEvidenceRuns.ts").read_text(
            encoding="utf-8"
        )

        self.assertIn("export interface DailyEvidenceRunRepository", data_access)
        self.assertIn("getLatestRun", data_access)
        self.assertIn("daily_evidence_runs", data_access)
        self.assertIn("run_timestamp", data_access)
        self.assertIn("maybeSingle", data_access)

    def test_authenticated_shell_renders_minimal_dashboard_frame(self):
        page = (APP_ROOT / "src" / "app" / "page.tsx").read_text(encoding="utf-8")
        layout = (APP_ROOT / "src" / "app" / "layout.tsx").read_text(encoding="utf-8")

        self.assertIn("Nattome Daily Evidence Dashboard", page)
        self.assertIn("Signed in as", page)
        self.assertIn("Latest Daily Evidence Run", page)
        self.assertIn("No cloud-published Daily Evidence Run is available yet.", page)
        self.assertIn("metadata", layout)

    def test_vercel_supabase_environment_is_documented(self):
        readme = README.read_text(encoding="utf-8")
        env_example = (APP_ROOT / ".env.example").read_text(encoding="utf-8")

        for name in ("NEXT_PUBLIC_SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_ANON_KEY"):
            self.assertIn(name, readme)
            self.assertIn(name, env_example)
        self.assertIn("Vercel Dashboard", readme)
        self.assertIn("Supabase Auth", readme)


if __name__ == "__main__":
    unittest.main()
