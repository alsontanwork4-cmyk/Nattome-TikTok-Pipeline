import json
import tempfile
import unittest
from pathlib import Path

from batch_analysis.evidence_quality import write_evidence_quality_from_snapshot


class EvidenceQualityTest(unittest.TestCase):
    def test_missing_video_and_visible_text_failure_require_low_quality_manual_review(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            quality_path = Path(temp_dir) / "evidence_quality.json"

            status = write_evidence_quality_from_snapshot(
                quality_path,
                {"visible_text_expected": True},
                {"source_video": {"state": "missing"}},
                {
                    "status": "missing_credentials",
                    "reason": "Gemini API key is missing",
                    "visual_observations": [],
                    "visible_text": [],
                    "spoken_content": [],
                    "audio_cues": [],
                    "hook_evidence": [],
                    "claim_evidence": [],
                },
                {"summary": {"flagged_count": 0}},
            )

            self.assertEqual(status["score"], "low")
            self.assertTrue(status["manual_review_required"])
            quality = json.loads(quality_path.read_text())
            self.assertIn("source video unavailable", quality["evidence_quality_score"]["reason"])
            self.assertIn("missing_gemini_visible_text", quality["manual_review_flag"]["reasons"])
