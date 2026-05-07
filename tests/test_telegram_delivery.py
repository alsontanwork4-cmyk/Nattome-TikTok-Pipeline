import json
import tempfile
import unittest
from pathlib import Path

from batch_analysis.telegram import build_telegram_brief_message, deliver_telegram_brief


class TelegramDeliveryTest(unittest.TestCase):
    def test_default_message_points_to_new_final_output_set(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir)

            message = build_telegram_brief_message(
                run_folder,
                {"run_timestamp": "2026-05-06T13:45:30Z", "mode": "debug"},
                {"source_video_count": 1, "top_priority_shootable_angles": []},
            )

            self.assertIn("Top 5 Creative Production Report", message)
            self.assertIn("Nattome Batch Analysis Final Outputs", message)
            self.assertNotIn("Weekly Evidence Brief", message)
            self.assertIn(
                "reports/2026-05-06/top5_creative_production_report_2026-05-06.md",
                message,
            )
            self.assertIn("Excel Planning Workbook", message)
            self.assertIn(
                "reports/2026-05-06/top5_angle_planning_sheet_2026-05-06.xlsx",
                message,
            )
            self.assertNotIn("reports/cross_video_pattern_summary.md", message)
            self.assertNotIn("data/spreadsheet_summary.csv", message)

    def test_missing_credentials_are_logged_as_skipped_delivery(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir)
            (run_folder / "logs").mkdir()

            status = deliver_telegram_brief(
                run_folder,
                {"run_timestamp": "2026-05-06T13:45:30Z", "mode": "debug"},
                {"source_video_count": 0, "top_priority_shootable_angles": []},
                {
                    "enabled": True,
                    "bot_token_env": "MISSING_TEST_TELEGRAM_BOT_TOKEN",
                    "chat_id_env": "MISSING_TEST_TELEGRAM_CHAT_ID",
                },
            )

            self.assertEqual(status["status"], "skipped")
            self.assertEqual(status["reason"], "missing Telegram credentials")
            self.assertEqual(
                status["missing"],
                ["MISSING_TEST_TELEGRAM_BOT_TOKEN", "MISSING_TEST_TELEGRAM_CHAT_ID"],
            )
            log = json.loads((run_folder / "logs" / "telegram_delivery.json").read_text())
            self.assertEqual(log["status"], "skipped")
