---
name: nattome-batch-analysis-run
description: Run or maintain the compact Nattome TikTok batch-analysis pipeline: scrape TikTok candidates, create the Daily Top Videos handoff, snapshot source videos, generate Gemini Nattome POV reports, and deliver final Markdown reports to Telegram.
---

# Nattome Batch Analysis Run

Use this as the single project skill for normal Nattome TikTok batch-analysis work. The active runtime code lives in `batch_analysis/`.

Python owns orchestration, candidate selection, source-video snapshots, manifest/status records, and delivery. Gemini owns source-video evidence interpretation and marketer-facing Nattome POV report wording.

## Pre-Flight

Check required credentials without printing values.

- `APIFY_TOKEN`: required for fresh TikTok discovery through Apify.
- `GEMINI_API_KEY`: required for Gemini evidence and Nattome POV report generation.
- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`: required only for Telegram delivery after reports are generated.

Treat the project root `.env` as a valid credential source. If Gemini or Telegram credentials are missing, the runtime records the missing phase honestly in `run_manifest.json`; do not imply those phases completed.

## Daily Run

From the project root, create one timestamp and reuse it for discovery and batch analysis:

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

```powershell
python batch_analysis/run_batch_analysis.py `
  --candidates "$runDir/data/daily_selection_top_videos.json" `
  --timestamp "$isoTimestamp"
```

The run folder is `runs/batch-analysis/<timestamp>_daily/`.

## Outputs To Report

Report the run in terms of concrete artifacts and manifest phase status:

- `data/raw_scrape_all.json`
- `data/daily_selection_top_videos.json`
- `data/selected_batch.json`
- `reports/selected_batch.md`
- `data/evidence_bundle_index.json`
- `data/<rank>_<video-id>_source_metadata.json`
- `data/<rank>_<video-id>_evidence_snapshot.json`
- `evidence/<rank>_<video-id>_source_video.<ext>`
- `data/<rank>_<video-id>_gemini_evidence.json`
- `data/<rank>_<video-id>_gemini_creative_response.json`
- `reports/<rank>_<video-id>_nattome_pov_report.md`
- `run_manifest.json` phase status, including `telegram_delivery`

## Operating Rules

- Do not invent analysis results from captions or metadata.
- Preserve selected candidate rank and source-video state exactly.
- Source video state is factual: `available`, `missing`, or `failed`.
- Do not render final Nattome POV reports from fixed Python templates; Gemini writes the final Markdown.
- Ground recommendations in observable video evidence or explicit Nattome brand guidance.
- Do not invent clinical claims, product outcomes, doctor recommendations, guaranteed relief, cure language, or disease-prevention claims.
- Treat Telegram delivery as separate from report generation. Delivery failure does not invalidate generated report artifacts.

## References And Assets

- `../../batch_analysis/scrape_tiktok.py` - Apify TikTok scraper.
- `../../batch_analysis/run_batch_analysis.py` - CLI entrypoint for the batch-analysis run.
- `../../batch_analysis/run.py` - orchestration, manifest, source snapshots, Gemini, and Telegram delivery.
- `../../batch_analysis/gemini_reports.py` - two-agent Gemini report generation.
- `../../batch_analysis/telegram_delivery.py` - Telegram summary and report document delivery.
- `../../batch_analysis/scrape_config.json` - active discovery config.
- `assets/config.example.json` - example config.
- `assets/daily_brief_template.md` - legacy brief template; do not use as the final report renderer.
- `references/nattome_brand.md` - brand voice and product positioning reference.
- `references/virality_framework.md` - virality analysis lens reference.
