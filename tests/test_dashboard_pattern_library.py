import http.client
import json
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.parse import urlencode

from dashboard.indexer import index_pipeline_artifacts
from dashboard.pattern_library import (
    approve_candidate_pattern,
    archive_approved_pattern,
    create_approved_pattern,
    generate_candidate_patterns,
    list_approved_patterns,
    list_candidate_patterns,
    list_pattern_versions,
    update_approved_pattern,
)
from dashboard.store import DASHBOARD_DB_PATH, initialize_dashboard_store
from dashboard.web import DashboardServer, create_handler, render_page


class DashboardPatternLibraryTest(unittest.TestCase):
    def test_candidate_generation_approval_edit_archive_and_version_history(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_fixture_workspace(workspace)
            index_pipeline_artifacts(workspace)

            candidates = generate_candidate_patterns(workspace, user="system")
            approved_before = list_approved_patterns(workspace)

            self.assertEqual(len(candidates), 1)
            self.assertEqual(approved_before, [])
            candidate = candidates[0]
            self.assertEqual(candidate.status, "candidate")
            self.assertEqual(candidate.hook_type, "problem_solution")
            self.assertEqual(candidate.format_type, "routine_demo")
            self.assertEqual(candidate.emotional_trigger, "relief")
            self.assertEqual([video["video_id"] for video in candidate.source_videos], ["vid-1", "vid-2"])
            self.assertEqual(candidate.source_videos[0]["tiktok_url"], "https://tiktok.test/vid-1")
            self.assertIn("median_views", candidate.performance_evidence)

            approved = approve_candidate_pattern(
                workspace,
                candidate.id,
                user="marketer@example.com",
                notes="Canonical external mechanic for creator examples.",
            )
            self.assertEqual(approved.status, "approved")
            self.assertEqual(approved.version, 1)
            self.assertEqual(approved.source_candidate_id, candidate.id)
            self.assertEqual(approved.nattome_adaptation_notes, "")
            self.assertEqual(approved.approval_metadata["approved_by"], "marketer@example.com")

            manual = create_approved_pattern(
                workspace,
                {
                    "pattern_name": "Comment-to-camera objection opener",
                    "hook_type": "objection",
                    "format_type": "talking_head",
                    "emotional_trigger": "confidence",
                    "source_videos": [{"video_id": "manual-1", "tiktok_url": "https://tiktok.test/manual-1"}],
                    "why_it_works": "Uses visible social proof before the claim.",
                    "nattome_adaptation_notes": "Use only digestion-support language.",
                    "shoot_difficulty": "low",
                    "freshness": "emerging",
                    "performance_evidence": {"views": 99000},
                    "related_povs": ["morning routine"],
                    "avoid_notes": "Do not imply treatment.",
                    "targeting": {"market": "MY", "persona": "office workers"},
                },
                user="strategist@example.com",
                status="draft",
            )
            edited = update_approved_pattern(
                workspace,
                manual.id,
                {
                    "status": "approved",
                    "targeting": {"market": "MY", "persona": "new parents"},
                    "avoid_notes": "Avoid disease claims and before/after promises.",
                },
                user="editor@example.com",
            )
            archived = archive_approved_pattern(workspace, edited.id, user="editor@example.com")
            versions = list_pattern_versions(workspace, edited.id)

            self.assertEqual(archived.status, "archived")
            self.assertEqual(archived.version, 3)
            self.assertEqual(archived.targeting["persona"], "new parents")
            self.assertEqual(
                [version.change_type for version in versions],
                ["created", "edited", "archived"],
            )
            self.assertEqual(versions[1].changed_by, "editor@example.com")
            self.assertIn("before/after", versions[1].pattern.avoid_notes)

    def test_pattern_library_route_renders_and_approves_candidate_patterns(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            self._write_fixture_workspace(workspace)

            body = render_page("/pattern-library", workspace)

            self.assertIn("Pattern Library", body)
            self.assertIn("Candidate Patterns", body)
            self.assertIn("Approved Patterns", body)
            self.assertIn("Bloating relief routine demo", body)
            self.assertIn("https://tiktok.test/vid-1", body)
            candidate = list_candidate_patterns(workspace)[0]

            response, _ = self._request(
                workspace,
                "POST",
                "/pattern-library/approve",
                body=urlencode(
                    {
                        "candidate_id": str(candidate.id),
                        "user": "marketer@example.com",
                        "notes": "Approved from route.",
                    }
                ),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            final_body = render_page("/pattern-library", workspace)

            self.assertEqual(response.status, 303)
            self.assertEqual(len(list_approved_patterns(workspace)), 1)
            self.assertIn("approved", final_body)
            self.assertIn("Approved from route.", json.dumps(list_approved_patterns(workspace)[0].approval_metadata))

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

    def _write_fixture_workspace(self, workspace: Path) -> None:
        raw_scrapes = workspace / "data" / "raw_scrapes"
        run_folder = workspace / "runs" / "batch-analysis" / "20260507T010000Z_daily"
        (run_folder / "data").mkdir(parents=True, exist_ok=True)
        raw_scrapes.mkdir(parents=True, exist_ok=True)

        videos = [
            self._video(
                "vid-1",
                "POV bloating after lunch? Try this simple relief routine demo.",
                120000,
                9000,
                200,
                300,
            ),
            self._video(
                "vid-2",
                "Stomach discomfort routine before work with quick digestion tips.",
                85000,
                6200,
                140,
                210,
            ),
        ]
        (raw_scrapes / "pattern_raw.json").write_text(
            json.dumps({"generated_at": "2026-05-07T01:00:00Z", "top": videos}),
            encoding="utf-8",
        )
        (run_folder / "run_manifest.json").write_text(
            json.dumps(
                {
                    "run_timestamp": "2026-05-07T01:00:00Z",
                    "mode": "daily",
                    "requested_batch_size": 2,
                    "configuration": {"version": "v4"},
                }
            ),
            encoding="utf-8",
        )
        (run_folder / "run_metadata.json").write_text(
            json.dumps({"run_timestamp": "2026-05-07T01:00:00Z", "mode": "daily"}),
            encoding="utf-8",
        )
        (run_folder / "data" / "selected_batch.json").write_text(
            json.dumps(
                {
                    "selected_at": "2026-05-07T01:00:00Z",
                    "candidate_source": "data/raw_scrapes/pattern_raw.json",
                    "input_candidate_count": 2,
                    "eligible_candidate_count": 2,
                    "selected_candidate_count": 2,
                    "selected_candidates": [{"id": "vid-1"}, {"id": "vid-2"}],
                    "config_version": "v4",
                }
            ),
            encoding="utf-8",
        )
        initialize_dashboard_store(workspace)

    def _video(
        self,
        video_id: str,
        caption: str,
        views: int,
        likes: int,
        comments: int,
        shares: int,
    ) -> dict:
        return {
            "id": video_id,
            "url": f"https://tiktok.test/{video_id}",
            "author_handle": f"creator-{video_id}",
            "caption": caption,
            "hashtags": ["guthealth", "bloating", "routine"],
            "source_input": "#guthealth",
            "video_download_url": f"https://cdn.test/{video_id}.mp4",
            "play_count": views,
            "like_count": likes,
            "comment_count": comments,
            "share_count": shares,
            "created_at": "2026-05-06T00:00:00Z",
        }


if __name__ == "__main__":
    unittest.main()
