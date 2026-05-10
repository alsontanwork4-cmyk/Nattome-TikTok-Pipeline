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
        if table_name == "agent_settings_versions":
            self.data = [
                {
                    "version": 1,
                    "settings": {"table": table_name},
                    "is_active": True,
                }
            ]

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


class FakeRpc:
    def __init__(self, name: str, params: dict, recorder: list[tuple]):
        self.name = name
        self.params = params
        self.recorder = recorder
        self.data = [
            {
                "version": 1,
                "settings": params.get("p_settings"),
                "reason": params.get("p_reason"),
                "is_active": True,
                "rollback_of_version": params.get("p_rollback_of_version"),
                "created_by": params.get("p_created_by"),
                "updated_by": params.get("p_created_by"),
            }
        ]

    def execute(self):
        self.recorder.append((self.name, "execute"))
        return self


class FakeSupabase:
    def __init__(self):
        self.calls: list[tuple] = []
        self.storage = FakeStorage(self.calls)

    def table(self, table_name: str):
        self.calls.append(("client", "table", table_name))
        return FakeQuery(table_name, self.calls)

    def rpc(self, name: str, params: dict):
        self.calls.append(("client", "rpc", name, params))
        return FakeRpc(name, params, self.calls)


class DashboardSupabaseContractTest(unittest.TestCase):
    def test_contract_defines_dashboard_tables_and_required_fields(self):
        expected_tables = {
            "runs",
            "run_outputs",
            "raw_videos",
            "selected_videos",
            "scrape_settings_versions",
            "agent_settings_versions",
            "agent_trace_events",
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

        self.assertEqual(report.object_path, "")
        self.assertEqual(report_body, "# Report\n")
        self.assertEqual(raw_videos, [{"table": "raw_videos"}])
        self.assertEqual(selected_videos, [{"table": "selected_videos"}])
        self.assertIn(("run_outputs", "eq", "run_id", "run-1"), fake.calls)
        self.assertIn(("run_outputs", "eq", "artifact_type", "report"), fake.calls)
        self.assertIn(("dashboard-artifacts", "download", "runs/run-1/report.md"), fake.calls)
        self.assertIn(("raw_videos", "order", "play_count", True), fake.calls)
        self.assertIn(("raw_videos", "order", "video_id", False), fake.calls)

    def test_client_versions_settings(self):
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

        self.assertEqual(saved["version"], 1)
        self.assertEqual(saved["settings"], settings)
        self.assertEqual(saved["created_by"], "owner@example.com")
        self.assertIn(("scrape_settings_versions", "order", "version", True), fake.calls)
        self.assertIn(
            (
                "client",
                "rpc",
                "save_scrape_settings_version",
                {
                    "p_settings": settings,
                    "p_reason": "Initial production settings",
                    "p_created_by": "owner@example.com",
                    "p_rollback_of_version": None,
                },
            ),
            fake.calls,
        )

    def test_client_versions_agent_settings_and_rolls_back(self):
        fake = FakeSupabase()
        client = DashboardSupabaseClient(fake, storage_bucket="dashboard-artifacts")
        settings = {
            "schema_version": 1,
            "agents": {
                "gemini_video_evidence": {
                    "enabled": True,
                    "model": "gemini-2.5-flash",
                    "prompt_sections": {"role": "Watch videos."},
                    "generation": {"temperature": 0.2},
                    "advanced_generation_config": {},
                }
            },
        }

        saved = client.save_agent_settings_version(
            settings,
            reason="Tune evidence extraction",
            user="owner@example.com",
        )
        rolled_back = client.rollback_agent_settings_version(
            target_version=1,
            reason="Restore prior agent config",
            user="owner@example.com",
        )

        self.assertEqual(saved["version"], 1)
        self.assertEqual(saved["settings"], settings)
        self.assertEqual(rolled_back["rollback_of_version"], 1)
        self.assertIn(("agent_settings_versions", "order", "version", True), fake.calls)
        self.assertIn(
            (
                "client",
                "rpc",
                "save_agent_settings_version",
                {
                    "p_settings": settings,
                    "p_reason": "Tune evidence extraction",
                    "p_created_by": "owner@example.com",
                    "p_rollback_of_version": None,
                },
            ),
            fake.calls,
        )
        self.assertIn(
            (
                "client",
                "rpc",
                "save_agent_settings_version",
                {
                    "p_settings": {"table": "agent_settings_versions"},
                    "p_reason": "Restore prior agent config",
                    "p_created_by": "owner@example.com",
                    "p_rollback_of_version": 1,
                },
            ),
            fake.calls,
        )

    def test_client_upserts_and_lists_agent_trace_events(self):
        fake = FakeSupabase()
        client = DashboardSupabaseClient(fake, storage_bucket="dashboard-artifacts")
        event = {
            "event_id": "trace-1",
            "run_id": "run-1",
            "agent": "gemini_video_evidence",
            "candidate_id": "video-1",
            "candidate_prefix": "001_video-1",
            "substep": "generating_evidence",
            "status": "completed",
            "started_at": "2026-05-10T00:00:00+00:00",
            "ended_at": "2026-05-10T00:00:01+00:00",
            "duration_ms": 1000,
            "config_source": "supabase",
            "config_version": 4,
            "artifact_references": ["data/001_video-1_gemini_evidence.json"],
            "uploaded_file": {"uri": "gemini://file"},
            "usage_metadata": {"total_token_count": 42},
            "error_summary": "",
        }

        upserted = client.upsert_agent_trace_event(event)
        run_events = client.list_agent_trace_events(run_id="run-1", limit=25)
        recent_events = client.list_recent_agent_trace_events(limit=10)

        self.assertEqual(upserted[0]["event_id"], "trace-1")
        self.assertEqual(run_events, [{"table": "agent_trace_events"}])
        self.assertEqual(recent_events, [{"table": "agent_trace_events"}])
        self.assertIn(("agent_trace_events", "upsert", event, "event_id"), fake.calls)
        self.assertIn(("agent_trace_events", "eq", "run_id", "run-1"), fake.calls)
        self.assertIn(("agent_trace_events", "order", "started_at", True), fake.calls)
        self.assertIn(("agent_trace_events", "limit", 25), fake.calls)
        self.assertIn(("agent_trace_events", "limit", 10), fake.calls)

if __name__ == "__main__":
    unittest.main()
