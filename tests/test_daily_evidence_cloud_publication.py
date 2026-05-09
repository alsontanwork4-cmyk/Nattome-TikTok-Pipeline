import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from batch_analysis.run import create_run


class FakeGeminiAdapter:
    def analyze_source_video(self, source_video_path, candidate_context):
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
                    "language": "English",
                    "confidence": 0.91,
                }
            ],
            "audio_cues": [{"timestamp_seconds": 0, "cue": "calm voiceover"}],
            "hook_evidence": [
                {"timestamp_seconds": 0.5, "evidence": "problem question opens the video"}
            ],
            "claim_evidence": [{"timestamp_seconds": 1.2, "text": "supports digestion"}],
            "missing_evidence": [],
        }


class RecordingPublicationAdapter:
    def __init__(self):
        self.runs = []
        self.artifacts = []

    def publish_run_with_artifacts(self, run, artifacts):
        self.runs.append(run)
        self.artifacts.extend(artifacts)
        from batch_analysis.cloud_publication import PublicationResult

        return PublicationResult(status="succeeded", errors=[])


class FailingPublicationAdapter:
    def publish_run_with_artifacts(self, run, artifacts):
        from batch_analysis.cloud_publication import PublicationResult

        return PublicationResult(
            status="failed",
            errors=["daily-runs/example/report.md: Supabase artifact upsert failed"],
        )


def write_daily_inputs(temp_path):
    daily_run_dir = temp_path / "data" / "daily_runs" / "nattome_20260509T010000"
    daily_run_dir.mkdir(parents=True)
    source_video = daily_run_dir / "source.mp4"
    source_video.write_bytes(b"fake mp4 bytes")
    raw_scrape = daily_run_dir / "raw_scrape_top30.json"
    raw_scrape.write_text(json.dumps({"top": []}), encoding="utf-8")
    daily_selection = daily_run_dir / "daily_selection_top3.json"
    daily_selection.write_text(
        json.dumps(
            {
                "top": [
                    {
                        "id": "daily-video",
                        "url": "https://www.tiktok.com/@creator/video/daily",
                        "video_download_url": str(source_video),
                        "caption": "Bloating after meals gut health routine",
                        "play_count": 120000,
                        "like_count": 12000,
                        "comment_count": 600,
                        "share_count": 700,
                        "created_at": "2026-05-05T00:00:00Z",
                        "audio_format_hint": "talking_head",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return raw_scrape, daily_selection


class DailyEvidenceCloudPublicationTest(unittest.TestCase):
    def test_enabled_daily_run_publishes_completed_run_and_required_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            raw_scrape, daily_selection = write_daily_inputs(temp_path)
            adapter = RecordingPublicationAdapter()

            run_folder = create_run(
                Namespace(
                    mode="daily",
                    batch_size=1,
                    runs_dir=temp_path / "runs",
                    outputs_dir=temp_path / "outputs",
                    config=None,
                    candidates=daily_selection,
                    timestamp="2026-05-09T01:00:00Z",
                    gemini_adapter=FakeGeminiAdapter(),
                    cloud_publication_enabled=True,
                    cloud_publication_adapter=adapter,
                )
            )

            self.assertEqual(adapter.runs[0].run_id, run_folder.name)
            self.assertEqual(adapter.runs[0].publication_status, "pending")
            artifact_types = {artifact.artifact_type for artifact in adapter.artifacts}
            self.assertTrue((run_folder / "batch_index.md").is_file())
            self.assertTrue(raw_scrape.is_file())
            self.assertTrue(daily_selection.is_file())
            self.assertGreaterEqual(
                artifact_types,
                {
                    "raw_scrape",
                    "daily_selection",
                    "markdown",
                    "json",
                    "spreadsheet",
                    "batch_analysis",
                },
            )
            source_paths = {artifact.source_path for artifact in adapter.artifacts}
            self.assertIn(str(raw_scrape).replace("\\", "/"), source_paths)
            self.assertIn(str(daily_selection).replace("\\", "/"), source_paths)
            self.assertTrue(
                all(Path(artifact.source_path).is_file() for artifact in adapter.artifacts)
            )

    def test_disabled_publication_still_generates_local_outputs_without_cloud_adapter(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            _raw_scrape, daily_selection = write_daily_inputs(temp_path)

            run_folder = create_run(
                Namespace(
                    mode="daily",
                    batch_size=1,
                    runs_dir=temp_path / "runs",
                    outputs_dir=temp_path / "outputs",
                    config=None,
                    candidates=daily_selection,
                    timestamp="2026-05-09T01:00:00Z",
                    gemini_adapter=FakeGeminiAdapter(),
                    cloud_publication_enabled=False,
                )
            )

            self.assertTrue((run_folder / "batch_index.md").is_file())
            self.assertTrue((run_folder / "data" / "structured_batch_analysis.json").is_file())
            self.assertFalse((run_folder / "logs" / "cloud_publication.json").exists())

    def test_failed_publication_reports_error_without_marking_cloud_run_complete(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            _raw_scrape, daily_selection = write_daily_inputs(temp_path)

            from batch_analysis.cloud_publication import CloudPublicationError

            with self.assertRaises(CloudPublicationError) as raised:
                create_run(
                    Namespace(
                        mode="daily",
                        batch_size=1,
                        runs_dir=temp_path / "runs",
                        outputs_dir=temp_path / "outputs",
                        config=None,
                        candidates=daily_selection,
                        timestamp="2026-05-09T01:00:00Z",
                        gemini_adapter=FakeGeminiAdapter(),
                        cloud_publication_enabled=True,
                        cloud_publication_adapter=FailingPublicationAdapter(),
                    )
                )

            self.assertIn("cloud publication failed", str(raised.exception))
            run_folder = raised.exception.run_folder
            self.assertIsNotNone(run_folder)
            self.assertTrue((run_folder / "data" / "structured_batch_analysis.json").is_file())
            publication_log = json.loads(
                (run_folder / "logs" / "cloud_publication.json").read_text(encoding="utf-8")
            )
            self.assertEqual(publication_log["status"], "failed")
            self.assertIn("Supabase artifact upsert failed", publication_log["errors"][0])


if __name__ == "__main__":
    unittest.main()
