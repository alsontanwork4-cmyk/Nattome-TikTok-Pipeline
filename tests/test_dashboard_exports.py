import csv
import json
import tempfile
import unittest
from http.client import HTTPConnection
from io import StringIO
from pathlib import Path
from threading import Thread

from dashboard.exports import (
    export_nattome_povs_markdown,
    export_raw_videos_csv,
    export_run_summaries_csv,
)
from dashboard.indexer import index_pipeline_artifacts
from dashboard.nattome_pov_library import create_nattome_pov
from dashboard.store import DASHBOARD_DB_PATH, initialize_dashboard_store
from dashboard.web import DashboardServer, create_handler, render_page


class DashboardExportsTest(unittest.TestCase):
    def test_raw_video_csv_export_preserves_metadata_and_filters_results(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_fixture_workspace(workspace)
            initialize_dashboard_store(workspace)
            index_pipeline_artifacts(workspace)
            self._save_curation(workspace)

            exported = export_raw_videos_csv(
                workspace,
                filters={"selection_status": "analyzed", "label": "Relevant"},
            )
            rows = list(csv.DictReader(StringIO(exported)))

            self.assertEqual([row["video_id"] for row in rows], ["video-1"])
            self.assertEqual(rows[0]["tiktok_url"], "https://tiktok.test/video-1")
            self.assertEqual(rows[0]["source_input"], "#guthealth")
            self.assertEqual(rows[0]["run_id"], "20260507T000000Z_default")
            self.assertEqual(rows[0]["config_version"], "v4")
            self.assertEqual(rows[0]["selection_status"], "analyzed")
            self.assertEqual(rows[0]["curation_labels"], "Relevant; Good Nattome Fit")
            self.assertEqual(rows[0]["curation_note"], "Keep for Nattome hook planning.")
            self.assertEqual(rows[0]["source_artifact_path"], "data/raw_scrapes/sample_raw.json")

    def test_run_summaries_csv_export_preserves_context_and_linked_deliverables(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_fixture_workspace(workspace)
            initialize_dashboard_store(workspace)
            index_pipeline_artifacts(workspace)

            exported = export_run_summaries_csv(workspace)
            rows = list(csv.DictReader(StringIO(exported)))

            self.assertEqual([row["run_id"] for row in rows], ["20260507T000000Z_default"])
            self.assertEqual(rows[0]["timestamp"], "2026-05-07T00:00:00Z")
            self.assertEqual(rows[0]["run_type"], "scheduled default")
            self.assertEqual(rows[0]["config_version"], "v4")
            self.assertEqual(rows[0]["raw_candidates"], "2")
            self.assertEqual(rows[0]["selected_count"], "1")
            self.assertIn("reports/current.md", rows[0]["output_links"])
            self.assertIn("reports/current.xlsx", rows[0]["output_links"])
            self.assertIn("report_markdown", rows[0]["output_types"])
            self.assertIn("excel_workbook", rows[0]["output_types"])

    def test_markdown_exports_include_nattome_pov_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            initialize_dashboard_store(workspace)
            create_nattome_pov(
                workspace,
                {
                    "title": "Morning gut reset",
                    "description": "Owned Nattome angle for breakfast routines.",
                    "brand_safe_interpretation": "Support daily digestive comfort.",
                    "adaptation_rules": "Pair with normal breakfast prep.",
                    "product": "Nattome",
                    "campaign": "Always-on gut comfort",
                    "market": "Malaysia",
                    "language": "mixed/English",
                    "audience_avatar": "office workers",
                    "source_links": ["https://docs.test/source"],
                },
                user="strategist@example.com",
                status="approved",
            )

            pov_markdown = export_nattome_povs_markdown(workspace)

            self.assertIn("# Nattome POV Export", pov_markdown)
            self.assertIn("## Morning gut reset", pov_markdown)
            self.assertIn("Campaign: Always-on gut comfort", pov_markdown)
            self.assertIn("Support daily digestive comfort.", pov_markdown)
            self.assertIn("https://docs.test/source", pov_markdown)
            self.assertNotIn("Linked approved pattern IDs", pov_markdown)

    def test_empty_exports_keep_headers_and_markdown_empty_states(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            initialize_dashboard_store(workspace)

            raw_rows = list(csv.DictReader(StringIO(export_raw_videos_csv(workspace))))
            run_rows = list(csv.DictReader(StringIO(export_run_summaries_csv(workspace))))

            self.assertEqual(raw_rows, [])
            self.assertIn("video_id,tiktok_url,author_handle", export_raw_videos_csv(workspace))
            self.assertEqual(run_rows, [])
            self.assertIn("run_id,timestamp,run_type", export_run_summaries_csv(workspace))
            self.assertIn("No Nattome POVs are available", export_nattome_povs_markdown(workspace))

    def test_dashboard_export_routes_return_downloadable_artifacts_and_pages_link_them(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_fixture_workspace(workspace)
            initialize_dashboard_store(workspace)
            index_pipeline_artifacts(workspace)
            self._save_curation(workspace)

            run_page = render_page("/run-history", workspace)

            csv_status, csv_headers, csv_body = self._get(workspace, "/exports/raw-videos.csv?selection_status=analyzed")
            run_status, run_headers, run_body = self._get(workspace, "/exports/run-summaries.csv")
            pov_status, pov_headers, pov_body = self._get(workspace, "/exports/nattome-povs.md")

            self.assertIn("/exports/raw-videos.csv", run_page)
            self.assertIn("/exports/run-summaries.csv", run_page)
            self.assertEqual(csv_status, 200)
            self.assertEqual(csv_headers["Content-Type"], "text/csv; charset=utf-8")
            self.assertEqual(
                csv_headers["Content-Disposition"],
                'attachment; filename="nattome-raw-videos.csv"',
            )
            self.assertIn("video-1", csv_body)
            self.assertNotIn("video-2", csv_body)
            self.assertEqual(run_status, 200)
            self.assertEqual(
                run_headers["Content-Disposition"],
                'attachment; filename="nattome-run-summaries.csv"',
            )
            self.assertIn("20260507T000000Z_default", run_body)
            self.assertEqual(pov_status, 200)
            self.assertEqual(pov_headers["Content-Type"], "text/markdown; charset=utf-8")
            self.assertEqual(
                pov_headers["Content-Disposition"],
                'attachment; filename="nattome-povs.md"',
            )
            self.assertIn("No Nattome POVs are available", pov_body)

    def _write_fixture_workspace(self, workspace: Path) -> None:
        raw_scrapes = workspace / "data" / "raw_scrapes"
        run_folder = workspace / "runs" / "batch-analysis" / "20260507T000000Z_default"
        for folder in [raw_scrapes, run_folder / "data", run_folder / "reports"]:
            folder.mkdir(parents=True, exist_ok=True)

        (raw_scrapes / "sample_raw.json").write_text(
            json.dumps(
                {
                    "generated_at": "2026-05-07T00:01:00Z",
                    "top": [
                        {
                            "id": "video-1",
                            "url": "https://tiktok.test/video-1",
                            "author_handle": "@creator1",
                            "caption": "Gut health hook with bloating routine",
                            "hashtags": ["guthealth", "bloating"],
                            "source_input": "#guthealth",
                            "video_download_url": "https://download.test/video-1.mp4",
                            "play_count": 12000,
                            "like_count": 900,
                            "comment_count": 20,
                            "share_count": 80,
                            "created_at": "2026-05-07T00:00:00Z",
                        },
                        {
                            "id": "video-2",
                            "url": "https://tiktok.test/video-2",
                            "author_handle": "@creator2",
                            "caption": "Generic wellness clip",
                            "hashtags": ["wellness"],
                            "source_input": "#wellness",
                            "play_count": 8000,
                            "like_count": 100,
                            "comment_count": 2,
                            "share_count": 1,
                            "created_at": "2026-05-06T00:00:00Z",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        (run_folder / "run_manifest.json").write_text(
            json.dumps(
                {
                    "run_timestamp": "2026-05-07T00:00:00Z",
                    "mode": "default",
                    "requested_batch_size": 1,
                    "configuration": {"version": "v4"},
                    "outputs": {
                        "report_markdown": "reports/current.md",
                        "excel_workbook": "reports/current.xlsx",
                    },
                }
            ),
            encoding="utf-8",
        )
        (run_folder / "data" / "selected_batch.json").write_text(
            json.dumps(
                {
                    "selected_at": "2026-05-07T00:02:00Z",
                    "candidate_source": "data/raw_scrapes/sample_raw.json",
                    "selected_candidate_count": 1,
                    "selected_candidates": [{"id": "video-1"}],
                    "config_version": "v4",
                }
            ),
            encoding="utf-8",
        )
        (run_folder / "reports" / "current.md").write_text("# Report\n", encoding="utf-8")
        (run_folder / "reports" / "current.xlsx").write_bytes(b"xlsx")
        (run_folder / "data" / "001_video-1_source_metadata.json").write_text(
            json.dumps({"id": "video-1"}),
            encoding="utf-8",
        )

    def _save_curation(self, workspace: Path) -> None:
        import sqlite3

        connection = sqlite3.connect(workspace / DASHBOARD_DB_PATH)
        try:
            connection.execute(
                """
                INSERT INTO video_curation (
                    tiktok_video_id,
                    labels,
                    note,
                    created_by,
                    updated_by
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "video-1",
                    json.dumps(["Relevant", "Good Nattome Fit"]),
                    "Keep for Nattome hook planning.",
                    "tester",
                    "tester",
                ),
            )
            connection.commit()
        finally:
            connection.close()

    def _get(self, workspace: Path, path: str) -> tuple[int, dict[str, str], str]:
        server = DashboardServer(("127.0.0.1", 0), create_handler(workspace))
        thread = Thread(target=server.serve_forever)
        thread.start()
        try:
            host, port = server.server_address
            connection = HTTPConnection(host, port, timeout=5)
            connection.request("GET", path)
            response = connection.getresponse()
            body = response.read().decode("utf-8")
            return response.status, {key: value for key, value in response.getheaders()}, body
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()


if __name__ == "__main__":
    unittest.main()
