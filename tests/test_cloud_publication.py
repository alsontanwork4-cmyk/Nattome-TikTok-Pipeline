import unittest
from pathlib import Path

from batch_analysis.cloud_publication import (
    CloudArtifactRecord,
    CloudPublicationConfigurationError,
    CloudRunRecord,
    SupabasePublicationAdapter,
    artifact_record_from_path,
    build_cloud_run_record,
    missing_cloud_environment,
    supabase_publication_adapter_from_env,
)


class FakeSupabaseClient:
    def __init__(self, failing_storage_paths=None):
        self.upserts = []
        self.failing_storage_paths = set(failing_storage_paths or [])

    def table(self, table_name):
        return FakeSupabaseTable(self, table_name)


class FakeSupabaseTable:
    def __init__(self, client, table_name):
        self.client = client
        self.table_name = table_name

    def upsert(self, payload, on_conflict=None):
        self.client.upserts.append(
            {
                "table": self.table_name,
                "payload": payload,
                "on_conflict": on_conflict,
            }
        )
        return self

    def execute(self):
        payload = self.client.upserts[-1]["payload"]
        if payload.get("storage_path") in self.client.failing_storage_paths:
            raise RuntimeError("Supabase artifact upsert failed")
        return {"data": []}


class CloudPublicationTest(unittest.TestCase):
    def test_publication_interface_can_create_or_update_cloud_run_record(self):
        client = FakeSupabaseClient()
        adapter = SupabasePublicationAdapter(client)
        run = CloudRunRecord(
            run_id="20260509T010000Z_daily",
            status="completed",
            run_timestamp="2026-05-09T01:00:00Z",
            report_date="2026-05-09",
            mode="daily",
            requested_batch_size=5,
            summary={"selected_candidate_count": 5, "source_video_count": 5},
            publication_status="pending",
            publication_errors=[],
            local_run_folder="runs/batch-analysis/20260509T010000Z_daily",
        )

        result = adapter.upsert_run(run)

        self.assertEqual(result.status, "succeeded")
        self.assertEqual(len(client.upserts), 1)
        upsert = client.upserts[0]
        self.assertEqual(upsert["table"], "daily_evidence_runs")
        self.assertEqual(upsert["on_conflict"], "run_id")
        self.assertEqual(upsert["payload"]["run_id"], "20260509T010000Z_daily")
        self.assertEqual(upsert["payload"]["status"], "completed")
        self.assertEqual(upsert["payload"]["report_date"], "2026-05-09")
        self.assertEqual(upsert["payload"]["summary"]["source_video_count"], 5)

    def test_publication_interface_can_publish_required_artifact_records(self):
        client = FakeSupabaseClient()
        adapter = SupabasePublicationAdapter(client)
        artifacts = [
            CloudArtifactRecord(
                run_id="20260509T010000Z_daily",
                artifact_type=artifact_type,
                storage_path=f"daily-runs/20260509T010000Z_daily/{filename}",
                source_path=f"outputs/{filename}",
                filename=filename,
                content_type=content_type,
            )
            for artifact_type, filename, content_type in [
                ("markdown", "report.md", "text/markdown"),
                ("json", "structured_batch_analysis.json", "application/json"),
                (
                    "spreadsheet",
                    "planning.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
                ("raw_scrape", "raw_scrape_top30.json", "application/json"),
                ("daily_selection", "daily_selection_top3.json", "application/json"),
                ("batch_analysis", "run_manifest.json", "application/json"),
            ]
        ]

        result = adapter.publish_artifacts(artifacts)

        self.assertEqual(result.status, "succeeded")
        self.assertEqual(
            [upsert["payload"]["artifact_type"] for upsert in client.upserts],
            [
                "markdown",
                "json",
                "spreadsheet",
                "raw_scrape",
                "daily_selection",
                "batch_analysis",
            ],
        )
        self.assertTrue(
            all(upsert["table"] == "daily_evidence_artifacts" for upsert in client.upserts)
        )
        self.assertTrue(
            all(upsert["on_conflict"] == "artifact_id" for upsert in client.upserts)
        )
        self.assertEqual(client.upserts[0]["payload"]["filename"], "report.md")
        self.assertEqual(client.upserts[0]["payload"]["content_type"], "text/markdown")

    def test_failed_artifact_publication_does_not_mark_run_fully_successful(self):
        client = FakeSupabaseClient(
            failing_storage_paths={"daily-runs/20260509T010000Z_daily/report.md"}
        )
        adapter = SupabasePublicationAdapter(client)
        run = CloudRunRecord(
            run_id="20260509T010000Z_daily",
            status="completed",
            run_timestamp="2026-05-09T01:00:00Z",
            report_date="2026-05-09",
            mode="daily",
            requested_batch_size=5,
            summary={},
            publication_status="pending",
            publication_errors=[],
            local_run_folder="runs/batch-analysis/20260509T010000Z_daily",
        )
        artifacts = [
            CloudArtifactRecord(
                run_id=run.run_id,
                artifact_type="markdown",
                storage_path="daily-runs/20260509T010000Z_daily/report.md",
                source_path="outputs/report.md",
                filename="report.md",
                content_type="text/markdown",
            )
        ]

        result = adapter.publish_run_with_artifacts(run, artifacts)

        self.assertEqual(result.status, "failed")
        self.assertIn("Supabase artifact upsert failed", result.errors[0])
        run_payloads = [
            upsert["payload"]
            for upsert in client.upserts
            if upsert["table"] == "daily_evidence_runs"
        ]
        self.assertEqual(run_payloads[-1]["publication_status"], "artifact_failed")
        self.assertNotEqual(run_payloads[-1]["publication_status"], "published")
        self.assertTrue(run_payloads[-1]["publication_errors"])

    def test_builders_create_compact_cloud_records_from_completed_run_inputs(self):
        run_folder = Path("runs/batch-analysis/20260509T010000Z_daily")
        metadata = {
            "run_timestamp": "2026-05-09T01:00:00Z",
            "mode": "daily",
            "requested_batch_size": 5,
        }
        manifest = {
            "phases": [
                {"name": "candidate_selection", "status": "completed"},
                {"name": "gemini_evidence", "status": "completed"},
            ]
        }
        summary = {
            "selected_candidate_count": 5,
            "source_video_count": 5,
            "recommendation": {"what_to_shoot_first": "Evidence-led gut routine"},
        }

        run = build_cloud_run_record(run_folder, metadata, manifest, summary)
        artifact = artifact_record_from_path(
            run_id=run.run_id,
            artifact_type="spreadsheet",
            source_path=Path("outputs/reports/2026-05-09/planning.xlsx"),
        )

        self.assertEqual(run.run_id, "20260509T010000Z_daily")
        self.assertEqual(run.status, "completed")
        self.assertEqual(run.report_date, "2026-05-09")
        self.assertEqual(run.publication_status, "pending")
        self.assertEqual(run.summary["source_video_count"], 5)
        self.assertEqual(artifact.storage_path, "20260509T010000Z_daily/planning.xlsx")
        self.assertEqual(artifact.filename, "planning.xlsx")
        self.assertEqual(
            artifact.content_type,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def test_supabase_environment_check_reports_missing_names_without_secret_values(self):
        env = {
            "SUPABASE_URL": "https://project.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "",
        }

        missing = missing_cloud_environment(env)

        self.assertEqual(missing, ["SUPABASE_SERVICE_ROLE_KEY"])
        with self.assertRaises(CloudPublicationConfigurationError) as raised:
            supabase_publication_adapter_from_env(env)
        message = str(raised.exception)
        self.assertIn("SUPABASE_SERVICE_ROLE_KEY", message)
        self.assertNotIn("https://project.supabase.co", message)


if __name__ == "__main__":
    unittest.main()
