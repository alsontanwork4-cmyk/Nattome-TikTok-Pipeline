import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlencode

from dashboard.indexer import index_pipeline_artifacts
from dashboard.nattome_pov_library import create_nattome_pov
from dashboard.pattern_library import (
    approve_candidate_pattern,
    create_approved_pattern,
    generate_candidate_patterns,
)
from dashboard.search import search_dashboard_records
from dashboard.store import initialize_dashboard_store
from dashboard.web import render_page


class DashboardGlobalSearchTest(unittest.TestCase):
    def test_keyword_search_returns_typed_results_across_dashboard_records(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_fixture_workspace(workspace)
            self._seed_mutable_records(workspace)

            results = search_dashboard_records(workspace, query="post-lunch bloating")
            result_types = {result.record_type for result in results.results}

            self.assertIn("raw_video", result_types)
            self.assertIn("run", result_types)
            self.assertIn("curation", result_types)
            self.assertIn("candidate_pattern", result_types)
            self.assertIn("approved_pattern", result_types)
            self.assertIn("nattome_pov", result_types)
            self.assertIn("report", result_types)
            self.assertIn("architecture_doc", result_types)
            self.assertTrue(any("post-lunch" in result.context.lower() for result in results.results))
            self.assertTrue(any(result.url for result in results.results))

    def test_facets_filter_results_and_can_combine_with_keyword_search(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_fixture_workspace(workspace)
            self._seed_mutable_records(workspace)

            filtered = search_dashboard_records(
                workspace,
                query="bloating",
                facets={
                    "record_type": ["raw_video"],
                    "run_date": ["2026-05-07"],
                    "run_type": ["daily"],
                    "config_version": ["v9"],
                    "source_input": ["#guthealth"],
                    "video_status": ["analyzed"],
                    "label": ["Relevant"],
                    "score_band": ["strong scrape"],
                    "relevance_band": ["high relevance"],
                    "engagement_band": ["high engagement"],
                    "freshness": ["fresh"],
                    "author": ["@creator-analyzed"],
                    "hashtag_topic": ["guthealth"],
                },
            )

            self.assertEqual([result.record_id for result in filtered.results], ["analyzed-1"])
            self.assertIn("run_date", filtered.facets)
            self.assertIn("2026-05-07", filtered.facets["run_date"])
            self.assertIn("record_type", filtered.facets)
            self.assertIn("raw_video", filtered.facets["record_type"])

    def test_pattern_pov_market_campaign_product_and_phase_facets(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_fixture_workspace(workspace)
            self._seed_mutable_records(workspace)

            pov_results = search_dashboard_records(
                workspace,
                facets={
                    "pov": ["Post-lunch office comfort"],
                    "market": ["Malaysia"],
                    "campaign": ["Always-on gut comfort"],
                    "product": ["Nattome"],
                },
            )
            pattern_results = search_dashboard_records(
                workspace,
                query="routine demo",
                facets={"pattern": ["Bloating routine proof"]},
            )
            phase_results = search_dashboard_records(
                workspace,
                facets={"pipeline_phase_status": ["completed"]},
            )

            self.assertEqual([result.record_type for result in pov_results.results], ["nattome_pov"])
            self.assertEqual([result.record_type for result in pattern_results.results], ["approved_pattern"])
            self.assertIn("pipeline_phase", {result.record_type for result in phase_results.results})
            self.assertIn("pipeline_phase_status", phase_results.facets)

    def test_empty_search_results_are_graceful_in_service_and_route(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_fixture_workspace(workspace)
            self._seed_mutable_records(workspace)

            results = search_dashboard_records(workspace, query="no matching marketer record")
            body = render_page(
                "/search",
                workspace,
                query_params={"q": "no matching marketer record"},
            )

            self.assertEqual(results.results, [])
            self.assertIn("No matching dashboard records found.", body)
            self.assertIn("Global Search", body)

    def _seed_mutable_records(self, workspace: Path) -> None:
        initialize_dashboard_store(workspace)
        index_pipeline_artifacts(workspace)
        candidates = generate_candidate_patterns(workspace, user="system")
        approved_from_candidate = approve_candidate_pattern(
            workspace,
            candidates[0].id,
            user="marketer@example.com",
            notes="Post-lunch bloating routine demo proof.",
        )
        create_approved_pattern(
            workspace,
            {
                "pattern_name": "Bloating routine proof",
                "hook_type": "problem_solution",
                "format_type": "routine_demo",
                "emotional_trigger": "relief",
                "why_it_works": "Routine demo uses post-lunch bloating tension.",
                "freshness": "emerging",
                "targeting": {"market": "Malaysia", "persona": "office workers"},
                "related_povs": ["Post-lunch office comfort"],
            },
            user="strategy@example.com",
            status="approved",
        )
        create_nattome_pov(
            workspace,
            {
                "title": "Post-lunch office comfort",
                "description": "Owned Nattome POV for post-lunch bloating.",
                "brand_safe_interpretation": "Support daily digestive comfort without treatment claims.",
                "adaptation_rules": "Adapt the routine demo for office desks.",
                "product": "Nattome",
                "campaign": "Always-on gut comfort",
                "market": "Malaysia",
                "linked_pattern_ids": [approved_from_candidate.id],
            },
            user="strategy@example.com",
            status="approved",
        )

    def _write_fixture_workspace(self, workspace: Path) -> None:
        raw_scrapes = workspace / "data" / "raw_scrapes"
        run_folder = workspace / "runs" / "batch-analysis" / "20260507T010000Z_daily"
        report_folder = workspace / "outputs" / "reports" / "2026-05-07"
        docs_prd = workspace / "docs" / "prd"
        docs_adr = workspace / "docs" / "adr"
        for folder in [raw_scrapes, run_folder / "data", run_folder / "reports", report_folder, docs_prd, docs_adr]:
            folder.mkdir(parents=True, exist_ok=True)

        (workspace / "README.md").write_text("# Post-lunch Bloating Pipeline\n", encoding="utf-8")
        (workspace / "CONTEXT.md").write_text("# Dashboard Context\n\nPost-lunch bloating search terms.\n", encoding="utf-8")
        (docs_prd / "dashboard-search.md").write_text("# Dashboard Search PRD\n", encoding="utf-8")
        (docs_adr / "0001-dashboard.md").write_text("# Dashboard ADR\n", encoding="utf-8")
        (raw_scrapes / "sample_raw.json").write_text(
            json.dumps(
                {
                    "generated_at": "2026-05-07T01:00:00Z",
                    "top": [
                        {
                            "id": "analyzed-1",
                            "url": "https://tiktok.test/analyzed-1",
                            "author_handle": "@creator-analyzed",
                            "caption": "Post-lunch bloating routine demo for office workers",
                            "hashtags": ["guthealth", "bloating"],
                            "source_input": "#guthealth",
                            "video_download_url": "https://cdn.test/analyzed-1.mp4",
                            "play_count": 120000,
                            "like_count": 12000,
                            "comment_count": 300,
                            "share_count": 500,
                            "created_at": "2026-05-06T00:00:00Z",
                        },
                        {
                            "id": "raw-1",
                            "url": "https://tiktok.test/raw-1",
                            "author_handle": "@creator-raw",
                            "caption": "Generic wellness trend",
                            "hashtags": ["wellness"],
                            "source_input": "#wellness",
                            "video_download_url": "",
                            "play_count": 2000,
                            "like_count": 20,
                            "comment_count": 0,
                            "share_count": 0,
                            "created_at": "2026-04-01T00:00:00Z",
                        },
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
                    "configuration": {"version": "v9", "selection": {"maximum_age_days": 14}},
                    "phases": [{"name": "gemini_evidence", "status": "completed"}],
                    "outputs": {"report_markdown": "reports/current.md"},
                }
            ),
            encoding="utf-8",
        )
        (run_folder / "run_metadata.json").write_text(
            json.dumps({"run_timestamp": "2026-05-07T01:00:00Z", "mode": "daily"}),
            encoding="utf-8",
        )
        (run_folder / "data" / "selected_batch.json").write_text(
            json.dumps(
                {
                    "selected_at": "2026-05-07T01:00:00Z",
                    "candidate_source": "data/raw_scrapes/sample_raw.json",
                    "input_candidate_count": 2,
                    "eligible_candidate_count": 1,
                    "selected_candidate_count": 1,
                    "selected_candidates": [{"id": "analyzed-1"}],
                    "config_version": "v9",
                }
            ),
            encoding="utf-8",
        )
        (run_folder / "data" / "001_analyzed-1_source_metadata.json").write_text(
            json.dumps({"id": "analyzed-1", "caption": "Post-lunch bloating source metadata"}),
            encoding="utf-8",
        )
        (run_folder / "reports" / "current.md").write_text("# Post-lunch Bloating Report\n", encoding="utf-8")
        (report_folder / "top5_report.md").write_text("# Post-lunch Bloating Report\n", encoding="utf-8")
        initialize_dashboard_store(workspace)
        self._save_curation(workspace)

    def _save_curation(self, workspace: Path) -> None:
        from dashboard.web import DashboardServer, create_handler
        import http.client
        import threading

        server = DashboardServer(("127.0.0.1", 0), create_handler(workspace))
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            host, port = server.server_address
            connection = http.client.HTTPConnection(host, port, timeout=5)
            connection.request(
                "POST",
                "/scraped-content/curation",
                body=urlencode(
                    {
                        "video_id": "analyzed-1",
                        "labels": ["Relevant", "Good Nattome Fit"],
                        "note": "Post-lunch bloating office routine worth saving.",
                    },
                    doseq=True,
                ),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response = connection.getresponse()
            response.read()
            self.assertEqual(response.status, 303)
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()


if __name__ == "__main__":
    unittest.main()
