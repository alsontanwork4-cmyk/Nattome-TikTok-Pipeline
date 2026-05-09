---
name: nattome-evidence-insight-analysis
description: Supporting reference skill for Phase 2 of the Nattome Daily Evidence Run. Use directly only for evidence-only reruns, debugging an existing daily candidate JSON, inspecting Gemini evidence outputs, or explaining `scripts/run_batch_analysis.py --mode daily`. Normal operation should use `nattome-viral-intelligence-run`.
user-invocable: false
---

# Nattome Evidence Insight Analysis

This is a supporting phase reference. It analyzes an existing Daily Top-5 Selection handoff and produces evidence-backed Nattome outputs. Normal users should trigger `nattome-viral-intelligence-run` instead.

## Role

Phase 2 turns downloaded TikTok candidates into evidence-first strategic research. Every claim about why a video worked must be backed by source-video evidence captured by Gemini 2.5 Flash, not metadata guesswork.

## Read First

- `CONTEXT.md`
- `skills/nattome-tiktok-candidate-discovery/references/nattome_brand.md`
- `skills/nattome-tiktok-candidate-discovery/references/virality_framework.md`

## Current Architecture

- Gemini 2.5 Flash is the evidence extraction adapter.
- FFmpeg, local OCR binaries, Tesseract fallback, and Whisper-style executables are not part of the current run path.
- Per-video files are flat and prefixed by rank and candidate ID, for example `001_video-id_gemini_evidence.json`.
- The Run Manifest is the source of truth for phase status and generated outputs.

## Pre-Flight

Required:

- Existing Daily Top-5 Selection JSON, normally `data/daily_runs/<run_id>/daily_selection_top5.json`.
- `GEMINI_API_KEY` in the environment or project root `.env`.
- Downloadable video sources in candidate rows. Missing `video_download_url` means the candidate is not evidence-ready.

Optional:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

`APIFY_TOKEN` is needed only when fresh discovery must run first.

## Daily Evidence Command

From the project root:

```powershell
python scripts/run_batch_analysis.py `
  --mode daily `
  --candidates data/daily_runs/<run_id>/daily_selection_top5.json
```

Daily mode preserves the discovery handoff order and analyzes only the daily-selected videos that pass the Minimum Eligibility Filter.

Optional flags:

- `--config <path>` - merge extra JSON config into runtime configuration.
- `--runs-dir <path>` - change the runs root; default is `runs/batch-analysis`.
- `--timestamp <ISO8601Z>` - deterministic timestamp for tests.

Do not pass retired local-tool flags such as `--ffmpeg-bin`, `--ocr-primary-bin`, `--ocr-fallback-bin`, or `--transcription-bin`.

## Outputs

Primary marketer-facing outputs:

- `outputs/reports/<YYYY-MM-DD>/top5_creative_production_report_<YYYY-MM-DD>.md`
- `outputs/reports/<YYYY-MM-DD>/top5_angle_planning_sheet_<YYYY-MM-DD>.xlsx`

Audit/debug Run Folder:

- `runs/batch-analysis/<timestamp>_daily/`
- `run_manifest.json`
- `run_metadata.json`
- `batch_index.md`
- `reports/selected_batch.md`
- `reports/<rank>_<video-id>_video_evidence_report.md`
- `data/selected_batch.json`
- `data/evidence_bundle_index.json`
- `data/<rank>_<video-id>_gemini_evidence.json`
- `data/<rank>_<video-id>_baseline_audio_analysis.json`
- `data/<rank>_<video-id>_claim_safety_review.json`
- `data/<rank>_<video-id>_evidence_quality.json`
- `data/<rank>_<video-id>_shootable_angles.json`
- `data/cross_video_pattern_summary.json`
- `data/structured_batch_analysis.json`
- `evidence/<rank>_<video-id>_source_video.<ext>`
- `logs/telegram_delivery.json` when Telegram is configured.

## After The Run

1. Read the Top 5 Creative Production Report.
2. Confirm the Excel planning workbook exists.
3. Inspect per-video reports when source evidence detail is needed.
4. Quote the top 3 available Shootable Angles with Nattome Priority Scores out of 30.
5. Surface Manual Review Flags from `data/*_evidence_quality.json`.
6. Surface Claim Safety Review findings from `data/*_claim_safety_review.json`.
7. Report Gemini evidence status exactly.

## Honest Reporting Rules

- Never invent visible text, spoken content, visual observations, audio cues, hook evidence, claim evidence, source video availability, or download success.
- Gemini evidence can be `completed`, `partial`, `missing_credentials`, `missing`, or `failed`. Preserve that status exactly.
- If Evidence Quality Score is medium or low, surface the Manual Review Flag.
- Do not generate or endorse Shootable Angles that depend on missing Gemini evidence without flagging the uncertainty.
- Do not override Claim Safety Review findings.
- A high-view video with weak engagement is not automatically a viral success. Say when the evidence suggests paid push or bait.
