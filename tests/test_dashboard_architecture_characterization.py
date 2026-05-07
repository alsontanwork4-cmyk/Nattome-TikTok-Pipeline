import html
import http.client
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path

import dashboard.web as dashboard_web
from dashboard.store import DASHBOARD_DB_PATH


class DashboardArchitectureCharacterizationTest(unittest.TestCase):
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

    def test_topbar_preserves_visible_brand_status_and_database_location(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            response, body = self._request(workspace, "GET", "/")

            self.assertEqual(response.status, 200)
            self.assertIn('<header class="topbar" role="banner">', body)
            self.assertIn('<div class="brand-mark">', body)
            self.assertIn("<span>Nattome</span>", body)
            self.assertIn('<span class="brand-tag">Scrape Quality</span>', body)
            self.assertIn("Pipeline ready", body)
            self.assertIn(html.escape(str(workspace / DASHBOARD_DB_PATH)), body)
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
