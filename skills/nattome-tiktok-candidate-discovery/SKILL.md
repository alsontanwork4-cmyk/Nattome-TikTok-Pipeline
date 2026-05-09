---
name: nattome-tiktok-candidate-discovery
description: Supporting reference for TikTok discovery and Daily Top Videos Selection handoff creation in the stripped Nattome source-video pipeline.
user-invocable: false
---

# Nattome TikTok Candidate Discovery

This skill documents scraper configuration and discovery handoff creation. The active runtime code lives in `batch_analysis/`.

The active runtime stops after source video download. Discovery must not describe downstream analysis or production outputs as active outputs.

## Pre-Flight

Required:

- `APIFY_TOKEN`

Treat the project root `.env` as a valid credential source. Check without printing token values. If `APIFY_TOKEN` is missing, stop and report it.

## Discovery Command

```powershell
$timestamp = (Get-Date).ToUniversalTime()
$localTimestamp = [System.TimeZoneInfo]::ConvertTimeBySystemTimeZoneId($timestamp, "Singapore Standard Time")
$stamp = $localTimestamp.ToString("yyyyMMddTHHmmss") + "+0800"
$isoTimestamp = $timestamp.ToString("yyyy-MM-ddTHH:mm:ssZ")
$runDir = "runs/batch-analysis/${stamp}_daily"
python batch_analysis/scrape_tiktok.py `
  --output "$runDir/data/raw_scrape_all.json" `
  --download-videos `
  --daily-selection-output "$runDir/data/daily_selection_top_videos.json"
```

Outputs:

- `runs/batch-analysis/<timestamp>_daily/data/raw_scrape_all.json`
- `runs/batch-analysis/<timestamp>_daily/data/daily_selection_top_videos.json`

The source-video snapshot step is handled by:

```powershell
python batch_analysis/run_batch_analysis.py `
  --candidates "$runDir/data/daily_selection_top_videos.json" `
  --timestamp "$isoTimestamp"
```

## Owned Files

- `../../batch_analysis/scrape_tiktok.py` - Apify TikTok scraper.
- `../../batch_analysis/scrape_config.json` - active discovery config.
- `assets/config.example.json` - example config.
- `assets/daily_brief_template.md` - optional discovery brief template.
- `references/nattome_brand.md` - brand voice and product positioning reference.
- `references/virality_framework.md` - virality analysis lens reference.
