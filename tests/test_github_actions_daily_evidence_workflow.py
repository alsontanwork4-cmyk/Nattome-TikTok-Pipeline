import re
import unittest
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
WORKFLOW = WORKSPACE / ".github" / "workflows" / "daily-evidence-run.yml"
README = WORKSPACE / "README.md"


class GitHubActionsDailyEvidenceWorkflowTest(unittest.TestCase):
    def test_workflow_runs_manually_and_at_0100_utc(self):
        text = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("workflow_dispatch:", text)
        self.assertRegex(text, r"cron:\s*['\"]0 1 \* \* \*['\"]")
        self.assertIn("09:00 Asia/Singapore", text)

    def test_workflow_runs_discovery_and_source_video_snapshot_step(self):
        text = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("actions/setup-python@", text)
        self.assertRegex(text, r"python-version:\s*['\"]3\.11['\"]")
        self.assertIn("python -m pip install -r requirements.txt", text)
        self.assertIn("batch_analysis/scrape_tiktok.py", text)
        self.assertIn("batch_analysis/run_batch_analysis.py", text)
        self.assertIn("--download-videos", text)

    def test_workflow_checks_apify_and_passes_optional_gemini_secret_without_echoing_values(self):
        text = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("APIFY_TOKEN", text)
        self.assertIn("GEMINI_API_KEY", text)
        self.assertIn("TELEGRAM_BOT_TOKEN", text)
        self.assertIn("TELEGRAM_CHAT_ID", text)
        self.assertIn("Missing required GitHub secret: APIFY_TOKEN", text)
        self.assertNotRegex(text, r"echo\s+\\?\"\$\{!?APIFY_TOKEN")
        self.assertNotRegex(text, r"echo\s+\\?\"\$\{!?GEMINI_API_KEY")
        self.assertNotRegex(text, r"echo\s+\\?\"\$\{!?TELEGRAM_BOT_TOKEN")
        self.assertNotRegex(text, r"echo\s+\\?\"\$\{!?TELEGRAM_CHAT_ID")

    def test_readme_documents_gemini_creative_reporting_boundary(self):
        text = README.read_text(encoding="utf-8")

        self.assertIn("two-agent Gemini creative-reporting path", text)
        self.assertIn("Python owns orchestration", text)
        self.assertIn("Gemini owns video evidence interpretation", text)
        self.assertIn("preferred Nattome POV report outline", text)
        self.assertIn("APIFY_TOKEN", text)
        self.assertIn("GEMINI_API_KEY", text)
        self.assertIn("TELEGRAM_BOT_TOKEN", text)
        self.assertIn("TELEGRAM_CHAT_ID", text)
        self.assertIn("generated `.md` report document", text)
        self.assertIn("official `google-genai` package", text)


if __name__ == "__main__":
    unittest.main()
