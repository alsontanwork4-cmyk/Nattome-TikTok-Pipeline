import json
import tempfile
import unittest
from pathlib import Path

from dashboard.run_publication import (
    artifact_uploads,
    build_run_record,
    raw_video_records,
    selected_video_records,
)


class DashboardRunPublicationTest(unittest.TestCase):
    def test_builds_manual_run_record_and_video_rows(self):
        selected_batch = {
            "selected_at": "2026-05-10T08:00:00+08:00",
            "input_candidate_count": 2,
            "eligible_candidate_count": 1,
            "selected_candidate_count": 1,
            "selected_candidates": [
                {
                    "id": "video-1",
                    "rank": 1,
                    "url": "https://tiktok.test/video-1",
                    "play_count": 1000,
                }
            ],
            "excluded_candidates": [{"id": "video-2", "play_count": 50}],
        }

        run = build_run_record(
            "manual-1",
            manifest={"run_timestamp": "2026-05-10T08:00:00+08:00", "mode": "daily"},
            selected_batch=selected_batch,
            metadata={"triggered_by": "owner@example.com"},
            manual_run={"run_type": "full_pipeline", "requested_at": "2026-05-10T00:00:00Z"},
        )
        raw_rows = raw_video_records("manual-1", selected_batch)
        selected_rows = selected_video_records(
            "manual-1",
            selected_batch,
            default_selection_reason="dashboard worker",
            default_evidence_status="published",
        )

        self.assertEqual(run["run_type"], "full_pipeline")
        self.assertEqual(run["selected_count"], 1)
        self.assertEqual({row["video_id"] for row in raw_rows}, {"video-1", "video-2"})
        self.assertEqual(selected_rows[0]["evidence_status"], "published")

    def test_builds_artifact_upload_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "20260510T010000_daily"
            (run_folder / "reports").mkdir(parents=True)
            (run_folder / "run_manifest.json").write_text(
                json.dumps({"run_timestamp": "2026-05-10T01:00:00Z", "mode": "daily"}),
                encoding="utf-8",
            )
            (run_folder / "reports" / "selected_batch.md").write_text(
                "# Selected batch\n",
                encoding="utf-8",
            )

            run = build_run_record(
                run_folder.name,
                manifest={"run_timestamp": "2026-05-10T01:00:00Z", "mode": "daily"},
                selected_batch={"selected_candidate_count": 3},
                metadata={"triggered_by": "dashboard-worker"},
            )
            uploads = artifact_uploads(
                run_folder,
                run_id=run["run_id"],
                storage_bucket="dashboard-artifacts",
            )

            object_paths = {upload.metadata.object_path for upload in uploads}
            self.assertEqual(run["triggered_by"], "dashboard-worker")
            self.assertIn(
                "runs/20260510T010000_daily/reports/selected_batch.md",
                object_paths,
            )


if __name__ == "__main__":
    unittest.main()
