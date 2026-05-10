import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_SQL = PROJECT_ROOT / "docs" / "supabase-dashboard-schema.sql"
DATA_CONTRACT = PROJECT_ROOT / "docs" / "supabase-dashboard-data-contract.md"
DEPLOYMENT_DOC = PROJECT_ROOT / "docs" / "vps-dashboard-deployment.md"
AGENT_SETTINGS_MIGRATION = PROJECT_ROOT / "docs" / "migrations" / "20260510_agent_settings_versions.sql"
AGENT_TRACE_MIGRATION = PROJECT_ROOT / "docs" / "migrations" / "20260510_agent_trace_events.sql"


class AgentDashboardDocsTest(unittest.TestCase):
    def test_schema_and_migrations_document_agent_tables(self):
        schema = SCHEMA_SQL.read_text(encoding="utf-8")
        settings_migration = AGENT_SETTINGS_MIGRATION.read_text(encoding="utf-8")
        trace_migration = AGENT_TRACE_MIGRATION.read_text(encoding="utf-8")

        expected_schema_fragments = [
            "create table if not exists public.agent_settings_versions",
            "create table if not exists public.agent_trace_events",
            "create unique index if not exists idx_agent_settings_one_active",
            "create index if not exists idx_agent_trace_events_run_started",
            "create index if not exists idx_agent_trace_events_recent",
            "create or replace function public.save_agent_settings_version",
        ]
        for fragment in expected_schema_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, schema)

        self.assertIn("Idempotent migration for existing Supabase dashboard projects", settings_migration)
        self.assertIn("Idempotent migration for live Gemini agent trace events", trace_migration)
        self.assertIn("create table if not exists public.agent_settings_versions", settings_migration)
        self.assertIn("create table if not exists public.agent_trace_events", trace_migration)
        self.assertIn("notify pgrst, 'reload schema'", settings_migration)
        self.assertIn("notify pgrst, 'reload schema'", trace_migration)

    def test_data_contract_documents_agent_security_and_artifact_boundaries(self):
        text = DATA_CONTRACT.read_text(encoding="utf-8")

        expected_fragments = [
            "`agent_settings_versions`",
            "`agent_trace_events`",
            "GEMINI_API_KEY remains environment-based",
            "must not be stored in this table",
            "Trace rows must not store API keys",
            "raw environment values",
            "full local filesystem paths",
            "full Gemini response text",
            "Full Gemini responses remain Supabase Storage artifacts",
            "artifact references are relative object paths",
        ]
        for fragment in expected_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_vps_deployment_docs_include_agent_migration_and_live_trace_ops(self):
        text = DEPLOYMENT_DOC.read_text(encoding="utf-8")

        expected_fragments = [
            "docs/supabase-dashboard-schema.sql",
            "docs/migrations/20260510_agent_settings_versions.sql",
            "docs/migrations/20260510_agent_trace_events.sql",
            "Run both idempotent agent migrations before restarting existing services",
            "GEMINI_API_KEY remains in the VPS EnvironmentFile",
            "Live tracing writes compact `agent_trace_events` rows",
            "full Gemini responses stay in Supabase Storage artifacts",
            "journalctl -u nattome-dashboard-worker",
        ]
        for fragment in expected_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)


if __name__ == "__main__":
    unittest.main()
