import json
import os
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from batch_analysis.run import create_run


WORKSPACE = Path(__file__).resolve().parents[1]
SCRIPT = WORKSPACE / "scripts" / "run_batch_analysis.py"


def write_candidates(temp_path, candidates):
    candidates_path = temp_path / "candidates.json"
    candidates_path.write_text(json.dumps({"top": candidates}), encoding="utf-8")
    return candidates_path


def candidate(temp_path, **overrides):
    source_video = temp_path / f"{overrides.get('id', 'video')}.mp4"
    source_video.write_bytes(b"fake mp4 bytes")
    payload = {
        "id": "two-layer-video",
        "url": "https://www.tiktok.com/@creator/video/twolayer",
        "video_download_url": str(source_video),
        "caption": "Bloating after meals gut health routine",
        "play_count": 120000,
        "like_count": 12000,
        "comment_count": 600,
        "share_count": 700,
        "created_at": "2026-05-05T00:00:00Z",
        "audio_format_hint": "talking_head",
        "visible_text_expected": True,
    }
    payload.update(overrides)
    return payload


class FakeGeminiAdapter:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def analyze_source_video(self, source_video_path, candidate_context):
        self.calls.append(
            {
                "source_video_path": source_video_path,
                "candidate_context": candidate_context,
            }
        )
        candidate_id = candidate_context["id"]
        if candidate_id in self.responses:
            return self.responses[candidate_id]
        return self.responses["default"]


def complete_gemini_evidence(**overrides):
    payload = {
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
                "language": "English",
                "confidence": 0.91,
            }
        ],
        "audio_cues": [{"timestamp_seconds": 0, "cue": "calm talking-head voiceover"}],
        "hook_evidence": [
            {"timestamp_seconds": 0.5, "evidence": "problem question opens the video"}
        ],
        "claim_evidence": [{"timestamp_seconds": 1.2, "text": "supports digestion"}],
        "missing_evidence": [],
    }
    payload.update(overrides)
    return payload


class FullBatchAnalysisTwoLayerCliTest(unittest.TestCase):
    def test_create_run_uses_two_layer_snapshots_gemini_adapter_and_manifest_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            candidates_path = write_candidates(temp_path, [candidate(temp_path)])
            adapter = FakeGeminiAdapter({"default": complete_gemini_evidence()})

            run_folder = create_run(
                Namespace(
                    mode="debug",
                    batch_size=1,
                    runs_dir=temp_path / "runs",
                    config=None,
                    candidates=candidates_path,
                    timestamp="2026-05-06T13:45:30Z",
                    ffmpeg_bin="unused-ffmpeg",
                    ocr_primary_bin="unused-ocr",
                    ocr_fallback_bin="unused-ocr",
                    transcription_bin="unused-transcriber",
                    gemini_adapter=adapter,
                )
            )

            self.assertEqual(len(adapter.calls), 1)
            self.assertEqual(
                adapter.calls[0]["source_video_path"],
                run_folder / "evidence" / "001_two-layer-video_source_video.mp4",
            )
            self.assertFalse((run_folder / "evidence_bundles").exists())
            self.assertFalse((run_folder / "batch_outputs").exists())
            self.assertTrue((run_folder / "run_manifest.json").is_file())
            self.assertTrue((run_folder / "batch_index.md").is_file())
            self.assertTrue((run_folder / "data" / "evidence_bundle_index.json").is_file())
            self.assertTrue((run_folder / "data" / "001_two-layer-video_gemini_evidence.json").is_file())
            self.assertTrue((run_folder / "reports" / "001_two-layer-video_video_evidence_report.md").is_file())
            self.assertTrue((run_folder / "data" / "001_two-layer-video_shootable_angles.json").is_file())
            self.assertTrue((run_folder / "reports" / "cross_video_pattern_summary.md").is_file())
            self.assertTrue((run_folder / "data" / "structured_batch_analysis.json").is_file())
            self.assertTrue((run_folder / "data" / "spreadsheet_summary.csv").is_file())
            self.assertTrue((run_folder / "logs" / "telegram_delivery.json").is_file())
            self.assertTrue((run_folder / "logs" / "evidence_artifact_cleanup.json").is_file())
            self.assertTrue((run_folder / "data" / "refinement_hooks.json").is_file())

            manifest = json.loads((run_folder / "run_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(
                next(phase for phase in manifest["phases"] if phase["name"] == "gemini_evidence")["status"],
                "completed",
            )
            self.assertIn("data/structured_batch_analysis.json", (run_folder / "batch_index.md").read_text(encoding="utf-8"))

    def test_cli_records_missing_gemini_credentials_without_legacy_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            candidates_path = write_candidates(temp_path, [candidate(temp_path, id="missing-gemini")])
            runs_dir = temp_path / "runs"
            env = os.environ.copy()
            env.pop("GEMINI_API_KEY", None)

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--mode",
                    "debug",
                    "--batch-size",
                    "1",
                    "--runs-dir",
                    str(runs_dir),
                    "--timestamp",
                    "2026-05-06T13:45:30Z",
                    "--candidates",
                    str(candidates_path),
                ],
                cwd=WORKSPACE,
                text=True,
                capture_output=True,
                env=env,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            run_folder = runs_dir / "20260506T134530Z_debug"
            self.assertFalse((run_folder / "evidence_bundles").exists())
            gemini = json.loads(
                (run_folder / "data" / "001_missing-gemini_gemini_evidence.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(gemini["status"], "missing_credentials")
            manifest = json.loads((run_folder / "run_manifest.json").read_text(encoding="utf-8"))
            gemini_phase = next(
                phase for phase in manifest["phases"] if phase["name"] == "gemini_evidence"
            )
            self.assertEqual(gemini_phase["status"], "failed")
            self.assertIn("missing-gemini", gemini_phase["notes"][0])

    def test_partial_run_failure_keeps_successful_and_failed_snapshot_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            candidates_path = write_candidates(
                temp_path,
                [
                    candidate(temp_path, id="completed-video", caption="Bloating after meals routine"),
                    candidate(temp_path, id="failed-video", caption="Acid reflux digestion support"),
                ],
            )
            adapter = FakeGeminiAdapter(
                {
                    "completed-video": complete_gemini_evidence(),
                    "failed-video": {
                        "status": "failed",
                        "model": "gemini-2.5-flash",
                        "reason": "Gemini timeout",
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
                    },
                }
            )

            run_folder = create_run(
                Namespace(
                    mode="quick",
                    batch_size=2,
                    runs_dir=temp_path / "runs",
                    config=None,
                    candidates=candidates_path,
                    timestamp="2026-05-06T13:45:30Z",
                    ffmpeg_bin="unused-ffmpeg",
                    ocr_primary_bin="unused-ocr",
                    ocr_fallback_bin="unused-ocr",
                    transcription_bin="unused-transcriber",
                    gemini_adapter=adapter,
                )
            )

            self.assertEqual(
                len(list((run_folder / "reports").glob("*_completed-video_video_evidence_report.md"))),
                1,
            )
            self.assertEqual(
                len(list((run_folder / "reports").glob("*_failed-video_video_evidence_report.md"))),
                1,
            )
            self.assertTrue((run_folder / "data" / "structured_batch_analysis.json").is_file())
            manifest = json.loads((run_folder / "run_manifest.json").read_text(encoding="utf-8"))
            gemini_phase = next(
                phase for phase in manifest["phases"] if phase["name"] == "gemini_evidence"
            )
            self.assertEqual(gemini_phase["status"], "failed")
            self.assertEqual(gemini_phase["notes"], ["failed-video: Gemini timeout"])


if __name__ == "__main__":
    unittest.main()
