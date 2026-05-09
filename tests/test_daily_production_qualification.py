import json
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from batch_analysis.run import create_run


WORKSPACE = Path(__file__).resolve().parents[1]
SCRIPT = WORKSPACE / "scripts" / "run_batch_analysis.py"


def candidate(temp_path: Path, candidate_id: str, index: int) -> dict:
    source_video = temp_path / f"{candidate_id}.mp4"
    source_video.write_bytes(b"fake mp4 bytes")
    return {
        "id": candidate_id,
        "url": f"https://www.tiktok.com/@creator/video/{candidate_id}",
        "video_download_url": str(source_video),
        "caption": "Bloating after meals gut health routine",
        "play_count": 120000 + index,
        "like_count": 12000,
        "comment_count": 600,
        "share_count": 700,
        "created_at": "2026-05-05T00:00:00Z",
        "audio_format_hint": "talking_head",
    }


def write_candidates(path: Path, candidates: list[dict]) -> Path:
    path.write_text(json.dumps({"top": candidates}), encoding="utf-8")
    return path


def complete_gemini_evidence() -> dict:
    return {
        "status": "completed",
        "model": "gemini-2.5-flash",
        "visual_observations": [
            {"timestamp_seconds": 0.5, "observation": "Creator points at stomach"}
        ],
        "visible_text": [{"timestamp_seconds": 0.8, "text": "Bloated after meals?"}],
        "spoken_content": [
            {
                "start_seconds": 0,
                "end_seconds": 2,
                "text": "Here is a gentle routine for digestion support",
            }
        ],
        "audio_cues": [{"timestamp_seconds": 0, "cue": "calm talking-head voiceover"}],
        "hook_evidence": [
            {"timestamp_seconds": 0.5, "evidence": "problem question opens the video"}
        ],
        "claim_evidence": [{"timestamp_seconds": 1.2, "text": "supports digestion"}],
        "missing_evidence": [],
    }


def failed_gemini_evidence(reason: str = "Gemini timeout") -> dict:
    return {
        "status": "failed",
        "model": "gemini-2.5-flash",
        "reason": reason,
        "visual_observations": [],
        "visible_text": [],
        "spoken_content": [],
        "audio_cues": [],
        "hook_evidence": [],
        "claim_evidence": [],
        "missing_evidence": [
            "visual_observations",
            "visible_text",
            "spoken_content",
            "audio_cues",
            "hook_evidence",
            "claim_evidence",
        ],
    }


class RecordingGeminiAdapter:
    def __init__(self, responses: dict[str, dict]):
        self.responses = responses
        self.calls: list[str] = []

    def analyze_source_video(self, source_video_path, candidate_context):
        candidate_id = candidate_context["id"]
        self.calls.append(candidate_id)
        return self.responses[candidate_id]


