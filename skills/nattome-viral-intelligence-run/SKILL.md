---
name: nattome-viral-intelligence-run
description: Primary normal-operation skill for the Nattome Daily Evidence Run. Scrapes TikTok candidates, creates the Daily Top-3 Selection handoff, runs Gemini evidence analysis on those same three videos, and reports the final evidence-backed Nattome outputs. Use this for recurring automations, "run the Nattome pipeline", "run today's TikTok analysis", "scrape TikTok and give actionable insights", or any request to find viral TikToks and turn them into production-ready Nattome content ideas. Do not split discovery and evidence analysis unless the user explicitly asks for discovery-only or evidence-only debugging.
---

# Nattome Daily Evidence Run

This is the only normal-operation skill for the Nattome TikTok pipeline.

The Daily Evidence Run has two phases:

1. `nattome-tiktok-candidate-discovery` creates the evidence-ready Daily Top-3 Selection handoff.
2. `nattome-evidence-insight-analysis` analyzes the Daily Top-3 first, then analyzes up to two backfill candidates only when needed, and produces evidence-qualified Nattome outputs.

The phase skills are supporting references, not normal entry points.

## Read First

- `CONTEXT.md`
- `skills/nattome-tiktok-candidate-discovery/references/nattome_brand.md`
- `skills/nattome-tiktok-candidate-discovery/references/virality_framework.md`
- `skills/nattome-tiktok-candidate-discovery/SKILL.md`
- `skills/nattome-evidence-insight-analysis/SKILL.md`

Keep brand voice, avatars, claim guardrails, and virality taxonomy in the reference files. Do not duplicate them here.

## Pre-Flight

Required:

- `APIFY_TOKEN` for TikTok discovery.
- `GEMINI_API_KEY` for source-video evidence analysis.

Optional:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Treat the project root `.env` as a valid credential source, alongside already-exported environment variables. Check for credentials without printing secret values. If `APIFY_TOKEN` or `GEMINI_API_KEY` is missing, stop and report the missing requirement. Do not fabricate TikTok discoveries or Gemini evidence.

## Daily Run

From the project root, create the raw top-30 scrape and Daily Top-3 Selection handoff:

```powershell
$runId = "nattome_$(Get-Date -Format yyyyMMddTHHmmss)"
$runDir = "data/daily_runs/$runId"
python skills/nattome-tiktok-candidate-discovery/scripts/scrape_tiktok.py `
  --output "$runDir/raw_scrape_top30.json" `
  --top 30 `
  --download-videos `
  --daily-selection-output "$runDir/daily_selection_top3.json"
```

Then analyze the same daily-selected videos:

```powershell
python scripts/run_batch_analysis.py `
  --candidates data/daily_runs/<run_id>/daily_selection_top3.json `
  --backfill-candidates data/daily_runs/<run_id>/daily_backfill_candidates.json
```

Use the actual `$runId` generated for the scrape command. Preserve UTF-8 reads and writes for JSON, Markdown, manifests, logs, and workbook-adjacent structured data.

## Primary Outputs

After a successful run, report these paths:

- Raw scrape: `data/daily_runs/<run_id>/raw_scrape_top30.json`
- Daily Top-3 Selection handoff: `data/daily_runs/<run_id>/daily_selection_top3.json`
- Daily backfill candidates: `data/daily_runs/<run_id>/daily_backfill_candidates.json`
- Final report: `outputs/reports/<YYYY-MM-DD>/production_creative_report_<YYYY-MM-DD>.md`
- Planning workbook: `outputs/reports/<YYYY-MM-DD>/production_angle_planning_sheet_<YYYY-MM-DD>.xlsx`
- Audit/debug Run Folder: `runs/batch-analysis/<timestamp>_daily/`

The markdown discovery brief under `outputs/daily_briefs/` is optional supporting output. Do not treat it as the final production report.

## Reporting Checklist

Return a concise summary with:

- Evidence completion status, preserving `completed`, `partial`, `missing_credentials`, `missing`, and `failed` exactly.
- Top patterns and top 3 evidence-backed Shootable Angles with Nattome Priority Scores out of 30.
- Claim Safety Review risks.
- Manual Review Flags from Evidence Quality outputs.
- Failed downloads, missing `video_download_url`, or low-quality evidence warnings.
- Production output status, including when no candidate qualified and no production report/workbook was created.
- Telegram delivery status only if Telegram was configured.

## Honest Reporting Rules

- Never invent visible text, spoken content, visual observations, audio cues, hook evidence, claim evidence, source video availability, or download success.
- Do not call an idea a Shootable Angle unless Gemini source-video evidence supports the hook, structure, pacing, and emotional-trigger read.
- Do not include candidates without at least one evidence-backed Shootable Angle in the final production report or workbook.
- Before Gemini evidence exists, only discuss candidate previews and metadata inferences.
- Do not override Claim Safety Review findings.
- A high-view video with weak engagement is not automatically a viral success; call out paid-push or bait signals when evidence suggests them.
