#!/usr/bin/env python3
"""
Nattome TikTok discovery scraper.

Calls the Apify TikTok scraper actor (clockworks/tiktok-scraper) for:
  - hashtags (e.g. #bloating, #guthealth)
  - keyword searches (e.g. "bloated stomach")
  - competitor profiles (e.g. @gaviscon)

Ranks by virality (engagement-weighted, recency-decayed) and writes the top N
to a JSON file for the SKILL to read and analyse.

Required env: APIFY_TOKEN
Optional: --config path/to/config.json   (defaults to ./config.json next to this script,
                                          falling back to the bundled config.example.json)
"""

import argparse
import json
import math
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from batch_analysis.candidates import select_candidates
from batch_analysis.config import DEFAULT_CONFIG, deep_merge
from batch_analysis.env import load_dotenv_files

APIFY_ACTOR_ID = "clockworks~tiktok-scraper"
APIFY_BASE = "https://api.apify.com/v2"
DAILY_SELECTION_POOL_SIZE = 30

# Engagement weighting — comments and shares are stronger signals than likes.
LIKE_WEIGHT = 1
COMMENT_WEIGHT = 5
SHARE_WEIGHT = 10

# Recency decay: a video older than this many days is half-weighted.
RECENCY_HALFLIFE_DAYS = 7


