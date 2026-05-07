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


if __name__ == "__main__":
    unittest.main()
