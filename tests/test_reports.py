import json
import tempfile
import unittest
from pathlib import Path

from batch_analysis.reports import write_video_evidence_report


class VideoEvidenceReportTest(unittest.TestCase):
    def test_video_evidence_report_uses_fixed_report_form_sections(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_folder = Path(temp_dir)
            for filename, payload in {
                "download_status.json": {"status": "missing", "reason": "no source"},
                "hybrid_timeline.json": {"status": "skipped", "reason": "source video artifact is missing"},
                "ocr_evidence.json": {"status": "skipped"},
                "transcript_evidence.json": {"status": "skipped"},
                "baseline_audio_analysis.json": {"status": "completed", "audio_format": "unknown"},
                "claim_safety_review.json": {"flagged_claims": []},
                "evidence_quality.json": {
                    "evidence_quality_score": {"level": "low", "reason": "video download failed"},
                    "manual_review_flag": {"required": True, "reasons": ["evidence_quality_low"]},
                    "checks": {"first_three_second_hook": {"clear": False}},
                },
            }.items():
                (bundle_folder / filename).write_text(json.dumps(payload), encoding="utf-8")

            status = write_video_evidence_report(
                bundle_folder,
                {
                    "id": "report-test",
                    "url": "https://www.tiktok.com/@creator/video/reporttest",
                    "caption": "Bloating after meals",
                    "play_count": 50000,
                    "weighted_engagement_rate": 0.1,
                    "nattome_relevance_score": 0.75,
                },
            )

            self.assertEqual(status["status"], "completed")
            report = (bundle_folder / "video_evidence_report.md").read_text(encoding="utf-8")
            self.assertIn("# Video Evidence Report: report-test", report)
            self.assertIn("## Video Reference", report)
            self.assertIn("## Claim Safety Review", report)
            self.assertIn("## Evidence Quality", report)
            self.assertIn("This report does not claim video evidence was inspected", report)
