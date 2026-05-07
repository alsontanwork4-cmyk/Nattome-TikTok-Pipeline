import json
import tempfile
import unittest
from pathlib import Path

from dashboard.report_view import load_selected_report
from dashboard.web import NAV_ITEMS, render_page


class DashboardReportPageTest(unittest.TestCase):
    def test_report_page_renders_latest_generated_report_with_run_context(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_report_run(
                workspace,
                run_id="20260506T010000Z_default",
                timestamp="2026-05-06T01:00:00Z",
                body="# Older report\n\n- Previous finding",
            )
            self._write_report_run(
                workspace,
                run_id="20260507T010000Z_default",
                timestamp="2026-05-07T01:00:00Z",
                body=(
                    "# What We Learned\n\n"
                    "- Lead with the stomach moment.\n\n"
                    "## Source Reference\n\n"
                    "| Concept | Hook |\n"
                    "|---|---|\n"
                    "| Routine demo | Show breakfast setup |\n"
                ),
            )

            selected, artifacts = load_selected_report(workspace)
            body = render_page("/report", workspace)

            self.assertIsNotNone(selected)
            self.assertEqual(selected.run_id, "20260507T010000Z_default")
            self.assertEqual(len(artifacts), 2)
            self.assertIn("Report - 2026-05-07 - Run 20260507T010000Z_default", body)
            self.assertIn("Lead with the stomach moment.", body)
            self.assertIn("<table", body)
            self.assertIn("Routine demo", body)
            self.assertNotIn("Top 5 Creative Production Report - 2026-05-07", body)

    def test_report_page_can_select_an_older_run_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_report_run(
                workspace,
                run_id="20260506T010000Z_default",
                timestamp="2026-05-06T01:00:00Z",
                body="# Older report\n\n- Previous finding",
            )
            self._write_report_run(
                workspace,
                run_id="20260507T010000Z_default",
                timestamp="2026-05-07T01:00:00Z",
                body="# Newer report\n\n- Current finding",
            )

            body = render_page(
                "/report",
                workspace,
                query_params={"run_id": ["20260506T010000Z_default"]},
            )

            self.assertIn("Report - 2026-05-06 - Run 20260506T010000Z_default", body)
            self.assertIn("Previous finding", body)
            self.assertNotIn("Current finding", body)

    def test_report_route_is_a_sidebar_navigation_item(self):
        self.assertIn(("Report", "/report"), NAV_ITEMS)

    def _write_report_run(
        self,
        workspace: Path,
        *,
        run_id: str,
        timestamp: str,
        body: str,
    ) -> None:
        report_date = timestamp[:10]
        run_folder = workspace / "runs" / "batch-analysis" / run_id
        report_folder = workspace / "outputs" / "reports" / report_date
        for folder in [run_folder, report_folder]:
            folder.mkdir(parents=True, exist_ok=True)
        (run_folder / "run_manifest.json").write_text(
            json.dumps(
                {
                    "run_timestamp": timestamp,
                    "mode": "default",
                    "requested_batch_size": 5,
                    "configuration": {"selection": {"minimum_views": 10000}},
                    "outputs": {"batch_index": "batch_index.md"},
                    "phases": [{"name": "report_generation", "status": "completed"}],
                }
            ),
            encoding="utf-8",
        )
        (report_folder / f"top5_creative_production_report_{report_date}.md").write_text(
            body,
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
