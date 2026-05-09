import unittest
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
README = WORKSPACE / "README.md"
DOC = WORKSPACE / "docs" / "cloud-operations.md"


class CloudOperationsDocumentationTest(unittest.TestCase):
    def test_operator_documentation_covers_cloud_runtime_boundaries(self):
        text = DOC.read_text(encoding="utf-8")

        for expected in (
            "Python remains the worker",
            "Apify discovery",
            "Gemini evidence analysis",
            "Daily Output Set generation",
            "The Python dashboard in `dashboard/` is the operational dashboard",
            "Host it on a VPS",
            "Supabase Postgres stores compact run metadata",
            "Supabase Storage stores generated artifacts",
            "09:00 Asia/Singapore",
            "publishes new runs only",
            "does not import historical local runs",
            "local backup process",
            "docs/cloud-migration-safety-checklist.md",
        ):
            self.assertIn(expected, text)

    def test_operator_documentation_lists_env_names_without_secret_values(self):
        text = DOC.read_text(encoding="utf-8")

        for name in (
            "APIFY_TOKEN",
            "GEMINI_API_KEY",
            "SUPABASE_URL",
            "SUPABASE_SERVICE_ROLE_KEY",
        ):
            self.assertIn(name, text)
        self.assertIn("Secret values must not be written", text)
        self.assertNotIn("your-supabase-anon-key", text)
        self.assertNotIn("example-anon-key", text)
        self.assertIn("There is no separate web dashboard configuration", text)

    def test_deferred_control_room_scope_is_explicit(self):
        text = DOC.read_text(encoding="utf-8")

        for deferred in (
            "manual run triggers",
            "scrape setting edits",
            "curation labels",
            "rollback controls",
            "full control-room behavior",
        ):
            self.assertIn(deferred, text)

    def test_readme_links_to_cloud_operations_guide(self):
        readme = README.read_text(encoding="utf-8")

        self.assertIn("docs/cloud-operations.md", readme)
        self.assertIn("Cloud Operations", readme)


if __name__ == "__main__":
    unittest.main()
