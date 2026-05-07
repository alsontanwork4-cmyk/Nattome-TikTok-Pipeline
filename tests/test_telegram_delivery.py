import json
import tempfile
import unittest
from pathlib import Path

from batch_analysis.telegram import build_telegram_brief_message, deliver_telegram_brief


class TelegramDeliveryTest(unittest.TestCase):
    def test_default_message_is_minimal_status_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir)

            message = build_telegram_brief_message(
                run_folder,
                {"run_timestamp": "2026-05-06T13:45:30Z", "mode": "debug"},
                {"source_video_count": 1, "top_priority_shootable_angles": []},
            )

            self.assertIn("Nattome Batch Analysis Final Outputs", message)
            self.assertIn("Run: 2026-05-06T13:45:30Z", message)
            self.assertIn("Videos compared: 1", message)
            self.assertIn("Success or Fail: Success", message)
            self.assertEqual(
                message.splitlines(),
                [
                    "Nattome Batch Analysis Final Outputs",
                    "Run: 2026-05-06T13:45:30Z",
                    "Videos compared: 1",
                    "Success or Fail: Success",
                ],
            )

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
