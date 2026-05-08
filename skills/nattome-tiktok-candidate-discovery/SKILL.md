---
name: nattome-tiktok-candidate-discovery
description: Supporting reference skill for Phase 1 of the Nattome Daily Evidence Run. Use directly only for discovery-only debugging, scraper configuration, or creating a fresh daily top-5 candidate handoff without running Gemini evidence analysis. Normal operation should use `nattome-viral-intelligence-run`.
user-invocable: false
---

# Nattome TikTok Candidate Discovery

This is a supporting phase reference. It owns the scraper command, scraper config, discovery assets, and candidate preview rules. Normal users should trigger `nattome-viral-intelligence-run` instead.

## Role

Phase 1 finds evidence-ready TikTok candidates and writes the daily top-5 handoff for Gemini analysis.

Discovery may produce candidate previews, but it must not produce production-ready Shootable Angles. Before Gemini evidence exists, all content reads are metadata inferences.

## Read First

- `CONTEXT.md`
- `references/nattome_brand.md`
- `references/virality_framework.md`

Brand voice, avatars, claim rules, and virality taxonomy live in those files. Do not duplicate or override them here.

## Pre-Flight

Required:

- `APIFY_TOKEN`

Treat the project root `.env` as a valid credential source. Check without printing token values. If `APIFY_TOKEN` is missing, stop and report it. Do not fabricate TikTok results.

## Discovery Command

From the project root:

```powershell
$runId = "nattome_$(Get-Date -Format yyyyMMddTHHmmss)"
$runDir = "data/daily_runs/$runId"
python skills/nattome-tiktok-candidate-discovery/scripts/scrape_tiktok.py `
  --output "$runDir/raw_scrape_top30.json" `
  --top 30 `
  --download-videos `
  --daily-selection-output "$runDir/daily_selection_top5.json"
```

Outputs:

- Full ranked scrape: `data/daily_runs/<run_id>/raw_scrape_top30.json`
- Daily evidence handoff: `data/daily_runs/<run_id>/daily_selection_top5.json`
- Optional discovery markdown: `outputs/daily_briefs/daily_brief_<YYYY-MM-DD>.md`

Keep JSON, Markdown, config, and brief files in UTF-8.
The scraper refuses to overwrite existing JSON outputs unless `--overwrite` is passed, so normal runs must use a fresh run folder.

## Candidate Preview Rules

For each top-5 candidate, previews may include:

- Topic.
- Metadata signals from caption, hashtags, author, engagement, recency, and URL.
- Likely hook direction, clearly labeled as inference.
- Likely structure, clearly labeled as inference.
- Likely emotional trigger, clearly labeled as inference.
- Why the video may have won, based only on available metadata and engagement signals.

Do not claim exact visible text, spoken content, pacing, scene changes, audio cues, or hook execution until Gemini evidence analysis has run.

## No Production Angles Before Gemini

Before Gemini:

- Say `candidate preview`, `likely hook direction`, and `metadata inference`.
- Do not say `Shootable Angle`, `Nattome Priority Score`, or `production-ready`.

After Gemini evidence exists, use `nattome-evidence-insight-analysis` or the main `nattome-viral-intelligence-run` reporting rules.

## Owned Files

- `scripts/scrape_tiktok.py` - Apify TikTok scraper.
- `scripts/telegram_send.py` - optional Telegram sender for markdown briefs.
- `config.json` - active discovery config.
- `assets/config.example.json` - example config.
- `assets/daily_brief_template.md` - optional discovery brief template.
- `references/nattome_brand.md` - brand voice and claim guardrails.
- `references/virality_framework.md` - virality analysis lens.
