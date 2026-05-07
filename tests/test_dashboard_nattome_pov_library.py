import http.client
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.parse import urlencode

from dashboard.nattome_pov_library import (
    archive_nattome_pov,
    create_nattome_pov,
    list_nattome_pov_versions,
    list_nattome_povs,
    update_nattome_pov,
)
from dashboard.pattern_library import create_approved_pattern
from dashboard.store import initialize_dashboard_store
from dashboard.web import DashboardServer, create_handler, render_page


class DashboardNattomePovLibraryTest(unittest.TestCase):
    def test_create_edit_approve_archive_pattern_links_defaults_and_version_history(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            initialize_dashboard_store(workspace)
            pattern = create_approved_pattern(
                workspace,
                {
                    "pattern_name": "Bloating relief routine demo",
                    "hook_type": "problem_solution",
                    "format_type": "routine_demo",
                    "emotional_trigger": "relief",
                    "why_it_works": "External routine mechanic.",
                },
                user="pattern-lead@example.com",
                status="approved",
            )

            pov = create_nattome_pov(
                workspace,
                {
                    "title": "Morning gut reset",
                    "description": "Owned Nattome angle for office workers.",
                    "brand_safe_interpretation": "Support daily digestive comfort without treatment claims.",
                    "adaptation_rules": "Show product in a normal breakfast routine.",
                    "product": "Nattome",
                    "campaign": "Always-on gut comfort",
                    "source_links": ["https://tiktok.test/source-1"],
                    "linked_pattern_ids": [pattern.id],
                },
                user="strategist@example.com",
            )
            self.assertEqual(pov.status, "draft")
            self.assertEqual(pov.version, 1)
            self.assertEqual(pov.market, "Malaysia")
            self.assertEqual(pov.language, "mixed/English")
            self.assertEqual(pov.channel, "TikTok")
            self.assertEqual(pov.linked_pattern_ids, [pattern.id])

            edited = update_nattome_pov(
                workspace,
                pov.id,
                {
                    "status": "approved",
                    "audience_avatar": "busy Klang Valley office workers",
                    "symptom_occasion": "post-lunch bloating",
                    "language": "English",
                    "adaptation_rules": "Use support language and avoid before/after promises.",
                },
                user="editor@example.com",
            )
            archived = archive_nattome_pov(workspace, edited.id, user="editor@example.com")
            versions = list_nattome_pov_versions(workspace, edited.id)

            self.assertEqual(archived.status, "archived")
            self.assertEqual(archived.version, 3)
            self.assertEqual(archived.audience_avatar, "busy Klang Valley office workers")
            self.assertEqual(archived.symptom_occasion, "post-lunch bloating")
            self.assertEqual(
                [version.change_type for version in versions],
                ["created", "edited", "archived"],
            )
            self.assertEqual(versions[1].changed_by, "editor@example.com")
            self.assertIn("before/after", versions[1].pov.adaptation_rules)

    def test_nattome_pov_library_route_renders_and_creates_povs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            initialize_dashboard_store(workspace)
            pattern = create_approved_pattern(
                workspace,
                {
                    "pattern_name": "Comment objection opener",
                    "hook_type": "objection",
                    "format_type": "talking_head",
                    "emotional_trigger": "confidence",
                },
                user="pattern-lead@example.com",
                status="approved",
            )

            initial_body = render_page("/nattome-pov-library", workspace)
            self.assertIn("Nattome POV Library", initial_body)
            self.assertIn("Owned Nattome interpretations", initial_body)
            self.assertIn("Approved Pattern Links", initial_body)
            self.assertIn("Comment objection opener", initial_body)

            response, _ = self._request(
                workspace,
                "POST",
                "/nattome-pov-library/create",
                body=urlencode(
                    {
                        "title": "Clinic-free comfort proof",
                        "description": "Nattome-safe angle for everyday digestion support.",
                        "brand_safe_interpretation": "Normalize proactive gut comfort.",
                        "adaptation_rules": "Keep claims in support territory.",
                        "product": "Nattome",
                        "campaign": "Gut comfort always-on",
                        "market": "",
                        "language": "",
                        "audience_avatar": "new supplement users",
                        "symptom_occasion": "heavy dinner",
                        "channel": "",
                        "source_links": "https://tiktok.test/source-2",
                        "linked_pattern_ids": str(pattern.id),
                        "user": "marketer@example.com",
                    }
                ),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            povs = list_nattome_povs(workspace)
            final_body = render_page("/nattome-pov-library", workspace)

            self.assertEqual(response.status, 303)
            self.assertEqual(len(povs), 1)
            self.assertEqual(povs[0].market, "Malaysia")
            self.assertEqual(povs[0].language, "mixed/English")
            self.assertEqual(povs[0].channel, "TikTok")
            self.assertIn("Clinic-free comfort proof", final_body)
            self.assertIn("Comment objection opener", final_body)

    def _request(
        self,
        workspace: Path,
        method: str,
        path: str,
        *,
        body: str | None = None,
        headers: dict[str, str] | None = None,
    ):
        server = DashboardServer(
            ("127.0.0.1", 0),
            create_handler(workspace),
        )
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            host, port = server.server_address
            connection = http.client.HTTPConnection(host, port, timeout=5)
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            response_body = response.read().decode("utf-8")
            return response, response_body
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()


if __name__ == "__main__":
    unittest.main()
