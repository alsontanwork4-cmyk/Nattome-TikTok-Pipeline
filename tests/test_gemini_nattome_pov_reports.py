import json
import os
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from dashboard.agent_settings import DEFAULT_AGENT_SETTINGS
from batch_analysis.gemini_reports import generate_nattome_pov_reports
from batch_analysis.run import create_run


class FakeGeminiResponse:
    def __init__(self, text):
        self.text = text


class FakeUploadedFile:
    def __init__(self, *, name="files/video", state="ACTIVE"):
        self.name = name
        self.uri = f"gemini://{name}"
        self.mime_type = "video/mp4"
        self.state = state


class FakeGeminiClient:
    def __init__(self):
        self.uploads = []
        self.calls = []
        self.files = self
        self.models = self

    def upload(self, *, file):
        self.uploads.append(Path(file))
        return {"uri": f"gemini://{Path(file).name}", "mime_type": "video/mp4"}

    def generate_content(self, *, model, contents, config=None):
        self.calls.append({"model": model, "contents": contents, "config": config})
        if len(self.calls) == 1:
            return FakeGeminiResponse(
                json.dumps(
                    {
                        "timestamped_visual_observations": [
                            {"timestamp": "0:00", "observation": "Creator opens with a meal close-up."}
                        ],
                        "spoken_content_notes": [
                            {"timestamp": "0:03", "note": "Mentions feeling bloated after eating."}
                        ],
                        "visible_text": [{"timestamp": "0:01", "text": "Bloated again?"}],
                        "hook_evidence": "Symptom-led opening in the first three seconds.",
                        "pacing_editing_notes": "Fast opening cut, then direct-to-camera explanation.",
                        "emotional_triggers": ["post-meal discomfort", "relief seeking"],
                        "creator_behavior": "Creator points to stomach and speaks directly to camera.",
                        "claim_evidence": ["Bloating discomfort is framed as personal experience."],
                    }
                )
            )
        return FakeGeminiResponse(
            "# Nattome POV Inspiration\n\nUse the post-meal bloating hook and keep claims grounded."
        )


class ExplodingGeminiClient:
    def __init__(self):
        self.files = self
        self.models = self

    def upload(self, *, file):
        raise AssertionError("Gemini should not be called")

    def generate_content(self, *, model, contents, config=None):
        raise AssertionError("Gemini should not be called")


def candidate(temp_path: Path, **overrides):
    source_video = temp_path / f"{overrides.get('id', 'video')}.mp4"
    source_video.write_bytes(b"fake mp4 bytes")
    payload = {
        "id": "first-video",
        "url": "https://www.tiktok.com/@creator/video/source",
        "video_download_url": str(source_video),
        "caption": "Bloating after meals gut health routine",
        "play_count": 120000,
        "like_count": 12000,
        "comment_count": 600,
        "share_count": 700,
        "created_at": "2026-05-05T00:00:00Z",
    }
    payload.update(overrides)
    return payload


