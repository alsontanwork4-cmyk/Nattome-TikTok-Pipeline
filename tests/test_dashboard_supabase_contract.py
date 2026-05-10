import unittest

from dashboard.supabase_client import (
    ARTIFACT_METADATA_FIELDS,
    DASHBOARD_TABLE_CONTRACT,
    ArtifactMetadata,
    DashboardSupabaseClient,
)


class FakeQuery:
    def __init__(self, table_name: str, recorder: list[tuple]):
        self.table_name = table_name
        self.recorder = recorder
        self.data = [{"table": table_name}]

    def select(self, columns: str):
        self.recorder.append((self.table_name, "select", columns))
        return self

    def eq(self, column: str, value: object):
        self.recorder.append((self.table_name, "eq", column, value))
        return self

    def order(self, column: str, desc: bool = False):
        self.recorder.append((self.table_name, "order", column, desc))
        return self

    def limit(self, count: int):
        self.recorder.append((self.table_name, "limit", count))
        return self

    def upsert(self, record: dict, on_conflict: str | None = None):
        self.recorder.append((self.table_name, "upsert", record, on_conflict))
        self.data = [record]
        return self

    def update(self, record: dict):
        self.recorder.append((self.table_name, "update", record))
        self.data = [record]
        return self

    def insert(self, record: dict):
        self.recorder.append((self.table_name, "insert", record))
        self.data = [record]
        return self

    def execute(self):
        self.recorder.append((self.table_name, "execute"))
        return self


class FakeStorageBucket:
    def __init__(self, bucket_name: str, recorder: list[tuple]):
        self.bucket_name = bucket_name
        self.recorder = recorder

    def create_signed_url(self, object_path: str, expires_in: int):
        self.recorder.append((self.bucket_name, "create_signed_url", object_path, expires_in))
        return {"signedURL": f"https://storage.example/{self.bucket_name}/{object_path}"}

    def download(self, object_path: str):
        self.recorder.append((self.bucket_name, "download", object_path))
        return b"# Report\n"

    def upload(self, object_path: str, payload: bytes, file_options: dict):
        self.recorder.append(
            (
                self.bucket_name,
                "upload",
                object_path,
                payload,
                file_options,
            )
        )
        return {"path": object_path}


class FakeStorage:
    def __init__(self, recorder: list[tuple]):
        self.recorder = recorder

    def from_(self, bucket_name: str):
        self.recorder.append(("storage", "from", bucket_name))
        return FakeStorageBucket(bucket_name, self.recorder)


class FakeSupabase:
    def __init__(self):
        self.calls: list[tuple] = []
        self.storage = FakeStorage(self.calls)

    def table(self, table_name: str):
        self.calls.append(("client", "table", table_name))
        return FakeQuery(table_name, self.calls)


