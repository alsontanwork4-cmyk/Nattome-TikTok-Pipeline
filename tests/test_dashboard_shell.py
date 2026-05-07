import http.client
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path

from dashboard.store import (
    DASHBOARD_DB_PATH,
    MUTABLE_TABLES,
    initialize_dashboard_store,
)
from dashboard.web import DashboardServer, create_handler


class DashboardStoreTest(unittest.TestCase):
    def test_dashboard_store_initializes_predictable_sqlite_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            db_path = initialize_dashboard_store(workspace)

            self.assertEqual(db_path, workspace / DASHBOARD_DB_PATH)
            self.assertTrue(db_path.is_file())

            connection = sqlite3.connect(db_path)
            try:
                user_version = connection.execute("PRAGMA user_version").fetchone()[0]
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    )
                }
            finally:
                connection.close()

            self.assertEqual(user_version, 1)
            self.assertIn("dashboard_metadata", tables)
            for table_name in MUTABLE_TABLES:
                self.assertIn(table_name, tables)

    def test_mutable_dashboard_tables_have_attribution_columns(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = initialize_dashboard_store(Path(temp_dir))

            connection = sqlite3.connect(db_path)
            try:
                for table_name in MUTABLE_TABLES:
                    with self.subTest(table=table_name):
                        columns = {
                            row[1]
                            for row in connection.execute(f"PRAGMA table_info({table_name})")
                        }

                        self.assertIn("created_by", columns)
                        self.assertIn("updated_by", columns)
                        self.assertIn("created_at", columns)
                        self.assertIn("updated_at", columns)
            finally:
                connection.close()


class DashboardWebShellTest(unittest.TestCase):
    def test_overview_route_loads_without_pipeline_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            server = DashboardServer(
                ("127.0.0.1", 0),
                create_handler(workspace),
            )
            thread = threading.Thread(target=server.serve_forever)
            thread.start()
            try:
                host, port = server.server_address
                connection = http.client.HTTPConnection(host, port, timeout=5)
                connection.request("GET", "/")
                response = connection.getresponse()
                body = response.read().decode("utf-8")
            finally:
                server.shutdown()
                thread.join(timeout=5)
                server.server_close()

            self.assertEqual(response.status, 200)
            self.assertIn("Latest Run Overview", body)
            self.assertIn("Overview", body)
            self.assertIn("Scraped Content", body)
            self.assertIn("Run History", body)
            self.assertIn("Scrape Settings", body)
            self.assertIn("Recommendations", body)
            self.assertIn("Pattern Library", body)
            self.assertIn("Nattome POV Library", body)
            self.assertIn("Pipeline Architecture", body)
            self.assertTrue((workspace / DASHBOARD_DB_PATH).is_file())
