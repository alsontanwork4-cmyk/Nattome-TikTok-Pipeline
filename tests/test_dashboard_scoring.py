import unittest
from datetime import datetime, timezone

from dashboard.scoring import (
    engagement_band,
    freshness_facet,
    freshness_label,
    nattome_relevance,
    relevance_band,
    scrape_freshness_score,
    video_score_band,
    weighted_engagement,
)


class DashboardScoringTest(unittest.TestCase):
    def test_raw_video_scoring_vocabulary_matches_dashboard_rules(self):
        raw_video = {
            "caption": "Acid reflux bloating gut health routine",
            "hashtags_json": '["guthealth", "digestive"]',
            "source_input": "#guthealth",
            "play_count": 100000,
            "like_count": 9000,
            "comment_count": 300,
            "share_count": 400,
            "created_at": "2026-05-06T00:00:00Z",
        }
        run_timestamp = datetime(2026, 5, 7, tzinfo=timezone.utc)

        self.assertEqual(nattome_relevance(raw_video), 1.0)
        self.assertEqual(relevance_band(raw_video), "high relevance")
        self.assertEqual(weighted_engagement(raw_video), 0.145)
        self.assertEqual(engagement_band(raw_video), "high engagement")
        self.assertEqual(video_score_band(raw_video), "strong scrape")
        self.assertAlmostEqual(
            scrape_freshness_score(raw_video, run_timestamp, max_age_days=14),
            1 - (1 / 14),
        )
        self.assertEqual(freshness_facet(raw_video["created_at"], run_timestamp), "fresh")
        self.assertEqual(freshness_label(raw_video["created_at"]), "created date available")

    def test_batch_run_missing_dates_keep_existing_freshness_text(self):
        raw_video = {
            "caption": "Generic wellness clip",
            "hashtags_json": "[]",
            "source_input": "#wellness",
            "play_count": 0,
            "like_count": 0,
            "comment_count": 0,
            "share_count": 0,
            "created_at": "",
        }

        self.assertEqual(nattome_relevance(raw_video), 0.0)
        self.assertEqual(relevance_band(raw_video), "low relevance")
        self.assertEqual(weighted_engagement(raw_video), 0.0)
        self.assertEqual(engagement_band(raw_video), "low engagement")
        self.assertEqual(video_score_band(raw_video), "needs attention")
        self.assertEqual(scrape_freshness_score(raw_video, None, max_age_days=14), 0.5)
        self.assertEqual(freshness_facet(raw_video["created_at"], None), "undated")
        self.assertEqual(freshness_label(raw_video["created_at"]), "created date missing")


if __name__ == "__main__":
    unittest.main()
