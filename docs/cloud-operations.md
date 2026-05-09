# Cloud Operations

This guide describes the cloud Daily Evidence Run v1 system for operators. It covers how new runs are produced, where cloud outputs live, what the Vercel dashboard reads, and what remains local or deferred.

## Runtime Boundaries

Python remains the worker for Apify discovery, Gemini evidence analysis, and Daily Output Set generation. The cloud workflow does not move scraping or evidence generation into Vercel. It runs the same project Python pipeline that local operators use:

- Apify discovery creates a raw scrape and Daily Top-5 Selection handoff.
- Gemini evidence analysis reads the selected source videos and writes timestamped evidence outputs.
- Daily Output Set generation writes the final markdown report, structured JSON, spreadsheet workbook, and supporting Run Folder artifacts.

GitHub Actions runs the daily worker at `09:00 Asia/Singapore` (`01:00 UTC`) through the **Daily Evidence Run Cloud Publisher** workflow. The workflow can also be started manually from GitHub Actions for verification or recovery, but the Python worker still owns discovery, analysis, and output generation.

Supabase is the cloud publication target:

- Supabase Postgres stores compact run metadata in `daily_evidence_runs`, including run status, timestamp, report date, summary fields, publication status, and publication errors.
- Supabase Postgres stores artifact records in `daily_evidence_artifacts`, including artifact type, storage path, filename, and content type.
- Supabase Storage stores generated artifacts such as final markdown, structured JSON, spreadsheet workbook, raw scrape, Daily Top-5 Selection, and supporting batch-analysis files.

Vercel hosts the public read-only Next.js dashboard in `web/vercel-dashboard/`. The dashboard does not require login, reads run and artifact records through the public anon key under Row Level Security, and links to Supabase Storage artifact downloads. Vercel does not run the Python worker and does not hold service-role credentials.

## Cloud v1 Data Policy

Cloud v1 shows new runs only. It does not import historical local runs into Supabase or the Vercel dashboard. Old local history is preserved locally and remains available through the existing local dashboard and filesystem artifacts.

Operators should use the local backup process for old data preservation before migration or cleanup work. The current backup policy and receipt location are documented in `docs/cloud-migration-safety-checklist.md`; that checklist points to the timestamped backup archive under `local-backups/` and records that historical local data is backed up but not imported into cloud dashboard v1.

## Required Configuration

Secret values must not be written to README files, docs, logs, workflow summaries, issue comments, or dashboard pages. List variable names only.

Required GitHub Actions secrets:

| Secret | Purpose |
|---|---|
| `APIFY_TOKEN` | Runs Apify TikTok discovery. |
| `GEMINI_API_KEY` | Runs Gemini evidence analysis. |
| `SUPABASE_URL` | Publishes run metadata and artifact records to Supabase. |
| `SUPABASE_SERVICE_ROLE_KEY` | Lets the Python worker publish to Supabase. Never expose this in Vercel. |

Optional GitHub Actions secrets:

| Secret | Purpose |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Enables optional Telegram delivery. |
| `TELEGRAM_CHAT_ID` | Selects the optional Telegram target chat. |

Required Vercel environment variables:

| Variable | Purpose |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Lets the Next.js dashboard connect to Supabase read APIs. |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Lets the Next.js dashboard read permitted run and artifact records under Row Level Security. |

Do not configure `SUPABASE_SERVICE_ROLE_KEY` in Vercel. The service-role key belongs only in the GitHub Actions worker environment.

## Deferred Control-Room Scope

Cloud dashboard v1 is read-only. It intentionally defers manual run triggers, scrape setting edits, curation labels, rollback controls, and full control-room behavior.

Those capabilities remain in the local Python dashboard for now:

- Manual run triggers stay local.
- Scrape setting edits stay local.
- Curation labels stay local.
- Rollback controls stay local.
- Full control-room behavior stays local.

Future cloud control-room work should be planned as a separate slice with explicit write permissions, audit trails, and rollback behavior. Do not add cloud write controls to the Vercel dashboard as incidental UI while working on read-only reporting.
