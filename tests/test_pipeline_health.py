import json
import tempfile
import unittest
from pathlib import Path

from dashboard.health import compute_pipeline_health
from dashboard.indexer import index_pipeline_artifacts
from dashboard.quality import compute_scrape_quality_scores
from dashboard.store import DASHBOARD_DB_PATH, initialize_dashboard_store


class PipelineHealthTest(unittest.TestCase):
    def test_completed_run_reports_plain_language_operational_health(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_fixture_workspace(
                workspace,
                run_id="20260507T000000Z_default",
                phases=[
                    {"name": "candidate_selection", "status": "completed"},
                    {"name": "evidence_bundles", "status": "completed"},
                    {"name": "gemini_evidence", "status": "completed"},
                    {"name": "structured_outputs", "status": "completed"},
                    {"name": "telegram_delivery", "status": "completed"},
                ],
                bundle_state="completed",
                with_source_video=True,
                with_gemini=True,
                with_report=True,
                with_excel=True,
                telegram_log={"status": "sent"},
            )
            initialize_dashboard_store(workspace)
            index_pipeline_artifacts(workspace)

            summaries = compute_pipeline_health(workspace)

            self.assertEqual(len(summaries), 1)
            summary = summaries[0]
            self.assertEqual(summary.run_id, "20260507T000000Z_default")
            self.assertEqual(summary.severity, "info")
            self.assertEqual(summary.status, "completed")
            self.assertIn("ready for marketer review", summary.impact_summary)
            self.assertEqual(
                {item.component for item in summary.items},
                {
                    "apify_scrape",
                    "raw_candidates",
                    "selected_batch",
                    "source_videos",
                    "gemini_evidence",
                    "report_generation",
                    "excel_generation",
                    "telegram_delivery",
                },
            )
            self.assertTrue(all(item.severity == "info" for item in summary.items))

    def test_partial_run_warns_when_some_artifacts_are_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_fixture_workspace(
                workspace,
                run_id="20260507T010000Z_default",
                phases=[
                    {"name": "candidate_selection", "status": "completed"},
                    {"name": "evidence_bundles", "status": "completed"},
                    {"name": "gemini_evidence", "status": "partial"},
                    {"name": "structured_outputs", "status": "completed"},
                    {"name": "telegram_delivery", "status": "completed"},
                ],
                bundle_state="partial",
                with_source_video=True,
                with_gemini=True,
                with_report=True,
                with_excel=True,
                telegram_log={"status": "sent"},
                video_count=2,
                source_video_count=1,
                gemini_count=1,
            )
            initialize_dashboard_store(workspace)
            index_pipeline_artifacts(workspace)

            summary = compute_pipeline_health(workspace)[0]

            self.assertEqual(summary.severity, "warning")
            self.assertEqual(summary.status, "partial")
            self.assertIn("partially ready", summary.impact_summary)
            source_videos = self._item(summary, "source_videos")
            gemini = self._item(summary, "gemini_evidence")
            self.assertEqual(source_videos.status, "partial")
            self.assertEqual(gemini.status, "partial")

    def test_failed_phase_includes_exception_drilldown(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_fixture_workspace(
                workspace,
                run_id="20260507T020000Z_default",
                phases=[
                    {"name": "candidate_selection", "status": "completed"},
                    {"name": "evidence_bundles", "status": "completed"},
                    {
                        "name": "gemini_evidence",
                        "status": "failed",
                        "exception": "Gemini quota exceeded",
                    },
                    {"name": "structured_outputs", "status": "completed"},
                    {"name": "telegram_delivery", "status": "completed"},
                ],
                bundle_state="missing",
                with_source_video=True,
                with_gemini=False,
                with_report=True,
                with_excel=True,
                telegram_log={"status": "sent"},
            )
            initialize_dashboard_store(workspace)
            index_pipeline_artifacts(workspace)

            summary = compute_pipeline_health(workspace)[0]

            self.assertEqual(summary.severity, "error")
            self.assertEqual(summary.status, "error")
            gemini = self._item(summary, "gemini_evidence")
            self.assertEqual(gemini.severity, "error")
            self.assertEqual(gemini.details["phase"], "gemini_evidence")
            self.assertEqual(gemini.details["exception_text"], "Gemini quota exceeded")
            self.assertIn("may be unavailable", gemini.impact)

    def test_blocked_run_reports_missing_prerequisites_and_persists_drilldown(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_fixture_workspace(
                workspace,
                run_id="20260507T030000Z_default",
                phases=[
                    {
                        "name": "candidate_selection",
                        "status": "blocked",
                        "reason": "Apify scrape returned no usable records",
                    },
                    {"name": "gemini_evidence", "status": "blocked"},
                ],
                bundle_state="missing",
                with_source_video=False,
                with_gemini=False,
                with_report=False,
                with_excel=False,
                telegram_log={"status": "skipped", "reason": "no report"},
                with_raw=False,
                with_selected_batch=False,
            )
            initialize_dashboard_store(workspace)
            index_pipeline_artifacts(workspace)

            summary = compute_pipeline_health(workspace)[0]

            self.assertEqual(summary.severity, "blocked")
            self.assertEqual(summary.status, "blocked")
            self.assertIn("blocked", summary.impact_summary)
            for item in summary.items:
                self.assertEqual(
                    set(item.details),
                    {
                        "phase",
                        "status",
                        "log_path",
                        "raw_json",
                        "exception_text",
                        "file_path",
                        "timestamp",
                    },
                )

            import sqlite3

            connection = sqlite3.connect(workspace / DASHBOARD_DB_PATH)
            connection.row_factory = sqlite3.Row
            try:
                persisted = connection.execute(
                    "SELECT * FROM pipeline_health_summaries WHERE run_id = ?",
                    ("20260507T030000Z_default",),
                ).fetchone()
            finally:
                connection.close()

            self.assertEqual(persisted["severity"], "blocked")
            persisted_items = json.loads(persisted["items_json"])
            self.assertTrue(any(item["component"] == "selected_batch" for item in persisted_items))

    def test_pipeline_health_does_not_change_scrape_quality_score(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_fixture_workspace(
                workspace,
                run_id="20260507T040000Z_default",
                phases=[
                    {"name": "candidate_selection", "status": "completed"},
                    {"name": "evidence_bundles", "status": "completed"},
                    {"name": "gemini_evidence", "status": "failed", "exception": "downstream"},
                    {"name": "structured_outputs", "status": "failed"},
                    {"name": "telegram_delivery", "status": "failed"},
                ],
                bundle_state="missing",
                with_source_video=True,
                with_gemini=False,
                with_report=False,
                with_excel=False,
                telegram_log={"status": "failed", "error": "missing token"},
            )
            initialize_dashboard_store(workspace)
            index_pipeline_artifacts(workspace)

            before = compute_scrape_quality_scores(workspace)[0]
            compute_pipeline_health(workspace)
            after = compute_scrape_quality_scores(workspace)[0]

            self.assertEqual(after.score, before.score)
            self.assertEqual(after.components, before.components)

    def _write_fixture_workspace(
        self,
        workspace: Path,
        *,
        run_id: str,
        phases: list[dict],
        bundle_state: str,
        with_source_video: bool,
        with_gemini: bool,
        with_report: bool,
        with_excel: bool,
        telegram_log: dict,
        video_count: int = 1,
        source_video_count: int | None = None,
        gemini_count: int | None = None,
        with_raw: bool = True,
        with_selected_batch: bool = True,
    ) -> None:
        raw_scrapes = workspace / "data" / "raw_scrapes"
        run_folder = workspace / "runs" / "batch-analysis" / run_id
        data_folder = run_folder / "data"
        evidence_folder = run_folder / "evidence"
        reports_folder = run_folder / "reports"
        logs_folder = run_folder / "logs"
        for folder in [raw_scrapes, data_folder, evidence_folder, reports_folder, logs_folder]:
            folder.mkdir(parents=True, exist_ok=True)

        source_video_count = video_count if source_video_count is None and with_source_video else (source_video_count or 0)
        gemini_count = video_count if gemini_count is None and with_gemini else (gemini_count or 0)
        candidate_source = "data/raw_scrapes/sample_raw.json"
        videos = [
            {
                "id": f"video-{index}",
                "url": f"https://tiktok.test/video-{index}",
                "author_handle": f"creator-{index}",
                "caption": "Acid reflux bloating gut health hook",
                "hashtags": ["guthealth", "digestive"],
                "source_input": "#guthealth",
                "video_download_url": f"https://download.test/video-{index}.mp4",
                "play_count": 100000,
                "like_count": 9000,
                "comment_count": 250,
                "share_count": 350,
                "created_at": "2026-05-06T00:00:00Z",
            }
            for index in range(1, video_count + 1)
        ]
        if with_raw:
            (raw_scrapes / "sample_raw.json").write_text(
                json.dumps({"generated_at": "2026-05-07T00:00:00Z", "top": videos}),
                encoding="utf-8",
            )
        manifest = {
            "run_timestamp": "2026-05-07T00:00:00Z",
            "mode": "default",
            "requested_batch_size": 1,
            "phases": phases,
            "outputs": {"batch_index": "batch_index.md"},
        }
        (run_folder / "run_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (run_folder / "run_metadata.json").write_text(
            json.dumps({"run_timestamp": "2026-05-07T00:00:00Z"}),
            encoding="utf-8",
        )
        if with_selected_batch:
            (data_folder / "selected_batch.json").write_text(
                json.dumps(
                    {
                        "selected_at": "2026-05-07T00:00:00Z",
                        "candidate_source": candidate_source,
                        "input_candidate_count": video_count,
                        "eligible_candidate_count": video_count,
                        "selected_candidate_count": video_count,
                        "selected_candidates": [{"id": f"video-{index}"} for index in range(1, video_count + 1)],
                    }
                ),
                encoding="utf-8",
            )
        bundle = {
            "created_at": "2026-05-07T00:00:00Z",
            "bundle_count": video_count,
            "bundles": [
                {
                    "candidate_id": f"video-{index}",
                    "source_video": {
                        "state": "available" if index <= source_video_count else "missing",
                        "path": f"evidence/{index:03d}_video-{index}_source_video.mp4"
                        if index <= source_video_count
                        else None,
                    },
                    "artifacts": {
                        "gemini_evidence": {
                            "state": "completed" if index <= gemini_count else bundle_state,
                            "path": f"data/{index:03d}_video-{index}_gemini_evidence.json"
                            if index <= gemini_count
                            else None,
                        },
                        "video_evidence_report": {
                            "state": "completed" if with_report else "missing",
                            "path": f"reports/{index:03d}_video-{index}_video_evidence_report.md" if with_report else None,
                        },
                    },
                }
                for index in range(1, video_count + 1)
            ],
        }
        (data_folder / "evidence_bundle_index.json").write_text(json.dumps(bundle), encoding="utf-8")
        for index in range(1, source_video_count + 1):
            (evidence_folder / f"{index:03d}_video-{index}_source_video.mp4").write_bytes(b"video")
        for index in range(1, gemini_count + 1):
            (data_folder / f"{index:03d}_video-{index}_gemini_evidence.json").write_text("{}", encoding="utf-8")
        if with_report:
            for index in range(1, video_count + 1):
                (reports_folder / f"{index:03d}_video-{index}_video_evidence_report.md").write_text(
                    "# Report\n",
                    encoding="utf-8",
                )
        if with_excel:
            (data_folder / "spreadsheet_summary.csv").write_text("id\nvideo-1\n", encoding="utf-8")
        (logs_folder / "telegram_delivery.json").write_text(json.dumps(telegram_log), encoding="utf-8")
        (run_folder / "batch_index.md").write_text("# Batch\n", encoding="utf-8")

    def _item(self, summary, component):
        for item in summary.items:
            if item.component == component:
                return item
        self.fail(f"Missing health item {component}")


if __name__ == "__main__":
    unittest.main()
