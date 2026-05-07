import tempfile
import unittest
from pathlib import Path

from batch_analysis.reports import write_video_evidence_report_from_snapshot


class VideoEvidenceReportTest(unittest.TestCase):
    def test_video_evidence_report_uses_fixed_report_form_sections(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "video_evidence_report.md"

            status = write_video_evidence_report_from_snapshot(
                report_path,
                {
                    "id": "report-test",
                    "url": "https://www.tiktok.com/@creator/video/reporttest",
                    "caption": "Bloating after meals",
                    "play_count": 50000,
                    "weighted_engagement_rate": 0.1,
                    "nattome_relevance_score": 0.75,
                },
                {
                    "snapshot_path": "data/001_report-test_evidence_snapshot.json",
                    "source_video": {"state": "missing"},
                },
                {
                    "status": "missing_credentials",
                    "reason": "Gemini API key is missing",
                    "visual_observations": [],
                    "visible_text": [],
                    "spoken_content": [],
                    "audio_cues": [],
                    "hook_evidence": [],
                    "claim_evidence": [],
                    "missing_evidence": ["visual_observations"],
                },
                {"status": "completed", "audio_format": "unknown"},
                {"flagged_claims": []},
                {
                    "evidence_quality_score": {"level": "low", "reason": "video download failed"},
                    "manual_review_flag": {"required": True, "reasons": ["evidence_quality_low"]},
                },
                [],
            )

            self.assertEqual(status["status"], "completed")
            report = report_path.read_text(encoding="utf-8")
            self.assertIn("# Video Evidence Report: report-test", report)
            self.assertIn("## Video Reference", report)
            self.assertNotIn("## Nattome POV", report)
            self.assertIn("## Claim Safety Review", report)
            self.assertIn("## Evidence Quality", report)
            self.assertIn("Gemini evidence not available", report)