class GeminiNattomePovReportsTest(unittest.TestCase):
    def test_run_snapshots_default_agent_config_and_records_source_version(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            candidates_path = temp_path / "candidates.json"
            candidates_path.write_text(json.dumps({"top": [candidate(temp_path)]}), encoding="utf-8")

            with patch.dict(os.environ, {"GEMINI_API_KEY": "test-gemini-key"}):
                run_folder = create_run(
                    Namespace(
                        mode="daily",
                        batch_size=1,
                        runs_dir=temp_path / "runs",
                        config=None,
                        candidates=candidates_path,
                        timestamp="2026-05-06T13:45:30Z",
                    ),
                    gemini_client_factory=lambda api_key: FakeGeminiClient(),
                )

            snapshot = json.loads(
                (run_folder / "data" / "agent_settings_snapshot.json").read_text(encoding="utf-8")
            )
            self.assertEqual(snapshot["source"], "defaults")
            self.assertIsNone(snapshot["version"])
            self.assertEqual(set(snapshot["settings"]["agents"]), {"gemini_video_evidence", "nattome_creative_strategy"})
            self.assertNotIn("GEMINI_API_KEY", json.dumps(snapshot))

            manifest = json.loads((run_folder / "run_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(
                manifest["agent_settings"],
                {
                    "source": "defaults",
                    "version": None,
                    "snapshot": "data/agent_settings_snapshot.json",
                },
            )

    def test_configured_agent_models_and_generation_options_are_used(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            candidates_path = temp_path / "candidates.json"
            candidates_path.write_text(json.dumps({"top": [candidate(temp_path)]}), encoding="utf-8")
            settings = json.loads(json.dumps(DEFAULT_AGENT_SETTINGS))
            settings["agents"]["gemini_video_evidence"]["model"] = "models/gemini-2.0-flash"
            settings["agents"]["gemini_video_evidence"]["generation"]["temperature"] = 0.15
            settings["agents"]["gemini_video_evidence"]["advanced_generation_config"] = {
                "response_mime_type": "application/json"
            }
            settings["agents"]["nattome_creative_strategy"]["model"] = "gemini-2.5-pro"
            settings["agents"]["nattome_creative_strategy"]["generation"]["temperature"] = 0.7
            fake_client = FakeGeminiClient()

            with patch.dict(os.environ, {"GEMINI_API_KEY": "test-gemini-key"}):
                create_run(
                    Namespace(
                        mode="daily",
                        batch_size=1,
                        runs_dir=temp_path / "runs",
                        config=None,
                        candidates=candidates_path,
                        timestamp="2026-05-06T13:45:30Z",
                        agent_settings_resolution={
                            "source": "supabase",
                            "version": 7,
                            "settings": settings,
                        },
                    ),
                    gemini_client_factory=lambda api_key: fake_client,
                )

            self.assertEqual(fake_client.calls[0]["model"], "models/gemini-2.0-flash")
            self.assertEqual(fake_client.calls[0]["config"]["temperature"], 0.15)
            self.assertEqual(fake_client.calls[0]["config"]["response_mime_type"], "application/json")
            self.assertEqual(fake_client.calls[1]["model"], "gemini-2.5-pro")
            self.assertEqual(fake_client.calls[1]["config"]["temperature"], 0.7)

    def test_disabled_evidence_agent_skips_full_gemini_reporting_chain(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            candidates_path = temp_path / "candidates.json"
            candidates_path.write_text(json.dumps({"top": [candidate(temp_path)]}), encoding="utf-8")
            settings = json.loads(json.dumps(DEFAULT_AGENT_SETTINGS))
            settings["agents"]["gemini_video_evidence"]["enabled"] = False

            with patch.dict(os.environ, {"GEMINI_API_KEY": "test-gemini-key"}):
                run_folder = create_run(
                    Namespace(
                        mode="daily",
                        batch_size=1,
                        runs_dir=temp_path / "runs",
                        config=None,
                        candidates=candidates_path,
                        timestamp="2026-05-06T13:45:30Z",
                        agent_settings_resolution={"source": "local", "version": None, "settings": settings},
                    ),
                    gemini_client_factory=lambda api_key: ExplodingGeminiClient(),
                )

            self.assertFalse((run_folder / "data" / "001_first-video_gemini_evidence.json").exists())
            self.assertFalse((run_folder / "reports" / "001_first-video_nattome_pov_report.md").exists())
            manifest = json.loads((run_folder / "run_manifest.json").read_text(encoding="utf-8"))
            phases = {phase["name"]: phase for phase in manifest["phases"]}
            self.assertEqual(phases["gemini_video_evidence"]["status"], "disabled")
            self.assertEqual(phases["gemini_creative_strategy"]["status"], "skipped")
            self.assertEqual(phases["nattome_pov_reports"]["status"], "skipped")

    def test_disabled_creative_agent_still_runs_evidence_and_skips_reports(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            candidates_path = temp_path / "candidates.json"
            candidates_path.write_text(json.dumps({"top": [candidate(temp_path)]}), encoding="utf-8")
            settings = json.loads(json.dumps(DEFAULT_AGENT_SETTINGS))
            settings["agents"]["nattome_creative_strategy"]["enabled"] = False
            fake_client = FakeGeminiClient()

            with patch.dict(os.environ, {"GEMINI_API_KEY": "test-gemini-key"}):
                run_folder = create_run(
                    Namespace(
                        mode="daily",
                        batch_size=1,
                        runs_dir=temp_path / "runs",
                        config=None,
                        candidates=candidates_path,
                        timestamp="2026-05-06T13:45:30Z",
                        agent_settings_resolution={"source": "local", "version": None, "settings": settings},
                    ),
                    gemini_client_factory=lambda api_key: fake_client,
                )

            self.assertEqual(len(fake_client.calls), 1)
            self.assertTrue((run_folder / "data" / "001_first-video_gemini_evidence.json").is_file())
            self.assertFalse((run_folder / "data" / "001_first-video_gemini_creative_response.json").exists())
            self.assertFalse((run_folder / "reports" / "001_first-video_nattome_pov_report.md").exists())
            manifest = json.loads((run_folder / "run_manifest.json").read_text(encoding="utf-8"))
            phases = {phase["name"]: phase for phase in manifest["phases"]}
            self.assertEqual(phases["gemini_video_evidence"]["status"], "completed")
            self.assertEqual(phases["gemini_creative_strategy"]["status"], "disabled")
            self.assertEqual(phases["nattome_pov_reports"]["status"], "skipped")
            self.assertEqual(manifest["outputs"]["final_outputs"], [])

    def test_invalid_agent_config_records_preflight_failure_without_calling_gemini(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            candidates_path = temp_path / "candidates.json"
            candidates_path.write_text(json.dumps({"top": [candidate(temp_path)]}), encoding="utf-8")
            settings = json.loads(json.dumps(DEFAULT_AGENT_SETTINGS))
            settings["agents"]["gemini_video_evidence"]["model"] = "text-bison"

            with patch.dict(os.environ, {"GEMINI_API_KEY": "test-gemini-key"}):
                run_folder = create_run(
                    Namespace(
                        mode="daily",
                        batch_size=1,
                        runs_dir=temp_path / "runs",
                        config=None,
                        candidates=candidates_path,
                        timestamp="2026-05-06T13:45:30Z",
                        agent_settings_resolution={"source": "supabase", "version": 9, "settings": settings},
                    ),
                    gemini_client_factory=lambda api_key: ExplodingGeminiClient(),
                )

            self.assertFalse((run_folder / "data" / "agent_settings_snapshot.json").exists())
            manifest = json.loads((run_folder / "run_manifest.json").read_text(encoding="utf-8"))
            phases = {phase["name"]: phase for phase in manifest["phases"]}
            self.assertEqual(phases["gemini_video_evidence"]["status"], "failed")
            self.assertIn("model", str(phases["gemini_video_evidence"]["failure_details"]))
            self.assertEqual(phases["gemini_creative_strategy"]["status"], "failed")
            self.assertEqual(phases["nattome_pov_reports"]["status"], "failed")

    def test_completed_run_writes_two_agent_gemini_artifacts_manifest_phases_and_sends_telegram(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            candidates_path = temp_path / "candidates.json"
            candidates_path.write_text(json.dumps({"top": [candidate(temp_path)]}), encoding="utf-8")
            fake_client = FakeGeminiClient()
            captured_api_keys = []
            telegram_messages = []
            telegram_documents = []

            def client_factory(api_key):
                captured_api_keys.append(api_key)
                return fake_client

            def telegram_sender(bot_token, chat_id, text):
                telegram_messages.append({"bot_token": bot_token, "chat_id": chat_id, "text": text})
                return {"status": "sent"}

            def telegram_document_sender(bot_token, chat_id, document_path):
                telegram_documents.append(
                    {"bot_token": bot_token, "chat_id": chat_id, "document_path": Path(document_path)}
                )
                return {"status": "sent"}

            with patch.dict(
                os.environ,
                {
                    "GEMINI_API_KEY": "test-gemini-key",
                    "TELEGRAM_BOT_TOKEN": "test-telegram-token",
                    "TELEGRAM_CHAT_ID": "test-chat-id",
                },
            ):
                run_folder = create_run(
                    Namespace(
                        mode="daily",
                        batch_size=1,
                        runs_dir=temp_path / "runs",
                        config=None,
                        candidates=candidates_path,
                        timestamp="2026-05-06T13:45:30Z",
                    ),
                    gemini_client_factory=client_factory,
                    telegram_sender=telegram_sender,
                    telegram_document_sender=telegram_document_sender,
                )

            self.assertEqual(captured_api_keys, ["test-gemini-key"])
            self.assertEqual(len(fake_client.uploads), 1)
            self.assertEqual(fake_client.uploads[0].name, "001_first-video_source_video.mp4")
            self.assertEqual(len(fake_client.calls), 2)
            self.assertIn("Video Evidence Analyst Agent", str(fake_client.calls[0]["contents"]))
            self.assertIn("Nattome Creative Strategist Agent", str(fake_client.calls[1]["contents"]))
            self.assertIn("Mandatory Nattome context", str(fake_client.calls[1]["contents"]))
            self.assertIn("skills/nattome-tiktok-candidate-discovery/references/nattome_brand.md", str(fake_client.calls[1]["contents"]))
            self.assertIn("Nattome is Atomic Group", str(fake_client.calls[1]["contents"]))
            self.assertIn("timestamped_visual_observations", str(fake_client.calls[1]["contents"]))
            self.assertIn("Preferred report outline", str(fake_client.calls[1]["contents"]))
            self.assertIn("| Concept | Hook | Format | Why it works |", str(fake_client.calls[1]["contents"]))
            self.assertIn("| Time | Scene | On-screen text | Exact line |", str(fake_client.calls[1]["contents"]))

            evidence_path = run_folder / "data" / "001_first-video_gemini_evidence.json"
            creative_path = run_folder / "data" / "001_first-video_gemini_creative_response.json"
            report_path = run_folder / "reports" / "001_first-video_nattome_pov_report.md"
            compiled_report_path = run_folder / "reports" / "nattome_batch_analysis_final_outputs.md"
            self.assertTrue(evidence_path.is_file())
            self.assertTrue(creative_path.is_file())
            self.assertEqual(
                report_path.read_text(encoding="utf-8"),
                "# Nattome POV Inspiration\n\nUse the post-meal bloating hook and keep claims grounded.\n",
            )
            self.assertTrue(compiled_report_path.is_file())
            self.assertIn("Video 1: 001_first-video", compiled_report_path.read_text(encoding="utf-8"))
            self.assertEqual(len(telegram_messages), 1)
            self.assertEqual(telegram_messages[0]["bot_token"], "test-telegram-token")
            self.assertEqual(telegram_messages[0]["chat_id"], "test-chat-id")
            self.assertIn("Nattome Batch Analysis Final Outputs", telegram_messages[0]["text"])
            self.assertIn("Run: 2026-05-06T21:45:30+08:00", telegram_messages[0]["text"])
            self.assertIn("Videos compared: 1", telegram_messages[0]["text"])
            self.assertIn("Success or Fail: Success", telegram_messages[0]["text"])
            self.assertEqual(len(telegram_documents), 1)
            self.assertEqual(telegram_documents[0]["bot_token"], "test-telegram-token")
            self.assertEqual(telegram_documents[0]["chat_id"], "test-chat-id")
            self.assertEqual(
                telegram_documents[0]["document_path"].name,
                "nattome_batch_analysis_final_outputs.md",
            )

            manifest = json.loads((run_folder / "run_manifest.json").read_text(encoding="utf-8"))
            phases = {phase["name"]: phase for phase in manifest["phases"]}
            self.assertEqual(phases["gemini_video_evidence"]["status"], "completed")
            self.assertEqual(phases["gemini_creative_strategy"]["status"], "completed")
            self.assertEqual(phases["nattome_pov_reports"]["status"], "completed")
            self.assertEqual(phases["telegram_delivery"]["status"], "completed")
            self.assertEqual(
                manifest["outputs"]["final_outputs"],
                ["reports/nattome_batch_analysis_final_outputs.md"],
            )
            self.assertEqual(
                phases["nattome_pov_reports"]["outputs"]["per_video_reports"],
                ["reports/001_first-video_nattome_pov_report.md"],
            )
            self.assertEqual(manifest["outputs"]["pipeline_status"], "nattome_pov_reports_delivered")

    def test_uploaded_video_is_polled_until_active_before_evidence_generation(self):
        class PollingGeminiClient(FakeGeminiClient):
            def __init__(self):
                super().__init__()
                self.get_calls = 0

            def upload(self, *, file):
                self.uploads.append(Path(file))
                return FakeUploadedFile(state="PROCESSING")

            def get(self, *, name):
                self.get_calls += 1
                return FakeUploadedFile(name=name, state="ACTIVE")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            candidates_path = temp_path / "candidates.json"
            candidates_path.write_text(json.dumps({"top": [candidate(temp_path)]}), encoding="utf-8")
            fake_client = PollingGeminiClient()

            with patch.dict(os.environ, {"GEMINI_API_KEY": "test-gemini-key"}), patch(
                "batch_analysis.gemini_reports.time.sleep"
            ):
                run_folder = create_run(
                    Namespace(
                        mode="daily",
                        batch_size=1,
                        runs_dir=temp_path / "runs",
                        config=None,
                        candidates=candidates_path,
                        timestamp="2026-05-06T13:45:30Z",
                    ),
                    gemini_client_factory=lambda api_key: fake_client,
                )

            self.assertEqual(fake_client.get_calls, 1)
            self.assertEqual(len(fake_client.calls), 2)
            evidence = json.loads(
                (run_folder / "data" / "001_first-video_gemini_evidence.json").read_text(encoding="utf-8")
            )
            self.assertEqual(evidence["uploaded_file"]["state"], "ACTIVE")

    def test_generated_report_records_missing_telegram_credentials_without_failing_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            candidates_path = temp_path / "candidates.json"
            candidates_path.write_text(json.dumps({"top": [candidate(temp_path)]}), encoding="utf-8")

            def telegram_sender(bot_token, chat_id, text):
                raise AssertionError("Telegram should not be called without credentials")

            with patch.dict(os.environ, {"GEMINI_API_KEY": "test-gemini-key"}, clear=True):
                run_folder = create_run(
                    Namespace(
                        mode="daily",
                        batch_size=1,
                        runs_dir=temp_path / "runs",
                        config=None,
                        candidates=candidates_path,
                        timestamp="2026-05-06T13:45:30Z",
                    ),
                    gemini_client_factory=lambda api_key: FakeGeminiClient(),
                    telegram_sender=telegram_sender,
                    telegram_document_sender=lambda bot_token, chat_id, document_path: {
                        "status": "should-not-send"
                    },
                )

            manifest = json.loads((run_folder / "run_manifest.json").read_text(encoding="utf-8"))
            phases = {phase["name"]: phase for phase in manifest["phases"]}
            self.assertEqual(phases["nattome_pov_reports"]["status"], "completed")
            self.assertEqual(phases["telegram_delivery"]["status"], "missing_credentials")
            self.assertIn("TELEGRAM_BOT_TOKEN", str(phases["telegram_delivery"]["failure_details"]))
            self.assertIn("TELEGRAM_CHAT_ID", str(phases["telegram_delivery"]["failure_details"]))
            self.assertEqual(manifest["outputs"]["pipeline_status"], "nattome_pov_reports_completed")

    def test_missing_credentials_records_phase_status_without_calling_gemini(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            candidates_path = temp_path / "candidates.json"
            candidates_path.write_text(json.dumps({"top": [candidate(temp_path)]}), encoding="utf-8")

            def client_factory(api_key):
                raise AssertionError("Gemini client should not be created without credentials")

            with patch.dict(os.environ, {}, clear=True):
                run_folder = create_run(
                    Namespace(
                        mode="daily",
                        batch_size=1,
                        runs_dir=temp_path / "runs",
                        config=None,
                        candidates=candidates_path,
                        timestamp="2026-05-06T13:45:30Z",
                    ),
                    gemini_client_factory=client_factory,
                )

            self.assertFalse((run_folder / "data" / "001_first-video_gemini_evidence.json").exists())
            self.assertFalse((run_folder / "reports" / "001_first-video_nattome_pov_report.md").exists())
            manifest = json.loads((run_folder / "run_manifest.json").read_text(encoding="utf-8"))
            phases = {phase["name"]: phase for phase in manifest["phases"]}
            self.assertEqual(phases["gemini_video_evidence"]["status"], "missing_credentials")
            self.assertEqual(phases["gemini_creative_strategy"]["status"], "missing_credentials")
            self.assertEqual(phases["nattome_pov_reports"]["status"], "missing_credentials")
            self.assertEqual(manifest["outputs"]["final_outputs"], [])
            self.assertIn("GEMINI_API_KEY is not configured", str(phases["gemini_video_evidence"]))

    def test_unavailable_video_fails_that_candidate_and_continues_other_reports(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            candidates_path = temp_path / "candidates.json"
            missing = candidate(
                temp_path,
                id="missing-video",
                play_count=130000,
                video_download_url=str(temp_path / "does-not-exist.mp4"),
            )
            available = candidate(temp_path, id="available-video", play_count=120000)
            candidates_path.write_text(json.dumps({"top": [missing, available]}), encoding="utf-8")
            fake_client = FakeGeminiClient()

            with patch.dict(os.environ, {"GEMINI_API_KEY": "test-gemini-key"}):
                run_folder = create_run(
                    Namespace(
                        mode="daily",
                        batch_size=2,
                        runs_dir=temp_path / "runs",
                        config=None,
                        candidates=candidates_path,
                        timestamp="2026-05-06T13:45:30Z",
                    ),
                    gemini_client_factory=lambda api_key: fake_client,
                )

            self.assertEqual(len(fake_client.uploads), 1)
            self.assertTrue((run_folder / "reports" / "002_available-video_nattome_pov_report.md").is_file())
            self.assertFalse((run_folder / "reports" / "001_missing-video_nattome_pov_report.md").exists())

            manifest = json.loads((run_folder / "run_manifest.json").read_text(encoding="utf-8"))
            phases = {phase["name"]: phase for phase in manifest["phases"]}
            self.assertEqual(phases["gemini_video_evidence"]["status"], "partial")
            self.assertEqual(phases["gemini_creative_strategy"]["status"], "partial")
            self.assertEqual(phases["nattome_pov_reports"]["status"], "partial")
            self.assertEqual(
                manifest["outputs"]["final_outputs"],
                ["reports/nattome_batch_analysis_final_outputs.md"],
            )
            compiled_report_path = run_folder / "reports" / "nattome_batch_analysis_final_outputs.md"
            self.assertTrue(compiled_report_path.is_file())
            self.assertIn("002_available-video", compiled_report_path.read_text(encoding="utf-8"))
            self.assertIn("missing-video", str(phases["nattome_pov_reports"]["failure_details"]))

    def test_completed_artifacts_are_skipped_on_phase_two_rerun(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            candidates_path = temp_path / "candidates.json"
            candidates = [candidate(temp_path)]
            candidates_path.write_text(json.dumps({"top": candidates}), encoding="utf-8")

            with patch.dict(os.environ, {"GEMINI_API_KEY": "test-gemini-key"}):
                run_folder = create_run(
                    Namespace(
                        mode="daily",
                        batch_size=1,
                        runs_dir=temp_path / "runs",
                        config=None,
                        candidates=candidates_path,
                        timestamp="2026-05-06T13:45:30Z",
                    ),
                    gemini_client_factory=lambda api_key: FakeGeminiClient(),
                )
                rerun = generate_nattome_pov_reports(
                    run_folder,
                    json.loads((run_folder / "data" / "selected_batch.json").read_text(encoding="utf-8"))[
                        "selected_candidates"
                    ],
                    client_factory=lambda api_key: ExplodingGeminiClient(),
                )

            phases = {phase["name"]: phase for phase in rerun["phases"]}
            self.assertEqual(phases["gemini_video_evidence"]["status"], "skipped")
            self.assertEqual(phases["gemini_creative_strategy"]["status"], "skipped")
            self.assertEqual(phases["nattome_pov_reports"]["status"], "skipped")
            self.assertEqual(rerun["final_outputs"], ["reports/nattome_batch_analysis_final_outputs.md"])


if __name__ == "__main__":
    unittest.main()
