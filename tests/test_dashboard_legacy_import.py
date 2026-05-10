import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from dashboard.legacy_import import import_legacy_artifacts


class FakeDashboardImportClient:
    def __init__(self):
        self.runs = {}
        self.artifacts = {}
        self.uploads = []
        self.curation = []

    def upsert_run(self, record: dict):
        self.runs[record["run_id"]] = record
        return record

    def upload_artifact_file(self, source_path: Path, metadata):
        self.uploads.append((Path(source_path), metadata.object_path))

    def upsert_artifact_metadata(self, metadata):
        self.artifacts[(metadata.run_id, metadata.object_path)] = metadata
        return [metadata.to_record()]

    def upsert_video_curation(
        self,
        video_id: str,
        *,
        labels: list[str],
        note: str,
        exclude_similar_reason: str,
        user: str,
    ):
        record = {
            "video_id": video_id,
            "labels": labels,
            "note": note,
            "exclude_similar_reason": exclude_similar_reason,
            "user": user,
        }
        self.curation.append(record)
        return record


class DashboardLegacyImportTest(unittest.TestCase):
    def test_import_uploads_legacy_run_artifacts_and_upserts_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            run_folder = workspace / "runs" / "batch-analysis" / "20260510T010000_daily"
            (run_folder / "data").mkdir(parents=True)
            (run_folder / "reports").mkdir()
            self._write_json(
                run_folder / "run_manifest.json",
                {
                    "run_timestamp": "2026-05-10T01:00:00Z",
                    "mode": "daily",
                    "phases": [{"name": "pipeline", "status": "completed"}],
                },
            )
            self._write_json(
                run_folder / "run_metadata.json",
                {"config_version": "v3", "triggered_by": "legacy-worker"},
            )
            self._write_json(
                run_folder / "data" / "selected_batch.json",
                {
                    "input_candidate_count": 30,
                    "eligible_candidate_count": 8,
                    "selected_candidate_count": 3,
                    "selected_candidates": [{"id": "video-1"}, {"id": "video-2"}],
                },
            )
            (run_folder / "reports" / "selected_batch.md").write_text(
                "# Selected batch\n",
                encoding="utf-8",
            )
            client = FakeDashboardImportClient()

            summary = import_legacy_artifacts(workspace, client, storage_bucket="dashboard-artifacts")
            import_legacy_artifacts(workspace, client, storage_bucket="dashboard-artifacts")

            self.assertEqual(summary.runs, 1)
            self.assertEqual(summary.artifacts, 4)
            self.assertEqual(set(client.runs), {"20260510T010000_daily"})
            run = client.runs["20260510T010000_daily"]
            self.assertEqual(run["status"], "succeeded")
            self.assertEqual(run["run_type"], "daily")
            self.assertEqual(run["raw_candidate_count"], 30)
            self.assertEqual(run["eligible_candidate_count"], 8)
            self.assertEqual(run["selected_count"], 3)
            object_paths = {metadata.object_path for metadata in client.artifacts.values()}
            self.assertIn("runs/20260510T010000_daily/reports/selected_batch.md", object_paths)
            report_metadata = client.artifacts[
                (
                    "20260510T010000_daily",
                    "runs/20260510T010000_daily/reports/selected_batch.md",
                )
            ]
            self.assertEqual(report_metadata.bucket, "dashboard-artifacts")
            self.assertEqual(report_metadata.content_type, "text/markdown")
            self.assertTrue(str(report_metadata.checksum).startswith("sha256:"))
            self.assertEqual(len(client.uploads), 8)
            self.assertEqual(len(client.artifacts), 4)

    def test_optional_legacy_sqlite_import_reads_curation_once_without_runtime_store(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            sqlite_path = workspace / "legacy.sqlite3"
            connection = sqlite3.connect(sqlite_path)
            try:
                connection.execute(
                    """
                    CREATE TABLE video_curation (
                        tiktok_video_id TEXT PRIMARY KEY,
                        labels TEXT,
                        note TEXT,
                        exclude_similar_reason TEXT,
                        updated_by TEXT
                    )
                    """
                )
                connection.execute(
                    """
                    INSERT INTO video_curation (
                        tiktok_video_id,
                        labels,
                        note,
                        exclude_similar_reason,
                        updated_by
                    )
                    VALUES ('video-1', '["Relevant"]', 'Strong hook', '', 'ops@example.com')
                    """
                )
                connection.commit()
            finally:
                connection.close()
            client = FakeDashboardImportClient()

            summary = import_legacy_artifacts(
                workspace,
                client,
                storage_bucket="dashboard-artifacts",
                legacy_sqlite_path=sqlite_path,
            )

            self.assertEqual(summary.curation_records, 1)
            self.assertEqual(client.curation[0]["video_id"], "video-1")
            self.assertEqual(client.curation[0]["labels"], ["Relevant"])
            self.assertFalse((workspace / "data" / "dashboard" / "dashboard.sqlite3").exists())

    def _write_json(self, path: Path, payload: dict) -> None:
        path.write_text(json.dumps(payload), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
