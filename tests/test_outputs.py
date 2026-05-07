import json
import tempfile
import unittest
from pathlib import Path

from batch_analysis.outputs import write_cross_video_pattern_summary


class BatchOutputSetTest(unittest.TestCase):
    def test_cross_video_pattern_summary_writes_priority_score_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir)
            (run_folder / "data").mkdir(parents=True)
            (run_folder / "reports").mkdir(parents=True)
            (run_folder / "data" / "001_output-video_evidence_quality.json").write_text(
                json.dumps(
                    {
                        "evidence_quality_score": {"level": "high"},
                        "checks": {"first_three_second_hook": {"clear": True}},
                    }
                ),
                encoding="utf-8",
            )
            (run_folder / "data" / "001_output-video_claim_safety_review.json").write_text(
                json.dumps({"flagged_claims": []}),
                encoding="utf-8",
            )
            (run_folder / "data" / "001_output-video_baseline_audio_analysis.json").write_text(
                json.dumps(
                    {
                        "audio_format": "talking_head",
                        "hook_support": "spoken hook supports first three seconds",
                    }
                ),
                encoding="utf-8",
            )
            (run_folder / "data" / "001_output-video_shootable_angles.json").write_text(
                json.dumps(
                    {
                        "status": "completed",
                        "angles": [
                            {
                                "angle_title": "Evidence-Led Bloating Routine",
                                "hook": "Ask what changed after meals.",
                                "avatar": "The Sufferer",
                                "format": "Talking-head explainer with simple on-screen text.",
                                "product_fit": "DH for daily digestive maintenance and routine support.",
                                "recommendation": "Adapt the pain point with support language.",
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

            selected_batch = {
                "selected_at": "2026-05-06T13:45:30Z",
                "selected_candidates": [
                    {
                        "id": "output-video",
                        "url": "https://www.tiktok.com/@creator/video/output",
                        "caption": "Bloating after meals routine",
                        "play_count": 120000,
                        "weighted_engagement_rate": 0.12,
                        "nattome_relevance_score": 0.75,
                        "audio_format_hint": "talking_head",
                    }
                ],
            }
            evidence_index = {
                "bundles": [
                    {
                        "candidate_id": "output-video",
                        "prefix": "001_output-video",
                        "artifacts": {
                            "baseline_audio_analysis": {
                                "path": "data/001_output-video_baseline_audio_analysis.json",
                            },
                            "claim_safety_review": {
                                "path": "data/001_output-video_claim_safety_review.json",
                            },
                            "evidence_quality": {
                                "path": "data/001_output-video_evidence_quality.json",
                            },
                            "shootable_angles": {
                                "path": "data/001_output-video_shootable_angles.json",
                            },
                        },
                    }
                ]
            }

            result = write_cross_video_pattern_summary(run_folder, selected_batch, evidence_index)

            self.assertEqual(result["status"], "completed")
            summary = json.loads(
                (run_folder / "data" / "cross_video_pattern_summary.json").read_text(
                    encoding="utf-8"
                )
            )
            top_angle = summary["top_priority_shootable_angles"][0]
            self.assertEqual(top_angle["candidate_id"], "output-video")
            self.assertEqual(top_angle["angle_title"], "Evidence-Led Bloating Routine")
            self.assertEqual(top_angle["priority_score"]["max_points"], 30)
            self.assertEqual(
                top_angle["priority_score"]["total"],
                sum(top_angle["priority_score"]["dimensions"].values()),
            )
            markdown = (
                run_folder / "reports" / "cross_video_pattern_summary.md"
            ).read_text(encoding="utf-8")
            self.assertIn("Nattome Priority Score", markdown)
            self.assertIn("output-video", markdown)
