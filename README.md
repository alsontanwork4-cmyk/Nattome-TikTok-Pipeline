# Nattome TikTok Source Video Pipeline

This repository runs the compact Nattome TikTok source-video pipeline.

The active pipeline discovers TikTok candidates, creates a Daily Top Videos handoff, copies/downloads source videos, writes flat source-video snapshot artifacts, then runs a two-agent Gemini creative-reporting path for available source videos.

Python owns orchestration, status tracking, retries/idempotency, and artifact persistence. Gemini owns video evidence interpretation, creative framing, and final marketer-facing wording using a preferred Nattome POV report outline.

## Active Runtime

| Step | Entry point | Output |
|---|---|---|
| Discovery | `batch_analysis/scrape_tiktok.py` | full unique scrape JSON and Daily Top Videos JSON |
| Source video snapshot run | `batch_analysis/run_batch_analysis.py` | run folder with selected batch, source metadata, source videos, snapshot index, Gemini agent outputs, and Nattome POV reports |

## Folder Layout

```text
batch_analysis/
  candidates.py       candidate loading, filtering, scoring, selection
  config.py           run defaults, timestamps, folder naming
  env.py              .env loading
  evidence_io.py      source metadata/video snapshot writer
  gemini_reports.py   two-agent Gemini POV report orchestration
  run.py              compact orchestration, manifest, and batch index writer
  run_batch_analysis.py command-line entrypoint for source-video snapshot runs
  scrape_config.json  active discovery config written by the dashboard
  scrape_tiktok.py    Apify TikTok scraper and Daily Top Videos handoff writer
  tool_adapters.py    source video copy/download helpers

skills/
  nattome-tiktok-candidate-discovery/  consolidated project skill plus assets/references
```

## Environment

| Variable | Required for | Notes |
|---|---|---|
| `APIFY_TOKEN` | Discovery | Needed when scraping via Apify. |
| `GEMINI_API_KEY` | Nattome POV reports | Loaded from the environment or `.env`; missing credentials are recorded in the run manifest without attempting Gemini generation. |
| `TELEGRAM_BOT_TOKEN` | Telegram delivery | Loaded from the environment or `.env`; missing credentials are recorded after report generation. |
| `TELEGRAM_CHAT_ID` | Telegram delivery | Target chat for generated report delivery. |

The Gemini runtime uses the official `google-genai` package.

## Manual Run

Create the daily discovery handoff:

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

Create the source-video run folder:

```powershell
python batch_analysis/run_batch_analysis.py `
  --candidates "$runDir/data/daily_selection_top_videos.json" `
  --timestamp "$isoTimestamp"
```

The run folder is written under `runs/batch-analysis/<timestamp>_daily/` and contains every artifact for that run:

- `run_metadata.json`
- `run_manifest.json`
- `data/raw_scrape_all.json`
- `data/daily_selection_top_videos.json`
- `data/selected_batch.json`
- `reports/selected_batch.md`
- `data/evidence_bundle_index.json`
- `data/<rank>_<video-id>_source_metadata.json`
- `data/<rank>_<video-id>_evidence_snapshot.json`
- `data/<rank>_<video-id>_gemini_evidence.json`
- `data/<rank>_<video-id>_gemini_creative_response.json`
- `evidence/<rank>_<video-id>_source_video.<ext>`
- `reports/<rank>_<video-id>_nattome_pov_report.md`

The final report is not rendered from a Python template. The Creative Strategist Gemini prompt provides a preferred outline based on the proven creative production report shape, then asks Gemini to generate the Markdown while grounding recommendations in observable evidence and the Nattome brand reference.

After report generation, the pipeline sends a Telegram summary message followed by the generated `.md` report document when `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are configured. The summary uses the run timestamp in Singapore time and includes run time, videos compared, and success/fail status. Telegram delivery is recorded as its own manifest phase so delivery failures do not erase successful report artifacts.

## Tests

```powershell
python -m pytest -q
```
