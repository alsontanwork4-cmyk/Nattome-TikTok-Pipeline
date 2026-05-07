---
name: nattome-evidence-insight-analysis
description: Phase 2 of the Nattome viral intelligence pipeline. Consumes candidate JSON from `nattome-tiktok-candidate-discovery`, preserves source videos as Evidence Artifacts, uses Gemini 2.5 Flash to extract timestamped visual, visible-text, spoken-content, audio, hook, and claim evidence, then generates Video Evidence Reports, Claim Safety Reviews, Evidence Quality Scores, evidence-backed Shootable Angles, structured JSON, a Top 5 Creative Production Report, an Excel angle planning workbook, Run Manifest, and optional Telegram delivery. If no fresh evidence-ready candidate file exists, run candidate discovery first. For recurring automations or end-to-end discovery plus evidence analysis, prefer `nattome-viral-intelligence-run`. Use this phase when the user asks for evidence analysis, production-ready shootable angles, claim safety, batch analysis, daily evidence analysis, or invokes `run_batch_analysis.py`.
user-invocable: true
---

# Nattome TikTok Evidence Insight Analysis

You are running Phase 2 of Nattome's viral intelligence pipeline. The deliverable is **evidence-first strategic research**: every claim about why a video worked must be backed by source-video evidence captured by Gemini 2.5 Flash, not metadata guesswork.

Read `CONTEXT.md` at the project root before producing reports. It is the terminology dictionary for **Video Evidence Report**, **Evidence Bundle**, **Run Folder**, **Top 5 Creative Production Report**, **Evidence Quality Score**, **Claim Safety Review**, **Shootable Angle**, and **Nattome Priority Score**.

This skill is normally run after `nattome-tiktok-candidate-discovery`. Discovery creates the evidence-ready candidate data; evidence insight analysis turns those discovered videos into actionable, evidence-backed Nattome insights. For automations, use `nattome-viral-intelligence-run` so discovery and evidence analysis run together unless the user explicitly asks for discovery-only or evidence-only work.

## Current Architecture

The pipeline now uses the Gemini two-layer Evidence Bundle layout:

- Gemini 2.5 Flash is the evidence extraction adapter.
- FFmpeg, local OCR binaries, Tesseract fallback, and Whisper-style executables are not part of the current run path.
- New runs do not write nested `evidence_bundles/` or `batch_outputs/` folders.
- Per-video files are flat and prefixed by rank and candidate ID, for example `001_video-id_gemini_evidence.json`.
- The Run Manifest is the source of truth for phase status and generated outputs.

## What This Pipeline Produces

For one completed Batch Analysis Run, the marketer-facing final deliverables are:

- `outputs/reports/YYYY-MM-DD/top5_creative_production_report_YYYY-MM-DD.md`
- `outputs/reports/YYYY-MM-DD/top5_angle_planning_sheet_YYYY-MM-DD.xlsx`

The Run Folder, `runs/batch-analysis/<timestamp>_<mode>/`, remains the audit and debug record:

- `reports/selected_batch.md`
- `reports/<rank>_<video-id>_video_evidence_report.md`
- `data/selected_batch.json`
- `data/evidence_bundle_index.json`
- `data/<rank>_<video-id>_source_metadata.json`
- `data/<rank>_<video-id>_evidence_snapshot.json`
- `data/<rank>_<video-id>_gemini_evidence.json`
- `data/<rank>_<video-id>_baseline_audio_analysis.json`
- `data/<rank>_<video-id>_claim_safety_review.json`
- `data/<rank>_<video-id>_evidence_quality.json`
- `data/<rank>_<video-id>_shootable_angles.json`
- `data/cross_video_pattern_summary.json`
- `data/structured_batch_analysis.json`
- `evidence/<rank>_<video-id>_source_video.<ext>`
- `logs/telegram_delivery.json`
- `logs/evidence_artifact_cleanup.json`
- `data/refinement_hooks.json`
- `run_metadata.json`
- `run_manifest.json`
- `batch_index.md`

A typical default run takes 15-30 minutes depending on source video availability and Gemini response time.

## Pre-Flight Checks

Before launching the run, verify these. Stop and tell the user honestly if a required input is missing.

| Requirement | How to check | If missing |
|---|---|---|
| Candidates JSON file | Pick the freshest `data/raw_scrapes/nattome_raw_*.json` by mtime unless the user specifies one. | Run `nattome-tiktok-candidate-discovery` first, or ask which file to use. |
| Downloadable video sources | Candidate rows need `video_download_url`; the Minimum Eligibility Filter requires this by default. | Tell the user the scrape is not evidence-ready. Use metadata-preview config only if explicitly requested. |
| `GEMINI_API_KEY` env var or project root `.env` | Load/check `.env`, then check `$env:GEMINI_API_KEY` in PowerShell without printing the value. | Ask the user to set it. Without it, the run records missing Gemini evidence rather than fabricating analysis. |
| `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | Env vars. | Optional. Skip Telegram silently if either is missing. |

Candidate JSON from `nattome-tiktok-candidate-discovery` is UTF-8. Preserve UTF-8 reads/writes for candidate JSON, reports, workbook-adjacent structured data, manifests, and Telegram logs so Unicode captions do not fail on Windows `cp1252`.

`APIFY_TOKEN` is needed only if you must run fresh discovery first. A Batch Analysis Run can use an existing candidates JSON without calling Apify.

## Choose The Mode

| Mode | Batch size | When to use |
|---|---:|---|
| `debug` | 1 | Smoke test, schema check, or one-video analysis. |
| `daily` | 5 | Daily evidence analysis for the exact top videos from `nattome-tiktok-candidate-discovery`. Preserves input order and does not rerank to 10. |
| `quick` | 5 | Pilot or mid-week sanity check. |
| `default` | 10 | Weekly standard run. Use this unless the user says otherwise. |
| `deep` | 20 | Strategic deep-dive. Use only when explicitly asked. |

If the user asks for the top candidate or one video, use `debug`. If the user asks to analyze the daily report videos, use `daily` with the newest `data/daily_selections/nattome_daily_*_top5.json`. If the user asks for a full weekly batch and does not specify size, use `default`.

## The Run

From the project root, with the freshest candidates JSON:

```powershell
python scripts/run_batch_analysis.py `
  --mode default `
  --candidates data/raw_scrapes/nattome_raw_<YYYYMMDD>_top30.json