def load_config(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    fallback = Path(__file__).parent.parent / "assets" / "config.example.json"
    if fallback.exists():
        print(f"[info] no config.json found, using {fallback}", file=sys.stderr)
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
        "top": int(args.top if args.top is not None else config.get("top_n", 5)),
        "daily_selection_size": int(
            args.daily_selection_size
            if args.daily_selection_size is not None
            else config.get("daily_selection_size", 3)
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


def parse_create_time(item: dict) -> datetime | None:
    """clockworks returns either a Unix timestamp or an ISO string depending on field."""
    for key in ("createTimeISO", "createTime"):
        v = item.get(key)
        if v is None:
            continue
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v, tz=timezone.utc)
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError:
                continue
    return None


def virality_score(item: dict, now: datetime) -> float:
    """Engagement-weighted, recency-decayed virality score.

    Pure views can be inflated by paid pushes — we lean on engagement ratio,
    then nudge by absolute reach so genuinely viral videos still beat
    high-engagement micro videos.
    """
    views = max(int(item.get("playCount") or 0), 1)
    likes = int(item.get("diggCount") or 0)
    comments = int(item.get("commentCount") or 0)
    shares = int(item.get("shareCount") or 0)

    engagement = (
        likes * LIKE_WEIGHT
        + comments * COMMENT_WEIGHT
        + shares * SHARE_WEIGHT
    )
    engagement_rate = engagement / views

    # Reach factor — log-scaled so 10M views isn't 100x a 100K-view banger
    reach = math.log10(views + 1)

    # Recency decay
    created = parse_create_time(item)
    if created is None:
        recency = 0.5  # unknown — give it middling weight
    else:
        age_days = max((now - created).total_seconds() / 86400, 0)
        recency = 0.5 ** (age_days / RECENCY_HALFLIFE_DAYS)

    return engagement_rate * reach * recency


def first_nonempty(*values) -> str | None:
    for value in values:
        if isinstance(value, str) and value:
            return value
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item:
                    return item
        if isinstance(value, dict):
            nested = first_nonempty(*value.values())
            if nested:
                return nested
    return None


def downloadable_video_url(item: dict) -> str | None:
    video_meta = item.get("videoMeta") if isinstance(item.get("videoMeta"), dict) else {}
    media_urls = item.get("mediaUrls") or item.get("media_urls") or []
    return first_nonempty(
        item.get("video_download_url"),
        item.get("download_url"),
        item.get("downloadUrl"),
        item.get("downloadLink"),
        item.get("downloadedVideoUrl"),
        item.get("downloaded_video_url"),
        item.get("media_url"),
        item.get("mediaUrl"),
        media_urls,
        video_meta.get("downloadAddr"),
        video_meta.get("downloadUrl"),
        video_meta.get("download_url"),
        video_meta.get("playAddr"),
    )


def normalize(item: dict) -> dict:
    """Pull a clean, predictable shape out of the actor's verbose output."""
    author = item.get("authorMeta") or {}
    music = item.get("musicMeta") or {}
    return {
        "id": item.get("id"),
        "url": item.get("webVideoUrl") or item.get("videoUrl"),
        "author_handle": author.get("name") or author.get("nickName"),
        "author_followers": author.get("fans"),
        "caption": item.get("text") or "",
        "hashtags": [h.get("name") for h in (item.get("hashtags") or []) if h.get("name")],
        "duration_s": item.get("videoMeta", {}).get("duration") if isinstance(item.get("videoMeta"), dict) else None,
        "music": {"title": music.get("musicName"), "author": music.get("musicAuthor"), "original": music.get("musicOriginal")},
        "video_download_url": downloadable_video_url(item),
        "play_count": item.get("playCount"),
        "like_count": item.get("diggCount"),
        "comment_count": item.get("commentCount"),
        "share_count": item.get("shareCount"),
        "created_at": (parse_create_time(item) or "").isoformat() if parse_create_time(item) else None,
        "source_input": item.get("_source_input"),  # set by us below
    }


def build_output_payload(
    *,
    now: datetime,
    scope: str,
    hashtags: list[str],
    keywords: list[str],
    profiles: list[str],
    total_candidates: int,
    top: list[dict],
) -> dict:
    return {
        "generated_at": now.isoformat(),
        "scope": scope,
        "inputs": {"hashtags": hashtags, "keywords": keywords, "profiles": profiles},
        "total_candidates": total_candidates,
        "top": [
            {**normalize(it), "virality_score": round(virality_score(it, now), 4)}
            for it in top
        ],
    }


def build_daily_selection_payload(
    *,
    full_payload: dict,
    source_scrape: Path,
    selection_size: int,
    configuration: dict,
    run_timestamp: datetime,
) -> dict:
    top = full_payload.get("top") if isinstance(full_payload.get("top"), list) else []
    candidate_pool = top[:DAILY_SELECTION_POOL_SIZE]
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
    ap.add_argument("--config", type=Path, default=Path(__file__).parent.parent / "config.json",
                    help="Path to config.json (defaults to ../config.json then bundled example)")
    ap.add_argument("--output", type=Path, required=True, help="Where to write the ranked top-N JSON")
    ap.add_argument("--top", type=int, default=None,
                    help="How many top videos to keep (default: config top_n, then 5)")
    ap.add_argument("--results-per-input", type=int, default=None,
                    help="Apify resultsPerPage per hashtag/keyword/profile (default: config results_per_input, then 20)")
    ap.add_argument("--download-videos", action="store_true",
                    help="Ask Apify to include downloadable video sources for evidence-first batch analysis")
    ap.add_argument("--daily-selection-output", type=Path,
                    help="Optional handoff JSON containing the daily top videos for daily evidence analysis")
    ap.add_argument("--daily-selection-size", type=int, default=None,
                    help="How many top videos to include in the daily evidence handoff (default: config daily_selection_size, then 3)")
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

    raw = deduplicate(raw)

    now = datetime.now(tz=timezone.utc)
    scored = sorted(raw, key=lambda it: virality_score(it, now), reverse=True)
    top = scored[: options["top"]]

    payload = build_output_payload(
        now=now,
        scope=options["scope"],
        hashtags=hashtags,
        keywords=keywords,
        profiles=profiles,
        total_candidates=len(raw),
        top=top,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[ok] wrote top {len(top)} to {args.output}", file=sys.stderr)
    if args.daily_selection_output:
        daily_selection = build_daily_selection_payload(
            full_payload=payload,
            source_scrape=args.output,
            selection_size=options["daily_selection_size"],
            configuration=config,
            run_timestamp=now,
        )
        args.daily_selection_output.parent.mkdir(parents=True, exist_ok=True)
        args.daily_selection_output.write_text(
            json.dumps(daily_selection, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(
            f"[ok] wrote daily selection top {daily_selection['selection_count']} to {args.daily_selection_output}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
