# Nattome TikTok Content Discovery Pipeline

Two-tier content intelligence pipeline for **Nattome** (Atomic Group's flagship digestive-health brand for Malaysians). Discovers viral TikToks, analyzes why they work, and generates Nattome-shootable angles — daily for ideation, weekly for evidence-backed strategic research.

## What This Project Is

| Cadence | Skill | Output | Runtime |
|---|---|---|---|
| **Daily** | `nattome-daily-discovery` | `outputs/daily_briefs/daily_brief_<date>.md` (top 5 viral videos + 3 Nattome angles each) | 3–8 min |
| **Weekly** | `nattome-batch-analysis` | `runs/batch-analysis/<ts>_default/` — per-video Video Evidence Reports, Cross-Video Pattern Summary, JSON, CSV | 15–30 min |

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
├── scripts/
│   └── run_batch_analysis.py      ← core batch CLI (called by the batch skill)
├── tests/                         ← unit tests for the batch CLI
├── docs/
│   ├── prd/                       ← full product spec
│   ├── adr/                       ← architecture decisions
│   └── issues/{,done/}            ← implementation tickets
├── data/raw_scrapes/              ← raw Apify TikTok scrapes (input to batch run)
├── outputs/daily_briefs/          ← daily brief deliverables
└── runs/batch-analysis/           ← timestamped weekly run folders
```

## Environment Variables

| Variable | Required for | Notes |
|---|---|---|
| `APIFY_TOKEN` | Both skills | Apify API token. Without it, no scraping. |
| `TELEGRAM_BOT_TOKEN` | Optional | Telegram bot token. Skip silently if unset. |
| `TELEGRAM_CHAT_ID` | Optional | Target chat. Both must be set together. |

External tools used by the weekly batch analysis (must be on `PATH` or passed via CLI flags): `ffmpeg`, `paddleocr` (or `tesseract` fallback), `whisper`.

## Running Manually

**Daily discovery brief:**

```powershell
python skills/nattome-daily-discovery/scripts/scrape_tiktok.py `
  --output data/raw_scrapes/nattome_raw_$(Get-Date -Format yyyyMMdd).json
```

Then ask Claude Code: *"Run the Nattome daily TikTok discovery brief for today."* — the skill picks up the JSON, analyzes the top 5, and writes the brief.

**Weekly batch evidence analysis:**

```powershell
python scripts/run_batch_analysis.py `
  --mode default `
  --candidates data/raw_scrapes/nattome_raw_<YYYYMMDD>_top30.json
```

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
2. `docs/prd/nattome-tiktok-ocr-video-evidence-pipeline-prd.md` — the full spec
3. `skills/nattome-daily-discovery/SKILL.md` — daily workflow
4. `skills/nattome-batch-analysis/SKILL.md` — weekly workflow
5. `skills/nattome-daily-discovery/references/nattome_brand.md` — voice + claim guardrails (shared)
6. `skills/nattome-daily-discovery/references/virality_framework.md` — analysis lens (shared)
7. `progress.txt` — chronological record of every implementation slice

## Tests

```powershell
python -m unittest discover -s tests
```
