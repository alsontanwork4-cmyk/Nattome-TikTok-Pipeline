import http.client
import json
import sqlite3
import subprocess
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

from dashboard.manual_runs import list_manual_runs, trigger_manual_run
from dashboard.settings import save_settings_version
from dashboard.store import DASHBOARD_DB_PATH, initialize_dashboard_store
from dashboard.web import DashboardServer, create_handler


class FakeExecutor:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.calls = []

    def __call__(self, command, *, cwd):
        self.calls.append((list(command), Path(cwd)))
        return subprocess.CompletedProcess(
            command,
            self.returncode,
            stdout=self.stdout,
            stderr=self.stderr,
        )


class DashboardManualRunsTest(unittest.TestCase):
    def test_run_history_route_exposes_controls_and_visible_status(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            executor = FakeExecutor(stdout="ok")

            initial_response, initial_body = self._request(workspace, "GET", "/run-history")
            post_response, _ = self._request(
                workspace,
                "POST",
                "/manual-runs/trigger",
                body=urlencode({"user": "marketer@example.com"}),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                executor=executor,
            )
            final_response, final_body = self._request(workspace, "GET", "/run-history")

            self.assertEqual(initial_response.status, 200)
            self.assertNotIn("Run scrape now", initial_body)
            self.assertIn("Run full pipeline", initial_body)
            self.assertIn("Estimated runtime: 15-30 minutes", initial_body)
            self.assertIn("Expected outputs: scrape JSON, selected batch, and source-video snapshot run folder.", initial_body)
            self.assertEqual(post_response.status, 303)
            self.assertEqual(len(executor.calls), 2)
            self.assertEqual(final_response.status, 200)
            self.assertIn("Full Pipeline", final_body)
            self.assertIn("completed", final_body)
            self.assertIn("marketer@example.com", final_body)
            self.assertIn("Source: manual", final_body)

    def test_full_pipeline_manual_run_records_provenance_and_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            save_settings_version(
                workspace,
                {
                    "hashtags": "#guthealth",
                    "keywords": "bloating",
                    "competitor_profiles": "@gaviscon",
                    "scope": "all",
                    "results_per_input": 25,
                    "minimum_views": 10000,
                    "maximum_age_days": 14,
                    "minimum_weighted_engagement_rate": 0.025,
                    "requires_downloadable_video": True,
                },
                reason="Production config",
                user="ops@example.com",
            )
            executor = FakeExecutor(stdout="scrape complete")

            record = trigger_manual_run(
                workspace,
                "full_pipeline",
                triggered_by="marketer@example.com",
                executor=executor,
                now=datetime(2026, 5, 7, 9, 15, tzinfo=timezone.utc),
            )

            self.assertEqual(record.run_type, "full_pipeline")
            self.assertEqual(record.status, "completed")
            self.assertEqual(record.config_version, "v1")
            self.assertEqual(record.triggered_by, "marketer@example.com")
            self.assertEqual(record.triggered_at, "2026-05-07T17:15:00+08:00")
            self.assertEqual(
                record.output_paths["raw_scrape"],
                "runs/batch-analysis/20260507T171500+0800_daily/data/raw_scrape_all.json",
            )
            self.assertEqual(
                record.output_paths["daily_selection"],
                "runs/batch-analysis/20260507T171500+0800_daily/data/daily_selection_top_videos.json",
            )
            self.assertEqual(
                record.output_paths["run_folder"],
                "runs/batch-analysis/20260507T171500+0800_daily",
            )
            self.assertEqual(
                record.output_paths["selected_batch"],
                "runs/batch-analysis/20260507T171500+0800_daily/data/selected_batch.json",
            )
            self.assertEqual(
                record.output_paths["source_video_index"],
                "runs/batch-analysis/20260507T171500+0800_daily/data/evidence_bundle_index.json",
            )
            self.assertEqual(
                record.output_paths["run_manifest"],
                "runs/batch-analysis/20260507T171500+0800_daily/run_manifest.json",
            )
            self.assertEqual(len(executor.calls), 2)
            command, cwd = executor.calls[0]
            self.assertEqual(cwd, workspace)
            self.assertIn("batch_analysis/scrape_tiktok.py", command)
            self.assertIn("--config", command)
            self.assertIn("batch_analysis/scrape_config.json", command)
            self.assertIn("--download-videos", command)

            rows = list_manual_runs(workspace)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].id, record.id)
            self.assertEqual(rows[0].source_type, "manual")

            connection = sqlite3.connect(workspace / DASHBOARD_DB_PATH)
            connection.row_factory = sqlite3.Row
            try:
                row = connection.execute("SELECT * FROM manual_runs").fetchone()
            finally:
                connection.close()

            self.assertEqual(row["status"], "completed")
            self.assertEqual(row["config_version"], "v1")
            self.assertEqual(row["source_type"], "manual")
            self.assertEqual(json.loads(row["output_paths_json"]), record.output_paths)

    def test_full_pipeline_manual_run_launches_scrape_then_batch_analysis(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            save_settings_version(
                workspace,
                {
                    "hashtags": "#guthealth",
                    "keywords": "bloating",
                    "competitor_profiles": "@gaviscon",
                },
                reason="Production config",
            )
            executor = FakeExecutor(stdout="ok")

            record = trigger_manual_run(
                workspace,
                "full_pipeline",
                triggered_by="marketer@example.com",
                executor=executor,
                now=datetime(2026, 5, 7, 9, 15, tzinfo=timezone.utc),
            )

            self.assertEqual(record.status, "completed")
            self.assertEqual(len(executor.calls), 2)
            scrape_command = executor.calls[0][0]
            batch_command = executor.calls[1][0]
            self.assertIn("batch_analysis/scrape_tiktok.py", scrape_command)
            self.assertIn("batch_analysis/run_batch_analysis.py", batch_command)
            self.assertNotIn("--mode", batch_command)
            self.assertIn("--candidates", batch_command)
            self.assertIn(record.output_paths["daily_selection"], batch_command)
            self.assertIn("--timestamp", batch_command)
            self.assertIn("2026-05-07T17:15:00+08:00", batch_command)
            self.assertIn("--runs-dir", batch_command)
            self.assertIn("runs/batch-analysis", batch_command)
            self.assertEqual(
                record.output_paths["run_folder"],
                "runs/batch-analysis/20260507T171500+0800_daily",
            )

    def test_manual_run_failure_records_failed_status_and_error_text(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            initialize_dashboard_store(workspace)
            executor = FakeExecutor(returncode=7, stderr="Apify unavailable")

            record = trigger_manual_run(
                workspace,
                "full_pipeline",
                triggered_by="marketer@example.com",
                executor=executor,
                now=datetime(2026, 5, 7, 9, 15, tzinfo=timezone.utc),
            )

            self.assertEqual(record.status, "failed")
            self.assertEqual(record.error_text, "Apify unavailable")

    def test_manual_runs_do_not_reuse_existing_output_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            existing = (
                workspace
                / "runs"
                / "batch-analysis"
                / "20260507T171500+0800_daily"
                / "data"
                / "raw_scrape_all.json"
            )
            existing.parent.mkdir(parents=True)
            existing.write_text("{}", encoding="utf-8")
            executor = FakeExecutor(stdout="ok")

            record = trigger_manual_run(
                workspace,
                "full_pipeline",
                triggered_by="marketer@example.com",
                executor=executor,
                now=datetime(2026, 5, 7, 9, 15, tzinfo=timezone.utc),
            )

            self.assertEqual(
                record.output_paths["raw_scrape"],
                "runs/batch-analysis/20260507T171501+0800_daily/data/raw_scrape_all.json",
            )

    def test_scrape_only_manual_run_type_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            with self.assertRaisesRegex(ValueError, "unknown manual run type: scrape_only"):
                trigger_manual_run(workspace, "scrape_only")

    def _request(
        self,
        workspace: Path,
        method: str,
        path: str,
        *,
        body: str | None = None,
        headers: dict[str, str] | None = None,
        executor: FakeExecutor | None = None,
    ):
        server = DashboardServer(
            ("127.0.0.1", 0),
            create_handler(workspace, manual_run_executor=executor),
        )
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            host, port = server.server_address
            connection = http.client.HTTPConnection(host, port, timeout=5)
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            response_body = response.read().decode("utf-8")
            return response, response_body
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()
