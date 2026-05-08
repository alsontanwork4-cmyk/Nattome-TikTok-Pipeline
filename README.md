# Nattome TikTok Content Discovery Pipeline

Daily viral intelligence pipeline for **Nattome** (Atomic Group's flagship digestive-health brand for Malaysians). It discovers viral TikToks, preserves evidence-ready candidates, analyzes source videos with Gemini, and generates evidence-backed Nattome Shootable Angles.

Discovery creates the data. Evidence analysis turns that data into actionable insight.

## What This Project Is

| Use case | Skill | Purpose / artifact | Runtime |
|---|---|---|---|
| **Normal daily run** | `nattome-viral-intelligence-run` | Runs discovery, creates the daily top-5 handoff, runs Gemini evidence analysis, and reports final paths and evidence status. | 20-40 min |
| **Discovery-only debugging** | `nattome-tiktok-candidate-discovery` | Supporting phase reference for scraper config and top-5 candidate handoff creation. | 3-8 min |
| **Evidence-only debugging** | `nattome-evidence-insight-analysis` | Supporting phase reference for rerunning `--mode daily` on an existing candidate JSON. | 15-30 min |

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
├── tests/
├── docs/
│   ├── prd/
│   ├── adr/
│   └── issues/{,done/}
├── data/raw_scrapes/              <- raw Apify TikTok scrapes
├── data/daily_selections/         <- daily top-5 handoffs
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
| `outputs.py` | Internal structured summaries plus the Top 5 Creative Production Report. |
| `planning_workbook.py` | Excel angle planning workbook generation. |
| `telegram.py` | Optional Telegram delivery. |
| `cleanup.py` | Optional evidence artifact cleanup. |
| `run.py` | End-to-end daily evidence orchestration. |

New code should import from `batch_analysis/` instead of importing the CLI script. This keeps the CLI from growing and makes each workflow stage easier to test directly.

## Running Manually

**Daily discovery and top-5 handoff:**

```powershell
python skills/nattome-tiktok-candidate-discovery/scripts/scrape_tiktok.py `
  --output data/raw_scrapes/nattome_raw_$(Get-Date -Format yyyyMMdd)_top30.json `
  --top 30 `
  --download-videos `
  --daily-selection-output data/daily_selections/nattome_daily_$(Get-Date -Format yyyyMMdd)_top5.json
```

**Daily evidence analysis for the same top videos:**

```powershell
python scripts/run_batch_analysis.py `
  --mode daily `
  --candidates data/daily_selections/nattome_daily_<YYYYMMDD>_top5.json
```

`daily` mode preserves the handoff order and analyzes only the daily-selected videos that pass the Minimum Eligibility Filter.

Completed daily runs write the final marketer-facing deliverables to `outputs/reports/<YYYY-MM-DD>/`: the Top 5 Creative Production Report Markdown file and the Excel angle planning workbook. The run folder remains the audit/debug record for manifests, per-video evidence reports, internal JSON, logs, and cleanup status.

## Local Dashboard

Start the marketer-facing Scrape Quality Dashboard shell locally:

```powershell
C:\Users\Alson\.venv\Scripts\python.exe -m dashboard.web
```

The app runs at `http://127.0.0.1:8765` by default and initializes its dashboard-owned SQLite state at `data/dashboard/dashboard.sqlite3`. The initial shell includes navigation for Overview, Scraped Content, Run History, Scrape Settings, Nattome POV Library, and Pipeline Architecture. The Overview route loads without Apify, Gemini, or existing run artifacts.

Rebuild the dashboard's artifact-derived SQLite index from existing repo files:

```powershell
C:\Users\Alson\.venv\Scripts\python.exe -c "from dashboard.indexer import index_pipeline_artifacts; print(index_pipeline_artifacts())"
```

## Running On a Schedule

Use one scheduled prompt for the normal pipeline. The prompt wording should trigger `nattome-viral-intelligence-run` so discovery and evidence run together.

| Cadence | Prompt | Matches skill |
|---|---|---|
| Daily 09:00 local | "Run the end-to-end Nattome TikTok viral intelligence pipeline for today." | `nattome-viral-intelligence-run` |

Manage schedules via the automation tool available in your runner.

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

```powershell
python -m unittest discover -s tests
```

On this workstation, use the project virtual environment directly if `python` resolves to the Windows Store shim:

```powershell
C:\Users\Alson\.venv\Scripts\python.exe -m unittest discover -s tests
```
