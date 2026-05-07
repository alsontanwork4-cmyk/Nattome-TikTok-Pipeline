import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from dashboard.health import compute_pipeline_health
from dashboard.indexer import index_pipeline_artifacts
from dashboard.manual_runs import trigger_manual_run
from dashboard.quality import compute_scrape_quality_scores
from dashboard.run_history import load_run_history, load_run_history_detail
from dashboard.store import DASHBOARD_DB_PATH, initialize_dashboard_store
from dashboard.web import render_page


class DashboardRunHistoryTest(unittest.TestCase):
    def test_run_history_combines_scheduled_manual_trends_and_drilldown(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_fixture_workspace(
                workspace,
                "20260506T010000Z_daily",
                "2026-05-06T01:00:00Z",
                "v2",
                video_prefix="baseline",
                score_hint="Baseline relevance",
            )
            self._write_fixture_workspace(
                workspace,
                "20260507T010000Z_daily",
                "2026-05-07T01:00:00Z",
                "v3",
                video_prefix="current",
                score_hint="Current relevance",
            )
            initialize_dashboard_store(workspace)
            index_pipeline_artifacts(workspace)
            compute_scrape_quality_scores(workspace)
            compute_pipeline_health(workspace)
            trigger_manual_run(
                workspace,
                "scrape_only",
                triggered_by="marketer@example.com",
                executor=lambda command, *, cwd: self._completed(command),
            )

            history = load_run_history(workspace)
            detail = load_run_history_detail(workspace, "20260507T010000Z_daily")
            body = render_page("/run-history", workspace)

            self.assertEqual([row.run_id for row in history.rows[:3]], [
                history.rows[0].run_id,
                "20260507T010000Z_daily",
                "20260506T010000Z_daily",
            ])
            self.assertEqual(history.rows[1].run_type, "scheduled daily")
            self.assertEqual(history.rows[1].config_version, "v3")
            self.assertEqual(history.rows[1].raw_candidates, 3)
            self.assertEqual(history.rows[1].eligible_candidates, 2)
            self.assertEqual(history.rows[1].selected_count, 2)
            self.assertGreater(history.rows[1].scrape_quality_score or 0, 0)
            self.assertGreater(history.rows[1].average_nattome_relevance, 0)
            self.assertGreater(history.rows[1].average_engagement, 0)
            self.assertEqual(history.rows[1].pipeline_health, "completed")
            self.assertTrue(any(link.artifact_type == "report_markdown" for link in history.rows[1].output_links))
            self.assertEqual([point.config_version for point in history.trend_points], ["v2", "v3"])
            self.assertEqual([overlay.version for overlay in history.config_overlays], ["v2", "v3"])
            self.assertIn("current-video-1", [video.video_id for video in detail.raw_content])
            self.assertEqual([video.video_id for video in detail.selected_content], ["current-video-1", "current-video-2"])
            self.assertTrue(detail.quality_drivers)
            self.assertTrue(detail.pipeline_phases)
            self.assertIn("logs/pipeline.log", detail.logs[0])
            self.assertTrue(any(link.artifact_type == "excel_workbook" for link in detail.output_links))
            self.assertIn("Scheduled Daily", body)
            self.assertIn("Trend Monitoring", body)
            self.assertIn("Config Overlays", body)
            self.assertIn("20260507T010000Z_daily", body)
            self.assertIn("reports/current.md", body)

    def test_empty_run_history_explains_missing_history(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            initialize_dashboard_store(workspace)

            history = load_run_history(workspace)
            body = render_page("/run-history", workspace)

            self.assertEqual(history.rows, [])
            self.assertEqual(history.trend_points, [])
            self.assertIn("No scheduled or manual runs have been indexed yet.", body)

    def _completed(self, command):
        import subprocess

        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    def _write_fixture_workspace(
        self,
        workspace: Path,
        run_id: str,
        run_timestamp: str,
        config_version: str,
        *,
        video_prefix: str,
        score_hint: str,
    ) -> None:
        raw_scrapes = workspace / "data" / "raw_scrapes"
        run_folder = workspace / "runs" / "batch-analysis" / run_id
        report_folder = workspace / "outputs" / "reports" / run_timestamp[:10]
        for folder in [raw_scrapes, run_folder / "data", run_folder / "evidence", run_folder / "logs", report_folder]:
            folder.mkdir(parents=True, exist_ok=True)

        candidate_source = f"data/raw_scrapes/{video_prefix}_raw.json"
        videos = [
            self._video(f"{video_prefix}-video-1", "Acid reflux bloating gut health hook", 100000, 9000, 200, 300),
            self._video(f"{video_prefix}-video-2", "Digestive relief stomach routine", 75000, 5000, 120, 180),
            self._video(f"{video_prefix}-video-3", "Generic wellness clip", 12000, 200, 5, 8),
        ]
        (raw_scrapes / f"{video_prefix}_raw.json").write_text(
            json.dumps({"generated_at": run_timestamp, "top": videos}),
            encoding="utf-8",
        )
        (run_folder / "run_manifest.json").write_text(
            json.dumps(
                {
                    "run_timestamp": run_timestamp,
                    "mode": "daily",
                    "requested_batch_size": 2,
                    "configuration": {
                        "version": config_version,
                        "next_scheduled_run": "2026-05-08T01:00:00Z",
                        "selection": {
                            "maximum_age_days": 14,
                            "minimum_views": 10000,
                        },
                    },
                    "phases": [
                        {"name": "candidate_selection", "status": "completed"},
                        {"name": "gemini_evidence", "status": "completed"},
                        {"name": "report_generation", "status": "completed"},
                    ],
                    "outputs": {
                        "report_markdown": "reports/current.md",
                        "excel_workbook": "reports/current.xlsx",
                    },
                }
            ),
            encoding="utf-8",
        )
        (run_folder / "run_metadata.json").write_text(
            json.dumps({"run_timestamp": run_timestamp, "mode": "daily"}),
            encoding="utf-8",
        )
        (run_folder / "data" / "selected_batch.json").write_text(
            json.dumps(
                {
                    "selected_at": run_timestamp,
                    "candidate_source": candidate_source,
                    "input_candidate_count": 3,
                    "eligible_candidate_count": 2,
                    "selected_candidate_count": 2,
                    "selected_candidates": [
                        {"id": f"{video_prefix}-video-1"},
                        {"id": f"{video_prefix}-video-2"},
                    ],
                    "score_hint": score_hint,
                    "config_version": config_version,
                }
            ),
            encoding="utf-8",
        )
        (run_folder / "logs" / "pipeline.log").write_text("ok\n", encoding="utf-8")
        (run_folder / "logs" / "telegram_delivery.json").write_text(
            json.dumps({"status": "sent"}),
            encoding="utf-8",
        )
        (run_folder / "data" / "evidence_bundle_index.json").write_text(
            json.dumps(
                {
                    "bundles": [
                        {
                            "candidate_id": f"{video_prefix}-video-1",
                            "source_video": {
                                "state": "available",
                                "path": f"evidence/{video_prefix}-video-1.mp4",
                            },
                            "artifacts": {
                                "gemini_evidence": {
                                    "state": "completed",
                                    "path": f"data/{video_prefix}-video-1_gemini.json",
                                },
                                "video_evidence_report": {
                                    "state": "completed",
                                    "path": "reports/current.md",
                                },
                            },
                        },
                        {
                            "candidate_id": f"{video_prefix}-video-2",
                            "source_video": {
                                "state": "available",
                                "path": f"evidence/{video_prefix}-video-2.mp4",
                            },
                            "artifacts": {
                                "gemini_evidence": {
                                    "state": "completed",
                                    "path": f"data/{video_prefix}-video-2_gemini.json",
                                },
                                "video_evidence_report": {
                                    "state": "completed",
                                    "path": "reports/current.md",
                                },
                            },
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        (run_folder / "evidence" / f"{video_prefix}-video-1.mp4").write_bytes(b"video")
        (run_folder / "evidence" / f"{video_prefix}-video-2.mp4").write_bytes(b"video")
        (run_folder / "data" / f"{video_prefix}-video-1_gemini.json").write_text("{}", encoding="utf-8")
        (run_folder / "data" / f"{video_prefix}-video-2_gemini.json").write_text("{}", encoding="utf-8")
        (run_folder / "reports").mkdir(exist_ok=True)
        (run_folder / "reports" / "current.md").write_text("# Report\n", encoding="utf-8")
        (run_folder / "reports" / "current.xlsx").write_bytes(b"xlsx")
        (report_folder / f"{video_prefix}.md").write_text("# Existing Markdown Report\n", encoding="utf-8")

    def _video(
        self,
        video_id: str,
        caption: str,
        views: int,
        likes: int,
        comments: int,
        shares: int,
    ) -> dict:
        return {
            "id": video_id,
            "url": f"https://tiktok.test/{video_id}",
            "author_handle": f"creator-{video_id}",
            "caption": caption,
            "hashtags": ["guthealth", "digestive"],
            "source_input": "#guthealth",
            "video_download_url": f"https://cdn.test/{video_id}.mp4",
            "play_count": views,
            "like_count": likes,
            "comment_count": comments,
            "share_count": shares,
            "created_at": "2026-05-06T00:00:00Z",
        }


if __name__ == "__main__":
    unittest.main()
