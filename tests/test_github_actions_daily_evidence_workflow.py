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

    def test_workflow_installs_python_dependencies_and_runs_daily_publication(self):
        text = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("actions/setup-python@", text)
        self.assertRegex(text, r"python-version:\s*['\"]3\.11['\"]")
        self.assertIn("python -m pip install --upgrade pip", text)
        self.assertIn("python -m pip install -r requirements.txt", text)
        self.assertIn("skills/nattome-tiktok-candidate-discovery/scripts/scrape_tiktok.py", text)
        self.assertIn("scripts/run_batch_analysis.py", text)
        self.assertIn("--mode daily", text)
        self.assertIn("--publish-cloud", text)

    def test_workflow_checks_required_secrets_without_echoing_values(self):
        text = WORKFLOW.read_text(encoding="utf-8")

        for secret_name in (
            "APIFY_TOKEN",
            "GEMINI_API_KEY",
            "SUPABASE_URL",
            "SUPABASE_SERVICE_ROLE_KEY",
        ):
            self.assertIn(secret_name, text)
        self.assertIn("Missing required GitHub secrets", text)
        self.assertNotRegex(text, r"echo\s+\\?\"\$\{!?APIFY_TOKEN")
        self.assertNotRegex(text, r"echo\s+\\?\"\$\{!?GEMINI_API_KEY")
        self.assertNotRegex(text, r"echo\s+\\?\"\$\{!?SUPABASE_SERVICE_ROLE_KEY")

    def test_workflow_reports_outputs_and_does_not_commit_generated_artifacts(self):
        text = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("cloud_publication.json", text)
        self.assertIn("GITHUB_STEP_SUMMARY", text)
        self.assertIn("final_outputs", text)
        self.assertNotIn("git add", text)
        self.assertNotIn("git commit", text)
        self.assertNotIn("git push", text)

    def test_readme_documents_required_github_actions_secrets(self):
        text = README.read_text(encoding="utf-8")

        self.assertIn("GitHub Actions Daily Evidence Run", text)
        self.assertIn("01:00 UTC", text)
        self.assertIn("09:00 Asia/Singapore", text)
        for secret_name in (
            "APIFY_TOKEN",
            "GEMINI_API_KEY",
            "TELEGRAM_BOT_TOKEN",
            "TELEGRAM_CHAT_ID",
            "SUPABASE_URL",
            "SUPABASE_SERVICE_ROLE_KEY",
        ):
            self.assertIn(secret_name, text)
        self.assertIn("does not commit generated artifacts", text)


if __name__ == "__main__":
    unittest.main()
