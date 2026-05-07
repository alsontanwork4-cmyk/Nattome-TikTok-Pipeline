import json
import tempfile
import unittest
from pathlib import Path

from batch_analysis.evidence_quality import write_evidence_quality


class EvidenceQualityTest(unittest.TestCase):
    def test_missing_video_and_visible_text_failure_require_low_quality_manual_review(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_folder = Path(temp_dir)
            (bundle_folder / "download_status.json").write_text(
                json.dumps({"status": "missing"}),
                encoding="utf-8",
            )
            (bundle_folder / "hybrid_timeline.json").write_text(
                json.dumps({"status": "skipped"}),
                encoding="utf-8",
            )
            (bundle_folder / "ocr_evidence.json").write_text(
                json.dumps({"status": "skipped", "summary": {"text_frame_count": 0}}),
                encoding="utf-8",
            )
            (bundle_folder / "transcript_evidence.json").write_text(
                json.dumps({"status": "skipped", "segments": []}),
                encoding="utf-8",
            )
            (bundle_folder / "baseline_audio_analysis.json").write_text(
                json.dumps({"status": "completed", "hook_support": "no audio hook evidence captured yet"}),
                encoding="utf-8",
            )
            (bundle_folder / "claim_safety_review.json").write_text(
                json.dumps({"summary": {"flagged_count": 0}}),
                encoding="utf-8",
            )

            status = write_evidence_quality(bundle_folder, {"visible_text_expected": True})

            self.assertEqual(status["score"], "low")
            self.assertTrue(status["manual_review_required"])
            quality = json.loads((bundle_folder / "evidence_quality.json").read_text())
            self.assertIn("video download failed", quality["evidence_quality_score"]["reason"])
            self.assertIn("ocr_failed_on_visible_text", quality["manual_review_flag"]["reasons"])
