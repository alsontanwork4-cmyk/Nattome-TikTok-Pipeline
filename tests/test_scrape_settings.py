import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from dashboard.settings import (
    READ_ONLY_SETTINGS,
    get_active_settings_version,
    list_settings_versions,
    rollback_settings_version,
    save_settings_version,
    validate_scrape_settings,
)
from dashboard.store import DASHBOARD_DB_PATH


class ScrapeSettingsTest(unittest.TestCase):
    def test_validation_normalizes_marketer_editable_settings(self):
        settings = validate_scrape_settings(
            {
                "hashtags": ["#GutHealth", " bloating "],
                "keywords": "bloated stomach\nacid reflux",
                "competitor_profiles": ["@gaviscon", " gutgang "],
                "scope": "hashtags",
                "results_per_input": "25",
                "top_n": "30",
                "daily_selection_size": "5",
                "minimum_views": "10000",
                "maximum_age_days": "14",
                "minimum_weighted_engagement_rate": "0.025",
                "requires_downloadable_video": "on",
                "exclusion_terms": "ozempic\nweight loss",
            }
        )

        self.assertEqual(settings["hashtags"], ["GutHealth", "bloating"])
        self.assertEqual(settings["keywords"], ["bloated stomach", "acid reflux"])
        self.assertEqual(settings["competitor_profiles"], ["gaviscon", "gutgang"])
        self.assertEqual(settings["scope"], "hashtags")
        self.assertEqual(settings["results_per_input"], 25)
        self.assertEqual(settings["top_n"], 30)
        self.assertEqual(settings["daily_selection_size"], 5)
        self.assertEqual(settings["minimum_views"], 10000)
        self.assertEqual(settings["maximum_age_days"], 14)
        self.assertEqual(settings["minimum_weighted_engagement_rate"], 0.025)
        self.assertIs(settings["requires_downloadable_video"], True)
        self.assertEqual(settings["exclusion_terms"], ["ozempic", "weight loss"])

    def test_save_requires_reason_and_creates_active_version_history(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            with self.assertRaises(ValueError):
                save_settings_version(
                    workspace,
                    {"hashtags": ["#guthealth"]},
                    reason="  ",
                    user="marketer@example.com",
                )

            first = save_settings_version(
                workspace,
                {"hashtags": ["#guthealth"], "keywords": ["bloating"]},
                reason="Initial production settings",
                user="marketer@example.com",
            )
            second = save_settings_version(
                workspace,
                {"hashtags": ["#guthealth", "#digestion"], "keywords": ["bloating"]},
                reason="Add digestion source",
                user="marketer@example.com",
            )
            active = get_active_settings_version(workspace)

            self.assertEqual(first.version, 1)
            self.assertEqual(second.version, 2)
            self.assertEqual(active.version, 2)
            self.assertEqual(second.old_settings["hashtags"], ["guthealth"])
            self.assertEqual(second.new_settings["hashtags"], ["guthealth", "digestion"])
            self.assertEqual(second.reason, "Add digestion source")
            self.assertEqual(second.changed_by, "marketer@example.com")
            self.assertTrue(second.is_active)

            connection = sqlite3.connect(workspace / DASHBOARD_DB_PATH)
            try:
                rows = connection.execute(
                    """
                    SELECT version, settings_json, old_settings_json, new_settings_json, reason, created_by, is_active
                    FROM scrape_settings_versions
                    ORDER BY version
                    """
                ).fetchall()
            finally:
                connection.close()

            self.assertEqual([row[0] for row in rows], [1, 2])
            self.assertEqual([row[6] for row in rows], [0, 1])
            self.assertEqual(json.loads(rows[1][1])["hashtags"], ["guthealth", "digestion"])
            self.assertEqual(json.loads(rows[1][2])["hashtags"], ["guthealth"])
            self.assertEqual(json.loads(rows[1][3])["hashtags"], ["guthealth", "digestion"])
            self.assertEqual(rows[1][4], "Add digestion source")
            self.assertEqual(rows[1][5], "marketer@example.com")

    def test_rollback_creates_new_active_version_without_deleting_history(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            save_settings_version(
                workspace,
                {"hashtags": ["guthealth"], "keywords": ["bloating"]},
                reason="Initial settings",
                user="local",
            )
            save_settings_version(
                workspace,
                {"hashtags": ["random"], "keywords": ["bloating"]},
                reason="Bad experiment",
                user="local",
            )

            rollback = rollback_settings_version(
                workspace,
                target_version=1,
                reason="Restore gut health source",
                user="marketer@example.com",
            )
            versions = list_settings_versions(workspace)

            self.assertEqual(rollback.version, 3)
            self.assertEqual(rollback.new_settings["hashtags"], ["guthealth"])
            self.assertEqual(rollback.rollback_of_version, 1)
            self.assertEqual([version.version for version in versions], [3, 2, 1])
            self.assertEqual([version.is_active for version in versions], [True, False, False])

    def test_read_only_settings_are_declared_for_mvp(self):
        self.assertIn("APIFY_TOKEN", READ_ONLY_SETTINGS["API keys"])
        self.assertIn("clockworks~tiktok-scraper", READ_ONLY_SETTINGS["Apify actor ID"])
        self.assertIn("gemini-2.5-flash", READ_ONLY_SETTINGS["Gemini model"])


if __name__ == "__main__":
    unittest.main()
