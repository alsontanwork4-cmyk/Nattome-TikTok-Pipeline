import json
import http.client
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.parse import urlencode

from dashboard.store import (
    DASHBOARD_DB_PATH,
    MUTABLE_TABLES,
    connect_dashboard_store,
    dump_json,
    initialize_dashboard_store,
    load_json,
)
from dashboard.web_actions import _save_video_curation
from dashboard.web import DashboardServer, NAV_ITEMS, create_handler, resolve_dashboard_workspace
from dashboard.web_layout import render_page
from dashboard.web_theme import render_theme_styles


class DashboardStoreTest(unittest.TestCase):
    def test_dashboard_connection_helper_initializes_store_with_row_access(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            connection = connect_dashboard_store(workspace)
            try:
                schema = connection.execute(
                    "SELECT value FROM dashboard_metadata WHERE key = 'schema_name'"
                ).fetchone()
                user_version = connection.execute("PRAGMA user_version").fetchone()
            finally:
                connection.close()

            self.assertTrue((workspace / DASHBOARD_DB_PATH).is_file())
            self.assertEqual(schema["value"], "nattome_scrape_quality_dashboard")
            self.assertEqual(user_version["user_version"], 1)

    def test_store_json_helpers_use_explicit_fallbacks_and_deterministic_dumps(self):
        fallback = {"fallback": True}

        self.assertEqual(load_json('{"b": 2, "a": 1}', fallback), {"a": 1, "b": 2})
        self.assertIs(load_json("", fallback), fallback)
        self.assertIs(load_json("{broken", fallback), fallback)
        self.assertEqual(dump_json({"b": 2, "a": "é"}), '{"a": "\\u00e9", "b": 2}')

    def test_video_curation_action_initializes_store_before_saving(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            _save_video_curation(
                workspace,
                {
                    "video_id": ["video-1"],
                    "labels": ["Relevant", "Great Hook"],
                    "exclude_similar_reason": [""],
                    "note": ["Preserve hook pattern"],
                },
            )
            connection = connect_dashboard_store(workspace)
            try:
                row = connection.execute(
                    """
                    SELECT labels, note
                    FROM video_curation
                    WHERE tiktok_video_id = 'video-1'
                    """
                ).fetchone()
            finally:
                connection.close()

            self.assertIsNotNone(row)
            self.assertEqual(load_json(row["labels"], []), ["Relevant", "Great Hook"])
            self.assertEqual(row["note"], "Preserve hook pattern")

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
    def test_launching_from_dashboard_folder_resolves_repo_workspace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            dashboard_folder = workspace / "dashboard"
            dashboard_folder.mkdir()
            (workspace / "runs" / "batch-analysis").mkdir(parents=True)

            resolved = resolve_dashboard_workspace(dashboard_folder)

            self.assertEqual(resolved, workspace.resolve())

    def test_handler_launched_from_dashboard_folder_uses_repo_workspace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            dashboard_folder = workspace / "dashboard"
            dashboard_folder.mkdir()
            (workspace / "runs" / "batch-analysis").mkdir(parents=True)

            response, body = self._request(dashboard_folder, "GET", "/")

            self.assertEqual(response.status, 200)
            self.assertIn("Latest Run Overview", body)
            self.assertTrue((workspace / DASHBOARD_DB_PATH).is_file())
            self.assertFalse((dashboard_folder / DASHBOARD_DB_PATH).exists())

    def test_all_navigation_routes_render_the_dashboard_shell(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            for label, route in NAV_ITEMS:
                with self.subTest(route=route):
                    response, body = self._request(workspace, "GET", route)

                    self.assertEqual(response.status, 200)
                    self.assertIn('<header class="topbar" role="banner">', body)
                    self.assertIn('<aside class="sidebar"', body)
                    self.assertIn("<main>", body)
                    self.assertIn(f'href="{route}" aria-current="page"', body)
                    self.assertIn(label, body)

    def test_rendered_page_uses_inline_theme_module_styles(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            body = render_page("/", Path(temp_dir))
            theme_styles = render_theme_styles().strip()

            self.assertIn("<style>", body)
            self.assertIn(theme_styles, body)
            self.assertIn(".layout {", theme_styles)
            self.assertIn('<header class="topbar" role="banner">', body)
            self.assertIn("Latest Run Overview", body)
            self.assertNotIn('href="/static/', body)

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

    def test_scraped_content_route_lists_raw_videos_with_status_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_scraped_content_workspace(workspace)

            response, body = self._request(workspace, "GET", "/scraped-content")

            self.assertEqual(response.status, 200)
            self.assertIn("Raw Scraped Videos", body)
            self.assertIn("Raw only clip", body)
            self.assertIn("Eligible clip", body)
            self.assertIn("Analyzed clip", body)
            self.assertIn("raw only", body)
            self.assertIn("eligible", body)
            self.assertIn("analyzed", body)
            self.assertIn("@creator-raw-1", body)
            self.assertIn("#guthealth", body)
            self.assertIn("15.0%", body)
            self.assertIn("https://www.tiktok.com/@creator/video/raw-1", body)
            self.assertNotIn("<video", body.lower())

    def test_scraped_content_route_persists_labels_notes_and_exclude_reason(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_scraped_content_workspace(workspace)
            form_body = (
                "video_id=raw-1&labels=Relevant&labels=Exclude+Similar"
                "&exclude_similar_reason=Wrong+market+pattern&note=Keep+for+hook+study"
            )

            post_response, _ = self._request(
                workspace,
                "POST",
                "/scraped-content/curation",
                body=form_body,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            get_response, body = self._request(workspace, "GET", "/scraped-content")

            self.assertEqual(post_response.status, 303)
            self.assertEqual(get_response.status, 200)
            self.assertIn("Relevant", body)
            self.assertIn("Exclude Similar", body)
            self.assertIn("Wrong market pattern", body)
            self.assertIn("Keep for hook study", body)

    def test_scrape_settings_route_saves_versions_and_rolls_back(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            initial_response, initial_body = self._request(workspace, "GET", "/scrape-settings")
            missing_reason_response, missing_reason_body = self._request(
                workspace,
                "POST",
                "/scrape-settings/save",
                body=urlencode(
                    {
                        "hashtags": "#guthealth",
                        "keywords": "bloating",
                        "competitor_profiles": "@gaviscon",
                    }
                ),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            first_save_response, _ = self._request(
                workspace,
                "POST",
                "/scrape-settings/save",
                body=urlencode(
                    {
                        "hashtags": "#guthealth\n#digestion",
                        "keywords": "bloating\nacid reflux",
                        "competitor_profiles": "@gaviscon",
                        "scope": "all",
                        "results_per_input": "25",
                        "top_n": "30",
                        "daily_selection_size": "5",
                        "minimum_views": "10000",
                        "maximum_age_days": "14",
                        "minimum_weighted_engagement_rate": "0.025",
                        "requires_downloadable_video": "on",
                        "exclusion_terms": "weight loss",
                        "reason": "Add focused gut health settings",
                        "user": "marketer@example.com",
                    }
                ),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            second_save_response, _ = self._request(
                workspace,
                "POST",
                "/scrape-settings/save",
                body=urlencode(
                    {
                        "hashtags": "#random",
                        "keywords": "bloating",
                        "competitor_profiles": "@gaviscon",
                        "scope": "all",
                        "results_per_input": "25",
                        "top_n": "30",
                        "daily_selection_size": "5",
                        "minimum_views": "10000",
                        "maximum_age_days": "14",
                        "minimum_weighted_engagement_rate": "0.025",
                        "reason": "Bad source experiment",
                        "user": "marketer@example.com",
                    }
                ),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            rollback_response, _ = self._request(
                workspace,
                "POST",
                "/scrape-settings/rollback",
                body=urlencode(
                    {
                        "target_version": "1",
                        "reason": "Restore gut health settings",
                        "user": "marketer@example.com",
                    }
                ),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            final_response, final_body = self._request(workspace, "GET", "/scrape-settings")

            self.assertEqual(initial_response.status, 200)
            self.assertIn("Production Scrape Settings", initial_body)
            self.assertIn("API keys", initial_body)
            self.assertIn("APIFY_TOKEN", initial_body)
            self.assertEqual(missing_reason_response.status, 400)
            self.assertIn("requires a reason", missing_reason_body)
            self.assertEqual(first_save_response.status, 303)
            self.assertEqual(second_save_response.status, 303)
            self.assertEqual(rollback_response.status, 303)
            self.assertEqual(final_response.status, 200)
            self.assertIn("Current production config version", final_body)
            self.assertIn("v3", final_body)
            self.assertIn("Next scheduled run will use version v3", final_body)
            self.assertIn("guthealth", final_body)
            self.assertIn("digestion", final_body)
            self.assertIn("Rollback of v1", final_body)
            self.assertIn("Restore gut health settings", final_body)
            self.assertNotIn(">#guthealth<", final_body)

    def _get_overview(self, workspace: Path):
        return self._request(workspace, "GET", "/")

    def _request(
        self,
        workspace: Path,
        method: str,
        path: str,
        *,
        body: str | None = None,
        headers: dict[str, str] | None = None,
    ):
        server = DashboardServer(
            ("127.0.0.1", 0),
            create_handler(workspace),
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

    def _write_scraped_content_workspace(self, workspace: Path) -> None:
        raw_scrapes = workspace / "data" / "raw_scrapes"
        run_folder = workspace / "runs" / "batch-analysis" / "20260507T030000Z_default"
        data_folder = run_folder / "data"
        raw_scrapes.mkdir(parents=True, exist_ok=True)
        data_folder.mkdir(parents=True, exist_ok=True)
        candidate_source = "data/raw_scrapes/sample_raw.json"
        videos = [
            {
                "id": "raw-1",
                "url": "https://www.tiktok.com/@creator/video/raw-1",
                "author_handle": "@creator-raw-1",
                "caption": "Raw only clip",
                "hashtags": ["guthealth", "routine"],
                "source_input": "#guthealth",
                "video_download_url": "https://cdn.example.com/raw-1.mp4",
                "play_count": 10000,
                "like_count": 1000,
                "comment_count": 50,
                "share_count": 25,
                "created_at": "2026-05-06T00:00:00Z",
            },
            {
                "id": "eligible-1",
                "url": "https://www.tiktok.com/@creator/video/eligible-1",
                "author_handle": "@creator-eligible-1",
                "caption": "Eligible clip",
                "hashtags": ["guthealth"],
                "source_input": "#guthealth",
                "video_download_url": "https://cdn.example.com/eligible-1.mp4",
                "play_count": 9000,
                "like_count": 900,
                "comment_count": 45,
                "share_count": 20,
                "created_at": "2026-05-06T00:00:00Z",
                "is_eligible": True,
            },
            {
                "id": "analyzed-1",
                "url": "https://www.tiktok.com/@creator/video/analyzed-1",
                "author_handle": "@creator-analyzed-1",
                "caption": "Analyzed clip",
                "hashtags": ["digestion"],
                "source_input": "#digestion",
                "video_download_url": "https://cdn.example.com/analyzed-1.mp4",
                "play_count": 8000,
                "like_count": 800,
                "comment_count": 40,
                "share_count": 16,
                "created_at": "2026-05-06T00:00:00Z",
            },
        ]
        (raw_scrapes / "sample_raw.json").write_text(
            json.dumps({"generated_at": "2026-05-07T00:00:00Z", "top": videos}),
            encoding="utf-8",
        )
        (run_folder / "run_manifest.json").write_text(
            json.dumps(
                {
                    "run_timestamp": "2026-05-07T00:00:00Z",
                    "mode": "default",
                    "requested_batch_size": 1,
                    "configuration": {"selection": {"maximum_age_days": 14}},
                }
            ),
            encoding="utf-8",
        )
        (data_folder / "selected_batch.json").write_text(
            json.dumps(
                {
                    "selected_at": "2026-05-07T00:00:00Z",
                    "candidate_source": candidate_source,
                    "input_candidate_count": 3,
                    "eligible_candidate_count": 2,
                    "selected_candidate_count": 1,
                    "selected_candidates": [{"id": "analyzed-1"}],
                }
            ),
            encoding="utf-8",
        )
        (data_folder / "001_analyzed-1_source_metadata.json").write_text(
            json.dumps({"id": "analyzed-1", "caption": "Analyzed clip"}),
            encoding="utf-8",
        )
