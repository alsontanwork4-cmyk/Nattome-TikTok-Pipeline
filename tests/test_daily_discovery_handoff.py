import importlib.util
from datetime import datetime, timezone
from types import SimpleNamespace
from pathlib import Path
import unittest


WORKSPACE = Path(__file__).resolve().parents[1]
SCRAPER = WORKSPACE / "batch_analysis" / "scrape_tiktok.py"


def load_scraper_module():
    spec = importlib.util.spec_from_file_location("nattome_daily_scraper", SCRAPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DailyDiscoveryHandoffTest(unittest.TestCase):
    def test_daily_selection_defaults_to_canonical_top_videos(self):
        scraper = load_scraper_module()

        options = scraper.effective_scrape_options(
            {},
            SimpleNamespace(
                scope=None,
                results_per_input=None,
                top=None,
                download_videos=False,
            ),
        )

        self.assertNotIn("top", options)
        self.assertNotIn("daily_selection_size", options)

    def test_dashboard_saved_config_can_supply_scrape_option_defaults(self):
        scraper = load_scraper_module()

        options = scraper.effective_scrape_options(
            {
                "scope": "hashtags",
                "results_per_input": 25,
                "daily_selection_size": 7,
                "selection": {"requires_downloadable_video": True},
            },
            SimpleNamespace(
                scope=None,
                results_per_input=None,
                top=None,
                download_videos=False,
            ),
        )

        self.assertEqual(
            options,
            {
                "scope": "hashtags",
                "results_per_input": 25,
                "download_videos": True,
            },
        )

    def test_scrape_payload_records_all_unique_items_without_top_cap(self):
        scraper = load_scraper_module()
        run_timestamp = datetime(2026, 5, 7, 7, 41, 52, tzinfo=timezone.utc)

        def scraped_item(candidate_id, likes):
            return {
                "id": candidate_id,
                "webVideoUrl": f"https://www.tiktok.com/@creator/video/{candidate_id}",
                "downloadedVideoUrl": f"https://cdn.example.com/{candidate_id}.mp4",
                "text": f"Video {candidate_id}",
                "playCount": 100000,
                "diggCount": likes,
                "commentCount": 0,
                "shareCount": 0,
                "createTimeISO": "2026-05-06T00:00:00Z",
            }

        raw_items = [scraped_item(str(index), index) for index in range(35)]
        raw_items.append(scraped_item("10", 9999))
        unique_items = scraper.deduplicate(raw_items)
        scored_items = sorted(unique_items, key=lambda item: scraper.virality_score(item, run_timestamp), reverse=True)

        payload = scraper.build_output_payload(
            now=run_timestamp,
            scope="all",
            hashtags=["guthealth"],
            keywords=["bloating"],
            profiles=["gaviscon"],
            raw_item_count=len(raw_items),
            unique_items=scored_items,
        )

        self.assertEqual(payload["raw_item_count"], 36)
        self.assertEqual(payload["unique_video_count"], 35)
        self.assertEqual(payload["total_candidates"], 35)
        self.assertEqual(len(payload["top"]), 35)
        self.assertEqual(len(payload["raw_items"]), 35)
        self.assertEqual(payload["top"][0]["id"], "34")
        self.assertEqual(payload["raw_items"][0]["id"], "34")

    def test_daily_selection_payload_uses_all_eligible_ranked_candidates(self):
        scraper = load_scraper_module()
        run_timestamp = datetime(2026, 5, 7, 7, 41, 52, tzinfo=timezone.utc)

        def candidate(candidate_id, **overrides):
            item = {
                "id": candidate_id,
                "url": f"https://www.tiktok.com/@creator/video/{candidate_id}",
                "video_download_url": f"https://cdn.example.com/{candidate_id}.mp4",
                "caption": "Acid reflux and bloating routine for gut health",
                "play_count": 100000,
                "like_count": 4000,
                "comment_count": 0,
                "share_count": 0,
                "created_at": "2026-05-06T00:00:00Z",
            }
            item.update(overrides)
            return item

        top = [
            candidate("low-views", play_count=9999),
            candidate("excluded-topic", caption="Weight loss cleanse for bloating"),
            candidate("missing-download", video_download_url=""),
            candidate("eligible-weaker", like_count=4000),
            candidate("eligible-stronger", like_count=8000),
            candidate("eligible-third", like_count=7000),
            candidate("eligible-fourth", like_count=6000),
            candidate("eligible-fifth", like_count=5000),
            candidate("eligible-sixth", like_count=4500),
        ]
        top.extend(candidate(f"pool-filler-{index}", play_count=9999) for index in range(25))
        top.append(candidate("outside-former-cap", like_count=50000))
        full_payload = {
            "generated_at": "2026-05-07T15:41:52+08:00",
            "top": top,
        }

        handoff = scraper.build_daily_selection_payload(
            full_payload=full_payload,
            source_scrape=Path("data/raw_scrapes/nattome_raw_20260507_all.json"),
            configuration={
                "selection": {
                    "minimum_views": 10000,
                    "maximum_age_days": 30,
                    "minimum_weighted_engagement_rate": 0.03,
                    "requires_downloadable_video": True,
                    "exclusion_terms": ["weight loss"],
                },
            },
            run_timestamp=run_timestamp,
        )

        self.assertEqual(handoff["selection_purpose"], "daily_evidence_analysis_handoff")
        self.assertEqual(handoff["selection_count"], 5)
        self.assertEqual(handoff["eligible_candidate_count"], 7)
        self.assertEqual(handoff["selection_pool_size"], 35)
        self.assertEqual([candidate["id"] for candidate in handoff["top"]], [
            "outside-former-cap",
            "eligible-stronger",
            "eligible-third",
            "eligible-fourth",
            "eligible-fifth",
        ])
        excluded = {item["id"]: item["reason"] for item in handoff["excluded_candidates"]}
        self.assertIn("below minimum views", excluded["low-views"])
        self.assertIn("matches exclusion term: weight loss", excluded["excluded-topic"])
        self.assertIn("missing downloadable video source", excluded["missing-download"])
        self.assertEqual(
            handoff["source_scrape"],
            "data\\raw_scrapes\\nattome_raw_20260507_all.json"
            if "\\" in str(Path("data/raw_scrapes/nattome_raw_20260507_all.json"))
            else "data/raw_scrapes/nattome_raw_20260507_all.json",
        )
    def test_scraper_refuses_to_overwrite_existing_outputs_by_default(self):
        scraper = load_scraper_module()
        output = WORKSPACE / ".tmp" / "existing_scrape_output.json"
        daily = WORKSPACE / ".tmp" / "existing_daily_selection.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("{}", encoding="utf-8")
        try:
            with self.assertRaises(FileExistsError):
                scraper.assert_output_paths_available(output, daily)
            scraper.assert_output_paths_available(output, daily, overwrite=True)
        finally:
            output.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
