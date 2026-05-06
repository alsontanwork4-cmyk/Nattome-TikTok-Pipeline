---
name: nattome-batch-analysis
description: Weekly batch evidence-first TikTok video analysis pipeline for Nattome (Atomic Group's flagship digestive-health brand). Selects 10 viral TikTok videos via the Minimum Eligibility Filter (10K+ views, ≤30 days old, 3%+ weighted engagement) and Viral Relevance Selection, downloads Evidence Bundles, extracts Hybrid Timeline frames (every second + extra at 0.5s/1.5s/2.5s), runs multilingual OCR (English, Malay, Mandarin, Traditional Chinese, Manglish), Whisper-style transcription, baseline audio/music trend analysis, evidence quality scoring, claim safety review, and generates per-video Video Evidence Reports + Cross-Video Pattern Summary with 30-point Nattome Priority Score, plus structured JSON and CSV spreadsheet exports, and optional Telegram weekly brief delivery. Use whenever the user asks to "run the weekly batch analysis", "do the weekly evidence run", "produce video evidence reports", "run batch evidence analysis", "weekly Nattome research", "analyze a batch of TikToks", "cross-video pattern summary", "claim safety review", or invokes `run_batch_analysis.py`. Different from the daily discovery brief — this is the heavier weekly run that downloads videos, OCRs frames, transcribes audio, and produces durable strategic research with full Evidence Bundles. Use the `nattome-daily-discovery` skill instead for fast daily ideation briefs without video download.
---

# Nattome TikTok Batch Evidence Analysis

You are running Nattome's weekly Batch Analysis Run. The deliverable is **evidence-first strategic research**: every claim about why a video worked must be backed by frames, OCR, transcript, or audio analysis from the actual video — never metadata guesswork. Read `CONTEXT.md` at the project root before producing reports; it is the terminology dictionary for this pipeline.

This skill is for the **weekly** workflow. If the user wants a fast daily content brief without downloading videos or running OCR, use the `nattome-daily-discovery` skill instead.

## What This Pipeline Produces

For one Batch Analysis Run, in `runs/batch-analysis/<timestamp>_<mode>/`:

- `batch_outputs/markdown/` — `selected_batch.md`, `cross_video_pattern_summary.md`, one `video_evidence_report.md` per video
- `batch_outputs/json/` — `selected_batch.json`, `cross_video_pattern_summary.json`, `structured_batch_analysis.json`
- `batch_outputs/spreadsheets/` — `spreadsheet_summary.csv`
- `evidence_bundles/<rank>_<video-id>/` — for each video: `source_metadata.json`, `download_status.json`, `evidence_bundle_index.json`, `artifacts/source_video.<ext>`, `artifacts/frames/...`, `artifacts/audio/...`, `hybrid_timeline.json`, `ocr_evidence.json`, `transcript_evidence.json`, `baseline_audio_analysis.json`, `evidence_quality.json`, `claim_safety_review.json`, `video_evidence_report.md`
- `evidence_bundles/index.json` — run-level bundle index
- `logs/` — Telegram delivery + cleanup logs
- `run_metadata.json` — deterministic record of mode, batch size, candidates path, tool versions, timestamps

A typical default run takes 15–30 minutes depending on tool availability and number of videos that successfully download.

## Pre-Flight Checks

Before launching the run, verify each of these. Stop and tell the user honestly if anything is missing — never fake the run.

| Requirement | How to check | If missing |
|---|---|---|
| `APIFY_TOKEN` env var | `$env:APIFY_TOKEN` (PowerShell) | Ask the user to set it. Skill cannot synthesize candidates. |
| Candidates JSON file | A recent `data/raw_scrapes/nattome_raw_*.json` — pick the freshest by mtime | Run the `nattome-daily-discovery` skill first to produce one, or ask the user which file to use. |
| FFmpeg | `ffmpeg -version` | Tell the user. The CLI will record `not_implemented` for frame extraction rather than fabricate frames. |
| PaddleOCR or Tesseract | `paddleocr --version` or `tesseract --version` | Same — OCR evidence will be marked unavailable, not invented. |
| Whisper | `whisper --version` | Same — transcript evidence will be marked unavailable. |
| `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | env vars | Optional. Skip Telegram silently if either is missing; do not pester. |

## Choose The Mode

| Mode | Batch size | When to use |
|---|---|---|
| `debug` | 1 video | Smoke test or schema check. Use when you've changed the CLI or just want to verify the pipeline runs end-to-end. |
| `quick` | 5 videos | Pilot or mid-week sanity check. Half the work, still gives a usable Cross-Video Pattern Summary. |
| `default` | 10 videos | **The weekly standard run.** Use this unless the user says otherwise. |
| `deep` | 20 videos | Quarterly or strategic deep-dive. Use only when explicitly asked. |

If the user did not specify, default to `default`.

## The Run

From the project root, with the freshest candidates JSON:

```powershell
python scripts/run_batch_analysis.py `
  --mode default `
  --candidates data/raw_scrapes/nattome_raw_<YYYYMMDD>_top30.json
```

Optional flags worth knowing about:
- `--batch-size N` — override the mode's default batch size
- `--config <path>` — merge an extra JSON config into the recorded run configuration
- `--runs-dir <path>` — change the runs root (default `runs/batch-analysis`)
- `--ffmpeg-bin`, `--ocr-primary-bin`, `--ocr-fallback-bin`, `--transcription-bin` — override executable names if they aren't on PATH
- `--timestamp <ISO8601Z>` — deterministic timestamp for tests

Stream the CLI output to the user as it runs. The CLI is structured to surface "not_implemented" honestly when a tool is missing — relay that verbatim, do not paper over it.

## After The Run

1. Read `runs/batch-analysis/<latest>/batch_outputs/markdown/cross_video_pattern_summary.md` and the per-video `video_evidence_report.md` files. Quote the **Nattome Priority Score** (out of 30) for the top 3 videos in your reply.
2. Surface any **Manual Review Flags** from `evidence_quality.json` and any **claim safety findings** from `claim_safety_review.json`. These are the things a human must look at before content gets shot.
3. If `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` are set, the run will deliver the weekly brief to Telegram automatically. Confirm `logs/telegram_delivery.json` shows success. If delivery is `skipped` or `failed`, tell the user which.
4. Tell the user the run folder path so they can open the bundles in Explorer.

## Honest Reporting Rules (Non-Negotiable)

- Never invent OCR text, transcripts, frame contents, audio analysis, or download success. The CLI marks missing pieces as `not_implemented` or records `download_status: failed` — preserve that signal in your reply.
- A video with high views but poor engagement is NOT a viral success — it is a paid push or bait hook. Say so.
- If `evidence_quality` is medium or low for a video, the Manual Review Flag is required. Do not generate Nattome shootable angles for that video without flagging it.
- Claim safety review may reject angles that contain cure claims, cancer prevention claims, "zero side effects", "doctor recommended" without sourcing, vague "clinically proven" without citing UCSI / NCT06524271, or competitor attacks. Do not override the safety review's verdict — surface it and let the human decide.

## When The User Asks Variants

- **"Just run debug"** → `--mode debug`, 1 video, smoke test only.
- **"Use last week's candidates"** → pick the second-newest scrape from `data/raw_scrapes/`.
- **"Skip Telegram this time"** → temporarily unset the Telegram env vars for the call, or note that delivery was intentionally skipped.
- **"Re-run on the same candidates"** → it's safe; each run gets a fresh timestamped folder.
- **"Clean up old runs"** → the cleanup hook (issue 0015) preserves durable outputs (markdown, JSON, CSV) and removes large artifacts. Use it deliberately, never on the most recent run.

## Reference Files

- `CONTEXT.md` (project root) — terminology dictionary: Video Evidence Report, Hybrid Timeline, Evidence Bundle, Cross-Video Pattern Summary, Nattome Priority Score, etc. Read it before writing anything for the user.
- `docs/prd/nattome-tiktok-ocr-video-evidence-pipeline-prd.md` — full product spec and 85 user stories.
- `docs/adr/0001-...md` and `docs/adr/0002-...md` — architecture decisions for batch-first and tool stack.
- `skills/nattome-daily-discovery/references/nattome_brand.md` — voice and claim guardrails (shared with the daily skill).
- `skills/nattome-daily-discovery/references/virality_framework.md` — analysis lens (hook taxonomy, pacing, structure, emotional triggers).

## Troubleshooting

- **CLI exits before creating a Run Folder** — usually missing config or candidates file. The CLI is designed to fail before creating the folder when inputs are invalid; that's intentional.
- **All downloads marked failed** — the candidates file only has TikTok page URLs, not direct download URLs. Apify config must include `video_download_url` extraction. Tell the user; do not retry blindly.
- **OCR returns empty for every frame** — verify the OCR binary is on PATH and supports the languages in the videos (English, Malay, Mandarin, Traditional Chinese). Prefer PaddleOCR for Chinese.
- **Tests passing but pipeline producing weird output** — check `progress.txt` for the most recent issue note; the answer is usually documented there.