```

For daily evidence analysis, use the daily handoff produced by `nattome-tiktok-candidate-discovery`:

```powershell
python scripts/run_batch_analysis.py `
  --mode daily `
  --candidates data/daily_selections/nattome_daily_<YYYYMMDD>_top5.json
```

Daily mode preserves the handoff order and analyzes only those 4-5 daily report videos that pass the Minimum Eligibility Filter.

Optional flags:

- `--batch-size N` — override the mode's default batch size.
- `--config <path>` — merge extra JSON config into runtime configuration.
- `--runs-dir <path>` — change the runs root; default is `runs/batch-analysis`.
- `--timestamp <ISO8601Z>` — deterministic timestamp for tests.

Do not pass `--ffmpeg-bin`, `--ocr-primary-bin`, `--ocr-fallback-bin`, or `--transcription-bin`; those legacy flags were retired.

Stream the CLI output to the user as it runs. Preserve missing-evidence signals exactly. Do not claim Gemini inspected a video if `gemini_evidence` is missing, failed, or partial.

## After The Run

1. Read `outputs/reports/YYYY-MM-DD/top5_creative_production_report_YYYY-MM-DD.md`.
2. Confirm `outputs/reports/YYYY-MM-DD/top5_angle_planning_sheet_YYYY-MM-DD.xlsx` exists.
3. Read the top per-video reports from `runs/batch-analysis/<latest>/reports/*_video_evidence_report.md` when source evidence detail is needed.
4. Quote the **Nattome Priority Score** out of 30 for the top 3 available Shootable Angles.
5. Surface **Manual Review Flags** from `data/*_evidence_quality.json`.
6. Surface **Claim Safety Review** findings from `data/*_claim_safety_review.json`.
7. Confirm `logs/telegram_delivery.json` if Telegram delivery was configured.
8. Tell the user both final output paths and the Run Folder path.

## Honest Reporting Rules

- Never invent visible text, spoken content, visual observations, audio cues, hook evidence, claim evidence, source video availability, or download success.
- Gemini evidence can be `completed`, `partial`, `missing_credentials`, `missing`, or `failed`. Preserve that status in your reply.
- If **Evidence Quality Score** is medium or low, surface the **Manual Review Flag**.
- Do not generate or endorse Shootable Angles that depend on missing Gemini evidence without flagging the uncertainty.
- Claim Safety Review may reject cure claims, cancer prevention claims, zero-side-effect claims, unsourced doctor-recommended claims, unsupported clinical percentages, detox/cleanse claims, guaranteed outcomes, overnight relief claims, or competitor attacks. Do not override it.
- A high-view video with weak engagement is not automatically a viral success. Say when the evidence suggests paid push or bait.

## When The User Asks Variants

- **"Just run debug"** -> `--mode debug`, 1 video.
- **"Analyze today's daily videos"** -> pick the newest `data/daily_selections/nattome_daily_*_top5.json` and run `--mode daily`.
- **"Use last week's candidates"** -> pick the second-newest scrape from `data/raw_scrapes/`.
- **"Skip Telegram this time"** -> set a config with Telegram disabled or note that missing Telegram env vars intentionally skip delivery.
- **"Re-run on the same candidates"** -> safe; each run gets a fresh timestamped Run Folder.
- **"Clean up old runs"** -> use cleanup deliberately; preserve the Top 5 Creative Production Report, Excel planning workbook, run manifest, internal structured JSON, and logs.

## Reference Files

- `CONTEXT.md` — current domain terminology.
- `docs/prd/gemini-two-layer-evidence-pipeline-architecture-prd.md` — current Gemini/two-layer architecture.
- `docs/adr/0001-...md` and `docs/adr/0002-...md` — batch-first and Gemini evidence-first decisions.
- `skills/nattome-tiktok-candidate-discovery/references/nattome_brand.md` — voice and claim guardrails.
- `skills/nattome-tiktok-candidate-discovery/references/virality_framework.md` — hook taxonomy, pacing, structure, emotional triggers.

## Troubleshooting

- **CLI exits before creating a Run Folder** — usually missing config or candidates file. This is intentional.
- **No candidates selected** — inspect `reports/selected_batch.md` for exclusion reasons, especially missing `video_download_url`.
- **Gemini evidence missing** — check `GEMINI_API_KEY` and `run_manifest.json` phase notes.
- **Reports exist but angles are empty** — Gemini evidence may be missing or too weak; inspect `data/*_gemini_evidence.json` and `data/*_evidence_quality.json`.
- **Telegram skipped** — check `logs/telegram_delivery.json`; missing Telegram credentials are optional, not a run failure.
