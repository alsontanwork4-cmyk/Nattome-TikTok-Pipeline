import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dashboard.indexer import index_pipeline_artifacts
from dashboard.quality import ScrapeQualityScore, compute_scrape_quality_scores
from dashboard.store import DASHBOARD_DB_PATH, initialize_dashboard_store


class ScrapeQualityScoreTest(unittest.TestCase):
    def test_strong_run_scores_on_scrape_only_components(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_fixture_workspace(
                workspace,
                run_id="20260507T000000Z_default",
                run_timestamp="2026-05-07T00:00:00Z",
                videos=[
                    self._video("video-1", days_old=1, views=100000, likes=9000, comments=300, shares=400),
                    self._video("video-2", days_old=2, views=85000, likes=6000, comments=220, shares=260),
                    self._video("video-3", days_old=3, views=70000, likes=5000, comments=180, shares=210),
                    self._video("video-4", days_old=1, views=50000, likes=4500, comments=120, shares=160),
                ],
                eligible_count=4,
                selected_ids=["video-1", "video-2", "video-3"],
                manifest_extra={
                    "phases": [
                        {"name": "source_video_snapshots", "status": "failed"},
                    ],
                    "outputs": {},
                },
            )
            initialize_dashboard_store(workspace)
            index_pipeline_artifacts(workspace)

            scores = compute_scrape_quality_scores(workspace)

            self.assertEqual(len(scores), 1)
            score = scores[0]
            self.assertEqual(score.run_id, "20260507T000000Z_default")
            self.assertGreaterEqual(score.score, 80)
            self.assertEqual(score.band, "strong scrape")
            self.assertFalse(score.needs_attention)
            self.assertEqual(
                set(score.components),
                {
                    "candidate_volume",
                    "eligibility_yield",
                    "nattome_relevance",
                    "freshness",
                    "engagement_strength",
                    "duplicate_noise_control",
                },
            )
            self.assertTrue(any(driver["direction"] == "helped" for driver in score.drivers))

            connection = sqlite3.connect(workspace / DASHBOARD_DB_PATH)
            connection.row_factory = sqlite3.Row
            try:
                persisted = connection.execute(
                    "SELECT * FROM scrape_quality_scores WHERE run_id = ?",
                    ("20260507T000000Z_default",),
                ).fetchone()
            finally:
                connection.close()

            self.assertIsNotNone(persisted)
            self.assertEqual(persisted["band"], "strong scrape")
            self.assertEqual(persisted["needs_attention"], 0)

    def test_usable_run_scores_between_sixty_and_seventy_nine(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_fixture_workspace(
                workspace,
                run_id="20260507T010000Z_default",
                run_timestamp="2026-05-07T01:00:00Z",
                videos=[
                    self._video(
                        "usable-1",
                        days_old=4,
                        views=40000,
                        likes=1200,
                        comments=50,
                        shares=60,
                        caption="Gut health habit",
                    ),
                    self._video(
                        "usable-2",
                        days_old=5,
                        views=35000,
                        likes=900,
                        comments=30,
                        shares=40,
                        caption="Digestive routine",
                    ),
                    self._video(
                        "usable-3",
                        days_old=8,
                        views=9000,
                        likes=120,
                        comments=3,
                        shares=5,
                        caption="Generic wellness vlog",
                    ),
                ],
                eligible_count=2,
                selected_ids=["usable-1", "usable-2"],
            )
            initialize_dashboard_store(workspace)
            index_pipeline_artifacts(workspace)

            score = compute_scrape_quality_scores(workspace)[0]

            self.assertGreaterEqual(score.score, 60)
            self.assertLess(score.score, 80)
            self.assertEqual(score.band, "usable scrape")
            self.assertFalse(score.needs_attention)

    def test_needs_attention_run_does_not_mutate_scrape_settings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_fixture_workspace(
                workspace,
                run_id="20260507T020000Z_default",
                run_timestamp="2026-05-07T02:00:00Z",
                videos=[
                    self._video(
                        "weak-1",
                        days_old=20,
                        views=3000,
                        likes=20,
                        comments=0,
                        shares=0,
                        caption="Random lifestyle clip",
                        author="same-creator",
                        downloadable=False,
                    ),
                    self._video(
                        "weak-2",
                        days_old=18,
                        views=2000,
                        likes=10,
                        comments=0,
                        shares=0,
                        caption="Another unrelated clip",
                        author="same-creator",
                        downloadable=False,
                    ),
                ],
                eligible_count=0,
                selected_ids=[],
            )
            db_path = initialize_dashboard_store(workspace)
            connection = sqlite3.connect(db_path)
            try:
                connection.execute(
                    """
                    INSERT INTO scrape_settings_versions (
                        version,
                        settings_json,
                        reason,
                        is_active,
                        created_by,
                        updated_by
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        1,
                        json.dumps({"selection": {"minimum_views": 10000}}, sort_keys=True),
                        "baseline",
                        1,
                        "tester",
                        "tester",
                    ),
                )
                connection.commit()
            finally:
                connection.close()
            index_pipeline_artifacts(workspace)

            score = compute_scrape_quality_scores(workspace)[0]

            self.assertLess(score.score, 60)
            self.assertEqual(score.band, "needs attention")
            self.assertTrue(score.needs_attention)
            self.assertTrue(any(driver["direction"] == "hurt" for driver in score.drivers))

            connection = sqlite3.connect(workspace / DASHBOARD_DB_PATH)
            connection.row_factory = sqlite3.Row
            try:
                settings_rows = list(
                    connection.execute(
                        """
                        SELECT version, settings_json, reason, is_active
                        FROM scrape_settings_versions
                        """
                    )
                )
                persisted = connection.execute(
                    "SELECT needs_attention FROM scrape_quality_scores WHERE run_id = ?",
                    ("20260507T020000Z_default",),
                ).fetchone()
            finally:
                connection.close()

            self.assertEqual(len(settings_rows), 1)
            self.assertEqual(settings_rows[0]["version"], 1)
            self.assertEqual(settings_rows[0]["reason"], "baseline")
            self.assertEqual(settings_rows[0]["is_active"], 1)
            self.assertEqual(persisted["needs_attention"], 1)

    def test_snapshot_phase_status_does_not_reduce_scrape_quality_score(self):
        healthy_score = self._compute_score_with_manifest_extra(
            {
                "phases": [
                    {"name": "source_video_snapshots", "status": "completed"},
                ],
                "outputs": {},
            }
        )
        failed_snapshot_score = self._compute_score_with_manifest_extra(
            {
                "phases": [
                    {"name": "source_video_snapshots", "status": "failed"},
                ],
                "outputs": {},
            }
        )

        self.assertEqual(failed_snapshot_score.score, healthy_score.score)
        self.assertEqual(failed_snapshot_score.components, healthy_score.components)

    def _compute_score_with_manifest_extra(self, manifest_extra: dict) -> ScrapeQualityScore:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_fixture_workspace(
                workspace,
                run_id="20260507T030000Z_default",
                run_timestamp="2026-05-07T03:00:00Z",
                videos=[
                    self._video("stable-1", days_old=1, views=90000, likes=8000, comments=200, shares=300),
                    self._video("stable-2", days_old=2, views=80000, likes=7000, comments=180, shares=250),
                    self._video("stable-3", days_old=2, views=70000, likes=6000, comments=160, shares=200),
                ],
                eligible_count=3,
                selected_ids=["stable-1", "stable-2", "stable-3"],
                manifest_extra=manifest_extra,
            )
            initialize_dashboard_store(workspace)
            index_pipeline_artifacts(workspace)
            return compute_scrape_quality_scores(workspace)[0]

    def _write_fixture_workspace(
        self,
        workspace: Path,
        *,
        run_id: str,
        run_timestamp: str,
        videos: list[dict],
        eligible_count: int,
        selected_ids: list[str],
        manifest_extra: dict | None = None,
    ) -> None:
        raw_scrapes = workspace / "data" / "raw_scrapes"
        run_folder = workspace / "runs" / "batch-analysis" / run_id
        (run_folder / "data").mkdir(parents=True, exist_ok=True)
        raw_scrapes.mkdir(parents=True, exist_ok=True)

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
                "selection": {
                    "minimum_views": 10000,
                    "maximum_age_days": 14,
                    "minimum_weighted_engagement_rate": 0.02,
                    "requires_tiktok_link": True,
                    "requires_downloadable_video": True,
                }
            },
        }
        if manifest_extra:
            manifest.update(manifest_extra)
        (run_folder / "run_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
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
                    "eligible_candidate_count": eligible_count,
                    "selected_candidate_count": len(selected_ids),
                    "selected_candidates": [{"id": video_id} for video_id in selected_ids],
                }
            ),
            encoding="utf-8",
        )

    def _video(
        self,
        video_id: str,
        *,
        days_old: int,
        views: int,
        likes: int,
        comments: int,
        shares: int,
        caption: str = "Acid reflux bloating gut health routine",
        author: str | None = None,
        downloadable: bool = True,
    ) -> dict:
        created_at = datetime(2026, 5, 7, tzinfo=timezone.utc) - timedelta(days=days_old)
        return {
            "id": video_id,
            "url": f"https://www.tiktok.com/@creator/video/{video_id}",
            "author_handle": author or f"creator-{video_id}",
            "caption": caption,
            "hashtags": ["guthealth", "digestive"],
            "source_input": "#guthealth",
            "video_download_url": f"https://cdn.example.com/{video_id}.mp4" if downloadable else "",
            "play_count": views,
            "like_count": likes,
            "comment_count": comments,
            "share_count": shares,
            "created_at": created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }


if __name__ == "__main__":
    unittest.main()