class DashboardSupabaseContractTest(unittest.TestCase):
    def test_contract_defines_dashboard_tables_and_required_fields(self):
        expected_tables = {
            "runs",
            "run_outputs",
            "raw_videos",
            "selected_videos",
            "video_curation",
            "scrape_settings_versions",
            "manual_runs",
        }

        self.assertEqual(set(DASHBOARD_TABLE_CONTRACT), expected_tables)
        for table_name, fields in DASHBOARD_TABLE_CONTRACT.items():
            with self.subTest(table=table_name):
                self.assertIn("created_at", fields)
                self.assertGreaterEqual(len(fields), 4)

        self.assertTrue(
            {
                "bucket",
                "object_path",
                "size_bytes",
                "checksum",
                "created_at",
                "run_id",
            }.issubset(ARTIFACT_METADATA_FIELDS)
        )

    def test_artifact_metadata_normalizes_storage_record(self):
        metadata = ArtifactMetadata(
            run_id="run-1",
            artifact_type="report",
            bucket="dashboard-artifacts",
            object_path="runs/run-1/report.md",
            filename="report.md",
            content_type="text/markdown",
            size_bytes=1234,
            checksum="sha256:abc",
            created_at="2026-05-10T01:00:00Z",
        )

        self.assertEqual(
            metadata.to_record(),
            {
                "run_id": "run-1",
                "artifact_type": "report",
                "bucket": "dashboard-artifacts",
                "object_path": "runs/run-1/report.md",
                "filename": "report.md",
                "content_type": "text/markdown",
                "size_bytes": 1234,
                "checksum": "sha256:abc",
                "created_at": "2026-05-10T01:00:00Z",
            },
        )

    def test_client_lists_runs_and_run_detail_with_supabase_style_queries(self):
        fake = FakeSupabase()
        client = DashboardSupabaseClient(fake, storage_bucket="dashboard-artifacts")

        runs = client.list_runs(limit=25)
        run = client.get_run("run-1")
        outputs = client.list_run_outputs("run-1")
        artifact = client.get_artifact_metadata("runs/run-1/report.md")

        self.assertEqual(runs, [{"table": "runs"}])
        self.assertEqual(run, {"table": "runs"})
        self.assertEqual(outputs, [{"table": "run_outputs"}])
        self.assertEqual(artifact.object_path, "runs/run-1/report.md")
        self.assertIn(("client", "table", "runs"), fake.calls)
        self.assertIn(("runs", "order", "started_at", True), fake.calls)
        self.assertIn(("runs", "limit", 25), fake.calls)
        self.assertIn(("runs", "eq", "run_id", "run-1"), fake.calls)
        self.assertIn(("run_outputs", "eq", "run_id", "run-1"), fake.calls)
        self.assertIn(
            ("run_outputs", "eq", "object_path", "runs/run-1/report.md"),
            fake.calls,
        )

    def test_client_writes_manual_runs_and_artifact_metadata(self):
        fake = FakeSupabase()
        client = DashboardSupabaseClient(fake, storage_bucket="dashboard-artifacts")
        metadata = ArtifactMetadata(
            run_id="run-1",
            artifact_type="report",
            bucket="dashboard-artifacts",
            object_path="runs/run-1/report.md",
            filename="report.md",
        )

        manual_run_result = client.upsert_manual_run(
            {
                "id": "manual-1",
                "status": "queued",
                "triggered_by": "owner@example.com",
                "created_at": "2026-05-10T01:00:00Z",
            }
        )
        artifact_result = client.upsert_artifact_metadata(metadata)
        run_result = client.upsert_run(
            {
                "run_id": "run-1",
                "status": "succeeded",
                "run_type": "daily",
                "created_at": "2026-05-10T01:00:00Z",
            }
        )

        self.assertEqual(manual_run_result[0]["id"], "manual-1")
        self.assertEqual(artifact_result[0]["object_path"], "runs/run-1/report.md")
        self.assertEqual(run_result["run_id"], "run-1")
        self.assertIn(("manual_runs", "upsert", manual_run_result[0], "id"), fake.calls)
        self.assertIn(
            ("run_outputs", "upsert", artifact_result[0], "run_id,object_path"),
            fake.calls,
        )
        self.assertIn(("runs", "upsert", run_result, "run_id"), fake.calls)

    def test_client_creates_signed_artifact_url_from_metadata(self):
        fake = FakeSupabase()
        client = DashboardSupabaseClient(fake, storage_bucket="dashboard-artifacts")
        metadata = ArtifactMetadata(
            run_id="run-1",
            artifact_type="report",
            bucket="dashboard-artifacts",
            object_path="runs/run-1/report.md",
            filename="report.md",
        )

        signed_url = client.create_signed_artifact_url(metadata, expires_in=900)

        self.assertEqual(
            signed_url,
            "https://storage.example/dashboard-artifacts/runs/run-1/report.md",
        )
        self.assertIn(("storage", "from", "dashboard-artifacts"), fake.calls)
        self.assertIn(
            ("dashboard-artifacts", "create_signed_url", "runs/run-1/report.md", 900),
            fake.calls,
        )

    def test_client_uploads_artifact_file_to_storage_bucket(self):
        fake = FakeSupabase()
        client = DashboardSupabaseClient(fake, storage_bucket="dashboard-artifacts")
        metadata = ArtifactMetadata(
            run_id="run-1",
            artifact_type="report",
            bucket="dashboard-artifacts",
            object_path="runs/run-1/report.md",
            filename="report.md",
            content_type="text/markdown",
        )

        class SourcePath:
            def read_bytes(self):
                return b"# Report\n"

        client.upload_artifact_file(SourcePath(), metadata)

        self.assertIn(("storage", "from", "dashboard-artifacts"), fake.calls)
        self.assertIn(
            (
                "dashboard-artifacts",
                "upload",
                "runs/run-1/report.md",
                b"# Report\n",
                {"content-type": "text/markdown", "upsert": "true"},
            ),
            fake.calls,
        )

    def test_client_reads_report_artifacts_and_export_tables(self):
        fake = FakeSupabase()
        client = DashboardSupabaseClient(fake, storage_bucket="dashboard-artifacts")

        report = client.get_report_artifact("run-1")
        report_body = client.download_artifact_text(
            ArtifactMetadata(
                run_id="run-1",
                artifact_type="report",
                bucket="dashboard-artifacts",
                object_path="runs/run-1/report.md",
                filename="report.md",
            )
        )
        raw_videos = client.list_raw_videos()
        selected_videos = client.list_selected_videos()
        video_curation = client.list_video_curation()

        self.assertEqual(report.object_path, "")
        self.assertEqual(report_body, "# Report\n")
        self.assertEqual(raw_videos, [{"table": "raw_videos"}])
        self.assertEqual(selected_videos, [{"table": "selected_videos"}])
        self.assertEqual(video_curation, [{"table": "video_curation"}])
        self.assertIn(("run_outputs", "eq", "run_id", "run-1"), fake.calls)
        self.assertIn(("run_outputs", "eq", "artifact_type", "report"), fake.calls)
        self.assertIn(("dashboard-artifacts", "download", "runs/run-1/report.md"), fake.calls)
        self.assertIn(("raw_videos", "order", "play_count", True), fake.calls)
        self.assertIn(("raw_videos", "order", "video_id", False), fake.calls)

    def test_client_versions_settings_and_upserts_video_curation(self):
        fake = FakeSupabase()
        client = DashboardSupabaseClient(fake, storage_bucket="dashboard-artifacts")
        settings = {
            "hashtags": ["guthealth"],
            "keywords": ["bloating"],
            "competitor_profiles": ["gaviscon"],
            "scope": "all",
        }

        saved = client.save_settings_version(
            settings,
            reason="Initial production settings",
            user="owner@example.com",
        )
        curation = client.upsert_video_curation(
            "video-1",
            labels=["Relevant", "Good Nattome Fit"],
            note="Use for hook planning.",
            exclude_similar_reason="",
            user="owner@example.com",
        )

        self.assertEqual(saved["version"], 1)
        self.assertEqual(saved["settings"], settings)
        self.assertEqual(saved["created_by"], "owner@example.com")
        self.assertEqual(curation["video_id"], "video-1")
        self.assertEqual(curation["labels"], ["Relevant", "Good Nattome Fit"])
        self.assertEqual(curation["updated_by"], "owner@example.com")
        self.assertIn(("scrape_settings_versions", "order", "version", True), fake.calls)
        self.assertIn(("scrape_settings_versions", "update", {"is_active": False}), fake.calls)
        self.assertIn(("scrape_settings_versions", "eq", "is_active", True), fake.calls)
        self.assertIn(("video_curation", "upsert", curation, "video_id"), fake.calls)


if __name__ == "__main__":
    unittest.main()