class DailyProductionQualificationTest(unittest.TestCase):
    def test_top3_are_analyzed_before_backfill_and_only_qualified_videos_reach_production(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            top3_path = write_candidates(
                temp_path / "daily_selection_top3.json",
                [
                    candidate(temp_path, "top-1", 1),
                    candidate(temp_path, "top-2", 2),
                    candidate(temp_path, "top-3", 3),
                ],
            )
            backfill_path = write_candidates(
                temp_path / "daily_backfill_candidates.json",
                [
                    candidate(temp_path, "backfill-1", 4),
                    candidate(temp_path, "backfill-2", 5),
                ],
            )
            adapter = RecordingGeminiAdapter(
                {
                    "top-1": complete_gemini_evidence(),
                    "top-2": failed_gemini_evidence(),
                    "top-3": complete_gemini_evidence(),
                    "backfill-1": complete_gemini_evidence(),
                    "backfill-2": complete_gemini_evidence(),
                }
            )

            run_folder = create_run(
                Namespace(
                    runs_dir=temp_path / "runs",
                    outputs_dir=temp_path / "outputs",
                    config=None,
                    candidates=top3_path,
                    backfill_candidates=backfill_path,
                    timestamp="2026-05-09T01:00:00Z",
                    gemini_adapter=adapter,
                )
            )

            self.assertEqual(adapter.calls, ["top-1", "top-2", "top-3", "backfill-1"])

            report_path = (
                temp_path
                / "outputs"
                / "reports"
                / "2026-05-09"
                / "20260509T010000Z_daily"
                / "production_creative_report_2026-05-09.md"
            )
            workbook_path = (
                temp_path
                / "outputs"
                / "reports"
                / "2026-05-09"
                / "20260509T010000Z_daily"
                / "production_angle_planning_sheet_2026-05-09.xlsx"
            )
            self.assertTrue(report_path.is_file())
            self.assertTrue(workbook_path.is_file())
            self.assertFalse(
                (
                    report_path.parent
                    / "top5_creative_production_report_2026-05-09.md"
                ).exists()
            )

            report = report_path.read_text(encoding="utf-8")
            self.assertIn("top-1", report)
            self.assertNotIn("top-2", report)
            self.assertIn("top-3", report)
            self.assertIn("backfill-1", report)
            self.assertNotIn("backfill-2", report)
            self.assertEqual(report.count("### Source Reference"), 3)
            self.assertIn("- Source selection rank: 3", report)

            structured = json.loads(
                (run_folder / "data" / "structured_batch_analysis.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                [item["id"] for item in structured["original_daily_selection"]["top"]],
                ["top-1", "top-2", "top-3"],
            )
            self.assertEqual(
                [item["id"] for item in structured["daily_backfill_candidates"]["top"]],
                ["backfill-1", "backfill-2"],
            )
            self.assertEqual(
                [item["id"] for item in structured["analyzed_candidates"]],
                ["top-1", "top-2", "top-3", "backfill-1"],
            )
            self.assertEqual(
                [item["id"] for item in structured["production_qualified_candidates"]],
                ["top-1", "top-3", "backfill-1"],
            )
            self.assertEqual(
                structured["cross_video_pattern_summary"]["source_video_count"],
                3,
            )

    def test_missing_gemini_credentials_skips_backfill_and_final_production_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            top3_path = write_candidates(
                temp_path / "daily_selection_top3.json",
                [candidate(temp_path, f"top-{index}", index) for index in range(1, 4)],
            )
            backfill_path = write_candidates(
                temp_path / "daily_backfill_candidates.json",
                [candidate(temp_path, "backfill-1", 4)],
            )
            adapter = RecordingGeminiAdapter(
                {
                    "top-1": failed_gemini_evidence(
                        "Gemini API key is missing; set GEMINI_API_KEY"
                    )
                    | {"status": "missing_credentials"},
                    "top-2": complete_gemini_evidence(),
                    "top-3": complete_gemini_evidence(),
                    "backfill-1": complete_gemini_evidence(),
                }
            )

            run_folder = create_run(
                Namespace(
                    runs_dir=temp_path / "runs",
                    outputs_dir=temp_path / "outputs",
                    config=None,
                    candidates=top3_path,
                    backfill_candidates=backfill_path,
                    timestamp="2026-05-09T01:00:00Z",
                    gemini_adapter=adapter,
                )
            )

            self.assertEqual(adapter.calls, ["top-1"])
            self.assertFalse(
                list((temp_path / "outputs").glob("**/production_creative_report_*.md"))
            )
            self.assertFalse(
                list((temp_path / "outputs").glob("**/production_angle_planning_sheet_*.xlsx"))
            )
            manifest = json.loads((run_folder / "run_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["outputs"]["final_outputs"], [])
            self.assertEqual(manifest["outputs"]["production_status"], "skipped")

    def test_public_cli_no_longer_exposes_mode_or_batch_size(self):
        help_result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            cwd=WORKSPACE,
            text=True,
            capture_output=True,
        )

        self.assertEqual(help_result.returncode, 0)
        self.assertNotIn("--mode", help_result.stdout)
        self.assertNotIn("--batch-size", help_result.stdout)
        self.assertIn("--backfill-candidates", help_result.stdout)

        rejected = subprocess.run(
            [sys.executable, str(SCRIPT), "--mode", "daily"],
            cwd=WORKSPACE,
            text=True,
            capture_output=True,
        )

        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("unrecognized arguments: --mode", rejected.stderr)


if __name__ == "__main__":
    unittest.main()
