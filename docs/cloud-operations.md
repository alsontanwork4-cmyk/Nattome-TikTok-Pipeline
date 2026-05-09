# Cloud Operations

This guide describes the cloud Daily Evidence Run v1 system for operators. It covers how new runs are produced, where cloud outputs live, and what remains local or deferred.

## Runtime Boundaries

Python remains the worker for Apify discovery, Gemini evidence analysis, Daily Output Set generation, and the operational dashboard. The cloud workflow runs the same project Python pipeline that local operators use:

- Apify discovery creates a raw scrape and Daily Top-3 Selection handoff.
- Gemini evidence analysis reads the selected source videos and writes timestamped evidence outputs.
- Daily Output Set generation writes the final markdown report, structured JSON, spreadsheet workbook, and supporting Run Folder artifacts.

GitHub Actions runs the daily worker at `09:00 Asia/Singapore` (`01:00 UTC`) through the **Daily Evidence Run Cloud Publisher** workflow. The workflow can also be started manually from GitHub Actions for verification or recovery, but the Python worker still owns discovery, analysis, and output generation.

Supabase is the cloud publication target:

- Supabase Postgres stores compact run metadata in `daily_evidence_runs`, including run status, timestamp, report date, summary fields, publication status, and publication errors.
- Supabase Postgres stores artifact records in `daily_evidence_artifacts`, including artifact type, storage path, filename, and content type.
- Supabase Storage stores generated artifacts such as final markdown, structured JSON, spreadsheet workbook, raw scrape, Daily Top-3 Selection, and supporting batch-analysis files.

The Python dashboard in `dashboard/` is the operational dashboard. Host it on a VPS or other long-running app host when remote access is needed. It requires durable access to the dashboard SQLite database and local pipeline folders such as `data/`, `runs/`, and `outputs/`.

## Cloud v1 Data Policy

Cloud v1 publishes new runs only. It does not import historical local runs into Supabase. Old local history is preserved locally and remains available through the Python dashboard and filesystem artifacts.

Operators should use the local backup process for old data preservation before migration or cleanup work. The current backup policy and receipt location are documented in `docs/cloud-migration-safety-checklist.md`; that checklist points to the timestamped backup archive under `local-backups/` and records that historical local data is backed up but not imported into cloud dashboard v1.

## Required Configuration

Secret values must not be written to README files, docs, logs, workflow summaries, issue comments, or dashboard pages. List variable names only.

Required GitHub Actions secrets:

| Secret | Purpose |
|---|---|
| `APIFY_TOKEN` | Runs Apify TikTok discovery. |
| `GEMINI_API_KEY` | Runs Gemini evidence analysis. |
| `SUPABASE_URL` | Publishes run metadata and artifact records to Supabase. |
| `SUPABASE_SERVICE_ROLE_KEY` | Lets the Python worker publish to Supabase. Never expose this in client-side code or dashboard pages. |

Optional GitHub Actions secrets:

| Secret | Purpose |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Enables optional Telegram delivery. |
| `TELEGRAM_CHAT_ID` | Selects the optional Telegram target chat. |

There is no separate web dashboard configuration. The removed Next.js dashboard is no longer part of this repository.

## Deferred Control-Room Scope

Cloud dashboard v1 is read-only. It intentionally defers manual run triggers, scrape setting edits, curation labels, rollback controls, and full control-room behavior.

Those capabilities remain in the Python dashboard:

- Manual run triggers stay local.
- Scrape setting edits stay local.
- Curation labels stay local.
- Rollback controls stay local.
- Full control-room behavior stays local.

Future cloud control-room work should be planned as a separate slice with explicit write permissions, audit trails, and rollback behavior.
