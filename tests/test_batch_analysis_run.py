import inspect
import json
import os
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from batch_analysis.run import build_metadata


WORKSPACE = Path(__file__).resolve().parents[1]
SCRIPT = WORKSPACE / "scripts" / "run_batch_analysis.py"


def run_cli(*args, cwd=WORKSPACE):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
    )


class BatchAnalysisRunCliTest(unittest.TestCase):
    def test_build_metadata_has_no_spreadsheet_summary_status_input(self):
        signature = inspect.signature(build_metadata)

        self.assertNotIn("has_spreadsheet_summary", signature.parameters)

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
                self.assertEqual(metadata["configuration"]["outputs"]["markdown"], "reports")
                self.assertEqual(metadata["implementation_status"]["video_download"], "not_implemented")
                self.assertEqual(metadata["implementation_status"]["gemini_evidence"], "not_implemented")
                self.assertEqual(metadata["implementation_status"]["audio_music_trend_analysis"], "not_implemented")
                self.assertNotIn("spreadsheet_summary", metadata["implementation_status"])

                expected_paths = [
                    "reports",
                    "data",
                    "evidence",
                    "logs",
                ]
                for relative_path in expected_paths:
                    self.assertTrue((run_folder / relative_path).is_dir(), relative_path)
                self.assertTrue((run_folder / "run_manifest.json").is_file())

                self.assertTrue(
                    (run_folder / "batch_index.md").read_text(encoding="utf-8").startswith(
                        "# Batch Analysis Run"
                    )
                )
                self.assertIn(str(run_folder), result.stdout)

    def test_skeleton_run_uses_two_layer_layout_and_manifest_index(self):
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

            run_folder = runs_dir / "20260506T134530Z_debug"
            self.assertEqual(
                sorted(child.name for child in run_folder.iterdir() if child.is_dir()),
                ["data", "evidence", "logs", "reports"],
            )
            self.assertFalse((run_folder / "batch_outputs").exists())
            self.assertFalse((run_folder / "evidence_bundles").exists())

            generated_paths = [
                path.relative_to(run_folder)
                for path in run_folder.rglob("*")
                if path != run_folder
            ]
            too_deep_paths = [
                str(path)
                for path in generated_paths
                if len(path.parts) > 2
            ]
            self.assertEqual(too_deep_paths, [])

            manifest = json.loads((run_folder / "run_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["run_timestamp"], "2026-05-06T13:45:30Z")
            self.assertEqual(manifest["mode"], "debug")
            self.assertEqual(manifest["requested_batch_size"], 1)
            self.assertIn("configuration", manifest)
            self.assertIsInstance(manifest["phases"], list)
            self.assertTrue(manifest["phases"])
            self.assertTrue(all(isinstance(phase, dict) for phase in manifest["phases"]))
            self.assertTrue(all("name" in phase and "status" in phase for phase in manifest["phases"]))
            self.assertNotIn("implementation_status", manifest)

            batch_index = (run_folder / "batch_index.md").read_text(encoding="utf-8")
            self.assertIn("# Batch Analysis Run", batch_index)
            self.assertIn("run_manifest.json", batch_index)
            self.assertIn("- `reports`", batch_index)
            self.assertIn("- Candidate selection was not run", batch_index)

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
            source_video = temp_path / "source.mp4"
            source_video.write_bytes(b"fake mp4 bytes")
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
                                "created_at": "2025-11-01T00:00:00Z",
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
                                "video_download_url": str(source_video),
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
                                "video_download_url": str(source_video),
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
                (run_folder / "data" / "selected_batch.json").read_text(
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
            self.assertIn("older than", excluded["too-old"])
            self.assertIn("below minimum weighted engagement rate", excluded["weak-engagement"])
            self.assertIn("missing usable TikTok link", excluded["missing-link"])

            preview = (
                run_folder / "reports" / "selected_batch.md"
            ).read_text(encoding="utf-8")
            self.assertIn("good-relevant", preview)
            self.assertIn("good-higher-views-less-relevant", preview)

            metadata = json.loads((run_folder / "run_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["implementation_status"]["candidate_selection"], "implemented")

    def test_telegram_delivery_reports_missing_credentials_and_supports_fake_sender(self):
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
                                "id": "telegram-video",
                                "url": "https://www.tiktok.com/@creator/video/telegram",
                                "video_download_url": str(source_video),
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
            env["NATTOME_DISABLE_DOTENV"] = "1"
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
                    "--outputs-dir",
                    str(temp_path / "outputs"),
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
            manifest = json.loads((run_folder / "run_manifest.json").read_text(encoding="utf-8"))
            cross_summary = json.loads(
                (
                    run_folder
                    / "data"
                    / "cross_video_pattern_summary.json"
                ).read_text(encoding="utf-8")
            )
            sent_messages = []
            sent_documents = []

            def fake_sender(token, chat_id, text):
                sent_messages.append((token, chat_id, text))
                return {"ok": True}

            def fake_document_sender(token, chat_id, document_path):
                sent_documents.append((token, chat_id, Path(document_path).name))
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
                manifest["outputs"]["final_outputs"],
                sender=fake_sender,
                document_sender=fake_document_sender,
            )

            self.assertEqual(send_status["status"], "sent")
            self.assertEqual(len(sent_messages), 1)
            self.assertEqual(len(sent_documents), 2)
            token, chat_id, message = sent_messages[0]
            self.assertEqual(token, "fake-token")
            self.assertEqual(chat_id, "fake-chat")
            self.assertLess(len(message), 1200)
            self.assertEqual(
                message.splitlines(),
                [
                    "Nattome Batch Analysis Final Outputs",
                    "Run: 2026-05-06T13:45:30Z",
                    "Videos compared: 1",
                    "Success or Fail: Success",
                ],
            )
            self.assertEqual(
                [document_name for _token, _chat_id, document_name in sent_documents],
                [
                    "top5_creative_production_report_2026-05-06.md",
                    "top5_angle_planning_sheet_2026-05-06.xlsx",
                ],
            )

            metadata = json.loads((run_folder / "run_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["implementation_status"]["telegram_delivery"], "implemented")

