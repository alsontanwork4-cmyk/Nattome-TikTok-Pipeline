import json
import http.client
import sqlite3
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

from dashboard.recommendations import (
    generate_recommendations,
    list_recommendations,
    update_recommendation_status,
)
from dashboard.settings import save_settings_version
from dashboard.store import DASHBOARD_DB_PATH, initialize_dashboard_store
from dashboard.web import DashboardServer, create_handler


class DashboardRecommendationsTest(unittest.TestCase):
    def test_generates_passive_recommendations_from_low_quality_drivers_and_curation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_weak_run_workspace(workspace, config_version="v1")
            save_settings_version(
                workspace,
                {"hashtags": "#random", "keywords": "wellness", "competitor_profiles": "@generic"},
                reason="Baseline weak source mix",
                user="marketer@example.com",
            )
            self._save_curation(
                workspace,
                video_id="weak-1",
                labels=["Irrelevant", "Exclude Similar"],
                note="Wrong market and repetitive hook.",
                exclude_reason="Generic wellness pattern",
            )

            recommendations = generate_recommendations(workspace)

            recommendation_types = {item.recommendation_type for item in recommendations}
            self.assertIn("low_eligibility_yield", recommendation_types)
            self.assertIn("low_relevance", recommendation_types)
            self.assertIn("stale_videos", recommendation_types)
            self.assertIn("duplicate_noise", recommendation_types)
            self.assertTrue(all(item.status == "needs_more_data" for item in recommendations))

            relevance = next(
                item for item in recommendations if item.recommendation_type == "low_relevance"
            )
            evidence_types = {evidence["entity_type"] for evidence in relevance.supporting_evidence}
            self.assertIn("run", evidence_types)
            self.assertIn("video", evidence_types)
            self.assertIn("source_input", evidence_types)
            self.assertIn("label", evidence_types)
            self.assertIn("config_version", evidence_types)
            self.assertIn("Wrong market and repetitive hook.", json.dumps(relevance.supporting_evidence))

    def test_lifecycle_state_changes_do_not_mutate_settings_or_scores(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_weak_run_workspace(workspace, config_version="v1")
            save_settings_version(
                workspace,
                {"hashtags": "#random", "keywords": "wellness", "competitor_profiles": "@generic"},
                reason="Baseline weak source mix",
            )
            recommendation = generate_recommendations(workspace)[0]
            before = self._settings_and_score_snapshot(workspace)

            updated = update_recommendation_status(
                workspace,
                recommendation.id,
                "accepted",
                user="marketer@example.com",
            )
            after = self._settings_and_score_snapshot(workspace)

            self.assertEqual(updated.status, "accepted")
            self.assertEqual(before, after)

    def test_invalid_lifecycle_state_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_weak_run_workspace(workspace, config_version="v1")
            recommendation = generate_recommendations(workspace)[0]

            with self.assertRaises(ValueError):
                update_recommendation_status(workspace, recommendation.id, "open")

    def test_active_config_change_resolves_stale_recommendations(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_weak_run_workspace(workspace, config_version="v1")
            save_settings_version(
                workspace,
                {"hashtags": "#random", "keywords": "wellness", "competitor_profiles": "@generic"},
                reason="Baseline weak source mix",
            )
            first = generate_recommendations(workspace)
            self.assertTrue(first)

            save_settings_version(
                workspace,
                {"hashtags": "#guthealth", "keywords": "bloating", "competitor_profiles": "@gaviscon"},
                reason="Replace weak source mix",
            )
            generate_recommendations(workspace)

            recommendations = list_recommendations(workspace)
            self.assertTrue(recommendations)
            self.assertTrue(all(item.status == "resolved" for item in recommendations))
            self.assertTrue(all(item.resolved_at for item in recommendations))

    def test_recommendations_route_renders_evidence_and_updates_lifecycle_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_weak_run_workspace(workspace, config_version="v1")
            save_settings_version(
                workspace,
                {"hashtags": "#random", "keywords": "wellness", "competitor_profiles": "@generic"},
                reason="Baseline weak source mix",
            )

            response, body = self._request(workspace, "GET", "/recommendations")

            self.assertEqual(response.status, 200)
            self.assertIn("Passive Recommendations", body)
            self.assertIn("needs more data", body)
            self.assertIn("low eligibility yield", body.lower())
            self.assertIn("20260507T020000Z_default", body)
            self.assertIn("weak-1", body)
            self.assertIn("#random", body)

            recommendation = list_recommendations(workspace)[0]
            post_response, _ = self._request(
                workspace,
                "POST",
                "/recommendations/status",
                body=urlencode(
                    {
                        "recommendation_id": str(recommendation.id),
                        "status": "ignored",
                        "user": "marketer@example.com",
                    }
                ),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            final_response, final_body = self._request(workspace, "GET", "/recommendations")

            self.assertEqual(post_response.status, 303)
            self.assertEqual(final_response.status, 200)
            self.assertIn("ignored", final_body)

    def _settings_and_score_snapshot(self, workspace: Path):
        connection = sqlite3.connect(workspace / DASHBOARD_DB_PATH)
        connection.row_factory = sqlite3.Row
        try:
            settings = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT version, settings_json, reason, is_active
                    FROM scrape_settings_versions
                    ORDER BY version
                    """
                )
            ]
            scores = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT run_id, score, band, needs_attention, drivers_json
                    FROM scrape_quality_scores
                    ORDER BY run_id
                    """
                )
            ]
            return settings, scores
        finally:
            connection.close()

    def _save_curation(
        self,
        workspace: Path,
        *,
        video_id: str,
        labels: list[str],
        note: str,
        exclude_reason: str,
    ) -> None:
        db_path = initialize_dashboard_store(workspace)
        connection = sqlite3.connect(db_path)
        try:
            connection.execute(
                """
                INSERT INTO video_curation (
                    tiktok_video_id,
                    labels,
                    exclude_similar_reason,
                    note
                )
                VALUES (?, ?, ?, ?)
                """,
                (video_id, json.dumps(labels), exclude_reason, note),
            )
            connection.commit()
        finally:
            connection.close()

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

    def _write_weak_run_workspace(self, workspace: Path, *, config_version: str) -> None:
        run_id = "20260507T020000Z_default"
        run_timestamp = "2026-05-07T02:00:00Z"
        raw_scrapes = workspace / "data" / "raw_scrapes"
        run_folder = workspace / "runs" / "batch-analysis" / run_id
        (run_folder / "data").mkdir(parents=True, exist_ok=True)
        raw_scrapes.mkdir(parents=True, exist_ok=True)

        videos = [
            self._video("weak-1", days_old=24, source_input="#random", author="same-creator"),
            self._video("weak-2", days_old=21, source_input="#random", author="same-creator"),
            self._video("weak-3", days_old=18, source_input="#genericwellness", author="same-creator"),
            self._video("weak-4", days_old=17, source_input="#genericwellness", author="same-creator"),
        ]
        candidate_source = "data/raw_scrapes/weak_raw.json"
        (raw_scrapes / "weak_raw.json").write_text(
            json.dumps({"generated_at": run_timestamp, "top": videos}),
            encoding="utf-8",
        )
        (run_folder / "run_manifest.json").write_text(
            json.dumps(
                {
                    "run_timestamp": run_timestamp,
                    "mode": "default",
                    "requested_batch_size": 12,
                    "configuration": {
                        "version": config_version,
                        "selection": {
                            "minimum_views": 10000,
                            "maximum_age_days": 14,
                            "minimum_weighted_engagement_rate": 0.03,
                            "requires_downloadable_video": True,
                        },
                    },
                }
            ),
            encoding="utf-8",
        )
        (run_folder / "run_metadata.json").write_text(
            json.dumps({"run_timestamp": run_timestamp, "mode": "default"}),
            encoding="utf-8",
        )
        (run_folder / "data" / "selected_batch.json").write_text(
            json.dumps(
                {
                    "selected_at": run_timestamp,
                    "candidate_source": candidate_source,
                    "input_candidate_count": len(videos),
                    "eligible_candidate_count": 0,
                    "selected_candidate_count": 0,
                    "selected_candidates": [],
                    "config_version": config_version,
                }
            ),
            encoding="utf-8",
        )

    def _video(
        self,
        video_id: str,
        *,
        days_old: int,
        source_input: str,
        author: str,
    ) -> dict:
        created_at = datetime(2026, 5, 7, 2, tzinfo=timezone.utc) - timedelta(days=days_old)
        return {
            "id": video_id,
            "url": f"https://www.tiktok.com/@creator/video/{video_id}",
            "author_handle": author,
            "caption": "Generic wellness clip with no Nattome fit",
            "hashtags": ["wellness"],
            "source_input": source_input,
            "video_download_url": "",
            "play_count": 3000,
            "like_count": 20,
            "comment_count": 0,
            "share_count": 0,
            "created_at": created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }


if __name__ == "__main__":
    unittest.main()
