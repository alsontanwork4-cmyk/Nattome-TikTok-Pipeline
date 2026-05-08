import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from batch_analysis.env import load_dotenv_files, parse_dotenv_line


class EnvLoadingTest(unittest.TestCase):
    def test_parse_dotenv_line_handles_quotes_export_and_comments(self):
        self.assertEqual(parse_dotenv_line("GEMINI_API_KEY=abc123"), ("GEMINI_API_KEY", "abc123"))
        self.assertEqual(parse_dotenv_line("export APIFY_TOKEN='tok'"), ("APIFY_TOKEN", "tok"))
        self.assertIsNone(parse_dotenv_line("# GEMINI_API_KEY=ignored"))
        self.assertIsNone(parse_dotenv_line(""))

    def test_load_dotenv_files_loads_nearest_env_without_overriding_process_env(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            nested = root / "a" / "b"
            nested.mkdir(parents=True)
            dotenv = root / ".env"
            dotenv.write_text(
                "GEMINI_API_KEY=from-file\nAPIFY_TOKEN=from-file\n",
                encoding="utf-8",
            )

            with patch.dict(os.environ, {"APIFY_TOKEN": "already-exported"}, clear=True):
                loaded = load_dotenv_files([nested])

                self.assertEqual(os.environ["GEMINI_API_KEY"], "from-file")
                self.assertEqual(os.environ["APIFY_TOKEN"], "already-exported")
                self.assertEqual(loaded["GEMINI_API_KEY"], str(dotenv))
                self.assertNotIn("APIFY_TOKEN", loaded)

    def test_load_dotenv_files_can_override_process_env(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dotenv = root / ".env"
            dotenv.write_text("APIFY_TOKEN=from-file\n", encoding="utf-8")

            with patch.dict(os.environ, {"APIFY_TOKEN": "already-exported"}, clear=True):
                loaded = load_dotenv_files([root], override=True)

                self.assertEqual(os.environ["APIFY_TOKEN"], "from-file")
                self.assertEqual(loaded["APIFY_TOKEN"], str(dotenv))

    def test_load_dotenv_files_can_be_disabled_for_missing_credential_tests(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".env").write_text("GEMINI_API_KEY=from-file\n", encoding="utf-8")

            with patch.dict(os.environ, {"NATTOME_DISABLE_DOTENV": "1"}, clear=True):
                loaded = load_dotenv_files([root])

                self.assertEqual(loaded, {})
                self.assertNotIn("GEMINI_API_KEY", os.environ)


if __name__ == "__main__":
    unittest.main()
