import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from dashboard.refresh import refresh_dashboard_derivatives
from dashboard.store import DASHBOARD_DB_PATH
from dashboard.web import render_page


class DashboardRefreshTest(unittest.TestCase):
    def test_refresh_derivatives_indexes_artifacts_quality_and_health(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_fixture_workspace(workspace)

            result = refresh_dashboard_derivatives(workspace, intent="overview", scope="all")

            self.assertEqual(result.intent, "overview")
            self.assertEqual(result.scope, "all")
            self.assertEqual(result.artifact_summary.batch_runs, 1)
            self.assertEqual([score.run_id for score in result.quality_scores], ["20260507T010000Z_daily"])
            self.assertEqual([summary.run_id for summary in result.health_summaries], ["20260507T010000Z_daily"])
            self.assertEqual(self._count(workspace, "scrape_quality_scores"), 1)
            self.assertEqual(self._count(workspace, "pipeline_health_summaries"), 1)

    def test_overview_page_refreshes_derived_dashboard_data_without_manual_step(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_fixture_workspace(workspace)

            body = render_page("/", workspace)

            self.assertIn("Latest Run Overview", body)
            self.assertIn("20260507T010000Z_daily", body)
            self.assertEqual(self._count(workspace, "batch_runs"), 1)
            self.assertEqual(self._count(workspace, "scrape_quality_scores"), 1)
            self.assertEqual(self._count(workspace, "pipeline_health_summaries"), 1)

    def _write_fixture_workspace(self, workspace: Path) -> None:
        raw_scrapes = workspace / "data" / "raw_scrapes"
        run_folder = workspace / "runs" / "batch-analysis" / "20260507T010000Z_daily"
        raw_scrapes.mkdir(parents=True, exist_ok=True)
        (run_folder / "data").mkdir(parents=True, exist_ok=True)
        (run_folder / "logs").mkdir(parents=True, exist_ok=True)

        (raw_scrapes / "sample_raw.json").write_text(
            json.dumps(
                {
                    "generated_at": "2026-05-07T01:00:00Z",
                    "top": [
                        {
                            "id": "video-1",
                            "url": "https://www.tiktok.com/@creator/video/video-1",
                            "author_handle": "@creator",
                            "caption": "Acid reflux bloating gut health routine",
                            "hashtags": ["guthealth", "bloating"],
                            "source_input": "#guthealth",
                            "video_download_url": "https://cdn.test/video-1.mp4",
                            "play_count": 100000,
                            "like_count": 9000,
                            "comment_count": 200,
                            "share_count": 300,
                            "created_at": "2026-05-06T00:00:00Z",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        (run_folder / "run_manifest.json").write_text(
            json.dumps(
                {
                    "run_timestamp": "2026-05-07T01:00:00Z",
                    "mode": "daily",
                    "requested_batch_size": 1,
                    "configuration": {"version": "v1", "selection": {"maximum_age_days": 14}},
                    "phases": [{"name": "candidate_selection", "status": "completed"}],
                }
            ),
            encoding="utf-8",
        )
        (run_folder / "data" / "selected_batch.json").write_text(
            json.dumps(
                {
                    "selected_at": "2026-05-07T01:00:00Z",
                    "candidate_source": "data/raw_scrapes/sample_raw.json",
                    "input_candidate_count": 1,
                    "eligible_candidate_count": 1,
                    "selected_candidate_count": 1,
                    "selected_candidates": [{"id": "video-1"}],
                    "config_version": "v1",
                }
            ),
            encoding="utf-8",
        )
        (run_folder / "logs" / "telegram_delivery.json").write_text(
            json.dumps({"status": "sent"}),
            encoding="utf-8",
        )

    def _count(self, workspace: Path, table_name: str) -> int:
        connection = sqlite3.connect(workspace / DASHBOARD_DB_PATH)
        try:
            return int(connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
