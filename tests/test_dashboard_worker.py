import unittest

from dashboard.supabase_client import ArtifactMetadata
from dashboard.worker import WorkerRunResult, run_manual_worker_once


class FakeDashboardDataClient:
    def __init__(self):
        self.claimed = None
        self.status_updates = []
        self.artifacts = []

    def claim_queued_manual_run(self, *, worker_id: str):
        return self.claimed

    def mark_manual_run_status(self, run_id: str, *, status: str, error_summary: str = ""):
        self.status_updates.append(
            {
                "run_id": run_id,
                "status": status,
                "error_summary": error_summary,
            }
        )

    def upsert_artifact_metadata(self, metadata: ArtifactMetadata):
        self.artifacts.append(metadata)
        return [metadata.to_record()]


class DashboardWorkerTest(unittest.TestCase):
    def test_worker_claims_queued_run_and_marks_success_with_artifact_metadata(self):
        data_client = FakeDashboardDataClient()
        data_client.claimed = {
            "id": "manual-1",
            "run_id": "run-1",
            "status": "running",
            "run_type": "full_pipeline",
        }
        artifact = ArtifactMetadata(
            run_id="run-1",
            artifact_type="report",
            bucket="dashboard-artifacts",
            object_path="runs/run-1/report.md",
            filename="report.md",
        )

        result = run_manual_worker_once(
            data_client,
            worker_id="worker-a",
            runner=lambda run: WorkerRunResult(status="succeeded", artifacts=[artifact]),
        )

        self.assertEqual(result, "succeeded")
        self.assertEqual(data_client.artifacts, [artifact])
        self.assertEqual(
            data_client.status_updates,
            [{"run_id": "run-1", "status": "succeeded", "error_summary": ""}],
        )

    def test_worker_failure_updates_visible_status_without_secret_values(self):
        data_client = FakeDashboardDataClient()
        data_client.claimed = {
            "id": "manual-1",
            "run_id": "run-1",
            "status": "running",
            "run_type": "full_pipeline",
        }

        result = run_manual_worker_once(
            data_client,
            worker_id="worker-a",
            runner=lambda run: (_ for _ in ()).throw(
                RuntimeError("SUPABASE_SERVICE_ROLE_KEY=secret-value\nApify unavailable")
            ),
        )

        self.assertEqual(result, "failed")
        self.assertEqual(data_client.status_updates[0]["status"], "failed")
        self.assertIn("[redacted secret]", data_client.status_updates[0]["error_summary"])
        self.assertIn("Apify unavailable", data_client.status_updates[0]["error_summary"])
        self.assertNotIn("secret-value", data_client.status_updates[0]["error_summary"])


if __name__ == "__main__":
    unittest.main()
