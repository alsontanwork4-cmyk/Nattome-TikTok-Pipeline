import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from batch_analysis.evidence import write_snapshot_evidence_outputs
from batch_analysis.evidence_io import EvidenceBundleStore
from batch_analysis.run import create_run


def candidate(**overrides):
    payload = {
        "id": "snapshot-video",
        "rank": 1,
        "url": "https://www.tiktok.com/@creator/video/snapshot",
        "caption": "Acid reflux after meals",
        "play_count": 120000,
        "weighted_engagement_rate": 0.18,
        "nattome_relevance_score": 0.85,
        "visible_text_expected": True,
    }
    payload.update(overrides)
    return payload


def complete_gemini_evidence(**overrides):
    payload = {
        "status": "completed",
        "model": "gemini-2.5-flash",
        "visual_observations": [
            {"timestamp_seconds": 0.5, "observation": "Creator points at stomach pain gesture"}
        ],
        "visible_text": [
            {"timestamp_seconds": 0.7, "text": "Acid reflux after dinner?"}
        ],
        "spoken_content": [
            {
                "start_seconds": 0,
                "end_seconds": 2,
                "text": "This cures reflux overnight with a 100% guarantee",
                "language": "English",
                "confidence": 0.94,
            }
        ],
        "audio_cues": [{"timestamp_seconds": 0, "cue": "calm voiceover"}],
        "hook_evidence": [{"timestamp_seconds": 0.5, "evidence": "problem question opens the video"}],
        "claim_evidence": [{"timestamp_seconds": 1.2, "text": "cures reflux overnight"}],
        "missing_evidence": [],
    }
    payload.update(overrides)
    return payload


class SnapshotEvidenceOutputsTest(unittest.TestCase):
    def test_complete_gemini_snapshot_writes_flat_report_and_review_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "run"
            for child in ("reports", "data", "evidence", "logs"):
                (run_folder / child).mkdir(parents=True)
            selected = candidate()
            store = EvidenceBundleStore(run_folder)
            store.write_source_snapshots([selected])
            snapshot = store.write_gemini_evidence(selected, complete_gemini_evidence())

            status = write_snapshot_evidence_outputs(run_folder, selected, snapshot)

            self.assertEqual(status["status"], "completed")
            self.assertEqual(status["report_path"], "reports/001_snapshot-video_video_evidence_report.md")
            self.assertTrue((run_folder / "reports" / "001_snapshot-video_video_evidence_report.md").is_file())
            self.assertTrue((run_folder / "data" / "001_snapshot-video_evidence_quality.json").is_file())
            self.assertTrue((run_folder / "data" / "001_snapshot-video_baseline_audio_analysis.json").is_file())
            self.assertTrue((run_folder / "data" / "001_snapshot-video_claim_safety_review.json").is_file())

            report = (run_folder / "reports" / "001_snapshot-video_video_evidence_report.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("Creator points at stomach pain gesture", report)
            self.assertIn("Acid reflux after dinner?", report)
            self.assertIn("problem question opens the video", report)
            self.assertNotIn("ocr_evidence.json", report)
            self.assertNotIn("transcript_evidence.json", report)

            review = json.loads(
                (run_folder / "data" / "001_snapshot-video_claim_safety_review.json").read_text(
                    encoding="utf-8"
                )
            )
            categories = {claim["category"] for claim in review["flagged_claims"]}
            self.assertIn("cure_claim", categories)
            self.assertIn("one_night_fix", categories)
            self.assertEqual(review["source_artifacts"], ["gemini_claim_evidence", "gemini_visible_text", "gemini_spoken_content"])

    def test_partial_and_missing_gemini_snapshots_record_uncertainty(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "run"
            for child in ("reports", "data", "evidence", "logs"):
                (run_folder / child).mkdir(parents=True)
            selected = candidate(id="missing-gemini", rank=1, visible_text_expected=False)
            status = write_snapshot_evidence_outputs(
                run_folder,
                selected,
                {
                    "candidate_id": "missing-gemini",
                    "rank": 1,
                    "prefix": "001_missing-gemini",
                    "source_video": {"state": "available", "path": "evidence/001_missing-gemini_source_video.mp4"},
                    "artifacts": {
                        "gemini_evidence": {
                            "state": "missing_credentials",
                            "path": None,
                            "reason": "Gemini API key is missing",
                            "missing_evidence": [
                                "visual_observations",
                                "visible_text",
                                "spoken_content",
                                "audio_cues",
                                "hook_evidence",
                                "claim_evidence",
                            ],
                        }
                    },
                },
            )

            self.assertEqual(status["status"], "completed")
            quality = json.loads(
                (run_folder / "data" / "001_missing-gemini_evidence_quality.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(quality["evidence_quality_score"]["level"], "low")
            self.assertTrue(quality["manual_review_flag"]["required"])
            self.assertIn("missing Gemini visual evidence", quality["evidence_quality_score"]["reason"])

            report = (run_folder / "reports" / "001_missing-gemini_video_evidence_report.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("Gemini evidence not available: Gemini API key is missing.", report)
            self.assertIn("Manual review required", report)
            self.assertIn("No evidence-backed Shootable Angle was generated", report)
            self.assertNotIn("Digestive Comfort Routine Check", report)

    def test_selected_batch_run_writes_snapshot_reports_to_two_layer_layout(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_video = temp_path / "source.mp4"
            source_video.write_bytes(b"fake mp4 bytes")
            candidates_path = temp_path / "candidates.json"
            candidates_path.write_text(
                json.dumps(
                    {
                        "top": [
                            {
                                "id": "selected-video",
                                "url": "https://www.tiktok.com/@creator/video/selected",
                                "video_download_url": str(source_video),
                                "caption": "Acid reflux after meals",
                                "play_count": 100000,
                                "like_count": 10000,
                                "comment_count": 500,
                                "share_count": 600,
                                "created_at": "2026-05-05T00:00:00Z",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            run_folder = create_run(
                Namespace(
                    mode="debug",
                    batch_size=1,
                    runs_dir=temp_path / "runs",
                    config=None,
                    candidates=candidates_path,
                    timestamp="2026-05-06T13:45:30Z",
                )
            )

            self.assertTrue((run_folder / "reports" / "001_selected-video_video_evidence_report.md").is_file())
            self.assertTrue((run_folder / "data" / "001_selected-video_claim_safety_review.json").is_file())
            snapshot = json.loads(
                (run_folder / "data" / "001_selected-video_evidence_snapshot.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                snapshot["artifacts"]["video_evidence_report"]["path"],
                "reports/001_selected-video_video_evidence_report.md",
            )


if __name__ == "__main__":
    unittest.main()
