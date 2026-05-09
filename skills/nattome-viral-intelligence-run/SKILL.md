---
name: nattome-viral-intelligence-run
description: Primary normal-operation skill for the stripped Nattome TikTok source-video pipeline. Scrapes TikTok candidates, creates the Daily Top Videos Selection handoff, downloads/copies source videos, and reports the run folder snapshot artifacts. Use this for recurring automations or "run the Nattome pipeline" while the downstream analysis pipeline is being rebuilt.
---

# Nattome Source Video Run

The active pipeline stops after source video download and snapshot indexing.

## Pre-Flight

Required for fresh discovery:

- `APIFY_TOKEN`

No other service credentials are used by the active runtime.

## Daily Run

From the project root:

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

Then create the source-video run folder:

```powershell
python batch_analysis/run_batch_analysis.py `
  --candidates "$runDir/data/daily_selection_top_videos.json" `
  --timestamp "$isoTimestamp"
```

## Report Back

Return only these paths/statuses:

- Raw scrape path
- Daily Top Videos Selection path
- Run Folder path
- `data/evidence_bundle_index.json`
- per-candidate source video state from `data/*_evidence_snapshot.json`

## Honesty Rules

- Do not discuss downstream analysis or production outputs as active outputs.
- Source video state can be `available`, `missing`, or `failed`; preserve it exactly.
