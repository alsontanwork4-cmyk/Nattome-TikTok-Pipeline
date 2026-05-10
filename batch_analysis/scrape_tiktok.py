#!/usr/bin/env python3
"""
Nattome TikTok discovery scraper.

Calls the Apify TikTok scraper actor (clockworks/tiktok-scraper) for:
  - hashtags (e.g. #bloating, #guthealth)
  - keyword searches (e.g. "bloated stomach")
  - competitor profiles (e.g. @gaviscon)

Ranks all unique scraped videos by virality (engagement-weighted, recency-decayed)
and writes the full unique set to a JSON file for records and downstream handoff.

Required env: APIFY_TOKEN
Optional: --config path/to/scrape_config.json   (defaults to ./scrape_config.json next to this script,
                                                falling back to the bundled skill example config)
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from batch_analysis.candidates import normalize_scraped_candidate, select_candidates, virality_score
from batch_analysis.config import (
    DAILY_SELECTION_SIZE,
    DEFAULT_CONFIG,
    deep_merge,
    isoformat_local,
)
from batch_analysis.env import load_dotenv_files

APIFY_ACTOR_ID = "clockworks~tiktok-scraper"
APIFY_BASE = "https://api.apify.com/v2"

def load_config(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    fallback = WORKSPACE_ROOT / "skills" / "nattome-tiktok-candidate-discovery" / "assets" / "config.example.json"
    if fallback.exists():
        print(f"[info] no scrape config found, using {fallback}", file=sys.stderr)
        return json.loads(fallback.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"No config at {path} and no example config bundled.")


def effective_scrape_options(config: dict, args) -> dict:
    """Resolve CLI flags over dashboard-saved production scrape defaults."""
    selection = config.get("selection") if isinstance(config.get("selection"), dict) else {}
    return {
        "scope": args.scope or config.get("scope") or "all",
        "results_per_input": int(
            args.results_per_input
            if args.results_per_input is not None
            else config.get("results_per_input", 20)
        ),
        "download_videos": bool(
            args.download_videos
            or config.get("requires_downloadable_video")
            or selection.get("requires_downloadable_video")
        ),
    }


def apify_run_actor(token: str, actor_id: str, run_input: dict, timeout_s: int = 300) -> list[dict]:
    """Run an Apify actor synchronously and return its dataset items."""
    url = f"{APIFY_BASE}/acts/{actor_id}/run-sync-get-dataset-items?token={token}"
    body = json.dumps(run_input).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Apify HTTP {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Apify network error: {e.reason}") from e


def build_run_input(
    hashtags: list[str],
    keywords: list[str],
    profiles: list[str],
    results_per_input: int,
    download_videos: bool,
) -> dict:
    """Shape the input the way clockworks/tiktok-scraper expects.

    The actor accepts hashtags, search queries, and profile URLs in one run.
    """
    profile_urls = []
    for p in profiles:
        handle = p.lstrip("@")
        profile_urls.append(f"https://www.tiktok.com/@{handle}")
    return {
        "hashtags": [h.lstrip("#") for h in hashtags],
        "searchQueries": keywords,
        "profiles": profile_urls,
        "resultsPerPage": results_per_input,
        "shouldDownloadVideos": download_videos,
        "shouldDownloadCovers": False,
        "shouldDownloadSubtitles": False,
        "shouldDownloadSlideshowImages": False,
    }


def build_output_payload(
    *,
    now: datetime,
    scope: str,
    hashtags: list[str],
    keywords: list[str],
    profiles: list[str],
    raw_item_count: int,
    unique_items: list[dict],
) -> dict:
    return {
        "generated_at": isoformat_local(now),
        "scope": scope,
        "inputs": {"hashtags": hashtags, "keywords": keywords, "profiles": profiles},
        "raw_item_count": raw_item_count,
        "unique_video_count": len(unique_items),
        "total_candidates": len(unique_items),
        "top": [
            {**normalize_scraped_candidate(it), "virality_score": round(virality_score(it, now), 4)}
            for it in unique_items
        ],
        "raw_items": unique_items,
    }


def build_daily_selection_payload(
    *,
    full_payload: dict,
    source_scrape: Path,
    selection_size: int = DAILY_SELECTION_SIZE,
    configuration: dict,
    run_timestamp: datetime,
) -> dict:
    top = full_payload.get("top") if isinstance(full_payload.get("top"), list) else []
    candidate_pool = top
    selected_batch = select_candidates(
        candidate_pool,
        discovery_selection_configuration(configuration),
        run_timestamp,
        selection_size,
        source_scrape,
    )
    selected = selected_batch["selected_candidates"]
    return {
        "generated_at": full_payload.get("generated_at"),
        "source_scrape": str(source_scrape),
        "selection_purpose": "daily_evidence_analysis_handoff",
        "selection_strategy": selected_batch["selection_strategy"],
        "selection_pool_size": len(candidate_pool),
        "input_candidate_count": selected_batch["input_candidate_count"],
        "eligible_candidate_count": selected_batch["eligible_candidate_count"],
        "selection_count": len(selected),
        "minimum_eligibility_filter": selected_batch["minimum_eligibility_filter"],
        "top": selected,
        "excluded_candidates": selected_batch["excluded_candidates"],
    }


def discovery_selection_configuration(config: dict) -> dict:
    """Build the batch-analysis selection config from discovery settings.

    Dashboard-saved scraper config stores eligibility under "selection". Older
    or hand-edited config may keep those values at the top level, so accept both
    while preserving batch-analysis defaults such as requires_tiktok_link.
    """
    selection = {}
    configured_selection = config.get("selection")
    if isinstance(configured_selection, dict):
        selection.update(configured_selection)
    for key in (
        "minimum_views",
        "maximum_age_days",
        "minimum_weighted_engagement_rate",
        "requires_tiktok_link",
        "requires_downloadable_video",
        "exclusion_terms",
    ):
        if key in config:
            selection[key] = config[key]
    return deep_merge(DEFAULT_CONFIG, {"selection": selection})


def assert_output_paths_available(*paths: Path, overwrite: bool = False) -> None:
    if overwrite:
        return
    existing = [path for path in paths if path and path.exists()]
    if existing:
        formatted = ", ".join(str(path) for path in existing)
        raise FileExistsError(
            "refusing to overwrite existing scrape output; use a unique run folder "
            f"or pass --overwrite: {formatted}"
        )


def deduplicate(items: list[dict]) -> list[dict]:
    """Same video can come back from multiple inputs — keep the first."""
    seen = set()
    out = []
    for it in items:
        vid = it.get("id")
        if not vid or vid in seen:
            continue
        seen.add(vid)
        out.append(it)
    return out


def main() -> int:
    load_dotenv_files([Path.cwd(), WORKSPACE_ROOT], override=True)
    ap = argparse.ArgumentParser(description="Nattome TikTok discovery scraper")
    ap.add_argument("--config", type=Path, default=Path(__file__).parent / "scrape_config.json",
                    help="Path to scrape_config.json (defaults to ./scrape_config.json then bundled example)")
    ap.add_argument("--output", type=Path, required=True, help="Where to write the ranked unique scrape JSON")
    ap.add_argument("--results-per-input", type=int, default=None,
                    help="Apify resultsPerPage per hashtag/keyword/profile (default: config results_per_input, then 20)")
    ap.add_argument("--download-videos", action="store_true",
                    help="Ask Apify to include downloadable video sources for evidence-first batch analysis")
    ap.add_argument("--daily-selection-output", type=Path,
                    help="Optional handoff JSON containing the daily top videos for daily evidence analysis")
    ap.add_argument("--scope", choices=["all", "hashtags", "keywords", "profiles"], default=None,
                    help="Limit which inputs to run (default: config scope, then all)")
    ap.add_argument("--overwrite", action="store_true",
                    help="Allow replacing existing output files. Defaults to refusing overwrites.")
    args = ap.parse_args()

    token = os.environ.get("APIFY_TOKEN")
    if not token:
        print("error: APIFY_TOKEN env var is not set. Get one from https://console.apify.com/account/integrations", file=sys.stderr)
        return 2

    config = load_config(args.config)

    options = effective_scrape_options(config, args)

    hashtags = config.get("hashtags", []) if options["scope"] in ("all", "hashtags") else []
    keywords = config.get("keywords", []) if options["scope"] in ("all", "keywords") else []
    profiles = config.get("competitor_profiles", []) if options["scope"] in ("all", "profiles") else []

    if not (hashtags or keywords or profiles):
        print("error: nothing to scrape (config has no hashtags/keywords/profiles for this scope)", file=sys.stderr)
        return 2

    try:
        output_paths = [args.output]
        if args.daily_selection_output:
            output_paths.append(args.daily_selection_output)
        assert_output_paths_available(*output_paths, overwrite=args.overwrite)
    except FileExistsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"[info] scraping: {len(hashtags)} hashtags, {len(keywords)} keywords, {len(profiles)} profiles", file=sys.stderr)

    run_input = build_run_input(
        hashtags,
        keywords,
        profiles,
        options["results_per_input"],
        options["download_videos"],
    )
    t0 = time.time()
    raw = apify_run_actor(token, APIFY_ACTOR_ID, run_input)
    print(f"[info] apify returned {len(raw)} raw items in {time.time()-t0:.1f}s", file=sys.stderr)

    unique = deduplicate(raw)

    now = datetime.now(tz=timezone.utc)
    scored = sorted(unique, key=lambda it: virality_score(it, now), reverse=True)

    payload = build_output_payload(
        now=now,
        scope=options["scope"],
        hashtags=hashtags,
        keywords=keywords,
        profiles=profiles,
        raw_item_count=len(raw),
        unique_items=scored,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[ok] wrote {len(scored)} unique scraped videos to {args.output}", file=sys.stderr)
    if args.daily_selection_output:
        daily_selection = build_daily_selection_payload(
            full_payload=payload,
            source_scrape=args.output,
            configuration=config,
            run_timestamp=now,
        )
        args.daily_selection_output.parent.mkdir(parents=True, exist_ok=True)
        args.daily_selection_output.write_text(
            json.dumps(daily_selection, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(
            f"[ok] wrote daily top videos selection to {args.daily_selection_output}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
