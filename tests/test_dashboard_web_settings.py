import unittest

from dashboard.web_actions import _settings_form_payload
from dashboard.web_settings import _render_current_settings


class DashboardWebSettingsTest(unittest.TestCase):
    def test_current_settings_summary_prints_active_scrape_values(self):
        html = _render_current_settings(
            {
                "hashtags": ["guthealth", "bloating"],
                "keywords": ["bloated stomach"],
                "competitor_profiles": ["gaviscon"],
                "exclusion_terms": ["weight loss"],
                "scope": "hashtags",
                "results_per_input": 25,
                "minimum_views": 10000,
                "maximum_age_days": 14,
                "minimum_weighted_engagement_rate": 0.025,
                "requires_downloadable_video": True,
            }
        )

        self.assertIn("Your current settings", html)
        self.assertIn("#guthealth, #bloating", html)
        self.assertIn("bloated stomach", html)
        self.assertIn("@gaviscon", html)
        self.assertIn("weight loss", html)
        self.assertIn("hashtags", html)
        self.assertIn("25", html)
        self.assertIn("0.025", html)
        self.assertIn("Yes", html)

    def test_settings_payload_converts_engagement_percent_to_decimal(self):
        payload = _settings_form_payload(
            {
                "hashtags": ["#guthealth"],
                "keywords": [""],
                "competitor_profiles": [""],
                "scope": ["all"],
                "results_per_input": ["20"],
                "minimum_views": ["10000"],
                "maximum_age_days": ["30"],
                "minimum_engagement_rate_percent": ["3"],
                "requires_downloadable_video": ["on"],
                "exclusion_terms": [""],
            }
        )

        self.assertEqual(payload["minimum_weighted_engagement_rate"], "0.03")


if __name__ == "__main__":
    unittest.main()
