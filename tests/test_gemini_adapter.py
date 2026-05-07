import json
import tempfile
import unittest
from pathlib import Path
from argparse import Namespace
from datetime import datetime, timezone

from batch_analysis.evidence_io import EvidenceBundleStore
from batch_analysis.config import DEFAULT_CONFIG
from batch_analysis.run_manifest import build_run_manifest
from batch_analysis.tool_adapters import GeminiFlashAdapter


def candidate(**overrides):
    payload = {
        "id": "gemini-video",
        "rank": 1,
        "url": "https://www.tiktok.com/@creator/video/gemini",
        "caption": "Acid reflux routine",
    }
    payload.update(overrides)
    return payload


class FakeGeminiClient:
    def __init__(self, response=None, error=None):
        self.response = response or {}
        self.error = error
        self.calls = []

    def analyze_video(self, *, model, api_key, source_video_path, candidate_context):
        self.calls.append(
            {
                "model": model,
                "api_key": api_key,
                "source_video_path": source_video_path,
                "candidate_context": candidate_context,
            }
        )
        if self.error:
            raise self.error
        return self.response


class GeminiFlashAdapterTest(unittest.TestCase):
    def test_gemini_flash_is_configured_as_primary_tool_stack_adapter(self):
        self.assertEqual(DEFAULT_CONFIG["tool_stack"]["primary_adapter"], "gemini_2_5_flash")
        self.assertEqual(DEFAULT_CONFIG["tool_stack"]["gemini_model"], "gemini-2.5-flash")
        self.assertEqual(DEFAULT_CONFIG["tool_stack"]["gemini_api_key_env"], "GEMINI_API_KEY")

    def test_run_manifest_records_gemini_failure_statuses(self):
        manifest = build_run_manifest(
            Namespace(mode="debug", batch_size=1, candidates=None),
            datetime(2026, 5, 6, 13, 45, 30, tzinfo=timezone.utc),
            DEFAULT_CONFIG,
            has_candidate_selection=True,
            has_evidence_bundles=True,
            has_cross_video_pattern_summary=False,
            has_structured_outputs=False,
            has_telegram_delivery=False,
            has_evidence_artifact_cleanup=False,
            has_refinement_hooks=False,
            gemini_evidence_statuses=[
                {
                    "candidate_id": "gemini-video",
                    "status": "missing_credentials",
                    "reason": "Gemini API key is missing; set GEMINI_API_KEY",
                }
            ],
        )

        phase = next(item for item in manifest["phases"] if item["name"] == "gemini_evidence")
        self.assertEqual(phase["status"], "failed")
        self.assertEqual(phase["outputs"]["evidence"], "data/*_gemini_evidence.json")
        self.assertEqual(phase["notes"], ["gemini-video: Gemini API key is missing; set GEMINI_API_KEY"])

    def test_normalizes_fake_gemini_response_without_shootable_angles(self):
        source_video = Path("source.mp4")
        response = {
            "visual_observations": [
                {"timestamp_seconds": 0.5, "description": "Creator points at stomach"}
            ],
            "visible_text": [{"timestamp_seconds": 0.8, "text": "Bloated after meals?"}],
            "spoken_content": [
                {"start_seconds": 0.0, "end_seconds": 2.0, "text": "If you get reflux after meals"}
            ],
            "audio_cues": [{"timestamp_seconds": 0.0, "cue": "calm voiceover"}],
            "hook_evidence": [{"timestamp_seconds": 0.5, "evidence": "opens with problem question"}],
            "claim_evidence": [{"timestamp_seconds": 1.2, "claim": "helps reflux"}],
            "shootable_angles": [{"title": "Should not be used"}],
        }
        client = FakeGeminiClient(response)
        adapter = GeminiFlashAdapter(api_key="fake-key", client=client)

        evidence = adapter.analyze_source_video(source_video, candidate())

        self.assertEqual(evidence["status"], "completed")
        self.assertEqual(evidence["model"], "gemini-2.5-flash")
        self.assertEqual(evidence["visual_observations"][0]["observation"], "Creator points at stomach")
        self.assertEqual(evidence["visible_text"][0]["text"], "Bloated after meals?")
        self.assertEqual(evidence["spoken_content"][0]["text"], "If you get reflux after meals")
        self.assertEqual(evidence["audio_cues"][0]["cue"], "calm voiceover")
        self.assertEqual(evidence["hook_evidence"][0]["evidence"], "opens with problem question")
        self.assertEqual(evidence["claim_evidence"][0]["text"], "helps reflux")
        self.assertNotIn("shootable_angles", evidence)
        self.assertEqual(client.calls[0]["model"], "gemini-2.5-flash")

    def test_partial_response_records_missing_evidence_sections(self):
        adapter = GeminiFlashAdapter(
            api_key="fake-key",
            client=FakeGeminiClient({"visible_text": [{"timestamp_seconds": 0.2, "text": "Gut tip"}]}),
        )

        evidence = adapter.analyze_source_video(Path("source.mp4"), candidate())

        self.assertEqual(evidence["status"], "partial")
        self.assertEqual(
            evidence["missing_evidence"],
            [
                "visual_observations",
                "spoken_content",
                "audio_cues",
                "hook_evidence",
                "claim_evidence",
            ],
        )

    def test_missing_credentials_and_client_failure_are_recorded_without_network(self):
        missing = GeminiFlashAdapter(api_key="", api_key_env="MISSING_GEMINI_KEY_FOR_TEST")

        missing_status = missing.analyze_source_video(Path("source.mp4"), candidate())

        self.assertEqual(missing_status["status"], "missing_credentials")
        self.assertIn("MISSING_GEMINI_KEY_FOR_TEST", missing_status["reason"])

        failed = GeminiFlashAdapter(
            api_key="fake-key",
            client=FakeGeminiClient(error=RuntimeError("Gemini timeout")),
        )

        failed_status = failed.analyze_source_video(Path("source.mp4"), candidate())

        self.assertEqual(failed_status["status"], "failed")
        self.assertIn("Gemini timeout", failed_status["reason"])

    def test_gemini_evidence_is_written_through_evidence_bundle_store(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "run"
            for child in ("reports", "data", "evidence", "logs"):
                (run_folder / child).mkdir(parents=True)
            selected = candidate()
            store = EvidenceBundleStore(run_folder)
            store.write_source_snapshots([selected])
            evidence = GeminiFlashAdapter(
                api_key="fake-key",
                client=FakeGeminiClient(
                    {
                        "visible_text": [{"timestamp_seconds": 0.2, "text": "Gut tip"}],
                        "hook_evidence": [{"timestamp_seconds": 0.2, "evidence": "text hook"}],
                    }
                ),
            ).analyze_source_video(run_folder / "evidence" / "001_gemini-video_source_video.mp4", selected)

            store.write_gemini_evidence(selected, evidence)
            snapshot = store.load_snapshot(selected)

            self.assertEqual(snapshot["artifacts"]["gemini_evidence"]["state"], "partial")
            self.assertEqual(
                snapshot["artifacts"]["gemini_evidence"]["path"],
                "data/001_gemini-video_gemini_evidence.json",
            )
            written = json.loads(
                (run_folder / "data" / "001_gemini-video_gemini_evidence.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(written["visible_text"][0]["text"], "Gut tip")


if __name__ == "__main__":
    unittest.main()
