import importlib.util
from types import SimpleNamespace
from pathlib import Path
import unittest


WORKSPACE = Path(__file__).resolve().parents[1]
SCRAPER = WORKSPACE / "skills" / "nattome-tiktok-candidate-discovery" / "scripts" / "scrape_tiktok.py"


def load_scraper_module():
    spec = importlib.util.spec_from_file_location("nattome_daily_scraper", SCRAPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DailyDiscoveryHandoffTest(unittest.TestCase):
    def test_dashboard_saved_config_can_supply_scrape_option_defaults(self):
        scraper = load_scraper_module()

        options = scraper.effective_scrape_options(
            {
                "scope": "hashtags",
                "results_per_input": 25,
                "top_n": 30,
                "daily_selection_size": 7,
                "selection": {"requires_downloadable_video": True},
            },
            SimpleNamespace(
                scope=None,
                results_per_input=None,
                top=None,
                daily_selection_size=None,
                download_videos=False,
            ),
        )

        self.assertEqual(
            options,
            {
                "scope": "hashtags",
                "results_per_input": 25,
                "top": 30,
                "daily_selection_size": 7,
                "download_videos": True,
            },
        )

    def test_daily_selection_payload_preserves_top_slice_and_source_scrape(self):
        scraper = load_scraper_module()
        full_payload = {
            "generated_at": "2026-05-07T07:41:52+00:00",
            "top": [
                {"id": "daily-1"},
                {"id": "daily-2"},
                {"id": "daily-3"},
                {"id": "daily-4"},
                {"id": "daily-5"},
                {"id": "not-daily"},
            ],
        }

        handoff = scraper.build_daily_selection_payload(
            full_payload=full_payload,
            source_scrape=Path("data/raw_scrapes/nattome_raw_20260507_top30.json"),
            selection_size=5,
        )

        self.assertEqual(handoff["selection_purpose"], "daily_evidence_analysis_handoff")
        self.assertEqual(handoff["selection_count"], 5)
        self.assertEqual([candidate["id"] for candidate in handoff["top"]], [
            "daily-1",
            "daily-2",
            "daily-3",
            "daily-4",
            "daily-5",
        ])
        self.assertEqual(
            handoff["source_scrape"],
            "data\\raw_scrapes\\nattome_raw_20260507_top30.json"
            if "\\" in str(Path("data/raw_scrapes/nattome_raw_20260507_top30.json"))
            else "data/raw_scrapes/nattome_raw_20260507_top30.json",
        )


if __name__ == "__main__":
    unittest.main()
