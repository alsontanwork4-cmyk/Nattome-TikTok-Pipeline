import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
SCRIPT = WORKSPACE / "scripts" / "run_batch_analysis.py"


def load_pipeline_module():
    spec = importlib.util.spec_from_file_location("run_batch_analysis", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_cli(*args, cwd=WORKSPACE):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
    )


class BatchAnalysisRunCliTest(unittest.TestCase):
    def test_batch_analysis_run_is_callable_from_importable_module(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_dir = Path(temp_dir) / "runs"
            from batch_analysis.run import create_run

            run_folder = create_run(
                Namespace(
                    mode="debug",
                    batch_size=1,
                    runs_dir=runs_dir,
                    config=None,
                    candidates=None,
                    timestamp="2026-05-06T13:45:30Z",
                    ffmpeg_bin="ffmpeg",
                    ocr_primary_bin="paddleocr",
                    ocr_fallback_bin="tesseract",
                    transcription_bin="whisper",
                )
            )

            self.assertEqual(run_folder, runs_dir / "20260506T134530Z_debug")
            metadata = json.loads((run_folder / "run_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["run_timestamp"], "2026-05-06T13:45:30Z")
            self.assertTrue((run_folder / "batch_index.md").is_file())

    def test_batch_analysis_run_creates_timestamped_run_folder(self):
        with self.subTest("debug run folder"):
            with tempfile.TemporaryDirectory() as temp_dir:
                runs_dir = Path(temp_dir) / "runs"

                result = run_cli(
                    "--mode",
                    "debug",
                    "--batch-size",
                    "1",
                    "--runs-dir",
                    str(runs_dir),
                    "--timestamp",
                    "2026-05-06T13:45:30Z",
                )

                self.assertEqual(result.returncode, 0, result.stderr)

                run_folders = list(runs_dir.iterdir())
                self.assertEqual(len(run_folders), 1)
                run_folder = run_folders[0]
                self.assertRegex(run_folder.name, r"20260506T134530Z_debug$")

                metadata = json.loads((run_folder / "run_metadata.json").read_text(encoding="utf-8"))
                self.assertEqual(metadata["run_timestamp"], "2026-05-06T13:45:30Z")
                self.assertEqual(metadata["mode"], "debug")
                self.assertEqual(metadata["requested_batch_size"], 1)
                self.assertEqual(metadata["configuration"]["outputs"]["markdown"], "batch_outputs/markdown")
                self.assertEqual(metadata["implementation_status"]["video_download"], "not_implemented")
                self.assertEqual(metadata["implementation_status"]["ocr"], "not_implemented")
                self.assertEqual(metadata["implementation_status"]["transcription"], "not_implemented")

                expected_paths = [
                    "batch_outputs/markdown",
                    "batch_outputs/json",
                    "batch_outputs/spreadsheets",
                    "evidence_bundles",
                    "logs",
                ]
                for relative_path in expected_paths:
                    self.assertTrue((run_folder / relative_path).is_dir(), relative_path)

                self.assertTrue(
                    (run_folder / "batch_index.md").read_text(encoding="utf-8").startswith(
                        "# Batch Analysis Run"
                    )
                )
                self.assertIn(str(run_folder), result.stdout)

    def test_missing_explicit_config_fails_without_creating_run_folder(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runs_dir = temp_path / "runs"
            missing_config = temp_path / "missing.json"

            result = run_cli(
                "--runs-dir",
                str(runs_dir),
                "--config",
                str(missing_config),
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("required config file not found", result.stderr)
            self.assertFalse(runs_dir.exists())

    def test_candidates_are_filtered_ranked_and_written_to_run_folder(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runs_dir = temp_path / "runs"
            candidates_path = temp_path / "candidates.json"
            candidates_path.write_text(
                json.dumps(
                    {
                        "generated_at": "2026-05-06T00:00:00Z",
                        "top": [
                            {
                                "id": "low-views",
                                "url": "https://www.tiktok.com/@creator/video/lowviews",
                                "caption": "Gut health routine",
                                "play_count": 9999,
                                "like_count": 900,
                                "comment_count": 10,
                                "share_count": 10,
                                "created_at": "2026-05-05T00:00:00Z",
                            },
                            {
                                "id": "too-old",
                                "url": "https://www.tiktok.com/@creator/video/tooold",
                                "caption": "Acid reflux tips",
                                "play_count": 50000,
                                "like_count": 5000,
                                "comment_count": 200,
                                "share_count": 200,
                                "created_at": "2026-03-01T00:00:00Z",
                            },
                            {
                                "id": "weak-engagement",
                                "url": "https://www.tiktok.com/@creator/video/weak",
                                "caption": "Bloating after meals",
                                "play_count": 100000,
                                "like_count": 1000,
                                "comment_count": 20,
                                "share_count": 20,
                                "created_at": "2026-05-05T00:00:00Z",
                            },
                            {
                                "id": "missing-link",
                                "url": "",
                                "caption": "Digestive health",
                                "play_count": 80000,
                                "like_count": 8000,
                                "comment_count": 300,
                                "share_count": 200,
                                "created_at": "2026-05-05T00:00:00Z",
                            },
                            {
                                "id": "good-relevant",
                                "url": "https://www.tiktok.com/@creator/video/goodrelevant",
                                "caption": "Acid reflux and bloating routine for gut health",
                                "play_count": 90000,
                                "like_count": 7000,
                                "comment_count": 300,
                                "share_count": 600,
                                "created_at": "2026-05-05T00:00:00Z",
                            },
                            {
                                "id": "good-higher-views-less-relevant",
                                "url": "https://www.tiktok.com/@creator/video/highviews",
                                "caption": "Morning recipe with peas",
                                "play_count": 300000,
                                "like_count": 9000,
                                "comment_count": 500,
                                "share_count": 500,
                                "created_at": "2026-05-05T00:00:00Z",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = run_cli(
                "--mode",
                "quick",
                "--batch-size",
                "2",
                "--runs-dir",
                str(runs_dir),
                "--timestamp",
                "2026-05-06T13:45:30Z",
                "--candidates",
                str(candidates_path),
            )

            self.assertEqual(result.returncode, 0, result.stderr)

            run_folder = runs_dir / "20260506T134530Z_quick"
            selected = json.loads(
                (run_folder / "batch_outputs" / "json" / "selected_batch.json").read_text(
                    encoding="utf-8"
                )
            )
            selected_ids = [candidate["id"] for candidate in selected["selected_candidates"]]
            self.assertEqual(
                selected_ids,
                ["good-relevant", "good-higher-views-less-relevant"],
            )

            excluded = {item["id"]: item["reason"] for item in selected["excluded_candidates"]}
            self.assertIn("below minimum views", excluded["low-views"])
            self.assertIn("older than 30 days", excluded["too-old"])
            self.assertIn("below minimum weighted engagement rate", excluded["weak-engagement"])
            self.assertIn("missing usable TikTok link", excluded["missing-link"])

            preview = (
                run_folder / "batch_outputs" / "markdown" / "selected_batch.md"
            ).read_text(encoding="utf-8")
            self.assertIn("good-relevant", preview)
            self.assertIn("good-higher-views-less-relevant", preview)

            metadata = json.loads((run_folder / "run_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["implementation_status"]["candidate_selection"], "implemented")

    def test_selected_candidates_get_evidence_bundles_with_download_status(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runs_dir = temp_path / "runs"
            source_video = temp_path / "source.mp4"
            source_video.write_bytes(b"fake mp4 bytes")
            candidates_path = temp_path / "candidates.json"
            candidates_path.write_text(
                json.dumps(
                    {
                        "top": [
                            {
                                "id": "with-video",
                                "url": "https://www.tiktok.com/@creator/video/withvideo",
                                "video_download_url": str(source_video),
                                "caption": "Gut health and bloating routine",
                                "play_count": 50000,
                                "like_count": 6000,
                                "comment_count": 200,
                                "share_count": 250,
                                "created_at": "2026-05-05T00:00:00Z",
                            },
                            {
                                "id": "missing-video",
                                "url": "https://www.tiktok.com/@creator/video/missingvideo",
                                "caption": "Acid reflux stomach tip",
                                "play_count": 45000,
                                "like_count": 4000,
                                "comment_count": 100,
                                "share_count": 120,
                                "created_at": "2026-05-05T00:00:00Z",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = run_cli(
                "--mode",
                "quick",
                "--batch-size",
                "2",
                "--runs-dir",
                str(runs_dir),
                "--timestamp",
                "2026-05-06T13:45:30Z",
                "--candidates",
                str(candidates_path),
            )

            self.assertEqual(result.returncode, 0, result.stderr)

            run_folder = runs_dir / "20260506T134530Z_quick"
            evidence_index = json.loads(
                (run_folder / "evidence_bundles" / "index.json").read_text(encoding="utf-8")
            )
            self.assertEqual(evidence_index["bundle_count"], 2)

            with_video = next(
                bundle for bundle in evidence_index["bundles"] if bundle["candidate_id"] == "with-video"
            )
            self.assertEqual(with_video["original_tiktok_url"], "https://www.tiktok.com/@creator/video/withvideo")
            self.assertTrue(with_video["artifacts"]["source_video"]["exists"])

            with_video_folder = run_folder / with_video["bundle_folder"]
            self.assertEqual(
                (with_video_folder / "artifacts" / "source_video.mp4").read_bytes(),
                b"fake mp4 bytes",
            )
            source_metadata = json.loads(
                (with_video_folder / "source_metadata.json").read_text(encoding="utf-8")
            )
            self.assertEqual(source_metadata["id"], "with-video")
            self.assertEqual(source_metadata["url"], "https://www.tiktok.com/@creator/video/withvideo")

            missing_video = next(
                bundle for bundle in evidence_index["bundles"] if bundle["candidate_id"] == "missing-video"
            )
            self.assertFalse(missing_video["artifacts"]["source_video"]["exists"])
            self.assertIn("no downloadable video source", missing_video["download_status"]["reason"])
            self.assertEqual(
                missing_video["original_tiktok_url"],
                "https://www.tiktok.com/@creator/video/missingvideo",
            )

            metadata = json.loads((run_folder / "run_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["implementation_status"]["video_download"], "implemented")

    def test_downloaded_videos_get_hybrid_timeline_frame_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runs_dir = temp_path / "runs"
            source_video = temp_path / "source.mp4"
            source_video.write_bytes(b"fake mp4 bytes")
            fake_ffmpeg = self.write_fake_ffmpeg(temp_path)
            candidates_path = temp_path / "candidates.json"
            candidates_path.write_text(
                json.dumps(
                    {
                        "top": [
                            {
                                "id": "timeline-video",
                                "url": "https://www.tiktok.com/@creator/video/timeline",
                                "video_download_url": str(source_video),
                                "caption": "Gut health and bloating routine",
                                "play_count": 50000,
                                "like_count": 6000,
                                "comment_count": 200,
                                "share_count": 250,
                                "created_at": "2026-05-05T00:00:00Z",
                                "duration_seconds": 4.2,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = run_cli(
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
                "--ffmpeg-bin",
                str(fake_ffmpeg),
            )

            self.assertEqual(result.returncode, 0, result.stderr)

            run_folder = runs_dir / "20260506T134530Z_debug"
            evidence_index = json.loads(
                (run_folder / "evidence_bundles" / "index.json").read_text(encoding="utf-8")
            )
            bundle = evidence_index["bundles"][0]
            self.assertTrue(bundle["artifacts"]["hybrid_timeline"]["exists"])
            self.assertEqual(bundle["artifacts"]["hybrid_timeline"]["frame_count"], 8)

            bundle_folder = run_folder / bundle["bundle_folder"]
            timeline = json.loads(
                (bundle_folder / "hybrid_timeline.json").read_text(encoding="utf-8")
            )
            self.assertEqual(timeline["status"], "extracted")
            self.assertEqual(timeline["source_video"], "artifacts/source_video.mp4")
            self.assertEqual(
                [frame["timestamp_seconds"] for frame in timeline["frames"]],
                [0, 0.5, 1, 1.5, 2, 2.5, 3, 4],
            )
            self.assertEqual(timeline["frames"][0]["sampling_reason"], "baseline_one_second")
            self.assertEqual(timeline["frames"][1]["sampling_reason"], "hook_first_three_seconds")
            for frame in timeline["frames"]:
                self.assertTrue((bundle_folder / frame["frame_path"]).is_file(), frame)

            self.assertEqual(
                timeline["extension_points"],
                {
                    "text_change_samples": "not_implemented",
                    "scene_change_samples": "not_implemented",
                },
            )
            metadata = json.loads((run_folder / "run_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["implementation_status"]["hybrid_timeline"], "implemented")

    def test_extracted_timeline_frames_get_timestamped_ocr_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runs_dir = temp_path / "runs"
            source_video = temp_path / "source.mp4"
            source_video.write_bytes(b"fake mp4 bytes")
            fake_ffmpeg = self.write_fake_ffmpeg(temp_path)
            fake_ocr = self.write_fake_ocr(temp_path, "English Malay Chinese mixed text")
            candidates_path = temp_path / "candidates.json"
            candidates_path.write_text(
                json.dumps(
                    {
                        "top": [
                            {
                                "id": "ocr-video",
                                "url": "https://www.tiktok.com/@creator/video/ocr",
                                "video_download_url": str(source_video),
                                "caption": "Gut health and bloating routine",
                                "play_count": 50000,
                                "like_count": 6000,
                                "comment_count": 200,
                                "share_count": 250,
                                "created_at": "2026-05-05T00:00:00Z",
                                "duration_seconds": 1.2,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = run_cli(
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
                "--ffmpeg-bin",
                str(fake_ffmpeg),
                "--ocr-primary-bin",
                str(fake_ocr),
            )

            self.assertEqual(result.returncode, 0, result.stderr)

            run_folder = runs_dir / "20260506T134530Z_debug"
            evidence_index = json.loads(
                (run_folder / "evidence_bundles" / "index.json").read_text(encoding="utf-8")
            )
            bundle = evidence_index["bundles"][0]
            self.assertTrue(bundle["artifacts"]["ocr_evidence"]["exists"])

            bundle_folder = run_folder / bundle["bundle_folder"]
            ocr = json.loads((bundle_folder / "ocr_evidence.json").read_text(encoding="utf-8"))
            self.assertEqual(ocr["status"], "completed")
            self.assertEqual(ocr["engine"]["selected"], "paddleocr")
            self.assertEqual(
                ocr["languages_requested"],
                ["English", "Malay", "Simplified Chinese", "Traditional Chinese", "mixed-language text"],
            )
            self.assertEqual(
                [(item["timestamp_seconds"], item["frame_path"]) for item in ocr["frames"]],
                [
                    (0, "artifacts/frames/frame_000000ms.jpg"),
                    (0.5, "artifacts/frames/frame_000500ms.jpg"),
                    (1, "artifacts/frames/frame_001000ms.jpg"),
                ],
            )
            self.assertTrue(all(item["ocr_text"] == "English Malay Chinese mixed text" for item in ocr["frames"]))
            self.assertEqual(ocr["summary"]["text_frame_count"], 3)
            self.assertEqual(
                ocr["summary"]["combined_text"],
                "English Malay Chinese mixed text\nEnglish Malay Chinese mixed text\nEnglish Malay Chinese mixed text",
            )

            metadata = json.loads((run_folder / "run_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["implementation_status"]["ocr"], "implemented")

    def test_missing_ocr_tooling_is_recorded_as_setup_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runs_dir = temp_path / "runs"
            source_video = temp_path / "source.mp4"
            source_video.write_bytes(b"fake mp4 bytes")
            fake_ffmpeg = self.write_fake_ffmpeg(temp_path)
            candidates_path = temp_path / "candidates.json"
            candidates_path.write_text(
                json.dumps(
                    {
                        "top": [
                            {
                                "id": "missing-ocr-video",
                                "url": "https://www.tiktok.com/@creator/video/missingocr",
                                "video_download_url": str(source_video),
                                "caption": "Gut health and bloating routine",
                                "play_count": 50000,
                                "like_count": 6000,
                                "comment_count": 200,
                                "share_count": 250,
                                "created_at": "2026-05-05T00:00:00Z",
                                "duration_seconds": 1,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = run_cli(
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
                "--ffmpeg-bin",
                str(fake_ffmpeg),
                "--ocr-primary-bin",
                str(temp_path / "missing-paddleocr"),
                "--ocr-fallback-bin",
                str(temp_path / "missing-tesseract"),
            )

            self.assertEqual(result.returncode, 0, result.stderr)

            run_folder = runs_dir / "20260506T134530Z_debug"
            evidence_index = json.loads(
                (run_folder / "evidence_bundles" / "index.json").read_text(encoding="utf-8")
            )
            bundle = evidence_index["bundles"][0]
            self.assertFalse(bundle["artifacts"]["ocr_evidence"]["exists"])
            self.assertEqual(bundle["artifacts"]["ocr_evidence"]["status"], "failed")

            bundle_folder = run_folder / bundle["bundle_folder"]
            ocr = json.loads((bundle_folder / "ocr_evidence.json").read_text(encoding="utf-8"))
            self.assertEqual(ocr["status"], "failed")
            self.assertIn("OCR tooling failed or is missing", ocr["reason"])
            self.assertIn("PaddleOCR", ocr["reason"])
            self.assertIn("Tesseract", ocr["reason"])

    def test_downloaded_videos_get_timestamped_transcript_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runs_dir = temp_path / "runs"
            source_video = temp_path / "source.mp4"
            source_video.write_bytes(b"fake mp4 bytes")
            fake_ffmpeg = self.write_fake_ffmpeg(temp_path)
            fake_transcriber = self.write_fake_transcriber(
                temp_path,
                {
                    "language": "code-mixed",
                    "segments": [
                        {
                            "start": 0.0,
                            "end": 1.2,
                            "text": "English Malay Chinese code mixed hook",
                            "confidence": 0.82,
                        }
                    ],
                },
            )
            candidates_path = temp_path / "candidates.json"
            candidates_path.write_text(
                json.dumps(
                    {
                        "top": [
                            {
                                "id": "transcript-video",
                                "url": "https://www.tiktok.com/@creator/video/transcript",
                                "video_download_url": str(source_video),
                                "caption": "Gut health and bloating routine",
                                "play_count": 50000,
                                "like_count": 6000,
                                "comment_count": 200,
                                "share_count": 250,
                                "created_at": "2026-05-05T00:00:00Z",
                                "duration_seconds": 1,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = run_cli(
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
                "--ffmpeg-bin",
                str(fake_ffmpeg),
                "--transcription-bin",
                str(fake_transcriber),
            )

            self.assertEqual(result.returncode, 0, result.stderr)

            run_folder = runs_dir / "20260506T134530Z_debug"
            evidence_index = json.loads(
                (run_folder / "evidence_bundles" / "index.json").read_text(encoding="utf-8")
            )
            bundle = evidence_index["bundles"][0]
            self.assertTrue(bundle["artifacts"]["audio"]["exists"])
            self.assertTrue(bundle["artifacts"]["transcript_evidence"]["exists"])

            bundle_folder = run_folder / bundle["bundle_folder"]
            transcript = json.loads(
                (bundle_folder / "transcript_evidence.json").read_text(encoding="utf-8")
            )
            self.assertEqual(transcript["status"], "completed")
            self.assertEqual(transcript["audio_artifact"], "artifacts/audio/source_audio.wav")
            self.assertEqual(
                transcript["languages_requested"],
                ["English", "Malay", "Mandarin Chinese", "code-mixed English-Malay-Chinese"],
            )
            self.assertEqual(
                transcript["segments"],
                [
                    {
                        "start_seconds": 0.0,
                        "end_seconds": 1.2,
                        "text": "English Malay Chinese code mixed hook",
                        "confidence": 0.82,
                        "language": "code-mixed",
                    }
                ],
            )
            self.assertEqual(transcript["summary"]["combined_text"], "English Malay Chinese code mixed hook")
            self.assertTrue(transcript["summary"]["has_confidence_metadata"])
            self.assertTrue((bundle_folder / "artifacts" / "audio" / "source_audio.wav").is_file())

            metadata = json.loads((run_folder / "run_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["implementation_status"]["transcription"], "implemented")

    def test_missing_transcription_tooling_is_recorded_as_setup_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runs_dir = temp_path / "runs"
            source_video = temp_path / "source.mp4"
            source_video.write_bytes(b"fake mp4 bytes")
            fake_ffmpeg = self.write_fake_ffmpeg(temp_path)
            candidates_path = temp_path / "candidates.json"
            candidates_path.write_text(
                json.dumps(
                    {
                        "top": [
                            {
                                "id": "missing-transcript-video",
                                "url": "https://www.tiktok.com/@creator/video/missingtranscript",
                                "video_download_url": str(source_video),
                                "caption": "Gut health and bloating routine",
                                "play_count": 50000,
                                "like_count": 6000,
                                "comment_count": 200,
                                "share_count": 250,
                                "created_at": "2026-05-05T00:00:00Z",
                                "duration_seconds": 1,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = run_cli(
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
                "--ffmpeg-bin",
                str(fake_ffmpeg),
                "--transcription-bin",
                str(temp_path / "missing-whisper"),
            )

            self.assertEqual(result.returncode, 0, result.stderr)

            run_folder = runs_dir / "20260506T134530Z_debug"
            evidence_index = json.loads(
                (run_folder / "evidence_bundles" / "index.json").read_text(encoding="utf-8")
            )
            bundle = evidence_index["bundles"][0]
            self.assertTrue(bundle["artifacts"]["audio"]["exists"])
            self.assertFalse(bundle["artifacts"]["transcript_evidence"]["exists"])
            self.assertEqual(bundle["artifacts"]["transcript_evidence"]["status"], "failed")

            bundle_folder = run_folder / bundle["bundle_folder"]
            transcript = json.loads(
                (bundle_folder / "transcript_evidence.json").read_text(encoding="utf-8")
            )
            self.assertEqual(transcript["status"], "failed")
            self.assertIn("Transcription tooling failed or is missing", transcript["reason"])
            self.assertIn("Whisper-style", transcript["reason"])

    def test_every_bundle_gets_baseline_audio_analysis(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runs_dir = temp_path / "runs"
            source_video = temp_path / "source.mp4"
            source_video.write_bytes(b"fake mp4 bytes")
            fake_ffmpeg = self.write_fake_ffmpeg(temp_path)
            fake_transcriber = self.write_fake_transcriber(
                temp_path,
                {
                    "language": "en",
                    "segments": [
                        {
                            "start": 0.0,
                            "end": 2.0,
                            "text": "If you feel bloated after meals try this",
                            "confidence": 0.9,
                        }
                    ],
                },
            )
            candidates_path = temp_path / "candidates.json"
            candidates_path.write_text(
                json.dumps(
                    {
                        "top": [
                            {
                                "id": "audio-video",
                                "url": "https://www.tiktok.com/@creator/video/audio",
                                "video_download_url": str(source_video),
                                "caption": "Gut health and bloating routine",
                                "play_count": 50000,
                                "like_count": 6000,
                                "comment_count": 200,
                                "share_count": 250,
                                "created_at": "2026-05-05T00:00:00Z",
                                "duration_seconds": 2,
                                "sound_title": "Original sound - creator",
                                "audio_format_hint": "talking_head",
                                "audio_mood": "calm explainer",
                                "is_reused_sound": False,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = run_cli(
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
                "--ffmpeg-bin",
                str(fake_ffmpeg),
                "--transcription-bin",
                str(fake_transcriber),
            )

            self.assertEqual(result.returncode, 0, result.stderr)

            run_folder = runs_dir / "20260506T134530Z_debug"
            evidence_index = json.loads(
                (run_folder / "evidence_bundles" / "index.json").read_text(encoding="utf-8")
            )
            bundle = evidence_index["bundles"][0]
            self.assertTrue(bundle["artifacts"]["baseline_audio_analysis"]["exists"])

            bundle_folder = run_folder / bundle["bundle_folder"]
            analysis = json.loads(
                (bundle_folder / "baseline_audio_analysis.json").read_text(encoding="utf-8")
            )
            self.assertEqual(analysis["status"], "completed")
            self.assertEqual(analysis["sound"]["title"], "Original sound - creator")
            self.assertFalse(analysis["sound"]["is_reused_sound"])
            self.assertEqual(analysis["audio_format"], "talking_head")
            self.assertEqual(analysis["mood"], "calm explainer")
            self.assertIn("spoken hook", analysis["hook_support"])
            self.assertEqual(analysis["nattome_recommendation"]["action"], "adapt")
            self.assertEqual(analysis["deep_sound_research"], {"status": "not_implemented"})

            metadata = json.loads((run_folder / "run_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(
                metadata["implementation_status"]["audio_music_trend_analysis"],
                "implemented",
            )

    def test_each_bundle_gets_evidence_quality_and_manual_review_flags(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runs_dir = temp_path / "runs"
            source_video = temp_path / "source.mp4"
            source_video.write_bytes(b"fake mp4 bytes")
            fake_ffmpeg = self.write_fake_ffmpeg(temp_path)
            fake_ocr = self.write_fake_ocr(temp_path, "Visible gut health hook")
            fake_transcriber = self.write_fake_transcriber(
                temp_path,
                {
                    "segments": [
                        {
                            "start": 4.0,
                            "end": 6.0,
                            "text": "Digestive routine details after the hook",
                            "confidence": 0.62,
                        }
                    ],
                },
            )
            candidates_path = temp_path / "candidates.json"
            candidates_path.write_text(
                json.dumps(
                    {
                        "top": [
                            {
                                "id": "quality-medium",
                                "url": "https://www.tiktok.com/@creator/video/qualitymedium",
                                "video_download_url": str(source_video),
                                "caption": "Gut health and bloating routine",
                                "play_count": 50000,
                                "like_count": 6000,
                                "comment_count": 200,
                                "share_count": 250,
                                "created_at": "2026-05-05T00:00:00Z",
                                "duration_seconds": 1,
                                "visible_text_expected": True,
                            },
                            {
                                "id": "quality-low",
                                "url": "https://www.tiktok.com/@creator/video/qualitylow",
                                "caption": "Acid reflux stomach tip",
                                "play_count": 45000,
                                "like_count": 4000,
                                "comment_count": 100,
                                "share_count": 120,
                                "created_at": "2026-05-05T00:00:00Z",
                                "visible_text_expected": True,
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = run_cli(
                "--mode",
                "quick",
                "--batch-size",
                "2",
                "--runs-dir",
                str(runs_dir),
                "--timestamp",
                "2026-05-06T13:45:30Z",
                "--candidates",
                str(candidates_path),
                "--ffmpeg-bin",
                str(fake_ffmpeg),
                "--ocr-primary-bin",
                str(fake_ocr),
                "--transcription-bin",
                str(fake_transcriber),
            )

            self.assertEqual(result.returncode, 0, result.stderr)

            run_folder = runs_dir / "20260506T134530Z_quick"
            evidence_index = json.loads(
                (run_folder / "evidence_bundles" / "index.json").read_text(encoding="utf-8")
            )
            by_id = {bundle["candidate_id"]: bundle for bundle in evidence_index["bundles"]}

            medium_bundle = by_id["quality-medium"]
            self.assertEqual(
                medium_bundle["artifacts"]["evidence_quality"]["score"],
                "medium",
            )
            self.assertTrue(medium_bundle["artifacts"]["evidence_quality"]["manual_review_required"])
            medium_quality = json.loads(
                (
                    run_folder
                    / medium_bundle["bundle_folder"]
                    / "evidence_quality.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(medium_quality["evidence_quality_score"]["level"], "medium")
            self.assertIn("language detection failed", medium_quality["evidence_quality_score"]["reason"])
            self.assertIn(
                "transcript_language_detection_failed",
                medium_quality["manual_review_flag"]["reasons"],
            )

            low_bundle = by_id["quality-low"]
            self.assertEqual(low_bundle["artifacts"]["evidence_quality"]["score"], "low")
            self.assertTrue(low_bundle["artifacts"]["evidence_quality"]["manual_review_required"])
            low_quality = json.loads(
                (run_folder / low_bundle["bundle_folder"] / "evidence_quality.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(low_quality["evidence_quality_score"]["level"], "low")
            self.assertIn("video download failed", low_quality["evidence_quality_score"]["reason"])
            self.assertIn("ocr_failed_on_visible_text", low_quality["manual_review_flag"]["reasons"])
            self.assertIn(
                "first_three_second_hook_unclear",
                low_quality["manual_review_flag"]["reasons"],
            )

    def test_complete_bundle_gets_high_evidence_quality_without_manual_review(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runs_dir = temp_path / "runs"
            source_video = temp_path / "source.mp4"
            source_video.write_bytes(b"fake mp4 bytes")
            fake_ffmpeg = self.write_fake_ffmpeg(temp_path)
            fake_ocr = self.write_fake_ocr(temp_path, "Visible first three second hook")
            fake_transcriber = self.write_fake_transcriber(
                temp_path,
                {
                    "language": "en",
                    "segments": [
                        {
                            "start": 0.0,
                            "end": 2.0,
                            "text": "If you feel bloated after meals try this",
                            "confidence": 0.92,
                        }
                    ],
                },
            )
            candidates_path = temp_path / "candidates.json"
            candidates_path.write_text(
                json.dumps(
                    {
                        "top": [
                            {
                                "id": "quality-high",
                                "url": "https://www.tiktok.com/@creator/video/qualityhigh",
                                "video_download_url": str(source_video),
                                "caption": "Gut health and bloating routine",
                                "play_count": 50000,
                                "like_count": 6000,
                                "comment_count": 200,
                                "share_count": 250,
                                "created_at": "2026-05-05T00:00:00Z",
                                "duration_seconds": 1,
                                "visible_text_expected": True,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = run_cli(
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
                "--ffmpeg-bin",
                str(fake_ffmpeg),
                "--ocr-primary-bin",
                str(fake_ocr),
                "--transcription-bin",
                str(fake_transcriber),
            )

            self.assertEqual(result.returncode, 0, result.stderr)

            run_folder = runs_dir / "20260506T134530Z_debug"
            evidence_index = json.loads(
                (run_folder / "evidence_bundles" / "index.json").read_text(encoding="utf-8")
            )
            bundle = evidence_index["bundles"][0]
            self.assertEqual(bundle["artifacts"]["evidence_quality"]["score"], "high")
            self.assertFalse(bundle["artifacts"]["evidence_quality"]["manual_review_required"])

            quality = json.loads(
                (run_folder / bundle["bundle_folder"] / "evidence_quality.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(quality["evidence_quality_score"]["level"], "high")
            self.assertFalse(quality["manual_review_flag"]["required"])
            self.assertEqual(quality["manual_review_flag"]["reasons"], [])
            self.assertTrue(quality["checks"]["first_three_second_hook"]["clear"])

            metadata = json.loads((run_folder / "run_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["implementation_status"]["evidence_quality"], "implemented")

    def test_claim_safety_review_flags_unsafe_claims_with_guidance(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runs_dir = temp_path / "runs"
            source_video = temp_path / "source.mp4"
            source_video.write_bytes(b"fake mp4 bytes")
            fake_ffmpeg = self.write_fake_ffmpeg(temp_path)
            unsafe_claim_text = (
                "Cure acid reflux overnight with a 100% guaranteed detox cleanse. "
                "Prevents cancer, has zero side effects, doctor recommended, "
                "97% clinically proven, better than every competitor."
            )
            fake_ocr = self.write_fake_ocr(temp_path, unsafe_claim_text)
            fake_transcriber = self.write_fake_transcriber(
                temp_path,
                {
                    "language": "en",
                    "segments": [
                        {
                            "start": 0.0,
                            "end": 3.0,
                            "text": unsafe_claim_text,
                            "confidence": 0.91,
                        }
                    ],
                },
            )
            candidates_path = temp_path / "candidates.json"
            candidates_path.write_text(
                json.dumps(
                    {
                        "top": [
                            {
                                "id": "claim-safety",
                                "url": "https://www.tiktok.com/@creator/video/claimsafety",
                                "video_download_url": str(source_video),
                                "caption": "Gut health and bloating routine",
                                "play_count": 50000,
                                "like_count": 6000,
                                "comment_count": 200,
                                "share_count": 250,
                                "created_at": "2026-05-05T00:00:00Z",
                                "duration_seconds": 1,
                                "visible_text_expected": True,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = run_cli(
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
                "--ffmpeg-bin",
                str(fake_ffmpeg),
                "--ocr-primary-bin",
                str(fake_ocr),
                "--transcription-bin",
                str(fake_transcriber),
            )

            self.assertEqual(result.returncode, 0, result.stderr)

            run_folder = runs_dir / "20260506T134530Z_debug"
            evidence_index = json.loads(
                (run_folder / "evidence_bundles" / "index.json").read_text(encoding="utf-8")
            )
            bundle = evidence_index["bundles"][0]
            self.assertTrue(bundle["artifacts"]["claim_safety_review"]["exists"])
            self.assertEqual(bundle["artifacts"]["claim_safety_review"]["flagged_count"], 9)

            bundle_folder = run_folder / bundle["bundle_folder"]
            review = json.loads(
                (bundle_folder / "claim_safety_review.json").read_text(encoding="utf-8")
            )
            categories = {claim["category"] for claim in review["flagged_claims"]}
            self.assertEqual(
                categories,
                {
                    "cure_claim",
                    "guaranteed_outcome",
                    "one_night_fix",
                    "cancer_prevention",
                    "zero_side_effect",
                    "detox_or_cleanse",
                    "unverified_doctor_recommended",
                    "unsupported_clinical_percentage",
                    "aggressive_competitor_claim",
                },
            )
            for claim in review["flagged_claims"]:
                self.assertIn(claim["guidance"]["action"], {"reuse", "soften", "avoid", "reframe"})
                self.assertTrue(claim["guidance"]["reason"])
                self.assertTrue(claim["guidance"]["nattome_safe_language"])

            quality = json.loads(
                (bundle_folder / "evidence_quality.json").read_text(encoding="utf-8")
            )
            self.assertIn(
                "claim_safety_review_flagged_claims",
                quality["manual_review_flag"]["reasons"],
            )
            self.assertEqual(quality["checks"]["claim_uncertainty"]["status"], "flagged")

            metadata = json.loads((run_folder / "run_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["implementation_status"]["claim_safety_review"], "implemented")

    def test_each_bundle_gets_video_evidence_report_with_required_sections(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runs_dir = temp_path / "runs"
            source_video = temp_path / "source.mp4"
            source_video.write_bytes(b"fake mp4 bytes")
            fake_ffmpeg = self.write_fake_ffmpeg(temp_path)
            fake_ocr = self.write_fake_ocr(temp_path, "Bloating after meals hook")
            fake_transcriber = self.write_fake_transcriber(
                temp_path,
                {
                    "language": "en",
                    "segments": [
                        {
                            "start": 0.0,
                            "end": 2.0,
                            "text": "If you feel bloated after meals try this routine",
                            "confidence": 0.9,
                        }
                    ],
                },
            )
            candidates_path = temp_path / "candidates.json"
            candidates_path.write_text(
                json.dumps(
                    {
                        "top": [
                            {
                                "id": "report-video",
                                "url": "https://www.tiktok.com/@creator/video/report",
                                "video_download_url": str(source_video),
                                "caption": "Gut health and bloating routine",
                                "play_count": 50000,
                                "like_count": 6000,
                                "comment_count": 200,
                                "share_count": 250,
                                "created_at": "2026-05-05T00:00:00Z",
                                "duration_seconds": 1,
                                "visible_text_expected": True,
                                "audio_format_hint": "talking_head",
                            },
                            {
                                "id": "missing-report-video",
                                "url": "https://www.tiktok.com/@creator/video/missingreport",
                                "caption": "Acid reflux stomach tip",
                                "play_count": 45000,
                                "like_count": 4000,
                                "comment_count": 100,
                                "share_count": 120,
                                "created_at": "2026-05-05T00:00:00Z",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = run_cli(
                "--mode",
                "quick",
                "--batch-size",
                "2",
                "--runs-dir",
                str(runs_dir),
                "--timestamp",
                "2026-05-06T13:45:30Z",
                "--candidates",
                str(candidates_path),
                "--ffmpeg-bin",
                str(fake_ffmpeg),
                "--ocr-primary-bin",
                str(fake_ocr),
                "--transcription-bin",
                str(fake_transcriber),
            )

            self.assertEqual(result.returncode, 0, result.stderr)

            run_folder = runs_dir / "20260506T134530Z_quick"
            evidence_index = json.loads(
                (run_folder / "evidence_bundles" / "index.json").read_text(encoding="utf-8")
            )
            by_id = {bundle["candidate_id"]: bundle for bundle in evidence_index["bundles"]}
            report_bundle = by_id["report-video"]
            self.assertTrue(report_bundle["artifacts"]["video_evidence_report"]["exists"])

            report = (
                run_folder
                / report_bundle["bundle_folder"]
                / "video_evidence_report.md"
            ).read_text(encoding="utf-8")
            for section in [
                "## Video Reference",
                "## Executive Creative Read",
                "## First 3 Seconds Hook Audit",
                "## Hybrid Timeline",
                "## OCR Text Summary",
                "## Speech Transcript Summary",
                "## Audio/Music Trend Analysis",
                "## Virality Breakdown",
                "## Nattome POV",
                "## Shootable Angles",
                "## Claim Safety Review",
                "## Evidence Quality",
            ]:
                self.assertIn(section, report)
            self.assertIn("[Source TikTok](https://www.tiktok.com/@creator/video/report)", report)
            self.assertIn("`evidence_quality.json`", report)
            self.assertIn("Hook:", report)
            self.assertIn("Avatar:", report)
            self.assertIn("Format:", report)
            self.assertIn("Product tie-in:", report)
            self.assertIn("Script beats:", report)
            self.assertIn("CTA:", report)
            self.assertIn("Claim guardrails:", report)

            missing_bundle = by_id["missing-report-video"]
            missing_report = (
                run_folder
                / missing_bundle["bundle_folder"]
                / "video_evidence_report.md"
            ).read_text(encoding="utf-8")
            self.assertIn("Hybrid timeline evidence not available", missing_report)
            self.assertIn("This report does not claim video evidence was inspected", missing_report)

            metadata = json.loads((run_folder / "run_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["implementation_status"]["video_evidence_reports"], "implemented")

    def test_batch_run_gets_cross_video_pattern_summary_with_priority_scores(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runs_dir = temp_path / "runs"
            source_video = temp_path / "source.mp4"
            source_video.write_bytes(b"fake mp4 bytes")
            fake_ffmpeg = self.write_fake_ffmpeg(temp_path)
            fake_ocr = self.write_fake_ocr(temp_path, "Bloating after meals? Try a calmer routine")
            fake_transcriber = self.write_fake_transcriber(
                temp_path,
                {
                    "language": "en",
                    "segments": [
                        {
                            "start": 0.0,
                            "end": 2.0,
                            "text": "If you feel bloated after meals try this routine",
                            "confidence": 0.92,
                        }
                    ],
                },
            )
            candidates_path = temp_path / "candidates.json"
            candidates_path.write_text(
                json.dumps(
                    {
                        "top": [
                            {
                                "id": "bloating-routine",
                                "url": "https://www.tiktok.com/@creator/video/bloating",
                                "video_download_url": str(source_video),
                                "caption": "Bloating after meals gut health routine",
                                "play_count": 120000,
                                "like_count": 12000,
                                "comment_count": 600,
                                "share_count": 700,
                                "created_at": "2026-05-05T00:00:00Z",
                                "duration_seconds": 1,
                                "visible_text_expected": True,
                                "audio_format_hint": "talking_head",
                            },
                            {
                                "id": "reflux-tip",
                                "url": "https://www.tiktok.com/@creator/video/reflux",
                                "caption": "Acid reflux stomach tip",
                                "play_count": 80000,
                                "like_count": 6000,
                                "comment_count": 250,
                                "share_count": 400,
                                "created_at": "2026-05-05T00:00:00Z",
                                "audio_format_hint": "voiceover",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = run_cli(
                "--mode",
                "quick",
                "--batch-size",
                "2",
                "--runs-dir",
                str(runs_dir),
                "--timestamp",
                "2026-05-06T13:45:30Z",
                "--candidates",
                str(candidates_path),
                "--ffmpeg-bin",
                str(fake_ffmpeg),
                "--ocr-primary-bin",
                str(fake_ocr),
                "--transcription-bin",
                str(fake_transcriber),
            )

            self.assertEqual(result.returncode, 0, result.stderr)

            run_folder = runs_dir / "20260506T134530Z_quick"
            summary_markdown = (
                run_folder / "batch_outputs" / "markdown" / "cross_video_pattern_summary.md"
            )
            summary_json = (
                run_folder / "batch_outputs" / "json" / "cross_video_pattern_summary.json"
            )
            self.assertTrue(summary_markdown.is_file())
            self.assertTrue(summary_json.is_file())

            summary = json.loads(summary_json.read_text(encoding="utf-8"))
            self.assertEqual(summary["source_video_count"], 2)
            self.assertEqual(
                summary["priority_score_dimensions"],
                [
                    "viral_strength",
                    "nattome_relevance",
                    "evidence_confidence",
                    "brand_safety",
                    "ease_of_production",
                    "product_fit",
                ],
            )
            top_angle = summary["top_priority_shootable_angles"][0]
            self.assertEqual(top_angle["priority_score"]["max_points"], 30)
            self.assertEqual(
                top_angle["priority_score"]["total"],
                sum(top_angle["priority_score"]["dimensions"].values()),
            )
            self.assertLessEqual(top_angle["priority_score"]["total"], 30)
            self.assertIn("what_to_shoot_first", summary["recommendation"])

            markdown = summary_markdown.read_text(encoding="utf-8")
            for section in [
                "## Cross-Video Pattern Comparison",
                "### Hooks",
                "### Formats",
                "### Emotional Triggers",
                "### Audio Patterns",
                "### Risky Claims",
                "### Nattome Opportunities",
                "## Top Priority Shootable Angles",
                "## What To Shoot First",
            ]:
                self.assertIn(section, markdown)
            self.assertIn("Nattome Priority Score", markdown)
            self.assertIn("bloating-routine", markdown)

            batch_index = (run_folder / "batch_index.md").read_text(encoding="utf-8")
            self.assertIn("cross_video_pattern_summary.md", batch_index)

            metadata = json.loads((run_folder / "run_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(
                metadata["implementation_status"]["cross_video_pattern_summary"],
                "implemented",
            )

    def test_batch_run_gets_structured_json_and_spreadsheet_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runs_dir = temp_path / "runs"
            source_video = temp_path / "source.mp4"
            source_video.write_bytes(b"fake mp4 bytes")
            fake_ffmpeg = self.write_fake_ffmpeg(temp_path)
            fake_ocr = self.write_fake_ocr(temp_path, "Bloating after meals hook")
            fake_transcriber = self.write_fake_transcriber(
                temp_path,
                {
                    "language": "en",
                    "segments": [
                        {
                            "start": 0.0,
                            "end": 2.0,
                            "text": "If you feel bloated after meals try this routine",
                            "confidence": 0.9,
                        }
                    ],
                },
            )
            candidates_path = temp_path / "candidates.json"
            candidates_path.write_text(
                json.dumps(
                    {
                        "top": [
                            {
                                "id": "structured-video",
                                "url": "https://www.tiktok.com/@creator/video/structured",
                                "video_download_url": str(source_video),
                                "caption": "Bloating after meals gut health routine",
                                "play_count": 100000,
                                "like_count": 10000,
                                "comment_count": 500,
                                "share_count": 600,
                                "created_at": "2026-05-05T00:00:00Z",
                                "duration_seconds": 1,
                                "visible_text_expected": True,
                                "audio_format_hint": "talking_head",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = run_cli(
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
                "--ffmpeg-bin",
                str(fake_ffmpeg),
                "--ocr-primary-bin",
                str(fake_ocr),
                "--transcription-bin",
                str(fake_transcriber),
            )

            self.assertEqual(result.returncode, 0, result.stderr)

            run_folder = runs_dir / "20260506T134530Z_debug"
            structured_json = run_folder / "batch_outputs" / "json" / "structured_batch_analysis.json"
            spreadsheet = run_folder / "batch_outputs" / "spreadsheets" / "spreadsheet_summary.csv"
            self.assertTrue(structured_json.is_file())
            self.assertTrue(spreadsheet.is_file())

            structured = json.loads(structured_json.read_text(encoding="utf-8"))
            self.assertIn("batch_metadata", structured)
            self.assertIn("selection_decisions", structured)
            self.assertIn("evidence_bundle_index", structured)
            self.assertIn("cross_video_pattern_summary", structured)
            self.assertEqual(len(structured["videos"]), 1)
            video = structured["videos"][0]
            for key in [
                "hybrid_timeline",
                "ocr_evidence",
                "transcript_evidence",
                "audio_analysis",
                "virality_analysis",
                "claim_safety_review",
                "quality_score",
                "manual_review_flag",
                "shootable_angles",
                "nattome_priority_score",
            ]:
                self.assertIn(key, video)
            self.assertEqual(video["nattome_priority_score"]["max_points"], 30)

            csv_text = spreadsheet.read_text(encoding="utf-8")
            header = csv_text.splitlines()[0].split(",")
            self.assertEqual(
                header,
                [
                    "link",
                    "topic",
                    "hook_type",
                    "format",
                    "emotional_trigger",
                    "avatar",
                    "product_fit",
                    "priority_score",
                    "evidence_quality",
                    "recommended_angle",
                ],
            )
            self.assertIn("https://www.tiktok.com/@creator/video/structured", csv_text)
            self.assertIn("Digestive Comfort Routine Check", csv_text)

            batch_index = (run_folder / "batch_index.md").read_text(encoding="utf-8")
            self.assertIn("structured_batch_analysis.json", batch_index)
            self.assertIn("spreadsheet_summary.csv", batch_index)

            metadata = json.loads((run_folder / "run_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["implementation_status"]["structured_json_output"], "implemented")
            self.assertEqual(metadata["implementation_status"]["spreadsheet_summary"], "implemented")

    def test_telegram_delivery_reports_missing_credentials_and_supports_fake_sender(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runs_dir = temp_path / "runs"
            candidates_path = temp_path / "candidates.json"
            candidates_path.write_text(
                json.dumps(
                    {
                        "top": [
                            {
                                "id": "telegram-video",
                                "url": "https://www.tiktok.com/@creator/video/telegram",
                                "caption": "Acid reflux stomach tip",
                                "play_count": 90000,
                                "like_count": 9000,
                                "comment_count": 300,
                                "share_count": 500,
                                "created_at": "2026-05-05T00:00:00Z",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            env = os.environ.copy()
            env.pop("TELEGRAM_BOT_TOKEN", None)
            env.pop("TELEGRAM_CHAT_ID", None)
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
            delivery_log = json.loads(
                (run_folder / "logs" / "telegram_delivery.json").read_text(encoding="utf-8")
            )
            self.assertEqual(delivery_log["status"], "skipped")
            self.assertIn("missing Telegram credentials", delivery_log["reason"])
            self.assertIn("TELEGRAM_BOT_TOKEN", delivery_log["missing"])
            self.assertIn("TELEGRAM_CHAT_ID", delivery_log["missing"])

            from batch_analysis.telegram import deliver_telegram_brief

            metadata = json.loads((run_folder / "run_metadata.json").read_text(encoding="utf-8"))
            cross_summary = json.loads(
                (
                    run_folder
                    / "batch_outputs"
                    / "json"
                    / "cross_video_pattern_summary.json"
                ).read_text(encoding="utf-8")
            )
            sent_messages = []

            def fake_sender(token, chat_id, text):
                sent_messages.append((token, chat_id, text))
                return {"ok": True}

            send_status = deliver_telegram_brief(
                run_folder,
                metadata,
                cross_summary,
                {
                    "enabled": True,
                    "bot_token": "fake-token",
                    "chat_id": "fake-chat",
                },
                sender=fake_sender,
            )

            self.assertEqual(send_status["status"], "sent")
            self.assertEqual(len(sent_messages), 1)
            token, chat_id, message = sent_messages[0]
            self.assertEqual(token, "fake-token")
            self.assertEqual(chat_id, "fake-chat")
            self.assertLess(len(message), 1200)
            self.assertIn("Weekly Evidence Brief", message)
            self.assertIn("batch_outputs/markdown/cross_video_pattern_summary.md", message)
            self.assertIn("batch_outputs/json/structured_batch_analysis.json", message)
            self.assertIn("batch_outputs/spreadsheets/spreadsheet_summary.csv", message)
            self.assertIn("telegram-video", message)
            self.assertNotIn("## Cross-Video Pattern Comparison", message)

            metadata = json.loads((run_folder / "run_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["implementation_status"]["telegram_delivery"], "implemented")

    def test_optional_cleanup_removes_large_artifacts_and_writes_refinement_hooks(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runs_dir = temp_path / "runs"
            source_video = temp_path / "source.mp4"
            source_video.write_bytes(b"fake mp4 bytes")
            fake_ffmpeg = self.write_fake_ffmpeg(temp_path)
            fake_ocr = self.write_fake_ocr(temp_path, "Bloating after meals hook")
            fake_transcriber = self.write_fake_transcriber(
                temp_path,
                {
                    "language": "en",
                    "segments": [
                        {
                            "start": 0.0,
                            "end": 2.0,
                            "text": "If you feel bloated after meals try this routine",
                            "confidence": 0.9,
                        }
                    ],
                },
            )
            config_path = temp_path / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "cleanup": {
                            "enabled": True,
                            "report_approved": True,
                            "remove_source_videos": True,
                            "remove_frames": True,
                        }
                    }
                ),
                encoding="utf-8",
            )
            candidates_path = temp_path / "candidates.json"
            candidates_path.write_text(
                json.dumps(
                    {
                        "top": [
                            {
                                "id": "cleanup-video",
                                "url": "https://www.tiktok.com/@creator/video/cleanup",
                                "video_download_url": str(source_video),
                                "caption": "Bloating after meals gut health routine",
                                "play_count": 100000,
                                "like_count": 10000,
                                "comment_count": 500,
                                "share_count": 600,
                                "created_at": "2026-05-05T00:00:00Z",
                                "duration_seconds": 1,
                                "visible_text_expected": True,
                                "audio_format_hint": "talking_head",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = run_cli(
                "--mode",
                "debug",
                "--batch-size",
                "1",
                "--runs-dir",
                str(runs_dir),
                "--timestamp",
                "2026-05-06T13:45:30Z",
                "--config",
                str(config_path),
                "--candidates",
                str(candidates_path),
                "--ffmpeg-bin",
                str(fake_ffmpeg),
                "--ocr-primary-bin",
                str(fake_ocr),
                "--transcription-bin",
                str(fake_transcriber),
            )

            self.assertEqual(result.returncode, 0, result.stderr)

            run_folder = runs_dir / "20260506T134530Z_debug"
            bundle_folder = next((run_folder / "evidence_bundles").glob("001_*"))
            self.assertFalse((bundle_folder / "artifacts" / "source_video.mp4").exists())
            self.assertFalse((bundle_folder / "artifacts" / "frames").exists())
            self.assertTrue((bundle_folder / "video_evidence_report.md").is_file())
            self.assertTrue(
                (run_folder / "batch_outputs" / "json" / "structured_batch_analysis.json").is_file()
            )
            self.assertTrue(
                (run_folder / "batch_outputs" / "spreadsheets" / "spreadsheet_summary.csv").is_file()
            )

            cleanup_log = json.loads(
                (run_folder / "logs" / "evidence_artifact_cleanup.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(cleanup_log["status"], "completed")
            self.assertGreaterEqual(cleanup_log["removed_artifact_count"], 2)
            self.assertTrue(all(item["preserved_outputs"] for item in cleanup_log["bundles"]))

            hooks = json.loads(
                (
                    run_folder
                    / "batch_outputs"
                    / "json"
                    / "refinement_hooks.json"
                ).read_text(encoding="utf-8")
            )
            self.assertIn("deep_sound_research", hooks)
            self.assertIn("multilingual_quality_improvements", hooks)
            self.assertIn("full_script_generation", hooks)
            self.assertEqual(
                hooks["full_script_generation"]["source"],
                "top_priority_shootable_angles",
            )

            batch_index = (run_folder / "batch_index.md").read_text(encoding="utf-8")
            self.assertIn("evidence_artifact_cleanup.json", batch_index)
            self.assertIn("refinement_hooks.json", batch_index)

            metadata = json.loads((run_folder / "run_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["implementation_status"]["evidence_artifact_cleanup"], "implemented")
            self.assertEqual(metadata["implementation_status"]["refinement_hooks"], "implemented")

    def write_fake_ffmpeg(self, temp_path):
        fake_py = temp_path / "fake_ffmpeg.py"
        fake_py.write_text(
            "\n".join(
                [
                    "import pathlib",
                    "import sys",
                    "pathlib.Path(sys.argv[-1]).write_bytes(b'fake frame')",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        if os.name == "nt":
            fake_cmd = temp_path / "fake_ffmpeg.cmd"
            fake_cmd.write_text(
                f'@echo off\r\n"{sys.executable}" "{fake_py}" %*\r\n',
                encoding="utf-8",
            )
            return fake_cmd

        fake_sh = temp_path / "fake_ffmpeg"
        fake_sh.write_text(
            f'#!/bin/sh\n"{sys.executable}" "{fake_py}" "$@"\n',
            encoding="utf-8",
        )
        fake_sh.chmod(0o755)
        return fake_sh

    def write_fake_ocr(self, temp_path, text):
        fake_py = temp_path / "fake_ocr.py"
        fake_py.write_text(
            "\n".join(
                [
                    "import sys",
                    f"sys.stdout.write({text!r})",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        if os.name == "nt":
            fake_cmd = temp_path / "fake_ocr.cmd"
            fake_cmd.write_text(
                f'@echo off\r\n"{sys.executable}" "{fake_py}" %*\r\n',
                encoding="utf-8",
            )
            return fake_cmd

        fake_sh = temp_path / "fake_ocr"
        fake_sh.write_text(
            f'#!/bin/sh\n"{sys.executable}" "{fake_py}" "$@"\n',
            encoding="utf-8",
        )
        fake_sh.chmod(0o755)
        return fake_sh

    def write_fake_transcriber(self, temp_path, payload):
        fake_py = temp_path / "fake_transcriber.py"
        fake_py.write_text(
            "\n".join(
                [
                    "import json",
                    "import sys",
                    f"sys.stdout.write(json.dumps({payload!r}))",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        if os.name == "nt":
            fake_cmd = temp_path / "fake_transcriber.cmd"
            fake_cmd.write_text(
                f'@echo off\r\n"{sys.executable}" "{fake_py}" %*\r\n',
                encoding="utf-8",
            )
            return fake_cmd

        fake_sh = temp_path / "fake_transcriber"
        fake_sh.write_text(
            f'#!/bin/sh\n"{sys.executable}" "{fake_py}" "$@"\n',
            encoding="utf-8",
        )
        fake_sh.chmod(0o755)
        return fake_sh
