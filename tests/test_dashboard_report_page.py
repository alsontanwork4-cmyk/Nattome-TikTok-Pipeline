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

    def test_report_page_uses_local_report_date_for_after_midnight_runs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_report_run(
                workspace,
                run_id="20260507T175306Z_daily",
                timestamp="2026-05-07T17:53:06Z",
                body="# Local date report\n\n- May 8 Singapore run",
                report_date="2026-05-08",
                final_outputs=True,
            )

            selected, artifacts = load_selected_report(workspace)
            body = render_page("/report", workspace)

            self.assertEqual(len(artifacts), 1)
            self.assertIsNotNone(selected)
            self.assertEqual(selected.report_date, "2026-05-08")
            self.assertIn("Report - 2026-05-08 - Run 20260507T175306Z_daily", body)

    def test_report_page_does_not_attach_modern_final_report_to_legacy_same_date_runs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_report_run(
                workspace,
                run_id="20260507T074557Z_default",
                timestamp="2026-05-07T07:45:57Z",
                body="# Shared legacy fallback\n\n- Should not be selected",
            )
            self._write_report_run(
                workspace,
                run_id="20260507T175306Z_daily",
                timestamp="2026-05-07T17:53:06Z",
                body="# First daily report\n\n- First scrape",
                report_date="2026-05-08",
                final_outputs=True,
            )
            self._write_report_run(
                workspace,
                run_id="20260507T174329Z_daily",
                timestamp="2026-05-07T17:43:29Z",
                body="# Second daily report\n\n- Second scrape",
                report_date="2026-05-08",
                final_outputs=True,
            )

            selected, artifacts = load_selected_report(workspace)

            self.assertIsNotNone(selected)
            self.assertEqual(
                [artifact.run_id for artifact in artifacts],
                ["20260507T175306Z_daily", "20260507T174329Z_daily"],
            )
            self.assertEqual(len({artifact.path for artifact in artifacts}), 2)

    def test_report_page_ignores_duplicate_manifest_report_paths_when_run_scoped_report_exists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            shared_path = Path("reports") / "2026-05-08" / "top5_creative_production_report_2026-05-08.md"
            self._write_report_run(
                workspace,
                run_id="20260507T175936Z_quick",
                timestamp="2026-05-07T17:59:36Z",
                body="# Shared stale report\n\n- Wrong for both runs",
                report_date="2026-05-08",
                final_outputs=True,
                final_report_path=shared_path,
            )
            self._write_report_run(
                workspace,
                run_id="20260507T175306Z_daily",
                timestamp="2026-05-07T17:53:06Z",
                body="# Shared stale report\n\n- Wrong for both runs",
                report_date="2026-05-08",
                final_outputs=True,
                final_report_path=shared_path,
            )
            for run_id, marker in [
                ("20260507T175936Z_quick", "Quick run report"),
                ("20260507T175306Z_daily", "Daily run report"),
            ]:
                scoped = (
                    workspace
                    / "runs"
                    / "batch-analysis"
                    / run_id
                    / "reports"
                    / "top5_creative_production_report_2026-05-08.md"
                )
                scoped.parent.mkdir(parents=True, exist_ok=True)
                scoped.write_text(f"# {marker}\n", encoding="utf-8")

            selected, artifacts = load_selected_report(workspace)
            body = render_page(
                "/report",
                workspace,
                query_params={"run_id": ["20260507T175306Z_daily"]},
            )

            self.assertIsNotNone(selected)
            self.assertEqual(len({artifact.path for artifact in artifacts}), 2)
            self.assertIn("Daily run report", body)
            self.assertNotIn("Shared stale report", body)

    def test_report_route_is_a_sidebar_navigation_item(self):
        self.assertIn(("Report", "/report"), NAV_ITEMS)

    def _write_report_run(
        self,
        workspace: Path,
        *,
        run_id: str,
        timestamp: str,
        body: str,
        report_date: str | None = None,
        final_outputs: bool = False,
        final_report_path: Path | None = None,
    ) -> None:
        report_date = report_date or timestamp[:10]
        run_folder = workspace / "runs" / "batch-analysis" / run_id
        relative_report_path = final_report_path or (
            Path("reports")
            / report_date
            / run_id
            / f"top5_creative_production_report_{report_date}.md"
            if final_outputs
            else Path("reports")
            / report_date
            / f"top5_creative_production_report_{report_date}.md"
        )
        report_folder = workspace / "outputs" / relative_report_path.parent
        for folder in [run_folder, report_folder]:
            folder.mkdir(parents=True, exist_ok=True)
        outputs = {"batch_index": "batch_index.md"}
        if final_outputs:
            outputs["output_root"] = "outputs"
            outputs["final_outputs"] = [
                {
                    "label": "Top 5 Creative Production Report",
                    "kind": "markdown",
                    "path": str(relative_report_path).replace("\\", "/"),
                }
            ]
        (run_folder / "run_manifest.json").write_text(
            json.dumps(
                {
                    "run_timestamp": timestamp,
                    "mode": "default",
                    "requested_batch_size": 5,
                    "configuration": {"selection": {"minimum_views": 10000}},
                    "outputs": outputs,
                    "phases": [{"name": "report_generation", "status": "completed"}],
                }
            ),
            encoding="utf-8",
        )
        (workspace / "outputs" / relative_report_path).write_text(
            body,
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
