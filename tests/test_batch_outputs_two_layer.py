import csv
import json
import tempfile
import unittest
from pathlib import Path

from batch_analysis.outputs import (
    write_cross_video_pattern_summary,
    write_structured_json_and_spreadsheet_summary,
)


class TwoLayerBatchOutputsTest(unittest.TestCase):
    def test_batch_outputs_use_flat_run_layout_and_structured_angles(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir)
            for folder in ["reports", "data", "logs"]:
                (run_folder / folder).mkdir()

            candidate = {
                "id": "angle-video",
                "rank": 1,
                "url": "https://www.tiktok.com/@creator/video/angle",
                "caption": "Bloating after meals routine",
                "play_count": 120000,
                "weighted_engagement_rate": 0.12,
                "nattome_relevance_score": 0.75,
                "audio_format_hint": "talking_head",
            }
            selected_batch = {
                "selected_at": "2026-05-06T13:45:30Z",
                "selected_candidates": [candidate],
            }
            snapshot = {
                "candidate_id": "angle-video",
                "rank": 1,
                "prefix": "001_angle-video",
                "snapshot_path": "data/001_angle-video_evidence_snapshot.json",
                "source_metadata": {
                    "state": "available",
                    "path": "data/001_angle-video_source_metadata.json",
                },
                "artifacts": {
                    "gemini_evidence": {"path": "data/001_angle-video_gemini_evidence.json"},
                    "baseline_audio_analysis": {
                        "path": "data/001_angle-video_baseline_audio_analysis.json"
                    },
                    "claim_safety_review": {
                        "path": "data/001_angle-video_claim_safety_review.json"
                    },
                    "evidence_quality": {
                        "path": "data/001_angle-video_evidence_quality.json"
                    },
                    "shootable_angles": {
                        "path": "data/001_angle-video_shootable_angles.json"
                    },
                },
            }
            evidence_index = {"bundle_count": 1, "bundles": [snapshot]}
            (run_folder / "data" / "001_angle-video_source_metadata.json").write_text(
                json.dumps(candidate), encoding="utf-8"
            )
            (run_folder / "data" / "001_angle-video_gemini_evidence.json").write_text(
                json.dumps({"status": "completed", "visual_observations": []}),
                encoding="utf-8",
            )
            (run_folder / "data" / "001_angle-video_baseline_audio_analysis.json").write_text(
                json.dumps(
                    {
                        "status": "completed",
                        "audio_format": "talking_head",
                        "hook_support": "Gemini hook evidence: creator opens with discomfort",
                    }
                ),
                encoding="utf-8",
            )
            (run_folder / "data" / "001_angle-video_claim_safety_review.json").write_text(
                json.dumps({"flagged_claims": []}), encoding="utf-8"
            )
            (run_folder / "data" / "001_angle-video_evidence_quality.json").write_text(
                json.dumps(
                    {
                        "evidence_quality_score": {"level": "high"},
                        "manual_review_flag": {"required": False},
                    }
                ),
                encoding="utf-8",
            )
            (run_folder / "data" / "001_angle-video_shootable_angles.json").write_text(
                json.dumps(
                    {
                        "status": "completed",
                        "angles": [
                            {
                                "angle_title": "Evidence-Led Bloating Routine",
                                "hook": "Ask what changed after meals.",
                                "avatar": "The Sufferer",
                                "format": "Talking-head explainer",
                                "product_fit": "DH for daily digestive maintenance and routine support.",
                                "recommendation": "Adapt the observed pain point safely.",
                                "claim_guardrails": "Avoid cure claims.",
                                "source_evidence": ["hook_evidence"],
                                "priority_score": {
                                    "dimensions": {
                                        "viral_strength": 4,
                                        "nattome_relevance": 4,
                                        "evidence_confidence": 5,
                                        "brand_safety": 5,
                                        "ease_of_production": 5,
                                        "product_fit": 5,
                                    },
                                    "total": 28,
                                    "max_points": 30,
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (run_folder / "data" / "001_angle-video_evidence_snapshot.json").write_text(
                json.dumps(snapshot), encoding="utf-8"
            )

            summary_result = write_cross_video_pattern_summary(
                run_folder, selected_batch, evidence_index
            )
            structured_result = write_structured_json_and_spreadsheet_summary(
                run_folder,
                selected_batch,
                evidence_index,
                {"run_timestamp": "2026-05-06T13:45:30Z", "mode": "debug"},
                summary_result["summary"],
            )

            self.assertTrue((run_folder / "reports" / "cross_video_pattern_summary.md").is_file())
            self.assertTrue((run_folder / "data" / "cross_video_pattern_summary.json").is_file())
            self.assertTrue((run_folder / "data" / "structured_batch_analysis.json").is_file())
            self.assertTrue((run_folder / "data" / "spreadsheet_summary.csv").is_file())
            self.assertFalse((run_folder / "batch_outputs").exists())

            summary = json.loads(
                (run_folder / "data" / "cross_video_pattern_summary.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                summary["top_priority_shootable_angles"][0]["angle_title"],
                "Evidence-Led Bloating Routine",
            )
            self.assertNotIn(
                "Digestive Comfort Routine Check",
                (run_folder / "reports" / "cross_video_pattern_summary.md").read_text(
                    encoding="utf-8"
                ),
            )

            with (run_folder / "data" / "spreadsheet_summary.csv").open(
                newline="", encoding="utf-8"
            ) as spreadsheet_file:
                rows = list(csv.DictReader(spreadsheet_file))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["recommended_angle"], "Evidence-Led Bloating Routine")
            self.assertEqual(
                structured_result["structured_json_path"], "data/structured_batch_analysis.json"
            )
            self.assertEqual(
                structured_result["spreadsheet_path"], "data/spreadsheet_summary.csv"
            )
