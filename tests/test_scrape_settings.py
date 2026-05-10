import unittest

from dashboard.scrape_settings import (
    DEFAULT_SCRAPE_SETTINGS,
    validate_scrape_settings,
)


class ScrapeSettingsTest(unittest.TestCase):
    def test_validation_normalizes_marketer_editable_settings(self):
        settings = validate_scrape_settings(
            {
                "hashtags": ["#GutHealth", " bloating "],
                "keywords": "bloated stomach\nacid reflux",
                "competitor_profiles": ["@gaviscon", " gutgang "],
                "scope": "hashtags",
                "results_per_input": "25",
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
        self.assertEqual(settings["minimum_views"], 10000)
        self.assertEqual(settings["maximum_age_days"], 14)
        self.assertEqual(settings["minimum_weighted_engagement_rate"], 0.025)
        self.assertIs(settings["requires_downloadable_video"], True)
        self.assertEqual(settings["exclusion_terms"], ["ozempic", "weight loss"])

    def test_default_settings_are_valid_for_supabase_dashboard(self):
        settings = validate_scrape_settings(DEFAULT_SCRAPE_SETTINGS)

        self.assertEqual(settings["scope"], DEFAULT_SCRAPE_SETTINGS["scope"])
        self.assertEqual(settings["results_per_input"], DEFAULT_SCRAPE_SETTINGS["results_per_input"])
        self.assertIn("gut health routine", settings["keywords"])


if __name__ == "__main__":
    unittest.main()
