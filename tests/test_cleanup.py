import json
import tempfile
import unittest
from pathlib import Path

from batch_analysis.cleanup import cleanup_evidence_artifacts


class EvidenceArtifactCleanupTest(unittest.TestCase):
    def test_cleanup_preserves_manifest_registered_final_report_and_workbook(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            run_folder = temp_path / "runs" / "20260506T134530Z_debug"
            output_root = temp_path / "outputs"
            logs = run_folder / "logs"
            evidence = run_folder / "evidence"
            final_report = (
                output_root
                / "reports"
                / "2026-05-06"
                / "top5_creative_production_report_2026-05-06.md"
            )
            final_workbook = (
                output_root
                / "reports"
                / "2026-05-06"
                / "top5_angle_planning_sheet_2026-05-06.xlsx"
            )
            for path in [logs, evidence, final_report.parent]:
                path.mkdir(parents=True, exist_ok=True)
            final_report.write_text("final report", encoding="utf-8")
            final_workbook.write_bytes(b"final workbook")
            source_video = evidence / "001_cleanup-video_source_video.mp4"
            source_video.write_bytes(b"large video")
            (run_folder / "run_manifest.json").write_text(
                json.dumps(
                    {
                        "outputs": {
                            "output_root": str(output_root),
                            "final_outputs": [
                                {
                                    "label": "Daily Top-3 Creative Production Report",
                                    "kind": "markdown",
                                    "path": (
                                        "reports/2026-05-06/"
                                        "top5_creative_production_report_2026-05-06.md"
                                    ),
                                },
                                {
                                    "label": "Excel Planning Workbook",
                                    "kind": "spreadsheet",
                                    "path": (
                                        "reports/2026-05-06/"
                                        "top5_angle_planning_sheet_2026-05-06.xlsx"
                                    ),
                                },
                            ],
                        }
                    }
                ),
                encoding="utf-8",
            )

            status = cleanup_evidence_artifacts(
                run_folder,
                {
                    "bundles": [
                        {
                            "candidate_id": "cleanup-video",
                            "artifacts": {
                                "source_video": {
                                    "path": "evidence/001_cleanup-video_source_video.mp4"
                                }
                            },
                        }
                    ]
                },
                {"enabled": True, "requires_report_approval": True, "report_approved": True},
            )

            self.assertEqual(status["status"], "completed")
            self.assertFalse(source_video.exists())
            self.assertTrue(final_report.exists())
            self.assertTrue(final_workbook.exists())
            log = json.loads((logs / "evidence_artifact_cleanup.json").read_text())
            self.assertTrue(log["bundles"][0]["preserved_outputs"])

    def test_cleanup_does_not_preserve_artifacts_for_retired_output_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir)
            logs = run_folder / "logs"
            evidence = run_folder / "evidence"
            logs.mkdir(parents=True)
            evidence.mkdir(parents=True)
            source_video = evidence / "001_cleanup-video_source_video.mp4"
            source_video.write_bytes(b"large video")

            for path in [
                run_folder / "reports" / "cross_video_pattern_summary.md",
                run_folder / "data" / "structured_batch_analysis.json",
                run_folder / "data" / "spreadsheet_summary.csv",
            ]:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("retired output", encoding="utf-8")

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
            self.assertFalse(log["bundles"][0]["preserved_outputs"])
