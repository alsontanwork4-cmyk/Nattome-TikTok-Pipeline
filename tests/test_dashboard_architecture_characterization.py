import html
import http.client
import inspect
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path

import dashboard.architecture as dashboard_architecture
import dashboard.exports as dashboard_exports
import dashboard.health as dashboard_health
import dashboard.indexer as dashboard_indexer
import dashboard.nattome_pov_library as dashboard_nattome_pov_library
import dashboard.pattern_library as dashboard_pattern_library
import dashboard.quality as dashboard_quality
import dashboard.recommendations as dashboard_recommendations
import dashboard.run_history as dashboard_run_history
import dashboard.search as dashboard_search
import dashboard.web as dashboard_web
from dashboard.store import DASHBOARD_DB_PATH


class DashboardArchitectureCharacterizationTest(unittest.TestCase):
    def test_heavy_dashboard_modules_use_store_connection_helper(self):
        modules = [
            dashboard_architecture,
            dashboard_exports,
            dashboard_health,
            dashboard_indexer,
            dashboard_nattome_pov_library,
            dashboard_pattern_library,
            dashboard_quality,
            dashboard_recommendations,
            dashboard_run_history,
            dashboard_search,
        ]

        for module in modules:
            with self.subTest(module=module.__name__):
                source = inspect.getsource(module)

                self.assertNotIn("initialize_dashboard_store(", source)
                self.assertNotIn("sqlite3.connect(", source)

    def test_public_dashboard_web_imports_remain_usable(self):
        namespace: dict[str, object] = {}

        exec("from dashboard.web import *", namespace)

        expected_exports = {
            "CURATION_LABELS",
            "DashboardServer",
            "NAV_GROUPS",
            "NAV_ITEMS",
            "create_handler",
            "main",
            "render_page",
            "resolve_dashboard_workspace",
            "serve",
        }
        self.assertEqual(set(dashboard_web.__all__), expected_exports)
        for export_name in expected_exports:
            with self.subTest(export=export_name):
                self.assertIn(export_name, namespace)

        self.assertIs(namespace["NAV_ITEMS"], dashboard_web.NAV_ITEMS)
        self.assertIs(namespace["NAV_GROUPS"], dashboard_web.NAV_GROUPS)
        self.assertIs(namespace["CURATION_LABELS"], dashboard_web.CURATION_LABELS)
        self.assertTrue(callable(namespace["create_handler"]))
        self.assertTrue(callable(namespace["render_page"]))
        self.assertTrue(callable(namespace["resolve_dashboard_workspace"]))
        self.assertTrue(issubclass(namespace["DashboardServer"], dashboard_web.DashboardServer))

    def test_topbar_preserves_visible_brand_and_operational_status(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            response, body = self._request(workspace, "GET", "/")
            topbar = body[
                body.index('<header class="topbar"') : body.index("</header>") + len("</header>")
            ]

            self.assertEqual(response.status, 200)
            self.assertIn('<header class="topbar" role="banner">', topbar)
            self.assertIn('<div class="brand-mark">', topbar)
            self.assertIn("<span>Nattome</span>", topbar)
            self.assertIn('<span class="brand-tag">Scrape Quality</span>', topbar)
            self.assertIn("Pipeline ready", topbar)
            self.assertIn("Local workspace", topbar)
            self.assertNotIn(html.escape(str(workspace / DASHBOARD_DB_PATH)), topbar)
            self.assertLess(body.index('<header class="topbar"'), body.index('<aside class="sidebar"'))

    def test_navigation_routes_initialize_the_dashboard_store_through_public_requests(self):
        for label, route in dashboard_web.NAV_ITEMS:
            with self.subTest(route=route):
                with tempfile.TemporaryDirectory() as temp_dir:
                    workspace = Path(temp_dir)
                    db_path = workspace / DASHBOARD_DB_PATH

                    response, body = self._request(workspace, "GET", route)

                    self.assertEqual(response.status, 200)
                    self.assertIn(label, body)
                    self.assertTrue(db_path.is_file())
                    connection = sqlite3.connect(db_path)
                    try:
                        schema_name = connection.execute(
                            "SELECT value FROM dashboard_metadata WHERE key = 'schema_name'"
                        ).fetchone()[0]
                        user_version = connection.execute("PRAGMA user_version").fetchone()[0]
                    finally:
                        connection.close()
                    self.assertEqual(schema_name, "nattome_scrape_quality_dashboard")
                    self.assertEqual(user_version, 1)

    def test_health_check_route_stays_lightweight_and_does_not_initialize_store(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            response, body = self._request(workspace, "GET", "/healthz")

            self.assertEqual(response.status, 200)
            self.assertEqual(body, "ok\n")
            self.assertFalse((workspace / DASHBOARD_DB_PATH).exists())

    def test_unknown_routes_return_404_without_initializing_store(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            response, body = self._request(workspace, "GET", "/not-a-dashboard-route")

            self.assertEqual(response.status, 404)
            self.assertIn("Dashboard route not found", body)
            self.assertFalse((workspace / DASHBOARD_DB_PATH).exists())

    def test_web_request_adapter_uses_route_dispatch_tables(self):
        source = inspect.getsource(dashboard_web.create_handler)

        self.assertIn("GET_EXPORT_ROUTES", source)
        self.assertIn("POST_FORM_ACTIONS", source)
        self.assertLessEqual(source.count("if parsed_path =="), 2)
        self.assertNotIn('if parsed_path == "/exports/raw-videos.csv"', source)
        self.assertNotIn('if parsed_path == "/scraped-content/curation"', source)

    def _request(self, workspace: Path, method: str, path: str):
        server = dashboard_web.DashboardServer(
            ("127.0.0.1", 0),
            dashboard_web.create_handler(workspace),
        )
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            host, port = server.server_address
            connection = http.client.HTTPConnection(host, port, timeout=5)
            connection.request(method, path)
            response = connection.getresponse()
            response_body = response.read().decode("utf-8")
            return response, response_body
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()
