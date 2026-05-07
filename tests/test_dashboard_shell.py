import json
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
            response, body = self._get_overview(workspace)

            self.assertEqual(response.status, 200)
            self.assertIn("Latest Run Overview", body)
            self.assertIn("No indexed runs yet", body)
            self.assertIn("Overview", body)
            self.assertIn("Scraped Content", body)
            self.assertIn("Run History", body)
            self.assertIn("Scrape Settings", body)
            self.assertIn("Recommendations", body)
            self.assertIn("Pattern Library", body)
            self.assertIn("Nattome POV Library", body)
            self.assertIn("Pipeline Architecture", body)
            self.assertIn("Run scrape now", body)
            self.assertIn("Run full pipeline", body)
            self.assertTrue((workspace / DASHBOARD_DB_PATH).is_file())

    def test_overview_route_summarizes_strong_latest_run(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_fixture_workspace(
                workspace,
                run_id="20260507T010000Z_default",
                run_timestamp="2026-05-07T01:00:00Z",
                videos=[
                    self._video("strong-1", views=100000, likes=9000, comments=300, shares=400),
                    self._video("strong-2", views=85000, likes=6500, comments=250, shares=280),
                    self._video("strong-3", views=72000, likes=5200, comments=200, shares=240),
                    self._video("strong-4", views=65000, likes=4900, comments=180, shares=210),
                ],
                eligible_count=4,
                selected_ids=["strong-1", "strong-2", "strong-3"],
                config_version="v7",
                next_scheduled_run="2026-05-08T01:00:00Z",
                health_phases=[
                    {"name": "candidate_selection", "status": "completed"},
                    {"name": "evidence_bundles", "status": "completed"},
                    {"name": "gemini_evidence", "status": "completed"},
                    {"name": "structured_outputs", "status": "completed"},
                    {"name": "telegram_delivery", "status": "completed"},
                ],
                with_outputs=True,
            )

            response, body = self._get_overview(workspace)

            self.assertEqual(response.status, 200)
            self.assertIn("strong scrape", body)
            self.assertIn("Pipeline outputs are ready for marketer review.", body)
            self.assertIn("2026-05-07T01:00:00Z", body)
            self.assertIn("default", body)
            self.assertIn("v7", body)
            self.assertIn("2026-05-08T01:00:00Z", body)
            self.assertIn("Acid reflux bloating gut health hook", body)
            self.assertIn("https://www.tiktok.com/@creator/video/strong-1", body)
            self.assertIn("Top Quality Drivers", body)

    def test_overview_route_summarizes_needs_attention_latest_run(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_fixture_workspace(
                workspace,
                run_id="20260507T020000Z_default",
                run_timestamp="2026-05-07T02:00:00Z",
                videos=[
                    self._video(
                        "weak-1",
                        views=3000,
                        likes=20,
                        comments=0,
                        shares=0,
                        caption="Random lifestyle clip",
                        source_input="#random",
                        downloadable=False,
                    ),
                    self._video(
                        "weak-2",
                        views=2000,
                        likes=10,
                        comments=0,
                        shares=0,
                        caption="Another unrelated clip",
                        source_input="#random",
                        downloadable=False,
                    ),
                ],
                eligible_count=0,
                selected_ids=[],
                health_phases=[
                    {"name": "candidate_selection", "status": "blocked", "reason": "No usable raw candidates"},
                    {"name": "gemini_evidence", "status": "blocked"},
                ],
                with_outputs=False,
            )

            response, body = self._get_overview(workspace)

            self.assertEqual(response.status, 200)
            self.assertIn("needs attention", body)
            self.assertIn("Pipeline is blocked before marketer-ready outputs can be trusted.", body)
            self.assertIn("No usable raw candidates", body)
            self.assertIn("Random lifestyle clip", body)
            self.assertIn("Edit scrape settings", body)
            self.assertIn("Browse content library", body)

    def _get_overview(self, workspace: Path):
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
            return response, body
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

    def _write_fixture_workspace(
        self,
        workspace: Path,
        *,
        run_id: str,
        run_timestamp: str,
        videos: list[dict],
        eligible_count: int,
        selected_ids: list[str],
        health_phases: list[dict],
        with_outputs: bool,
        config_version: str | None = None,
        next_scheduled_run: str | None = None,
    ) -> None:
        raw_scrapes = workspace / "data" / "raw_scrapes"
        run_folder = workspace / "runs" / "batch-analysis" / run_id
        data_folder = run_folder / "data"
        evidence_folder = run_folder / "evidence"
        reports_folder = run_folder / "reports"
        logs_folder = run_folder / "logs"
        for folder in [raw_scrapes, data_folder, evidence_folder, reports_folder, logs_folder]:
            folder.mkdir(parents=True, exist_ok=True)

        candidate_source = "data/raw_scrapes/sample_raw.json"
        (raw_scrapes / "sample_raw.json").write_text(
            json.dumps({"generated_at": run_timestamp, "top": videos}),
            encoding="utf-8",
        )
        manifest = {
            "run_timestamp": run_timestamp,
            "mode": "default",
            "requested_batch_size": 3,
            "configuration": {
                "version": config_version,
                "next_scheduled_run": next_scheduled_run,
                "selection": {
                    "minimum_views": 10000,
                    "maximum_age_days": 14,
                    "minimum_weighted_engagement_rate": 0.02,
                    "requires_tiktok_link": True,
                    "requires_downloadable_video": True,
                },
            },
            "phases": health_phases,
            "outputs": {"batch_index": "batch_index.md"} if with_outputs else {},
        }
        (run_folder / "run_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (run_folder / "run_metadata.json").write_text(
            json.dumps({"run_timestamp": run_timestamp, "mode": "default"}),
            encoding="utf-8",
        )
        (data_folder / "selected_batch.json").write_text(
            json.dumps(
                {
                    "selected_at": run_timestamp,
                    "candidate_source": candidate_source,
                    "input_candidate_count": len(videos),
                    "eligible_candidate_count": eligible_count,
                    "selected_candidate_count": len(selected_ids),
                    "selected_candidates": [{"id": video_id} for video_id in selected_ids],
                }
            ),
            encoding="utf-8",
        )
        bundle_count = max(len(selected_ids), 1)
        (data_folder / "evidence_bundle_index.json").write_text(
            json.dumps(
                {
                    "bundle_count": bundle_count,
                    "bundles": [
                        {
                            "candidate_id": f"bundle-{index}",
                            "source_video": {"state": "available" if with_outputs else "missing"},
                            "artifacts": {
                                "gemini_evidence": {"state": "completed" if with_outputs else "missing"},
                                "video_evidence_report": {"state": "completed" if with_outputs else "missing"},
                            },
                        }
                        for index in range(1, bundle_count + 1)
                    ],
                }
            ),
            encoding="utf-8",
        )
        if with_outputs:
            (reports_folder / "001_video_evidence_report.md").write_text("# Report\n", encoding="utf-8")
            (data_folder / "spreadsheet_summary.csv").write_text("id\nstrong-1\n", encoding="utf-8")
            (run_folder / "batch_index.md").write_text("# Batch\n", encoding="utf-8")
            (logs_folder / "telegram_delivery.json").write_text(json.dumps({"status": "sent"}), encoding="utf-8")
        else:
            (logs_folder / "telegram_delivery.json").write_text(json.dumps({"status": "skipped"}), encoding="utf-8")

    def _video(
        self,
        video_id: str,
        *,
        views: int,
        likes: int,
        comments: int,
        shares: int,
        caption: str = "Acid reflux bloating gut health hook",
        source_input: str = "#guthealth",
        downloadable: bool = True,
    ) -> dict:
        return {
            "id": video_id,
            "url": f"https://www.tiktok.com/@creator/video/{video_id}",
            "author_handle": f"creator-{video_id}",
            "caption": caption,
            "hashtags": ["guthealth", "digestive"] if "gut" in source_input else ["random"],
            "source_input": source_input,
            "video_download_url": f"https://cdn.example.com/{video_id}.mp4" if downloadable else "",
            "play_count": views,
            "like_count": likes,
            "comment_count": comments,
            "share_count": shares,
            "created_at": "2026-05-06T00:00:00Z",
        }
