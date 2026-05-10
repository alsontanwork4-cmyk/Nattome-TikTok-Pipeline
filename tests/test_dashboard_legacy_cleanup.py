import importlib
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_ROOT = PROJECT_ROOT / "dashboard"


class DashboardLegacyCleanupTest(unittest.TestCase):
    def test_dashboard_web_points_to_fastapi_entrypoint(self):
        dashboard_web = importlib.import_module("dashboard.web")

        source = (DASHBOARD_ROOT / "web.py").read_text(encoding="utf-8")
        self.assertIn("from .app import create_app as fastapi_create_app", source)
        self.assertTrue(callable(dashboard_web.create_app))
        self.assertIn("create_app", dashboard_web.__all__)
        self.assertIn("DashboardSettings", dashboard_web.__all__)
        self.assertNotIn("DashboardServer", dashboard_web.__all__)
        self.assertNotIn("create_handler", dashboard_web.__all__)
        self.assertNotIn("serve", dashboard_web.__all__)

    def test_legacy_dashboard_runtime_files_are_removed(self):
        retired_files = [
            "store.py",
            "indexer.py",
            "refresh.py",
            "manual_runs.py",
            "exports.py",
            "report_view.py",
            "run_history.py",
            "settings.py",
            "web_actions.py",
            "web_components.py",
            "web_layout.py",
            "web_overview.py",
            "web_report.py",
            "web_run_history.py",
            "web_server.py",
            "web_settings.py",
        ]

        for file_name in retired_files:
            with self.subTest(file_name=file_name):
                self.assertFalse((DASHBOARD_ROOT / file_name).exists())

    def test_dashboard_runtime_no_longer_initializes_sqlite(self):
        forbidden_fragments = [
            "sqlite3.connect(",
            "connect_dashboard_store",
            "initialize_dashboard_store",
            "DASHBOARD_DB_PATH",
        ]
        runtime_files = list(DASHBOARD_ROOT.glob("*.py"))

        for path in runtime_files:
            source = path.read_text(encoding="utf-8")
            for fragment in forbidden_fragments:
                with self.subTest(path=path.name, fragment=fragment):
                    self.assertNotIn(fragment, source)

    def test_retired_import_and_route_modules_are_removed(self):
        retired_files = [
            DASHBOARD_ROOT / "legacy_import.py",
            DASHBOARD_ROOT / "routes" / "legacy.py",
            DASHBOARD_ROOT / "time_display.py",
        ]

        for path in retired_files:
            with self.subTest(path=path.name):
                self.assertFalse(path.exists())

    def test_superseded_docs_do_not_prohibit_fastapi_or_supabase(self):
        docs_to_check = [
            PROJECT_ROOT / "README.md",
            PROJECT_ROOT / "docs" / "prd" / "dashboard-codebase-architecture-deepening-prd.md",
            PROJECT_ROOT / "docs" / "prd" / "dashboard-architecture-contract-verification.md",
        ]
        forbidden_fragments = [
            "python -m dashboard.web",
            "should not migrate to Flask, FastAPI",
            "The local HTTP server should remain",
            "SQLite remains the only dashboard store",
            "Keep SQLite as the only real dashboard storage adapter",
        ]

        for path in docs_to_check:
            source = path.read_text(encoding="utf-8")
            for fragment in forbidden_fragments:
                with self.subTest(path=path.name, fragment=fragment):
                    self.assertNotIn(fragment, source)

        readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("uvicorn dashboard.app:create_app --factory", readme)
        self.assertIn("docs/vps-dashboard-deployment.md", readme)


if __name__ == "__main__":
    unittest.main()
