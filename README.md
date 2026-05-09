# Nattome TikTok Content Discovery Pipeline

Daily viral intelligence pipeline for **Nattome** (Atomic Group's flagship digestive-health brand for Malaysians). It discovers viral TikToks, preserves evidence-ready candidates, analyzes source videos with Gemini, and generates evidence-backed Nattome Shootable Angles.

Discovery creates the data. Evidence analysis turns that data into actionable insight.

## What This Project Is

| Use case | Skill | Purpose / artifact | Runtime |
|---|---|---|---|
| **Normal daily run** | `nattome-viral-intelligence-run` | Runs discovery, creates the Daily Top-3 Selection handoff, prepares separate backfill candidates when useful, runs Gemini evidence analysis, and reports final paths and evidence status. | 20-40 min |
| **Discovery-only debugging** | `nattome-tiktok-candidate-discovery` | Supporting phase reference for scraper config and Daily Top-3 Selection handoff creation. | 3-8 min |
| **Evidence-only debugging** | `nattome-evidence-insight-analysis` | Supporting phase reference for rerunning evidence analysis on an existing Daily Top-3 JSON and optional backfill JSON. | 15-30 min |

Use `nattome-viral-intelligence-run` for normal operation. The phase skills are supporting references, not alternative normal workflows.

## Folder Layout

```text
.
├── README.md
├── CONTEXT.md                     <- terminology dictionary
├── progress.txt                   <- chronological execution log
├── .claude/settings.json          <- registers skills/ as a skill directory
├── skills/
│   ├── nattome-viral-intelligence-run/       <- primary daily run skill
│   ├── nattome-tiktok-candidate-discovery/   <- supporting phase 1 docs/scripts/assets
│   └── nattome-evidence-insight-analysis/    <- supporting phase 2 docs
├── batch_analysis/                <- importable evidence analysis package
├── scripts/
│   └── run_batch_analysis.py      <- thin compatibility CLI
├── dashboard/                     <- Python marketer-facing control room
├── tests/
├── docs/
│   ├── prd/
│   ├── adr/
│   └── issues/{,done/}
├── data/daily_runs/               <- raw scrapes + Daily Top-3 handoffs grouped by run id
├── data/raw_scrapes/              <- raw Apify TikTok scrapes
├── data/dashboard/                <- dashboard-owned SQLite state, ignored by git
├── outputs/daily_briefs/          <- optional discovery previews
├── outputs/reports/               <- final report + Excel workbook
└── runs/batch-analysis/           <- timestamped daily audit/debug run folders
```

## Environment Variables

| Variable | Required for | Notes |
|---|---|---|
| `APIFY_TOKEN` | Discovery | Apify API token. Without it, no scraping. |
| `GEMINI_API_KEY` | Evidence analysis | Gemini key used for source-video evidence extraction. |
| `TELEGRAM_BOT_TOKEN` | Optional | Telegram bot token. Skip silently if unset. |
| `TELEGRAM_CHAT_ID` | Optional | Target chat. Both Telegram variables must be set together. |
| `SUPABASE_URL` | Optional cloud publication | Required only when `run_batch_analysis.py --publish-cloud` is used. |
| `SUPABASE_SERVICE_ROLE_KEY` | Optional cloud publication | Required only when `run_batch_analysis.py --publish-cloud` is used. Never print this value. |

The project loads credentials from exported environment variables and from the project root `.env`. Do not print token values in logs or reports.

The evidence analysis path no longer shells out to local video/OCR/transcription tools. Gemini analyzes the source video and returns timestamped visual, visible-text, spoken-content, audio, hook, and claim evidence.

## Daily Evidence Architecture

The daily pipeline keeps `scripts/run_batch_analysis.py` as the stable CLI interface. It should stay thin: parse flags, call `batch_analysis.run.create_run`, and return the process exit code. Existing prompts, schedules, and shell commands can keep using the same script path and flags.

Implementation logic lives in `batch_analysis/`:

| Module | Responsibility |
|---|---|
| `config.py` | Defaults, run timestamps, run folder naming, config loading, mode batch sizes. |
| `candidates.py` | Candidate JSON loading, normalization, scoring, filtering, and selection. |
| `tool_adapters.py` | Gemini evidence extraction adapter plus source video copy/download helpers. |
| `evidence_io.py` | Flat Evidence Bundle snapshot paths, source video state, and Gemini evidence files. |
| `evidence.py` | Snapshot-derived evidence outputs: audio baseline, claim review, quality, shootable angles, and reports. |
| `claim_safety.py` | Claim safety review rules and report writing. |
| `evidence_quality.py` | Evidence Quality Score and manual review flag logic. |
| `reports.py` | Per-video Video Evidence Report generation. |
| `outputs.py` | Internal structured summaries plus the Creative Production Report. |
| `creative_scripts.py` | Script-oriented helpers for approved creative follow-ups. |
| `planning_workbook.py` | Excel angle planning workbook generation. |
| `report_dates.py` | Report date and output folder helpers. |
| `run_manifest.py` | Run Manifest construction and batch index writing. |
| `shootable_angles.py` | Shootable Angle extraction and scoring helpers. |
| `telegram.py` | Optional Telegram delivery. |
| `cleanup.py` | Optional evidence artifact cleanup. |
| `run.py` | End-to-end daily evidence orchestration. |

New code should import from `batch_analysis/` instead of importing the CLI script. This keeps the CLI from growing and makes each workflow stage easier to test directly.

## Running Manually

**Daily discovery and Daily Top-3 handoff:**

```powershell
$runId = "nattome_$(Get-Date -Format yyyyMMddTHHmmss)"
$runDir = "data/daily_runs/$runId"
python skills/nattome-tiktok-candidate-discovery/scripts/scrape_tiktok.py `
  --output "$runDir/raw_scrape_top30.json" `
  --top 30 `
  --download-videos `
  --daily-selection-output "$runDir/daily_selection_top3.json"
```

**Daily evidence analysis for the same top videos:**

```powershell
python scripts/run_batch_analysis.py `
  --candidates data/daily_runs/<run_id>/daily_selection_top3.json `
  --backfill-candidates data/daily_runs/<run_id>/daily_backfill_candidates.json
```

Use the actual `$runId` created by the scrape command. The Daily Evidence Run preserves the Top-3 handoff order, analyzes those videos first, and analyzes up to two backfill candidates only when needed. The scraper refuses to overwrite existing JSON outputs unless `--overwrite` is passed, so normal runs should use a fresh run folder.

Completed daily runs write evidence-qualified marketer-facing deliverables to `outputs/reports/<YYYY-MM-DD>/`: `production_creative_report_<YYYY-MM-DD>.md` and `production_angle_planning_sheet_<YYYY-MM-DD>.xlsx`. If no candidate qualifies with at least one evidence-backed Shootable Angle, those production files are skipped. The Daily Top-3 Selection is the canonical evidence-analysis set; up to two backfill candidates are prepared separately, but they are not part of the canonical selection. The run folder remains the audit/debug record for manifests, per-video evidence reports, internal JSON, logs, and cleanup status.

Cloud publication is disabled by default. To publish a newly completed Daily Evidence Run to Supabase, set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`, then add `--publish-cloud` to the evidence-analysis command. The worker registers the run metadata plus raw scrape, Daily Top-3 Selection, final markdown report, structured JSON, spreadsheet workbook, and batch-analysis artifacts. If publication fails, the local Run Folder remains available and `logs/cloud_publication.json` records the failure instead of marking the cloud run complete.

Useful optional flags:

| Command | Flag | Purpose |
|---|---|---|
| `scrape_tiktok.py` | `--config <path>` | Use a scraper config other than `skills/nattome-tiktok-candidate-discovery/config.json`. |
| `scrape_tiktok.py` | `--scope all|hashtags|keywords|profiles` | Limit which discovery inputs are scraped. |
| `scrape_tiktok.py` | `--results-per-input <n>` | Override Apify `resultsPerPage`. |
| `scrape_tiktok.py` | `--daily-backfill-output <path>` | Override where the separate backfill candidate JSON is written. |
| `run_batch_analysis.py` | `--config <path>` | Merge extra runtime config into the evidence run. |
| `run_batch_analysis.py` | `--runs-dir <path>` | Change where timestamped Run Folders are created. |
| `run_batch_analysis.py` | `--outputs-dir <path>` | Change where final dated reports and workbooks are written. |
| `run_batch_analysis.py` | `--timestamp <ISO8601Z>` | Use a deterministic timestamp for tests or controlled reruns. |
| `run_batch_analysis.py` | `--publish-cloud` | Publish the completed run and artifact records to Supabase after local output generation succeeds. |

## Python Dashboard

Start the marketer-facing Scrape Quality Dashboard shell locally:

```powershell
python -m dashboard.web
```

On this workstation, use the project virtual environment directly if `python` resolves to the Windows Store shim:

```powershell
C:\Users\Alson\.venv\Scripts\python.exe -m dashboard.web
```

The app runs at `http://127.0.0.1:8765` by default and initializes its dashboard-owned SQLite state at `data/dashboard/dashboard.sqlite3`. Current navigation includes Overview, Report, Run History, Scrape Settings, and Pipeline Architecture. The dashboard can also serve static assets, health checks, CSV exports, scrape-setting saves/rollbacks, curation updates, and manual run triggers.

For hosted use, deploy this Python dashboard on a VPS or long-running app host where the process can keep durable access to `data/dashboard/dashboard.sqlite3`, `data/`, `runs/`, and `outputs/`. Put it behind a reverse proxy such as Caddy or Nginx with authentication. Do not deploy the operational dashboard to a serverless static app platform; the project no longer includes a separate web dashboard app.

Useful dashboard routes:

| Route | Purpose |
|---|---|
| `/` | Latest run overview and pipeline health summary. |
| `/report` | Marketer-facing report view. |
| `/run-history` | Indexed run history, curation state, and manual run context. |
| `/scrape-settings` | Versioned scrape settings. |
| `/pipeline-architecture` | Pipeline architecture browser. |
| `/exports/raw-videos.csv` | Filterable raw video CSV export. |
| `/exports/run-summaries.csv` | Run summary CSV export. |
| `/healthz` | Plain `ok` health check. |

Rebuild the dashboard's artifact-derived SQLite index from existing repo files:

```powershell
C:\Users\Alson\.venv\Scripts\python.exe -c "from dashboard.indexer import index_pipeline_artifacts; print(index_pipeline_artifacts())"
```

## Running On a Schedule

Use the GitHub Actions Daily Evidence Run workflow for cloud publication. It runs at `01:00 UTC`, which is `09:00 Asia/Singapore`, and can also be started manually from the GitHub Actions UI. The workflow runs discovery, creates a Daily Top-3 Selection, runs daily evidence analysis with `--publish-cloud`, and writes final output paths plus `logs/cloud_publication.json` status to the workflow summary.

For the full Cloud Operations guide, including Supabase publication behavior, the new-runs-only cloud v1 policy, local backup expectations, and deferred control-room scope, see `docs/cloud-operations.md`.

Required GitHub Actions secrets:

| Secret | Required for | Notes |
|---|---|---|
| `APIFY_TOKEN` | Discovery | Required for scheduled and manual workflow runs. |
| `GEMINI_API_KEY` | Evidence analysis | Required for source-video evidence extraction. |
| `SUPABASE_URL` | Cloud publication | Required for `--publish-cloud`. |
| `SUPABASE_SERVICE_ROLE_KEY` | Cloud publication | Required for `--publish-cloud`; never print this value. |
| `TELEGRAM_BOT_TOKEN` | Optional delivery | Used only when Telegram delivery is configured. |
| `TELEGRAM_CHAT_ID` | Optional delivery | Used only when Telegram delivery is configured. |

The workflow checks required secret names before running and does not print secret values. It does not commit generated artifacts back to the repository; raw scrapes, Run Folders, reports, workbooks, and logs live only in the workflow runner and in Supabase publication records.

Manual verification for this HITL slice: run **Daily Evidence Run Cloud Publisher** from GitHub Actions after configuring the required secrets, then confirm the summary shows a Run Folder, `final_outputs`, and cloud publication status `published`.

## Key Reading Order For New Contributors

1. `CONTEXT.md` - what every domain term means.
2. `docs/prd/gemini-two-layer-evidence-pipeline-architecture-prd.md` - current Gemini/two-layer architecture.
3. `skills/nattome-viral-intelligence-run/SKILL.md` - primary daily automation workflow.
4. `skills/nattome-tiktok-candidate-discovery/SKILL.md` - supporting phase 1 workflow.
5. `skills/nattome-evidence-insight-analysis/SKILL.md` - supporting phase 2 workflow.
6. `skills/nattome-tiktok-candidate-discovery/references/nattome_brand.md` - voice and claim guardrails.
7. `skills/nattome-tiktok-candidate-discovery/references/virality_framework.md` - analysis lens.
8. `progress.txt` - chronological implementation record.

## Tests

The project currently uses Python 3.10+ and only the standard library plus local modules.

```powershell
python -m unittest discover -s tests
```

On this workstation, use the project virtual environment directly if `python` resolves to the Windows Store shim:

```powershell
C:\Users\Alson\.venv\Scripts\python.exe -m unittest discover -s tests
```
