import json
import tempfile
import unittest
from pathlib import Path

from batch_analysis.claim_safety import write_claim_safety_review


class ClaimSafetyReviewTest(unittest.TestCase):
    def test_claim_safety_review_flags_unsafe_transcript_claims(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_folder = Path(temp_dir)
            (bundle_folder / "transcript_evidence.json").write_text(
                json.dumps(
                    {
                        "segments": [
                            {
                                "start_seconds": 0,
                                "text": "Cure reflux overnight with a 100% guaranteed detox.",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (bundle_folder / "ocr_evidence.json").write_text(
                json.dumps({"frames": []}),
                encoding="utf-8",
            )

            status = write_claim_safety_review(bundle_folder)

            self.assertEqual(status["status"], "completed")
            review = json.loads((bundle_folder / "claim_safety_review.json").read_text())
            categories = {claim["category"] for claim in review["flagged_claims"]}
            self.assertIn("cure_claim", categories)
            self.assertIn("one_night_fix", categories)
            self.assertIn("guaranteed_outcome", categories)
            self.assertIn("detox_or_cleanse", categories)
