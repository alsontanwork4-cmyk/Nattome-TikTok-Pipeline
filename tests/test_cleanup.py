import json
import tempfile
import unittest
from pathlib import Path

from batch_analysis.cleanup import cleanup_evidence_artifacts


class EvidenceArtifactCleanupTest(unittest.TestCase):
    def test_cleanup_removes_large_artifacts_after_report_approval(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir)
            bundle_folder = run_folder / "evidence_bundles" / "001_cleanup-video"
            artifacts = bundle_folder / "artifacts"
            frames = artifacts / "frames"
            logs = run_folder / "logs"
            logs.mkdir(parents=True)
            frames.mkdir(parents=True)
            source_video = artifacts / "source_video.mp4"
            source_video.write_bytes(b"large video")
            (frames / "frame_000000ms.jpg").write_bytes(b"frame")

            for path in [
                bundle_folder / "video_evidence_report.md",
                run_folder / "batch_outputs" / "markdown" / "cross_video_pattern_summary.md",
                run_folder / "batch_outputs" / "json" / "structured_batch_analysis.json",
                run_folder / "batch_outputs" / "spreadsheets" / "spreadsheet_summary.csv",
            ]:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("durable", encoding="utf-8")

            evidence_index = {
                "bundles": [
                    {
                        "candidate_id": "cleanup-video",
                        "bundle_folder": "evidence_bundles/001_cleanup-video",
                        "artifacts": {
                            "source_video": {
                                "path": "evidence_bundles/001_cleanup-video/artifacts/source_video.mp4"
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
            self.assertEqual(status["removed_artifact_count"], 2)
            self.assertFalse(source_video.exists())
            self.assertFalse(frames.exists())
            log = json.loads((logs / "evidence_artifact_cleanup.json").read_text())
            self.assertTrue(log["bundles"][0]["preserved_outputs"])
