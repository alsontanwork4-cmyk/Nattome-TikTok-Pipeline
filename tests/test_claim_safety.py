import json
import tempfile
import unittest
from pathlib import Path

from batch_analysis.claim_safety import write_claim_safety_review_from_snapshot


class ClaimSafetyReviewTest(unittest.TestCase):
    def test_claim_safety_review_flags_unsafe_gemini_claims(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            review_path = Path(temp_dir) / "claim_safety_review.json"

            status = write_claim_safety_review_from_snapshot(
                review_path,
                {
                    "status": "completed",
                    "claim_evidence": [
                        {
                            "timestamp_seconds": 0,
                            "text": "Cure reflux overnight with a 100% guaranteed detox.",
                        }
                    ],
                    "visible_text": [],
                    "spoken_content": [],
                },
            )

            self.assertEqual(status["status"], "completed")
            review = json.loads(review_path.read_text())
            categories = {claim["category"] for claim in review["flagged_claims"]}
            self.assertIn("cure_claim", categories)
            self.assertIn("one_night_fix", categories)
            self.assertIn("guaranteed_outcome", categories)
            self.assertIn("detox_or_cleanse", categories)
