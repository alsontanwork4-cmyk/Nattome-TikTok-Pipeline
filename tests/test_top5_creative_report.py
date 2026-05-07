import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from batch_analysis.outputs import write_top5_creative_production_report
from batch_analysis.run import create_run


def candidate(temp_path: Path, index: int, **overrides):
    source_video = temp_path / f"source-{index}.mp4"
    source_video.write_bytes(b"fake mp4 bytes")
    payload = {
        "id": f"video-{index}",
        "rank": index,
        "url": f"https://www.tiktok.com/@creator{index}/video/{index}",
        "video_download_url": str(source_video),
        "author_handle": f"creator{index}",
        "caption": f"Bloating after meals routine {index}",
        "play_count": 100000 + index,
        "like_count": 10000 + index,
        "comment_count": 500 + index,
        "share_count": 700 + index,
        "created_at": "2026-05-05T00:00:00Z",
        "weighted_engagement_rate": 0.12,
        "nattome_relevance_score": 0.75,
        "audio_format_hint": "talking_head",
        "visible_text_expected": True,
    }
    payload.update(overrides)
    return payload


def write_json(path: Path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def snapshot(candidate_id: str, rank: int):
    prefix = f"{rank:03d}_{candidate_id}"
    return {
        "candidate_id": candidate_id,
        "rank": rank,
        "prefix": prefix,
        "artifacts": {
            "shootable_angles": {"path": f"data/{prefix}_shootable_angles.json"},
        },
    }


def angles(prefix: str):
    return {
        "status": "completed",
        "angles": [
            {
                "angle_title": f"{prefix} Daily Digestive Check",
                "hook": "Ask what changed after meals.",
                "format": "Talking-head explainer",
                "recommendation": "Convert the discomfort moment into routine support.",
                "recommended_because": "It is the clearest low-lift way to turn the source tension into a Nattome retail education moment.",
                "product_fit": "DH for daily digestive maintenance and routine support.",
                "cta": "Ask for Nattome DH at your nearest pharmacy if you want daily digestive support.",
            },
            {
                "angle_title": f"{prefix} Claim-Safe Overlay",
                "hook": "Turn the source tension into a safer question.",
                "format": "Text-led explainer",
                "recommendation": "Keep the tension, remove outcome promises.",
            },
            {
                "angle_title": f"{prefix} Voiceover Routine",
                "hook": "Use a calm routine opener.",
                "format": "Voiceover with simple B-roll",
                "recommendation": "Borrow the pacing while rewriting for Nattome.",
            },
        ],
    }


def soft_close_angles(prefix: str):
    payload = angles(prefix)
    payload["angles"][0] = {
        "angle_title": f"{prefix} Calm After-Meal Routine",
        "hook": "Start with the moment your stomach feels heavy after makan.",
        "format": "Voiceover routine",
        "recommendation": "Use a gentle routine story instead of a hard product sell.",
        "recommended_because": "It fits a softer routine concept where a direct CTA would feel too salesy.",
        "soft_close": "Try one small after-meal routine first and see what feels comfortable for you.",
    }
    return payload


def complete_gemini_evidence():
    return {
        "status": "completed",
        "model": "gemini-2.5-flash",
        "visual_observations": [{"timestamp_seconds": 0.5, "observation": "Creator points at stomach"}],
        "visible_text": [{"timestamp_seconds": 0.8, "text": "Bloated after meals?"}],
        "spoken_content": [
            {
                "start_seconds": 0,
                "end_seconds": 2,
                "text": "Here is a gentle routine for digestion support",
            }
        ],
        "audio_cues": [{"timestamp_seconds": 0, "cue": "calm talking-head voiceover"}],
        "hook_evidence": [{"timestamp_seconds": 0.5, "evidence": "problem question opens the video"}],
        "claim_evidence": [{"timestamp_seconds": 1.2, "text": "supports digestion"}],
        "missing_evidence": [],
    }


class FakeGeminiAdapter:
    def analyze_source_video(self, source_video_path, candidate_context):
        return complete_gemini_evidence()


class Top5CreativeReportTest(unittest.TestCase):
    def test_renderer_writes_base_report_contract_without_removed_sections(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "run"
            (run_folder / "data").mkdir(parents=True)
            output_root = Path(temp_dir) / "outputs"
            candidates = [
                candidate(Path(temp_dir), 1, id="rank-1", rank=1),
                candidate(Path(temp_dir), 2, id="rank-2", rank=2),
                candidate(Path(temp_dir), 3, id="rank-3", rank=3),
                candidate(Path(temp_dir), 4, id="rank-4", rank=4),
                candidate(Path(temp_dir), 5, id="rank-5", rank=5),
                candidate(Path(temp_dir), 6, id="rank-6", rank=6),
            ]
            selected_batch = {
                "selected_at": "2026-05-07T08:00:00Z",
                "selected_candidates": list(reversed(candidates)),
            }
            bundles = []
            for item in candidates:
                bundle = snapshot(item["id"], item["rank"])
                bundles.append(bundle)
                write_json(
                    run_folder / bundle["artifacts"]["shootable_angles"]["path"],
                    angles(item["id"]),
                )
            evidence_index = {"bundle_count": len(bundles), "bundles": list(reversed(bundles))}

            status = write_top5_creative_production_report(
                run_folder,
                output_root,
                selected_batch,
                evidence_index,
                "2026-05-07T08:00:00Z",
            )

            self.assertEqual(
                status["path"],
                "reports/2026-05-07/top5_creative_production_report_2026-05-07.md",
            )
            report = (output_root / status["path"]).read_text(encoding="utf-8")
            self.assertTrue(report.startswith("## 1. rank-1 Daily Digestive Check"))
            self.assertNotIn("What We Learned From These 5 Videos", report)
            self.assertLess(report.index("## 1. rank-1 Daily Digestive Check"), report.index("## 2. rank-2 Daily Digestive Check"))
            self.assertNotIn("rank-6", report)
            self.assertIn("- Creator: creator1", report)
            self.assertIn("- Source video: https://www.tiktok.com/@creator1/video/1", report)
            self.assertIn("- Views: 100001", report)
            self.assertIn("- Likes: 10001", report)
            self.assertIn("- Comments: 501", report)
            self.assertIn("- Shares: 701", report)
            self.assertEqual(report.count("### Inspiration Pattern"), 5)
            self.assertEqual(report.count("### Why This Works For Nattome Content"), 5)
            self.assertEqual(report.count("| Concept | Hook | Format | Why it works |"), 5)
            self.assertNotIn("Executive Summary", report)
            self.assertNotIn("Top Priority", report)
            self.assertNotIn("Product Theme", report)
            self.assertNotIn("thumbnail", report.lower())
            self.assertNotIn("screenshot", report.lower())
            self.assertNotIn("Original Source Hook", report)
            self.assertNotIn("Full Caption", report)
            self.assertNotIn("Claims Guardrail Bank", report)
            self.assertNotIn("selected_at", report)
            self.assertNotIn("selection_score", report)

    def test_completed_run_writes_dated_top5_report_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            candidates_path = temp_path / "candidates.json"
            candidates_path.write_text(
                json.dumps({"top": [candidate(temp_path, index) for index in range(1, 6)]}),
                encoding="utf-8",
            )
            output_root = temp_path / "outputs"

            create_run(
                Namespace(
                    mode="daily",
                    batch_size=None,
                    runs_dir=temp_path / "runs",
                    outputs_dir=output_root,
                    config=None,
                    candidates=candidates_path,
                    timestamp="2026-05-07T08:00:00Z",
                    gemini_adapter=FakeGeminiAdapter(),
                )
            )

            report_path = (
                output_root
                / "reports"
                / "2026-05-07"
                / "20260507T080000Z_daily"
                / "top5_creative_production_report_2026-05-07.md"
            )
            self.assertTrue(report_path.is_file())
            report = report_path.read_text(encoding="utf-8")
            self.assertTrue(report.startswith("## 1. Digestive Comfort Routine Check"))
            self.assertNotIn("What We Learned From These 5 Videos", report)
            self.assertEqual(report.count("### Source Reference"), 5)

    def test_recommended_shoot_gets_the_only_full_script_with_cta_ending(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "run"
            (run_folder / "data").mkdir(parents=True)
            output_root = Path(temp_dir) / "outputs"
            candidates = [candidate(Path(temp_dir), 1, id="rank-1", rank=1)]
            selected_batch = {
                "selected_at": "2026-05-07T08:00:00Z",
                "selected_candidates": candidates,
            }
            bundle = snapshot("rank-1", 1)
            write_json(
                run_folder / bundle["artifacts"]["shootable_angles"]["path"],
                angles("rank-1"),
            )
            evidence_index = {"bundle_count": 1, "bundles": [bundle]}

            status = write_top5_creative_production_report(
                run_folder,
                output_root,
                selected_batch,
                evidence_index,
                "2026-05-07T08:00:00Z",
            )

            report = (output_root / status["path"]).read_text(encoding="utf-8")
            self.assertEqual(report.count("### Recommended Shoot"), 1)
            self.assertIn("Recommended because: It is the clearest low-lift way", report)
            self.assertIn("Hook: Ask what changed after meals.", report)
            self.assertEqual(report.count("| Time | Scene | On-screen text | Exact line |"), 1)
            self.assertIn("| 22-30s | Close | Daily support, simple choice | Ask for Nattome DH at your nearest pharmacy if you want daily digestive support. |", report)
            self.assertIn("| rank-1 Claim-Safe Overlay | Turn the source tension into a safer question. | Text-led explainer |", report)
            self.assertNotIn("#### rank-1 Claim-Safe Overlay", report)

    def test_recommended_shoot_script_can_use_soft_close_ending(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "run"
            (run_folder / "data").mkdir(parents=True)
            output_root = Path(temp_dir) / "outputs"
            candidates = [candidate(Path(temp_dir), 1, id="rank-1", rank=1)]
            selected_batch = {
                "selected_at": "2026-05-07T08:00:00Z",
                "selected_candidates": candidates,
            }
            bundle = snapshot("rank-1", 1)
            write_json(
                run_folder / bundle["artifacts"]["shootable_angles"]["path"],
                soft_close_angles("rank-1"),
            )
            evidence_index = {"bundle_count": 1, "bundles": [bundle]}

            status = write_top5_creative_production_report(
                run_folder,
                output_root,
                selected_batch,
                evidence_index,
                "2026-05-07T08:00:00Z",
            )

            report = (output_root / status["path"]).read_text(encoding="utf-8")
            self.assertEqual(report.count("### Recommended Shoot"), 1)
            self.assertIn("Recommended because: It fits a softer routine concept", report)
            self.assertIn("Hook: Start with the moment your stomach feels heavy after makan.", report)
            self.assertIn("| 14-22s | Routine proof | One small habit | Keep the story on one everyday habit, so the message feels helpful instead of salesy. |", report)
            self.assertIn("| 22-30s | Close | Small routine first | Try one small after-meal routine first and see what feels comfortable for you. |", report)
            self.assertNotIn("Ask for Nattome DH", report)
            self.assertNotIn("If Nattome fits this concept", report)


if __name__ == "__main__":
    unittest.main()
