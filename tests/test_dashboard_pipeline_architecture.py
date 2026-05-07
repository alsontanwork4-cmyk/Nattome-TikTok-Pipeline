import json
import tempfile
import unittest
from pathlib import Path

from dashboard.architecture import load_pipeline_architecture
from dashboard.indexer import index_pipeline_artifacts
from dashboard.store import initialize_dashboard_store
from dashboard.web import render_page


class DashboardPipelineArchitectureTest(unittest.TestCase):
    def test_pipeline_architecture_indexes_docs_and_builds_read_only_view_model(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_fixture_workspace(workspace)
            initialize_dashboard_store(workspace)
            index_pipeline_artifacts(workspace)

            architecture = load_pipeline_architecture(workspace)
            body = render_page("/pipeline-architecture", workspace)

            self.assertIn("README.md", [doc.path for doc in architecture.documents])
            self.assertIn("CONTEXT.md", [doc.path for doc in architecture.documents])
            self.assertIn("docs/prd/sample-prd.md", [doc.path for doc in architecture.documents])
            self.assertIn("docs/adr/0001-sample.md", [doc.path for doc in architecture.documents])
            self.assertIn("skills/nattome-batch-analysis/SKILL.md", [doc.path for doc in architecture.documents])
            self.assertEqual(
                [step.name for step in architecture.pipeline_flow],
                ["Scrape", "Score", "Select", "Analyze", "Report"],
            )
            self.assertTrue(any("Apify" in decision.summary for decision in architecture.tool_decisions))
            self.assertTrue(any("Gemini" in decision.summary for decision in architecture.tool_decisions))
            self.assertIn("gemini_evidence", [phase.name for phase in architecture.phase_statuses])
            self.assertIn("data/raw_scrapes/sample_raw.json", architecture.file_output_map["Raw scrapes"])
            self.assertIn("runs/batch-analysis/20260507T000000Z_default", architecture.file_output_map["Run folders"])
            self.assertIn("outputs/reports/2026-05-07/top5_report.md", architecture.file_output_map["Reports"])
            self.assertIn("outputs/reports/2026-05-07/top5_workbook.xlsx", architecture.file_output_map["Workbooks"])
            self.assertIn("runs/batch-analysis/20260507T000000Z_default/logs/telegram_delivery.json", architecture.file_output_map["Logs"])
            self.assertIn("Raw scrape", [step.name for step in architecture.data_lineage])
            self.assertIn("Selected batch", [step.name for step in architecture.data_lineage])
            self.assertIn("Final report", [step.name for step in architecture.data_lineage])
            self.assertIn("Pipeline Architecture", body)
            self.assertIn("Scrape to score to select to analyze to report", body)
            self.assertIn("Apify discovery/download", body)
            self.assertIn("Gemini evidence-first analysis", body)
            self.assertIn("sample-prd.md", body)
            self.assertNotIn("<form", body.lower())
            self.assertNotIn("method=\"post\"", body.lower())

    def _write_fixture_workspace(self, workspace: Path) -> None:
        raw_scrapes = workspace / "data" / "raw_scrapes"
        run_folder = workspace / "runs" / "batch-analysis" / "20260507T000000Z_default"
        report_folder = workspace / "outputs" / "reports" / "2026-05-07"
        docs_prd = workspace / "docs" / "prd"
        docs_adr = workspace / "docs" / "adr"
        skill_folder = workspace / "skills" / "nattome-batch-analysis"
        for folder in [raw_scrapes, run_folder / "data", run_folder / "logs", report_folder, docs_prd, docs_adr, skill_folder]:
            folder.mkdir(parents=True, exist_ok=True)

        (workspace / "README.md").write_text("# Project Readme\n", encoding="utf-8")
        (workspace / "CONTEXT.md").write_text("# Domain Context\n", encoding="utf-8")
        (docs_prd / "sample-prd.md").write_text("# Sample PRD\n", encoding="utf-8")
        (docs_adr / "0001-sample.md").write_text("# Sample ADR\n", encoding="utf-8")
        (skill_folder / "SKILL.md").write_text("# Batch Skill\n", encoding="utf-8")
        (raw_scrapes / "sample_raw.json").write_text(
            json.dumps(
                {
                    "generated_at": "2026-05-07T00:00:00Z",
                    "top": [
                        {
                            "id": "video-1",
                            "url": "https://tiktok.test/video-1",
                            "caption": "Gut health hook",
                            "video_download_url": "https://cdn.test/video-1.mp4",
                            "play_count": 12000,
                            "like_count": 800,
                            "comment_count": 20,
                            "share_count": 40,
                        }
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
        (run_folder / "data" / "selected_batch.json").write_text(
            json.dumps(
                {
                    "selected_at": "2026-05-07T00:01:00Z",
                    "candidate_source": "data/raw_scrapes/sample_raw.json",
                    "selected_candidate_count": 1,
                    "selected_candidates": [{"id": "video-1"}],
                }
            ),
            encoding="utf-8",
        )
        (run_folder / "logs" / "telegram_delivery.json").write_text(
            json.dumps({"status": "sent"}),
            encoding="utf-8",
        )
        (run_folder / "reports").mkdir(exist_ok=True)
        (run_folder / "reports" / "current.md").write_text("# Current\n", encoding="utf-8")
        (run_folder / "reports" / "current.xlsx").write_bytes(b"xlsx")
        (report_folder / "top5_report.md").write_text("# Report\n", encoding="utf-8")
        (report_folder / "top5_workbook.xlsx").write_bytes(b"xlsx")


if __name__ == "__main__":
    unittest.main()
