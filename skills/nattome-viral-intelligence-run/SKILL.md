---
name: nattome-viral-intelligence-run
description: End-to-end Nattome TikTok viral intelligence pipeline. Runs `nattome-tiktok-candidate-discovery` first to scrape, rank, and preserve evidence-ready viral candidates, then runs `nattome-evidence-insight-analysis` to turn selected videos into actionable Nattome insights, evidence-backed Shootable Angles, Claim Safety Reviews, Evidence Quality Scores, Nattome Priority Scores, final reports, and planning workbooks. Use this skill for recurring automations, daily or weekly TikTok scraping plus evidence analysis, viral content research, "scrape TikTok and give actionable insights", "run the Nattome pipeline", or any request to find viral TikTok content and turn it into production-ready Nattome content ideas. Do not split discovery and evidence into separate automations unless the user explicitly asks for discovery-only or evidence-only work.
user-invocable: true
---

# Nattome Viral Intelligence Run

You are running the end-to-end Nattome TikTok viral intelligence pipeline. Discovery and evidence analysis are two phases of one workflow:

1. `nattome-tiktok-candidate-discovery` creates the evidence-ready candidate data.
2. `nattome-evidence-insight-analysis` turns those discovered videos into actionable, evidence-backed Nattome insight.

Do not treat the two phase skills as alternatives. For automations, run both phases together unless the user explicitly asks for a discovery-only scrape or evidence-only rerun on an existing candidate file.

## Pre-Flight

Read these files before producing output:

- `CONTEXT.md`
- `skills/nattome-tiktok-candidate-discovery/references/nattome_brand.md`
- `skills/nattome-tiktok-candidate-discovery/references/virality_framework.md`
- `skills/nattome-tiktok-candidate-discovery/SKILL.md`
- `skills/nattome-evidence-insight-analysis/SKILL.md`

Check required credentials:

- `APIFY_TOKEN` is required for discovery.
- `GEMINI_API_KEY` is required for evidence insight analysis.
- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are optional. Skip Telegram silently if either is missing.

Credential sources:

- Treat the project root `.env` file as a valid credential source as well as already-exported shell variables.
- Before declaring credentials missing, load/check `.env` without printing secret values. The bundled CLIs load nearest `.env` files without overriding already-exported environment variables.

If `APIFY_TOKEN` or `GEMINI_API_KEY` is missing, stop and report the missing requirement. Do not fabricate TikTok discoveries or Gemini evidence.

## Default End-To-End Run

From the project root, create a fresh evidence-ready discovery scrape and daily top-5 handoff:

```powershell
python skills/nattome-tiktok-candidate-discovery/scripts/scrape_tiktok.py `
  --output data/raw_scrapes/nattome_raw_$(Get-Date -Format yyyyMMdd)_top30.json `
  --top 30 `
  --download-videos `
  --daily-selection-output data/daily_selections/nattome_daily_$(Get-Date -Format yyyyMMdd)_top5.json
```

Then run Gemini evidence insight analysis on the same daily-selected videos:

```powershell
python scripts/run_batch_analysis.py `
  --mode daily `
  --candidates data/daily_selections/nattome_daily_<YYYYMMDD>_top5.json
```

Use the actual local date for `<YYYYMMDD>`. Preserve UTF-8 reads and writes for JSON, Markdown, manifests, logs, and workbook-adjacent structured data.

## Weekly Deep Run Variant

If the user asks for a weekly batch, strategic deep dive, or broader pattern read, still run discovery first, then run evidence insight analysis on the top-30 candidate file:

```powershell
python scripts/run_batch_analysis.py `
  --mode default `
  --candidates data/raw_scrapes/nattome_raw_<YYYYMMDD>_top30.json
```

Use `--mode deep` only when explicitly requested.

## Reporting

After the run, return a concise summary with:

- Raw scrape path.
- Daily selection or selected candidates path.
- Final report path under `outputs/reports/YYYY-MM-DD/`.
- Excel planning workbook path.
- Run Folder path under `runs/batch-analysis/`.
- Evidence completion status, preserving `completed`, `partial`, `missing_credentials`, `missing`, and `failed` exactly.
- Top patterns and top 3 Shootable Angles with Nattome Priority Scores out of 30.
- Claim Safety Review risks.
- Manual Review Flags from Evidence Quality outputs.
- Failed downloads, missing `video_download_url`, or low-quality evidence warnings.
- Telegram delivery status only if Telegram was configured.

## Honest Reporting Rules

- Never invent visible text, spoken content, visual observations, audio cues, hook evidence, claim evidence, source video availability, or download success.
- Do not call an angle shootable unless Gemini source-video evidence supports the hook, structure, pacing, and emotional-trigger read.
- Do not override Claim Safety Review findings.
- A high-view video with weak engagement is not automatically a viral success; call out paid-push or bait signals when evidence suggests them.
