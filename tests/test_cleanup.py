import json
import tempfile
import unittest
from pathlib import Path

from batch_analysis.cleanup import cleanup_evidence_artifacts


class EvidenceArtifactCleanupTest(unittest.TestCase):
    def test_cleanup_removes_large_artifacts_after_report_approval(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir)
            logs = run_folder / "logs"
            evidence = run_folder / "evidence"
            logs.mkdir(parents=True)
            evidence.mkdir(parents=True)
            source_video = evidence / "001_cleanup-video_source_video.mp4"
            source_video.write_bytes(b"large video")

            for path in [
                run_folder / "reports" / "001_cleanup-video_video_evidence_report.md",
                run_folder / "reports" / "cross_video_pattern_summary.md",
                run_folder / "data" / "structured_batch_analysis.json",
                run_folder / "data" / "spreadsheet_summary.csv",
            ]:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("durable", encoding="utf-8")

            evidence_index = {
                "bundles": [
                    {
                        "candidate_id": "cleanup-video",
                        "prefix": "001_cleanup-video",
                        "artifacts": {
                            "source_video": {
                                "path": "evidence/001_cleanup-video_source_video.mp4"
                            }
                        },
                    }
                ]
            }

            status = cleanup_evidence_artifacts(
                run_folder,
                evidence_index,
                {"enabled": True, "requires_report_approval": True, "report_approved": True},
            )

            self.assertEqual(status["status"], "completed")
            self.assertEqual(status["removed_artifact_count"], 1)
            self.assertFalse(source_video.exists())
            log = json.loads((logs / "evidence_artifact_cleanup.json").read_text())
            self.assertTrue(log["bundles"][0]["preserved_outputs"])
