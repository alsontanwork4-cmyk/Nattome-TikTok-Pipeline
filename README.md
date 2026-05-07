# Nattome TikTok Content Discovery Pipeline

Two-tier content intelligence pipeline for **Nattome** (Atomic Group's flagship digestive-health brand for Malaysians). Discovers viral TikToks, analyzes why they work, and generates Nattome-shootable angles — daily for ideation, weekly for evidence-backed strategic research.

## What This Project Is

| Cadence | Skill | Purpose / artifact | Runtime |
|---|---|---|---|
| **Daily** | `nattome-daily-discovery` | Discovery and ideation handoff: `outputs/daily_briefs/daily_brief_<date>.md` plus `data/daily_selections/nattome_daily_<date>_top5.json` | 3–8 min |
| **Weekly** | `nattome-batch-analysis` | Final production deliverables: `outputs/reports/<date>/top5_creative_production_report_<date>.md` + `top5_angle_planning_sheet_<date>.xlsx` | 15–30 min |

Both skills live under `skills/` and are loaded automatically by Claude Code via `.claude/settings.json`.

## Folder Layout

```
.
├── README.md                      ← you are here
├── CONTEXT.md                     ← terminology dictionary (read first)
├── progress.txt                   ← chronological execution log
├── .claude/settings.json          ← registers skills/ as a skill directory
├── skills/
│   ├── nattome-daily-discovery/   ← daily ideation skill (with scrape + Telegram scripts)
│   └── nattome-batch-analysis/    ← weekly evidence-first analysis skill
├── batch_analysis/                ← importable weekly batch analysis package
├── scripts/
│   └── run_batch_analysis.py      ← thin compatibility CLI (called by the batch skill)
├── tests/                         ← unit tests for extracted modules + CLI behavior
├── docs/
│   ├── prd/                       ← full product spec
│   ├── adr/                       ← architecture decisions
│   └── issues/{,done/}            ← implementation tickets
├── data/raw_scrapes/              ← raw Apify TikTok scrapes (input to batch run)
├── outputs/daily_briefs/          ← daily discovery and ideation handoffs
├── outputs/reports/               ← final production report + Excel workbook deliverables
└── runs/batch-analysis/           ← timestamped weekly run folders
```

## Environment Variables

| Variable | Required for | Notes |
|---|---|---|
| `APIFY_TOKEN` | Both skills | Apify API token. Without it, no scraping. |
| `GEMINI_API_KEY` | Weekly batch analysis | Gemini key used for source-video evidence extraction. |
| `TELEGRAM_BOT_TOKEN` | Optional | Telegram bot token. Skip silently if unset. |
| `TELEGRAM_CHAT_ID` | Optional | Target chat. Both must be set together. |

The weekly batch analysis no longer shells out to local video/OCR/transcription tools. Gemini analyzes the source video and returns timestamped visual, visible-text, spoken-content, audio, hook, and claim evidence.

## Weekly Batch Architecture

The weekly batch pipeline keeps `scripts/run_batch_analysis.py` as the stable CLI interface. It should stay thin: parse flags, call `batch_analysis.run.create_run`, and return the process exit code. Existing prompts, schedules, and shell commands can keep using the same script path and flags.

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
| `run.py` | End-to-end weekly batch orchestration. |

New code should import from `batch_analysis/` instead of importing the CLI script. This keeps the CLI from bloating again and makes each workflow stage easier to test directly.

## Running Manually

**Daily discovery brief:**

```powershell
python skills/nattome-daily-discovery/scripts/scrape_tiktok.py `
  --output data/raw_scrapes/nattome_raw_$(Get-Date -Format yyyyMMdd)_top30.json `
  --top 30 `
  --download-videos `
  --daily-selection-output data/daily_selections/nattome_daily_$(Get-Date -Format yyyyMMdd)_top5.json
```

Then ask Claude Code: *"Run the Nattome daily TikTok discovery brief for today."* — the skill picks up the JSON, analyzes the top 5, and writes the brief.

**Daily evidence analysis for the same top videos:**

```powershell
python scripts/run_batch_analysis.py `
  --mode daily `
  --candidates data/daily_selections/nattome_daily_<YYYYMMDD>_top5.json
```

`daily` mode preserves the handoff order and analyzes only the daily-selected videos instead of reranking the top-30 scrape into the 10-video weekly batch.

**Weekly batch evidence analysis:**

```powershell
python scripts/run_batch_analysis.py `
  --mode default `
  --candidates data/raw_scrapes/nattome_raw_<YYYYMMDD>_top30.json
```

The CLI interface is preserved for compatibility. Use it from Codex, Claude Code, schedules, or PowerShell exactly as before.

Completed weekly runs write the final marketer-facing deliverables to `outputs/reports/<YYYY-MM-DD>/`: the Top 5 Creative Production Report Markdown file and the Excel angle planning workbook. The run folder remains the audit/debug record for manifests, per-video evidence reports, internal JSON, logs, and cleanup status.

Or ask Claude Code: *"Run the Nattome weekly batch evidence analysis on this week's top candidates."*

## Running On a Schedule

The two skills are wired to run via the `anthropic-skills:schedule` skill. Each schedule entry is just a prompt — the prompt's wording triggers the matching skill via its `description:` field.

| Cadence | Prompt | Matches skill |
|---|---|---|
| Daily 09:00 local | "Run the Nattome daily TikTok discovery brief for today." | `nattome-daily-discovery` |
| Weekly Mon 08:00 local | "Run the Nattome weekly batch evidence analysis on this week's top candidates." | `nattome-batch-analysis` |

Manage these via `/anthropic-skills:schedule` (create / list / update / run).

## Key Reading Order For New Contributors

1. `CONTEXT.md` — what every domain term means
2. `docs/prd/gemini-two-layer-evidence-pipeline-architecture-prd.md` — current Gemini/two-layer architecture
3. `skills/nattome-daily-discovery/SKILL.md` — daily workflow
4. `skills/nattome-batch-analysis/SKILL.md` — weekly workflow
5. `skills/nattome-daily-discovery/references/nattome_brand.md` — voice + claim guardrails (shared)
6. `skills/nattome-daily-discovery/references/virality_framework.md` — analysis lens (shared)
7. `progress.txt` — chronological record of every implementation slice

## Tests

```powershell
python -m unittest discover -s tests
```

On this workstation, use the project virtual environment directly if `python` resolves to the Windows Store shim:

```powershell
C:\Users\Alson\.venv\Scripts\python.exe -m unittest discover -s tests
```
