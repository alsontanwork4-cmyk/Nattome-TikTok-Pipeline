from copy import deepcopy
from datetime import datetime, timezone
import unittest

from batch_analysis.candidates import select_candidates
from batch_analysis.config import DEFAULT_CONFIG


RUN_TIMESTAMP = datetime(2026, 5, 6, 13, 45, 30, tzinfo=timezone.utc)


def eligible_candidate(candidate_id, **overrides):
    candidate = {
        "id": candidate_id,
        "url": f"https://www.tiktok.com/@creator/video/{candidate_id}",
        "video_download_url": f"https://cdn.example.com/{candidate_id}.mp4",
        "caption": "Acid reflux and bloating routine for gut health",
        "play_count": 100000,
        "like_count": 9000,
        "comment_count": 300,
        "share_count": 400,
        "created_at": "2026-05-05T00:00:00Z",
    }
    candidate.update(overrides)
    return candidate


class CandidateSelectionTest(unittest.TestCase):
    def test_excludes_candidates_without_downloadable_video_source_by_default(self):
        configuration = deepcopy(DEFAULT_CONFIG)

        selected_batch = select_candidates(
            [
                eligible_candidate("with-video"),
                eligible_candidate("metadata-only", video_download_url=""),
            ],
            configuration,
            RUN_TIMESTAMP,
            batch_size=2,
            candidates_path=None,
        )

        self.assertEqual(
            [candidate["id"] for candidate in selected_batch["selected_candidates"]],
            ["with-video"],
        )
        self.assertEqual(selected_batch["eligible_candidate_count"], 1)
        excluded = {item["id"]: item["reason"] for item in selected_batch["excluded_candidates"]}
        self.assertIn("missing downloadable video source", excluded["metadata-only"])

    def test_explicit_override_allows_metadata_only_selection_preview(self):
        configuration = deepcopy(DEFAULT_CONFIG)
        configuration["selection"]["requires_downloadable_video"] = False

        selected_batch = select_candidates(
            [
                eligible_candidate("with-video"),
                eligible_candidate("metadata-only", video_download_url=""),
            ],
            configuration,
            RUN_TIMESTAMP,
            batch_size=2,
            candidates_path=None,
        )

        self.assertEqual(
            [candidate["id"] for candidate in selected_batch["selected_candidates"]],
            ["with-video", "metadata-only"],
        )
        self.assertEqual(selected_batch["eligible_candidate_count"], 2)
        self.assertEqual(selected_batch["excluded_candidates"], [])

    def test_exclusion_terms_filter_caption_hashtags_and_source_input(self):
        configuration = deepcopy(DEFAULT_CONFIG)
        configuration["selection"]["exclusion_terms"] = ["weight loss"]

        selected_batch = select_candidates(
            [
                eligible_candidate("gut-fit"),
                eligible_candidate(
                    "excluded-topic",
                    caption="Weight loss cleanse for bloating",
                ),
            ],
            configuration,
            RUN_TIMESTAMP,
            batch_size=2,
            candidates_path=None,
        )

        self.assertEqual(
            [candidate["id"] for candidate in selected_batch["selected_candidates"]],
            ["gut-fit"],
        )
        excluded = {item["id"]: item["reason"] for item in selected_batch["excluded_candidates"]}
        self.assertIn("matches exclusion term: weight loss", excluded["excluded-topic"])

    def test_preserve_order_uses_daily_handoff_order_without_reranking(self):
        configuration = deepcopy(DEFAULT_CONFIG)

        selected_batch = select_candidates(
            [
                eligible_candidate("daily-first", play_count=10000, like_count=500, comment_count=10, share_count=10),
                eligible_candidate("daily-second", play_count=500000, like_count=90000, comment_count=900, share_count=900),
                eligible_candidate("daily-third", play_count=300000, like_count=80000, comment_count=800, share_count=800),
            ],
            configuration,
            RUN_TIMESTAMP,
            batch_size=2,
            candidates_path=None,
            preserve_order=True,
        )

        self.assertEqual(
            [candidate["id"] for candidate in selected_batch["selected_candidates"]],
            ["daily-first", "daily-second"],
        )
        self.assertEqual(selected_batch["selection_strategy"], "input_order")

    def test_default_selection_still_reranks_by_viral_relevance_score(self):
        configuration = deepcopy(DEFAULT_CONFIG)

        selected_batch = select_candidates(
            [
                eligible_candidate("weaker-first", play_count=10000, like_count=500, comment_count=10, share_count=10),
                eligible_candidate("stronger-second", play_count=500000, like_count=90000, comment_count=900, share_count=900),
            ],
            configuration,
            RUN_TIMESTAMP,
            batch_size=2,
            candidates_path=None,
        )

        self.assertEqual(
            [candidate["id"] for candidate in selected_batch["selected_candidates"]],
            ["stronger-second", "weaker-first"],
        )
        self.assertEqual(selected_batch["selection_strategy"], "viral_relevance_score")


if __name__ == "__main__":
    unittest.main()
