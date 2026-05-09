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

    def test_vercel_app_has_public_supabase_read_boundary(self):
        page = (APP_ROOT / "src" / "app" / "page.tsx").read_text(encoding="utf-8")
        login = (APP_ROOT / "src" / "app" / "login" / "page.tsx").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("requireAuthenticatedUser", page)
        self.assertNotIn("signInWithPassword", login)
        self.assertNotIn('name="password"', login)
        self.assertIn('redirect("/")', login)

    def test_data_access_layer_exposes_latest_run_interface(self):
        data_access = (APP_ROOT / "src" / "lib" / "dailyEvidenceRuns.ts").read_text(
            encoding="utf-8"
        )

        self.assertIn("export interface DailyEvidenceRunRepository", data_access)
        self.assertIn("getLatestRun", data_access)
        self.assertIn("getRunById", data_access)
        self.assertIn("listRuns", data_access)
        self.assertIn("daily_evidence_runs", data_access)
        self.assertIn("daily_evidence_artifacts", data_access)
        self.assertIn('.eq("publication_status", "published")', data_access)
        self.assertIn("run_timestamp", data_access)
        self.assertIn("maybeSingle", data_access)

    def test_public_shell_renders_minimal_dashboard_frame(self):
        page = (APP_ROOT / "src" / "app" / "page.tsx").read_text(encoding="utf-8")
        layout = (APP_ROOT / "src" / "app" / "layout.tsx").read_text(encoding="utf-8")

        self.assertIn("Nattome Daily Evidence Dashboard", page)
        self.assertNotIn("Signed in as", page)
        self.assertIn("Latest Daily Evidence Run", page)
        self.assertIn("Run History", page)
        self.assertIn("Daily Output Set", page)
        self.assertIn("runView.message", page)
        self.assertIn("metadata", layout)

    def test_latest_run_view_covers_daily_output_set_states(self):
        data_access = (APP_ROOT / "src" / "lib" / "dailyEvidenceRuns.ts").read_text(
            encoding="utf-8"
        )
        view_tests = (
            APP_ROOT / "src" / "lib" / "dailyEvidenceRuns.test.mjs"
        ).read_text(encoding="utf-8")

        for label in (
            "Cross-Video Pattern Summary",
            "Final Markdown",
            "Structured JSON",
            "Spreadsheet",
            "Raw Scrape",
            "Daily Top-5 Selection",
        ):
            self.assertIn(label, data_access)
        self.assertIn("No cloud-published Daily Evidence Run is available yet.", data_access)
        self.assertIn("marks missing artifacts unavailable", view_tests)
        self.assertIn("returns the empty state", view_tests)

    def test_run_history_and_detail_download_surfaces_exist(self):
        page = (APP_ROOT / "src" / "app" / "page.tsx").read_text(encoding="utf-8")
        detail_page = (
            APP_ROOT / "src" / "app" / "runs" / "[runId]" / "page.tsx"
        ).read_text(encoding="utf-8")
        data_access = (APP_ROOT / "src" / "lib" / "dailyEvidenceRuns.ts").read_text(
            encoding="utf-8"
        )
        view_tests = (
            APP_ROOT / "src" / "lib" / "dailyEvidenceRuns.test.mjs"
        ).read_text(encoding="utf-8")

        self.assertIn("buildDailyEvidenceRunHistoryView", page)
        self.assertIn("repository.listRuns", page)
        self.assertIn("href={run.href}", page)
        self.assertIn("getRunById", detail_page)
        self.assertIn("Back to run history", detail_page)
        self.assertIn("?download=", data_access)
        self.assertNotIn("SUPABASE_SERVICE_ROLE_KEY", data_access)
        self.assertIn("without service role data", view_tests)
        self.assertIn("repository lists run history across publication states", view_tests)

    def test_vercel_supabase_environment_is_documented(self):
        readme = README.read_text(encoding="utf-8")
        env_example = (APP_ROOT / ".env.example").read_text(encoding="utf-8")

        for name in ("NEXT_PUBLIC_SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_ANON_KEY"):
            self.assertIn(name, readme)
            self.assertIn(name, env_example)
        self.assertIn("Vercel Dashboard", readme)
        self.assertIn("public Supabase anon key", readme)


if __name__ == "__main__":
    unittest.main()
