import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from dashboard.config import DashboardSettings
from dashboard.supabase_client import ArtifactMetadata
from dashboard.worker import (
    WorkerArtifact,
    WorkerRunResult,
    build_pipeline_runner,
    main,
    run_manual_worker_once,
    run_worker_loop,
)


class FakeDashboardDataClient:
    def __init__(self):
        self.claimed = None
        self.status_updates = []
        self.artifacts = []
        self.uploads = []
        self.runs = {}
        self.raw_videos = {}
        self.selected_videos = {}

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

    def upload_artifact_file(self, source_path: Path, metadata: ArtifactMetadata):
        self.uploads.append((Path(source_path), metadata))

    def upsert_run(self, record: dict):
        self.runs[record["run_id"]] = record
        return record

    def upsert_raw_videos(self, records: list[dict]):
        for record in records:
            self.raw_videos[(record["run_id"], record["video_id"])] = record
        return records

    def upsert_selected_videos(self, records: list[dict]):
        for record in records:
            self.selected_videos[(record["run_id"], record["video_id"])] = record
        return records


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

    def test_worker_uploads_artifacts_before_marking_success(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "report.md"
            source_path.write_text("# Report\n", encoding="utf-8")
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
                runner=lambda run: WorkerRunResult(
                    status="succeeded",
                    artifact_uploads=[WorkerArtifact(source_path, artifact)],
                ),
            )

            self.assertEqual(result, "succeeded")
            self.assertEqual(data_client.uploads, [(source_path, artifact)])
            self.assertEqual(data_client.artifacts, [artifact])
            self.assertEqual(data_client.status_updates[0]["status"], "succeeded")

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

    def test_worker_loop_can_run_one_poll_for_systemd_smoke_checks(self):
        data_client = FakeDashboardDataClient()

        result = run_worker_loop(
            data_client,
            worker_id="worker-a",
            runner=lambda run: WorkerRunResult(status="succeeded"),
            poll_interval_seconds=0,
            once=True,
            sleep=lambda seconds: None,
        )

        self.assertIsNone(result)

    def test_pipeline_runner_executes_existing_batch_path_and_prepares_publication(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            settings = DashboardSettings(
                workspace_path=workspace,
                runs_path=workspace / "runs",
                supabase_storage_bucket="pipeline-artifacts",
            )
            data_client = FakeDashboardDataClient()
            expected_config = workspace / "batch_analysis" / "scrape_config.json"

            def fake_discovery(run_folder: Path, config_path: Path, timestamp: str) -> Path:
                self.assertEqual(config_path, expected_config)
                self.assertEqual(timestamp, "2026-05-10T00:00:00+00:00")
                data_path = run_folder / "data"
                data_path.mkdir(parents=True)
                candidates_path = data_path / "daily_selection_top_videos.json"
                candidates_path.write_text(json.dumps({"top": []}), encoding="utf-8")
                return candidates_path

            def fake_create_run(args) -> Path:
                self.assertEqual(args.runs_dir, workspace / "runs" / "batch-analysis")
                self.assertEqual(args.config, expected_config)
                run_folder = args.runs_dir / "20260510T080000+0800_daily"
                (run_folder / "data").mkdir(parents=True, exist_ok=True)
                (run_folder / "reports").mkdir(parents=True, exist_ok=True)
                (run_folder / "run_manifest.json").write_text(
                    json.dumps(
                        {
                            "run_timestamp": "2026-05-10T08:00:00+08:00",
                            "mode": "daily",
                            "phases": [{"name": "pipeline", "status": "completed"}],
                        }
                    ),
                    encoding="utf-8",
                )
                (run_folder / "run_metadata.json").write_text(
                    json.dumps({"triggered_by": "owner@example.com"}),
                    encoding="utf-8",
                )
                (run_folder / "data" / "selected_batch.json").write_text(
                    json.dumps(
                        {
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
                            "excluded_candidates": [{"id": "video-2"}],
                        }
                    ),
                    encoding="utf-8",
                )
                (run_folder / "reports" / "selected_batch.md").write_text(
                    "# Selected batch\n",
                    encoding="utf-8",
                )
                return run_folder

            runner = build_pipeline_runner(
                settings,
                data_client,
                discovery_runner=fake_discovery,
                create_run_func=fake_create_run,
            )

            result = runner(
                {
                    "id": "manual-1",
                    "run_id": "manual-20260510-full",
                    "status": "running",
                    "run_type": "full_pipeline",
                    "triggered_by": "owner@example.com",
                    "requested_at": "2026-05-10T00:00:00+00:00",
                }
            )

            self.assertEqual(result.status, "succeeded")
            self.assertEqual(data_client.runs["manual-20260510-full"]["selected_count"], 1)
            self.assertIn(("manual-20260510-full", "video-1"), data_client.selected_videos)
            self.assertIn(("manual-20260510-full", "video-2"), data_client.raw_videos)
            object_paths = {upload.metadata.object_path for upload in result.artifact_uploads}
            self.assertIn(
                "runs/manual-20260510-full/reports/selected_batch.md",
                object_paths,
            )

    def test_worker_main_builds_settings_supabase_client_runner_and_poll_loop(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = DashboardSettings(
                workspace_path=Path(temp_dir),
                supabase_url="https://project.supabase.co",
                supabase_service_role_key="service-key",
            )
            fake_client = object()
            fake_runner = lambda run: WorkerRunResult()

            with (
                mock.patch("dashboard.worker.DashboardSettings.from_env", return_value=settings),
                mock.patch(
                    "dashboard.worker.build_dashboard_data_client",
                    return_value=fake_client,
                ) as build_client,
                mock.patch(
                    "dashboard.worker.build_pipeline_runner",
                    return_value=fake_runner,
                ) as build_runner,
                mock.patch("dashboard.worker.run_worker_loop") as loop,
            ):
                result = main(["--worker-id", "worker-a", "--poll-interval", "0", "--once"])

            self.assertEqual(result, 0)
            build_client.assert_called_once_with(settings, require_supabase=True)
            build_runner.assert_called_once_with(
                settings,
                fake_client,
                runs_dir=None,
                config_path=None,
            )
            loop.assert_called_once_with(
                fake_client,
                worker_id="worker-a",
                runner=fake_runner,
                poll_interval_seconds=0.0,
                once=True,
            )


if __name__ == "__main__":
    unittest.main()
