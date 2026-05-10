import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from dashboard.indexer import index_pipeline_artifacts
from dashboard.store import DASHBOARD_DB_PATH, initialize_dashboard_store


class DashboardArtifactIndexerTest(unittest.TestCase):
    def test_reindex_normalizes_pipeline_artifacts_without_deleting_curation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_fixture_workspace(workspace)
            db_path = initialize_dashboard_store(workspace)
            connection = sqlite3.connect(db_path)
            try:
                connection.execute(
                    """
                    INSERT INTO video_curation (
                        tiktok_video_id,
                        labels,
                        note,
                        created_by,
                        updated_by
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        "video-1",
                        json.dumps(["Great Hook"]),
                        "Keep this hook pattern.",
                        "tester",
                        "tester",
                    ),
                )
                connection.commit()
            finally:
                connection.close()

            summary = index_pipeline_artifacts(workspace)
            summary_after_reindex = index_pipeline_artifacts(workspace)

            self.assertEqual(summary.raw_videos, 2)
            self.assertEqual(summary.selected_batches, 1)
            self.assertEqual(summary.batch_runs, 1)
            self.assertEqual(summary_after_reindex.raw_videos, 2)

            connection = sqlite3.connect(workspace / DASHBOARD_DB_PATH)
            connection.row_factory = sqlite3.Row
            try:
                videos = {
                    row["video_id"]: dict(row)
                    for row in connection.execute(
                        "SELECT * FROM raw_videos ORDER BY video_id"
                    )
                }
                selected = dict(
                    connection.execute(
                        "SELECT * FROM selected_batches WHERE run_id = ?",
                        ("20260507T000000Z_default",),
                    ).fetchone()
                )
                outputs = {
                    row["artifact_type"]: dict(row)
                    for row in connection.execute(
                        "SELECT * FROM run_outputs WHERE run_id = ?",
                        ("20260507T000000Z_default",),
                    )
                }
                curation = connection.execute(
                    "SELECT labels, note FROM video_curation WHERE tiktok_video_id = ?",
                    ("video-1",),
                ).fetchone()
            finally:
                connection.close()

            self.assertEqual(videos["video-1"]["tiktok_url"], "https://tiktok.test/video-1")
            self.assertEqual(videos["video-1"]["author_handle"], "nattomecreator")
            self.assertEqual(videos["video-1"]["caption"], "Gut health hook")
            self.assertEqual(json.loads(videos["video-1"]["hashtags_json"]), ["guthealth"])
            self.assertEqual(videos["video-1"]["source_input"], "#guthealth")
            self.assertEqual(videos["video-1"]["play_count"], 12000)
            self.assertEqual(videos["video-1"]["like_count"], 900)
            self.assertEqual(videos["video-1"]["comment_count"], 20)
            self.assertEqual(videos["video-1"]["share_count"], 80)
            self.assertEqual(videos["video-1"]["created_at"], "2026-05-07T00:00:00Z")
            self.assertEqual(videos["video-1"]["is_downloadable"], 1)
            self.assertEqual(videos["video-1"]["run_id"], "20260507T000000Z_default")
            self.assertEqual(videos["video-1"]["selection_status"], "analyzed")

            self.assertEqual(videos["video-2"]["selection_status"], "raw")
            self.assertEqual(selected["candidate_source"], "data/raw_scrapes/sample_raw.json")
            self.assertIn("manifest", outputs)
            self.assertIn("selected_batch", outputs)
            self.assertEqual(json.loads(curation["labels"]), ["Great Hook"])
            self.assertEqual(curation["note"], "Keep this hook pattern.")

    def _write_fixture_workspace(self, workspace: Path) -> None:
        raw_scrapes = workspace / "data" / "raw_scrapes"
        run_folder = workspace / "runs" / "batch-analysis" / "20260507T000000Z_default"
        for folder in [raw_scrapes, run_folder / "data"]:
            folder.mkdir(parents=True, exist_ok=True)

        (raw_scrapes / "sample_raw.json").write_text(
            json.dumps(
                {
                    "generated_at": "2026-05-07T00:01:00Z",
                    "scope": "hashtags",
                    "top": [
                        {
                            "id": "video-1",
                            "url": "https://tiktok.test/video-1",
                            "author_handle": "nattomecreator",
                            "caption": "Gut health hook",
                            "hashtags": ["guthealth"],
                            "source_input": "#guthealth",
                            "video_download_url": "https://download.test/video-1.mp4",
                            "play_count": 12000,
                            "like_count": 900,
                            "comment_count": 20,
                            "share_count": 80,
                            "created_at": "2026-05-07T00:00:00Z",
                        },
                        {
                            "id": "video-2",
                            "url": "https://tiktok.test/video-2",
                            "author_handle": "othercreator",
                            "caption": "Less relevant",
                            "hashtags": [],
                            "source_input": "#guthealth",
                            "video_download_url": "",
                            "play_count": 8000,
                            "like_count": 100,
                            "comment_count": 2,
                            "share_count": 1,
                            "created_at": "2026-05-06T00:00:00Z",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        (run_folder / "run_manifest.json").write_text(
            json.dumps(
                {
                    "run_timestamp": "2026-05-07T00:00:00Z",
                    "mode": "default",
                    "requested_batch_size": 1,
                    "configuration": {"selection": {"minimum_views": 10000}},
                    "outputs": {},
                    "phases": [{"name": "source_video_snapshots", "status": "completed"}],
                }
            ),
            encoding="utf-8",
        )
        (run_folder / "run_metadata.json").write_text(
            json.dumps({"run_timestamp": "2026-05-07T00:00:00Z", "mode": "default"}),
            encoding="utf-8",
        )
        (run_folder / "data" / "selected_batch.json").write_text(
            json.dumps(
                {
                    "selected_at": "2026-05-07T00:02:00Z",
                    "candidate_source": "data/raw_scrapes/sample_raw.json",
                    "selected_candidate_count": 1,
                    "selected_candidates": [{"id": "video-1", "rank": 1}],
                }
            ),
            encoding="utf-8",
        )
        (run_folder / "data" / "001_video-1_source_metadata.json").write_text(
            json.dumps({"id": "video-1", "rank": 1}),
            encoding="utf-8",
        )
        (run_folder / "logs").mkdir()
        (run_folder / "logs" / "pipeline.log").write_text("ok\n", encoding="utf-8")
